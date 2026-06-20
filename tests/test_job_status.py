from pathlib import Path

from video_clipper import job_status, storage
from video_clipper.models import JobStage


def test_job_status_roundtrip(tmp_path: Path):
    workdir = tmp_path / "job"
    workdir.mkdir()
    source = tmp_path / "video.mp4"

    job_status.init(workdir, source)
    rec = job_status.set_status(
        workdir,
        stage=JobStage.TRANSCRIBING,
        progress=25.0,
        message="Transcribiendo…",
    )
    assert rec.stage == JobStage.TRANSCRIBING
    assert rec.progress == 25.0

    loaded = storage.load_job_status(workdir)
    assert loaded is not None
    assert loaded.message == "Transcribiendo…"

    failed = job_status.fail(workdir, "boom")
    assert failed.stage == JobStage.FAILED
    assert failed.error == "boom"
