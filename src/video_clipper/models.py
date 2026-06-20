"""Modelos de datos centrales del pipeline.

Estos objetos se serializan a JSON como artefactos en el workdir, de modo que cada
etapa pueda re-ejecutarse de forma independiente leyendo el output de la anterior.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Layout(str, Enum):
    """Layout de reencuadre vertical."""

    STACKED = "A"          # slide arriba, webcam al medio, subtitulos abajo
    SCREEN_FOCUS = "B"     # pantalla protagonista, webcam chica en esquina


class ClipStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"


class RejectionReason(str, Enum):
    """Why a clip was rejected. Each value calibrates a rubric sub-score (M1 eval loop)."""

    BAD_HOOK = "bad_hook"                    # weak opening → hook_strength
    NOT_SELF_CONTAINED = "not_self_contained"  # needs the rest of the class → self_contained
    BAD_CUT = "bad_cut"                      # in/out poorly placed → payoff
    DIRTY_SCREEN = "dirty_screen"            # Meet UI / browser visible (pre-filtered)
    WEAK_TOPIC = "weak_topic"                # no clear takeaway → takeaway_clarity


class JobStage(str, Enum):
    """Etapa del pipeline para status.json (consumible por UI)."""

    QUEUED = "queued"
    INGESTING = "ingesting"
    TRANSCRIBING = "transcribing"
    SIGNALS = "signals"
    PROPOSING = "proposing"
    READY_FOR_REVIEW = "ready_for_review"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class Word(BaseModel):
    """Palabra transcripta con timestamps absolutos (segundos) respecto al crudo."""

    text: str
    start: float
    end: float
    speaker: str | None = None


class Segment(BaseModel):
    """Bloque de habla continuo (oración/frase) compuesto por palabras."""

    text: str
    start: float
    end: float
    speaker: str | None = None
    words: list[Word] = Field(default_factory=list)


class Transcript(BaseModel):
    """Transcripción completa del crudo."""

    language: str
    duration: float
    words: list[Word] = Field(default_factory=list)
    segments: list[Segment] = Field(default_factory=list)


class TimeRange(BaseModel):
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class Signals(BaseModel):
    """Señales locales extraídas del audio/video para guiar la selección."""

    silences: list[TimeRange] = Field(default_factory=list)
    scene_changes: list[float] = Field(default_factory=list)
    dirty_segments: list[TimeRange] = Field(default_factory=list)

    def is_dirty(self, t: float) -> bool:
        return any(r.start <= t <= r.end for r in self.dirty_segments)


class Caption(BaseModel):
    """Subtítulo por idioma (ruta al .ass generado)."""

    lang: str
    ass_path: str


class ClipCandidate(BaseModel):
    """Momento candidato a clip, con su estado de revisión y outputs."""

    id: str
    start: float
    end: float
    score: float = 0.0              # 0-100 (combined)
    # Rubric sub-scores (0-100), filled by the rank pass; default 0 for legacy/scan-only clips.
    hook_strength: float = 0.0
    self_contained: float = 0.0
    takeaway_clarity: float = 0.0
    payoff: float = 0.0
    rejection_reason: RejectionReason | None = None
    reason: str = ""
    title: str = ""
    hook: str = ""
    transcript: str = ""
    words: list[Word] = Field(default_factory=list)
    layout: Layout = Layout.STACKED
    status: ClipStatus = ClipStatus.PROPOSED
    captions: list[Caption] = Field(default_factory=list)
    outputs: dict[str, str] = Field(default_factory=dict)  # {"9x16": path, "16x9": path}

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class CandidateSet(BaseModel):
    """Colección de candidatos asociada a un crudo (artefacto candidates.json)."""

    source: str
    candidates: list[ClipCandidate] = Field(default_factory=list)


class GoldenRange(BaseModel):
    """A human-judged time range: approved (good clip) or rejected (with reason)."""

    start: float
    end: float
    approved: bool
    reason: RejectionReason | None = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class GoldenSet(BaseModel):
    """Human judgment per class, by time range (artifact labels.json).

    Persisted separately from candidates.json so re-running a stage never overwrites it.
    """

    source: str
    ranges: list[GoldenRange] = Field(default_factory=list)

    def approved(self) -> list[GoldenRange]:
        return [r for r in self.ranges if r.approved]

    def rejected(self) -> list[GoldenRange]:
        return [r for r in self.ranges if not r.approved]


class JobStatusRecord(BaseModel):
    """Estado del job de procesamiento (artefacto status.json)."""

    source: str
    stage: JobStage = JobStage.QUEUED
    progress: float = 0.0
    message: str = ""
    error: str | None = None
    started_at: str | None = None
    updated_at: str | None = None
    clip_count: int | None = None
