"""Esquemas Pydantic para la API REST."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ..models import ClipCandidate, ClipStatus, JobStage, JobStatusRecord, RejectionReason, Word


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
    rejection_reason: RejectionReason | None = None
    title: str | None = None
    layout: str | None = None
    words: list[Word] | None = None


class GoldenSummary(BaseModel):
    approved: int
    rejected: int
    total: int


class EvalReportResponse(BaseModel):
    n: int
    matched: int = 0
    precision_at_n: float = 0.0
    recall: float = 0.0
    false_positives_by_reason: dict[str, int] = Field(default_factory=dict)
    has_baseline: bool = False


class RenderPrefsResponse(BaseModel):
    caption_style: str
    caption_social_max_words: int
    output_vertical: bool
    output_horizontal: bool


class RenderPrefsPatch(BaseModel):
    caption_style: str | None = None
    caption_social_max_words: int | None = Field(default=None, ge=2, le=12)
    output_vertical: bool | None = None
    output_horizontal: bool | None = None


class CaptionStylePreview(BaseModel):
    style: str
    style_label: str
    font: str
    sample_lines: list[str] = Field(default_factory=list)


class CaptionPreviewResponse(BaseModel):
    clip_id: str | None = None
    clip_title: str | None = None
    previews: list[CaptionStylePreview] = Field(default_factory=list)
    message: str | None = None


class ProposePrefsResponse(BaseModel):
    target_clips: int
    min_duration: float
    max_duration: float
    rank_finalists: int


class ProposePrefsPatch(BaseModel):
    target_clips: int | None = Field(default=None, ge=1, le=50)
    min_duration: float | None = Field(default=None, ge=5.0, le=300.0)
    max_duration: float | None = Field(default=None, ge=10.0, le=600.0)
    rank_finalists: int | None = Field(default=None, ge=1, le=100)


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
