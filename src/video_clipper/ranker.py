"""Pass 2 — rank + refine (M2).

Takes the scan's top finalists, sends their full transcripts together to the better-tier
model, scores them on the rubric in ONE comparable scale, sets the hook-first in/out points,
and combines the sub-scores into the final score. The router is injectable so this is tested
with a fake (no network in tests).
"""

from __future__ import annotations

from rich.console import Console

from .clip_utils import transcript_text, words_in_range
from .config import settings
from .models import ClipCandidate, Signals, Transcript
from .router import get_router
from .rubric import combine_score

console = Console()


def _clips_block(candidates: list[ClipCandidate], transcript: Transcript) -> str:
    lines = []
    for c in candidates:
        text = transcript_text(words_in_range(transcript, c.start, c.end))
        lines.append(f"clip {c.id} [{c.start:.1f}-{c.end:.1f}]: {text}")
    return "\n\n".join(lines)


def rank(
    candidates: list[ClipCandidate],
    transcript: Transcript,
    signals: Signals,
    router=None,
    *,
    finalists: int | None = None,
    weights: tuple[float, float, float, float] | None = None,
) -> list[ClipCandidate]:
    """Score the scan finalists on the rubric and refine their boundaries (pass 2)."""
    if not candidates:
        return []

    router = router or get_router()
    finalists = finalists or settings.rank_finalists
    weights = weights or (
        settings.w_hook,
        settings.w_self_contained,
        settings.w_takeaway,
        settings.w_payoff,
    )

    top = sorted(candidates, key=lambda c: c.score, reverse=True)[:finalists]
    by_id = {c.id: c for c in top}

    result = router.run(
        "rank_moments",
        {
            "clips_block": _clips_block(top, transcript),
            "min_duration": settings.min_duration,
            "max_duration": settings.max_duration,
        },
    )

    ranked: list[ClipCandidate] = []
    for r in result.get("clips", []):
        c = by_id.get(r.get("id"))
        if c is None:
            continue
        c.hook_strength = float(r.get("hook_strength", 0))
        c.self_contained = float(r.get("self_contained", 0))
        c.takeaway_clarity = float(r.get("takeaway_clarity", 0))
        c.payoff = float(r.get("payoff", 0))
        if "start" in r and "end" in r:
            c.start, c.end = float(r["start"]), float(r["end"])
        if r.get("title"):
            c.title = r["title"]
        if r.get("hook"):
            c.hook = r["hook"]
        if r.get("reason"):
            c.reason = r["reason"]
        c.score = combine_score(
            c.hook_strength, c.self_contained, c.takeaway_clarity, c.payoff, weights
        )
        ranked.append(c)

    ranked.sort(key=lambda c: c.score, reverse=True)
    console.log(f"[cyan]Rank[/]: {len(ranked)} finalistas puntuados")
    return ranked
