# ADR-0002: Motor de selección en dos pasadas (scan → rank)

**Estado:** Accepted
**Fecha:** 2026-06-20
**Decisor:** Ale (+ agente)

## Contexto

Un solo pase de LLM para elegir clips daba baja calidad: bordes flojos, clips que se solapan,
hooks débiles y costo alto si se usaba un modelo caro sobre todo el transcript.

## Drivers de decisión

- Necesitamos alta *recall* barata + juicio fino caro solo en finalistas.
- Los clips deben empezar en el hook y no solaparse.
- Calidad debe ser comparable en una escala (rúbrica).

## Opciones consideradas

- **Un pase caro sobre todo:** costoso y aún así bordes flojos.
- **Dos pasadas (elegida):** scan barato (recall) → rank caro (rúbrica + refine).

## Decisión

Motor en **dos pasadas**:
- **Scan** (modelo barato, alto recall) sobre chunks con límites en silencios + overlap;
  recibe `dirty_ranges` para evitar Meet UI/tabs.
- **Rank** (modelo mejor) juzga los top-N finalistas en una rúbrica (`hook_strength`,
  `self_contained`, `takeaway_clarity`, `payoff`), fija start en el hook, prohíbe solapamiento,
  con retry/fallback y few-shot del golden set.

## Consecuencias

**Positivas:** mejor calidad de borde/hook, costo controlado, escala de score comparable.

**Negativas:** más piezas (ranker, rubric, few_shot); dos prompts que mantener.

**Riesgos:** el rank LLM puede omitir clips (mitigado con fallback que preserva score de scan).

## Done-when

- [x] `scan → rank → refine` encadenado en `stage_propose`.
- [x] Rúbrica combina sub-scores; hook-first snap.
- [ ] `precision@N` supera baseline M1 en una clase etiquetada (pendiente etiquetado de Ale).

## Relacionados

- Spec: `../specs/2026-06-20-clip-selection-quality-design.md`
- Plan: `../plans/2026-06-20-m2-selection-engine.md`
- ADR-0003 (eval loop que lo valida)
