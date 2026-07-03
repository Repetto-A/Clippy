"""Render final de cada clip: trim + reencuadre + subtítulos + encode (NVENC)."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from .clip_utils import clip_words
from .captions import build_ass
from .config import settings
from .ffmpeg_utils import ffmpeg_has_encoder, run
from .models import ClipCandidate, Transcript, Word
from .render_prefs import RenderPrefs, default_render_prefs
from .reframe import build_vertical_filter, detect_webcam_region

console = Console()

_OUTPUT_KEYS = {
    ("karaoke", "vertical"): "9x16",
    ("social", "vertical"): "9x16_social",
    ("karaoke", "horizontal"): "16x9",
    ("social", "horizontal"): "16x9_social",
}


def _video_codec_args() -> list[str]:
    if settings.use_nvenc and ffmpeg_has_encoder("h264_nvenc"):
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "23", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p"]


def _caption_presets(prefs: RenderPrefs) -> list[str]:
    if prefs.caption_style == "both":
        return ["karaoke", "social"]
    if prefs.caption_style == "social":
        return ["social"]
    return ["karaoke"]


def _words_in(clip: ClipCandidate, transcript: Transcript) -> list[Word]:
    return clip_words(clip, transcript)


def _clip_dir(out_dir: Path, clip_id: str) -> Path:
    d = out_dir / clip_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _render_vertical(
    source: Path,
    clip: ClipCandidate,
    words: list[Word],
    dur: float,
    clip_dir: Path,
    preset: str,
    codec: list[str],
    prefs: RenderPrefs,
) -> tuple[str, str]:
    ass_path = build_ass(
        words,
        clip.start,
        clip_dir / f"{preset}_v.ass",
        style=preset,
        play_w=1080,
        play_h=1920,
        max_words=prefs.caption_social_max_words,
    )
    webcam = detect_webcam_region(source, clip.start, clip.end)
    vfilter = build_vertical_filter(clip.layout, webcam)
    out_key = _OUTPUT_KEYS[(preset, "vertical")]
    out_path = clip_dir / f"clip_{out_key}.mp4"
    run([
        "ffmpeg", "-y", "-v", "error",
        "-ss", str(clip.start), "-i", str(source), "-t", str(dur),
        "-filter_complex", f"{vfilter};[v]ass={ass_path.name}[vout]",
        "-map", "[vout]", "-map", "0:a:0",
        *codec, "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        str(out_path),
    ], capture=True)
    return out_key, str(out_path.resolve())


def _render_horizontal(
    source: Path,
    clip: ClipCandidate,
    words: list[Word],
    dur: float,
    clip_dir: Path,
    preset: str,
    codec: list[str],
    prefs: RenderPrefs,
) -> tuple[str, str]:
    ass_path = build_ass(
        words,
        clip.start,
        clip_dir / f"{preset}_h.ass",
        style=preset,
        play_w=1920,
        play_h=1080,
        max_words=prefs.caption_social_max_words,
    )
    out_key = _OUTPUT_KEYS[(preset, "horizontal")]
    out_path = clip_dir / f"clip_{out_key}.mp4"
    run([
        "ffmpeg", "-y", "-v", "error",
        "-ss", str(clip.start), "-i", str(source), "-t", str(dur),
        "-filter_complex",
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2[s];[s]ass={ass_path.name}[vout]",
        "-map", "[vout]", "-map", "0:a:0",
        *codec, "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        str(out_path),
    ], capture=True)
    return out_key, str(out_path.resolve())


def render_clip(
    source: Path,
    clip: ClipCandidate,
    transcript: Transcript,
    out_dir: Path,
    prefs: RenderPrefs | None = None,
) -> dict[str, str]:
    prefs = prefs or default_render_prefs()
    clip_dir = _clip_dir(out_dir, clip.id)
    words = _words_in(clip, transcript)
    dur = clip.duration
    outputs: dict[str, str] = {}
    codec = _video_codec_args()
    presets = _caption_presets(prefs)

    for preset in presets:
        if prefs.output_vertical:
            key, path = _render_vertical(source, clip, words, dur, clip_dir, preset, codec, prefs)
            outputs[key] = path
        if prefs.output_horizontal:
            key, path = _render_horizontal(source, clip, words, dur, clip_dir, preset, codec, prefs)
            outputs[key] = path

    console.log(f"[green]Render[/] {clip.id}: {', '.join(outputs.keys())}")
    return outputs


def render_clip_cwd(
    source: Path,
    clip: ClipCandidate,
    transcript: Transcript,
    out_dir: Path,
    prefs: RenderPrefs | None = None,
) -> dict[str, str]:
    """Wrapper que ejecuta ffmpeg con cwd=clip_dir para evitar problemas de escape
    de rutas Windows en el filtro ass (se referencia el .ass por nombre)."""
    import os

    source_abs = source.resolve()
    out_abs = out_dir.resolve()
    out_abs.mkdir(parents=True, exist_ok=True)
    clip_dir = _clip_dir(out_abs, clip.id)
    prev = os.getcwd()
    try:
        os.chdir(clip_dir)
        return render_clip(source_abs, clip, transcript, out_abs, prefs=prefs)
    finally:
        os.chdir(prev)
