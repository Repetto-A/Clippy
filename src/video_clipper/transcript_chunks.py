"""Particionado del transcript para llamadas LLM en videos largos."""

from __future__ import annotations

from .models import Segment


def segment_line(seg: Segment) -> str:
    return f"[{seg.start:.1f}-{seg.end:.1f}] {seg.text}"


def lines_from_segments(segments: list[Segment]) -> str:
    return "\n".join(segment_line(s) for s in segments)


def chunk_segments(segments: list[Segment], max_chars: int) -> list[list[Segment]]:
    """Agrupa segmentos en bloques que entren en el contexto del LLM.

    Los timestamps de cada línea siguen siendo absolutos respecto al crudo completo.
    """
    if not segments or max_chars <= 0:
        return [segments] if segments else []

    chunks: list[list[Segment]] = []
    current: list[Segment] = []
    size = 0

    for seg in segments:
        line_len = len(segment_line(seg)) + 1
        if current and size + line_len > max_chars:
            chunks.append(current)
            current = []
            size = 0
        current.append(seg)
        size += line_len

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
