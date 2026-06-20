"""Interfaz de línea de comandos del pipeline."""



from __future__ import annotations



from pathlib import Path

from typing import Annotated



import typer

from rich.console import Console



from . import job_status, pipeline, review

from .config import settings

from .models import ClipStatus, RejectionReason



app = typer.Typer(

    help="Video Clipper: detecta momentos, recorta y subtitula clips desde tus crudos.",

    no_args_is_help=True,

    add_completion=False,

)



console = Console()

SourceArg = Annotated[Path, typer.Argument(help="Ruta al crudo .mp4")]





@app.command()

def ingest(source: SourceArg) -> None:

    """Valida el crudo y extrae el audio."""

    pipeline.stage_ingest(source, track=False)





@app.command()

def transcribe(source: SourceArg) -> None:

    """Transcribe el audio con timestamps por palabra (requiere extra 'asr')."""

    pipeline.stage_transcribe(source, track=False)





@app.command()

def signals(source: SourceArg) -> None:

    """Extrae señales locales (silencios, escenas, pantalla sucia)."""

    pipeline.stage_signals(source, track=False)





@app.command()

def propose(source: SourceArg) -> None:

    """Detecta momentos y propone clips candidatos."""

    pipeline.stage_propose(source, track=False)





@app.command()

def run(

    source: SourceArg,

    auto_approve: Annotated[bool, typer.Option(help="Aprobar y renderizar todo sin revisión")] = False,

) -> None:

    """Corre el pipeline completo hasta proponer (o hasta render con --auto-approve)."""

    pipeline.run_all(source, auto_approve=auto_approve)





@app.command()

def process(

    source: SourceArg,

    auto_approve: Annotated[bool, typer.Option(help="Aprobar y renderizar todo sin revisión")] = False,

) -> None:

    """Igual que `run`, pero escribe progreso en work/{video}/status.json (para UI futura)."""

    pipeline.run_all(source, auto_approve=auto_approve, track=True)





@app.command()

def status(source: SourceArg) -> None:

    """Muestra el estado del job (status.json)."""

    workdir = settings.source_workdir(source)

    rec = job_status.load(workdir)

    if rec is None:

        console.print("[yellow]Sin status.json — todavía no se procesó este video.[/]")

        raise typer.Exit(1)

    console.print(f"[bold]{Path(source).name}[/]")

    console.print(f"  Etapa:     {rec.stage.value}")

    console.print(f"  Progreso:  {rec.progress:.0f}%")

    console.print(f"  Mensaje:   {rec.message}")

    if rec.clip_count is not None:

        console.print(f"  Clips:     {rec.clip_count}")

    if rec.error:

        console.print(f"  [red]Error:[/] {rec.error}")

    if rec.updated_at:

        console.print(f"  Actualizado: {rec.updated_at}")





@app.command(name="review")

def review_cmd(source: SourceArg) -> None:

    """Muestra la tabla de clips candidatos para revisar."""

    review.show(source)





@app.command()

def approve(source: SourceArg, clip_id: str) -> None:

    """Aprueba un clip por ID."""

    review.set_status(source, clip_id, ClipStatus.APPROVED)





@app.command()

def reject(
    source: SourceArg,
    clip_id: str,
    reason: Annotated[
        RejectionReason | None,
        typer.Option(help="Razón del rechazo (alimenta el golden set / rúbrica)"),
    ] = None,
) -> None:

    """Rechaza un clip por ID, con razón opcional."""

    review.set_status(source, clip_id, ClipStatus.REJECTED, rejection_reason=reason)





@app.command(name="set-range")

def set_range_cmd(source: SourceArg, clip_id: str, start: float, end: float) -> None:

    """Ajusta el rango (segundos) de un clip y lo marca como editado."""

    review.set_range(source, clip_id, start, end)





@app.command(name="show-words")

def show_words_cmd(source: SourceArg, clip_id: str) -> None:

    """Lista palabras del clip con índice (para edit-word)."""

    review.show_words(source, clip_id)





@app.command(name="edit-word")

def edit_word_cmd(source: SourceArg, clip_id: str, word_index: int, text: str) -> None:

    """Edita el texto de una palabra del clip (índice 0-based)."""

    review.edit_word(source, clip_id, word_index, text)





@app.command()

def render(

    source: SourceArg,

    all_clips: Annotated[bool, typer.Option("--all", help="Renderizar todos, no solo aprobados")] = False,

) -> None:

    """Renderiza los clips aprobados (9:16 y 16:9)."""

    pipeline.stage_render(source, only_approved=not all_clips, track=True)





@app.command(name="eval")
def eval_cmd(source: SourceArg) -> None:
    """Evalúa los candidatos contra el golden set (labels.json) → eval_report.json."""
    from .eval import run_eval

    workdir = settings.source_workdir(source)
    rep = run_eval(workdir, n=settings.target_clips, iou_threshold=settings.eval_iou_threshold)
    console.print(rep.model_dump())


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Host")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Puerto")] = 8765,
) -> None:
    """Levanta la UI web + API local."""
    import uvicorn

    typer.echo(f"UI: http://{host}:{port}")
    uvicorn.run("video_clipper.api.app:app", host=host, port=port, reload=False)





if __name__ == "__main__":

    app()

