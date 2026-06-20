from pathlib import Path

from video_clipper import review, storage
from video_clipper.models import (
    CandidateSet,
    ClipCandidate,
    ClipStatus,
    RejectionReason,
)

SOURCE = Path("c1.mp4")


def _workdir(tmp_path, monkeypatch):
    # source_workdir(source) == settings.workdir / source.stem
    monkeypatch.setattr(review.settings, "workdir", tmp_path)
    wd = tmp_path / "c1"
    wd.mkdir()
    return wd


def _seed(wd):
    storage.save_candidates(
        CandidateSet(
            source="c1",
            candidates=[ClipCandidate(id="a1", start=10.0, end=30.0, score=80.0)],
        ),
        wd,
    )


def test_rejecting_with_reason_writes_a_rejected_golden_range(tmp_path, monkeypatch):
    wd = _workdir(tmp_path, monkeypatch)
    _seed(wd)
    review.set_status(SOURCE, "a1", ClipStatus.REJECTED, rejection_reason=RejectionReason.BAD_HOOK)
    gs = storage.load_golden(wd)
    assert len(gs.rejected()) == 1
    r = gs.rejected()[0]
    assert (r.start, r.end) == (10.0, 30.0)
    assert r.reason is RejectionReason.BAD_HOOK


def test_approving_writes_an_approved_golden_range(tmp_path, monkeypatch):
    wd = _workdir(tmp_path, monkeypatch)
    _seed(wd)
    review.set_status(SOURCE, "a1", ClipStatus.APPROVED)
    gs = storage.load_golden(wd)
    assert len(gs.approved()) == 1
    assert gs.approved()[0].reason is None


def test_re_judging_same_clip_replaces_its_golden_range(tmp_path, monkeypatch):
    wd = _workdir(tmp_path, monkeypatch)
    _seed(wd)
    review.set_status(SOURCE, "a1", ClipStatus.REJECTED, rejection_reason=RejectionReason.WEAK_TOPIC)
    review.set_status(SOURCE, "a1", ClipStatus.APPROVED)
    gs = storage.load_golden(wd)
    assert len(gs.ranges) == 1            # not duplicated
    assert gs.ranges[0].approved is True
