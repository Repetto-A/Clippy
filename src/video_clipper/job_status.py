"""Estado persistente del job por video (status.json en el workdir)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .models import JobStage, JobStatusRecord
from . import storage


def _now() -> str:
    return datetime.now(UTC).isoformat()


def init(workdir: Path, source: Path) -> JobStatusRecord:
    rec = JobStatusRecord(
        source=str(source.resolve()),
        stage=JobStage.QUEUED,
        progress=0.0,
        message="En cola",
        started_at=_now(),
        updated_at=_now(),
    )
    storage.save_job_status(rec, workdir)
    return rec


def load(workdir: Path) -> JobStatusRecord | None:
    return storage.load_job_status(workdir)


def set_status(
    workdir: Path,
    *,
    stage: JobStage | None = None,
    progress: float | None = None,
    message: str | None = None,
    clip_count: int | None = None,
    error: str | None = None,
) -> JobStatusRecord:
    rec = storage.load_job_status(workdir)
    if rec is None:
        rec = JobStatusRecord(source=str(workdir), stage=JobStage.QUEUED, started_at=_now())

    if stage is not None:
        rec.stage = stage
    if progress is not None:
        rec.progress = max(0.0, min(100.0, progress))
    if message is not None:
        rec.message = message
    if clip_count is not None:
        rec.clip_count = clip_count
    if error is not None:
        rec.error = error
    rec.updated_at = _now()
    storage.save_job_status(rec, workdir)
    return rec


def fail(workdir: Path, error: str) -> JobStatusRecord:
    return set_status(
        workdir,
        stage=JobStage.FAILED,
        progress=0.0,
        message="Error en el procesamiento",
        error=error,
    )
