# M1 — Golden set y baseline de calidad

## Flujo

1. Procesá una clase (`process` o UI upload).
2. Revisá clips en la UI o CLI.
3. **Aprobá** clips buenos; **rechazá** malos eligiendo una razón:
   - `bad_hook` — apertura débil
   - `not_self_contained` — necesita contexto previo
   - `bad_cut` — in/out mal puestos
   - `dirty_screen` — Meet/browser visible
   - `weak_topic` — takeaway poco claro
4. Las decisiones se guardan en `work/<clase>/labels.json` (golden set).
5. Corré eval:
   ```bash
   python -m video_clipper.cli eval "ruta/al/crudo.mp4"
   ```
   O botón **Evaluar calidad** en la UI.

## Métricas (`eval_report.json`)

- **precision@N**: de los top-N clips propuestos, cuántos solapan un rango aprobado (IoU >= umbral).
- **recall**: cuántos rangos aprobados quedaron cubiertos por el top-N.
- **false_positives_by_reason**: solapes con rangos rechazados por razón.

Config: `VC_EVAL_IOU_THRESHOLD` (default 0.5), `VC_TARGET_CLIPS` (N).

## M2 done-when

Después de cambios al motor (scan→rank→refine), volvé a correr `propose` + `eval` y compará
`precision@N` contra el baseline guardado. El nuevo motor debe superarlo sin aumentar falsos
positivos por razón.
