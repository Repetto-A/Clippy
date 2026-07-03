# ADR-0007: Perfiles de contenido (training / podcast / stream)

**Estado:** Accepted
**Fecha:** 2026-07-03
**Decisor:** agente autónomo (audita: Ale)

## Contexto

Clippy nació para clases (slide + webcam). Ale ya anticipó un **podcast clipper** a futuro.
Podcast, stream y clase tienen layouts, rúbricas y estilos de subtítulo distintos. Sin una
abstracción, cada tipo forzaría forks o `if` dispersos.

## Drivers de decisión

- Evitar reescrituras al sumar un tipo nuevo (ADR-0004 ya per-job).
- Reutilizar el 90% del pipeline; variar solo layout/rúbrica/estilo.
- Mantener local-first y el motor de dos pasadas.

## Opciones consideradas

- **Fork por tipo:** duplica código, diverge.
- **Flags sueltos:** entropía creciente.
- **Perfil declarativo (elegida):** un `profile` (ej. `training`, `podcast`, `stream`) que
  agrupa defaults de reframe (webcam-detect vs speaker-switch), rúbrica, estilo de caption y
  duraciones. Los `propose_prefs`/`render_prefs` por-job siguen pudiendo sobrescribir.

## Decisión

Introducir un concepto de **perfil de contenido**: un preset nombrado que fija los defaults de
las etapas sensibles al formato. `training` es el actual (webcam-detect, rúbrica pedagógica).
`podcast`/`stream` se agregan como presets nuevos sin tocar el core. El perfil se elige al
crear el job y alimenta los defaults de prefs (ADR-0004).

## Consecuencias

**Positivas:** escalar a nuevos formatos sin reescribir; onboarding claro por caso de uso.

**Negativas:** capa de configuración extra; hay que definir bien qué varía por perfil.

**Riesgos:** sobre-abstraer antes de tener el 2º caso real → implementar recién cuando el
podcast clipper esté pedido; por ahora solo formalizar `training` como perfil default.

## Done-when

- [ ] Concepto `profile` con `training` como default (sin cambio de comportamiento).
- [ ] Perfil elegible al crear job; alimenta defaults de prefs.
- [ ] Documentado qué campos varía cada perfil (reframe/rúbrica/caption/duración).

## Relacionados

- ADR-0004 (prefs por-job), ADR-0002 (rúbrica), ADR-0001 (reframe/webcam)
