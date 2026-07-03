"""Preferencias de propose por job (UI). Defaults desde config (.env)."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from .config import settings


class ProposePrefs(BaseModel):
    """Opciones de detección/selección de clips antes de proponer o re-proponer."""

    target_clips: int = Field(default=12, ge=1, le=50)
    min_duration: float = Field(default=15.0, ge=5.0, le=300.0)
    max_duration: float = Field(default=60.0, ge=10.0, le=600.0)
    rank_finalists: int = Field(default=24, ge=1, le=100)

    @model_validator(mode="after")
    def _min_le_max(self) -> ProposePrefs:
        if self.min_duration > self.max_duration:
            raise ValueError("min_duration no puede ser mayor que max_duration")
        return self


def default_propose_prefs() -> ProposePrefs:
    return ProposePrefs(
        target_clips=settings.target_clips,
        min_duration=settings.min_duration,
        max_duration=settings.max_duration,
        rank_finalists=settings.rank_finalists,
    )
