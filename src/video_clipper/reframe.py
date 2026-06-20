"""Construcción del filtergraph de reencuadre vertical 9:16 (layouts A y B).

El reencuadre no renderiza por sí mismo: produce el string de filter_complex que
render.py combina con los subtítulos y el encode. La detección de cara es opcional
y solo refina la posición del tile de webcam (fallback: región de config).
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from .config import WebcamRegion, settings
from .models import Layout

console = Console()

BG = "0x0d1117"
OUT_W, OUT_H = 1080, 1920


def _crop(region) -> str:
    return (
        f"crop=in_w*{region.w:.4f}:in_h*{region.h:.4f}:"
        f"in_w*{region.x:.4f}:in_h*{region.y:.4f}"
    )


def _blurred_bg(slide) -> str:
    """Fondo que llena 1080x1920 con la slide ampliada y difuminada (sin barras negras)."""
    return (
        f"[0:v]{_crop(slide)},scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
        f"crop={OUT_W}:{OUT_H},boxblur=24:2,eq=brightness=-0.22:saturation=0.9[bg]"
    )


def build_vertical_filter(layout: Layout, webcam: WebcamRegion | None = None) -> str:
    """Devuelve un filter_complex que produce el stream [v] en 1080x1920.

    Ambos layouts rellenan el fondo con la slide difuminada para evitar barras negras.
    """
    webcam = webcam or settings.webcam
    slide = settings.slide

    if layout == Layout.SCREEN_FOCUS:
        # Pantalla protagonista: slide a todo el ancho, webcam chica en esquina.
        return (
            f"{_blurred_bg(slide)};"
            f"[0:v]{_crop(slide)},scale={OUT_W}:-2[slide];"
            f"[0:v]{_crop(webcam)},scale=380:-2,setsar=1[cam];"
            f"[bg][slide]overlay=(W-w)/2:(H-h)/2:shortest=1[t1];"
            f"[t1][cam]overlay=W-w-40:140[v]"
        )

    # Layout A (apilado) por defecto: slide arriba, webcam abajo, ambos grandes.
    return (
        f"{_blurred_bg(slide)};"
        f"[0:v]{_crop(slide)},scale=1040:-2[slide];"
        f"[0:v]{_crop(webcam)},scale=720:-2,setsar=1[cam];"
        f"[bg][slide]overlay=(W-w)/2:430:shortest=1[t1];"
        f"[t1][cam]overlay=(W-w)/2:1080[v]"
    )


def detect_webcam_region(source: Path, t: float) -> WebcamRegion:
    """Refina la región de webcam detectando la cara en un frame (opcional).

    Si opencv/mediapipe no están instalados o no se detecta cara, devuelve el default.
    """
    try:
        import cv2  # type: ignore
        import mediapipe as mp  # type: ignore
    except ImportError:
        return settings.webcam

    import tempfile

    from .ffmpeg_utils import run

    with tempfile.TemporaryDirectory() as td:
        frame_path = Path(td) / "f.jpg"
        run([
            "ffmpeg", "-v", "error", "-ss", str(t), "-i", str(source),
            "-frames:v", "1", "-q:v", "3", str(frame_path), "-y",
        ])
        img = cv2.imread(str(frame_path))
        if img is None:
            return settings.webcam
        h, w = img.shape[:2]
        with mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as fd:
            res = fd.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if not res.detections:
            return settings.webcam
        # Tomar la detección más a la derecha (el tile de webcam suele estar a la derecha)
        best = max(res.detections, key=lambda d: d.location_data.relative_bounding_box.xmin)
        box = best.location_data.relative_bounding_box
        # Expandir alrededor de la cara para encuadrar el tile completo
        pad_x, pad_y = box.width * 0.9, box.height * 0.9
        x = max(0.0, box.xmin - pad_x / 2)
        y = max(0.0, box.ymin - pad_y / 2)
        rw = min(1.0 - x, box.width + pad_x)
        rh = min(1.0 - y, box.height + pad_y)
        return WebcamRegion(x=round(x, 4), y=round(y, 4), w=round(rw, 4), h=round(rh, 4))
