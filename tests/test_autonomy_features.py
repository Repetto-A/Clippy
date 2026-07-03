from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from video_clipper.api.app import app
from video_clipper.content_profile import (
    ContentProfileKind,
    JobProfile,
    propose_defaults_for_profile,
    render_defaults_for_profile,
)
from video_clipper.models import CandidateSet, ClipCandidate, ClipStatus, Signals, TimeRange, Transcript
from video_clipper.performance import (
    PerformanceSet,
    build_performance_report,
    merge_performance,
    parse_performance_csv,
    parse_performance_json,
)
from video_clipper.storage import load_job_profile, load_propose_prefs, save_candidates, save_job_profile, save_performance, save_signals
from video_clipper.timeline import build_job_timeline


def test_training_profile_matches_settings_defaults():
    training = propose_defaults_for_profile(ContentProfileKind.TRAINING)
    assert training.target_clips >= 1
    assert training.min_duration <= training.max_duration


def test_podcast_profile_differs_from_training():
    training = propose_defaults_for_profile(ContentProfileKind.TRAINING)
    podcast = propose_defaults_for_profile(ContentProfileKind.PODCAST)
    assert podcast.max_duration >= training.max_duration


def test_profile_persisted(tmp_path: Path):
    save_job_profile(JobProfile(profile=ContentProfileKind.TRAINING), tmp_path)
    loaded = load_job_profile(tmp_path)
    assert loaded.profile == ContentProfileKind.TRAINING


def test_load_propose_prefs_uses_profile_when_missing_file(tmp_path: Path):
    save_job_profile(JobProfile(profile=ContentProfileKind.PODCAST), tmp_path)
    prefs = load_propose_prefs(tmp_path)
    assert prefs.target_clips == 8


def test_build_job_timeline(tmp_path: Path):
    (tmp_path / "duration.txt").write_text("100", encoding="utf-8")
    save_signals(
        Signals(
            silences=[TimeRange(start=10, end=12)],
            dirty_segments=[TimeRange(start=50, end=55)],
        ),
        tmp_path,
    )
    save_candidates(
        CandidateSet(
            source="demo.mp4",
            candidates=[
                ClipCandidate(
                    id="c1",
                    start=20,
                    end=40,
                    score=80,
                    title="Hook fuerte",
                    hook="Mira esto",
                    status=ClipStatus.PROPOSED,
                )
            ],
        ),
        tmp_path,
    )
    tl = build_job_timeline(tmp_path, bucket_count=10)
    assert tl.duration == 100
    assert len(tl.buckets) == 10
    assert tl.clips[0].id == "c1"
    assert tl.dirty[0].start == 50


def test_performance_import_and_report(tmp_path: Path):
    save_candidates(
        CandidateSet(
            source="demo.mp4",
            candidates=[
                ClipCandidate(
                    id="c1",
                    start=0,
                    end=30,
                    score=70,
                    hook_strength=80,
                    self_contained=60,
                    takeaway_clarity=70,
                    payoff=65,
                ),
                ClipCandidate(
                    id="c2",
                    start=40,
                    end=70,
                    score=50,
                    hook_strength=40,
                    self_contained=55,
                    takeaway_clarity=45,
                    payoff=50,
                ),
            ],
        ),
        tmp_path,
    )
    incoming = parse_performance_json(
        '[{"clip_id":"c1","views":1000,"retention_pct":70},'
        '{"clip_id":"c2","views":200,"retention_pct":35}]'
    )
    merged = merge_performance(PerformanceSet(), incoming)
    save_performance(merged, tmp_path)
    report = build_performance_report(tmp_path)
    assert report.sample_size == 2
    assert report.correlations


def test_performance_csv_parser():
    raw = "clip_id,views,retention_pct\n c1 ,100,55.5\n"
    perf = parse_performance_csv(raw)
    assert perf.records[0].clip_id == "c1"
    assert perf.records[0].retention_pct == 55.5


def test_api_timeline_profile_performance(tmp_path: Path, monkeypatch):
    job_id = "demo"
    wd = tmp_path / job_id
    wd.mkdir()
    save_job_profile(JobProfile(profile=ContentProfileKind.TRAINING), wd)
    save_signals(Signals(dirty_segments=[TimeRange(start=1, end=2)]), wd)
    (wd / "duration.txt").write_text("60", encoding="utf-8")
    monkeypatch.setattr("video_clipper.api.services.settings.workdir", tmp_path)

    client = TestClient(app)
    assert client.get(f"/api/jobs/{job_id}/profile").json()["profile"] == "training"
    assert client.patch(
        f"/api/jobs/{job_id}/profile",
        json={"profile": "podcast"},
    ).json()["profile"] == "podcast"
    assert client.get(f"/api/jobs/{job_id}/timeline").status_code == 200
    assert client.post(
        f"/api/jobs/{job_id}/performance",
        json={"format": "json", "data": '[{"clip_id":"x","views":10}]'},
    ).status_code == 200
