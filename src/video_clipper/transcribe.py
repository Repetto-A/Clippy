"""Transcripción con timestamps por palabra, detrás de una interfaz intercambiable."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from rich.console import Console

from .config import settings
from .ffmpeg_utils import probe, run
from .models import Segment, Transcript, Word

console = Console()

ProgressFn = Callable[[float, str], None]


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path, *, on_progress: ProgressFn | None = None) -> Transcript: ...


def _group_into_segments(words: list[Word], max_gap: float = 0.8) -> list[Segment]:
    """Agrupa palabras en frases usando puntuación y huecos de tiempo."""
    segments: list[Segment] = []
    buf: list[Word] = []

    def flush() -> None:
        if not buf:
            return
        text = "".join(w.text for w in buf).strip()
        segments.append(
            Segment(text=text, start=buf[0].start, end=buf[-1].end, speaker=buf[0].speaker, words=list(buf))
        )
        buf.clear()

    for i, w in enumerate(words):
        buf.append(w)
        ends_sentence = w.text.strip().endswith((".", "?", "!", "…"))
        gap_next = (words[i + 1].start - w.end) if i + 1 < len(words) else 0.0
        if ends_sentence or gap_next > max_gap:
            flush()
    flush()
    return segments


def _split_audio_chunks(audio_path: Path, chunk_dir: Path, chunk_seconds: int) -> list[tuple[Path, float]]:
    """Parte audio largo en trozos PCM para evitar límites de PyAV en decode_audio."""
    chunk_dir.mkdir(parents=True, exist_ok=True)
    for old in chunk_dir.glob("chunk_*.wav"):
        old.unlink(missing_ok=True)

    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-i", str(audio_path),
        "-f", "segment",
        "-segment_time", str(chunk_seconds),
        "-reset_timestamps", "1",
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(chunk_dir / "chunk_%03d.wav"),
    ]
    run(cmd)

    chunks: list[tuple[Path, float]] = []
    offset = 0.0
    for path in sorted(chunk_dir.glob("chunk_*.wav")):
        chunks.append((path, offset))
        offset += probe(path).duration
    return chunks


class FasterWhisperTranscriber:
    """Transcriptor local basado en faster-whisper (requiere extra 'asr')."""

    def __init__(self) -> None:
        self.model_name = settings.whisper_model
        self.device = settings.whisper_device
        self.compute_type = settings.whisper_compute_type
        self.language = settings.language
        self.chunk_seconds = settings.whisper_chunk_seconds

    def _add_cuda_dll_dirs(self) -> None:
        """En Windows, registra las DLLs de cuBLAS/cuDNN (paquetes nvidia-*-cu12)
        para que CTranslate2 las encuentre sin tener que tocar el PATH a mano."""
        import os
        import site
        import sys

        if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
            return

        roots = list(site.getsitepackages())
        user = site.getusersitepackages()
        if user:
            roots.append(user)

        for root in roots:
            base = Path(root) / "nvidia"
            if not base.is_dir():
                continue
            for sub in ("cublas/bin", "cudnn/bin", "cuda_nvrtc/bin"):
                d = base / sub
                if d.is_dir():
                    os.add_dll_directory(str(d))
                    os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")

    def _load_model(self):
        if self.device == "cuda":
            self._add_cuda_dll_dirs()
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "faster-whisper no está instalado. Instalá el extra: pip install -e .[asr]"
            ) from e

        console.log(f"[cyan]Transcripción[/]: cargando {self.model_name} en {self.device}...")
        return WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)

    def _transcribe_file(self, model, audio_path: Path) -> tuple[list[Word], str | None]:
        seg_iter, info = model.transcribe(
            str(audio_path),
            language=self.language,
            word_timestamps=True,
            vad_filter=True,
        )
        words: list[Word] = []
        for seg in seg_iter:
            for w in (seg.words or []):
                words.append(Word(text=w.word, start=float(w.start), end=float(w.end)))
        return words, info.language

    def transcribe(self, audio_path: Path, *, on_progress: ProgressFn | None = None) -> Transcript:
        model = self._load_model()
        duration = probe(audio_path).duration
        chunk_seconds = max(60, self.chunk_seconds)

        if duration <= chunk_seconds * 1.05:
            if on_progress:
                on_progress(0.1, "Transcribiendo audio…")
            words, lang = self._transcribe_file(model, audio_path)
            if on_progress:
                on_progress(1.0, "Transcripción lista")
        else:
            chunk_dir = audio_path.parent / "audio_chunks"
            chunks = _split_audio_chunks(audio_path, chunk_dir, chunk_seconds)
            console.log(
                f"[cyan]Audio largo[/]: {duration/60:.1f} min -> {len(chunks)} trozos de ~{chunk_seconds//60} min"
            )
            words = []
            lang = self.language
            for i, (chunk_path, offset) in enumerate(chunks):
                pct = (i + 0.5) / len(chunks)
                if on_progress:
                    on_progress(pct, f"Transcribiendo trozo {i + 1}/{len(chunks)}…")
                chunk_words, chunk_lang = self._transcribe_file(model, chunk_path)
                if chunk_lang:
                    lang = chunk_lang
                for w in chunk_words:
                    words.append(Word(text=w.text, start=w.start + offset, end=w.end + offset))
            if on_progress:
                on_progress(1.0, "Transcripción lista")

        segments = _group_into_segments(words)
        out_duration = words[-1].end if words else duration
        console.log(f"[green]Transcripción lista[/]: {len(words)} palabras, {len(segments)} frases")
        return Transcript(
            language=lang or self.language,
            duration=out_duration,
            words=words,
            segments=segments,
        )


def get_transcriber() -> Transcriber:
    return FasterWhisperTranscriber()
