# Architecture Decision Records — Clippy

Registro de decisiones de arquitectura y producto. Cada ADR captura **contexto → decisión →
consecuencias**. Ver `../autonomy-charter.md` para cómo el agente decide de forma autónoma.

## Índice

| ADR | Título | Estado | Fecha |
| --- | ------ | ------ | ----- |
| [0001](0001-local-first-pipeline.md) | Pipeline local-first modular con human-in-the-loop | Accepted | 2026-06-18 |
| [0002](0002-two-pass-selection-engine.md) | Motor de selección en dos pasadas (scan → rank) | Accepted | 2026-06-20 |
| [0003](0003-human-eval-loop.md) | Loop de evaluación con golden set (M1) | Accepted | 2026-06-20 |
| [0004](0004-per-job-preferences.md) | Preferencias de propuesta/render por job | Accepted | 2026-07-02 |
| [0005](0005-external-performance-loop.md) | Loop de performance externo (métricas de plataforma → rúbrica) | Accepted | 2026-07-03 |
| [0006](0006-semantic-timeline-ui.md) | Timeline semántico en el editor (heatmap + navegación) | Accepted | 2026-07-03 |
| [0007](0007-multi-profile-platform.md) | Perfiles de contenido (training / podcast / stream) | Accepted | 2026-07-03 |

## Estados

- **Proposed** — decidido de forma autónoma o en discusión; pendiente de auditoría de Ale.
- **Accepted** — vigente, implementándose o implementado.
- **Deprecated** — ya no aplica.
- **Superseded** — reemplazado por otro ADR (se indica cuál).
- **Rejected** — considerado y descartado (se conserva por su valor).

## Crear un ADR

1. Copiar `template.md` a `NNNN-titulo-con-guiones.md` (N correlativo).
2. Completar. Si es una decisión autónoma reversible, arranca en `Proposed`.
3. Agregar la fila al índice de arriba.
4. Al implementarse y validarse, pasar a `Accepted`.

## Regla

**No se editan ADRs `Accepted`.** Si una decisión cambia, se escribe un ADR nuevo que
`Supersedes` al anterior.
