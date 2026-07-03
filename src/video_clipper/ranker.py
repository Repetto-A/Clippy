"""Pass 2 — rank + refine (M2).

Takes the scan's top finalists, sends their full transcripts together to the better-tier
model, scores them on the rubric in ONE comparable scale, sets the hook-first in/out points,
and combines the sub-scores into the final score. The router is injectable so this is tested
with a fake (no network in tests).
"""

from __future__ import annotations

import json
from copy import deepcopy

from rich.console import Console

from .clip_utils import clamp_range, transcript_text, words_in_range
from .config import settings
from .propose_prefs import ProposePrefs, default_propose_prefs
from .few_shot import build_rank_few_shot
from .models import ClipCandidate, GoldenSet, Signals, Transcript
from .router import get_router
from .rubric import combine_score

console = Console()

_MAX_RANK_ATTEMPTS = 2


def _clips_block(candidates: list[ClipCandidate], transcript: Transcript) -> str:
    lines = []
    for c in candidates:
        text = transcript_text(words_in_range(transcript, c.start, c.end))
        lines.append(f"clip {c.id} [{c.start:.1f}-{c.end:.1f}]: {text}")
    return "\n\n".join(lines)


def _run_rank_router(router, payload: dict) -> dict:
    """Call rank_moments with retry on parse/transport failures."""
    last_err: Exception | None = None
    for attempt in range(_MAX_RANK_ATTEMPTS):
        try:
            result = router.run("rank_moments", payload)
            if isinstance(result, dict) and isinstance(result.get("clips"), list):
                return result
            last_err = ValueError("respuesta rank sin lista clips")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as exc:
            last_err = exc
        if attempt + 1 < _MAX_RANK_ATTEMPTS:
            console.log(f"[yellow]Rank[/]: intento {attempt + 1} fallo, reintentando...")
    if last_err:
        console.log(f"[yellow]Rank[/]: sin respuesta valida ({last_err}), fallback scan")
    return {"clips": []}


def _apply_rank_row(c: ClipCandidate, row: dict, weights: tuple[float, float, float, float]) -> None:
    c.hook_strength = float(row.get("hook_strength", 0))
    c.self_contained = float(row.get("self_contained", 0))
    c.takeaway_clarity = float(row.get("takeaway_clarity", 0))
    c.payoff = float(row.get("payoff", 0))
    if "start" in row and "end" in row:
        c.start, c.end = float(row["start"]), float(row["end"])
    if row.get("title"):
        c.title = row["title"]
    if row.get("hook"):
        c.hook = row["hook"]
    if row.get("reason"):
        c.reason = row["reason"]
    c.score = combine_score(
        c.hook_strength, c.self_contained, c.takeaway_clarity, c.payoff, weights
    )


def rank(
    candidates: list[ClipCandidate],
    transcript: Transcript,
    signals: Signals,
    router=None,
    *,
    golden: GoldenSet | None = None,
    finalists: int | None = None,
    min_duration: float | None = None,
    max_duration: float | None = None,
    weights: tuple[float, float, float, float] | None = None,
) -> list[ClipCandidate]:
    """Score the scan finalists on the rubric and refine their boundaries (pass 2)."""
    if not candidates:
        return []

    router = router or get_router()
    prefs = default_propose_prefs()
    finalists = finalists if finalists is not None else prefs.rank_finalists
    min_d = min_duration if min_duration is not None else prefs.min_duration
    max_d = max_duration if max_duration is not None else prefs.max_duration
    weights = weights or (
        settings.w_hook,
        settings.w_self_contained,
        settings.w_takeaway,
        settings.w_payoff,
    )

    top = sorted(candidates, key=lambda c: c.score, reverse=True)[:finalists]
    by_id = {c.id: deepcopy(c) for c in top}

    payload = {
        "clips_block": _clips_block(top, transcript),
        "min_duration": min_d,
        "max_duration": max_d,
        "few_shot": build_rank_few_shot(golden, transcript) if golden else "",
    }
    result = _run_rank_router(router, payload)

    ranked: list[ClipCandidate] = []
    seen: set[str] = set()
    for row in result.get("clips", []):
        cid = row.get("id")
        base = by_id.get(cid)
        if base is None:
            continue
        c = deepcopy(base)
        _apply_rank_row(c, row, weights)
        c.start, c.end = clamp_range(c.start, c.end, transcript.duration)
        ranked.append(c)
        seen.add(c.id)

    for c in top:
        if c.id in seen:
            continue
        fallback = deepcopy(c)
        console.log(f"[yellow]Rank[/]: clip {c.id} sin respuesta LLM, conservando score scan")
        ranked.append(fallback)

    ranked.sort(key=lambda c: c.score, reverse=True)
    console.log(f"[cyan]Rank[/]: {len(ranked)} finalistas puntuados")
    return ranked
