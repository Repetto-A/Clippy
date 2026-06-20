"""Configuración global del pipeline, cargada desde entorno (.env) con defaults sensatos."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


def _get(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _get_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


class WebcamRegion(BaseModel):
    """Región por defecto del tile de webcam (fracciones 0-1 del frame).

    Derivada del análisis del crudo de muestra (Google Meet, tile a la derecha).
    Se usa como fallback cuando la detección de cara no está disponible.
    """

    x: float = 0.747
    y: float = 0.391
    w: float = 0.239
    h: float = 0.234


class SlideRegion(BaseModel):
    """Región por defecto del área de slides (fracciones 0-1 del frame)."""

    x: float = 0.029
    y: float = 0.104
    w: float = 0.669
    h: float = 0.642


class Settings(BaseModel):
    # Rutas
    workdir: Path = Path(_get("VC_WORKDIR", "work"))

    # Transcripción
    whisper_model: str = _get("VC_WHISPER_MODEL", "large-v3")
    whisper_device: str = _get("VC_WHISPER_DEVICE", "cuda")
    whisper_compute_type: str = _get("VC_WHISPER_COMPUTE", "float16")
    whisper_chunk_seconds: int = _get_int("VC_WHISPER_CHUNK_SECONDS", 600)
    language: str = _get("VC_LANGUAGE", "es")

    # Scoring / LLM
    scorer: str = _get("VC_SCORER", "llm")     # "heuristic" | "llm"
    llm_provider: str = _get("VC_LLM_PROVIDER", "opencode")   # "ollama" | "opencode" | "anthropic"
    llm_model: str = _get("VC_LLM_MODEL", "opencode-go/deepseek-v4-flash")
    ollama_host: str = _get("VC_OLLAMA_HOST", "http://localhost:11434")
    opencode_timeout: float = _get_float("VC_OPENCODE_TIMEOUT", 600.0)
    anthropic_api_key: str = _get("ANTHROPIC_API_KEY", "")

    # Selección de clips
    min_duration: float = _get_float("VC_MIN_DURATION", 15.0)
    max_duration: float = _get_float("VC_MAX_DURATION", 60.0)
    target_clips: int = _get_int("VC_TARGET_CLIPS", 12)

    # Eval (M1): umbral de solape IoU que cuenta como "match" contra el golden set
    eval_iou_threshold: float = _get_float("VC_EVAL_IOU", 0.5)

    # Chunking LLM (videos largos)
    llm_chunk_chars: int = _get_int("VC_LLM_CHUNK_CHARS", 12000)
    llm_clips_per_chunk: int = _get_int("VC_LLM_CLIPS_PER_CHUNK", 6)

    # Salida
    output_vertical: bool = _get("VC_OUT_VERTICAL", "1") == "1"
    output_horizontal: bool = _get("VC_OUT_HORIZONTAL", "1") == "1"
    translate_en: bool = _get("VC_TRANSLATE_EN", "0") == "1"

    # Render
    use_nvenc: bool = _get("VC_NVENC", "1") == "1"

    # Layout
    webcam: WebcamRegion = WebcamRegion()
    slide: SlideRegion = SlideRegion()

    def source_workdir(self, source: Path) -> Path:
        """Workdir específico para un crudo (por nombre de archivo, sin extensión)."""
        return self.workdir / source.stem


settings = Settings()
