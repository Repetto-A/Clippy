const API = "/api";
const ACTIVE = new Set([
  "queued", "ingesting", "transcribing", "signals", "proposing", "rendering",
]);

const NUDGE = 0.1;
const SEEK_STEP = 0.5;

const state = {
  view: "inbox",
  jobId: null,
  job: null,
  clip: null,
  candidates: [],
  selectedClipId: null,
  duration: 0,
  pollTimer: null,
  activeWord: -1,
  editingWord: -1,
  drag: null,
  editorBound: false,
  prefsBound: false,
  proposePrefsBound: false,
  profileBound: false,
  performanceBound: false,
  gridBound: false,
  timelineZoom: 1,
};

const $ = (id) => document.getElementById(id);

function fmtTime(sec) {
  sec = Math.max(0, sec || 0);
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function fmtTimePrecise(sec) {
  sec = Math.max(0, sec || 0);
  const m = Math.floor(sec / 60);
  const s = (sec % 60).toFixed(1).padStart(4, "0");
  return `${m}:${s}`;
}

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  const ann = $("status-announcer");
  if (ann) ann.textContent = msg;
  setTimeout(() => el.classList.add("hidden"), 3000);
}

async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

function enc(id) {
  return encodeURIComponent(id);
}

function showView(name) {
  state.view = name;
  $("view-inbox").classList.toggle("hidden", name !== "inbox");
  $("view-job").classList.toggle("hidden", name !== "job");
  $("view-editor").classList.toggle("hidden", name !== "editor");
  $("btn-back").classList.toggle("hidden", name === "inbox");
  if (name !== "editor") teardownEditor();
}

function teardownEditor() {
  const player = $("player");
  player.pause();
  player.removeAttribute("src");
  player.load();
  state.activeWord = -1;
  state.editingWord = -1;
  state.drag = null;
}

$("btn-back").onclick = () => {
  if (state.view === "editor") openJob(state.jobId);
  else showView("inbox");
};

async function loadJobs() {
  const jobs = await api("/jobs");
  const list = $("jobs-list");
  if (!jobs.length) {
    list.innerHTML = emptyState(
      "📂",
      "No hay trabajos todavía",
      "Arrastrá un .mp4 a la zona de arriba o hacé click para subir tu primer video.",
    );
    return;
  }
  list.innerHTML = jobs.map((j) => {
    const badgeCls = stageBadgeClass(j.stage);
    return `
      <article class="job-card" data-id="${escapeAttr(j.id)}" tabindex="0" role="button" aria-label="Abrir ${escapeAttr(j.name)}">
        <div class="job-card-head">
          <div>
            <div class="job-name">${escapeHtml(j.name)}</div>
            <div class="job-stage">${escapeHtml(j.message)}</div>
          </div>
          <div class="job-card-badges">
            <span class="status-badge ${badgeCls}">${stageLabel(j.stage)}</span>
            <span class="job-progress-pct">${Math.round(j.progress)}%</span>
          </div>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${j.progress}%"></div></div>
      </article>`;
  }).join("");

  list.querySelectorAll(".job-card").forEach((el) => {
    const open = () => openJob(el.dataset.id);
    el.onclick = open;
    el.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      }
    };
  });

  if (jobs.some((j) => ACTIVE.has(j.stage))) startPoll();
  else stopPoll();
}

function stageLabel(s) {
  const map = {
    queued: "En cola",
    ingesting: "Ingesta",
    transcribing: "Transcribiendo",
    signals: "Señales",
    proposing: "Detectando clips",
    ready_for_review: "Listo para revisar",
    rendering: "Renderizando",
    completed: "Completado",
    failed: "Error",
  };
  return map[s] || s;
}

function stageBadgeClass(s) {
  if (s === "failed") return "status-failed";
  if (s === "ready_for_review" || s === "completed") return "status-ready";
  if (ACTIVE.has(s)) return "status-working";
  return "status-neutral";
}

function statusLabel(s) {
  const map = {
    proposed: "Propuesto",
    approved: "Aprobado",
    rejected: "Rechazado",
    edited: "Editado",
  };
  return map[s] || s;
}

function statusBadgeClass(s) {
  if (s === "approved") return "badge-approved";
  if (s === "rejected") return "badge-rejected";
  if (s === "edited") return "badge-edited";
  return "badge-proposed";
}

function emptyState(icon, title, desc, { compact = false } = {}) {
  return `<div class="empty-state${compact ? " compact" : ""}">
    <div class="empty-state-icon" aria-hidden="true">${icon}</div>
    <p class="empty-state-title">${title}</p>
    <p class="empty-state-desc">${desc}</p>
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function escapeAttr(s) {
  return escapeHtml(s).replace(/"/g, "&quot;");
}

function hasRubric(c) {
  return (c.hook_strength || c.self_contained || c.takeaway_clarity || c.payoff) > 0;
}

function rubricHtml(c) {
  if (!hasRubric(c)) return "";
  const items = [
    ["Hook", c.hook_strength],
    ["Autocontenido", c.self_contained],
    ["Takeaway", c.takeaway_clarity],
    ["Remate", c.payoff],
  ];
  return items.map(([label, val]) => `
    <div class="rubric-row">
      <span class="rubric-label">${label}</span>
      <div class="rubric-bar"><div class="rubric-fill" style="width:${Math.round(val)}%"></div></div>
      <span class="rubric-val">${Math.round(val)}</span>
    </div>`).join("");
}

function clipMetaLine(c) {
  const base = `${fmtTime(c.start)} – ${fmtTime(c.end)} · ${Math.round(c.end - c.start)}s · puntaje ${Math.round(c.score)}`;
  if (!hasRubric(c)) return base;
  return `${base}<br><span class="rubric-mini">H${Math.round(c.hook_strength)} · S${Math.round(c.self_contained)} · T${Math.round(c.takeaway_clarity)} · P${Math.round(c.payoff)}</span>`;
}

function clipExplainHtml(c, { compact = false } = {}) {
  const hook = c.hook || (c.transcript ? c.transcript.slice(0, compact ? 100 : 220) : "");
  const reason = c.reason || "";
  const parts = [];
  if (hook) parts.push(`<p class="clip-hook">${escapeHtml(hook)}</p>`);
  if (reason) parts.push(`<p class="clip-reason meta">${escapeHtml(reason)}</p>`);
  if (hasRubric(c) && !compact) {
    parts.push(`<div class="rubric-bars compact">${rubricHtml(c)}</div>`);
  }
  return parts.join("");
}

function updateJobHeader(job) {
  $("job-title").textContent = job.name;
  const badge = $("job-status-badge");
  badge.textContent = stageLabel(job.stage);
  badge.className = `status-badge ${stageBadgeClass(job.stage)}`;
  badge.classList.remove("hidden");
  const parts = [job.message];
  if (job.clip_count != null) parts.push(`${job.clip_count} clips`);
  $("job-meta").textContent = parts.join(" · ");
}

function startPoll() {
  if (state.pollTimer) return;
  state.pollTimer = setInterval(() => {
    if (state.view === "inbox") loadJobs();
    else if (state.view === "job" && state.jobId) refreshJob();
  }, 3000);
}
function stopPoll() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = null;
}

async function openJob(jobId) {
  state.jobId = jobId;
  showView("job");
  await refreshJob();
}

async function refreshJob() {
  const job = await api(`/jobs/${enc(state.jobId)}`);
  state.job = job;
  state.duration = job.duration || 0;
  updateJobHeader(job);
  $("btn-retry").classList.toggle("hidden", job.stage !== "failed");
  $("btn-repropose").classList.toggle(
    "hidden",
    !["ready_for_review", "completed"].includes(job.stage) || ACTIVE.has(job.stage),
  );

  if (ACTIVE.has(job.stage)) {
    const banner = `
      <div class="job-progress-banner">
        <div class="meta">${stageLabel(job.stage)} · ${escapeHtml(job.message)}</div>
        <div class="progress-bar"><div class="progress-fill" style="width:${job.progress}%"></div></div>
      </div>`;
    if (job.stage === "rendering" || job.stage === "proposing") {
      try {
        const data = await api(`/jobs/${enc(state.jobId)}/candidates`);
        $("clips-list").innerHTML = banner + renderClipsHtml(data.candidates);
      } catch {
        $("clips-list").innerHTML = banner + emptyState(
          "⏳",
          "Procesando video",
          `Etapa actual: ${stageLabel(job.stage)} · ${Math.round(job.progress)}% completado.`,
          { compact: true },
        );
      }
    } else {
      $("clips-list").innerHTML = banner + emptyState(
        "⏳",
        "Procesando video",
        `Etapa actual: ${stageLabel(job.stage)} · ${Math.round(job.progress)}% completado.`,
        { compact: true },
      );
    }
    $("renders-section").classList.add("hidden");
    $("eval-section").classList.add("hidden");
    $("propose-prefs-section").classList.add("hidden");
    $("render-prefs-section").classList.add("hidden");
    $("timeline-section").classList.add("hidden");
    $("profile-section").classList.add("hidden");
    $("performance-section").classList.add("hidden");
    startPoll();
    return;
  }

  if (job.stage !== "ready_for_review" && job.stage !== "completed") {
    $("clips-list").innerHTML = emptyState(
      "⏳",
      "Todavía procesando",
      `${Math.round(job.progress)}% completado. Los candidatos aparecerán acá cuando estén listos.`,
      { compact: true },
    );
    $("renders-section").classList.add("hidden");
    if (ACTIVE.has(job.stage)) startPoll();
    return;
  }

  try {
    const data = await api(`/jobs/${enc(state.jobId)}/candidates`);
    renderClips(data.candidates);
    renderOutputs(data.candidates);
    await refreshEval();
    await loadJobProfile();
    await loadProposePrefs();
    await loadRenderPrefs();
    await loadJobTimeline();
    await loadPerformanceReport();
  } catch {
    $("clips-list").innerHTML = emptyState(
      "📋",
      "Clips aún no disponibles",
      "El pipeline todavía no terminó de proponer candidatos. Volvé en unos segundos.",
      { compact: true },
    );
    $("renders-section").classList.add("hidden");
    $("eval-section").classList.add("hidden");
  }
}

async function loadProposePrefs() {
  const section = $("propose-prefs-section");
  try {
    const prefs = await api(`/jobs/${enc(state.jobId)}/propose-prefs`);
    section.classList.remove("hidden");
    $("pref-target-clips").value = prefs.target_clips;
    $("pref-min-duration").value = prefs.min_duration;
    $("pref-max-duration").value = prefs.max_duration;
    $("pref-rank-finalists").value = prefs.rank_finalists;
  } catch {
    section.classList.add("hidden");
  }
}

async function saveProposePrefs() {
  if (!state.jobId) return;
  const minDur = parseFloat($("pref-min-duration").value);
  const maxDur = parseFloat($("pref-max-duration").value);
  if (minDur > maxDur) {
    toast("La duración mínima no puede superar la máxima");
    return;
  }
  try {
    await api(`/jobs/${enc(state.jobId)}/propose-prefs`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_clips: parseInt($("pref-target-clips").value, 10) || 12,
        min_duration: minDur,
        max_duration: maxDur,
        rank_finalists: parseInt($("pref-rank-finalists").value, 10) || 24,
      }),
    });
    toast("Opciones de propuesta guardadas");
  } catch (e) {
    toast(e.message);
  }
}

function bindProposePrefsOnce() {
  if (state.proposePrefsBound) return;
  state.proposePrefsBound = true;
  ["pref-target-clips", "pref-min-duration", "pref-max-duration", "pref-rank-finalists"].forEach((id) => {
    $(id).addEventListener("change", saveProposePrefs);
  });
}

async function loadRenderPrefs() {
  const section = $("render-prefs-section");
  try {
    const prefs = await api(`/jobs/${enc(state.jobId)}/render-prefs`);
    section.classList.remove("hidden");
    $("pref-caption-style").value = prefs.caption_style;
    $("pref-social-words").value = prefs.caption_social_max_words;
    $("pref-out-vertical").checked = prefs.output_vertical;
    $("pref-out-horizontal").checked = prefs.output_horizontal;
    await loadCaptionPreview();
  } catch {
    section.classList.add("hidden");
  }
}

async function loadCaptionPreview() {
  const panel = $("caption-preview-content");
  if (!panel || !state.jobId) return;
  try {
    const data = await api(`/jobs/${enc(state.jobId)}/caption-preview`);
    if (!data.previews?.length) {
      panel.innerHTML = `<p class="meta">${escapeHtml(data.message || "Aprobá un clip para ver el estilo de subtítulos.")}</p>`;
      return;
    }
    const subtitle = data.clip_title
      ? `<p class="caption-preview-source meta">Ejemplo desde: ${escapeHtml(data.clip_title)}</p>`
      : "";
    const blocks = data.previews.map((p) => `
      <div class="caption-preview-block caption-preview-${p.style}">
        <div class="caption-preview-style-label">${escapeHtml(p.style_label)} · ${escapeHtml(p.font)}</div>
        ${p.sample_lines.map((line) => `<div class="caption-preview-line">${escapeHtml(line)}</div>`).join("")}
      </div>`).join("");
    panel.innerHTML = subtitle + blocks;
  } catch {
    panel.innerHTML = `<p class="meta">Vista previa no disponible.</p>`;
  }
}

async function saveRenderPrefs() {
  if (!state.jobId) return;
  const vertical = $("pref-out-vertical").checked;
  const horizontal = $("pref-out-horizontal").checked;
  if (!vertical && !horizontal) {
    toast("Elegí al menos un formato de salida");
    $("pref-out-vertical").checked = true;
    return;
  }
  try {
    await api(`/jobs/${enc(state.jobId)}/render-prefs`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        caption_style: $("pref-caption-style").value,
        caption_social_max_words: parseInt($("pref-social-words").value, 10) || 5,
        output_vertical: vertical,
        output_horizontal: horizontal,
      }),
    });
    toast("Opciones guardadas");
    await loadCaptionPreview();
  } catch (e) {
    toast(e.message);
  }
}

function bindRenderPrefsOnce() {
  if (state.prefsBound) return;
  state.prefsBound = true;
  ["pref-caption-style", "pref-social-words", "pref-out-vertical", "pref-out-horizontal"].forEach((id) => {
    $(id).addEventListener("change", saveRenderPrefs);
  });
  $("pref-caption-style").addEventListener("change", loadCaptionPreview);
  $("pref-social-words").addEventListener("change", loadCaptionPreview);
}

async function loadJobProfile() {
  const section = $("profile-section");
  if (!state.jobId) return;
  try {
    const job = state.job || await api(`/jobs/${enc(state.jobId)}`);
    section.classList.remove("hidden");
    $("job-profile").value = job.profile || "training";
  } catch {
    section.classList.add("hidden");
  }
}

async function saveJobProfile() {
  if (!state.jobId) return;
  try {
    await api(`/jobs/${enc(state.jobId)}/profile`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile: $("job-profile").value }),
    });
    toast("Perfil actualizado");
    await loadProposePrefs();
    await loadRenderPrefs();
  } catch (e) {
    toast(e.message);
  }
}

function bindProfileOnce() {
  if (state.profileBound) return;
  state.profileBound = true;
  $("job-profile").addEventListener("change", saveJobProfile);
}

function renderJobTimeline(tl) {
  const el = $("job-timeline");
  if (!tl?.duration) {
    el.innerHTML = "";
    return;
  }
  let track = '<div class="job-timeline-track">';
  track += '<div class="job-timeline-heat">';
  for (const b of tl.buckets || []) {
    const left = (b.start / tl.duration) * 100;
    const width = ((b.end - b.start) / tl.duration) * 100;
    const opacity = 0.12 + (b.intensity || 0) * 0.88;
    track += `<div class="heat-seg" style="left:${left}%;width:${width}%;opacity:${opacity}"></div>`;
  }
  track += "</div>";
  for (const d of tl.dirty || []) {
    const left = (d.start / tl.duration) * 100;
    const width = ((d.end - d.start) / tl.duration) * 100;
    track += `<div class="dirty-seg" style="left:${left}%;width:${width}%"></div>`;
  }
  for (const c of tl.clips || []) {
    const left = (c.start / tl.duration) * 100;
    const width = Math.max(0.4, ((c.end - c.start) / tl.duration) * 100);
    track += `<button type="button" class="clip-seg" data-id="${escapeAttr(c.id)}" style="left:${left}%;width:${width}%" title="${escapeAttr(c.title || c.id)}"></button>`;
  }
  track += "</div>";
  track += `<div class="job-timeline-axis meta">${fmtTime(0)} · ${fmtTime(tl.duration)}</div>`;
  el.innerHTML = track;
  el.querySelectorAll(".clip-seg").forEach((btn) => {
    btn.onclick = (e) => {
      e.stopPropagation();
      openEditor(btn.dataset.id);
    };
  });
  const trackEl = el.querySelector(".job-timeline-track");
  trackEl.onclick = (e) => {
    if (e.target.closest(".clip-seg")) return;
    const rect = trackEl.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const t = ratio * tl.duration;
    const clips = tl.clips || [];
    if (!clips.length) return;
    let nearest = clips[0];
    let best = Math.abs((nearest.start + nearest.end) / 2 - t);
    for (const c of clips) {
      const dist = Math.abs((c.start + c.end) / 2 - t);
      if (dist < best) {
        best = dist;
        nearest = c;
      }
    }
    openEditor(nearest.id);
  };
}

async function loadJobTimeline() {
  const section = $("timeline-section");
  if (!state.jobId) return;
  try {
    const tl = await api(`/jobs/${enc(state.jobId)}/timeline`);
    section.classList.remove("hidden");
    renderJobTimeline(tl);
  } catch {
    section.classList.add("hidden");
  }
}

async function loadPerformanceReport() {
  const section = $("performance-section");
  if (!state.jobId) return;
  section.classList.remove("hidden");
  try {
    const report = await api(`/jobs/${enc(state.jobId)}/performance/report`);
    const el = $("performance-report");
    if (report.message && !report.sample_size) {
      el.textContent = report.message;
      return;
    }
    const lines = [`Muestra: ${report.sample_size} clips`];
    for (const c of report.correlations || []) {
      if (c.correlation != null) {
        lines.push(`${c.sub_score}: r=${c.correlation.toFixed(2)} (${c.metric})`);
      }
    }
    for (const s of report.suggestions || []) {
      lines.push(`Sugerencia ${s.sub_score}: ${s.current} -> ${s.suggested.toFixed(2)} · ${s.reason}`);
    }
    el.innerHTML = lines.map((line) => `<div>${escapeHtml(line)}</div>`).join("");
  } catch {
    $("performance-report").textContent = "";
  }
}

async function importPerformance() {
  const raw = $("performance-import").value.trim();
  if (!raw) {
    toast("Pegá JSON o CSV primero");
    return;
  }
  const format = raw.startsWith("[") || raw.startsWith("{") ? "json" : "csv";
  try {
    await api(`/jobs/${enc(state.jobId)}/performance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format, data: raw }),
    });
    toast("Metricas importadas");
    await loadPerformanceReport();
  } catch (e) {
    toast(e.message);
  }
}

function bindPerformanceOnce() {
  if (state.performanceBound) return;
  state.performanceBound = true;
  $("btn-import-performance").onclick = importPerformance;
}

function getSelectedGridClipId() {
  return state.selectedClipId || state.candidates[0]?.id || null;
}

function selectGridClip(clipId, { focus = true } = {}) {
  state.selectedClipId = clipId;
  const list = $("clips-list");
  if (!list) return;
  let card = null;
  list.querySelectorAll(".clip-card").forEach((el) => {
    const sel = el.dataset.id === clipId;
    el.classList.toggle("selected", sel);
    el.tabIndex = sel ? 0 : -1;
    if (sel) {
      card = el;
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  });
  if (focus && card) card.focus();
}

function navigateGrid(delta) {
  if (!state.candidates.length) return;
  let idx = state.candidates.findIndex((c) => c.id === state.selectedClipId);
  if (idx < 0) idx = delta > 0 ? -1 : 0;
  idx = (idx + delta + state.candidates.length) % state.candidates.length;
  selectGridClip(state.candidates[idx].id);
}

function onGridKeydown(e) {
  if (state.view !== "job") return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

  switch (e.key) {
    case "j":
    case "J":
      e.preventDefault();
      navigateGrid(1);
      break;
    case "k":
    case "K":
      e.preventDefault();
      navigateGrid(-1);
      break;
    case "a":
    case "A":
      e.preventDefault();
      setClipStatus("approved", { clipId: getSelectedGridClipId() });
      break;
    case "r":
    case "R":
      e.preventDefault();
      setClipStatus("rejected", {
        clipId: getSelectedGridClipId(),
        rejectionReason: "bad_hook",
      });
      break;
    default:
      break;
  }
}

function bindGridKeyboardOnce() {
  if (state.gridBound) return;
  state.gridBound = true;
  document.addEventListener("keydown", onGridKeydown);
}

async function refreshEval() {
  const section = $("eval-section");
  try {
    const [golden, evalRep] = await Promise.all([
      api(`/jobs/${enc(state.jobId)}/golden`),
      api(`/jobs/${enc(state.jobId)}/eval`),
    ]);
    section.classList.remove("hidden");
    $("eval-hint").classList.toggle("hidden", golden.total > 0);
    const pct = Math.round((evalRep.precision_at_n || 0) * 100);
    const recall = Math.round((evalRep.recall || 0) * 100);
    $("eval-stats").innerHTML = golden.total
      ? `Golden set: ${golden.approved} aprobados, ${golden.rejected} rechazados`
        + (evalRep.n
          ? ` · precisión@${evalRep.n}: ${pct}% · recall: ${recall}%`
          : " · ejecutá Evaluar calidad para medir")
      : "Sin etiquetas todavía. Aprobá o rechazá clips en el editor.";
  } catch {
    section.classList.add("hidden");
  }
}

function outputLabel(fmt) {
  const labels = {
    "9x16": "Vertical 9:16 (karaoke)",
    "9x16_social": "Vertical 9:16 (social)",
    "16x9": "Horizontal 16:9 (karaoke)",
    "16x9_social": "Horizontal 16:9 (social)",
  };
  return labels[fmt] || fmt;
}

const OUTPUT_FMTS = ["9x16", "9x16_social", "16x9", "16x9_social"];

const OUTPUT_SUFFIX = {
  "9x16": "vertical-karaoke",
  "9x16_social": "vertical-social",
  "16x9": "horizontal-karaoke",
  "16x9_social": "horizontal-social",
};

function slugifyName(text, maxLen = 48) {
  const slug = String(text || "clip")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
  const trimmed = slug.slice(0, maxLen).replace(/-+$/g, "");
  return trimmed || "clip";
}

function exportFilename(c, fmt) {
  const job = slugifyName(state.job?.name || state.jobId || "job", 32);
  const title = slugifyName(c.title || c.id, 48);
  const suffix = OUTPUT_SUFFIX[fmt] || fmt;
  return `${job}-${title}-${suffix}.mp4`;
}

function previewFormat(outputs, preferred = "9x16") {
  if (outputs[preferred]) return preferred;
  return OUTPUT_FMTS.find((f) => outputs[f]);
}

function renderBadgeHtml(c) {
  const keys = c.outputs ? Object.keys(c.outputs) : [];
  if (!keys.length) return "";
  return `<span class="badge badge-render" title="${keys.length} archivo(s)">${keys.length} render</span>`;
}

function renderOutputs(clips) {
  const withOut = clips.filter((c) => c.outputs && Object.keys(c.outputs).length);
  const section = $("renders-section");
  const list = $("renders-list");
  if (!withOut.length) {
    section.classList.add("hidden");
    return;
  }
  section.classList.remove("hidden");
  list.innerHTML = withOut.map((c) => {
    const formats = OUTPUT_FMTS.filter((f) => c.outputs[f]);
    const defaultFmt = previewFormat(c.outputs);
    const links = formats.map((fmt) => {
      const url = `/api/jobs/${enc(state.jobId)}/clips/${c.id}/output/${fmt}`;
      const fname = exportFilename(c, fmt);
      return `<a href="${url}" download="${escapeAttr(fname)}" target="_blank" rel="noopener" class="render-dl-pill">${outputLabel(fmt)}</a>`;
    }).join("");
    const previewTabs = formats.length > 1
      ? `<div class="render-preview-tabs" data-clip="${escapeAttr(c.id)}">${formats.map((fmt, i) =>
          `<button type="button" class="render-preview-tab${fmt === defaultFmt ? " active" : ""}" data-fmt="${fmt}">${outputLabel(fmt)}</button>`
        ).join("")}</div>`
      : `<div class="render-preview-meta meta">${outputLabel(defaultFmt)}</div>`;
    const previewUrl = `/api/jobs/${enc(state.jobId)}/clips/${c.id}/output/${defaultFmt}`;
    return `
      <article class="render-card" data-clip-id="${escapeAttr(c.id)}">
        <div class="render-card-head">
          <div>
            <div class="clip-title">${escapeHtml(c.title || c.id)}</div>
            <div class="clip-meta">${fmtTime(c.start)} – ${fmtTime(c.end)} · ${statusLabel(c.status)} · ${formats.length} formato(s)</div>
          </div>
          <div class="render-links">${links}</div>
        </div>
        ${previewTabs}
        <video class="render-preview" data-preview-for="${escapeAttr(c.id)}" src="${previewUrl}" controls playsinline preload="metadata"></video>
      </article>`;
  }).join("");

  list.querySelectorAll(".render-preview-tabs").forEach((tabs) => {
    const clipId = tabs.dataset.clip;
    const card = tabs.closest(".render-card");
    const video = card?.querySelector(".render-preview");
    tabs.querySelectorAll(".render-preview-tab").forEach((btn) => {
      btn.onclick = () => {
        tabs.querySelectorAll(".render-preview-tab").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        if (video) {
          video.src = `/api/jobs/${enc(state.jobId)}/clips/${clipId}/output/${btn.dataset.fmt}`;
          video.load();
        }
      };
    });
  });
}

$("btn-retry").onclick = async () => {
  try {
    await api(`/jobs/${enc(state.jobId)}/retry`, { method: "POST" });
    toast("Procesamiento reiniciado");
    startPoll();
    await refreshJob();
  } catch (e) {
    toast(e.message);
  }
};

function renderClipsHtml(clips) {
  if (!clips.length) {
    return emptyState(
      "🎬",
      "Sin clips propuestos",
      "El motor no encontró candidatos en este video. Probá Re-proponer clips con otro umbral.",
      { compact: true },
    );
  }
  return clips.map((c) => `
    <article class="clip-card" data-id="${c.id}" tabindex="0" role="listitem">
      <div class="clip-card-body">
        <div class="clip-title">${escapeHtml(c.title || c.id)}</div>
        <div class="clip-meta">${clipMetaLine(c)}</div>
        ${clipExplainHtml(c, { compact: true })}
      </div>
      <div class="clip-badges">
        ${renderBadgeHtml(c)}
        <span class="badge ${statusBadgeClass(c.status)}">${statusLabel(c.status)}</span>
      </div>
    </article>
  `).join("");
}

function bindClipCards(container) {
  const cards = [...container.querySelectorAll(".clip-card")];
  cards.forEach((el) => {
    const open = () => openEditor(el.dataset.id);
    el.onclick = open;
    el.onfocus = () => selectGridClip(el.dataset.id, { focus: false });
    el.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      } else if (e.key === "ArrowDown" || e.key === "j" || e.key === "J") {
        e.preventDefault();
        navigateGrid(1);
      } else if (e.key === "ArrowUp" || e.key === "k" || e.key === "K") {
        e.preventDefault();
        navigateGrid(-1);
      } else if (e.key === "a" || e.key === "A") {
        e.preventDefault();
        setClipStatus("approved", { clipId: el.dataset.id });
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        setClipStatus("rejected", { clipId: el.dataset.id, rejectionReason: "bad_hook" });
      }
    };
  });
}

function renderClips(clips) {
  state.candidates = clips;
  const list = $("clips-list");
  list.innerHTML = renderClipsHtml(clips);
  bindClipCards(list);
  if (state.selectedClipId && clips.some((c) => c.id === state.selectedClipId)) {
    selectGridClip(state.selectedClipId, { focus: false });
  } else {
    state.selectedClipId = null;
  }
}

function getRange() {
  return {
    start: parseFloat($("range-start").value),
    end: parseFloat($("range-end").value),
  };
}

function setRange(start, end) {
  const dur = state.duration || Math.max(end + 5, 100);
  start = Math.max(0, Math.min(start, dur - 0.5));
  end = Math.max(start + 0.5, Math.min(end, dur));
  $("range-start").value = start;
  $("range-end").value = end;
  updateReadout();
  updateTimeline();
}

function pctOf(t) {
  const dur = state.duration || 1;
  return Math.max(0, Math.min(100, (t / dur) * 100));
}

function timeFromClientX(clientX, laneEl) {
  const rect = laneEl.getBoundingClientRect();
  const pct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
  return timeFromPct(pct);
}

function timeFromPct(pct) {
  return (pct / 100) * (state.duration || 0);
}

function applyTimelineZoom() {
  $("timeline-inner").style.width = `${state.timelineZoom * 100}%`;
  $("zoom-label").textContent = `${Math.round(state.timelineZoom * 100)}%`;
}

function renderRuler() {
  const dur = state.duration || 0;
  if (!dur) {
    $("timeline-ruler").innerHTML = "";
    return;
  }
  const step = dur > 600 ? 60 : dur > 180 ? 30 : dur > 60 ? 10 : 5;
  const ticks = [];
  for (let t = 0; t <= dur; t += step) {
    ticks.push(`<span class="ruler-tick" style="left:${pctOf(t)}%"><span>${fmtTime(t)}</span></span>`);
  }
  $("timeline-ruler").innerHTML = ticks.join("");
}

function renderSubsTrack() {
  const lane = $("subs-track");
  const words = state.clip?.words || [];
  if (!words.length) {
    lane.innerHTML = `<span class="track-empty">Sin palabras en el rango</span>`;
    return;
  }
  lane.innerHTML = words.map((w, i) => {
    const left = pctOf(w.start);
    const width = Math.max(0.35, pctOf(w.end) - left);
    return `<button type="button" class="subs-block${i === state.activeWord ? " active" : ""}" data-i="${i}" style="left:${left}%;width:${width}%" title="${escapeAttr(w.text.trim())}"></button>`;
  }).join("");
  lane.querySelectorAll(".subs-block").forEach((el) => {
    el.addEventListener("click", () => seekTo(state.clip.words[parseInt(el.dataset.i, 10)].start));
  });
}

function updateTimeline() {
  const { start, end } = getRange();
  const player = $("player");
  const t = player.currentTime || start;
  $("timeline-clip").style.left = `${pctOf(start)}%`;
  $("timeline-clip").style.width = `${pctOf(end) - pctOf(start)}%`;
  $("timeline-playhead").style.left = `${pctOf(t)}%`;
  $("handle-start").style.left = `${pctOf(start)}%`;
  $("handle-end").style.left = `${pctOf(end)}%`;
  $("preview-progress-fill").style.width = `${pctOf(t)}%`;
  $("transport-time").textContent = `${fmtTimePrecise(t)} / ${fmtTimePrecise(state.duration)}`;
  $("overlay-time").textContent = fmtTimePrecise(t);
  renderSubsTrack();
}

function updateReadout() {
  const { start, end } = getRange();
  $("readout-start").textContent = fmtTimePrecise(start);
  $("readout-end").textContent = fmtTimePrecise(end);
  $("readout-dur").textContent = `${Math.max(0, end - start).toFixed(1)}s`;
}

function seekTo(t, { pauseAtEnd = false } = {}) {
  const player = $("player");
  const { start, end } = getRange();
  t = Math.max(0, Math.min(t, state.duration || t));
  player.currentTime = t;
  updateTimeline();
  if (pauseAtEnd && t >= end - 0.05) player.pause();
}

function syncActiveWord() {
  const player = $("player");
  const t = player.currentTime;
  const words = state.clip?.words || [];
  let idx = -1;
  for (let i = 0; i < words.length; i++) {
    if (t >= words[i].start && t < words[i].end + 0.05) {
      idx = i;
      break;
    }
  }
  if (idx === state.activeWord) return;
  state.activeWord = idx;
  const list = $("words-list");
  list.querySelectorAll(".word-chip").forEach((el, i) => {
    el.classList.toggle("active", i === idx);
    el.classList.toggle("past", i < idx && idx >= 0);
    if (i === idx) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
  $("subs-track").querySelectorAll(".subs-block").forEach((el, i) => {
    el.classList.toggle("active", i === idx);
  });
}

function updatePlayButton() {
  const player = $("player");
  const icon = player.paused ? "▶" : "⏸";
  $("btn-play").textContent = icon;
  $("btn-overlay-play").textContent = icon;
}

function zoomTimeline(factor) {
  state.timelineZoom = Math.max(1, Math.min(6, state.timelineZoom * factor));
  applyTimelineZoom();
}

function zoomToClip() {
  const { start, end } = getRange();
  const clipDur = Math.max(0.5, end - start);
  const pad = clipDur * 0.15;
  const viewStart = Math.max(0, start - pad);
  const viewEnd = Math.min(state.duration || end, end + pad);
  const viewDur = Math.max(0.5, viewEnd - viewStart);
  state.timelineZoom = Math.min(6, Math.max(1, (state.duration || viewDur) / viewDur));
  applyTimelineZoom();
  const scroll = $("timeline-scroll");
  const inner = $("timeline-inner");
  const ratio = viewStart / (state.duration || 1);
  scroll.scrollLeft = ratio * (inner.scrollWidth - scroll.clientWidth);
}

async function openEditor(clipId) {
  const data = await api(`/jobs/${enc(state.jobId)}/candidates`);
  const clip = data.candidates.find((c) => c.id === clipId);
  if (!clip) return toast("Clip no encontrado");
  state.clip = clip;
  state.activeWord = -1;
  showView("editor");

  $("editor-clip-title").textContent = clip.title || clip.id;
  $("editor-clip-meta").textContent =
    `${fmtTime(clip.start)} – ${fmtTime(clip.end)} · ${Math.round(clip.end - clip.start)}s · ${statusLabel(clip.status)}`;

  const rubricEl = $("editor-rubric");
  const rubric = rubricHtml(clip);
  rubricEl.innerHTML = rubric;
  rubricEl.classList.toggle("hidden", !rubric);

  const explainEl = $("editor-explain");
  const explain = clipExplainHtml(clip);
  explainEl.innerHTML = explain;
  explainEl.classList.toggle("hidden", !explain);

  const player = $("player");
  player.src = `/api/jobs/${enc(state.jobId)}/video`;
  player.load();

  const max = state.duration || clip.end + 5;
  $("range-start").max = max;
  $("range-end").max = max;
  setRange(clip.start, clip.end);

  player.onloadedmetadata = () => {
    if (!state.duration && player.duration) {
      state.duration = player.duration;
      $("range-start").max = state.duration;
      $("range-end").max = state.duration;
    }
    renderRuler();
    applyTimelineZoom();
    zoomToClip();
    updateTimeline();
    seekTo(clip.start);
  };

  player.ontimeupdate = () => {
    updateTimeline();
    syncActiveWord();
    const { end } = getRange();
    if (!player.paused && player.currentTime >= end) {
      player.pause();
      player.currentTime = end;
    }
  };
  player.onplay = updatePlayButton;
  player.onpause = updatePlayButton;

  renderWords(clip.words || []);
  bindEditorOnce();
  updatePlayButton();
}

function bindEditorOnce() {
  if (state.editorBound) return;
  state.editorBound = true;

  const togglePlay = () => {
    const player = $("player");
    if (player.paused) {
      const { start, end } = getRange();
      if (player.currentTime < start || player.currentTime >= end) {
        player.currentTime = start;
      }
      player.play();
    } else {
      player.pause();
    }
  };

  $("btn-play").onclick = togglePlay;
  $("btn-overlay-play").onclick = togglePlay;

  $("btn-step-back").onclick = () => {
    const { start } = getRange();
    seekTo(Math.max(start, $("player").currentTime - SEEK_STEP));
  };
  $("btn-step-fwd").onclick = () => {
    const { end } = getRange();
    seekTo(Math.min(end, $("player").currentTime + SEEK_STEP));
  };

  $("btn-nudge-in-minus").onclick = () => nudgeRange("start", -NUDGE);
  $("btn-nudge-in-plus").onclick = () => nudgeRange("start", NUDGE);
  $("btn-nudge-out-minus").onclick = () => nudgeRange("end", -NUDGE);
  $("btn-nudge-out-plus").onclick = () => nudgeRange("end", NUDGE);
  $("btn-set-in").onclick = () => setRange($("player").currentTime, getRange().end);
  $("btn-set-out").onclick = () => setRange(getRange().start, $("player").currentTime);

  $("btn-save-range").onclick = saveRange;
  $("btn-approve").onclick = () => setClipStatus("approved");
  $("btn-reject").onclick = () => setClipStatus("rejected");

  $("btn-zoom-in").onclick = () => zoomTimeline(1.5);
  $("btn-zoom-out").onclick = () => zoomTimeline(1 / 1.5);
  $("btn-zoom-fit").onclick = zoomToClip;

  const seekFromLane = (e) => {
    if (e.target.classList.contains("timeline-handle")) return;
    seekTo(timeFromClientX(e.clientX, $("video-track")));
  };
  $("video-track").onclick = seekFromLane;
  $("subs-track").onclick = (e) => {
    if (e.target.classList.contains("subs-block")) return;
    seekFromLane(e);
  };

  $("preview-progress").onclick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    seekTo(timeFromPct(pct));
  };

  setupHandleDrag("handle-start", "start");
  setupHandleDrag("handle-end", "end");

  document.addEventListener("keydown", onEditorKeydown);
}

function setupHandleDrag(handleId, edge) {
  const handle = $(handleId);
  handle.addEventListener("mousedown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    state.drag = edge;
    document.body.classList.add("dragging");
  });
}

document.addEventListener("mousemove", (e) => {
  if (!state.drag || state.view !== "editor") return;
  const t = timeFromClientX(e.clientX, $("video-track"));
  const { start, end } = getRange();
  if (state.drag === "start") setRange(Math.min(t, end - 0.5), end);
  else setRange(start, Math.max(t, start + 0.5));
});

document.addEventListener("mouseup", () => {
  if (state.drag) {
    state.drag = null;
    document.body.classList.remove("dragging");
  }
});

function nudgeRange(edge, delta) {
  const { start, end } = getRange();
  if (edge === "start") setRange(start + delta, end);
  else setRange(start, end + delta);
}

function onEditorKeydown(e) {
  if (state.view !== "editor") return;
  if (state.editingWord >= 0) return;
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

  const player = $("player");
  switch (e.key) {
    case " ":
      e.preventDefault();
      $("btn-play").click();
      break;
    case "ArrowLeft":
      e.preventDefault();
      seekTo(player.currentTime - SEEK_STEP);
      break;
    case "ArrowRight":
      e.preventDefault();
      seekTo(player.currentTime + SEEK_STEP);
      break;
    case "i":
    case "I":
      setRange(player.currentTime, getRange().end);
      break;
    case "o":
    case "O":
      setRange(getRange().start, player.currentTime);
      break;
    case "[":
      nudgeRange("start", e.shiftKey ? -NUDGE : NUDGE);
      break;
    case "]":
      nudgeRange("end", e.shiftKey ? -NUDGE : NUDGE);
      break;
    case "a":
    case "A":
      e.preventDefault();
      setClipStatus("approved");
      break;
    case "r":
    case "R":
      e.preventDefault();
      setClipStatus("rejected");
      break;
    default:
      break;
  }
}

async function saveRange() {
  const { start, end } = getRange();
  const clip = await api(`/jobs/${enc(state.jobId)}/clips/${state.clip.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start, end }),
  });
  state.clip = clip;
  renderWords(clip.words || []);
  toast("Rango guardado");
}

async function setClipStatus(status, { clipId, rejectionReason } = {}) {
  const id = clipId || state.clip?.id;
  if (!id) return;

  const body = { status };
  if (status === "rejected") {
    let reason = rejectionReason;
    if (!reason && state.view === "editor") {
      reason = $("reject-reason").value;
      if (!reason) {
        toast("Elegí una razón de rechazo");
        return;
      }
    }
    if (!reason) reason = "bad_hook";
    body.rejection_reason = reason;
  }

  const clip = await api(`/jobs/${enc(state.jobId)}/clips/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (state.clip?.id === id) {
    state.clip = clip;
    $("editor-clip-meta").textContent =
      `${fmtTime(clip.start)} – ${fmtTime(clip.end)} · ${Math.round(clip.end - clip.start)}s · ${statusLabel(clip.status)}`;
  }

  if (state.view === "job") {
    const idx = state.candidates.findIndex((c) => c.id === id);
    if (idx >= 0) state.candidates[idx] = clip;
    renderClips(state.candidates);
    selectGridClip(clip.id, { focus: false });
  }

  toast(status === "approved" ? "Clip aprobado" : "Clip rechazado");
  await refreshEval();
  if (status === "approved") await loadCaptionPreview();
}

function renderWords(words) {
  const list = $("words-list");
  if (!words.length) {
    list.innerHTML = emptyState(
      "💬",
      "Sin subtítulos en este rango",
      "Ajustá el inicio y fin del clip, o esperá a que la transcripción cubra este tramo.",
      { compact: true },
    );
    return;
  }
  list.innerHTML = words.map((w, i) =>
    `<button type="button" class="word-chip" data-i="${i}" title="${fmtTimePrecise(w.start)}">${escapeHtml(w.text.trim())}</button>`
  ).join("");

  list.querySelectorAll(".word-chip").forEach((el) => {
    const i = parseInt(el.dataset.i, 10);
    el.addEventListener("click", () => {
      if (state.editingWord === i) return;
      seekTo(state.clip.words[i].start);
    });
    el.addEventListener("dblclick", (ev) => {
      ev.preventDefault();
      startWordEdit(i, el);
    });
  });
}

function startWordEdit(index, chipEl) {
  if (state.editingWord >= 0) return;
  state.editingWord = index;
  const word = state.clip.words[index];
  const input = document.createElement("input");
  input.type = "text";
  input.className = "word-edit-input";
  input.value = word.text.trim();
  chipEl.replaceWith(input);
  input.focus();
  input.select();

  const finish = async (save) => {
    state.editingWord = -1;
    if (save) await saveWord(index, input.value.trim());
    renderWords(state.clip.words || []);
  };

  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") { ev.preventDefault(); finish(true); }
    if (ev.key === "Escape") { ev.preventDefault(); finish(false); }
  });
  input.addEventListener("blur", () => finish(true));
}

async function saveWord(index, text) {
  const current = state.clip.words[index]?.text?.trim() || "";
  if (!text || text === current) return;
  try {
    const word = await api(
      `/jobs/${enc(state.jobId)}/clips/${state.clip.id}/words/${index}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      }
    );
    state.clip.words[index] = word;
    toast("Palabra actualizada");
  } catch (e) {
    toast(e.message);
  }
}

$("btn-render").onclick = async () => {
  await api(`/jobs/${enc(state.jobId)}/render`, { method: "POST" });
  toast("Render iniciado");
  startPoll();
  setTimeout(refreshJob, 2000);
};

$("btn-repropose").onclick = async () => {
  if (!confirm("¿Re-proponer clips con el motor actual? Se reemplazan los candidatos actuales.")) return;
  try {
    await api(`/jobs/${enc(state.jobId)}/repropose`, { method: "POST" });
    toast("Re-proposición iniciada");
    startPoll();
    await refreshJob();
  } catch (e) {
    toast(e.message);
  }
};

$("btn-run-eval").onclick = async () => {
  try {
    const rep = await api(`/jobs/${enc(state.jobId)}/eval`, { method: "POST" });
    toast(`Precisión@${rep.n}: ${Math.round(rep.precision_at_n * 100)}%`);
    await refreshEval();
  } catch (e) {
    toast(e.message);
  }
};

const dropzone = $("dropzone");
const fileInput = $("file-input");

dropzone.onclick = () => fileInput.click();
dropzone.ondragover = (e) => { e.preventDefault(); dropzone.classList.add("dragover"); };
dropzone.ondragleave = () => dropzone.classList.remove("dragover");
dropzone.ondrop = (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
};
fileInput.onchange = () => {
  if (fileInput.files[0]) uploadFile(fileInput.files[0]);
};

async function uploadFile(file) {
  if (!file.name.toLowerCase().endsWith(".mp4")) {
    toast("Solo .mp4");
    return;
  }
  toast(`Subiendo ${file.name}…`);
  const fd = new FormData();
  fd.append("file", file);
  try {
    const job = await api("/jobs/upload", { method: "POST", body: fd });
    toast("Procesamiento iniciado");
    await loadJobs();
    openJob(job.id);
  } catch (e) {
    toast(e.message);
  }
}

loadJobs();
bindProposePrefsOnce();
bindRenderPrefsOnce();
bindProfileOnce();
bindPerformanceOnce();
bindGridKeyboardOnce();
startPoll();
