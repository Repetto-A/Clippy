"""Timeline semantico del job completo (heatmap + capas) para la UI (ADR-0006)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from . import storage


class TimelineRange(BaseModel):
    start: float
    end: float


class TimelineBucket(BaseModel):
    start: float
    end: float
    intensity: float = Field(ge=0.0, le=1.0)


class TimelineClip(BaseModel):
    id: str
    start: float
    end: float
    score: float
    title: str = ""
    status: str = "proposed"
    hook: str = ""


class JobTimeline(BaseModel):
    duration: float
    bucket_count: int
    buckets: list[TimelineBucket] = Field(default_factory=list)
    clips: list[TimelineClip] = Field(default_factory=list)
    silences: list[TimelineRange] = Field(default_factory=list)
    dirty: list[TimelineRange] = Field(default_factory=list)


def _duration(workdir: Path) -> float:
    transcript_path = workdir / "transcript.json"
    if transcript_path.exists():
        return storage.load_transcript(workdir).duration
    dur_file = workdir / "duration.txt"
    if dur_file.exists():
        return float(dur_file.read_text(encoding="utf-8"))
    return 0.0


def _build_buckets(duration: float, bucket_count: int, scores: list[tuple[float, float, float]]) -> list[TimelineBucket]:
    if duration <= 0 or bucket_count <= 0:
        return []
    width = duration / bucket_count
    values = [0.0] * bucket_count
    for start, end, score in scores:
        if score <= 0:
            continue
        lo = max(0, int(start / width))
        hi = min(bucket_count - 1, int(end / width))
        for i in range(lo, hi + 1):
            b_start = i * width
            b_end = min(duration, (i + 1) * width)
            overlap = max(0.0, min(end, b_end) - max(start, b_start))
            span = max(0.001, end - start)
            values[i] = max(values[i], (score / 100.0) * (overlap / span))
    peak = max(values) if values else 0.0
    if peak <= 0:
        norm = values
    else:
        norm = [v / peak for v in values]
    return [
        TimelineBucket(start=i * width, end=min(duration, (i + 1) * width), intensity=norm[i])
        for i in range(bucket_count)
    ]


def build_job_timeline(workdir: Path, *, bucket_count: int = 200) -> JobTimeline:
    duration = _duration(workdir)
    silences: list[TimelineRange] = []
    dirty: list[TimelineRange] = []
    if (workdir / "signals.json").exists():
        signals = storage.load_signals(workdir)
        silences = [TimelineRange(start=r.start, end=r.end) for r in signals.silences]
        dirty = [TimelineRange(start=r.start, end=r.end) for r in signals.dirty_segments]

    score_ranges: list[tuple[float, float, float]] = []
    clips: list[TimelineClip] = []
    if (workdir / "candidates.json").exists():
        cset = storage.load_candidates(workdir)
        for c in cset.candidates:
            score_ranges.append((c.start, c.end, c.score))
            clips.append(
                TimelineClip(
                    id=c.id,
                    start=c.start,
                    end=c.end,
                    score=c.score,
                    title=c.title,
                    status=c.status.value if hasattr(c.status, "value") else str(c.status),
                    hook=c.hook or (c.transcript[:120] if c.transcript else ""),
                )
            )

    buckets = _build_buckets(duration, bucket_count, score_ranges)
    return JobTimeline(
        duration=duration,
        bucket_count=bucket_count,
        buckets=buckets,
        clips=clips,
        silences=silences,
        dirty=dirty,
    )
