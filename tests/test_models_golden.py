from video_clipper.models import (
    ClipCandidate,
    GoldenRange,
    GoldenSet,
    RejectionReason,
)


def test_clip_candidate_has_rubric_subscores_defaulting_to_zero():
    c = ClipCandidate(id="a1", start=0.0, end=20.0)
    assert c.hook_strength == 0.0
    assert c.self_contained == 0.0
    assert c.takeaway_clarity == 0.0
    assert c.payoff == 0.0
    assert c.rejection_reason is None


def test_golden_set_roundtrips_through_json():
    gs = GoldenSet(
        source="clase1",
        ranges=[
            GoldenRange(start=10.0, end=40.0, approved=True),
            GoldenRange(
                start=80.0, end=110.0, approved=False, reason=RejectionReason.BAD_HOOK
            ),
        ],
    )
    restored = GoldenSet.model_validate_json(gs.model_dump_json())
    assert restored == gs
    assert restored.ranges[1].reason is RejectionReason.BAD_HOOK


def test_golden_set_filters_approved_and_rejected():
    gs = GoldenSet(
        source="c",
        ranges=[
            GoldenRange(start=0, end=10, approved=True),
            GoldenRange(start=20, end=30, approved=False, reason=RejectionReason.WEAK_TOPIC),
        ],
    )
    assert len(gs.approved()) == 1
    assert len(gs.rejected()) == 1
    assert gs.rejected()[0].reason is RejectionReason.WEAK_TOPIC
