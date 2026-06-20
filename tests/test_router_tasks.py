from video_clipper.config import settings
from video_clipper.router import build_rank_prompt, build_scan_prompt, model_for_task


def test_model_for_task_maps_scan_and_rank(monkeypatch):
    monkeypatch.setattr(settings, "scan_model", "flash")
    monkeypatch.setattr(settings, "rank_model", "pro")
    monkeypatch.setattr(settings, "llm_model", "default")
    assert model_for_task("score_moments") == "flash"
    assert model_for_task("rank_moments") == "pro"
    assert model_for_task("translate") == "default"


def test_scan_prompt_surfaces_dirty_ranges():
    system, user = build_scan_prompt(
        {
            "transcript_lines": "[0.0-5.0] hola",
            "min_duration": 15,
            "max_duration": 60,
            "target_clips": 8,
            "dirty_ranges": [(100.0, 160.0)],
        }
    )
    assert "100" in user and "160" in user


def test_rank_prompt_asks_for_all_subscores():
    system, user = build_rank_prompt(
        {
            "clips_block": "clip a1 [10-30]: bla bla",
            "min_duration": 15,
            "max_duration": 60,
        }
    )
    for field in ("hook_strength", "self_contained", "takeaway_clarity", "payoff"):
        assert field in user
