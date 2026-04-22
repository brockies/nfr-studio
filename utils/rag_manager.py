"""RAG utilities for NFR Studio (MVP).

Features:
- Ingest markdown documents under knowledge_base/ into a local ChromaDB store
- Retrieve top-k semantically similar chunks with a simple lexical rerank
- Provide formatted context + provenance for prompt injection and UI display

Design goals:
- Optional dependency: if chromadb is not installed, core app still works.
- Simple local persistence: `.chroma/` directory in repo root.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI

from .chunking import chunk_markdown


DEFAULT_CHROMA_DIR = Path(".chroma")
PROJECT_COLLECTION_PREFIX = "project_kb__"
LEGACY_SHARED_COLLECTIONS = {"nfr_kb"}

_EMBED_CACHE: dict[str, list[float]] = {}
_RETRIEVE_CACHE: dict[str, tuple[float, list["RagHit"]]] = {}


EmbedProvider = Literal["openai", "local"]


@dataclass(frozen=True)
class RagHit:
    """One retrieved chunk from the knowledge base."""

    id: str
    document: str
    metadata: dict[str, Any]
    score: float


class RagUnavailable(RuntimeError):
    pass


def _try_import_chroma():  # type: ignore[no-untyped-def]
    try:
        # Avoid noisy telemetry failures if telemetry deps are mismatched.
        # Users can override by explicitly setting ANONYMIZED_TELEMETRY=TRUE.
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")
        import chromadb  # noqa: F401
        from chromadb.config import Settings  # noqa: F401
        from chromadb import PersistentClient  # noqa: F401

        return chromadb
    except Exception as exc:  # pragma: no cover
        raise RagUnavailable(
            "ChromaDB is not available. Install `chromadb` to enable RAG."
        ) from exc


def _frontmatter_split(markdown: str) -> tuple[str, str]:
    """Return (frontmatter_text, body_text). Frontmatter is YAML-ish between --- blocks."""

    content = (markdown or "").replace("\r\n", "\n")
    if not content.lstrip().startswith("---\n"):
        return "", content

    # Only treat very first block as frontmatter.
    start = content.find("---\n")
    end = content.find("\n---\n", start + 4)
    if start != 0 or end == -1:
        return "", content

    fm = content[start + 4 : end].strip()
    body = content[end + 5 :].lstrip("\n")
    return fm, body


def _parse_frontmatter_value(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return ""

    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip() for p in inner.split(",")]
        return [_strip_quotes(p) for p in parts if p]

    return _strip_quotes(raw)


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def parse_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    """Parse a minimal YAML frontmatter block.

    Supported:
    - key: "value"
    - key: [a, b]
    - key:
        - item
        - item2
    """

    fm_text, body = _frontmatter_split(markdown)
    if not fm_text.strip():
        return {}, body

    meta: dict[str, Any] = {}
    lines = [line.rstrip() for line in fm_text.split("\n") if line.strip() and not line.strip().startswith("#")]

    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue

        key, remainder = line.split(":", 1)
        key = key.strip()
        remainder = remainder.strip()

        if remainder:
            meta[key] = _parse_frontmatter_value(remainder)
            i += 1
            continue

        # Multi-line list block
        items: list[str] = []
        j = i + 1
        while j < len(lines):
            next_line = lines[j].lstrip()
            if not next_line.startswith("- "):
                break
            items.append(_strip_quotes(next_line[2:].strip()))
            j += 1

        if items:
            meta[key] = items
            i = j
        else:
            meta[key] = ""
            i += 1

    return meta, body


def _hash_id(*parts: str) -> str:
    joined = "::".join(part.strip() for part in parts if part is not None)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]


def _normalise_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _infer_nfr_category(text: str) -> str:
    lowered = (text or "").lower()
    if "performance" in lowered or "latency" in lowered or "throughput" in lowered or "scalab" in lowered:
        return "performance_scalability"
    if "availability" in lowered or "reliab" in lowered or "resilien" in lowered or "failover" in lowered:
        return "availability_reliability"
    if "security" in lowered or "pci" in lowered or "gdpr" in lowered or "compliance" in lowered:
        return "security_compliance"
    if "operab" in lowered or "observab" in lowered or "monitor" in lowered:
        return "maintainability_operability"
    if "usability" in lowered or "accessib" in lowered:
        return "usability_accessibility"
    if "integration" in lowered or "erp" in lowered or "api" in lowered or "data" in lowered:
        return "data_integration"
    if "disaster" in lowered or "business continuity" in lowered or "dr " in lowered:
        return "dr_bc"
    if "cost" in lowered or "efficien" in lowered:
        return "cost_efficiency"
    return ""


def _tokenize(text: str) -> set[str]:
    # Simple lexical signal for hybrid reranking.
    tokens: set[str] = set()
    for raw in (text or "").lower().replace("/", " ").replace("_", " ").split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if len(token) >= 3:
            tokens.add(token)
    return tokens


def _hybrid_rerank(query: str, hits: list[RagHit]) -> list[RagHit]:
    q = _tokenize(query)
    if not q:
        return sorted(
            hits,
            key=lambda hit: (
                -hit.score,
                str(hit.metadata.get("source_path", "")),
                int(hit.metadata.get("chunk_index", 0) or 0),
                hit.id,
            ),
        )

    rescored: list[tuple[float, RagHit]] = []
    for hit in hits:
        d = _tokenize(hit.document)
        overlap = len(q & d)
        # Higher overlap should win; hit.score is already "similarity-like".
        combined = hit.score + min(0.35, overlap / 40.0)
        rescored.append((combined, hit))

    rescored.sort(
        key=lambda pair: (
            -pair[0],
            str(pair[1].metadata.get("source_path", "")),
            int(pair[1].metadata.get("chunk_index", 0) or 0),
            pair[1].id,
        )
    )
    return [hit for _, hit in rescored]


class Embedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class OpenAIEmbedder(Embedder):
    def __init__(self, *, model: str = "text-embedding-3-small") -> None:
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


class LocalEmbedder(Embedder):
    def __init__(self, *, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RagUnavailable(
                "Local embeddings requested but `sentence-transformers` is not installed."
            ) from exc

        self.model_name = model
        self.model = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return [embedding.tolist() for embedding in embeddings]


def get_embedder(provider: EmbedProvider | None = None) -> Embedder:
    provider = provider or os.getenv("RAG_EMBEDDINGS_PROVIDER", "openai").lower()  # type: ignore[assignment]
    if provider == "local":
        return LocalEmbedder(model=os.getenv("RAG_LOCAL_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    return OpenAIEmbedder(model=os.getenv("RAG_OPENAI_MODEL", "text-embedding-3-small"))


def get_chroma_collection(
    *,
    persist_dir: Path = DEFAULT_CHROMA_DIR,
    collection_name: str,
):
    chromadb = _try_import_chroma()
    from chromadb import PersistentClient  # type: ignore
    from chromadb.config import Settings  # type: ignore

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(name=collection_name)


def get_chroma_client(*, persist_dir: Path = DEFAULT_CHROMA_DIR):
    """Return a persistent Chroma client for collection-level inspection."""

    _try_import_chroma()
    from chromadb import PersistentClient  # type: ignore
    from chromadb.config import Settings  # type: ignore

    persist_dir.mkdir(parents=True, exist_ok=True)
    return PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False),
    )


def retire_legacy_shared_collections(*, persist_dir: Path = DEFAULT_CHROMA_DIR) -> None:
    """Remove deprecated shared collections from the local Chroma store."""

    client = get_chroma_client(persist_dir=persist_dir)
    for collection_name in LEGACY_SHARED_COLLECTIONS:
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            continue


def sanitize_collection_slug(value: str) -> str:
    """Return a deterministic, filesystem-safe collection suffix."""

    cleaned = "".join(
        char.lower() if char.isalnum() or char in {"-", "_"} else "_"
        for char in value.strip()
    )
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("._") or "default"


def project_collection_name(project_name: str) -> str:
    """Return the Chroma collection name for a project-scoped corpus."""

    return f"{PROJECT_COLLECTION_PREFIX}{sanitize_collection_slug(project_name)}"


def collection_count(
    *,
    persist_dir: Path = DEFAULT_CHROMA_DIR,
    collection_name: str,
) -> int:
    """Return the current document count for a collection, or zero if unavailable."""

    try:
        collection = get_chroma_collection(persist_dir=persist_dir, collection_name=collection_name)
        return int(collection.count())
    except Exception:
        return 0


def ingest_project_documents(
    *,
    project_name: str,
    documents: list[dict[str, Any]],
    persist_dir: Path = DEFAULT_CHROMA_DIR,
    provider: EmbedProvider | None = None,
    chunk_size_tokens: int = 800,
    chunk_overlap_tokens: int = 120,
) -> dict[str, Any]:
    """Ingest project-scoped attachment content into its own Chroma collection."""

    project_name = project_name.strip()
    if not project_name:
        return {"indexed": False, "reason": "Project name is required.", "chunk_count": 0}

    collection_name = project_collection_name(project_name)
    collection = get_chroma_collection(persist_dir=persist_dir, collection_name=collection_name)
    embedder = get_embedder(provider)

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for document in documents:
        content = str(document.get("content") or "").strip()
        if not content:
            continue

        source_name = str(document.get("source_name") or "attachment").strip()
        source_kind = str(document.get("source_kind") or "document").strip()
        media_type = str(document.get("media_type") or "").strip()
        source_path = str(document.get("source_path") or f"attachment::{source_name}").strip()

        chunks = chunk_markdown(
            content,
            chunk_size_tokens=chunk_size_tokens,
            chunk_overlap_tokens=chunk_overlap_tokens,
        )

        for chunk in chunks:
            chunk_id = _hash_id(project_name, source_name, str(chunk.index))
            ids.append(chunk_id)
            texts.append(chunk.text)
            metadatas.append(
                {
                    "project_id": project_name,
                    "project_type": "project_attachment",
                    "industry": "",
                    "tech_stack": "",
                    "scale": "",
                    "lessons": "",
                    "nfr_category": _infer_nfr_category(chunk.text),
                    "lesson_learned": "",
                    "source_path": source_path,
                    "chunk_index": chunk.index,
                    "source_name": source_name,
                    "source_kind": source_kind,
                    "media_type": media_type,
                    "scope": "project",
                }
            )

    if not ids:
        return {"indexed": False, "reason": "No project documents contained usable text.", "chunk_count": 0}

    embeddings = embedder.embed(texts)

    try:
        collection.delete(ids=ids)
    except Exception:
        pass

    collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

    return {
        "indexed": True,
        "chunk_count": len(ids),
        "file_count": len(documents),
        "provider": provider or os.getenv("RAG_EMBEDDINGS_PROVIDER", "openai"),
        "collection": collection_name,
        "persist_dir": str(persist_dir),
        "scope": "project",
    }


def kb_status(*, persist_dir: Path = DEFAULT_CHROMA_DIR) -> dict[str, Any]:
    """Return a project-scoped vector store summary."""

    status: dict[str, Any] = {
        "indexed": False,
        "chunk_count": 0,
        "collection_count": 0,
    }

    try:
        retire_legacy_shared_collections(persist_dir=persist_dir)
        collections = list_chroma_collections(persist_dir=persist_dir)
        project_collections = [item for item in collections if item.get("scope") == "project"]
        status["indexed"] = bool(project_collections)
        status["collection_count"] = len(project_collections)
        status["chunk_count"] = sum(int(item.get("chunk_count") or 0) for item in project_collections)
    except RagUnavailable:
        status["indexed"] = False
        status["reason"] = "ChromaDB not installed."
    except Exception:
        status["indexed"] = False
        status["reason"] = "Could not access project collections."

    return status


def list_chroma_collections(*, persist_dir: Path = DEFAULT_CHROMA_DIR) -> list[dict[str, Any]]:
    """Return visible Chroma collections with lightweight stats."""

    retire_legacy_shared_collections(persist_dir=persist_dir)
    client = get_chroma_client(persist_dir=persist_dir)
    collections = client.list_collections()
    items: list[dict[str, Any]] = []

    for collection in collections:
        name = getattr(collection, "name", "")
        count = 0
        try:
            count = int(collection.count())
        except Exception:
            count = 0

        if name.startswith(PROJECT_COLLECTION_PREFIX):
            scope = "project"
        else:
            scope = "other"

        items.append(
            {
                "name": name,
                "scope": scope,
                "chunk_count": count,
            }
        )

    items = [item for item in items if item["scope"] == "project"]
    items.sort(key=lambda item: item["name"])
    return items


def preview_chroma_collection(
    collection_name: str,
    *,
    persist_dir: Path = DEFAULT_CHROMA_DIR,
    limit: int = 12,
) -> dict[str, Any]:
    """Return a lightweight preview of documents and metadata in one collection."""

    collection_name = collection_name.strip()
    if not collection_name:
        raise ValueError("Collection name is required.")

    collection = get_chroma_collection(persist_dir=persist_dir, collection_name=collection_name)
    count = int(collection.count())
    result = collection.get(limit=max(1, limit), include=["documents", "metadatas"])
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    ids = result.get("ids") or []

    items: list[dict[str, Any]] = []
    for index, doc in enumerate(documents):
        metadata = dict(metadatas[index] or {}) if index < len(metadatas) else {}
        text = str(doc or "").strip()
        items.append(
            {
                "id": str(ids[index]) if index < len(ids) else _hash_id(collection_name, str(index)),
                "document_preview": (text[:320].rstrip() + "...") if len(text) > 320 else text,
                "metadata": metadata,
            }
        )

    return {
        "collection": collection_name,
        "chunk_count": count,
        "items": items,
    }


def retrieve(
    query: str,
    *,
    top_k: int = 5,
    persist_dir: Path = DEFAULT_CHROMA_DIR,
    provider: EmbedProvider | None = None,
) -> list[RagHit]:
    """Compatibility shim: shared knowledge-base retrieval has been retired."""

    _ = (query, top_k, persist_dir, provider)
    return []


def retrieve_project_documents(
    query: str,
    *,
    project_name: str,
    top_k: int = 5,
    persist_dir: Path = DEFAULT_CHROMA_DIR,
    provider: EmbedProvider | None = None,
) -> list[RagHit]:
    """Retrieve relevant project-scoped attachment chunks for a query."""

    project_name = project_name.strip()
    if not project_name:
        return []

    collection_name = project_collection_name(project_name)
    if collection_count(persist_dir=persist_dir, collection_name=collection_name) == 0:
        return []

    return _retrieve_from_collection(
        query,
        top_k=top_k,
        persist_dir=persist_dir,
        collection_name=collection_name,
        provider=provider,
    )


def _retrieve_from_collection(
    query: str,
    *,
    top_k: int,
    persist_dir: Path,
    collection_name: str,
    provider: EmbedProvider | None,
) -> list[RagHit]:
    """Shared retrieval implementation for any Chroma collection."""

    collection = get_chroma_collection(persist_dir=persist_dir, collection_name=collection_name)
    provider_name = provider or os.getenv("RAG_EMBEDDINGS_PROVIDER", "openai")
    collection_count_value = int(collection.count())
    cache_ttl = int(os.getenv("RAG_CACHE_TTL_SECONDS", "600") or 600)
    query_key = _hash_id(
        "retrieve",
        provider_name,
        os.getenv("RAG_OPENAI_MODEL", "text-embedding-3-small"),
        os.getenv("RAG_LOCAL_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        collection_name,
        str(collection_count_value),
        str(top_k),
        query,
    )

    now = time.time()
    cached = _RETRIEVE_CACHE.get(query_key)
    if cached and (now - cached[0]) < cache_ttl:
        return cached[1]

    embedder = get_embedder(provider)
    embed_key = _hash_id(
        "embed",
        provider_name,
        os.getenv("RAG_OPENAI_MODEL", "text-embedding-3-small"),
        os.getenv("RAG_LOCAL_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        collection_name,
        query,
    )
    if embed_key in _EMBED_CACHE:
        query_embedding = _EMBED_CACHE[embed_key]
    else:
        query_embedding = embedder.embed([query])[0]
        _EMBED_CACHE[embed_key] = query_embedding

    candidate_k = max(12, top_k * 4)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=candidate_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    hits: list[RagHit] = []
    for idx, doc in enumerate(docs):
        meta = dict(metas[idx] or {})
        distance = float(distances[idx]) if idx < len(distances) and distances[idx] is not None else 0.0
        score = 1.0 / (1.0 + distance)
        hits.append(
            RagHit(
                id=str((results.get("ids") or [[]])[0][idx]) if results.get("ids") else _hash_id(meta.get("source_path", ""), str(idx)),
                document=str(doc or "").strip(),
                metadata=meta,
                score=score,
            )
        )

    hits = _hybrid_rerank(query, hits)
    final_hits = hits[:top_k]
    _RETRIEVE_CACHE[query_key] = (now, final_hits)
    return final_hits


def format_retrieved_context(hits: list[RagHit]) -> str:
    """Format retrieved chunks for safe-ish prompt injection."""

    if not hits:
        return ""

    lines: list[str] = [
        "## Retrieved Context",
        "Use these as grounded reference material. Reuse only what genuinely fits the described system.",
    ]

    for hit in hits:
        meta = hit.metadata or {}
        project_id = meta.get("project_id", "unknown_project")
        industry = meta.get("industry", "")
        tech_stack = meta.get("tech_stack", "")
        scale = meta.get("scale", "")
        lessons = meta.get("lessons", "")
        source_path = meta.get("source_path", "")
        scope = meta.get("scope", "shared")
        snippet = hit.document.strip()
        if len(snippet) > 1400:
            snippet = snippet[:1400].rstrip() + "..."

        lines.extend(
            [
                f"### Source: {project_id}",
                f"- Scope: {'Project-specific retrieval context' if scope == 'project' else 'Other collection'}",
                f"- File: {source_path}",
                f"- Industry: {industry}",
                f"- Tech stack: {tech_stack}",
                f"- Scale: {scale}",
                f"- Lessons: {lessons}",
                "",
                snippet,
                "",
            ]
        )

    return "\n".join(lines).strip()
