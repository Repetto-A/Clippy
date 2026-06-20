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

def build_score_prompt(payload: dict) -> tuple[str, str]:
    system = (
        "Sos un editor experto de contenido corto educativo en español. "
        "Recibís la transcripción de una capacitación/stream con timestamps. "
        "Tu trabajo es detectar los momentos más clipeables: explicaciones auto-contenidas, "
        "insights, tips accionables, analogías potentes o preguntas/respuestas del Q&A. "
        "Cada clip debe tener sentido por sí solo y durar entre "
        f"{int(payload.get('min_duration', 15))} y {int(payload.get('max_duration', 60))} segundos. "
        "Respondé SOLO JSON válido."
    )
    user = (
        "Transcripción (cada línea: [start-end] texto). "
        "Los timestamps son segundos absolutos desde el inicio del video completo, "
        "no relativos al fragmento:\n\n"
        f"{payload['transcript_lines']}\n\n"
        f"Devolvé hasta {payload.get('target_clips', 12)} momentos con este formato JSON:\n"
        '{"clips": [{"start": float, "end": float, "score": 0-100, "reason": str, '
        '"title": str, "hook": str}]}'
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
    "score_moments": build_score_prompt,
    "translate": build_translate_prompt,
}


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
            "model": self.model,
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
                self.bin, "run", "-m", self.model, "--pure",
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
            model=self.model,
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
