"""Extracción de señales locales: silencios, cambios de escena y 'pantalla sucia'.

Estas señales no deciden el clip por sí solas; alimentan al scorer y al ajuste de
cortes (snap a silencios) y permiten descartar tramos donde la pantalla muestra UI
de Meet / navegador en vez de la slide.
"""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console

from .ffmpeg_utils import run
from .models import Signals, TimeRange

console = Console()

_SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)")
_PTS_TIME = re.compile(r"pts_time:([0-9.]+)")


def detect_silences(audio_wav: Path, noise_db: float = -30.0, min_dur: float = 0.4) -> list[TimeRange]:
    """Detecta silencios con el filtro silencedetect de ffmpeg."""
    cmd = [
        "ffmpeg", "-v", "info", "-nostats", "-i", str(audio_wav),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}",
        "-f", "null", "-",
    ]
    proc = run(cmd)
    text = (proc.stderr or "") + (proc.stdout or "")

    silences: list[TimeRange] = []
    pending_start: float | None = None
    for line in text.splitlines():
        if m := _SILENCE_START.search(line):
            pending_start = float(m.group(1))
        elif m := _SILENCE_END.search(line):
            end = float(m.group(1))
            start = pending_start if pending_start is not None else max(0.0, end - min_dur)
            silences.append(TimeRange(start=start, end=end))
            pending_start = None
    return silences


def detect_scene_changes(source: Path, threshold: float = 0.4) -> list[float]:
    """Detecta cambios de escena (timestamps) usando el filtro scene de ffmpeg.

    Trabaja sobre una versión reducida del video para acelerar el análisis.
    """
    cmd = [
        "ffmpeg", "-v", "info", "-nostats", "-i", str(source),
        "-vf", f"scale=320:-2,select='gt(scene,{threshold})',showinfo",
        "-an", "-f", "null", "-",
    ]
    proc = run(cmd)
    text = (proc.stderr or "") + (proc.stdout or "")
    return [float(m.group(1)) for m in _PTS_TIME.finditer(text)]


def detect_dirty_segments(
    scene_changes: list[float],
    duration: float,
    window: float = 6.0,
    cuts_threshold: int = 4,
) -> list[TimeRange]:
    """Heurística v1: tramos con alta densidad de cambios de escena.

    Cuando se navega la UI de Meet / pestañas del navegador hay muchos cortes en poco
    tiempo, a diferencia de una slide estable. Marcamos esas ventanas como 'sucias'.
    Es un proxy mejorable (futuro: validación multimodal con visual_check).
    """
    if not scene_changes:
        return []

    dirty: list[TimeRange] = []
    n = len(scene_changes)
    i = 0
    while i < n:
        j = i
        while j < n and scene_changes[j] - scene_changes[i] <= window:
            j += 1
        if (j - i) >= cuts_threshold:
            start = max(0.0, scene_changes[i])
            end = min(duration, scene_changes[j - 1] + 1.0)
            if dirty and start <= dirty[-1].end:
                dirty[-1].end = max(dirty[-1].end, end)
            else:
                dirty.append(TimeRange(start=start, end=end))
        i += 1
    return dirty


def extract_signals(source: Path, audio_wav: Path, duration: float) -> Signals:
    console.log("[cyan]Señales[/]: detectando silencios...")
    silences = detect_silences(audio_wav)
    console.log(f"  silencios: {len(silences)}")

    console.log("[cyan]Señales[/]: detectando cambios de escena...")
    scenes = detect_scene_changes(source)
    console.log(f"  escenas: {len(scenes)}")

    dirty = detect_dirty_segments(scenes, duration)
    console.log(f"  tramos 'sucios': {len(dirty)}")

    return Signals(silences=silences, scene_changes=scenes, dirty_segments=dirty)
