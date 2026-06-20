"""Rubric: combine the four moment-quality sub-scores into a single 0-100 score.

Pure and weight-driven so the weights can be tuned (config) without re-prompting the model.
"""

from __future__ import annotations

DEFAULT_WEIGHTS = (0.25, 0.25, 0.25, 0.25)  # hook, self_contained, takeaway, payoff


def combine_score(
    hook_strength: float,
    self_contained: float,
    takeaway_clarity: float,
    payoff: float,
    weights: tuple[float, float, float, float] = DEFAULT_WEIGHTS,
) -> float:
    """Weighted combination of the rubric sub-scores, clamped to 0-100."""
    wh, ws, wt, wp = weights
    total = hook_strength * wh + self_contained * ws + takeaway_clarity * wt + payoff * wp
    return max(0.0, min(100.0, total))
