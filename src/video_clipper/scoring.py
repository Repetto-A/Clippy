"""Detección/scoring de momentos: propone clips candidatos a partir del transcript.

Dos implementaciones:
- HeuristicScorer: sin dependencias ni API. Permite correr el pipeline punta a punta
  para validar todo antes de tener keys. Calidad limitada (baseline).
- LLMScorer: usa el TaskRouter (Claude) para juicio editorial de calidad.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from rich.console import Console

from .clip_utils import clamp_range
from .config import settings
from .propose_prefs import ProposePrefs, default_propose_prefs
from .models import ClipCandidate, Segment, Signals, Transcript
from .router import get_router
from .transcript_chunks import chunk_segments, clips_target_for_chunk, lines_from_segments

console = Console()

# Palabras que suelen marcar momentos valiosos en contenido educativo.
_KEYWORDS = {
    "clave", "importante", "secreto", "truco", "error", "errores", "ejemplo",
    "consejo", "tip", "recordá", "ojo", "atención", "fundamental", "nunca",
    "siempre", "lo que pasa", "la idea", "en resumen", "entonces", "porque",
    "imaginá", "pensá", "mirá", "la diferencia", "el problema", "la solución",
}


class MomentScorer(Protocol):
    def propose(
        self,
        transcript: Transcript,
        signals: Signals,
        *,
        propose_prefs: ProposePrefs | None = None,
    ) -> list[ClipCandidate]: ...


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class HeuristicScorer:
    """Baseline sin API: ventanas de frases consecutivas puntuadas por features simples."""

    def propose(
        self,
        transcript: Transcript,
        signals: Signals,
        *,
        propose_prefs: ProposePrefs | None = None,
    ) -> list[ClipCandidate]:
        prefs = propose_prefs or default_propose_prefs()
        segs = transcript.segments
        candidates: list[ClipCandidate] = []

        for i in range(len(segs)):
            acc: list[Segment] = []
            for j in range(i, len(segs)):
                acc.append(segs[j])
                dur = acc[-1].end - acc[0].start
                if dur < prefs.min_duration:
                    continue
                if dur > prefs.max_duration:
                    break
                start, end = acc[0].start, acc[-1].end
                text = " ".join(s.text for s in acc)
                score = self._score_window(text, start, end, signals)
                candidates.append(
                    ClipCandidate(
                        id=_new_id(),
                        start=start,
                        end=end,
                        score=score,
                        reason="Heurística: densidad de keywords y duración objetivo",
                        title=acc[0].text[:60],
                        hook=acc[0].text[:80],
                        transcript=text,
                    )
                )
                break  # una ventana por punto de inicio

        candidates.sort(key=lambda c: c.score, reverse=True)
        console.log(f"[green]Heurístico[/]: {len(candidates)} ventanas candidatas")
        return candidates

    def _score_window(self, text: str, start: float, end: float, signals: Signals) -> float:
        low = text.lower()
        kw = sum(1 for k in _KEYWORDS if k in low)
        words = max(1, len(text.split()))
        wps = words / max(1.0, end - start)

        score = 30.0
        score += min(40.0, kw * 8.0)
        score += min(15.0, (wps - 1.5) * 10.0)  # premia ritmo de habla
        if "?" in text:
            score += 5.0
        mid = (start + end) / 2
        if signals.is_dirty(mid):
            score -= 30.0
        return max(0.0, min(100.0, score))


class LLMScorer:
    """Scorer de calidad vía TaskRouter, con chunking automático en transcripts largos."""

    def __init__(self) -> None:
        self.router = get_router()

    def propose(
        self,
        transcript: Transcript,
        signals: Signals,
        *,
        propose_prefs: ProposePrefs | None = None,
    ) -> list[ClipCandidate]:
        prefs = propose_prefs or default_propose_prefs()
        chunks = chunk_segments(
            transcript.segments,
            settings.llm_chunk_chars,
            silences=signals.silences,
            overlap_segments=settings.chunk_overlap_segments,
        )
        if len(chunks) <= 1:
            console.log("[cyan]LLM[/]: pidiendo momentos al modelo...")
            raw = self._score_chunk(chunks[0], transcript, signals, prefs.target_clips, prefs)
        else:
            console.log(
                f"[cyan]LLM[/]: transcript largo -> {len(chunks)} chunks "
                f"(~{settings.llm_chunk_chars} chars c/u)"
            )
            raw: list[ClipCandidate] = []
            for i, chunk in enumerate(chunks):
                n = clips_target_for_chunk(
                    i, len(chunks), prefs.target_clips, settings.llm_clips_per_chunk,
                )
                t0 = chunk[0].start if chunk else 0
                t1 = chunk[-1].end if chunk else 0
                console.log(f"  chunk {i + 1}/{len(chunks)} ({t0 / 60:.0f}-{t1 / 60:.0f} min, hasta {n} clips)")
                raw.extend(self._score_chunk(chunk, transcript, signals, n, prefs))

        raw.sort(key=lambda x: x.score, reverse=True)
        console.log(f"[green]LLM[/]: {len(raw)} momentos propuestos (pre-selección)")
        return raw

    def _score_chunk(
        self,
        segments: list[Segment],
        transcript: Transcript,
        signals: Signals,
        target: int,
        prefs: ProposePrefs,
    ) -> list[ClipCandidate]:
        result = self.router.run(
            "score_moments",
            {
                "transcript_lines": lines_from_segments(segments),
                "min_duration": prefs.min_duration,
                "max_duration": prefs.max_duration,
                "target_clips": target,
                "dirty_ranges": [(r.start, r.end) for r in signals.dirty_segments],
            },
        )
        out: list[ClipCandidate] = []
        for c in result.get("clips", []):
            start, end = float(c["start"]), float(c["end"])
            start, end = clamp_range(start, end, transcript.duration)
            mid = (start + end) / 2
            score = float(c.get("score", 50))
            if signals.is_dirty(mid):
                score -= 30.0
            out.append(
                ClipCandidate(
                    id=_new_id(),
                    start=start,
                    end=end,
                    score=max(0.0, score),
                    reason=c.get("reason", ""),
                    title=c.get("title", ""),
                    hook=c.get("hook", ""),
                )
            )
        return out


def get_scorer() -> MomentScorer:
    if settings.scorer == "heuristic":
        return HeuristicScorer()
    return LLMScorer()
