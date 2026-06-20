"""Lectura/escritura de los artefactos JSON del workdir."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .models import CandidateSet, GoldenSet, JobStatusRecord, Signals, Transcript

if TYPE_CHECKING:
    from .eval import EvalReport


def save_transcript(t: Transcript, workdir: Path) -> Path:
    p = workdir / "transcript.json"
    p.write_text(t.model_dump_json(indent=2), encoding="utf-8")
    return p


def load_transcript(workdir: Path) -> Transcript:
    return Transcript.model_validate_json((workdir / "transcript.json").read_text(encoding="utf-8"))


def save_signals(s: Signals, workdir: Path) -> Path:
    p = workdir / "signals.json"
    p.write_text(s.model_dump_json(indent=2), encoding="utf-8")
    return p


def load_signals(workdir: Path) -> Signals:
    return Signals.model_validate_json((workdir / "signals.json").read_text(encoding="utf-8"))


def save_candidates(c: CandidateSet, workdir: Path) -> Path:
    p = workdir / "candidates.json"
    p.write_text(c.model_dump_json(indent=2), encoding="utf-8")
    return p


def load_candidates(workdir: Path) -> CandidateSet:
    return CandidateSet.model_validate_json((workdir / "candidates.json").read_text(encoding="utf-8"))


def save_golden(g: GoldenSet, workdir: Path) -> Path:
    """Persist the human golden set (labels.json), separate from candidates.json."""
    p = workdir / "labels.json"
    p.write_text(g.model_dump_json(indent=2), encoding="utf-8")
    return p


def load_golden(workdir: Path, source: str = "") -> GoldenSet:
    """Load the golden set; return an empty set (no labels yet) when the file is absent."""
    p = workdir / "labels.json"
    if not p.exists():
        return GoldenSet(source=source)
    return GoldenSet.model_validate_json(p.read_text(encoding="utf-8"))


def save_eval_report(r: EvalReport, workdir: Path) -> Path:
    """Persist the eval metric of a run against the golden set (eval_report.json)."""
    p = workdir / "eval_report.json"
    p.write_text(r.model_dump_json(indent=2), encoding="utf-8")
    return p


def save_job_status(j: JobStatusRecord, workdir: Path) -> Path:
    p = workdir / "status.json"
    p.write_text(j.model_dump_json(indent=2), encoding="utf-8")
    return p


def load_job_status(workdir: Path) -> JobStatusRecord | None:
    p = workdir / "status.json"
    if not p.exists():
        return None
    return JobStatusRecord.model_validate_json(p.read_text(encoding="utf-8"))
