# ADR-0001: Pipeline local-first modular con human-in-the-loop

**Estado:** Accepted
**Fecha:** 2026-06-18
**Decisor:** Ale (+ agente)

## Contexto

Ale necesita generar clips cortos a partir de clases/streams largos (español, layout slide +
webcam, ~1-3 videos/semana). Tiene una RTX 5060 local. Objetivos: costo ~0, privacidad,
control total, y calidad publicable. Referencia conceptual: Opus Clip.

## Drivers de decisión

- Volumen bajo (no hace falta escala cloud).
- Privacidad del material (clases privadas).
- GPU local disponible (NVENC + faster-whisper viables).
- Ale quiere revisar antes de publicar (no full-auto).

## Decisión

Pipeline **modular por etapas** (ingest → transcribe → signals → propose → refine → render),
ejecutado **localmente**, con artefactos JSON persistidos por etapa y un **paso de revisión
humana** obligatorio antes del render/publicación. La I/O de LLM vive detrás de un `TaskRouter`
(Protocol) para poder testear sin red y cambiar backend.

## Consecuencias

**Positivas:** costo casi nulo, privacidad, etapas resumibles, testeable con fakes, extensible.

**Negativas:** dependencia del hardware local; procesamiento no paralelizable a gran escala.

**Riesgos:** videos muy largos rompen ASR (mitigado con chunking de audio — ver M1/notas).

## Done-when

- [x] Pipeline corre end-to-end en una clase real.
- [x] Artefactos JSON por etapa; etapas resumibles.
- [x] Router abstrae LLM; tests sin red.

## Relacionados

- Spec: `../specs/2026-06-18-video-clipper-design.md`
