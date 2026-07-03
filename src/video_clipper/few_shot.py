"""Few-shot examples for the rank prompt, built from the human golden set."""

from __future__ import annotations

from .clip_utils import transcript_text, words_in_range
from .models import GoldenRange, GoldenSet, Transcript


def _snippet(transcript: Transcript, r: GoldenRange, max_chars: int) -> str:
    text = transcript_text(words_in_range(transcript, r.start, r.end)) or "..."
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


def build_rank_few_shot(
    golden: GoldenSet,
    transcript: Transcript,
    *,
    max_good: int = 2,
    max_bad: int = 2,
    snippet_chars: int = 280,
) -> str:
    """Format approved/rejected ranges as editorial examples for the rank LLM."""
    if not golden.ranges:
        return ""

    lines = [
        "Ejemplos de juicio humano previo sobre esta clase (usá como guía de calidad):",
    ]
    for r in golden.approved()[:max_good]:
        lines.append(
            f"- BUENO [{r.start:.1f}-{r.end:.1f}]: {_snippet(transcript, r, snippet_chars)}"
        )
    for r in golden.rejected()[:max_bad]:
        reason = r.reason.value if r.reason else "rechazado"
        lines.append(
            f"- MALO ({reason}) [{r.start:.1f}-{r.end:.1f}]: "
            f"{_snippet(transcript, r, snippet_chars)}"
        )
    return "\n".join(lines)
