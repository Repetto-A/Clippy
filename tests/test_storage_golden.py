from video_clipper import storage
from video_clipper.models import GoldenRange, GoldenSet, RejectionReason


def test_golden_roundtrip(tmp_path):
    gs = GoldenSet(
        source="c1",
        ranges=[
            GoldenRange(start=5.0, end=25.0, approved=True),
            GoldenRange(
                start=60.0, end=90.0, approved=False, reason=RejectionReason.WEAK_TOPIC
            ),
        ],
    )
    storage.save_golden(gs, tmp_path)
    assert (tmp_path / "labels.json").exists()
    assert storage.load_golden(tmp_path) == gs


def test_load_golden_returns_empty_set_when_absent(tmp_path):
    gs = storage.load_golden(tmp_path, source="c1")
    assert gs.source == "c1"
    assert gs.ranges == []
