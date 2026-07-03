from pathlib import Path

from video_clipper.captions import _fmt_time, build_ass, build_karaoke_ass, build_social_ass
from video_clipper.models import Word


def test_fmt_time():
    assert _fmt_time(0) == "0:00:00.00"
    assert _fmt_time(65.5) == "0:01:05.50"
    assert _fmt_time(3661.0) == "1:01:01.00"


def test_build_karaoke_ass(tmp_path: Path):
    words = [
        Word(text="Hola", start=10.0, end=10.4),
        Word(text="mundo", start=10.4, end=10.9),
        Word(text="esto", start=10.9, end=11.2),
        Word(text="es", start=11.2, end=11.4),
        Word(text="un", start=11.4, end=11.5),
        Word(text="test.", start=11.5, end=12.0),
    ]
    out = build_karaoke_ass(words, clip_start=10.0, out_path=tmp_path / "c.ass")
    text = out.read_text(encoding="utf-8")
    assert "[Events]" in text
    assert "\\k" in text  # tiene tags de karaoke
    assert "Dialogue:" in text
    # El primer subtítulo arranca en t=0 relativo
    assert "0:00:00.00" in text


def test_build_social_ass_no_karaoke_tags(tmp_path: Path):
    words = [
        Word(text="Uno", start=0.0, end=0.3),
        Word(text="dos", start=0.3, end=0.6),
        Word(text="tres", start=0.6, end=0.9),
        Word(text="cuatro", start=0.9, end=1.2),
        Word(text="cinco", start=1.2, end=1.5),
        Word(text="seis", start=1.5, end=1.8),
    ]
    out = build_social_ass(words, clip_start=0.0, out_path=tmp_path / "s.ass", max_words=5)
    text = out.read_text(encoding="utf-8")
    assert "Style: Social,Anton" in text
    assert "\\k" not in text
    assert "Uno dos tres cuatro cinco" in text
    assert "seis" in text


def test_build_ass_dispatches_social(tmp_path: Path):
    words = [Word(text="hola", start=0.0, end=0.5)]
    out = build_ass(words, 0.0, tmp_path / "x.ass", style="social")
    assert "Social" in out.read_text(encoding="utf-8")
