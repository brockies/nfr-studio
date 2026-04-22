"""Pydantic models shared across the API surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Mode = Literal["generate", "validate"]
ResultSource = Literal["fresh", "loaded", "refined"]
ChatRole = Literal["user", "assistant"]
RunJobState = Literal["queued", "running", "completed", "failed"]


class UsageStat(BaseModel):
    """Stable usage and estimated cost details for one agent call."""

    label: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    estimated_cost: float = 0.0


class RunCounts(BaseModel):
    """Quick summary values used by the frontend."""

    nfr_count: int = 0
    critical_count: int = 0
    agents_run: int = 0


class RagSource(BaseModel):
    """One retrieved knowledge base chunk used as context for a run."""

    project_id: str = ""
    project_type: str = ""
    industry: str = ""
    tech_stack: str = ""
    scale: str = ""
    lessons: str = ""
    source_path: str = ""
    chunk_index: int = 0
    score: float = 0.0
    snippet: str = ""


class RagStatus(BaseModel):
    """Current RAG availability/health for a run."""

    enabled: bool = True
    indexed: bool = False
    file_count: int = 0
    chunk_count: int = 0
    provider: str = "openai"
    message: str = ""


class KnowledgeBaseFile(BaseModel):
    target: str = ""
    filename: str = ""
    relative_path: str = ""
    project_id: str = ""
    industry: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    scale: str = ""
    lessons: list[str] = Field(default_factory=list)
    modified: int = 0
    bytes: int = 0


class ComplianceFramework(BaseModel):
    framework: str = ""
    applicability: str = ""
    rationale: str = ""
    confidence_note: str = ""
    confidence_improvement: str = ""


class ComplianceMappingRow(BaseModel):
    framework: str = ""
    applicability: str = ""
    nfr_theme: str = ""
    control_theme: str = ""
    coverage_view: str = ""
    evidence_required: str = ""
    suggested_owner: str = ""
    validation_approach: str = ""
    notes: str = ""


class EvidencePlanItem(BaseModel):
    priority: str = ""
    nfr_theme: str = ""
    evidence_required: str = ""
    suggested_owner: str = ""
    suggested_delivery_stage: str = ""


class EvidenceCrosswalkItem(BaseModel):
    evidence_artifact: str = ""
    supports_frameworks: str = ""
    control_themes: str = ""
    usage_scope: str = ""
    notes: str = ""


class RunPayload(BaseModel):
    """Complete generate or validate run returned by the API."""

    mode: Mode
    system_description: str
    existing_nfrs: str = ""
    project_name: str = ""
    framework_pack: str = "core_saas"
    industry_profile: str = "saas"
    attachment_context: str = ""
    result_source: ResultSource = "fresh"
    results: dict[str, str] = Field(default_factory=dict)
    agent_states: dict[str, str] = Field(default_factory=dict)
    usage_stats: dict[str, UsageStat] = Field(default_factory=dict)
    counts: RunCounts = Field(default_factory=RunCounts)
    warnings: list[str] = Field(default_factory=list)
    pack_markdown: str = ""
    rag_sources: list[RagSource] = Field(default_factory=list)
    rag_status: RagStatus = Field(default_factory=RagStatus)
    compliance_frameworks: list[ComplianceFramework] = Field(default_factory=list)
    compliance_mappings: list[ComplianceMappingRow] = Field(default_factory=list)
    evidence_plan: list[EvidencePlanItem] = Field(default_factory=list)
    evidence_crosswalks: list[EvidenceCrosswalkItem] = Field(default_factory=list)
    proof_gaps: list[str] = Field(default_factory=list)


class SavedRunSummary(BaseModel):
    """Saved run metadata shown in the frontend sidebar."""

    file_name: str
    project_name: str = ""
    mode: Mode
    mode_label: str
    kind_label: str
    modified: str


class SavedRunDetail(BaseModel):
    """Loaded saved run plus metadata."""

    file_name: str
    modified: str
    run: RunPayload


class SaveRunRequest(BaseModel):
    """Persist the supplied run with the provided filename."""

    filename: str
    run: RunPayload


class RenameRunRequest(BaseModel):
    """Rename an existing saved run file."""

    current_filename: str
    new_filename: str


class SaveRunResponse(BaseModel):
    """Result of saving a run."""

    file_name: str
    modified: str


class ChatMessage(BaseModel):
    """Follow-up chat entry bound to a run."""

    role: ChatRole
    content: str


class FollowUpRequest(BaseModel):
    """Ask a grounded question about an existing run."""

    run: RunPayload
    question: str
    history: list[ChatMessage] = Field(default_factory=list)


class FollowUpResponse(BaseModel):
    """Follow-up answer with usage metadata."""

    answer: str
    usage: UsageStat


class RedactionPreview(BaseModel):
    """Redaction preview returned to the frontend."""

    changed: bool
    redacted_text: str
    summary: str
    items: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class RedactionRequest(BaseModel):
    """Preview request for deterministic input masking."""

    text: str


class RefineRunRequest(BaseModel):
    """Request to rerun an existing workflow with additional context."""

    run: RunPayload
    additional_context: str


class RunJobStatus(BaseModel):
    """Current state of a background run plus the latest run snapshot."""

    job_id: str
    mode: Mode
    status: RunJobState
    run: RunPayload | None = None
    error: str = ""
