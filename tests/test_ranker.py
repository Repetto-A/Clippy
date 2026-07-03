from video_clipper.models import ClipCandidate, GoldenRange, GoldenSet, Segment, Signals, Transcript, Word
from video_clipper.ranker import rank


class FakeRouter:
    def __init__(self, out):
        self.out = out
        self.calls = []

    def run(self, task, payload):
        self.calls.append((task, payload))
        return self.out


def _transcript():
    return Transcript(
        language="es",
        duration=200.0,
        words=[Word(text="hola", start=10.0, end=10.5), Word(text="mundo", start=29.0, end=29.5)],
        segments=[],
    )


def test_rank_applies_subscores_hookfirst_boundaries_and_combined_score():
    cands = [ClipCandidate(id="a1", start=10.0, end=30.0, score=50.0)]
    fake = FakeRouter(
        {
            "clips": [
                {
                    "id": "a1",
                    "hook_strength": 90,
                    "self_contained": 80,
                    "takeaway_clarity": 70,
                    "payoff": 60,
                    "start": 12.0,
                    "end": 28.0,
                    "title": "T",
                    "hook": "H",
                    "reason": "R",
                }
            ]
        }
    )
    out = rank(cands, _transcript(), Signals(), router=fake, weights=(0.25, 0.25, 0.25, 0.25))

    assert fake.calls[0][0] == "rank_moments"
    c = out[0]
    assert (c.hook_strength, c.self_contained, c.takeaway_clarity, c.payoff) == (90, 80, 70, 60)
    assert c.start == 12.0 and c.end == 28.0   # hook-first boundaries from the ranker
    assert c.score == 75.0                     # combine of 90/80/70/60 at equal weights
    assert c.title == "T" and c.hook == "H"


def test_rank_orders_by_combined_score_and_drops_unreturned():
    cands = [
        ClipCandidate(id="lo", start=0, end=20, score=99),
        ClipCandidate(id="hi", start=40, end=60, score=10),
    ]
    fake = FakeRouter(
        {
            "clips": [
                {"id": "hi", "hook_strength": 100, "self_contained": 100,
                 "takeaway_clarity": 100, "payoff": 100},
                {"id": "lo", "hook_strength": 10, "self_contained": 10,
                 "takeaway_clarity": 10, "payoff": 10},
            ]
        }
    )
    out = rank(cands, _transcript(), Signals(), router=fake, weights=(0.25, 0.25, 0.25, 0.25))
    assert [c.id for c in out] == ["hi", "lo"]   # re-ranked by rubric, not by scan score


def test_rank_empty_returns_empty():
    assert rank([], _transcript(), Signals(), router=FakeRouter({"clips": []})) == []


def test_rank_fallback_keeps_scan_score_when_llm_omits_clip():
    cands = [
        ClipCandidate(id="a", start=10.0, end=30.0, score=80.0),
        ClipCandidate(id="b", start=40.0, end=60.0, score=70.0),
    ]
    fake = FakeRouter(
        {
            "clips": [
                {
                    "id": "a",
                    "hook_strength": 90,
                    "self_contained": 90,
                    "takeaway_clarity": 90,
                    "payoff": 90,
                }
            ]
        }
    )
    out = rank(cands, _transcript(), Signals(), router=fake, weights=(0.25, 0.25, 0.25, 0.25))
    assert len(out) == 2
    by_id = {c.id: c for c in out}
    assert by_id["a"].score == 90.0
    assert by_id["b"].score == 70.0


def test_rank_passes_few_shot_in_payload():
    cands = [ClipCandidate(id="a1", start=10.0, end=30.0, score=50.0)]
    fake = FakeRouter({"clips": []})
    golden = GoldenSet(
        source="x",
        ranges=[GoldenRange(start=10.0, end=20.0, approved=True)],
    )
    transcript = Transcript(
        language="es",
        duration=200.0,
        segments=[Segment(text="demo", start=10.0, end=20.0)],
    )
    rank(cands, transcript, Signals(), router=fake, golden=golden)
    assert "few_shot" in fake.calls[0][1]
    assert "BUENO" in fake.calls[0][1]["few_shot"]


def test_rank_retries_on_router_failure():
    class FlakyRouter:
        def __init__(self):
            self.calls = 0

        def run(self, task, payload):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("timeout")
            return {
                "clips": [
                    {
                        "id": "x",
                        "hook_strength": 50,
                        "self_contained": 50,
                        "takeaway_clarity": 50,
                        "payoff": 50,
                    }
                ]
            }

    cands = [ClipCandidate(id="x", start=0, end=20, score=10)]
    router = FlakyRouter()
    out = rank(cands, _transcript(), Signals(), router=router)
    assert router.calls == 2
    assert len(out) == 1 and out[0].score == 50.0
