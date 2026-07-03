from pathlib import Path

from video_clipper import pipeline, selection, storage
from video_clipper.models import ClipCandidate, Signals, Transcript, Word
from video_clipper.propose_prefs import ProposePrefs

SOURCE = Path("c.mp4")


class FakeScorer:
    def __init__(self):
        self.last_prefs = None

    def propose(self, transcript, signals, *, propose_prefs=None):
        self.last_prefs = propose_prefs
        return [
            ClipCandidate(id="a1", start=10.0, end=50.0, score=90.0),
            ClipCandidate(id="a2", start=60.0, end=100.0, score=80.0),
            ClipCandidate(id="a3", start=110.0, end=150.0, score=70.0),
        ]


def _setup(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline.settings, "workdir", tmp_path)
    monkeypatch.setattr(pipeline.settings, "scorer", "heuristic")
    wd = tmp_path / "c"
    wd.mkdir()
    storage.save_transcript(
        Transcript(
            language="es",
            duration=200.0,
            words=[Word(text="x", start=10.0, end=10.5)],
            segments=[],
        ),
        wd,
    )
    storage.save_signals(Signals(), wd)
    fake = FakeScorer()
    monkeypatch.setattr(pipeline, "get_scorer", lambda: fake)
    return wd, fake


def test_stage_propose_uses_job_prefs(tmp_path, monkeypatch):
    wd, fake = _setup(tmp_path, monkeypatch)
    prefs = ProposePrefs(target_clips=1, min_duration=20.0, max_duration=40.0, rank_finalists=2)
    storage.save_propose_prefs(prefs, wd)

    pipeline.stage_propose(SOURCE, track=False)

    assert fake.last_prefs is not None
    assert fake.last_prefs.target_clips == 1

    cset = storage.load_candidates(wd)
    assert len(cset.candidates) == 1


def test_refine_respects_target_clips_override():
    transcript = Transcript(language="es", duration=300.0, words=[], segments=[])
    signals = Signals()
    cands = [
        ClipCandidate(id=f"c{i}", start=i * 50.0, end=i * 50.0 + 30.0, score=100 - i)
        for i in range(5)
    ]
    prefs = ProposePrefs(target_clips=2, min_duration=15.0, max_duration=60.0, rank_finalists=24)
    out = selection.refine(cands, transcript, signals, propose_prefs=prefs)
    assert len(out) == 2
