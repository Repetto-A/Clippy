from pathlib import Path

from video_clipper import pipeline, ranker, storage
from video_clipper.models import ClipCandidate, Signals, Transcript, Word

SOURCE = Path("c.mp4")


class FakeScorer:
    def __init__(self, cands):
        self.cands = cands

    def propose(self, transcript, signals, *, propose_prefs=None):
        return self.cands


class FakeRouter:
    def __init__(self, out):
        self.out = out

    def run(self, task, payload):
        return self.out


def _setup(tmp_path, monkeypatch, scorer_mode):
    monkeypatch.setattr(pipeline.settings, "workdir", tmp_path)
    monkeypatch.setattr(pipeline.settings, "scorer", scorer_mode)
    wd = tmp_path / "c"
    wd.mkdir()
    storage.save_transcript(
        Transcript(language="es", duration=100.0,
                   words=[Word(text="x", start=10.0, end=10.5)], segments=[]),
        wd,
    )
    storage.save_signals(Signals(), wd)
    monkeypatch.setattr(
        pipeline, "get_scorer",
        lambda: FakeScorer([ClipCandidate(id="a1", start=10.0, end=30.0, score=50.0)]),
    )
    return wd


def test_stage_propose_runs_rank_on_llm_path(tmp_path, monkeypatch):
    wd = _setup(tmp_path, monkeypatch, "llm")
    monkeypatch.setattr(
        ranker, "get_router",
        lambda: FakeRouter({"clips": [{"id": "a1", "hook_strength": 90,
                                       "self_contained": 80, "takeaway_clarity": 70,
                                       "payoff": 60}]}),
    )
    pipeline.stage_propose(SOURCE, track=False)
    cset = storage.load_candidates(wd)
    assert cset.candidates[0].hook_strength == 90   # rank pass ran
    assert cset.candidates[0].score == 75.0


def test_stage_propose_skips_rank_on_heuristic_path(tmp_path, monkeypatch):
    wd = _setup(tmp_path, monkeypatch, "heuristic")
    # If rank were (wrongly) invoked, this fake returns no clips → candidate would vanish.
    monkeypatch.setattr(ranker, "get_router", lambda: FakeRouter({"clips": []}))
    pipeline.stage_propose(SOURCE, track=False)
    cset = storage.load_candidates(wd)
    assert cset.candidates[0].id == "a1"            # candidate survived → rank skipped
    assert cset.candidates[0].hook_strength == 0.0  # sub-scores untouched
