"""Evaluation of pipeline output against the human golden set (M1).

Pure metric functions: how well a set of proposed clips matches what Ale approved/rejected,
by time-range overlap (IoU). This is the measurement loop that lets M2's new engine prove it
beats the current baseline instead of being judged by eye.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from .models import ClipCandidate, GoldenSet


def iou(a0: float, a1: float, b0: float, b1: float) -> float:
    """Intersection-over-union of two time ranges [a0,a1] and [b0,b1]."""
    inter = max(0.0, min(a1, b1) - max(a0, b0))
    union = (a1 - a0) + (b1 - b0) - inter
    return inter / union if union > 0 else 0.0


class EvalReport(BaseModel):
    """Metric of one pipeline run against a class's golden set (artifact eval_report.json)."""

    n: int                                                  # how many top clips were scored
    matched: int = 0                                        # top clips overlapping an approved range
    precision_at_n: float = 0.0                             # matched / n
    recall: float = 0.0                                     # approved ranges covered / total approved
    false_positives_by_reason: dict[str, int] = Field(default_factory=dict)


def evaluate(
    proposed: list[ClipCandidate],
    golden: GoldenSet,
    n: int,
    iou_threshold: float,
) -> EvalReport:
    """Score the top-N proposed clips (by score) against the golden set."""
    top = sorted(proposed, key=lambda c: c.score, reverse=True)[:n]
    approved = golden.approved()
    rejected = golden.rejected()

    matched = sum(
        1 for c in top
        if any(iou(c.start, c.end, r.start, r.end) >= iou_threshold for r in approved)
    )
    covered = sum(
        1 for r in approved
        if any(iou(c.start, c.end, r.start, r.end) >= iou_threshold for c in top)
    )

    fp: dict[str, int] = {}
    for c in top:
        for r in rejected:
            if r.reason and iou(c.start, c.end, r.start, r.end) >= iou_threshold:
                fp[r.reason.value] = fp.get(r.reason.value, 0) + 1

    return EvalReport(
        n=len(top),
        matched=matched,
        precision_at_n=matched / len(top) if top else 0.0,
        recall=covered / len(approved) if approved else 0.0,
        false_positives_by_reason=fp,
    )


def run_eval(workdir: Path, n: int, iou_threshold: float) -> EvalReport:
    """Load candidates + golden set from a workdir, compute the metric, persist the report."""
    from . import storage

    cset = storage.load_candidates(workdir)
    golden = storage.load_golden(workdir, source=cset.source)
    rep = evaluate(cset.candidates, golden, n=n, iou_threshold=iou_threshold)
    storage.save_eval_report(rep, workdir)
    return rep
