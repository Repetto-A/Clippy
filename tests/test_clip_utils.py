from video_clipper.clip_utils import clamp_range, sync_clip_words, transcript_text, words_in_range
from video_clipper.models import ClipCandidate, Transcript, Word


def test_clamp_range_respects_duration():
    start, end = clamp_range(70.0, 85.0, duration=75.0, min_duration=10.0, max_duration=60.0)
    assert start == 65.0
    assert end == 75.0


def test_clamp_range_min_duration():
    start, end = clamp_range(10.0, 12.0, duration=100.0, min_duration=15.0, max_duration=60.0)
    assert end - start >= 15.0


def test_words_in_range():
    transcript = Transcript(
        language="es",
        duration=30.0,
        words=[
            Word(text="a", start=1.0, end=1.5),
            Word(text="b", start=5.0, end=5.5),
            Word(text="c", start=10.0, end=10.5),
        ],
    )
    words = words_in_range(transcript, 4.0, 11.0)
    assert [w.text for w in words] == ["b", "c"]


def test_sync_clip_words():
    transcript = Transcript(
        language="es",
        duration=20.0,
        words=[
            Word(text="Hola", start=2.0, end=2.5),
            Word(text="mundo", start=2.5, end=3.0),
        ],
    )
    clip = ClipCandidate(id="x", start=2.0, end=3.0)
    sync_clip_words(clip, transcript)
    assert len(clip.words) == 2
    assert transcript_text(clip.words) == "Hola mundo"
