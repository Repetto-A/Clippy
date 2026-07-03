from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from video_clipper.api.app import app
from video_clipper.propose_prefs import ProposePrefs, default_propose_prefs
from video_clipper.storage import load_propose_prefs, save_propose_prefs


def test_default_propose_prefs():
    prefs = default_propose_prefs()
    assert prefs.target_clips >= 1
    assert prefs.min_duration <= prefs.max_duration


def test_propose_prefs_validation():
    with pytest.raises(ValueError):
        ProposePrefs(min_duration=80, max_duration=30)


def test_save_and_load_propose_prefs(tmp_path: Path):
    prefs = ProposePrefs(
        target_clips=8,
        min_duration=20.0,
        max_duration=45.0,
        rank_finalists=16,
    )
    save_propose_prefs(prefs, tmp_path)
    loaded = load_propose_prefs(tmp_path)
    assert loaded.target_clips == 8
    assert loaded.min_duration == 20.0
    assert loaded.max_duration == 45.0
    assert loaded.rank_finalists == 16


def test_api_propose_prefs_get_patch(tmp_path: Path, monkeypatch):
    job_id = "demo"
    wd = tmp_path / job_id
    wd.mkdir()
    monkeypatch.setattr("video_clipper.api.services.settings.workdir", tmp_path)

    client = TestClient(app)
    r = client.get(f"/api/jobs/{job_id}/propose-prefs")
    assert r.status_code == 200
    body = r.json()
    assert body["target_clips"] == default_propose_prefs().target_clips

    r = client.patch(
        f"/api/jobs/{job_id}/propose-prefs",
        json={"target_clips": 6, "rank_finalists": 10},
    )
    assert r.status_code == 200
    assert r.json()["target_clips"] == 6
    assert r.json()["rank_finalists"] == 10

    loaded = load_propose_prefs(wd)
    assert loaded.target_clips == 6
    assert loaded.rank_finalists == 10


def test_api_propose_prefs_404(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("video_clipper.api.services.settings.workdir", tmp_path)
    client = TestClient(app)
    r = client.get("/api/jobs/missing/propose-prefs")
    assert r.status_code == 404
