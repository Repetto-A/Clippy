# Clippy — Carta de Autonomía

- **Fecha:** 2026-07-03
- **Estado:** Activo
- **Propósito:** Permitir que el agente avance en la dirección del producto **sin revisión
  constante** de Ale, manteniendo calidad, reversibilidad y trazabilidad.

Este documento es el **contrato de trabajo autónomo**. Define qué puede decidir el agente
solo, qué requiere a Ale, cómo se documenta cada decisión y cómo se elige el próximo paso.

---

## 1. Norte del producto

**Clippy convierte grabaciones largas (clases/streams en español, slide + webcam) en clips
cortos publicables, con revisión humana mínima y calidad medible.**

No competimos con clippers de YouTube genéricos. El diferencial es:
1. **Local-first** (RTX, costo ~0, privacidad).
2. **Editorial medible** (golden set + eval, no "confiá en el prompt").
3. **Contexto educativo ES** (slide+webcam, dirty screen, rúbrica pedagógica).

Cualquier decisión autónoma debe **reforzar** uno de estos tres pilares o reducir la fricción
de la acción central: **revisar → aprobar/rechazar → renderizar**.

---

## 2. Principios de decisión

Derivados de los skills `reducing-entropy`, `taste-skill` y `game-changing-features`:

1. **No reescribir el pipeline** — insertar/modificar quirúrgicamente, respetar la separación
   de responsabilidades (screaming architecture).
2. **Data sobre abstracciones** — preferir artefactos JSON simples y funciones puras sobre
   capas de indirección.
3. **Medir antes de mover el cerebro** — todo cambio al motor de selección se valida contra
   el baseline (`eval_report.json`), no a ojo.
4. **Reversibilidad primero** — cambios detrás de flags/config; nada destructivo sin pedirlo.
5. **Local-first innegociable** — no introducir dependencias cloud obligatorias.
6. **Taste** — un solo acento, anti-card en el editor, mono para números, estados completos
   (loading/empty/error), sin emojis como UI.
7. **Reps chicos** — shippear la versión más chica que aporte valor y aprender (ship-learn-next).

---

## 3. Derechos de decisión

### El agente PUEDE decidir y ejecutar solo

- Refactors internos sin cambio de comportamiento observable.
- Nuevos flags/config con **default = comportamiento actual**.
- Mejoras de UI/UX que no cambian el modelo de datos (taste, a11y, estados, atajos).
- Prompts nuevos o ajustes de prompt **detrás de un flag** o validados contra baseline.
- Tests, docs, fixes de bugs, mejoras de performance.
- Endpoints nuevos que no rompen los existentes.
- Nuevos artefactos JSON por job (aditivos, con defaults).
- Elegir naming, estructura de archivos, orden de tareas.

### El agente DEBE pedir a Ale antes de

- Cambios destructivos o irreversibles (borrar artefactos, migraciones sin vuelta atrás).
- Introducir dependencias **cloud obligatorias** o servicios pagos.
- `git push --force`, reescritura de historia, tocar `git config`.
- Cambiar el norte del producto o descartar uno de los tres pilares.
- Subir/publicar contenido a plataformas externas de forma automática.
- Exponer datos privados (transcripts, clips) fuera de `work/`.
- Cualquier cosa que gaste dinero real (APIs pagas) sin que esté ya configurado por Ale.

### Zona gris → decidir y documentar

Si no está claro pero es reversible y de bajo riesgo: **decidir, ejecutar, y registrar la
decisión en un ADR con estado `Proposed`** para que Ale la audite asincrónico. Si Ale no
objeta, pasa a `Accepted`.

---

## 4. El loop autónomo (Ship → Learn → Next)

```
1. PICK   elegí el próximo rep del roadmap (docs/roadmap/) por prioridad y done-when claro
2. SPEC   si el cambio es no trivial, escribí/actualizá un ADR o spec antes de codear
3. SHIP   implementá con TDD (red → green), tests verdes, lint limpio
4. VERIFY chequeá el done-when del rep; si toca el motor, corré eval vs baseline
5. RECORD actualizá el ADR (Proposed→Accepted), el roadmap (rep done), y el CHANGELOG
6. NEXT   dejá una nota de handoff con estado + próximo rep sugerido
```

Regla: **nunca terminar un turno con tests rojos, lint sucio, o un rep a medias sin nota de
handoff.**

---

## 5. Definición de "hecho" (Done-when global)

Un cambio está hecho cuando:
- [ ] Los tests pasan (`./.venv-asr/Scripts/python.exe -m pytest -q`).
- [ ] No hay lints nuevos en archivos tocados.
- [ ] El comportamiento por defecto no cambió (o el cambio está documentado en un ADR).
- [ ] Si toca selección/motor: `precision@N` no baja vs `eval_report.json` baseline y los
      falsos positivos por razón no aumentan.
- [ ] El doc correspondiente (ADR/roadmap/README) quedó actualizado.
- [ ] Hay una nota de handoff con el próximo paso.

---

## 6. Guardrails de calidad medible

- El **baseline M1** es la vara. Sin baseline etiquetado, los cambios de motor se marcan como
  "no validados" y no se consideran mejoras hasta que Ale etiquete una clase.
- Cambios de prompt/rúbrica: correr eval antes/después y anotar el delta en el ADR.
- Si un cambio mejora una métrica pero empeora otra, **no** se acepta solo: se documenta el
  trade-off y se marca `Proposed` para que Ale decida.

---

## 7. Trazabilidad

Todo cambio significativo deja rastro en uno de:
- `docs/adr/NNNN-*.md` — decisiones de arquitectura/producto (ver `docs/adr/README.md`).
- `docs/roadmap/*.md` — qué se está construyendo y en qué orden.
- `docs/specs/*.md` — diseño detallado de un subsistema.
- `docs/plans/*.md` — plan de implementación por milestone (TDD, tareas).
- `CHANGELOG.md` — resumen legible por humano de lo shippeado.

Commits: mensajes descriptivos del *por qué*. Nunca commitear artefactos locales
(`work/`, `.pytest_tmp/`, `.playwright-cli/`).

---

## 8. Cuándo frenar y preguntar

Aunque el default es avanzar, frená y consultá si:
- Detectás que el norte del producto podría estar mal (ej. Ale usa Clippy distinto a lo asumido).
- Dos ADRs propuestos se contradicen y no hay forma reversible de elegir.
- Un rep requiere una decisión de negocio (precios, plataformas, marca).
- El costo (tiempo/tokens/dinero) de un rep se dispara respecto a lo estimado.

En esos casos: dejá el trabajo en un estado limpio, escribí la pregunta concreta con opciones,
y seguí con otro rep desbloqueado mientras tanto.
