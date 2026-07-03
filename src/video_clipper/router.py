"""TaskRouter: enruta tareas nombradas a modelos (local u online).

En el MVP todas las tareas van a un único proveedor. La arquitectura permite, a
futuro, mapear cada tarea a un modelo distinto (best-of-breed) cambiando solo config.

Backends:
- OllamaRouter: LLM local en la GPU (sin costo, sin datos afuera). Ideal para iterar.
- ClaudeRouter: API de Anthropic (mejor juicio editorial), para cuando haya key.

Tareas previstas: "score_moments", "titles", "translate", "visual_check".
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Protocol

from .config import settings


# --- Prompts compartidos entre backends ---------------------------------------

def build_scan_prompt(payload: dict) -> tuple[str, str]:
    """Pasada 1 (scan): recall alto, bordes aproximados, evita tramos sucios."""
    system = (
        "Sos un editor experto de contenido corto educativo en español. "
        "Recibís la transcripción de una capacitación/stream con timestamps. "
        "Este es el PRIMER PASE (scan): marcá GENEROSAMENTE los momentos potencialmente "
        "clipeables —explicaciones auto-contenidas, insights, tips, analogías, Q&A—. "
        "Priorizá recall: mejor sobrar candidatos que perder un buen momento; otro pase filtra. "
        "Cada clip debe durar entre "
        f"{int(payload.get('min_duration', 15))} y {int(payload.get('max_duration', 60))} segundos. "
        "Respondé SOLO JSON válido."
    )
    dirty = payload.get("dirty_ranges") or []
    dirty_note = ""
    if dirty:
        ranges = ", ".join(f"[{float(a):.1f}-{float(b):.1f}]" for a, b in dirty)
        dirty_note = (
            "\n\nEVITÁ estos tramos (la pantalla muestra UI/navegador, no sirven como clip): "
            f"{ranges}.\n"
        )
    user = (
        "Transcripción (cada línea: [start-end] texto). "
        "Los timestamps son segundos absolutos desde el inicio del video completo:\n\n"
        f"{payload['transcript_lines']}"
        f"{dirty_note}\n\n"
        f"Devolvé hasta {payload.get('target_clips', 12)} momentos con este formato JSON:\n"
        '{"clips": [{"start": float, "end": float, "score": 0-100, "reason": str, '
        '"title": str, "hook": str}]}'
    )
    return system, user


def build_rank_prompt(payload: dict) -> tuple[str, str]:
    """Pasada 2 (rank+refine): juzga finalistas en una escala única, hook-first."""
    system = (
        "Sos un editor EXIGENTE de shorts educativos en español. Recibís una lista de clips "
        "finalistas con su transcripción completa. Juzgalos cabeza a cabeza en UNA escala "
        "comparable. El clip debe ABRIR en el hook (engancha en los primeros segundos) y CERRAR "
        "en un remate. Sé duro. Respondé SOLO JSON válido."
    )
    few_shot = payload.get("few_shot") or ""
    few_shot_block = f"\n\n{few_shot}\n" if few_shot else ""
    user = (
        "Clips finalistas:\n\n"
        f"{payload['clips_block']}"
        f"{few_shot_block}\n"
        "Reglas estrictas:\n"
        "- Devolvé UN entry por cada clip listado (mismo id).\n"
        "- Los timestamps start/end deben ser segundos del transcript dado (no inventar).\n"
        "- Los clips NO deben solaparse entre si.\n"
        "- Cada clip debe durar entre min y max segundos.\n\n"
        "Para cada clip devolvé las sub-scores 0-100 y los cortes hook-first. Formato JSON:\n"
        '{"clips": [{"id": str, "hook_strength": 0-100, "self_contained": 0-100, '
        '"takeaway_clarity": 0-100, "payoff": 0-100, "start": float, "end": float, '
        '"title": str, "hook": str, "reason": str}]}\n'
        f"Duración objetivo: {int(payload.get('min_duration', 15))}-"
        f"{int(payload.get('max_duration', 60))} s."
    )
    return system, user


def build_translate_prompt(payload: dict) -> tuple[str, str]:
    system = "Traducí del español al inglés de forma natural y concisa. Respondé SOLO JSON válido."
    user = (
        "Traducí cada item conservando el índice:\n"
        f"{json.dumps(payload['items'], ensure_ascii=False)}\n\n"
        'Formato: {"translations": [{"i": int, "text": str}]}'
    )
    return system, user


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


_PROMPTS = {
    "score_moments": build_scan_prompt,
    "rank_moments": build_rank_prompt,
    "translate": build_translate_prompt,
}


def model_for_task(task: str) -> str:
    """Resolve the model for a task: cheap scan tier vs better rank tier."""
    if task == "score_moments":
        return settings.scan_model
    if task == "rank_moments":
        return settings.rank_model
    return settings.llm_model


class TaskRouter(Protocol):
    def run(self, task: str, payload: dict) -> dict: ...


class OllamaRouter:
    """LLM local vía Ollama (API nativa, sin dependencias externas)."""

    def __init__(self) -> None:
        self.model = settings.llm_model
        self.host = settings.ollama_host.rstrip("/")

    def run(self, task: str, payload: dict) -> dict:
        if task not in _PROMPTS:
            raise ValueError(f"Tarea no soportada: {task}")
        system, user = _PROMPTS[task](payload)
        body = json.dumps({
            "model": model_for_task(task),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.4},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return _extract_json(data["message"]["content"])


class OpenCodeRouter:
    """Backend que reutiliza la suscripción vía el CLI `opencode run`.

    Permite usar modelos de OpenCode Go (p.ej. opencode-go/deepseek-v4-flash) sin API key
    propia. Corre en un dir temporal vacío y con --pure para evitar que opencode indexe el
    proyecto o cargue plugins/contexto (lo que lo vuelve lento o lo cuelga).
    """

    def __init__(self) -> None:
        self.model = settings.llm_model
        self.timeout = settings.opencode_timeout
        self.bin = shutil.which("opencode") or "opencode"

    def run(self, task: str, payload: dict) -> dict:
        if task not in _PROMPTS:
            raise ValueError(f"Tarea no soportada: {task}")
        system, user = _PROMPTS[task](payload)
        prompt = f"{system}\n\n{user}"
        with tempfile.TemporaryDirectory() as td:
            pf = Path(td) / "prompt.md"
            pf.write_text(prompt, encoding="utf-8")
            # El mensaje va ANTES de -f: --file es un flag tipo array (greedy) y si va
            # último se comería el texto del mensaje como si fuera otra ruta de archivo.
            cmd = [
                self.bin, "run", "-m", model_for_task(task), "--pure",
                "Segui estrictamente las instrucciones del archivo adjunto. "
                "Responde SOLO con JSON valido, sin markdown ni texto extra.",
                "-f", str(pf),
            ]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                stdin=subprocess.DEVNULL,
                cwd=td,
                timeout=self.timeout,
            )
        if proc.returncode != 0:
            raise RuntimeError(f"opencode run falló: {(proc.stderr or '')[-1500:]}")
        return _extract_json(proc.stdout)


class ClaudeRouter:
    """Backend basado en la API de Anthropic."""

    def __init__(self) -> None:
        self.model = settings.llm_model
        self.api_key = settings.anthropic_api_key

    def _client(self):
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("Instalá el extra LLM: pip install -e .[llm]") from e
        if not self.api_key:
            raise RuntimeError("Falta ANTHROPIC_API_KEY en el entorno/.env")
        return anthropic.Anthropic(api_key=self.api_key)

    def run(self, task: str, payload: dict) -> dict:
        if task not in _PROMPTS:
            raise ValueError(f"Tarea no soportada: {task}")
        system, user = _PROMPTS[task](payload)
        client = self._client()
        msg = client.messages.create(
            model=model_for_task(task),
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        return _extract_json(text)


def get_router() -> TaskRouter:
    provider = settings.llm_provider
    if provider == "ollama":
        return OllamaRouter()
    if provider == "opencode":
        return OpenCodeRouter()
    if provider == "anthropic":
        return ClaudeRouter()
    raise ValueError(f"Proveedor LLM no soportado: {provider}")
