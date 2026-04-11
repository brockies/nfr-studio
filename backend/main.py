"""FastAPI app that exposes the NFR Studio workflow to a React frontend."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .jobs import complete_job, create_job, fail_job, get_job, update_job
from .models import (
    FollowUpRequest,
    FollowUpResponse,
    RedactionPreview,
    RedactionRequest,
    RefineRunRequest,
    RunJobStatus,
    RunPayload,
    SaveRunRequest,
    SaveRunResponse,
    SavedRunDetail,
    SavedRunSummary,
)
from .pipeline import (
    answer_follow_up,
    buffer_uploads,
    build_agent_states,
    build_redaction_preview,
    new_run,
    refine_run,
    run_generate_pipeline,
    run_generate_pipeline_sync,
    run_validate_pipeline,
    run_validate_pipeline_sync,
)
from .storage import list_saved_runs, load_saved_run, save_run_file
from utils.redaction import redact_text
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

from utils.rag_manager import ingest_knowledge_base, kb_status


app = FastAPI(
    title="NFR Studio API",
    version="0.1.0",
    summary="Backend for the React migration of NFR Studio.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    """Simple readiness endpoint for local development."""

    return {"status": "ok"}


@app.get("/api/kb/status")
def knowledge_base_status() -> dict[str, object]:
    """Return basic knowledge base and vector index status."""

    return kb_status()


@app.post("/api/kb/ingest")
def ingest_knowledge_base_now() -> dict[str, object]:
    """(Re)ingest the knowledge base into the local ChromaDB store."""

    return ingest_knowledge_base()


@app.post("/api/kb/upload")
async def upload_knowledge_base_project(
    project_file: UploadFile = File(...),
    target: str = Form("projects"),
) -> dict[str, object]:
    """Upload a markdown knowledge base file and re-ingest.

    `target` should be "projects" or "compliance".
    """

    if not project_file.filename or not project_file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Please upload a .md file.")

    safe_target = "projects" if target not in {"projects", "compliance"} else target
    dest_dir = Path("knowledge_base") / safe_target
    dest_dir.mkdir(parents=True, exist_ok=True)

    payload = await project_file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file was empty.")

    dest_path = dest_dir / Path(project_file.filename).name
    dest_path.write_bytes(payload)

    return ingest_knowledge_base()


async def _run_generate_job(
    job_id: str,
    *,
    system_description: str,
    project_name: str,
    attachments,
) -> None:
    """Execute a generate job in the background and publish progress."""

    try:
        result = await asyncio.to_thread(
            run_generate_pipeline_sync,
            system_description=system_description,
            project_name=project_name,
            attachments=attachments,
            on_progress=lambda run: update_job(job_id, run),
        )
        complete_job(job_id, result)
    except Exception as exc:  # pragma: no cover
        fail_job(job_id, str(exc))


async def _run_validate_job(
    job_id: str,
    *,
    system_description: str,
    existing_nfrs: str,
    project_name: str,
    attachments,
) -> None:
    """Execute a validate job in the background and publish progress."""

    try:
        result = await asyncio.to_thread(
            run_validate_pipeline_sync,
            system_description=system_description,
            existing_nfrs=existing_nfrs,
            project_name=project_name,
            attachments=attachments,
            on_progress=lambda run: update_job(job_id, run),
        )
        complete_job(job_id, result)
    except Exception as exc:  # pragma: no cover
        fail_job(job_id, str(exc))


@app.post("/api/redact", response_model=RedactionPreview)
def preview_redaction(request: RedactionRequest) -> RedactionPreview:
    """Return deterministic masking details for an input preview."""

    return build_redaction_preview(request.text)


@app.post("/api/generate/start", response_model=RunJobStatus)
async def start_generate_run(
    system_description: str = Form(...),
    project_name: str = Form(""),
    attachments: list[UploadFile] | None = File(default=None),
) -> RunJobStatus:
    """Queue a generate workflow and return a pollable job id."""

    if not system_description.strip():
        raise HTTPException(status_code=400, detail="System description is required.")

    try:
        processed_system_description = redact_text(system_description.strip()).redacted_text
        buffered_attachments = await buffer_uploads(attachments or [])
        initial_run = new_run(
            mode="generate",
            system_description=processed_system_description,
            project_name=project_name.strip(),
        )
        initial_run.agent_states = build_agent_states("generate")
        job = create_job("generate", initial_run)
        asyncio.create_task(
            _run_generate_job(
                job.job_id,
                system_description=processed_system_description,
                project_name=project_name.strip(),
                attachments=buffered_attachments,
            )
        )
        return job
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/validate/start", response_model=RunJobStatus)
async def start_validate_run(
    system_description: str = Form(...),
    existing_nfrs: str = Form(...),
    project_name: str = Form(""),
    attachments: list[UploadFile] | None = File(default=None),
) -> RunJobStatus:
    """Queue a validation workflow and return a pollable job id."""

    if not system_description.strip() or not existing_nfrs.strip():
        raise HTTPException(
            status_code=400,
            detail="System description and existing NFRs are both required.",
        )

    try:
        processed_system_description = redact_text(system_description.strip()).redacted_text
        processed_existing_nfrs = redact_text(existing_nfrs.strip()).redacted_text
        buffered_attachments = await buffer_uploads(attachments or [])
        initial_run = new_run(
            mode="validate",
            system_description=processed_system_description,
            existing_nfrs=processed_existing_nfrs,
            project_name=project_name.strip(),
        )
        initial_run.agent_states = build_agent_states("validate")
        job = create_job("validate", initial_run)
        asyncio.create_task(
            _run_validate_job(
                job.job_id,
                system_description=processed_system_description,
                existing_nfrs=processed_existing_nfrs,
                project_name=project_name.strip(),
                attachments=buffered_attachments,
            )
        )
        return job
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/jobs/{job_id}", response_model=RunJobStatus)
def get_run_job(job_id: str) -> RunJobStatus:
    """Return the latest known state for a background run."""

    try:
        return get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run job was not found.") from exc


@app.post("/api/generate", response_model=RunPayload)
async def generate_run(
    system_description: str = Form(...),
    project_name: str = Form(""),
    attachments: list[UploadFile] | None = File(default=None),
):
    """Run the full generate workflow."""

    if not system_description.strip():
        raise HTTPException(status_code=400, detail="System description is required.")

    try:
        processed_system_description = redact_text(system_description.strip()).redacted_text
        return await run_generate_pipeline(
            system_description=processed_system_description,
            project_name=project_name.strip(),
            attachments=attachments or [],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/validate", response_model=RunPayload)
async def validate_run(
    system_description: str = Form(...),
    existing_nfrs: str = Form(...),
    project_name: str = Form(""),
    attachments: list[UploadFile] | None = File(default=None),
):
    """Run the validate workflow."""

    if not system_description.strip() or not existing_nfrs.strip():
        raise HTTPException(
            status_code=400,
            detail="System description and existing NFRs are both required.",
        )

    try:
        processed_system_description = redact_text(system_description.strip()).redacted_text
        processed_existing_nfrs = redact_text(existing_nfrs.strip()).redacted_text
        return await run_validate_pipeline(
            system_description=processed_system_description,
            existing_nfrs=processed_existing_nfrs,
            project_name=project_name.strip(),
            attachments=attachments or [],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/refine", response_model=RunPayload)
async def refine_existing_run(request: RefineRunRequest) -> RunPayload:
    """Rerun the existing workflow with additional context."""

    if not request.additional_context.strip():
        raise HTTPException(status_code=400, detail="Additional context is required.")

    if request.run.mode == "validate" and not request.run.existing_nfrs.strip():
        raise HTTPException(
            status_code=400,
            detail="This validation run does not include the original NFR input, so it cannot be refined automatically.",
        )

    try:
        return await refine_run(request.run, request.additional_context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/follow-up", response_model=FollowUpResponse)
def ask_follow_up(request: FollowUpRequest) -> FollowUpResponse:
    """Answer a grounded follow-up question for the current run."""

    try:
        answer, usage = answer_follow_up(
            run=request.run,
            question=request.question.strip(),
            history=request.history,
        )
        return FollowUpResponse(answer=answer, usage=usage)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/saved-runs", response_model=list[SavedRunSummary])
def saved_runs() -> list[SavedRunSummary]:
    """List saved run metadata."""

    return list_saved_runs()


@app.get("/api/saved-runs/{filename}", response_model=SavedRunDetail)
def get_saved_run(filename: str) -> SavedRunDetail:
    """Load a single saved run."""

    try:
        path, run = load_saved_run(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SavedRunDetail(
        file_name=path.name,
        modified=datetime.fromtimestamp(path.stat().st_mtime).strftime("%d %b %Y %H:%M"),
        run=run,
    )


@app.post("/api/saved-runs", response_model=SaveRunResponse)
def save_run(request: SaveRunRequest) -> SaveRunResponse:
    """Persist the supplied run to the local saved-runs directory."""

    try:
        path = save_run_file(request.filename, request.run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SaveRunResponse(
        file_name=path.name,
        modified=datetime.fromtimestamp(path.stat().st_mtime).strftime("%d %b %Y %H:%M"),
    )
