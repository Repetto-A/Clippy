# Clippy (Video Clipper)

Pipeline local-first (Python) que toma los crudos de tus streams/capacitaciones, detecta
los momentos más interesantes, recorta los clips, los reencuadra a vertical (9:16) y
horizontal (16:9), y los subtitula automáticamente con estilo karaoke.

Repositorio: [github.com/Repetto-A/Clippy](https://github.com/Repetto-A/Clippy)

Pensado para grabaciones tipo Google Meet con **slide compartida + webcam**, contenido
educativo en español, con **revisión humana** antes del render final.

## Cómo funciona (pipeline por etapas)

```
ingest -> transcribe -> signals -> propose -> [review humano] -> render
```

Cada etapa lee/escribe artefactos en `work/<nombre-del-crudo>/`, así que podés re-correr
cualquier etapa sin rehacer todo.

## Requisitos

- Python 3.11+
- **ffmpeg** en el PATH (con `h264_nvenc` para acelerar el render en GPU NVIDIA)
- **opencode** en el PATH (opcional, para scoring con tu suscripción OpenCode Go)
- Para transcripción: GPU NVIDIA + `pip install -e ".[asr]"` (faster-whisper + CUDA)
- Para UI web: `pip install -e ".[api]"`

## Instalación

```bash
pip install -e ".[asr,api,dev]"   # recomendado: ASR + UI + tests
pip install -e ".[face]"          # opcional: detección de cara para webcam dinámica
pip install -e ".[llm]"           # opcional: API Anthropic
```

En Windows, para CUDA con faster-whisper:

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

Configurá copiando `.env.example` a `.env`.

## UI web (revisión y edición)

```bash
python -m video_clipper.cli serve
# → http://127.0.0.1:8765
```

- Arrastrá un `.mp4` → procesa en background (`work/.../status.json`)
- Revisá clips, ajustá in/out, editá subtítulos palabra por palabra
- Aprobá y renderizá; descargá los `.mp4` finales desde la UI

## CLI

```bash
# Pipeline con tracking de progreso (status.json)
python -m video_clipper.cli process "C:/ruta/al/crudo.mp4"

# Ver estado
python -m video_clipper.cli status "C:/ruta/al/crudo.mp4"

# Revisar y curar
python -m video_clipper.cli review "C:/ruta/al/crudo.mp4"
python -m video_clipper.cli approve "C:/ruta/al/crudo.mp4" <clip_id>
python -m video_clipper.cli set-range "C:/ruta/al/crudo.mp4" <clip_id> 12.0 45.0
python -m video_clipper.cli show-words "C:/ruta/al/crudo.mp4" <clip_id>
python -m video_clipper.cli edit-word "C:/ruta/al/crudo.mp4" <clip_id> 3 "delegar"

# Renderizar aprobados
python -m video_clipper.cli render "C:/ruta/al/crudo.mp4"
```

Etapas sueltas: `ingest`, `transcribe`, `signals`, `propose`.

## Scoring de momentos (LLM)

Default: **OpenCode Go** (tu suscripción, sin API key propia).

```env
VC_SCORER=llm
VC_LLM_PROVIDER=opencode
VC_LLM_MODEL=opencode-go/deepseek-v4-flash   # rápido; deepseek-v4-pro = mejor calidad
VC_OPENCODE_TIMEOUT=600
```

Alternativas:

| Provider | Cuándo usar |
|----------|-------------|
| `opencode` | Default. Usa `opencode run` con modelos `opencode-go/*` |
| `ollama` | 100% local en GPU (`qwen2.5:7b-instruct`, etc.) |
| `anthropic` | Máxima calidad editorial (`ANTHROPIC_API_KEY` + extra `[llm]`) |
| `heuristic` | Baseline sin LLM (`VC_SCORER=heuristic`) |

### Videos largos (>30 min)

El transcript se parte en chunks automáticamente para no exceder el contexto del LLM:

```env
VC_LLM_CHUNK_CHARS=12000      # tamaño máximo por chunk
VC_LLM_CLIPS_PER_CHUNK=6    # clips a pedir por chunk
VC_TARGET_CLIPS=12          # cupo final tras dedupe
VC_WHISPER_CHUNK_SECONDS=600  # trozos ASR para videos largos (Windows)
```

## Subtítulos

Default: **karaoke** (Montserrat, palabra resaltada). Para Shorts/Reels:

```env
VC_CAPTION_STYLE=social   # Anton bold, lineas cortas
VC_CAPTION_STYLE=both     # genera karaoke + social (9x16 y 16x9 cada uno)
VC_CAPTION_SOCIAL_WORDS=5
```

Los renders quedan en `work/<job>/clips/<clip_id>/` con `.ass` y `.mp4` por variante.

En la **UI web**, dentro de cada job, panel **Opciones de export**: estilo de subtítulos, palabras por línea (social), vertical/horizontal. Se guarda en `render_prefs.json` por job (defaults desde `.env` si no tocás nada).

## Resume del pipeline

`process` y **Reintentar** en la UI saltan etapas cuyos artefactos ya existen
(`audio.wav`, `transcript.json`, `signals.json`, `candidates.json`). Útil si falló en
propose tras transcribir una clase larga.

## Evaluación de calidad (M1)

Aprobar/rechazar clips alimenta `labels.json`. Medí precision@N con:

```bash
python -m video_clipper.cli eval "C:/ruta/al/crudo.mp4"
```

En la UI: botón **Evaluar calidad** (requiere al menos un approve/reject).

Guía: `docs/M1-baseline.md`. El motor M2 (scan→rank→refine) debe superar ese baseline.

## Diseño

Ver `docs/specs/2026-06-18-video-clipper-design.md`.

## Decisiones y roadmap

El proyecto avanza mediante un loop autónomo documentado:

- **Carta de autonomía** — cómo se decide sin revisión constante, guardrails y done-when:
  `docs/autonomy-charter.md`.
- **ADRs** — decisiones de arquitectura/producto (contexto → decisión → consecuencias):
  `docs/adr/README.md`.
- **Roadmap** — reps priorizados con done-when: `docs/roadmap/2026-Q3.md`.
- **Specs / plans** — diseño detallado por subsistema: `docs/specs/`, `docs/plans/`.
