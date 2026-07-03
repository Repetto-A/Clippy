from pathlib import Path

from video_clipper.api import services
from video_clipper.captions import caption_preview_samples, sample_caption_lines
from video_clipper.config import settings
from video_clipper.models import (
    CandidateSet,
    ClipCandidate,
    ClipStatus,
    Transcript,
    Word,
)
from video_clipper import storage


def _words():
    return [
        Word(text="Hola", start=10.0, end=10.3),
        Word(text="mundo", start=10.3, end=10.6),
        Word(text="esto", start=10.6, end=10.8),
        Word(text="es", start=10.8, end=10.9),
        Word(text="un", start=10.9, end=11.0),
        Word(text="ejemplo", start=11.0, end=11.4),
        Word(text="largo", start=11.4, end=11.7),
        Word(text="de", start=11.7, end=11.8),
        Word(text="subtitulos.", start=11.8, end=12.2),
    ]


def test_sample_caption_lines_karaoke_max_two():
    lines = sample_caption_lines(_words(), clip_start=10.0, style="karaoke", max_lines=2)
    assert len(lines) <= 2
    assert "Hola" in lines[0]


def test_sample_caption_lines_social_respects_max_words():
    lines = sample_caption_lines(_words(), clip_start=10.0, style="social", max_words=3, max_lines=2)
    assert len(lines) <= 2
    assert len(lines[0].split()) <= 3


def test_caption_preview_samples_both_returns_two_styles():
    previews = caption_preview_samples(_words(), clip_start=10.0, caption_style="both", max_words=4)
    styles = {p["style"] for p in previews}
    assert styles == {"karaoke", "social"}
    assert all(p["sample_lines"] for p in previews)
    assert previews[0]["font"] in ("Montserrat", "Anton")


def _seed_job(tmp_path: Path, monkeypatch, *, approved: bool = True):
    monkeypatch.setattr(settings, "workdir", tmp_path)
    wd = tmp_path / "job1"
    wd.mkdir()
    clip = ClipCandidate(
        id="c1",
        start=10.0,
        end=20.0,
        score=80.0,
        status=ClipStatus.APPROVED if approved else ClipStatus.PROPOSED,
        words=_words(),
        title="Clip demo",
    )
    storage.save_candidates(CandidateSet(source="job1", candidates=[clip]), wd)
    storage.save_transcript(
        Transcript(language="es", duration=60.0, words=_words()),
        wd,
    )
    storage.save_render_prefs(storage.load_render_prefs(wd), wd)
    return wd


def test_get_caption_preview_first_approved_clip(tmp_path, monkeypatch):
    _seed_job(tmp_path, monkeypatch, approved=True)
    result = services.get_caption_preview("job1")
    assert result is not None
    assert result["clip_id"] == "c1"
    assert result["clip_title"] == "Clip demo"
    assert len(result["previews"]) >= 1
    assert result["previews"][0]["sample_lines"]


def test_get_caption_preview_without_approved(tmp_path, monkeypatch):
    _seed_job(tmp_path, monkeypatch, approved=False)
    result = services.get_caption_preview("job1")
    assert result is not None
    assert result["previews"] == []
    assert "Aprobá" in (result["message"] or "")
