# Changelog

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
