# M2 — Selection Engine Implementation Plan

> Implements milestone **M2** of `docs/specs/2026-06-20-clip-selection-quality-design.md`.
> TDD: red → green → commit per task. The LLM I/O lives behind the `TaskRouter` Protocol, so
> the orchestration is tested with a fake router (no network in tests).

**Goal:** Replace the single-pass scorer with a two-pass engine (cheap **scan** → better
**rank+refine**) that scores clips on a comparable rubric scale and pins clip starts on the
hook — beating the M1 baseline.

**Architecture:** `scoring.py` stays as the scan pass; new `ranker.py` is the rank pass;
`selection.py` keeps the mechanical snap/dedup/layout but stops loosening the in-point;
`router.py` gains per-task models and a `rank_moments` prompt; `pipeline.stage_propose`
chains scan → rank → refine.

**Test runner:** `./.venv-asr/Scripts/python.exe -m pytest -q`.

---

## File map

- `transcript_chunks.py` — MODIFY: `chunk_segments` closes chunks at silence boundaries + overlap.
- `config.py` — MODIFY: `scan_model`, `rank_model`, `rank_finalists`, rubric weights.
- `router.py` — MODIFY: per-task model resolution; `build_scan_prompt`, `build_rank_prompt`.
- `models.py` — (already has sub-scores from M1) no change expected.
- `rubric.py` — CREATE: `combine_score()` pure weighting of sub-scores.
- `ranker.py` — CREATE: `rank()` pass-2 orchestration (uses an injectable router).
- `selection.py` — MODIFY: hook-first snap (out snaps to silence, in stays pinned).
- `scoring.py` / `pipeline.py` — MODIFY: chain scan → rank → refine in `stage_propose`.
- `tests/` — CREATE: `test_chunking_boundaries.py`, `test_router_tasks.py`, `test_rubric.py`,
  `test_ranker.py`, `test_selection_hookfirst.py`.

---

## Task 1 — Natural-boundary chunking

**Files:** Modify `transcript_chunks.py`; Test `tests/test_chunking_boundaries.py`.
`chunk_segments(segments, max_chars, silences=None, overlap_segments=0)`. When a chunk hits
the budget, close it after the segment whose end is nearest a silence start; carry the last
`overlap_segments` into the next chunk. `silences=None` ⇒ current behavior (back-compat).

- [ ] Test: a chunk boundary lands on a silence rather than mid-sentence; overlap repeats N segments.
- [ ] Test: `silences=None` reproduces the existing greedy split.
- [ ] Implement, run green, commit `feat(chunking): close chunks on silence boundaries + overlap`.

## Task 2 — Per-task model routing

**Files:** Modify `config.py`, `router.py`; Test `tests/test_router_tasks.py`.
Config: `scan_model`/`rank_model` (default to `llm_model`). `router.model_for_task(task)`
returns the right model; backends use it instead of `self.model` per call.

- [ ] Test: `model_for_task("score_moments")==scan_model`, `("rank_moments")==rank_model`, else `llm_model`.
- [ ] Implement, green, commit `feat(router): per-task model resolution (scan/rank tiers)`.

## Task 3 — Scan & Rank prompts

**Files:** Modify `router.py`; Test `tests/test_router_tasks.py`.
`build_scan_prompt(payload)` (recall-oriented; includes `dirty_ranges`).
`build_rank_prompt(payload)` (full finalist transcripts; asks for `hook_strength`,
`self_contained`, `takeaway_clarity`, `payoff`, hook-first `start`/`end`, `title`, `hook`).
Register both in `_PROMPTS` (`score_moments`→scan, `rank_moments`→rank).

- [ ] Test: scan prompt mentions the dirty ranges passed in.
- [ ] Test: rank prompt asks for all four sub-score field names.
- [ ] Implement, green, commit `feat(router): scan + rank prompt builders`.

## Task 4 — Rubric combine

**Files:** Create `rubric.py`; Modify `config.py`; Test `tests/test_rubric.py`.
`combine_score(hook, self_contained, takeaway, payoff, weights) -> float` (weighted, 0-100).
Config: `rubric_weights` (default equal 0.25 each).

- [ ] Test: equal weights average; custom weights honored; clamps to 0-100.
- [ ] Implement, green, commit `feat(rubric): weighted sub-score combination`.

## Task 5 — Ranker (pass 2)

**Files:** Create `ranker.py`; Test `tests/test_ranker.py`.
`rank(candidates, transcript, signals, router=None, *, target, weights) -> list[ClipCandidate]`.
Takes the top `rank_finalists` scan candidates, builds a payload with their full transcripts
(via `words_in_range`), calls `router.run("rank_moments", ...)`, maps the returned sub-scores
onto each clip, sets hook-first `start`/`end`, and `combine_score`s the final `score`. Router
is injectable so tests pass a fake returning canned JSON.

- [ ] Test (fake router): sub-scores land on clips, `score` == combined, `start`==hook word.
- [ ] Implement, green, commit `feat(ranker): pass-2 rank+refine with rubric and hook-first`.

## Task 6 — Hook-first selection refinement

**Files:** Modify `selection.py`; Test `tests/test_selection_hookfirst.py`.
Today `_snap` moves both ends. Change `refine` so the **out** snaps to a nearby silence but
the **in** stays pinned to the ranker's chosen start.

- [ ] Test: given a ranked clip + silences, `start` unchanged, `end` snapped.
- [ ] Implement, green, commit `feat(selection): keep hook in-point, snap only the out`.

## Task 7 — Wire scan → rank → refine

**Files:** Modify `pipeline.py` (`stage_propose`); Test via integration smoke with a fake.
`stage_propose`: `raw = scorer.propose(...)` → `ranked = rank(raw, ...)` (only on the LLM path;
heuristic scorer skips rank) → `selected = refine(ranked, ...)`.

- [ ] Test/smoke: end-to-end propose with a fake router yields ranked candidates with sub-scores.
- [ ] Implement, green, commit `feat(pipeline): chain scan → rank → refine in propose`.

---

## Done-when (M2 acceptance)

Run `propose` (LLM path) on a labeled class and `video-clipper eval` — `precision@N` beats the
M1 baseline `eval_report.json`. Per-reason false positives should not increase.

## Notes

- The HeuristicScorer path remains the no-API fallback and skips the rank pass.
- Real LLM calls are never made in tests — the router is faked. A manual run validates the
  live path against the baseline (the done-when).
