# Video Clipper — Design Spec: Clip Selection Quality

- **Date:** 2026-06-20
- **Status:** Approved for writing implementation plans (per milestone)
- **Author:** Ale (+ assistant)
- **Related:** `2026-06-18-video-clipper-design.md` (base pipeline design)

## 1. Context and goal

The base pipeline (ingest → transcribe → signals → scoring → selection → review →
reframe → render) already runs end-to-end on real classes. The goal of this spec is to
**raise moment-selection quality to Opus-Clip level**, adapted to Spanish educational
content with a slide + webcam layout, and to build the infrastructure to **measure** that
quality instead of judging it by eye.

Conceptual reference: Opus Clip isn't good because of its prompt — it's good because it
measures what performed and adjusts. We don't have social-media telemetry, but we do have
Ale's human judgment during review (`ClipStatus`), which we turn into an evaluation signal.

Scope covers four subsystems in **a single spec**, with **separate implementation plans per
milestone** (M1–M4, see §9).

## 2. Diagnosis: why current selection caps quality

Three harness bugs limit quality regardless of the prompt:

1. **Scores not comparable across chunks.** `LLMScorer` scores each chunk on its own 0–100
   scale, and `selection.refine()` sorts globally and takes the top-N. Different scales get
   compared.
2. **Blind chunk boundaries.** `chunk_segments` splits by a character budget, ignoring
   silences and topics. A moment straddling a boundary is never seen whole.
3. **Single pass.** No global re-ranking (the base design doc already called for
   filter→refine; today it's filter only).

Bonus: the "dirty screen" signal is applied as a post-hoc penalty only at the clip's
midpoint; the model never sees it while choosing.

## 3. Design decisions (agreed)

| Decision | Choice | Rationale |
|---|---|---|
| Packaging | One spec; plans per milestone | Coherent north star, incremental execution |
| Eval signal | Binary (approved/rejected) + rejection reason | Each reason calibrates a rubric sub-score |
| Milestone order | Eval → Engine → API → Render | Measure before moving the brain |
| Scoring architecture | Two passes: scan → rank+refine | Global calibration + boundary refinement |
| Models | Two tiers (cheap scan / better rank), per-task router | Scan processes the bulk of tokens; that's where the savings are |
| Pass 2 | New module `ranker.py` | Respects responsibility separation (screaming architecture) |

Guiding principle: **don't rewrite the pipeline** — insert and modify stages surgically,
respecting the existing separation of responsibilities.

## 4. Overall architecture

```
ingest → transcribe → signals → CHUNK(natural boundaries)
   → SCAN (cheap tier, high recall, approx boundaries, sees dirty ranges)
   → RANK+REFINE (better tier, single comparable rubric scale, hook-first in/out)
   → select (snap/dedup/layout — mechanical)
   → review (captures binary + reason)
   → render
                    ▲
        EVAL compares output vs golden set ──┘
```

### Changes per module

| Module | Change |
|---|---|
| `transcript_chunks.py` | Splits at the long silence nearest the char budget (reuses `signals.silences`), with a small overlap. Eliminates mid-moment cuts. No extra LLM cost. |
| `scoring.py` | Pass 1 (Scan): `LLMScorer.propose` becomes the scan — cheap model, high recall, approximate boundaries, per chunk. Receives `dirty_segments` in the prompt so it avoids them. |
| `ranker.py` (NEW) | Pass 2 (Rank+Refine): takes the scan's top-N, sends their full transcripts together to the better model, scores them on the rubric in one comparable scale, picks hook-first in/out, writes title/hook. |
| `selection.py` | Slimmed down: keeps the mechanical parts (snap out-point to silence, clamp, dedup by overlap, A/B layout). The global sort is no longer a bug because scores now come from a single rank pass. |
| `router.py` | Per-task model (`scan_model`/`rank_model`), new `rank_moments` task, structured outputs (M3). |
| `models.py` | `ClipCandidate` gains sub-scores and `rejection_reason`; `RejectionReason` enum; `GoldenSet` model. |
| `eval.py` (NEW) | Persists human judgment (golden set), computes the metric (precision@N + per-reason breakdown). |
| `signals.py` | No functional change; its silences now feed chunking. |

## 5. Components in detail

### 5.1 Natural-boundary chunking

`chunk_segments(segments, max_chars, silences)` groups segments up to the char budget and
**closes the chunk at the nearest long silence** (not an arbitrary cut). A configurable
**overlap** (e.g. 1–2 segments) is added between consecutive chunks so a moment at the
boundary is visible from both sides. Downstream dedup removes any duplicates the overlap
produces.

Timestamps remain absolute relative to the raw video.

### 5.2 Pass 1 — Scan (`scoring.py`)

- Cheap tier (`scan_model`).
- Goal: **recall**, not precision. Better to over-produce candidates than miss a good moment.
- Per chunk. Receives lines with absolute timestamps and the `dirty` ranges to avoid.
- Returns many candidates with approximate `start`/`end`, a single provisional score, and a
  one-line reason.
- `HeuristicScorer` stays as the no-API fallback.

### 5.3 Pass 2 — Rank + Refine (`ranker.py`)

- Better tier (`rank_model`).
- Receives the **full** transcripts of the scan's top-N finalists, with word-level timing
  (to pick the exact in-point on the hook).
- Judges them **head-to-head on a single comparable scale** (fixes the non-comparable-scores
  bug).
- Returns per clip: the 4 rubric sub-scores, hook-first `in`/`out`, `title`, `hook`, reason.
- Few-shot: 1–2 good-vs-bad clip examples for Spanish educational content. These examples are
  **seeded from the golden set** (the reasoned rejections) once it exists → the prompt learns
  from what Ale rejected.

### 5.4 Rubric

Four sub-scores 0–100, combined with weights in config (tunable without re-prompting):

| Sub-score | Question | Rejection reason that calibrates it |
|---|---|---|
| `hook_strength` | Do the first ~3s land on their own? | `bad_hook` |
| `self_contained` | Does it make sense without the rest of the class? | `not_self_contained` |
| `takeaway_clarity` | Does it deliver ONE clear idea? | `weak_topic` |
| `payoff` | Does it close on a resolution/punchline? | `bad_cut` |

`final_score = Σ(weight_i · subscore_i)`. "Dirty screen" (`dirty_screen`) is **not** a rubric
dimension: it's filtered earlier via the `dirty` signal injected into the scan prompt.

### 5.5 Hook-first refinement

The ranker returns exact word-level in/out. `selection.py` then:
- snaps the **out** to the nearby silence (so the clip breathes at the close),
- **keeps the in pinned to the hook word** — never loosens it, because retention is decided
  there.

The model proposes duration based on the idea's natural boundary; `clamp_range` constrains it
to min/max afterward.

### 5.6 Per-task router (`router.py`)

- `settings` adds `scan_model` and `rank_model` (alongside the current `llm_model` as the
  default).
- New `rank_moments` task with its `build_rank_prompt`.
- Each backend (opencode, ollama, anthropic) resolves the task with its assigned model.
- On opencode today: `scan_model = deepseek-v4-flash`, `rank_model = deepseek-v4-pro`.
  On Anthropic (M3): scan Haiku/Sonnet, rank Sonnet/Opus.

### 5.7 Eval loop and golden set (`eval.py`)

- **Golden set per class**, by time range (not by ID, because the new engine produces
  different boundaries): a set of **approved** ranges + **rejected** ranges with reasons.
- Persisted in `labels.json`, **separate from `candidates.json`**, so re-running a stage
  doesn't overwrite human judgment.
- Metric:
  - `precision@N`: fraction of the top-N proposed clips that overlap (IoU > threshold) an
    approved range.
  - `recall`: fraction of approved ranges covered.
  - **Per-reason breakdown**: how many proposed clips fall on a range rejected for each
    category → detects per-dimension regressions.
- Enables A/B: two prompt versions over the same labeled classes.

### 5.8 Data model (`models.py`)

- `ClipCandidate` gains: `hook_strength`, `self_contained`, `takeaway_clarity`, `payoff`
  (floats 0–100) and `rejection_reason: RejectionReason | None`.
- `RejectionReason` enum: `bad_hook` | `not_self_contained` | `bad_cut` | `dirty_screen` |
  `weak_topic`.
- `GoldenSet` model (approved/rejected ranges per class) → `labels.json` artifact.
- The review UI (CLI + web) adds the reason field on rejection.

## 6. Prompts (skeletons)

### Scan (Pass 1)
- **System:** editor of Spanish educational shorts; mark candidates **generously**, don't
  filter; better to over-produce than miss a good moment.
- **User:** chunk lines `[start-end] text` (absolute timestamps) + `dirty` ranges to avoid;
  return up to N candidates with `start`, `end`, `score` (0–100), `reason`.

### Rank + Refine (Pass 2)
- **System:** **demanding** editor; you judge finalists head-to-head on a single scale; be
  strict; the clip must open on the hook and close on the payoff.
- **User:** full transcripts of the finalists with word-level timing + good/bad few-shot;
  return per clip the 4 sub-scores, exact `in`/`out`, `title`, `hook`, `reason`.

## 7. Data flow and artifacts

```
workdir/<class>/
  audio.wav
  transcript.json
  signals.json
  candidates.json          # candidates + review state (regenerable)
  labels.json              # NEW: golden set (human judgment, persistent)
  eval_report.json         # NEW: last run's metric vs golden set
  clips/
    <clip_id>.ass
    <clip_id>_9x16.mp4
    <clip_id>_16x9.mp4
```

## 8. Error handling and edge cases

- Scan returns zero candidates for a chunk → continue.
- Rank returns invalid JSON (opencode/ollama without structured outputs) → 1 retry; then fall
  back to the scan score for those clips.
- No API key / provider down → existing `HeuristicScorer`.
- Chunk overlaps → duplicates removed by `selection`'s dedup.
- Empty golden set (unlabeled class) → `eval` reports "no baseline", doesn't break.
- Clip range falling on a dirty segment → no longer proposed (dirty is in the scan prompt).

## 9. Milestones

Everything lives in this spec; each milestone gets its own implementation plan.

### M1 — Eval (baseline)
- **Delivers:** `eval.py`, `GoldenSet` model + `labels.json`, reason field in the review UI
  (CLI + web), metric (precision@N + recall + per-reason breakdown).
- **Done when:** running the CURRENT pipeline over 2–3 real classes, labeling them, and
  producing an `eval_report.json` with the baseline.

### M2 — Selection engine
- **Delivers:** natural-boundary chunking, Scan (pass 1), `ranker.py` (pass 2), the rubric,
  hook-first refinement, per-task model in the router, sub-scores on `ClipCandidate`.
- **Done when:** the new engine **beats the M1 baseline precision** on the labeled classes.

### M3 — Anthropic infra
- **Delivers:** structured outputs (`output_config.format` / `messages.parse`) in
  `ClaudeRouter`, prompt caching on the scan system prompt, Batches API for the offline scan,
  mapping of `scan_model`/`rank_model` to Anthropic tiers.
- **Done when:** scan and rank run on Anthropic with guaranteed JSON; per-class cost measured
  and reduced vs the run without caching/batches.

### M4 — Render quality
- **Delivers:** robust reframe (median webcam region across several frames), 2–3 ASS
  templates + keyword highlighting, multimodal `visual_check` for A/B and dirty-screen
  rejection.
- **Done when:** rendered clips have no broken framing when the webcam moves; the A/B
  decision is validated on real frames.

## 10. Testing

- **Unit:** boundary chunking (silence fixtures), rubric parsing, hook-first refinement
  (snaps the out, never the in), IoU/precision metric.
- **Integration:** pipeline over a short fragment extracted from a real class.
- **Regression:** from M2 onward, the eval against the golden set is a regression test — a
  prompt change that lowers precision is a failure.

## 11. Risks and open questions

- **Golden-set size:** 2–3 classes may be too few for a stable metric; expand as Ale reviews
  more material.
- **Rank cost with full transcripts:** finalists send their entire transcript; bound N (the
  number of finalists) to control tokens. Caching helps in M3.
- **Few-shot seeding from the golden set:** define when and how the good/bad examples are
  chosen (risk of overfitting to one specific class).
- **Chunk overlap:** calibrate the overlap size — too much inflates tokens, too little misses
  the boundary.
- **Eval IoU threshold:** choosing the overlap threshold that counts as a "match" requires
  iteration on real data.
