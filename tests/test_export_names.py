from video_clipper.export_names import build_export_filename
from video_clipper.models import ClipCandidate


def test_build_export_filename_uses_title_and_format():
    clip = ClipCandidate(id="c1", start=0, end=30, title="Concepto Clave de IA")
    name = build_export_filename(clip, "9x16_social", job_slug="Formacion IA 2026")
    assert name.endswith(".mp4")
    assert "vertical-social" in name
    assert "concepto-clave-de-ia" in name
    assert "formacion-ia-2026" in name


def test_build_export_filename_falls_back_to_clip_id():
    clip = ClipCandidate(id="scan_03", start=0, end=20, title="")
    name = build_export_filename(clip, "16x9")
    assert name == "scan_03-horizontal-karaoke.mp4"
