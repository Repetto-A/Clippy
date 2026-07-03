"""Preferencias de render por job (UI). Defaults desde config (.env)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from .config import settings


class RenderPrefs(BaseModel):
    """Opciones de export elegibles desde la UI antes de renderizar."""

    caption_style: str = Field(default="karaoke", description="karaoke | social | both")
    caption_social_max_words: int = Field(default=5, ge=2, le=12)
    output_vertical: bool = True
    output_horizontal: bool = True

    @field_validator("caption_style")
    @classmethod
    def _valid_style(cls, v: str) -> str:
        s = v.lower().strip()
        if s not in ("karaoke", "social", "both"):
            raise ValueError("caption_style debe ser karaoke, social o both")
        return s


def default_render_prefs() -> RenderPrefs:
    return RenderPrefs(
        caption_style=settings.caption_style.lower().strip(),
        caption_social_max_words=settings.caption_social_max_words,
        output_vertical=settings.output_vertical,
        output_horizontal=settings.output_horizontal,
    )
