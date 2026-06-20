"""Esquemas Pydantic para la API REST."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ..models import ClipCandidate, ClipStatus, JobStage, JobStatusRecord, Word


class JobSummary(BaseModel):
    id: str
    name: str
    stage: JobStage
    progress: float
    message: str
    clip_count: int | None = None
    error: str | None = None
    updated_at: str | None = None


class JobDetail(JobSummary):
    source: str
    duration: float | None = None
    started_at: str | None = None


class CandidateSetResponse(BaseModel):
    source: str
    candidates: list[ClipCandidate]


class ClipPatch(BaseModel):
    start: float | None = None
    end: float | None = None
    status: ClipStatus | None = None
    title: str | None = None
    layout: str | None = None
    words: list[Word] | None = None


class WordPatch(BaseModel):
    text: str


class ProcessPathRequest(BaseModel):
    path: str = Field(description="Ruta absoluta al .mp4 en disco local")


class MessageResponse(BaseModel):
    ok: bool = True
    message: str = ""


def job_summary(job_id: str, rec: JobStatusRecord) -> JobSummary:
    name = Path(rec.source).name if rec.source else job_id
    return JobSummary(
        id=job_id,
        name=name,
        stage=rec.stage,
        progress=rec.progress,
        message=rec.message,
        clip_count=rec.clip_count,
        error=rec.error,
        updated_at=rec.updated_at,
    )
