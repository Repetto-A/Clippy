"""Particionado del transcript para llamadas LLM en videos largos."""

from __future__ import annotations

from .models import Segment


def segment_line(seg: Segment) -> str:
    return f"[{seg.start:.1f}-{seg.end:.1f}] {seg.text}"


def lines_from_segments(segments: list[Segment]) -> str:
    return "\n".join(segment_line(s) for s in segments)


def _chunk_chars(segs: list[Segment]) -> int:
    return sum(len(segment_line(s)) + 1 for s in segs)


def _close_index(current: list[Segment], silences, window: float) -> int:
    """Index of the segment in `current` to close the chunk after.

    Prefer the segment nearest the budget whose end lands on a silence (a strong
    natural boundary), scanning from the end backward. Falls back to the last
    segment (greedy) when no boundary aligns or no silences are given.
    """
    if not silences:
        return len(current) - 1
    starts = [s.start for s in silences]
    for i in range(len(current) - 1, -1, -1):
        if any(abs(current[i].end - ss) <= window for ss in starts):
            return i
    return len(current) - 1


def chunk_segments(
    segments: list[Segment],
    max_chars: int,
    silences=None,
    overlap_segments: int = 0,
    boundary_window: float = 1.0,
) -> list[list[Segment]]:
    """Agrupa segmentos en bloques que entren en el contexto del LLM.

    Cierra cada bloque en el silencio largo más cercano al presupuesto (si se pasan
    `silences`), evitando partir un momento coherente a la mitad. `overlap_segments`
    repite los últimos N segmentos al inicio del bloque siguiente para cubrir la
    frontera. Sin `silences` reproduce el corte greedy original.

    Los timestamps de cada línea siguen siendo absolutos respecto al crudo completo.
    """
    if not segments or max_chars <= 0:
        return [segments] if segments else []

    chunks: list[list[Segment]] = []
    current: list[Segment] = []

    for seg in segments:
        line_len = len(segment_line(seg)) + 1
        if current and _chunk_chars(current) + line_len > max_chars:
            ci = _close_index(current, silences, boundary_window)
            emitted = current[: ci + 1]
            remainder = current[ci + 1 :]
            chunks.append(emitted)
            carry = emitted[-overlap_segments:] if overlap_segments > 0 else []
            current = list(carry) + remainder
        current.append(seg)

    if current:
        chunks.append(current)
    return chunks


def clips_target_for_chunk(
    chunk_index: int,
    chunk_count: int,
    total_target: int,
    per_chunk: int,
) -> int:
    """Reparte el cupo de clips entre chunks (mínimo 2 por chunk si hay varios)."""
    if chunk_count <= 1:
        return total_target
    base = max(2, per_chunk)
    if chunk_index == chunk_count - 1:
        # último chunk: el resto del cupo global
        assigned = base * (chunk_count - 1)
        return max(2, total_target - assigned)
    return base
