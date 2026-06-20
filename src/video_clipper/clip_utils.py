"""Utilidades compartidas para rangos de clip y sincronización de palabras."""

from __future__ import annotations

from .config import settings
from .models import ClipCandidate, Transcript, Word


def clamp_range(
    start: float,
    end: float,
    duration: float,
    *,
    min_duration: float | None = None,
    max_duration: float | None = None,
) -> tuple[float, float]:
    """Acota [start, end] al crudo y respeta duración mínima/máxima de clip."""
    min_d = settings.min_duration if min_duration is None else min_duration
    max_d = settings.max_duration if max_duration is None else max_duration
    duration = max(0.0, duration)

    start = max(0.0, min(start, duration))
    end = max(0.0, min(end, duration))
    if end < start:
        start, end = end, start

    if end - start < min_d:
        end = min(duration, start + min_d)
        if end - start < min_d:
            start = max(0.0, end - min_d)

    if end - start > max_d:
        end = start + max_d
        end = min(end, duration)

    return round(start, 2), round(end, 2)


def words_in_range(transcript: Transcript, start: float, end: float) -> list[Word]:
    """Palabras del transcript dentro del rango [start, end] (copias independientes)."""
    return [
        Word(text=w.text, start=w.start, end=w.end, speaker=w.speaker)
        for w in transcript.words
        if start <= w.start <= end
    ]


def transcript_text(words: list[Word]) -> str:
    return " ".join(w.text for w in words).strip()


def sync_clip_words(clip: ClipCandidate, transcript: Transcript) -> None:
    """Rellena clip.words y clip.transcript desde el transcript global."""
    clip.words = words_in_range(transcript, clip.start, clip.end)
    clip.transcript = transcript_text(clip.words) or clip.transcript


def clip_words(clip: ClipCandidate, transcript: Transcript) -> list[Word]:
    """Palabras del clip: editadas en el candidato o derivadas del transcript."""
    if clip.words:
        return clip.words
    return words_in_range(transcript, clip.start, clip.end)
