from video_clipper.models import ClipCandidate, Signals, TimeRange, Transcript, Word
from video_clipper.selection import refine


def test_refine_keeps_start_pinned_and_snaps_only_the_end():
    transcript = Transcript(
        language="es",
        duration=120.0,
        words=[Word(text="a", start=10.2, end=10.5), Word(text="b", start=44.0, end=44.5)],
        segments=[],
    )
    # silence_end at 10.0 (near the start) and silence_start at 45.0 (near the end)
    signals = Signals(silences=[TimeRange(start=9.0, end=10.0), TimeRange(start=45.0, end=46.0)])
    c = ClipCandidate(id="c1", start=10.2, end=44.3, score=90.0)

    out = refine([c], transcript, signals)

    assert out[0].start == 10.2   # hook in-point stays pinned (NOT snapped to 10.0)
    assert out[0].end == 45.0     # out-point snapped to the nearby silence start
