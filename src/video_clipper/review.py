"""Revisión humana por CLI: listar candidatos, aprobar/rechazar y ajustar rangos/subtítulos."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import storage
from .clip_utils import clamp_range, sync_clip_words
from .config import settings
from .models import ClipStatus, GoldenRange, RejectionReason

console = Console()


def _fmt(t: float) -> str:
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def _duration_for(source: Path, workdir: Path) -> float:
    dur_file = workdir / "duration.txt"
    if dur_file.exists():
        return float(dur_file.read_text(encoding="utf-8"))
    if (workdir / "transcript.json").exists():
        return storage.load_transcript(workdir).duration
    return 0.0


def show(source: Path) -> None:
    workdir = settings.source_workdir(source)
    cset = storage.load_candidates(workdir)

    table = Table(title=f"Clips candidatos · {Path(source).name}")
    table.add_column("ID", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Inicio")
    table.add_column("Fin")
    table.add_column("Dur", justify="right")
    table.add_column("Layout")
    table.add_column("Estado")
    table.add_column("Palabras", justify="right")
    table.add_column("Título")

    for c in sorted(cset.candidates, key=lambda x: x.start):
        style = {
            ClipStatus.APPROVED: "green",
            ClipStatus.REJECTED: "red dim",
            ClipStatus.EDITED: "yellow",
        }.get(c.status, "")
        table.add_row(
            c.id, f"{c.score:.0f}", _fmt(c.start), _fmt(c.end), f"{c.duration:.0f}s",
            c.layout.value, c.status.value, str(len(c.words)), (c.title or "")[:50], style=style,
        )
    console.print(table)


def set_status(
    source: Path,
    clip_id: str,
    status: ClipStatus,
    rejection_reason: RejectionReason | None = None,
) -> None:
    workdir = settings.source_workdir(source)
    cset = storage.load_candidates(workdir)
    for c in cset.candidates:
        if c.id == clip_id:
            c.status = status
            if status is ClipStatus.REJECTED:
                c.rejection_reason = rejection_reason
            storage.save_candidates(cset, workdir)
            _record_golden(workdir, cset.source, c, status, rejection_reason)
            suffix = f" ({rejection_reason.value})" if rejection_reason else ""
            console.print(f"[green]{clip_id}[/] -> {status.value}{suffix}")
            return
    console.print(f"[red]No se encontró el clip {clip_id}[/]")


def record_golden(workdir: Path, source: str, clip, status: ClipStatus, reason: RejectionReason | None) -> None:
    """Persist approve/reject judgment into labels.json (golden set)."""
    _record_golden(workdir, source, clip, status, reason)


def _record_golden(workdir, source, clip, status, reason) -> None:
    """Persist the human judgment of a clip into the golden set (labels.json).

    Only approve/reject are recorded; re-judging the same time range replaces its entry.
    """
    if status not in (ClipStatus.APPROVED, ClipStatus.REJECTED):
        return
    gs = storage.load_golden(workdir, source=source)
    gs.ranges = [
        r for r in gs.ranges if not (r.start == clip.start and r.end == clip.end)
    ]
    gs.ranges.append(
        GoldenRange(
            start=clip.start,
            end=clip.end,
            approved=(status is ClipStatus.APPROVED),
            reason=reason if status is ClipStatus.REJECTED else None,
        )
    )
    storage.save_golden(gs, workdir)


def set_range(source: Path, clip_id: str, start: float, end: float) -> None:
    workdir = settings.source_workdir(source)
    cset = storage.load_candidates(workdir)
    duration = _duration_for(source, workdir)
    transcript = storage.load_transcript(workdir) if (workdir / "transcript.json").exists() else None

    for c in cset.candidates:
        if c.id == clip_id:
            c.start, c.end = clamp_range(start, end, duration)
            if transcript is not None:
                sync_clip_words(c, transcript)
            c.status = ClipStatus.EDITED
            storage.save_candidates(cset, workdir)
            console.print(
                f"[green]{clip_id}[/] rango -> {_fmt(c.start)}-{_fmt(c.end)} "
                f"({len(c.words)} palabras, editado)"
            )
            return
    console.print(f"[red]No se encontró el clip {clip_id}[/]")


def edit_word(source: Path, clip_id: str, word_index: int, text: str) -> None:
    """Edita el texto de una palabra del clip (índice 0-based en clip.words)."""
    workdir = settings.source_workdir(source)
    cset = storage.load_candidates(workdir)
    transcript = storage.load_transcript(workdir)

    for c in cset.candidates:
        if c.id != clip_id:
            continue
        if not c.words:
            sync_clip_words(c, transcript)
        if word_index < 0 or word_index >= len(c.words):
            console.print(f"[red]Índice fuera de rango (0-{len(c.words) - 1})[/]")
            return
        c.words[word_index].text = text
        c.transcript = " ".join(w.text for w in c.words).strip()
        c.status = ClipStatus.EDITED
        storage.save_candidates(cset, workdir)
        console.print(f"[green]{clip_id}[/] palabra {word_index} -> {text!r}")
        return
    console.print(f"[red]No se encontró el clip {clip_id}[/]")


def show_words(source: Path, clip_id: str) -> None:
    """Lista palabras del clip con índice (útil para edit-word)."""
    workdir = settings.source_workdir(source)
    cset = storage.load_candidates(workdir)
    transcript = storage.load_transcript(workdir)

    for c in cset.candidates:
        if c.id != clip_id:
            continue
        if not c.words:
            sync_clip_words(c, transcript)
            storage.save_candidates(cset, workdir)
        table = Table(title=f"Palabras · {clip_id}")
        table.add_column("#", justify="right")
        table.add_column("Inicio")
        table.add_column("Fin")
        table.add_column("Texto")
        for i, w in enumerate(c.words):
            table.add_row(str(i), _fmt(w.start), _fmt(w.end), w.text.strip())
        console.print(table)
        return
    console.print(f"[red]No se encontró el clip {clip_id}[/]")
