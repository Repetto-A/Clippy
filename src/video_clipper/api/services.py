"""Lógica de negocio compartida por la API."""

from __future__ import annotations

import threading
from pathlib import Path
from urllib.parse import unquote

from .. import job_status, storage
from ..clip_utils import clamp_range, clip_words, sync_clip_words
from ..config import settings
from ..content_profile import JobProfile, parse_profile
from ..models import ClipStatus, JobStage, Layout, RejectionReason
from ..performance import (
    PerformanceReport,
    PerformanceSet,
    build_performance_report,
    merge_performance,
    parse_performance_csv,
    parse_performance_json,
)
from ..review import record_golden
from ..captions import caption_preview_samples
from ..pipeline import run_all, stage_propose, stage_render
from ..timeline import JobTimeline, build_job_timeline

_lock = threading.Lock()
_running: set[str] = set()


def inbox_dir() -> Path:
    d = settings.workdir / "inbox"
    d.mkdir(parents=True, exist_ok=True)
    return d


def decode_job_id(job_id: str) -> str:
    return unquote(job_id)


def workdir_for(job_id: str) -> Path:
    return settings.workdir / decode_job_id(job_id)


def list_jobs() -> list[tuple[str, object]]:
    root = settings.workdir
    if not root.is_dir():
        return []
    jobs: list[tuple[str, object]] = []
    for d in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir() or d.name == "inbox":
            continue
        rec = storage.load_job_status(d)
        if rec is not None:
            jobs.append((d.name, rec))
    return jobs


def get_job(job_id: str):
    wd = workdir_for(job_id)
    rec = storage.load_job_status(wd)
    if rec is None:
        return None
    duration = None
    dur_file = wd / "duration.txt"
    if dur_file.exists():
        duration = float(dur_file.read_text(encoding="utf-8"))
    return rec, duration


def source_path(job_id: str) -> Path | None:
    rec, _ = get_job(job_id) or (None, None)
    if rec is None or not rec.source:
        return None
    p = Path(rec.source)
    return p if p.is_file() else None


def is_processing(job_id: str) -> bool:
    with _lock:
        return decode_job_id(job_id) in _running


def _run_pipeline(source: Path, job_id: str) -> None:
    try:
        run_all(source, track=True, init=False)
    finally:
        with _lock:
            _running.discard(job_id)


def start_job(source: Path, *, profile: str | None = None) -> str:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"No existe: {source}")
    job_id = source.stem
    with _lock:
        if job_id in _running:
            raise RuntimeError("Este video ya se está procesando")
        _running.add(job_id)
    workdir = settings.source_workdir(source)
    workdir.mkdir(parents=True, exist_ok=True)
    job_status.init(workdir, source)
    if profile:
        storage.save_job_profile(JobProfile(profile=parse_profile(profile)), workdir)
    threading.Thread(target=_run_pipeline, args=(source, job_id), daemon=True).start()
    return job_id


def save_upload(filename: str, data: bytes) -> Path:
    safe = Path(filename).name
    if not safe.lower().endswith(".mp4"):
        raise ValueError("Solo se aceptan archivos .mp4")
    dest = inbox_dir() / safe
    dest.write_bytes(data)
    return dest


def get_candidates(job_id: str):
    wd = workdir_for(job_id)
    if not (wd / "candidates.json").exists():
        return None
    return storage.load_candidates(wd)


def patch_clip(job_id: str, clip_id: str, patch) -> object | None:
    wd = workdir_for(job_id)
    if not (wd / "candidates.json").exists():
        return None
    cset = storage.load_candidates(wd)
    transcript = storage.load_transcript(wd) if (wd / "transcript.json").exists() else None
    duration = float((wd / "duration.txt").read_text(encoding="utf-8")) if (wd / "duration.txt").exists() else 0.0

    target = None
    for c in cset.candidates:
        if c.id == clip_id:
            target = c
            break
    if target is None:
        return None

    if patch.start is not None or patch.end is not None:
        start = patch.start if patch.start is not None else target.start
        end = patch.end if patch.end is not None else target.end
        target.start, target.end = clamp_range(start, end, duration)
        if transcript is not None and patch.words is None:
            sync_clip_words(target, transcript)
        target.status = ClipStatus.EDITED

    if patch.words is not None:
        target.words = patch.words
        target.transcript = " ".join(w.text for w in target.words).strip()
        target.status = ClipStatus.EDITED

    if patch.status is not None:
        target.status = patch.status
        if patch.status is ClipStatus.REJECTED and patch.rejection_reason is not None:
            target.rejection_reason = patch.rejection_reason
        if patch.status in (ClipStatus.APPROVED, ClipStatus.REJECTED):
            record_golden(wd, cset.source, target, patch.status, patch.rejection_reason)
    if patch.title is not None:
        target.title = patch.title
    if patch.layout is not None:
        target.layout = Layout(patch.layout)

    storage.save_candidates(cset, wd)
    return target


def patch_word(job_id: str, clip_id: str, word_index: int, text: str):
    wd = workdir_for(job_id)
    cset = storage.load_candidates(wd)
    transcript = storage.load_transcript(wd)
    for c in cset.candidates:
        if c.id != clip_id:
            continue
        if not c.words:
            sync_clip_words(c, transcript)
        if word_index < 0 or word_index >= len(c.words):
            return None
        c.words[word_index].text = text
        c.transcript = " ".join(w.text for w in c.words).strip()
        c.status = ClipStatus.EDITED
        storage.save_candidates(cset, wd)
        return c.words[word_index]
    return None


def start_render(job_id: str) -> None:
    src = source_path(job_id)
    if src is None:
        raise FileNotFoundError("No se encontró el video fuente del job")
    with _lock:
        if job_id in _running:
            raise RuntimeError("Job ocupado con otra tarea")
        _running.add(job_id)

    def _render() -> None:
        try:
            stage_render(src, only_approved=True, track=True)
        finally:
            with _lock:
                _running.discard(job_id)

    threading.Thread(target=_render, daemon=True).start()


def start_repropose(job_id: str) -> None:
    """Re-run scan+rank+refine using existing transcript/signals."""
    src = source_path(job_id)
    if src is None:
        raise FileNotFoundError("No se encontro el video fuente del job")
    wd = workdir_for(job_id)
    for name in ("transcript.json", "signals.json"):
        if not (wd / name).exists():
            raise FileNotFoundError(f"Falta {name}; corre el pipeline completo primero")
    with _lock:
        if job_id in _running:
            raise RuntimeError("Job ocupado con otra tarea")
        _running.add(job_id)

    def _repropose() -> None:
        try:
            candidates_path = wd / "candidates.json"
            if candidates_path.exists():
                candidates_path.unlink()
            stage_propose(src, track=True)
        finally:
            with _lock:
                _running.discard(job_id)

    threading.Thread(target=_repropose, daemon=True).start()


def clip_output_path(job_id: str, clip_id: str, fmt: str) -> Path | None:
    """fmt: '9x16' o '16x9'."""
    cset = get_candidates(job_id)
    if cset is None:
        return None
    for c in cset.candidates:
        if c.id != clip_id:
            continue
        path_str = c.outputs.get(fmt)
        if not path_str:
            return None
        p = Path(path_str)
        return p if p.is_file() else None
    return None


def clip_output_download(job_id: str, clip_id: str, fmt: str) -> tuple[Path, str] | None:
    """Ruta del render + nombre de descarga legible."""
    from ..export_names import build_export_filename

    path = clip_output_path(job_id, clip_id, fmt)
    if path is None:
        return None
    cset = get_candidates(job_id)
    if cset is None:
        return path, path.name
    clip = next((c for c in cset.candidates if c.id == clip_id), None)
    if clip is None:
        return path, path.name
    job_slug = decode_job_id(job_id)
    return path, build_export_filename(clip, fmt, job_slug=job_slug)


def run_job_eval(job_id: str):
    from ..config import settings
    from ..eval import run_eval

    wd = workdir_for(job_id)
    if not (wd / "candidates.json").exists():
        return None
    return run_eval(wd, n=settings.target_clips, iou_threshold=settings.eval_iou_threshold)


def get_eval_report(job_id: str):
    wd = workdir_for(job_id)
    return storage.load_eval_report(wd)


def get_golden_summary(job_id: str) -> dict:
    wd = workdir_for(job_id)
    gs = storage.load_golden(wd)
    approved = len(gs.approved())
    rejected = len(gs.rejected())
    return {"approved": approved, "rejected": rejected, "total": approved + rejected}


def get_render_prefs(job_id: str):
    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    return storage.load_render_prefs(wd)


def patch_render_prefs(job_id: str, patch) -> object | None:
    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    current = storage.load_render_prefs(wd)
    data = patch.model_dump(exclude_unset=True)
    updated = current.model_copy(update=data)
    storage.save_render_prefs(updated, wd)
    return updated


def get_caption_preview(job_id: str) -> dict | None:
    """Texto de ejemplo del primer clip aprobado según render_prefs."""
    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    cset = get_candidates(job_id)
    if cset is None:
        return None

    approved = [
        c for c in cset.candidates
        if c.status in (ClipStatus.APPROVED, ClipStatus.EDITED)
    ]
    if not approved:
        return {
            "clip_id": None,
            "clip_title": None,
            "previews": [],
            "message": "Aprobá un clip para ver el estilo de subtítulos.",
        }

    clip = approved[0]
    transcript = storage.load_transcript(wd) if (wd / "transcript.json").exists() else None
    if transcript is not None:
        words = clip_words(clip, transcript)
    else:
        words = clip.words or []

    if not words:
        return {
            "clip_id": clip.id,
            "clip_title": clip.title or clip.id,
            "previews": [],
            "message": "El clip no tiene palabras en el rango.",
        }

    prefs = storage.load_render_prefs(wd)
    previews = caption_preview_samples(
        words,
        clip.start,
        caption_style=prefs.caption_style,
        max_words=prefs.caption_social_max_words,
    )
    return {
        "clip_id": clip.id,
        "clip_title": clip.title or clip.id,
        "previews": previews,
        "message": None,
    }


def get_propose_prefs(job_id: str):
    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    return storage.load_propose_prefs(wd)


def patch_propose_prefs(job_id: str, patch) -> object | None:
    from ..propose_prefs import ProposePrefs

    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    current = storage.load_propose_prefs(wd)
    data = patch.model_dump(exclude_unset=True)
    updated = ProposePrefs.model_validate({**current.model_dump(), **data})
    storage.save_propose_prefs(updated, wd)
    return updated


def get_job_profile(job_id: str):
    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    return storage.load_job_profile(wd)


def patch_job_profile(job_id: str, profile: str):
    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    updated = JobProfile(profile=parse_profile(profile))
    storage.save_job_profile(updated, wd)
    return updated


def get_job_timeline(job_id: str) -> JobTimeline | None:
    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    if not (wd / "signals.json").exists() and not (wd / "candidates.json").exists():
        return None
    return build_job_timeline(wd)


def import_performance(job_id: str, *, raw: str, fmt: str = "json") -> PerformanceSet | None:
    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    if fmt == "csv":
        incoming = parse_performance_csv(raw)
    else:
        incoming = parse_performance_json(raw)
    merged = merge_performance(storage.load_performance(wd), incoming)
    storage.save_performance(merged, wd)
    return merged


def get_performance_report(job_id: str) -> PerformanceReport | None:
    wd = workdir_for(job_id)
    if not wd.is_dir():
        return None
    return build_performance_report(wd)
