"""In-memory job registry for background pipeline progress."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from uuid import uuid4

from .models import Mode, RunJobStatus, RunPayload


@dataclass
class JobRecord:
    """Internal mutable record for one background run."""

    mode: Mode
    status: str
    run: RunPayload | None = None
    error: str = ""


_jobs: dict[str, JobRecord] = {}
_jobs_lock = Lock()


def create_job(mode: Mode, run: RunPayload) -> RunJobStatus:
    """Register a queued job and return its initial public snapshot."""

    job_id = uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = JobRecord(
            mode=mode,
            status="queued",
            run=run.model_copy(deep=True),
        )
    return get_job(job_id)


def update_job(job_id: str, run: RunPayload, status: str = "running") -> None:
    """Persist the latest in-flight run snapshot for a job."""

    with _jobs_lock:
        record = _jobs[job_id]
        record.status = status
        record.run = run.model_copy(deep=True)
        record.error = ""


def complete_job(job_id: str, run: RunPayload) -> None:
    """Mark a job as completed with the final run payload."""

    update_job(job_id, run, status="completed")


def fail_job(job_id: str, error: str) -> None:
    """Mark a job as failed while preserving the latest partial run snapshot."""

    with _jobs_lock:
        record = _jobs[job_id]
        record.status = "failed"
        record.error = error


def get_job(job_id: str) -> RunJobStatus:
    """Return the current public snapshot for a job."""

    with _jobs_lock:
        record = _jobs[job_id]
        run = record.run.model_copy(deep=True) if record.run else None
        return RunJobStatus(
            job_id=job_id,
            mode=record.mode,
            status=record.status,
            run=run,
            error=record.error,
        )
