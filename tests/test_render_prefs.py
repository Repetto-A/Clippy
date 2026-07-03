from pathlib import Path

import pytest

from video_clipper.render_prefs import RenderPrefs, default_render_prefs
from video_clipper.storage import load_render_prefs, save_render_prefs


def test_default_render_prefs():
    prefs = default_render_prefs()
    assert prefs.caption_style in ("karaoke", "social", "both")


def test_render_prefs_validation():
    with pytest.raises(ValueError):
        RenderPrefs(caption_style="invalid")


def test_save_and_load_render_prefs(tmp_path: Path):
    prefs = RenderPrefs(caption_style="both", caption_social_max_words=6, output_horizontal=False)
    save_render_prefs(prefs, tmp_path)
    loaded = load_render_prefs(tmp_path)
    assert loaded.caption_style == "both"
    assert loaded.caption_social_max_words == 6
    assert loaded.output_horizontal is False
