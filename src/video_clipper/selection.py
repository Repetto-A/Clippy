"""Refinamiento de candidatos: snap de cortes, duración, dedupe y layout A/B."""

from __future__ import annotations

from rich.console import Console

from .clip_utils import clamp_range, sync_clip_words, transcript_text, words_in_range
from .config import settings
from .models import ClipCandidate, Layout, Signals, Transcript

console = Console()

# Señales de que el momento es visual (slide protagonista) -> Layout B.
_VISUAL_CUES = {
    "acá ven", "aca ven", "en pantalla", "este gráfico", "este grafico",
    "esta slide", "miren", "vean", "como ven", "el cuadro", "la tabla",
    "este diagrama", "fíjense", "fijense", "acá arriba", "aca arriba",
}


def _snap(t: float, boundaries: list[float], window: float) -> float:
    """Acerca t al boundary más cercano si está dentro de la ventana."""
    if not boundaries:
        return t
    nearest = min(boundaries, key=lambda b: abs(b - t))
    return nearest if abs(nearest - t) <= window else t


def _fill_text(c: ClipCandidate, transcript: Transcript) -> str:
    return transcript_text(words_in_range(transcript, c.start, c.end)) or c.transcript


def _pick_layout(text: str) -> Layout:
    low = text.lower()
    return Layout.SCREEN_FOCUS if any(cue in low for cue in _VISUAL_CUES) else Layout.STACKED


def _overlaps(a: ClipCandidate, b: ClipCandidate, max_ratio: float = 0.3) -> bool:
    inter = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    shorter = min(a.duration, b.duration) or 1.0
    return (inter / shorter) > max_ratio


def refine(
    candidates: list[ClipCandidate],
    transcript: Transcript,
    signals: Signals,
) -> list[ClipCandidate]:
    silence_starts = [s.start for s in signals.silences]

    refined: list[ClipCandidate] = []
    for c in candidates:
        # Hook-first: keep the in-point pinned (the ranker chose it on the hook); only the
        # out-point snaps to a nearby silence so the clip breathes at the close.
        start = c.start
        end = _snap(c.end, silence_starts, window=1.5)
        if end - start < settings.min_duration:
            end = start + settings.min_duration
        if end - start > settings.max_duration:
            end = start + settings.max_duration

        start, end = clamp_range(start, end, transcript.duration)

        # Descartar si el grueso del clip cae en tramo sucio
        mid = (start + end) / 2
        if signals.is_dirty(mid):
            continue

        c.start, c.end = start, end
        sync_clip_words(c, transcript)
        if not c.title:
            c.title = c.transcript[:60]
        c.layout = _pick_layout(c.transcript)
        refined.append(c)

    # Dedupe greedy por score, sin solapamientos fuertes
    refined.sort(key=lambda x: x.score, reverse=True)
    selected: list[ClipCandidate] = []
    for c in refined:
        if all(not _overlaps(c, s) for s in selected):
            selected.append(c)
        if len(selected) >= settings.target_clips:
            break

    selected.sort(key=lambda x: x.start)
    console.log(f"[green]Selección[/]: {len(selected)} clips finales (de {len(candidates)} candidatos)")
    return selected
