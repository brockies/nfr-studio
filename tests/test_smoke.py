from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import backend.main
import backend.orchestrator
import backend.pipeline
from agents.nfr_agent import (
    AgentRunResult,
    COMPLIANCE_MAPPING_PROMPT,
    _sanitize_plantuml_markdown,
    map_compliance,
)
import backend.storage
from backend.storage import hydrate_compliance_details
from utils.redaction import redact_text


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


def test_framework_pack_endpoint_returns_named_packs() -> None:
    client = TestClient(backend.main.app)
    response = client.get("/api/framework-packs")
    assert response.status_code == 200

    payload = response.json()
    assert any(item["key"] == "core_saas" for item in payload)
    assert any(item["key"] == "ai_product" for item in payload)


def test_industry_profile_endpoint_returns_named_profiles() -> None:
    client = TestClient(backend.main.app)
    response = client.get("/api/industry-profiles")
    assert response.status_code == 200

    payload = response.json()
    assert any(item["key"] == "saas" for item in payload)
    assert any(item["key"] == "ai_saas" for item in payload)


def test_chroma_collections_endpoint_returns_collection_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        backend.main,
        "list_chroma_collections",
        lambda: [
            {"name": "nfr_kb", "scope": "shared", "chunk_count": 12},
            {"name": "project_kb__acme", "scope": "project", "chunk_count": 5},
        ],
    )

    client = TestClient(backend.main.app)
    response = client.get("/api/kb/chroma/collections")
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["name"] == "nfr_kb"
    assert payload[1]["scope"] == "project"


def test_chroma_collection_preview_endpoint_returns_items(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        backend.main,
        "preview_chroma_collection",
        lambda collection_name, limit=12: {
            "collection": collection_name,
            "chunk_count": 2,
            "items": [
                {
                    "id": "abc123",
                    "document_preview": "Preview text",
                    "metadata": {"source_path": "knowledge_base/projects/demo.md", "scope": "shared"},
                }
            ],
        },
    )

    client = TestClient(backend.main.app)
    response = client.get("/api/kb/chroma/collections/nfr_kb?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["collection"] == "nfr_kb"
    assert payload["items"][0]["metadata"]["scope"] == "shared"


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


def test_project_attachment_ingest_and_retrieve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import utils.rag_manager as rag_manager

    persist_dir = tmp_path / ".chroma"
    rag_manager._EMBED_CACHE.clear()
    rag_manager._RETRIEVE_CACHE.clear()
    monkeypatch.setattr(rag_manager, "get_embedder", lambda provider=None: FakeEmbedder())

    ingest_result = rag_manager.ingest_project_documents(
        project_name="Acme Procurement",
        documents=[
            {
                "source_name": "supplier_workflow.pdf",
                "source_kind": "document",
                "media_type": "application/pdf",
                "source_path": "attachment::supplier_workflow.pdf",
                "content": "Supplier proposals are uploaded, reviewed by legal, then approved before release.",
            }
        ],
        persist_dir=persist_dir,
        provider="openai",
    )

    hits = rag_manager.retrieve_project_documents(
        "legal review supplier approval workflow",
        project_name="Acme Procurement",
        top_k=3,
        persist_dir=persist_dir,
        provider="openai",
    )

    assert ingest_result["indexed"] is True
    assert ingest_result["collection"] == rag_manager.project_collection_name("Acme Procurement")
    assert len(hits) > 0
    assert hits[0].metadata.get("project_type") == "project_attachment"
    assert hits[0].metadata.get("scope") == "project"


def test_generate_endpoint_returns_run(monkeypatch: pytest.MonkeyPatch) -> None:
    # Avoid OpenAI calls by stubbing agent functions used by the pipeline.
    monkeypatch.setenv("RAG_ENABLED", "false")

    monkeypatch.setattr(backend.pipeline, "clarify_gaps", lambda _: _agent("## Gap Clarification Analysis\n- ok"))
    monkeypatch.setattr(
        backend.pipeline,
        "generate_system_diagram",
        lambda *_args, **_kwargs: _agent(
            """## System Diagram

### Diagram Summary
- Core platform with one external integration.

### PlantUML

```plantuml
@startuml
actor User
rectangle Platform
User --> Platform
@enduml
```
"""
        ),
    )
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
        lambda *_, **__: _agent("## Compliance Mapping\n- ok"),
    )

    client = TestClient(backend.main.app)
    response = client.post("/api/generate", data={"system_description": "demo system", "project_name": "Demo"})
    assert response.status_code == 200

    payload: dict[str, Any] = response.json()
    assert payload["mode"] == "generate"
    assert "diagram" in payload["results"]
    assert "nfr" in payload["results"]
    assert isinstance(payload.get("rag_status"), dict)
    assert payload["counts"]["nfr_count"] >= 1


def test_validate_pipeline_uses_retrieved_project_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "demo-key")

    shared_hit = backend.pipeline.RagHit(
        id="shared-1",
        document="Shared control guidance for audit logging.",
        metadata={
            "project_id": "shared_ref",
            "project_type": "compliance",
            "source_path": "knowledge_base/compliance/shared.md",
            "chunk_index": 0,
            "scope": "shared",
        },
        score=0.9,
    )
    project_hit = backend.pipeline.RagHit(
        id="project-1",
        document="Project workflow includes legal review before approval.",
        metadata={
            "project_id": "Acme",
            "project_type": "project_attachment",
            "source_path": "attachment::workflow.pdf",
            "chunk_index": 0,
            "scope": "project",
        },
        score=0.95,
    )

    captured: dict[str, str] = {}

    def _capture_clarify(content: str) -> AgentRunResult:
        captured["clarify_input"] = content
        return _agent("## Gap Clarification Analysis\n- ok")

    def _capture_validate(content: str, _existing: str) -> AgentRunResult:
        captured["validate_input"] = content
        return _agent("## NFR Validation Report\n- ok")

    monkeypatch.setattr(backend.pipeline, "kb_status", lambda: {"indexed": True, "chunk_count": 3, "file_count": 1, "provider": "openai"})
    monkeypatch.setattr(backend.pipeline, "retrieve", lambda *_args, **_kwargs: [shared_hit])
    monkeypatch.setattr(backend.pipeline, "retrieve_project_documents", lambda *_args, **_kwargs: [project_hit])
    monkeypatch.setattr(backend.pipeline, "ingest_project_documents", lambda **_kwargs: {"indexed": True})
    monkeypatch.setattr(backend.pipeline, "clarify_gaps", _capture_clarify)
    monkeypatch.setattr(backend.pipeline, "validate_nfrs", _capture_validate)
    monkeypatch.setattr(backend.pipeline, "remediate_nfrs", lambda *_: _agent("## Remediation Plan\n- ok"))
    monkeypatch.setattr(backend.pipeline, "map_compliance", lambda *_, **__: _agent("## Compliance Mapping\n- ok"))

    run = backend.pipeline.run_validate_pipeline_sync(
        system_description="Demo system",
        existing_nfrs="NFR-01 demo",
        project_name="Acme",
        attachments=[],
    )

    assert "## Retrieved Context" in captured["clarify_input"]
    assert "Project-specific attachments" in captured["clarify_input"]
    assert "## Retrieved Context" in captured["validate_input"]
    assert run.rag_sources[0].project_type in {"project_attachment", "compliance"}


def test_workflow_runner_updates_states_results_and_progress() -> None:
    run = backend.pipeline.new_run(mode="generate", system_description="demo system")
    context = backend.orchestrator.PipelineExecutionContext(
        run=run,
        combined_system_description="demo system",
        analysis_system_description="demo system",
    )
    progress_states: list[dict[str, str]] = []

    backend.orchestrator.run_workflow(
        context,
        [
            backend.orchestrator.WorkflowStep("one", "Step One", lambda _context: _agent("first result")),
            backend.orchestrator.WorkflowStep("two", "Step Two", lambda _context: _agent("second result")),
        ],
        emit_progress=lambda current_run: progress_states.append(dict(current_run.agent_states)),
        record_usage=backend.pipeline.record_usage,
    )

    assert run.results["one"] == "first result"
    assert run.results["two"] == "second result"
    assert run.agent_states == {"one": "done", "two": "done"}
    assert progress_states == [
        {"one": "waiting", "two": "waiting"},
        {"one": "running", "two": "waiting"},
        {"one": "done", "two": "waiting"},
        {"one": "done", "two": "running"},
        {"one": "done", "two": "done"},
    ]


def test_compliance_prompt_includes_evidence_planning_sections() -> None:
    assert "Applicable, Potentially Applicable, or Not Applicable" in COMPLIANCE_MAPPING_PROMPT
    assert "## Compliance & Evidence Mapping" in COMPLIANCE_MAPPING_PROMPT
    assert "### Prioritised Evidence Plan" in COMPLIANCE_MAPPING_PROMPT
    assert "### Evidence Crosswalks" in COMPLIANCE_MAPPING_PROMPT
    assert "### Proof Gaps" in COMPLIANCE_MAPPING_PROMPT
    assert "What would improve confidence" in COMPLIANCE_MAPPING_PROMPT


def test_map_compliance_includes_selected_framework_pack_and_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def _fake_call(system_prompt: str, user_prompt: str, max_tokens: int = 0) -> AgentRunResult:
        captured["system_prompt"] = system_prompt
        captured["user_prompt"] = user_prompt
        captured["max_tokens"] = str(max_tokens)
        return _agent("## Compliance Mapping\n- ok")

    monkeypatch.setattr("agents.nfr_agent._call_openai", _fake_call)

    map_compliance(
        "Demo system",
        "NFR-01 demo",
        "supporting analysis",
        framework_pack="ai_product",
        industry_profile="ai_saas",
    )

    assert "## Selected Framework Pack" in captured["user_prompt"]
    assert "Name: AI Product" in captured["user_prompt"]
    assert "- EU AI Act" in captured["user_prompt"]
    assert "Guidance: Bias toward AI governance" in captured["user_prompt"]
    assert "## Selected Industry Profile" in captured["user_prompt"]
    assert "Name: AI SaaS" in captured["user_prompt"]
    assert "- human oversight" in captured["user_prompt"]


def test_hydrate_compliance_details_parses_structured_sections() -> None:
    run = backend.pipeline.new_run(mode="generate", system_description="demo system")
    run.results["compliance"] = """## Compliance & Evidence Mapping

### Relevant Frameworks
- **EU AI Act** - Applicability: `Applicable`
  - The system uses AI to support user-facing business decisions.
  - Confidence note: AI usage is explicitly described.
  - What would improve confidence: Clear confirmation of whether the system falls into a regulated high-risk use case.
- **PCI DSS** - Applicability: `Not Applicable`
  - Core workflows do not directly process cardholder data.

### Mapping Matrix

| Framework | Applicability | NFR Theme / Requirement | Control Theme | Coverage View | Evidence Required | Suggested Owner | Validation Approach | Notes |
|-----------|---------------|-------------------------|---------------|---------------|-------------------|-----------------|--------------------|-------|
| EU AI Act | Applicable | Human review over AI outputs | Human oversight | Partial | Oversight procedure and approval records | Product | Control walkthrough | Demo note |

### Prioritised Evidence Plan

| Priority | NFR / Theme | Evidence Required | Suggested Owner | Suggested Delivery Stage |
|----------|--------------|-------------------|-----------------|--------------------------|
| HIGH | Human oversight | Signed oversight procedure | Product | Before production |

### Evidence Crosswalks

| Evidence Artifact | Supports Frameworks | Control Themes | Usage Scope | Notes |
|-------------------|---------------------|----------------|-------------|-------|
| Oversight procedure and approval records | EU AI Act; ISO/IEC 42001; NIST AI RMF | Human oversight; governance | Shared across AI governance reviews | Reusable across assurance and audit activities |

### Proof Gaps
- No defined AI literacy training artefact yet.
- No clear owner for periodic model-provider reassessment.
"""

    hydrated = hydrate_compliance_details(run)

    assert len(hydrated.compliance_frameworks) == 2
    assert hydrated.compliance_frameworks[0].framework == "EU AI Act"
    assert hydrated.compliance_frameworks[0].applicability == "Applicable"
    assert hydrated.compliance_frameworks[0].confidence_improvement.startswith("Clear confirmation")
    assert len(hydrated.compliance_mappings) == 1
    assert hydrated.compliance_mappings[0].control_theme == "Human oversight"
    assert len(hydrated.evidence_plan) == 1
    assert hydrated.evidence_plan[0].suggested_owner == "Product"
    assert len(hydrated.evidence_crosswalks) == 1
    assert hydrated.evidence_crosswalks[0].evidence_artifact == "Oversight procedure and approval records"
    assert len(hydrated.proof_gaps) == 2


def test_saved_run_pack_round_trip_preserves_pack_and_profile() -> None:
    run = backend.pipeline.new_run(
        mode="generate",
        system_description="demo system",
        project_name="Acme",
        framework_pack="ai_product",
        industry_profile="ai_saas",
    )
    run.results = {
        "clarify": "## Gap Clarification Analysis\n- ok",
        "diagram": "## System Diagram\n- ok",
        "nfr": "## NFR Analysis\n- ok",
        "score": "## NFR Priority Matrix\n- ok",
        "test": "## Test Acceptance Criteria\n- ok",
        "conflict": "## NFR Conflict & Tension Analysis\n- ok",
        "remediate": "## NFR Remediation Plan\n- ok",
        "compliance": "## Compliance & Evidence Mapping\n- ok",
    }

    pack = backend.storage.build_pack(run)
    parsed = backend.storage.parse_saved_run(pack)

    assert parsed["framework_pack"] == "ai_product"
    assert parsed["industry_profile"] == "ai_saas"


def test_redaction_masks_credential_like_values_without_labels() -> None:
    result = redact_text('Temporary login secret is "Tr0ub4dor!2026" for the demo.')

    assert result.changed is True
    assert "[SECRET_01]" in result.redacted_text
    assert any(item.name == "credential-like value" for item in result.items)


def test_redaction_does_not_mask_normal_architecture_text() -> None:
    result = redact_text(
        "The platform uses https://api.example.com, stores files in blob storage, and serves 1500 users."
    )

    assert "[SECRET_" not in result.redacted_text
    assert "[URL_01]" in result.redacted_text


def test_rename_saved_run_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend.storage, "SAVE_DIR", tmp_path)
    source = tmp_path / "demo_run.md"
    source.write_text("# NFR Pack\n\n## System Description\nDemo\n", encoding="utf-8")

    renamed = backend.storage.rename_run_file("demo_run.md", "renamed_demo.md")

    assert renamed.name == "renamed_demo.md"
    assert renamed.exists()
    assert not source.exists()


def test_plantuml_sanitizer_rewrites_boundary_blocks() -> None:
    content = """## System Diagram

### PlantUML

```plantuml
@startuml
boundary "AI Provider" {
  component "LLM API" as LLM
}
@enduml
```
"""

    sanitized = _sanitize_plantuml_markdown(content)

    assert 'boundary "AI Provider"' not in sanitized
    assert 'rectangle "AI Provider"' in sanitized

