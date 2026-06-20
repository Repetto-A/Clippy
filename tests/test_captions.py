from pathlib import Path

from video_clipper.captions import _fmt_time, build_karaoke_ass
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
