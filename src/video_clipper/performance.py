"""Metricas de plataforma por clip publicado e import manual (ADR-0005)."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from pydantic import BaseModel, Field

from . import storage


class ClipPerformance(BaseModel):
    clip_id: str
    platform: str = "youtube"
    views: int = Field(default=0, ge=0)
    retention_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    saves: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    published_at: str | None = None


class PerformanceSet(BaseModel):
    records: list[ClipPerformance] = Field(default_factory=list)


class RubricCorrelation(BaseModel):
    sub_score: str
    metric: str
    sample_size: int
    correlation: float | None = None
    avg_high: float | None = None
    avg_low: float | None = None


class WeightSuggestion(BaseModel):
    sub_score: str
    current: float
    suggested: float
    reason: str


class PerformanceReport(BaseModel):
    sample_size: int = 0
    correlations: list[RubricCorrelation] = Field(default_factory=list)
    suggestions: list[WeightSuggestion] = Field(default_factory=list)
    message: str | None = None


_RUBRIC_FIELDS = (
    ("hook_strength", "Hook"),
    ("self_contained", "Autocontenido"),
    ("takeaway_clarity", "Takeaway"),
    ("payoff", "Remate"),
)


def _metric_value(rec: ClipPerformance) -> float | None:
    if rec.retention_pct is not None:
        return rec.retention_pct
    if rec.views > 0:
        return float(rec.views)
    if rec.saves > 0:
        return float(rec.saves)
    return None


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs) ** 0.5
    den_y = sum((y - my) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def parse_performance_json(raw: str) -> PerformanceSet:
    data = json.loads(raw)
    if isinstance(data, list):
        return PerformanceSet(records=[ClipPerformance.model_validate(row) for row in data])
    return PerformanceSet.model_validate(data)


def parse_performance_csv(raw: str) -> PerformanceSet:
    reader = csv.DictReader(io.StringIO(raw))
    records: list[ClipPerformance] = []
    for row in reader:
        if not row.get("clip_id"):
            continue
        records.append(
            ClipPerformance(
                clip_id=row["clip_id"].strip(),
                platform=(row.get("platform") or "youtube").strip(),
                views=int(row.get("views") or 0),
                retention_pct=float(row["retention_pct"]) if row.get("retention_pct") else None,
                saves=int(row.get("saves") or 0),
                shares=int(row.get("shares") or 0),
                published_at=row.get("published_at") or None,
            )
        )
    return PerformanceSet(records=records)


def merge_performance(existing: PerformanceSet, incoming: PerformanceSet) -> PerformanceSet:
    by_id = {r.clip_id: r for r in existing.records}
    for rec in incoming.records:
        by_id[rec.clip_id] = rec
    return PerformanceSet(records=list(by_id.values()))


def build_performance_report(workdir: Path) -> PerformanceReport:
    perf = storage.load_performance(workdir)
    if not perf.records:
        return PerformanceReport(message="Sin metricas importadas todavia.")

    if not (workdir / "candidates.json").exists():
        return PerformanceReport(message="Faltan candidatos para correlacionar.")

    cset = storage.load_candidates(workdir)
    by_id = {c.id: c for c in cset.candidates}
    pairs: list[tuple] = []
    for rec in perf.records:
        clip = by_id.get(rec.clip_id)
        metric = _metric_value(rec)
        if clip is None or metric is None:
            continue
        pairs.append((clip, rec, metric))

    if not pairs:
        return PerformanceReport(
            sample_size=0,
            message="No hay overlap entre clip_id importados y candidatos con metrica util.",
        )

    correlations: list[RubricCorrelation] = []
    suggestions: list[WeightSuggestion] = []
    metric_name = "retention_pct" if any(p[1].retention_pct is not None for p in pairs) else "views"

    for field, label in _RUBRIC_FIELDS:
        xs = [getattr(p[0], field) for p in pairs]
        ys = [p[2] for p in pairs]
        corr = _pearson(xs, ys)
        high = [y for x, y in zip(xs, ys) if x >= 70]
        low = [y for x, y in zip(xs, ys) if x < 50]
        correlations.append(
            RubricCorrelation(
                sub_score=field,
                metric=metric_name,
                sample_size=len(pairs),
                correlation=corr,
                avg_high=sum(high) / len(high) if high else None,
                avg_low=sum(low) / len(low) if low else None,
            )
        )
        if corr is not None and corr > 0.15 and high and low:
            avg_high = sum(high) / len(high)
            avg_low = sum(low) / len(low)
            if avg_high > avg_low:
                suggestions.append(
                    WeightSuggestion(
                        sub_score=field,
                        current=0.25,
                        suggested=min(0.4, 0.25 + corr * 0.1),
                        reason=f"{label} correlaciona positivamente con {metric_name} (r={corr:.2f}).",
                    )
                )

    return PerformanceReport(
        sample_size=len(pairs),
        correlations=correlations,
        suggestions=suggestions,
        message=None,
    )
