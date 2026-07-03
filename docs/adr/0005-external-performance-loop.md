# ADR-0005: Loop de performance externo (métricas de plataforma → rúbrica)

**Estado:** Accepted
**Fecha:** 2026-07-03
**Decisor:** agente autónomo (audita: Ale)

## Contexto

Hoy la calidad se mide solo con el juicio previo de Ale (golden set, ADR-0003). Pero el juez
final de un clip corto es **la plataforma**: retención, views, saves, shares. Cerrar ese loop
convierte a Clippy de "generador" en "sistema que aprende qué funciona" — el pilar *editorial
medible* llevado a su conclusión.

## Drivers de decisión

- El golden set captura gusto, no rendimiento real.
- YouTube/TikTok/IG exponen métricas por video.
- Queremos que la rúbrica del ranker se ajuste con evidencia, no intuición.
- Local-first: la ingesta de métricas debe ser opcional y no bloquear el flujo.

## Opciones consideradas

- **Manual CSV import:** Ale pega métricas; simple, sin OAuth. Bajo esfuerzo, dato tardío.
- **API de plataforma (YouTube Data API):** automático pero requiere OAuth/credenciales.
- **Híbrido (elegida):** empezar con import manual (CSV/JSON) mapeado a `clip_id`, dejar la
  interfaz lista para un fetcher automático detrás de un flag opt-in.

## Decisión

Crear un artefacto `performance.json` por clip publicado (views, retención, saves, source,
fecha) y un comando/endpoint para importarlo. Un análisis correlaciona sub-scores de rúbrica
vs performance real y **sugiere** (no aplica solo) ajustes de `rubric_weights`. La aplicación
automática de pesos queda detrás de flag y requiere OK de Ale (toca el motor → ADR-0003).

## Consecuencias

**Positivas:** el sistema aprende de resultados reales; cierra el loop producto↔motor.

**Negativas:** requiere que Ale publique y traiga datos; muestra chica al inicio (ruido).

**Riesgos:** sobreajuste a pocos datos → los ajustes son *sugerencias*, nunca automáticos sin
validación vs baseline.

## Done-when

- [ ] `performance.json` schema + import (CSV/JSON) mapeando a `clip_id`.
- [ ] Reporte de correlación sub-score ↔ métrica en la UI.
- [ ] Sugerencia de pesos documentada; aplicación detrás de flag opt-in.

## Relacionados

- ADR-0002 (rúbrica), ADR-0003 (eval loop)
