from video_clipper.models import Segment
from video_clipper.transcript_chunks import chunk_segments, clips_target_for_chunk, lines_from_segments


def test_chunk_segments_splits_on_size():
    segs = [
        Segment(text="a" * 100, start=float(i), end=float(i) + 1)
        for i in range(200)
    ]
    chunks = chunk_segments(segs, max_chars=500)
    assert len(chunks) > 1
    assert sum(len(c) for c in chunks) == len(segs)


def test_lines_from_segments():
    segs = [Segment(text="Hola", start=1.0, end=2.0)]
    assert "[1.0-2.0] Hola" in lines_from_segments(segs)


def test_clips_target_single_chunk():
    assert clips_target_for_chunk(0, 1, 12, 6) == 12


def test_clips_target_multi_chunk():
    n = clips_target_for_chunk(0, 3, 12, 4)
    assert n >= 2
