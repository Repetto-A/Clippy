# ADR-0003: Loop de evaluación con golden set (M1)

**Estado:** Accepted
**Fecha:** 2026-06-20
**Decisor:** Ale (+ agente)

## Contexto

Sin una vara objetiva, cada cambio de prompt/rúbrica se juzgaba "a ojo". Necesitamos medir si
un cambio del motor mejora o empeora la selección de clips.

## Drivers de decisión

- El juicio editorial de Ale es la fuente de verdad.
- Los cambios de motor deben ser comparables entre sí.
- El golden set debe alimentar también el few-shot del ranker (doble uso).

## Decisión

Introducir un **golden set** (`labels.json`) con juicios humanos (aprobado/rechazado + razón +
rango) por clase, y un `eval_report.json` que compara la salida del pipeline contra ese
baseline (`precision@N`, falsos positivos por razón). El golden set se reutiliza como
**few-shot** para el ranker.

## Consecuencias

**Positivas:** mejoras del motor verificables; regresiones detectables; few-shot gratis.

**Negativas:** requiere trabajo humano de etiquetado inicial por clase.

**Riesgos:** sin etiquetado, el motor no tiene vara → los cambios se marcan "no validados".

## Done-when

- [x] `labels.json` y `eval_report.json` definidos y wired en la API/UI.
- [x] Comando/`eval` compara pipeline vs baseline.
- [ ] Al menos una clase completamente etiquetada por Ale (baseline real).

## Relacionados

- `../M1-baseline.md`, `../plans/2026-06-20-m1-eval-loop.md`
- ADR-0002 (motor que este loop valida)
