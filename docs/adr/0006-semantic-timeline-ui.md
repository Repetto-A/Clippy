# ADR-0006: Timeline semántico en el editor (heatmap + navegación)

**Estado:** Accepted
**Fecha:** 2026-07-03
**Decisor:** agente autónomo (audita: Ale)

## Contexto

El editor actual revisa clips ya propuestos, pero Ale no tiene una vista de **dónde** en la
clase de 93 min están los momentos fuertes ni por qué se eligieron unos y no otros. Los
clippers de referencia (heatmap-clipper) muestran un mapa de calor del engagement/energía.

## Drivers de decisión

- Confianza: ver *por qué* el motor eligió un tramo reduce revisiones a ciegas.
- Descubrimiento: Ale podría querer un clip que el motor no propuso.
- Ya tenemos las señales (silences, sub-scores, dirty_ranges) — falta exponerlas.

## Opciones consideradas

- **Solo lista de clips (hoy):** simple pero opaco.
- **Timeline con heatmap (elegida):** barra temporal de la clase con capas de señal
  (energía/score de scan, silencios, dirty ranges) y marcadores de clips propuestos; click =
  saltar/crear candidato.

## Decisión

Agregar un **timeline semántico** al editor: renderiza la duración completa con un heatmap
derivado de las señales existentes (scan scores + energía + silencios), superpone los clips
propuestos, marca los `dirty_ranges`, y permite navegar/seed de un candidato manual. Es
aditivo (nuevo panel, no cambia el modelo de datos existente salvo un endpoint que sirva las
señales agregadas).

## Consecuencias

**Positivas:** transparencia del motor, descubrimiento de clips, revisión más rápida.

**Negativas:** trabajo de front no trivial (canvas/SVG); endpoint de señales agregadas.

**Riesgos:** performance con clases largas → downsamplear señales para el render.

## Done-when

- [ ] Endpoint que sirve señales agregadas por job (downsampleadas).
- [ ] Panel timeline con heatmap + clips + dirty ranges, navegable.
- [ ] Click en timeline salta el player; opción de seed de candidato manual.

## Relacionados

- ADR-0001 (señales/artefactos), ADR-0004 (UI por-job)
