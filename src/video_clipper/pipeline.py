"""Orquestación del pipeline por etapas. Cada etapa lee/escribe artefactos en el workdir."""



from __future__ import annotations



from pathlib import Path



from rich.console import Console



from . import job_status, storage

from .config import settings

from .ingest import ingest

from .models import CandidateSet, ClipStatus, JobStage

from .render import render_clip_cwd

from .scoring import get_scorer

from .ranker import rank

from .selection import refine

from .signals import extract_signals

from .transcribe import get_transcriber



console = Console()





def _workdir(source: Path) -> Path:

    wd = settings.source_workdir(source)

    wd.mkdir(parents=True, exist_ok=True)

    return wd





def stage_ingest(source: Path, *, track: bool = True) -> Path:

    workdir = _workdir(source)

    if track:

        job_status.set_status(workdir, stage=JobStage.INGESTING, progress=5, message="Validando y extrayendo audio...")

    info, _ = ingest(source, workdir)

    (workdir / "duration.txt").write_text(str(info.duration), encoding="utf-8")

    if track:

        job_status.set_status(workdir, progress=10, message="Audio extraído")

    return workdir





def stage_transcribe(source: Path, *, track: bool = True) -> None:

    workdir = _workdir(source)

    if track:

        job_status.set_status(

            workdir, stage=JobStage.TRANSCRIBING, progress=15, message="Transcribiendo (puede tardar varios minutos)...",

        )

    transcriber = get_transcriber()

    def _progress(pct: float, msg: str) -> None:
        if track:
            job_status.set_status(workdir, progress=15 + pct * 40, message=msg)

    transcript = transcriber.transcribe(workdir / "audio.wav", on_progress=_progress if track else None)

    storage.save_transcript(transcript, workdir)

    if track:

        job_status.set_status(workdir, progress=55, message="Transcripción lista")





def stage_signals(source: Path, *, track: bool = True) -> None:

    workdir = _workdir(source)

    if track:

        job_status.set_status(workdir, stage=JobStage.SIGNALS, progress=60, message="Extrayendo senales locales...")

    dur_file = workdir / "duration.txt"

    duration = float(dur_file.read_text(encoding="utf-8")) if dur_file.exists() else 0.0

    signals = extract_signals(source, workdir / "audio.wav", duration)

    storage.save_signals(signals, workdir)

    if track:

        job_status.set_status(workdir, progress=70, message="Señales listas")





def stage_propose(source: Path, *, track: bool = True) -> None:

    workdir = _workdir(source)

    if track:

        job_status.set_status(workdir, stage=JobStage.PROPOSING, progress=75, message="Detectando momentos...")

    transcript = storage.load_transcript(workdir)

    signals = storage.load_signals(workdir)

    propose_prefs = storage.load_propose_prefs(workdir)

    scorer = get_scorer()

    raw = scorer.propose(transcript, signals, propose_prefs=propose_prefs)

    # Pasada 2 (rank+refine) solo en el path LLM; el heurístico no llama al modelo.
    if settings.scorer != "heuristic":
        golden = storage.load_golden(workdir, str(source))
        raw = rank(
            raw,
            transcript,
            signals,
            golden=golden,
            finalists=propose_prefs.rank_finalists,
            min_duration=propose_prefs.min_duration,
            max_duration=propose_prefs.max_duration,
        )

    selected = refine(raw, transcript, signals, propose_prefs=propose_prefs)

    storage.save_candidates(CandidateSet(source=str(source), candidates=selected), workdir)

    console.log(f"[bold green]Propuesta guardada[/]: {len(selected)} clips para revisar")

    if track:

        job_status.set_status(

            workdir,

            stage=JobStage.READY_FOR_REVIEW,

            progress=100,

            message=f"{len(selected)} clips listos para revisar",

            clip_count=len(selected),

        )





def stage_render(source: Path, only_approved: bool = True, *, track: bool = True) -> None:

    workdir = _workdir(source)

    transcript = storage.load_transcript(workdir)

    cset = storage.load_candidates(workdir)

    clips_dir = workdir / "clips"
    prefs = storage.load_render_prefs(workdir)



    targets = [

        c for c in cset.candidates

        if (not only_approved) or c.status in (ClipStatus.APPROVED, ClipStatus.EDITED)

    ]

    if not targets:

        console.print("[yellow]No hay clips aprobados para renderizar. Usá el comando 'review' primero.[/]")

        return



    if track:

        job_status.set_status(

            workdir, stage=JobStage.RENDERING, progress=0, message=f"Renderizando {len(targets)} clips...",

        )



    for i, c in enumerate(targets):

        c.outputs = render_clip_cwd(Path(source), c, transcript, clips_dir, prefs=prefs)

        if track:

            pct = round((i + 1) / len(targets) * 100, 1)

            job_status.set_status(workdir, progress=pct, message=f"Render {i + 1}/{len(targets)}")



    storage.save_candidates(cset, workdir)

    if track:

        job_status.set_status(

            workdir,

            stage=JobStage.COMPLETED,

            progress=100,

            message=f"{len(targets)} clips renderizados",

            clip_count=len(targets),

        )

    console.log(f"[bold green]Render completo[/]: {len(targets)} clips en {clips_dir}")





def run_all(source: Path, auto_approve: bool = False, *, track: bool = True, init: bool = True, resume: bool = True) -> None:

    """Pipeline completo hasta proponer. El render queda tras la revision humana.

    Con resume=True (default) salta etapas cuyos artefactos ya existen en el workdir.
    """

    workdir = _workdir(source)

    if track and init:

        job_status.init(workdir, source)

    def _exists(name: str) -> bool:
        return (workdir / name).is_file()

    try:

        if not resume or not _exists("audio.wav"):
            stage_ingest(source, track=track)
        elif track:
            job_status.set_status(workdir, progress=10, message="Audio ya extraido (resume)")

        if not resume or not _exists("transcript.json"):
            stage_transcribe(source, track=track)
        elif track:
            job_status.set_status(workdir, progress=55, message="Transcripcion lista (resume)")

        if not resume or not _exists("signals.json"):
            stage_signals(source, track=track)
        elif track:
            job_status.set_status(workdir, progress=70, message="Senales listas (resume)")

        if not resume or not _exists("candidates.json"):
            stage_propose(source, track=track)
        elif track:
            cset = storage.load_candidates(workdir)
            job_status.set_status(
                workdir,
                stage=JobStage.READY_FOR_REVIEW,
                progress=100,
                message=f"{len(cset.candidates)} clips listos (resume)",
                clip_count=len(cset.candidates),
            )

        if auto_approve:

            cset = storage.load_candidates(workdir)

            for c in cset.candidates:

                c.status = ClipStatus.APPROVED

            storage.save_candidates(cset, workdir)

            stage_render(source, track=track)

    except Exception as exc:

        if track:

            job_status.fail(workdir, str(exc))

        raise


