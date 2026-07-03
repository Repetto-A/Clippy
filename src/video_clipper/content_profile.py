"""Perfiles de contenido: defaults de propose/render por tipo de material (ADR-0007)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from .config import settings
from .propose_prefs import ProposePrefs
from .render_prefs import RenderPrefs


class ContentProfileKind(str, Enum):
    TRAINING = "training"
    PODCAST = "podcast"
    STREAM = "stream"


class JobProfile(BaseModel):
    profile: ContentProfileKind = ContentProfileKind.TRAINING


def _settings_propose() -> ProposePrefs:
    return ProposePrefs(
        target_clips=settings.target_clips,
        min_duration=settings.min_duration,
        max_duration=settings.max_duration,
        rank_finalists=settings.rank_finalists,
    )


def _settings_render() -> RenderPrefs:
    return RenderPrefs(
        caption_style=settings.caption_style.lower().strip(),
        caption_social_max_words=settings.caption_social_max_words,
        output_vertical=settings.output_vertical,
        output_horizontal=settings.output_horizontal,
    )


_PROFILE_PROPOSE: dict[ContentProfileKind, ProposePrefs] = {
    ContentProfileKind.TRAINING: _settings_propose(),
    ContentProfileKind.PODCAST: ProposePrefs(
        target_clips=8,
        min_duration=30.0,
        max_duration=90.0,
        rank_finalists=16,
    ),
    ContentProfileKind.STREAM: ProposePrefs(
        target_clips=10,
        min_duration=20.0,
        max_duration=75.0,
        rank_finalists=20,
    ),
}

_PROFILE_RENDER: dict[ContentProfileKind, RenderPrefs] = {
    ContentProfileKind.TRAINING: _settings_render(),
    ContentProfileKind.PODCAST: RenderPrefs(
        caption_style="social",
        caption_social_max_words=4,
        output_vertical=True,
        output_horizontal=False,
    ),
    ContentProfileKind.STREAM: RenderPrefs(
        caption_style="both",
        caption_social_max_words=5,
        output_vertical=True,
        output_horizontal=True,
    ),
}


def propose_defaults_for_profile(kind: ContentProfileKind) -> ProposePrefs:
    return _PROFILE_PROPOSE.get(kind, _settings_propose()).model_copy()


def render_defaults_for_profile(kind: ContentProfileKind) -> RenderPrefs:
    return _PROFILE_RENDER.get(kind, _settings_render()).model_copy()


def default_job_profile() -> JobProfile:
    return JobProfile(profile=ContentProfileKind.TRAINING)


def parse_profile(value: str | None) -> ContentProfileKind:
    if not value:
        return ContentProfileKind.TRAINING
    try:
        return ContentProfileKind(value.lower().strip())
    except ValueError:
        return ContentProfileKind.TRAINING
