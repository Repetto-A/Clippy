"""Aplicación FastAPI: jobs, upload, edición de clips y streaming de video."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import services
from .schemas import (
    CandidateSetResponse,
    ClipPatch,
    JobDetail,
    JobSummary,
    MessageResponse,
    ProcessPathRequest,
    WordPatch,
    job_summary,
)

STATIC_DIR = Path(__file__).resolve().parents[3] / "web" / "static"

app = FastAPI(title="Video Clipper", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/jobs", response_model=list[JobSummary])
def list_jobs() -> list[JobSummary]:
    return [job_summary(jid, rec) for jid, rec in services.list_jobs()]


@app.get("/api/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: str) -> JobDetail:
    result = services.get_job(job_id)
    if result is None:
        raise HTTPException(404, "Job no encontrado")
    rec, duration = result
    base = job_summary(services.decode_job_id(job_id), rec)
    return JobDetail(
        **base.model_dump(),
        source=rec.source,
        duration=duration,
        started_at=rec.started_at,
    )


@app.post("/api/jobs/upload", response_model=JobSummary)
async def upload_job(file: UploadFile = File(...)) -> JobSummary:
    if not file.filename:
        raise HTTPException(400, "Archivo sin nombre")
    data = await file.read()
    try:
        dest = services.save_upload(file.filename, data)
        job_id = services.start_job(dest)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    rec, _ = services.get_job(job_id) or (None, None)
    if rec is None:
        raise HTTPException(500, "No se pudo iniciar el job")
    return job_summary(job_id, rec)


@app.post("/api/jobs/from-path", response_model=JobSummary)
def process_path(body: ProcessPathRequest) -> JobSummary:
    path = Path(body.path)
    try:
        job_id = services.start_job(path)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    rec, _ = services.get_job(job_id) or (None, None)
    if rec is None:
        raise HTTPException(500, "No se pudo iniciar el job")
    return job_summary(job_id, rec)


@app.get("/api/jobs/{job_id}/candidates", response_model=CandidateSetResponse)
def get_candidates(job_id: str) -> CandidateSetResponse:
    cset = services.get_candidates(job_id)
    if cset is None:
        raise HTTPException(404, "Candidatos no disponibles todavía")
    return CandidateSetResponse(source=cset.source, candidates=cset.candidates)


@app.patch("/api/jobs/{job_id}/clips/{clip_id}")
def patch_clip(job_id: str, clip_id: str, body: ClipPatch):
    clip = services.patch_clip(job_id, clip_id, body)
    if clip is None:
        raise HTTPException(404, "Clip no encontrado")
    return clip


@app.patch("/api/jobs/{job_id}/clips/{clip_id}/words/{word_index}")
def patch_word(job_id: str, clip_id: str, word_index: int, body: WordPatch):
    word = services.patch_word(job_id, clip_id, word_index, body.text)
    if word is None:
        raise HTTPException(404, "Palabra o clip no encontrado")
    return word


@app.post("/api/jobs/{job_id}/render", response_model=MessageResponse)
def render_job(job_id: str) -> MessageResponse:
    try:
        services.start_render(job_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    return MessageResponse(message="Render iniciado")


@app.api_route(
    "/api/jobs/{job_id}/clips/{clip_id}/output/{fmt}",
    methods=["GET", "HEAD"],
)
def download_clip_output(job_id: str, clip_id: str, fmt: str) -> FileResponse:
    if fmt not in ("9x16", "16x9"):
        raise HTTPException(400, "fmt debe ser 9x16 o 16x9")
    path = services.clip_output_path(job_id, clip_id, fmt)
    if path is None:
        raise HTTPException(404, "Render no encontrado")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.post("/api/jobs/{job_id}/retry", response_model=JobSummary)
def retry_job(job_id: str) -> JobSummary:
    src = services.source_path(job_id)
    if src is None:
        result = services.get_job(job_id)
        if result and result[0].source:
            src = Path(result[0].source)
    if src is None or not src.is_file():
        raise HTTPException(404, "No se encontró el video fuente")
    try:
        services.start_job(src)
    except RuntimeError as e:
        raise HTTPException(409, str(e)) from e
    rec, _ = services.get_job(job_id) or (None, None)
    if rec is None:
        raise HTTPException(500, "No se pudo reiniciar el job")
    return job_summary(services.decode_job_id(job_id), rec)


@app.api_route("/api/jobs/{job_id}/video", methods=["GET", "HEAD"])
def stream_video(job_id: str) -> FileResponse:
    path = services.source_path(job_id)
    if path is None:
        raise HTTPException(404, "Video no encontrado")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
