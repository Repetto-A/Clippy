"""Render final de cada clip: trim + reencuadre + subtítulos + encode (NVENC)."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from .clip_utils import clip_words
from .captions import build_karaoke_ass
from .config import settings
from .ffmpeg_utils import ffmpeg_has_encoder, run
from .models import ClipCandidate, Transcript, Word
from .reframe import build_vertical_filter, detect_webcam_region

console = Console()


def _video_codec_args() -> list[str]:
    if settings.use_nvenc and ffmpeg_has_encoder("h264_nvenc"):
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "23", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p"]


def _words_in(clip: ClipCandidate, transcript: Transcript) -> list[Word]:
    return clip_words(clip, transcript)


def render_clip(
    source: Path,
    clip: ClipCandidate,
    transcript: Transcript,
    out_dir: Path,
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    words = _words_in(clip, transcript)
    dur = clip.duration
    outputs: dict[str, str] = {}
    codec = _video_codec_args()

    if settings.output_vertical:
        ass_v = build_karaoke_ass(
            words, clip.start, out_dir / f"{clip.id}_v.ass",
            play_w=1080, play_h=1920, font_size=64, margin_v=220,
        )
        webcam = detect_webcam_region(source, (clip.start + clip.end) / 2)
        vfilter = build_vertical_filter(clip.layout, webcam)
        out_v = out_dir / f"{clip.id}_9x16.mp4"
        run([
            "ffmpeg", "-y", "-v", "error",
            "-ss", str(clip.start), "-i", str(source), "-t", str(dur),
            "-filter_complex", f"{vfilter};[v]ass={ass_v.name}[vout]",
            "-map", "[vout]", "-map", "0:a:0",
            *codec, "-c:a", "aac", "-b:a", "160k",
            str(out_v),
        ], capture=True)
        outputs["9x16"] = str(out_v)

    if settings.output_horizontal:
        ass_h = build_karaoke_ass(
            words, clip.start, out_dir / f"{clip.id}_h.ass",
            play_w=1920, play_h=1080, font_size=48, margin_v=80,
        )
        out_h = out_dir / f"{clip.id}_16x9.mp4"
        run([
            "ffmpeg", "-y", "-v", "error",
            "-ss", str(clip.start), "-i", str(source), "-t", str(dur),
            "-filter_complex",
            f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2[s];[s]ass={ass_h.name}[vout]",
            "-map", "[vout]", "-map", "0:a:0",
            *codec, "-c:a", "aac", "-b:a", "160k",
            str(out_h),
        ], capture=True)
        outputs["16x9"] = str(out_h)

    console.log(f"[green]Render[/] {clip.id}: {', '.join(outputs.keys())}")
    return outputs


def render_clip_cwd(source: Path, clip: ClipCandidate, transcript: Transcript, out_dir: Path) -> dict[str, str]:
    """Wrapper que ejecuta ffmpeg con cwd=out_dir para evitar problemas de escape
    de rutas Windows en el filtro ass (se referencia el .ass por nombre)."""
    import os

    source_abs = source.resolve()
    out_abs = out_dir.resolve()
    out_abs.mkdir(parents=True, exist_ok=True)
    prev = os.getcwd()
    try:
        os.chdir(out_abs)
        return render_clip(source_abs, clip, transcript, out_abs)
    finally:
        os.chdir(prev)
