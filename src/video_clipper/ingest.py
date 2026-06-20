"""Etapa de ingesta: validar el crudo y extraer el audio para ASR."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from .ffmpeg_utils import MediaInfo, probe, run

console = Console()


def extract_audio(source: Path, out_wav: Path, sample_rate: int = 16000) -> Path:
    """Extrae audio mono PCM 16kHz (formato esperado por Whisper)."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-i", str(source),
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-c:a", "pcm_s16le",
        str(out_wav),
    ]
    run(cmd)
    return out_wav


def ingest(source: Path, workdir: Path) -> tuple[MediaInfo, Path]:
    """Procesa el crudo: probe + extracción de audio. Devuelve (info, ruta_audio)."""
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"No existe el crudo: {source}")

    info = probe(source)
    console.log(
        f"[cyan]Ingesta[/]: {source.name} · {info.width}x{info.height} · "
        f"{info.fps:.0f}fps · {info.duration/60:.1f} min · audio={'sí' if info.has_audio else 'no'}"
    )
    if not info.has_audio:
        raise RuntimeError("El crudo no tiene pista de audio; no se puede transcribir.")

    audio_path = extract_audio(source, workdir / "audio.wav")
    console.log(f"[green]Audio extraído[/]: {audio_path}")
    return info, audio_path
