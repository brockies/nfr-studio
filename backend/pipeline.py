"""Pipeline orchestration and attachment processing for the API backend."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from fastapi import UploadFile

from backend.industry_profiles import render_industry_profile_context
from backend.orchestrator import PipelineExecutionContext, WorkflowStep, run_workflow
from agents.nfr_agent import (
    AgentRunResult,
    MODEL_NAME,
    answer_nfr_question,
    clarify_gaps,
    detect_conflicts,
    estimate_usage_cost,
    generate_nfrs,
    generate_system_diagram,
    generate_test_criteria,
    map_compliance,
    remediate_nfrs,
    score_nfrs,
    summarize_supporting_attachment,
    validate_nfrs,
)
from utils.attachments import extract_uploaded_attachment
from utils.rag_manager import (
    RagHit,
    RagUnavailable,
    format_retrieved_context,
    ingest_project_documents,
    kb_status,
    retrieve_project_documents,
)
from utils.redaction import describe_redaction_items, redact_text, summarize_redaction

from .models import ChatMessage, RagSource, RagStatus, RedactionPreview, RunPayload, UsageStat
from .storage import hydrate_pack

ProgressCallback = Callable[[RunPayload], None]


@dataclass(frozen=True)
class InMemoryUpload:
    """Minimal adapter so FastAPI uploads can reuse the existing attachment helper."""

    name: str
    type: str
    payload: bytes

    def getvalue(self) -> bytes:
        return self.payload


def emit_progress(run: RunPayload, on_progress: ProgressCallback | None) -> None:
    """Publish a deep-copied run snapshot to the supplied progress callback."""

    if on_progress is None:
        return
    on_progress(run.model_copy(deep=True))


async def buffer_uploads(uploaded_files: Sequence[UploadFile] | None) -> list[InMemoryUpload]:
    """Read FastAPI uploads into in-memory payloads for threaded execution."""

    buffered: list[InMemoryUpload] = []
    for uploaded_file in uploaded_files or []:
        payload = await uploaded_file.read()
        await uploaded_file.seek(0)
        buffered.append(
            InMemoryUpload(
                name=uploaded_file.filename or "attachment",
                type=uploaded_file.content_type or "",
                payload=payload,
            )
        )
    return buffered


def build_usage_stat(label: str, model: str, usage: dict[str, Any]) -> UsageStat:
    """Convert usage details into the API model."""

    usage_dict = {key: int(value or 0) for key, value in dict(usage).items()}
    return UsageStat(
        label=label,
        model=model,
        prompt_tokens=usage_dict.get("prompt_tokens", 0),
        completion_tokens=usage_dict.get("completion_tokens", 0),
        total_tokens=usage_dict.get("total_tokens", 0),
        cached_tokens=usage_dict.get("cached_tokens", 0),
        reasoning_tokens=usage_dict.get("reasoning_tokens", 0),
        estimated_cost=estimate_usage_cost(usage_dict),
    )


def record_usage(
    usage_stats: dict[str, UsageStat],
    agent_key: str,
    label: str,
    result: AgentRunResult,
) -> None:
    """Attach a normalized usage record to the run."""

    usage_stats[agent_key] = build_usage_stat(label, result.model, dict(result.usage))


def compose_system_context(system_description: str, attachment_context: str) -> str:
    """Combine the main description with supporting attachment summaries."""

    description = system_description.strip()
    attachments = attachment_context.strip()
    if not attachments:
        return description
    return f"{description}\n\n{attachments}"


def combine_refinement_context(current_description: str, additional_context: str) -> str:
    """Append additional context to an existing system description."""

    current = current_description.strip()
    extra = additional_context.strip()
    if not extra:
        return current
    return f"""{current}

Additional context added later:
{extra}
"""


def build_redaction_preview(text: str) -> RedactionPreview:
    """Return the same deterministic redaction preview used by Streamlit."""

    result = redact_text(text)
    return RedactionPreview(
        changed=result.changed,
        redacted_text=result.redacted_text,
        summary=summarize_redaction(result),
        items=describe_redaction_items(result),
        counts=result.counts,
    )


def process_supporting_attachments(
    uploaded_files: Sequence[InMemoryUpload] | None,
    mode: str,
) -> tuple[str, dict[str, UsageStat], list[str], list[dict[str, str]]]:
    """Extract and summarize attachments for downstream NFR analysis."""

    if not uploaded_files:
        return "", {}, [], []

    sections = ["## Supporting Attachments"]
    usage_stats: dict[str, UsageStat] = {}
    warnings: list[str] = []
    rag_documents: list[dict[str, str]] = []

    for index, adapter in enumerate(uploaded_files, start=1):
        try:
            extracted = extract_uploaded_attachment(adapter)
            if extracted.kind == "image":
                summary_result = summarize_supporting_attachment(
                    extracted.name,
                    extracted.media_type,
                    image_bytes=extracted.binary_data,
                    truncated=extracted.truncated,
                    extraction_note=extracted.extraction_note,
                )
                rag_documents.append(
                    {
                        "source_name": extracted.name,
                        "source_kind": extracted.kind,
                        "media_type": extracted.media_type,
                        "source_path": f"attachment::{extracted.name}",
                        "content": f"Image attachment summary for {extracted.name}\n\n{summary_result.content.strip()}",
                    }
                )
            else:
                redacted_result = redact_text(extracted.content_text)
                extraction_note = extracted.extraction_note
                if redacted_result.changed:
                    extraction_note = (
                        f"{extraction_note} Sensitive values were masked before analysis."
                    )
                summary_result = summarize_supporting_attachment(
                    extracted.name,
                    extracted.media_type,
                    text_content=redacted_result.redacted_text,
                    truncated=extracted.truncated,
                    extraction_note=extraction_note,
                )
                rag_documents.append(
                    {
                        "source_name": extracted.name,
                        "source_kind": extracted.kind,
                        "media_type": extracted.media_type,
                        "source_path": f"attachment::{extracted.name}",
                        "content": redacted_result.redacted_text,
                    }
                )

            notes = [f"- Type: `{extracted.media_type}`"]
            if extracted.truncated:
                notes.append("- Note: Content was truncated before analysis.")
            sections.append(
                "\n".join(
                    [
                        f"### {extracted.name}",
                        *notes,
                        "",
                        summary_result.content.strip(),
                    ]
                )
            )
            usage_stats[f"attachment_{mode}_{index}"] = build_usage_stat(
                f"Attachment Review: {extracted.name}",
                summary_result.model,
                dict(summary_result.usage),
            )
        except ValueError as exc:
            warnings.append(str(exc))

    if len(sections) == 1:
        return "", usage_stats, warnings, rag_documents
    return "\n\n".join(sections), usage_stats, warnings, rag_documents


def merge_rag_hits(*groups: Sequence[RagHit], top_k: int = 6) -> list[RagHit]:
    """Merge multiple retrieval groups and keep the highest-value unique chunks."""

    merged: list[RagHit] = []
    seen: set[str] = set()

    for hit in sorted(
        (item for group in groups for item in group),
        key=lambda item: (
            -item.score,
            str(item.metadata.get("source_path", "")),
            int(item.metadata.get("chunk_index", 0) or 0),
            item.id,
        ),
    ):
        dedupe_key = f"{hit.metadata.get('source_path', '')}::{hit.metadata.get('chunk_index', 0)}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        merged.append(hit)
        if len(merged) >= top_k:
            break

    return merged


def new_run(
    *,
    mode: str,
    system_description: str,
    existing_nfrs: str = "",
    project_name: str = "",
    framework_pack: str = "core_saas",
    industry_profile: str = "saas",
    attachment_context: str = "",
    warnings: list[str] | None = None,
    result_source: str = "fresh",
) -> RunPayload:
    """Create the base run payload used by both pipelines."""

    return RunPayload(
        mode=mode,
        system_description=system_description,
        existing_nfrs=existing_nfrs,
        project_name=project_name,
        framework_pack=framework_pack,
        industry_profile=industry_profile,
        attachment_context=attachment_context,
        result_source=result_source,
        warnings=warnings or [],
    )


def with_industry_profile_context(content: str, industry_profile: str) -> str:
    """Append the selected industry profile bias to a prompt input."""

    profile_context = render_industry_profile_context(industry_profile).strip()
    if not profile_context:
        return content.strip()
    return f"{content.strip()}\n\n{profile_context}"


def build_agent_states(mode: str) -> dict[str, str]:
    """Return the initial waiting-state map for the selected pipeline mode."""

    if mode == "generate":
        keys = ["clarify", "diagram", "nfr", "score", "test", "conflict", "remediate", "compliance"]
    else:
        keys = ["clarify", "validate", "remediate", "compliance"]
    return {key: "waiting" for key in keys}


def generate_workflow_steps() -> list[WorkflowStep]:
    """Return the ordered generate workflow definition."""

    return [
        WorkflowStep(
            key="clarify",
            label="Gap Clarification Agent",
            runner=lambda context: clarify_gaps(
                f"{context.analysis_system_description}\n\n{context.rag_context}".strip()
                if context.rag_context
                else context.analysis_system_description
            ),
        ),
        WorkflowStep(
            key="diagram",
            label="Diagram Generation Agent",
            runner=lambda context: generate_system_diagram(
                f"{context.analysis_system_description}\n\n{context.rag_context}".strip()
                if context.rag_context
                else context.analysis_system_description
            ),
        ),
        WorkflowStep(
            key="nfr",
            label="NFR Generation Agent",
            runner=lambda context: generate_nfrs(
                f"""## Source System Description
{context.analysis_system_description}

## Gap Clarification Analysis
{context.run.results["clarify"]}

Use the source description as the primary input. Treat the clarification analysis as working assumptions and open questions.""",
                retrieved_context=context.rag_context,
            ),
        ),
        WorkflowStep(
            key="score",
            label="Scoring and Priority Agent",
            runner=lambda context: score_nfrs(context.run.results["nfr"]),
        ),
        WorkflowStep(
            key="test",
            label="Test Acceptance Criteria Agent",
            runner=lambda context: generate_test_criteria(
                context.run.results["nfr"],
                context.run.results["score"],
            ),
        ),
        WorkflowStep(
            key="conflict",
            label="Conflict Detection Agent",
            runner=lambda context: detect_conflicts(context.run.results["nfr"]),
        ),
        WorkflowStep(
            key="remediate",
            label="Remediation Agent",
            runner=lambda context: remediate_nfrs(
                context.analysis_system_description,
                context.run.results["nfr"],
                f"""## Gap Clarification
{context.run.results["clarify"]}

## Priority Analysis
{context.run.results["score"]}

## Conflict Analysis
{context.run.results["conflict"]}
""",
            ),
        ),
        WorkflowStep(
            key="compliance",
            label="Compliance Mapping Agent",
            runner=lambda context: map_compliance(
                context.analysis_system_description,
                context.run.results["nfr"],
                f"""## Priority Analysis
{context.run.results["score"]}

## Remediation Plan
{context.run.results["remediate"]}
""",
                framework_pack=context.run.framework_pack,
                industry_profile=context.run.industry_profile,
            ),
        ),
    ]


def validate_workflow_steps() -> list[WorkflowStep]:
    """Return the ordered validate workflow definition."""

    return [
        WorkflowStep(
            key="clarify",
            label="Gap Clarification Agent",
            runner=lambda context: clarify_gaps(
                f"{context.analysis_system_description}\n\n{context.rag_context}".strip()
                if context.rag_context
                else context.analysis_system_description
            ),
        ),
        WorkflowStep(
            key="validate",
            label="NFR Validation Agent",
            runner=lambda context: validate_nfrs(
                f"""## Source System Description
{context.analysis_system_description}

## Gap Clarification Analysis
{context.run.results["clarify"]}

{context.rag_context}
""",
                context.run.existing_nfrs,
            ),
        ),
        WorkflowStep(
            key="remediate",
            label="Remediation Agent",
            runner=lambda context: remediate_nfrs(
                context.analysis_system_description,
                context.run.existing_nfrs,
                context.run.results["validate"],
            ),
        ),
        WorkflowStep(
            key="compliance",
            label="Compliance Mapping Agent",
            runner=lambda context: map_compliance(
                context.analysis_system_description,
                context.run.existing_nfrs,
                context.run.results["validate"],
                framework_pack=context.run.framework_pack,
                industry_profile=context.run.industry_profile,
            ),
        ),
    ]


def run_generate_pipeline_sync(
    *,
    system_description: str,
    project_name: str = "",
    framework_pack: str = "core_saas",
    industry_profile: str = "saas",
    attachments: Sequence[InMemoryUpload] | None = None,
    attachment_context: str = "",
    result_source: str = "fresh",
    on_progress: ProgressCallback | None = None,
) -> RunPayload:
    """Execute the full generate pipeline."""

    attachment_context_from_files, attachment_usage, warnings, attachment_rag_documents = process_supporting_attachments(
        attachments,
        "generate",
    )
    merged_attachment_context = attachment_context.strip()
    if attachment_context.strip() and attachment_context_from_files.strip():
        merged_attachment_context = (
            f"{attachment_context.strip()}\n\n{attachment_context_from_files.strip()}"
        )
    elif attachment_context_from_files.strip():
        merged_attachment_context = attachment_context_from_files.strip()

    run = new_run(
        mode="generate",
        system_description=system_description,
        project_name=project_name,
        framework_pack=framework_pack,
        industry_profile=industry_profile,
        attachment_context=merged_attachment_context,
        warnings=warnings,
        result_source=result_source,
    )
    combined_system_description = compose_system_context(
        run.system_description,
        run.attachment_context,
    )
    analysis_system_description = with_industry_profile_context(
        combined_system_description,
        run.industry_profile,
    )

    rag_hits = []
    rag_context = ""
    provider = os.getenv("RAG_EMBEDDINGS_PROVIDER", "openai").lower()
    enabled = os.getenv("RAG_ENABLED", "true").lower() not in {"0", "false", "no", "off"}
    kb = kb_status()
    indexed = bool(kb.get("indexed")) and int(kb.get("chunk_count") or 0) > 0
    run.rag_status = RagStatus(
        enabled=enabled,
        indexed=indexed,
        file_count=int(kb.get("collection_count") or 0),
        chunk_count=int(kb.get("chunk_count") or 0),
        provider=str(kb.get("provider") or provider),
        message=str(kb.get("reason") or ""),
    )

    try:
        if enabled and attachment_rag_documents and run.project_name.strip():
            ingest_project_documents(
                project_name=run.project_name,
                documents=attachment_rag_documents,
                provider=provider,
            )

        project_hits: list[RagHit] = []

        if not enabled:
            run.rag_status.message = "Project retrieval is disabled (RAG_ENABLED=false)."
        else:
            if run.project_name.strip():
                if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
                    run.rag_status.message = "OPENAI_API_KEY is missing, so project retrieval is unavailable."
                else:
                    project_hits = retrieve_project_documents(
                        combined_system_description,
                        project_name=run.project_name,
                        top_k=4,
                        provider=provider,
                    )

            if not run.project_name.strip():
                run.rag_status.message = "Add a project name to keep uploaded documents isolated and retrievable."
            elif not indexed and not project_hits:
                run.rag_status.message = "No project-scoped retrieval context exists yet for this project."

            rag_hits = merge_rag_hits(project_hits, top_k=6)
            rag_context = format_retrieved_context(rag_hits)
            run.rag_sources = [
                RagSource(
                    project_id=str(hit.metadata.get("project_id", "")),
                    project_type=str(hit.metadata.get("project_type", "")),
                    industry=str(hit.metadata.get("industry", "")),
                    tech_stack=str(hit.metadata.get("tech_stack", "")),
                    scale=str(hit.metadata.get("scale", "")),
                    lessons=str(hit.metadata.get("lessons", "")),
                    source_path=str(hit.metadata.get("source_path", "")),
                    chunk_index=int(hit.metadata.get("chunk_index", 0) or 0),
                    score=float(hit.score),
                    snippet=(hit.document[:420].rstrip() + "...") if len(hit.document) > 420 else hit.document,
                )
                for hit in rag_hits
            ]
            if run.rag_sources:
                run.rag_status.message = ""
    except RagUnavailable:
        # No-op: RAG is an enhancement layer.
        rag_context = ""
        run.rag_status.message = run.rag_status.message or "ChromaDB is not installed, so project retrieval is unavailable."
    except Exception:
        rag_context = ""
        run.rag_status.message = run.rag_status.message or "Project retrieval failed (continuing without it)."

    run.usage_stats.update(attachment_usage)
    run_workflow(
        PipelineExecutionContext(
            run=run,
            combined_system_description=combined_system_description,
            analysis_system_description=analysis_system_description,
            rag_context=rag_context,
        ),
        generate_workflow_steps(),
        emit_progress=on_progress,
        record_usage=record_usage,
    )

    return hydrate_pack(run)


def run_validate_pipeline_sync(
    *,
    system_description: str,
    existing_nfrs: str,
    project_name: str = "",
    framework_pack: str = "core_saas",
    industry_profile: str = "saas",
    attachments: Sequence[InMemoryUpload] | None = None,
    attachment_context: str = "",
    result_source: str = "fresh",
    on_progress: ProgressCallback | None = None,
) -> RunPayload:
    """Execute the full validate pipeline."""

    attachment_context_from_files, attachment_usage, warnings, attachment_rag_documents = process_supporting_attachments(
        attachments,
        "validate",
    )
    merged_attachment_context = attachment_context.strip()
    if attachment_context.strip() and attachment_context_from_files.strip():
        merged_attachment_context = (
            f"{attachment_context.strip()}\n\n{attachment_context_from_files.strip()}"
        )
    elif attachment_context_from_files.strip():
        merged_attachment_context = attachment_context_from_files.strip()

    run = new_run(
        mode="validate",
        system_description=system_description,
        existing_nfrs=existing_nfrs,
        project_name=project_name,
        framework_pack=framework_pack,
        industry_profile=industry_profile,
        attachment_context=merged_attachment_context,
        warnings=warnings,
        result_source=result_source,
    )
    combined_system_description = compose_system_context(
        run.system_description,
        run.attachment_context,
    )
    analysis_system_description = with_industry_profile_context(
        combined_system_description,
        run.industry_profile,
    )
    rag_hits: list[RagHit] = []
    rag_context = ""
    provider = os.getenv("RAG_EMBEDDINGS_PROVIDER", "openai").lower()
    enabled = os.getenv("RAG_ENABLED", "true").lower() not in {"0", "false", "no", "off"}
    kb = kb_status()
    indexed = bool(kb.get("indexed")) and int(kb.get("chunk_count") or 0) > 0
    run.rag_status = RagStatus(
        enabled=enabled,
        indexed=indexed,
        file_count=int(kb.get("collection_count") or 0),
        chunk_count=int(kb.get("chunk_count") or 0),
        provider=str(kb.get("provider") or provider),
        message=str(kb.get("reason") or ""),
    )
    if enabled and attachment_rag_documents and run.project_name.strip():
        try:
            ingest_project_documents(
                project_name=run.project_name,
                documents=attachment_rag_documents,
                provider=provider,
            )
        except Exception:
            pass

    try:
        project_hits: list[RagHit] = []

        if not enabled:
            run.rag_status.message = "Project retrieval is disabled (RAG_ENABLED=false)."
        else:
            if run.project_name.strip():
                if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
                    run.rag_status.message = "OPENAI_API_KEY is missing, so project retrieval is unavailable."
                else:
                    project_hits = retrieve_project_documents(
                        combined_system_description,
                        project_name=run.project_name,
                        top_k=4,
                        provider=provider,
                    )

            if not run.project_name.strip():
                run.rag_status.message = "Add a project name to keep uploaded documents isolated and retrievable."
            elif not indexed and not project_hits:
                run.rag_status.message = "No project-scoped retrieval context exists yet for this project."

            rag_hits = merge_rag_hits(project_hits, top_k=6)
            rag_context = format_retrieved_context(rag_hits)
            run.rag_sources = [
                RagSource(
                    project_id=str(hit.metadata.get("project_id", "")),
                    project_type=str(hit.metadata.get("project_type", "")),
                    industry=str(hit.metadata.get("industry", "")),
                    tech_stack=str(hit.metadata.get("tech_stack", "")),
                    scale=str(hit.metadata.get("scale", "")),
                    lessons=str(hit.metadata.get("lessons", "")),
                    source_path=str(hit.metadata.get("source_path", "")),
                    chunk_index=int(hit.metadata.get("chunk_index", 0) or 0),
                    score=float(hit.score),
                    snippet=(hit.document[:420].rstrip() + "...") if len(hit.document) > 420 else hit.document,
                )
                for hit in rag_hits
            ]
            if run.rag_sources:
                run.rag_status.message = ""
    except RagUnavailable:
        rag_context = ""
        run.rag_status.message = run.rag_status.message or "ChromaDB is not installed, so project retrieval is unavailable."
    except Exception:
        rag_context = ""
        run.rag_status.message = run.rag_status.message or "Project retrieval failed (continuing without it)."
    run.usage_stats.update(attachment_usage)
    run_workflow(
        PipelineExecutionContext(
            run=run,
            combined_system_description=combined_system_description,
            analysis_system_description=analysis_system_description,
            rag_context=rag_context,
        ),
        validate_workflow_steps(),
        emit_progress=on_progress,
        record_usage=record_usage,
    )

    return hydrate_pack(run)


async def run_generate_pipeline(
    *,
    system_description: str,
    project_name: str = "",
    framework_pack: str = "core_saas",
    industry_profile: str = "saas",
    attachments: Sequence[UploadFile] | None = None,
    attachment_context: str = "",
    result_source: str = "fresh",
    on_progress: ProgressCallback | None = None,
) -> RunPayload:
    """Execute the full generate pipeline without blocking the event loop."""

    buffered_attachments = await buffer_uploads(attachments)
    return await asyncio.to_thread(
        run_generate_pipeline_sync,
        system_description=system_description,
        project_name=project_name,
        framework_pack=framework_pack,
        industry_profile=industry_profile,
        attachments=buffered_attachments,
        attachment_context=attachment_context,
        result_source=result_source,
        on_progress=on_progress,
    )


async def run_validate_pipeline(
    *,
    system_description: str,
    existing_nfrs: str,
    project_name: str = "",
    framework_pack: str = "core_saas",
    industry_profile: str = "saas",
    attachments: Sequence[UploadFile] | None = None,
    attachment_context: str = "",
    result_source: str = "fresh",
    on_progress: ProgressCallback | None = None,
) -> RunPayload:
    """Execute the full validate pipeline without blocking the event loop."""

    buffered_attachments = await buffer_uploads(attachments)
    return await asyncio.to_thread(
        run_validate_pipeline_sync,
        system_description=system_description,
        existing_nfrs=existing_nfrs,
        project_name=project_name,
        framework_pack=framework_pack,
        industry_profile=industry_profile,
        attachments=buffered_attachments,
        attachment_context=attachment_context,
        result_source=result_source,
        on_progress=on_progress,
    )


def build_followup_context(run: RunPayload) -> str:
    """Build grounded context for the follow-up assistant."""

    if run.mode == "generate":
        sections = [
            ("Gap Clarification", run.results.get("clarify", "")),
            ("System Diagram", run.results.get("diagram", "")),
            ("Generated NFRs", run.results.get("nfr", "")),
            ("Priority Matrix", run.results.get("score", "")),
            ("Test Acceptance Criteria", run.results.get("test", "")),
            ("Conflicts", run.results.get("conflict", "")),
            ("Remediation", run.results.get("remediate", "")),
            ("Compliance Mapping", run.results.get("compliance", "")),
        ]
    else:
        sections = [
            ("Gap Clarification", run.results.get("clarify", "")),
            ("Validation Report", run.results.get("validate", "")),
            ("Remediation", run.results.get("remediate", "")),
            ("Compliance Mapping", run.results.get("compliance", "")),
        ]

    parts = [
        f"## Mode\n{run.mode.title()}",
        f"## System Description\n{run.system_description}",
    ]
    if run.project_name.strip():
        parts.append(f"## Project\n{run.project_name}")
    if getattr(run, "industry_profile", "").strip():
        parts.append(f"## Industry Profile\n{run.industry_profile}")
    if getattr(run, "framework_pack", "").strip():
        parts.append(f"## Framework Pack\n{run.framework_pack}")
    if run.attachment_context.strip():
        parts.append(run.attachment_context.strip())
    if run.mode == "validate" and run.existing_nfrs.strip():
        parts.append(f"## Existing NFRs\n{run.existing_nfrs}")
    for title, content in sections:
        if content:
            parts.append(f"## {title}\n{content}")
    return "\n\n".join(parts)


def answer_follow_up(
    *,
    run: RunPayload,
    question: str,
    history: Sequence[ChatMessage] | None = None,
) -> tuple[str, UsageStat]:
    """Answer a grounded follow-up question about the current run."""

    history_payload = [
        message.model_dump() if hasattr(message, "model_dump") else message.dict()
        for message in history or []
    ]
    answer = answer_nfr_question(
        build_followup_context(run),
        question,
        history=history_payload,
    )
    usage = build_usage_stat("Follow-up Question", answer.model, dict(answer.usage))
    return answer.content, usage


async def refine_run(run: RunPayload, additional_context: str) -> RunPayload:
    """Rerun the current workflow with additional context appended."""

    redaction_preview = build_redaction_preview(additional_context.strip())
    processed_context = redaction_preview.redacted_text.strip()
    refined_description = combine_refinement_context(
        run.system_description,
        processed_context,
    )

    if run.mode == "generate":
        return await run_generate_pipeline(
            system_description=refined_description,
            project_name=run.project_name,
            framework_pack=run.framework_pack,
            industry_profile=run.industry_profile,
            attachment_context=run.attachment_context,
            result_source="refined",
        )

    return await run_validate_pipeline(
        system_description=refined_description,
        existing_nfrs=run.existing_nfrs,
        project_name=run.project_name,
        framework_pack=run.framework_pack,
        industry_profile=run.industry_profile,
        attachment_context=run.attachment_context,
        result_source="refined",
    )


def usage_summary(usage_stats: dict[str, UsageStat]) -> str:
    """Build a short usage summary for the frontend."""

    prompt_tokens = sum(item.prompt_tokens for item in usage_stats.values())
    completion_tokens = sum(item.completion_tokens for item in usage_stats.values())
    total_tokens = sum(item.total_tokens for item in usage_stats.values())
    estimated_cost = sum(item.estimated_cost for item in usage_stats.values())
    return (
        f"Usage: {total_tokens:,} total tokens "
        f"({prompt_tokens:,} in, {completion_tokens:,} out) "
        f"- Estimated cost: ${estimated_cost:.4f} using {MODEL_NAME} pricing."
    )
