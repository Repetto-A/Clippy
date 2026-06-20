from video_clipper.eval import EvalReport, evaluate, iou
from video_clipper.models import (
    ClipCandidate,
    GoldenRange,
    GoldenSet,
    RejectionReason,
)


def test_iou_known_cases():
    assert iou(0, 10, 0, 10) == 1.0
    assert iou(0, 10, 20, 30) == 0.0
    assert iou(0, 10, 5, 15) == 1 / 3  # intersection 5, union 15


def test_precision_recall_and_reason_breakdown():
    golden = GoldenSet(
        source="c1",
        ranges=[
            GoldenRange(start=10, end=30, approved=True),    # good A
            GoldenRange(start=100, end=120, approved=True),  # good B
            GoldenRange(
                start=200, end=220, approved=False, reason=RejectionReason.BAD_HOOK
            ),  # known-bad
        ],
    )
    proposed = [
        ClipCandidate(id="p1", start=11, end=31, score=90),    # matches good A
        ClipCandidate(id="p2", start=201, end=219, score=80),  # lands on known-bad
        ClipCandidate(id="p3", start=400, end=420, score=70),  # nothing
    ]
    rep = evaluate(proposed, golden, n=3, iou_threshold=0.5)
    assert isinstance(rep, EvalReport)
    assert rep.matched == 1                       # only p1
    assert rep.precision_at_n == 1 / 3
    assert rep.recall == 1 / 2                     # 1 of 2 approved covered
    assert rep.false_positives_by_reason["bad_hook"] == 1


def test_top_n_uses_score_ordering():
    golden = GoldenSet(source="c", ranges=[GoldenRange(start=0, end=20, approved=True)])
    proposed = [
        ClipCandidate(id="low", start=0, end=20, score=10),   # would match but low score
        ClipCandidate(id="hi", start=500, end=520, score=99),  # high score, no match
    ]
    rep = evaluate(proposed, golden, n=1, iou_threshold=0.5)
    assert rep.n == 1
    assert rep.matched == 0  # only the top-1 (hi) is considered, it doesn't match


def test_empty_golden_does_not_crash():
    proposed = [ClipCandidate(id="p", start=0, end=10, score=50)]
    rep = evaluate(proposed, GoldenSet(source="c"), n=12, iou_threshold=0.5)
    assert rep.recall == 0.0
    assert rep.precision_at_n == 0.0
