"""Pipeline orchestration and attachment processing for the API backend."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from fastapi import UploadFile

from agents.nfr_agent import (
    AgentRunResult,
    MODEL_NAME,
    answer_nfr_question,
    clarify_gaps,
    detect_conflicts,
    estimate_usage_cost,
    generate_nfrs,
    generate_test_criteria,
    map_compliance,
    remediate_nfrs,
    score_nfrs,
    summarize_supporting_attachment,
    validate_nfrs,
)
from utils.attachments import extract_uploaded_attachment
from utils.rag_manager import RagUnavailable, format_retrieved_context, kb_status, retrieve
from utils.redaction import describe_redaction_items, redact_text, summarize_redaction

from .models import ChatMessage, RagSource, RagStatus, RedactionPreview, RunPayload, UsageStat
from .storage import hydrate_pack


GENERATE_AGENTS: list[tuple[str, str]] = [
    ("clarify", "Gap Clarification Agent"),
    ("nfr", "NFR Generation Agent"),
    ("score", "Scoring and Priority Agent"),
    ("test", "Test Acceptance Criteria Agent"),
    ("conflict", "Conflict Detection Agent"),
    ("remediate", "Remediation Agent"),
    ("compliance", "Compliance Mapping Agent"),
]

VALIDATE_AGENTS: list[tuple[str, str]] = [
    ("clarify", "Gap Clarification Agent"),
    ("validate", "NFR Validation Agent"),
    ("remediate", "Remediation Agent"),
    ("compliance", "Compliance Mapping Agent"),
]

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
) -> tuple[str, dict[str, UsageStat], list[str]]:
    """Extract and summarize attachments for downstream NFR analysis."""

    if not uploaded_files:
        return "", {}, []

    sections = ["## Supporting Attachments"]
    usage_stats: dict[str, UsageStat] = {}
    warnings: list[str] = []

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
        return "", usage_stats, warnings
    return "\n\n".join(sections), usage_stats, warnings


def new_run(
    *,
    mode: str,
    system_description: str,
    existing_nfrs: str = "",
    project_name: str = "",
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
        attachment_context=attachment_context,
        result_source=result_source,
        warnings=warnings or [],
    )


def build_agent_states(mode: str) -> dict[str, str]:
    """Return the initial waiting-state map for the selected pipeline mode."""

    if mode == "generate":
        return {key: "waiting" for key, _ in GENERATE_AGENTS}
    return {key: "waiting" for key, _ in VALIDATE_AGENTS}


def run_generate_pipeline_sync(
    *,
    system_description: str,
    project_name: str = "",
    attachments: Sequence[InMemoryUpload] | None = None,
    attachment_context: str = "",
    result_source: str = "fresh",
    on_progress: ProgressCallback | None = None,
) -> RunPayload:
    """Execute the full generate pipeline."""

    attachment_context_from_files, attachment_usage, warnings = process_supporting_attachments(
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
        attachment_context=merged_attachment_context,
        warnings=warnings,
        result_source=result_source,
    )
    combined_system_description = compose_system_context(
        run.system_description,
        run.attachment_context,
    )

    rag_hits = []
    rag_context = ""
    provider = os.getenv("RAG_EMBEDDINGS_PROVIDER", "openai").lower()
    enabled = os.getenv("RAG_ENABLED", "true").lower() not in {"0", "false", "no", "off"}
    kb = kb_status()
    indexed = bool(kb.get("indexed")) and int(kb.get("chunk_count") or 0) > 0 and int(kb.get("file_count") or 0) > 0
    run.rag_status = RagStatus(
        enabled=enabled,
        indexed=indexed,
        file_count=int(kb.get("file_count") or 0),
        chunk_count=int(kb.get("chunk_count") or 0),
        provider=str(kb.get("provider") or provider),
        message=str(kb.get("reason") or ""),
    )

    try:
        if not enabled:
            run.rag_status.message = "Knowledge base retrieval is disabled (RAG_ENABLED=false)."
        elif not indexed:
            if run.rag_status.file_count == 0:
                run.rag_status.message = "No knowledge base files found under knowledge_base/."
            else:
                run.rag_status.message = "Knowledge base not indexed yet. Ingest it via Admin: Knowledge Base or scripts/ingest_knowledge_base.py."
        elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            run.rag_status.message = "OPENAI_API_KEY is missing, so knowledge base retrieval is unavailable."
        else:
            # RAG retrieval runs once and its context is reused for all downstream agents.
            rag_hits = retrieve(combined_system_description, top_k=5)
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
                    snippet=(hit.document[:420].rstrip() + "…") if len(hit.document) > 420 else hit.document,
                )
                for hit in rag_hits
            ]
            if run.rag_sources:
                run.rag_status.message = ""
    except RagUnavailable:
        # No-op: RAG is an enhancement layer.
        rag_context = ""
        run.rag_status.message = run.rag_status.message or "ChromaDB is not installed, so knowledge base retrieval is unavailable."
    except Exception:
        rag_context = ""
        run.rag_status.message = run.rag_status.message or "Knowledge base retrieval failed (continuing without it)."

    run.agent_states = build_agent_states("generate")
    run.usage_stats.update(attachment_usage)
    emit_progress(run, on_progress)

    run.agent_states["clarify"] = "running"
    emit_progress(run, on_progress)
    clarify_input = combined_system_description
    if rag_context:
        clarify_input = f"{clarify_input}\n\n{rag_context}"
    clarify_run = clarify_gaps(clarify_input)
    run.results["clarify"] = clarify_run.content
    record_usage(run.usage_stats, "clarify", "Gap Clarification Agent", clarify_run)
    run.agent_states["clarify"] = "done"
    emit_progress(run, on_progress)

    run.agent_states["nfr"] = "running"
    emit_progress(run, on_progress)
    nfr_input = f"""## Source System Description
{combined_system_description}

## Gap Clarification Analysis
{run.results["clarify"]}

Use the source description as the primary input. Treat the clarification analysis as working assumptions and open questions."""
    nfr_run = generate_nfrs(nfr_input, retrieved_context=rag_context)
    run.results["nfr"] = nfr_run.content
    record_usage(run.usage_stats, "nfr", "NFR Generation Agent", nfr_run)
    run.agent_states["nfr"] = "done"
    emit_progress(run, on_progress)

    run.agent_states["score"] = "running"
    emit_progress(run, on_progress)
    score_run = score_nfrs(run.results["nfr"])
    run.results["score"] = score_run.content
    record_usage(run.usage_stats, "score", "Scoring and Priority Agent", score_run)
    run.agent_states["score"] = "done"
    emit_progress(run, on_progress)

    run.agent_states["test"] = "running"
    emit_progress(run, on_progress)
    test_run = generate_test_criteria(run.results["nfr"], run.results["score"])
    run.results["test"] = test_run.content
    record_usage(run.usage_stats, "test", "Test Acceptance Criteria Agent", test_run)
    run.agent_states["test"] = "done"
    emit_progress(run, on_progress)

    run.agent_states["conflict"] = "running"
    emit_progress(run, on_progress)
    conflict_run = detect_conflicts(run.results["nfr"])
    run.results["conflict"] = conflict_run.content
    record_usage(run.usage_stats, "conflict", "Conflict Detection Agent", conflict_run)
    run.agent_states["conflict"] = "done"
    emit_progress(run, on_progress)

    run.agent_states["remediate"] = "running"
    emit_progress(run, on_progress)
    remediation_input = f"""## Gap Clarification
{run.results["clarify"]}

## Priority Analysis
{run.results["score"]}

## Conflict Analysis
{run.results["conflict"]}
"""
    remediation_run = remediate_nfrs(
        combined_system_description,
        run.results["nfr"],
        remediation_input,
    )
    run.results["remediate"] = remediation_run.content
    record_usage(run.usage_stats, "remediate", "Remediation Agent", remediation_run)
    run.agent_states["remediate"] = "done"
    emit_progress(run, on_progress)

    run.agent_states["compliance"] = "running"
    emit_progress(run, on_progress)
    compliance_input = f"""## Priority Analysis
{run.results["score"]}

## Remediation Plan
{run.results["remediate"]}
"""
    compliance_run = map_compliance(
        combined_system_description,
        run.results["nfr"],
        compliance_input,
    )
    run.results["compliance"] = compliance_run.content
    record_usage(run.usage_stats, "compliance", "Compliance Mapping Agent", compliance_run)
    run.agent_states["compliance"] = "done"
    emit_progress(run, on_progress)

    return hydrate_pack(run)


def run_validate_pipeline_sync(
    *,
    system_description: str,
    existing_nfrs: str,
    project_name: str = "",
    attachments: Sequence[InMemoryUpload] | None = None,
    attachment_context: str = "",
    result_source: str = "fresh",
    on_progress: ProgressCallback | None = None,
) -> RunPayload:
    """Execute the full validate pipeline."""

    attachment_context_from_files, attachment_usage, warnings = process_supporting_attachments(
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
        attachment_context=merged_attachment_context,
        warnings=warnings,
        result_source=result_source,
    )
    combined_system_description = compose_system_context(
        run.system_description,
        run.attachment_context,
    )
    run.agent_states = build_agent_states("validate")
    run.usage_stats.update(attachment_usage)
    emit_progress(run, on_progress)

    run.agent_states["clarify"] = "running"
    emit_progress(run, on_progress)
    clarify_run = clarify_gaps(combined_system_description)
    run.results["clarify"] = clarify_run.content
    record_usage(run.usage_stats, "clarify", "Gap Clarification Agent", clarify_run)
    run.agent_states["clarify"] = "done"
    emit_progress(run, on_progress)

    run.agent_states["validate"] = "running"
    emit_progress(run, on_progress)
    validation_system_context = f"""## Source System Description
{combined_system_description}

## Gap Clarification Analysis
{run.results["clarify"]}
"""
    validation_run = validate_nfrs(validation_system_context, run.existing_nfrs)
    run.results["validate"] = validation_run.content
    record_usage(run.usage_stats, "validate", "NFR Validation Agent", validation_run)
    run.agent_states["validate"] = "done"
    emit_progress(run, on_progress)

    run.agent_states["remediate"] = "running"
    emit_progress(run, on_progress)
    remediation_run = remediate_nfrs(
        combined_system_description,
        run.existing_nfrs,
        run.results["validate"],
    )
    run.results["remediate"] = remediation_run.content
    record_usage(run.usage_stats, "remediate", "Remediation Agent", remediation_run)
    run.agent_states["remediate"] = "done"
    emit_progress(run, on_progress)

    run.agent_states["compliance"] = "running"
    emit_progress(run, on_progress)
    compliance_run = map_compliance(
        combined_system_description,
        run.existing_nfrs,
        run.results["validate"],
    )
    run.results["compliance"] = compliance_run.content
    record_usage(run.usage_stats, "compliance", "Compliance Mapping Agent", compliance_run)
    run.agent_states["compliance"] = "done"
    emit_progress(run, on_progress)

    return hydrate_pack(run)


async def run_generate_pipeline(
    *,
    system_description: str,
    project_name: str = "",
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
            attachment_context=run.attachment_context,
            result_source="refined",
        )

    return await run_validate_pipeline(
        system_description=refined_description,
        existing_nfrs=run.existing_nfrs,
        project_name=run.project_name,
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
