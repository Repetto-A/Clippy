from video_clipper.models import Segment, TimeRange
from video_clipper.transcript_chunks import chunk_segments, segment_line


def _seg(i: int) -> Segment:
    return Segment(text=f"seg{i}", start=i * 2.0, end=i * 2.0 + 2.0)


def _budget_for(n: int, segs: list[Segment]) -> int:
    return sum(len(segment_line(s)) + 1 for s in segs[:n])


def test_backcompat_greedy_without_silences():
    segs = [_seg(i) for i in range(5)]
    chunks = chunk_segments(segs, _budget_for(3, segs))
    assert [len(c) for c in chunks] == [3, 2]


def test_closes_at_silence_boundary_nearest_budget():
    segs = [_seg(i) for i in range(5)]
    # long silence aligned with the end of seg1 (t=4.0); seg2.end (6.0) is not aligned
    silences = [TimeRange(start=4.0, end=5.0)]
    chunks = chunk_segments(segs, _budget_for(3, segs), silences=silences)
    assert [s.start for s in chunks[0]] == [0.0, 2.0]   # closed at the silence, not at budget
    assert chunks[1][0].start == 4.0                    # remainder carried into next chunk


def test_overlap_repeats_boundary_segment():
    segs = [_seg(i) for i in range(5)]
    chunks = chunk_segments(segs, _budget_for(3, segs), overlap_segments=1)
    assert chunks[0][-1].start == chunks[1][0].start    # boundary segment appears in both
