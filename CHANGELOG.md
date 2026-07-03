# Changelog

## 2026-07-03 — Home de producto + onboarding (inbox)

### Inbox como home
- Hero sobrio con identidad y una línea de qué hace Clippy (sin CTA/pricing; es tool local).
- Bloque "Cómo funciona" (4 pasos: subir → procesar → revisar → renderizar) que aparece
  solo cuando no hay trabajos, como onboarding.
- La sección "Trabajos" se oculta cuando está vacía (se evita el estado vacío redundante).

## 2026-07-03 — Toasts tipados + dropzone accesible

### Toasts
- Tipos `success` / `error` / `info` con icono y color (borde izquierdo distintivo).
- Errores usan `aria-live="assertive"` y duran más (5s vs 3s).
- Timer único (se evita el bug de timeouts acumulados) + click para cerrar.

### Accesibilidad
- Dropzone ahora es `role="button"` enfocable, con soporte de Enter/Espacio y focus-ring.

## 2026-07-03 — Timeline highlight + deep-linking + i18n numbers

### Timeline semántico
- El segmento del clip seleccionado se resalta (`.clip-seg.active`) sincronizado con la grilla.
- Hover sobre un segmento selecciona el clip en la grilla; `aria-label` con título y rango temporal.

### Deep-linking (URL state)
- `job`, `clip`, `filter` y `sort` se reflejan en query params (`syncUrl`/`routeFromUrl`).
- Soporte de back/forward del navegador (`popstate`) y restauración al recargar.

### Números localizados
- Helpers `fmtPct`/`fmtNum` con `Intl.NumberFormat` para porcentajes (precisión, recall, zoom)
  y correlaciones/pesos, respetando el locale del usuario.

## 2026-07-03 — A11y + guidelines audit (Vercel Web Interface Guidelines + WCAG)

### Accesibilidad
- `aria-label` en botones icon-only (play, step, zoom, overlay) + glifos `aria-hidden`.
- `aria-label` en el select de razon de rechazo.
- `color-scheme: dark` en root (scrollbars/inputs nativos correctos).
- `touch-action: manipulation` en interactivos (sin delay de doble-tap).

### Feedback / estados
- Helper `withBusy`: botones async (Render, Re-proponer, Evaluar, Importar) se
  deshabilitan y muestran "...accion..." durante la request.

### Tipografia
- `text-wrap: balance` en headings y titulos de estado vacio; `pretty` en descripciones.
- `tabular-nums` en lecturas de tiempo/zoom restantes.

## 2026-07-03 — UI polish (review flow + taste)

### Producto / UI
- Barra de progreso de revisión ("N de M revisados" + aprobados/rechazados/pendientes).
- Filtros de candidatos (Todos/Pendientes/Aprobados/Rechazados) con contador por estado.
- Orden de candidatos: cronológico o mejor puntaje primero.
- Navegación J/K y atajos A/R ahora respetan el filtro activo.
- Iconos SVG limpios en estados vacíos (reemplazan emojis, alineado con la carta de autonomia).

## 2026-07-03 — R3 export polish

### Producto / UI
- Nombres de descarga legibles (`job-titulo-formato.mp4`) en API y UI.
- Preview de renders con tabs por formato cuando hay multiples salidas.
- Badge `N render` en cards de clips aprobados/renderizados.

## 2026-07-03 — Loop autonomo (R1, R2, R4, R6)

### Documentacion
- Carta de autonomia, ADRs 0001-0007, roadmap Q3.

### Producto / UI
- **R2** Explicabilidad: hook, razon y rubrica en cards y editor.
- **R1** Timeline semantico del job (heatmap + clips + dirty ranges).
- **R4** Import manual de performance (JSON/CSV) + reporte de correlacion.
- **R6** Perfil de contenido `training` formalizado; defaults por perfil.

### API
- `GET/PATCH /api/jobs/{id}/profile`
- `GET /api/jobs/{id}/timeline`
- `GET/POST /api/jobs/{id}/performance`
- `GET /api/jobs/{id}/performance/report`

### Pendiente (requiere Ale)
- **R0** Etiquetar clase para baseline M1 real.
- **RC1** Validacion E2E clase 93 min (si hay video local disponible).
