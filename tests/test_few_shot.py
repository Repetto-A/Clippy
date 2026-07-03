from video_clipper.few_shot import build_rank_few_shot
from video_clipper.models import GoldenRange, GoldenSet, RejectionReason, Segment, Transcript
from video_clipper.router import build_rank_prompt


def test_build_rank_few_shot_from_golden():
    transcript = Transcript(
        language="es",
        duration=120.0,
        segments=[
            Segment(text="concepto clave explicado", start=10.0, end=20.0),
            Segment(text="intro sin valor", start=0.0, end=5.0),
        ],
    )
    golden = GoldenSet(
        source="class.mp4",
        ranges=[
            GoldenRange(start=10.0, end=25.0, approved=True),
            GoldenRange(
                start=0.0, end=8.0, approved=False, reason=RejectionReason.BAD_HOOK
            ),
        ],
    )
    block = build_rank_few_shot(golden, transcript)
    assert "BUENO" in block and "MALO" in block
    assert "bad_hook" in block
    assert "[10.0-25.0]" in block


def test_rank_prompt_includes_few_shot_when_present():
    _, user = build_rank_prompt(
        {
            "clips_block": "clip x [0-10]: hola",
            "min_duration": 15,
            "max_duration": 60,
            "few_shot": "- BUENO [10-20]: demo util",
        }
    )
    assert "demo util" in user
