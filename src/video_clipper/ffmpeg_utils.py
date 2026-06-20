"""Helpers finos sobre ffmpeg / ffprobe."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Ejecuta un comando y levanta FFmpegError si falla.

    stdin=DEVNULL evita que ffmpeg se cuelgue leyendo stdin cuando corre como
    subproceso (modo interactivo); equivale a pasarle -nostdin.
    """
    proc = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        stderr = proc.stderr or ""
        raise FFmpegError(f"Comando falló ({proc.returncode}): {' '.join(cmd[:3])} ...\n{stderr[-2000:]}")
    return proc


@dataclass
class MediaInfo:
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool


def probe(path: Path) -> MediaInfo:
    """Devuelve metadata básica del archivo via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path),
    ]
    out = run(cmd).stdout
    data = json.loads(out)

    duration = float(data.get("format", {}).get("duration", 0.0))
    width = height = 0
    fps = 0.0
    has_audio = False
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and width == 0:
            width = int(s.get("width", 0))
            height = int(s.get("height", 0))
            rate = s.get("r_frame_rate", "0/1")
            try:
                num, den = rate.split("/")
                fps = float(num) / float(den) if float(den) else 0.0
            except (ValueError, ZeroDivisionError):
                fps = 0.0
        elif s.get("codec_type") == "audio":
            has_audio = True
    return MediaInfo(duration=duration, width=width, height=height, fps=fps, has_audio=has_audio)


def ffmpeg_has_encoder(name: str) -> bool:
    """Indica si ffmpeg tiene disponible un encoder (p.ej. h264_nvenc)."""
    try:
        out = run(["ffmpeg", "-v", "error", "-hide_banner", "-encoders"]).stdout
    except FFmpegError:
        return False
    return name in out
