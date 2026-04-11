from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import backend.main
import backend.pipeline
from agents.nfr_agent import AgentRunResult


class FakeEmbedder:
    """Deterministic embedder for tests (no network, no model downloads)."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256((text or "").encode("utf-8")).digest()
            # 8-dim vector in [-1, 1]
            vec = [((digest[i] / 255.0) * 2.0 - 1.0) for i in range(8)]
            vectors.append(vec)
        return vectors


def _agent(content: str) -> AgentRunResult:
    return AgentRunResult(content=content, usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})


def test_api_health() -> None:
    client = TestClient(backend.main.app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_kb_ingest_and_retrieve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Local kb root in temp directory (don't touch repo knowledge_base/).
    kb_root = tmp_path / "knowledge_base"
    (kb_root / "projects").mkdir(parents=True)
    (kb_root / "compliance").mkdir(parents=True)

    (kb_root / "projects" / "demo_001.md").write_text(
        """---
project_id: "demo_001"
industry: "fashion_ecommerce"
tech_stack: ["shopify_plus", "headless"]
scale: "peak"
lessons: ["black_friday"]
---

# Demo

This system needs high availability and performance during seasonal peaks.
""",
        encoding="utf-8",
    )

    persist_dir = tmp_path / ".chroma"

    # Stub embedding so ingest/retrieve don't call OpenAI or sentence-transformers.
    import utils.rag_manager as rag_manager

    rag_manager._EMBED_CACHE.clear()
    rag_manager._RETRIEVE_CACHE.clear()
    monkeypatch.setattr(rag_manager, "get_embedder", lambda provider=None: FakeEmbedder())

    ingest_result = rag_manager.ingest_knowledge_base(kb_root=kb_root, persist_dir=persist_dir, provider="openai")
    assert ingest_result["indexed"] is True
    assert ingest_result["chunk_count"] > 0

    hits = rag_manager.retrieve(
        "high availability performance seasonal peak",
        top_k=5,
        kb_root=kb_root,
        persist_dir=persist_dir,
        provider="openai",
    )
    assert len(hits) > 0
    assert hits[0].metadata.get("project_id") == "demo_001"


def test_generate_endpoint_returns_run(monkeypatch: pytest.MonkeyPatch) -> None:
    # Avoid OpenAI calls by stubbing agent functions used by the pipeline.
    monkeypatch.setenv("RAG_ENABLED", "false")

    monkeypatch.setattr(backend.pipeline, "clarify_gaps", lambda _: _agent("## Gap Clarification Analysis\n- ok"))
    monkeypatch.setattr(
        backend.pipeline,
        "generate_nfrs",
        lambda *_args, **_kwargs: _agent(
            """## NFR Analysis

### System Summary
Test system.

### Non-Functional Requirements

#### Performance & Scalability

| ID | Requirement | Rationale | Target | Based on insights from |
|----|-------------|-----------|--------|------------------------|
| NFR-01 | p95 latency | demo | <200ms | |

### Flagged Gaps
- none
"""
        ),
    )
    monkeypatch.setattr(
        backend.pipeline,
        "score_nfrs",
        lambda _: _agent(
            """## NFR Priority Matrix

### Scoring Summary
| ID | Requirement (short) | Business Risk | Complexity | Priority |
|----|---------------------|--------------|------------|----------|
| NFR-01 | latency | 4 | 2 | CRITICAL |
"""
        ),
    )
    monkeypatch.setattr(
        backend.pipeline,
        "generate_test_criteria",
        lambda *_: _agent(
            """## Test Acceptance Criteria

| NFR | Test Scenario | Tool | Pass Criteria |
|-----|--------------|------|---------------|
| NFR-01 | load | k6 | <200ms |
"""
        ),
    )
    monkeypatch.setattr(backend.pipeline, "detect_conflicts", lambda _: _agent("## NFR Conflict & Tension Analysis\n- none"))
    monkeypatch.setattr(
        backend.pipeline,
        "remediate_nfrs",
        lambda *_: _agent("## Remediation Plan\n- ok"),
    )
    monkeypatch.setattr(
        backend.pipeline,
        "map_compliance",
        lambda *_: _agent("## Compliance Mapping\n- ok"),
    )

    client = TestClient(backend.main.app)
    response = client.post("/api/generate", data={"system_description": "demo system", "project_name": "Demo"})
    assert response.status_code == 200

    payload: dict[str, Any] = response.json()
    assert payload["mode"] == "generate"
    assert "nfr" in payload["results"]
    assert isinstance(payload.get("rag_status"), dict)
    assert payload["counts"]["nfr_count"] >= 1

