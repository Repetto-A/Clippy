"""Nombres de archivo legibles para descargas de clips renderizados."""

from __future__ import annotations

import re
import unicodedata

from .models import ClipCandidate

_FORMAT_SUFFIX = {
    "9x16": "vertical-karaoke",
    "9x16_social": "vertical-social",
    "16x9": "horizontal-karaoke",
    "16x9_social": "horizontal-social",
}


def slugify(text: str, *, max_len: int = 48) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    if not slug:
        slug = "clip"
    return slug[:max_len].strip("-") or "clip"


def build_export_filename(
    clip: ClipCandidate,
    fmt: str,
    *,
    job_slug: str | None = None,
) -> str:
    if fmt not in _FORMAT_SUFFIX:
        raise ValueError(f"formato desconocido: {fmt}")
    base = slugify(clip.title) if clip.title else clip.id
    parts = [p for p in (slugify(job_slug) if job_slug else None, base, _FORMAT_SUFFIX[fmt]) if p]
    return "-".join(parts) + ".mp4"
