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
  duration: 0,
  pollTimer: null,
  activeWord: -1,
  editingWord: -1,
  drag: null,
  editorBound: false,
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
    list.innerHTML = `<p class="meta">No hay trabajos todavía.</p>`;
    return;
  }
  list.innerHTML = jobs.map((j) => {
    const cls = j.stage === "failed" ? "stage-failed"
      : j.stage === "ready_for_review" || j.stage === "completed" ? "stage-ready"
      : ACTIVE.has(j.stage) ? "stage-working" : "";
    return `
      <article class="job-card" data-id="${escapeAttr(j.id)}">
        <div class="job-card-head">
          <div>
            <div class="job-name">${escapeHtml(j.name)}</div>
            <div class="job-stage ${cls}">${stageLabel(j.stage)} · ${j.message}</div>
          </div>
          <div>${Math.round(j.progress)}%</div>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${j.progress}%"></div></div>
      </article>`;
  }).join("");

  list.querySelectorAll(".job-card").forEach((el) => {
    el.onclick = () => openJob(el.dataset.id);
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

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function escapeAttr(s) {
  return escapeHtml(s).replace(/"/g, "&quot;");
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
  $("job-title").textContent = job.name;
  $("job-meta").textContent = `${stageLabel(job.stage)} · ${job.message}${job.clip_count != null ? ` · ${job.clip_count} clips` : ""}`;
  $("btn-retry").classList.toggle("hidden", job.stage !== "failed");

  if (job.stage !== "ready_for_review" && job.stage !== "completed") {
    $("clips-list").innerHTML = `<p class="meta">Todavía procesando… (${Math.round(job.progress)}%)</p>`;
    $("renders-section").classList.add("hidden");
    if (ACTIVE.has(job.stage)) startPoll();
    return;
  }

  try {
    const data = await api(`/jobs/${enc(state.jobId)}/candidates`);
    renderClips(data.candidates);
    renderOutputs(data.candidates);
    await refreshEval();
  } catch {
    $("clips-list").innerHTML = `<p class="meta">Clips aún no disponibles.</p>`;
    $("renders-section").classList.add("hidden");
    $("eval-section").classList.add("hidden");
  }
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
          ? ` · precision@${evalRep.n}: ${pct}% · recall: ${recall}%`
          : " · corré Evaluar para medir")
      : "Sin etiquetas todavía. Aproba/rechaza clips en el editor.";
  } catch {
    section.classList.add("hidden");
  }
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
    const links = Object.entries(c.outputs).map(([fmt]) => {
      const url = `/api/jobs/${enc(state.jobId)}/clips/${c.id}/output/${fmt}`;
      const label = fmt === "9x16" ? "Vertical 9:16" : "Horizontal 16:9";
      return `<a href="${url}" download target="_blank" rel="noopener">${label} ↓</a>`;
    }).join("");
    const preview = c.outputs["9x16"]
      ? `/api/jobs/${enc(state.jobId)}/clips/${c.id}/output/9x16`
      : `/api/jobs/${enc(state.jobId)}/clips/${c.id}/output/16x9`;
    return `
      <article class="render-card">
        <div class="render-card-head">
          <div>
            <div class="clip-title">${escapeHtml(c.title || c.id)}</div>
            <div class="clip-meta">${fmtTime(c.start)} – ${fmtTime(c.end)} · ${c.status}</div>
          </div>
          <div class="render-links">${links}</div>
        </div>
        <video class="render-preview" src="${preview}" controls playsinline preload="metadata"></video>
      </article>`;
  }).join("");
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

function renderClips(clips) {
  const list = $("clips-list");
  if (!clips.length) {
    list.innerHTML = `<p class="meta">Sin clips propuestos.</p>`;
    return;
  }
  list.innerHTML = clips.map((c) => `
    <article class="clip-card" data-id="${c.id}">
      <div>
        <div class="clip-title">${escapeHtml(c.title || c.id)}</div>
        <div class="clip-meta">${fmtTime(c.start)} – ${fmtTime(c.end)} · ${Math.round(c.end - c.start)}s · score ${Math.round(c.score)}</div>
      </div>
      <span class="badge badge-${c.status}">${c.status}</span>
    </article>
  `).join("");
  list.querySelectorAll(".clip-card").forEach((el) => {
    el.onclick = () => openEditor(el.dataset.id);
  });
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
    `${fmtTime(clip.start)} – ${fmtTime(clip.end)} · ${Math.round(clip.end - clip.start)}s · ${clip.status}`;

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
  if (tag === "INPUT" || tag === "TEXTAREA") return;

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

async function setClipStatus(status) {
  const body = { status };
  if (status === "rejected") {
    const reason = $("reject-reason").value;
    if (!reason) {
      toast("Elegí una razón de rechazo");
      return;
    }
    body.rejection_reason = reason;
  }
  const clip = await api(`/jobs/${enc(state.jobId)}/clips/${state.clip.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  state.clip = clip;
  $("editor-clip-meta").textContent =
    `${fmtTime(clip.start)} – ${fmtTime(clip.end)} · ${Math.round(clip.end - clip.start)}s · ${clip.status}`;
  toast(status === "approved" ? "Aprobado" : "Rechazado");
  await refreshEval();
}

function renderWords(words) {
  const list = $("words-list");
  if (!words.length) {
    list.innerHTML = `<p class="meta">Sin palabras en este rango.</p>`;
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

$("btn-run-eval").onclick = async () => {
  try {
    const rep = await api(`/jobs/${enc(state.jobId)}/eval`, { method: "POST" });
    toast(`precision@${rep.n}: ${Math.round(rep.precision_at_n * 100)}%`);
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
startPoll();
