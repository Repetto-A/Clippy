from video_clipper.models import Segment, Signals, TimeRange, Transcript
from video_clipper.scoring import LLMScorer


class FakeRouter:
    def __init__(self):
        self.calls: list[dict] = []

    def run(self, task, payload):
        self.calls.append(payload)
        return {"clips": []}


def test_llm_scorer_passes_dirty_ranges_and_chunks_on_silences():
    router = FakeRouter()
    scorer = LLMScorer()
    scorer.router = router

    segs = [
        Segment(text=f"parte {i}", start=float(i * 10), end=float(i * 10 + 5))
        for i in range(6)
    ]
    signals = Signals(
        silences=[TimeRange(start=25.0, end=26.0)],
        dirty_segments=[TimeRange(start=100.0, end=160.0)],
    )
    transcript = Transcript(language="es", duration=60.0, segments=segs)

    from video_clipper.config import settings

    old_chars = settings.llm_chunk_chars
    old_overlap = settings.chunk_overlap_segments
    try:
        settings.llm_chunk_chars = 80
        settings.chunk_overlap_segments = 1
        scorer.propose(transcript, signals)
    finally:
        settings.llm_chunk_chars = old_chars
        settings.chunk_overlap_segments = old_overlap

    assert router.calls
    payload = router.calls[0]
    assert payload["dirty_ranges"] == [(100.0, 160.0)]
    assert len(router.calls) >= 2  # chunking split the transcript
