# ADR-0004: Preferencias de propuesta/render por job

**Estado:** Accepted
**Fecha:** 2026-07-02
**Decisor:** agente autónomo (audita: Ale)

## Contexto

Distintas clases necesitan distintos parámetros (nº de clips, duración, estilo de subtítulos,
formatos de salida). Hardcodear config global obligaba a editar `.env` y re-correr todo.

## Drivers de decisión

- Ale quiere ajustar sin tocar código ni variables de entorno.
- Los ajustes deben persistir por job y ser reversibles.
- No romper defaults existentes.

## Decisión

Dos artefactos por job — `propose_prefs.json` (target clips, min/max duración, rank finalists)
y `render_prefs.json` (estilo de caption, words por línea social, formatos vertical/horizontal)
— editables desde la UI vía endpoints `GET/PATCH`. Defaults cargados desde `config.settings`,
así que un job sin prefs se comporta como antes.

## Consecuencias

**Positivas:** control por-job sin código; reversible; base para "re-proponer/re-render".

**Negativas:** más superficie de API/UI y más artefactos que versionar (aditivos).

## Done-when

- [x] Modelos `ProposePrefs`/`RenderPrefs` + persistencia en `storage`.
- [x] Endpoints `GET/PATCH` y paneles en la UI.
- [x] Defaults = comportamiento previo (back-compat).

## Relacionados

- ADR-0001 (artefactos JSON por etapa)
