# Phase 20 — Reference-Anchored Vision Veto (Mode1) + Mode3 Hold — Implementation Notes

> NOT the 20-04 SUMMARY. The orchestrator finalizes 20-04 after the Pod 6-pair
> generalization eval. This file records the code changes; Pod eval is **pending**.

belle decision (2026-06-20): **Mode1 비교 앵커 + Mode3 보류**. The single-video
(vacuum) vision veto can't tell a mild fault from correct form — it over-penalizes
everything (v2: 정은지 정타→50) or under-penalizes everything (v3: 잘못된 kip-up→100).
Comparing the student video AGAINST the 정은지 reference (like a coach) is the
principled fix. Mode3 has no fixed reference → veto held; absolute dims + prev-video
delta stand.

## What changed

### A. Adapter — `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py`

- `assess_fault_severity(local_video_path, at_seconds=None, reference_video_path=None)`
  — new optional `reference_video_path`.
  - When provided → **COMPARISON mode**: uploads BOTH videos via `_upload_video`
    (reference/정타 first, student second), calls `_call_gemini_comparison`.
  - When None → single-video path unchanged (back-compat). Mode3 won't call it.
- `_COMPARISON_PROMPT` + `_build_comparison_prompt(at_seconds)` — **generic**
  comparison prompt. Frames video 1 = 기준(정타), video 2 = 학생, same motion. Reports
  `dominant_severity` (none/minor/moderate/major) for the student's deviation vs the
  reference; camera angle/distance/background/quality explicitly NOT a fault; no
  numeric scores. Reuses the same response schema as the single-video prompt.
- `VisionVetoCache.build_key` — added `reference_hash` component (None → `'noref'`).
  Cache is now keyed on the (student, reference) PAIR. Different reference → different
  key; comparison key ≠ single-video key.
- `PROMPT_VERSION` / `SCHEMA_VERSION` bumped `v3.0 → v4.0` (comparison prompt = new
  cache generation; stale single-video verdicts auto-invalidated).
- `_call_gemini_comparison` — contents = ["기준(정타) 영상:", ref, "평가 대상(학생) 영상:",
  student, comparison_prompt]; temperature 0.0, schema, thinking unchanged.
- Objectivity guards intact: no score/overall/rating/점수 in schema; `_SCORE_PATTERN`
  leak guard; graceful None on any failure (key absent / API error / score leak).

### B. Pipeline — `backend/functions/pipeline/app.py`

- `_apply_vision_veto(..., mode=None, reference_video_path=None)`:
  - `mode == MODE_SELF` → **HOLD**: passthrough with status `mode3_held` (no adapter
    call, no download).
  - `mode == MODE_EXPERT` + `reference_video_path is None` → `missing_reference`
    (graceful — no vacuum judging).
  - `mode == MODE_EXPERT` + reference → comparison veto via `assess_fault_severity`,
    then `apply_downward_cap` as before (applied / not_applicable / skipped_error).
  - `mode == None` → single-video back-compat path preserved (existing callers/tests).
  - status enum docstrings updated with `mode3_held`, `missing_reference`.
- `_process` MODE_EXPERT branch: when veto is ON, downloads the 정은지 reference video
  from `ref["videoS3Key"]` to a `delete=False` temp file (`_s3.download_file`),
  holding it in `reference_local_video_path` (initialized to None **before the outer
  try** so it is always in scope for cleanup). Reference download failure → graceful
  (falls through to `missing_reference`).
- Veto call site threads `mode=mode, reference_video_path=reference_local_video_path`,
  wrapped in try/finally that unlinks the temp file. The `_process` outer `finally`
  also unlinks it (idempotent safety net — no leak even if an exception fires between
  download and the veto call).
- RunPod server (`runpod_inference/server.py`) reuses `_process` (single code path) —
  inherits the change with zero edits.

## Anti-curve-fit compliance ([[scoring-redesign-must-generalize-no-overfit]])

- Comparison prompt grep: **0 motion names** (kip-up/spin/climb/peter/elbow/pdshape/
  power/sister/정은지/jeong), **0 numeric expected answers**. The only numbers are the
  score-prohibition negative examples (85점/89%/8/10/100/100), identical in spirit to
  the original single-video prompt.
- Caps **unchanged** (D-02): `vision_veto.py` not modified — minor=None, moderate=75,
  major=50. Severity comes from Gemini's comparison; caps stay spec-anchored.

## Tests (all pass — pod-free, mocked adapter)

`cd backend && PYTHONPATH=shared/python python3 -m pytest tests/test_gemini_vision_scorer.py tests/test_vision_veto.py tests/test_pipeline_mode3.py -q`
→ **64 passed**.

New coverage:
- Adapter: comparison uploads both + parses severity; cache key includes
  reference_hash (different reference → different key); comparison key ≠ single-video
  key; single-video back-compat (default None).
- Pipeline: Mode3 → `mode3_held` (no cap even with active caps + major stub);
  Mode1 + reference None → `missing_reference`; Mode1 + reference + major → applied/
  capped (reference path reaches adapter); Mode1 + reference + none → not_applicable
  (정타 보존, 위양성 회귀 가드).

No TS touched — visionVeto status (`mode3_held`/`missing_reference`) is
backend-internal; not surfaced to the app contract, so the 3-way lockstep is
unaffected and `npm run typecheck` not required.

## PENDING (orchestrator)

- **Pod 6-pair generalization eval** on the RunPod GPU — validates that the generic
  comparison prompt distinguishes success/fail pairs WITHOUT curve-fitting to any
  specific motion. Not run here (executor does not run Pod eval).
- 20-04 SUMMARY finalization after the eval.

## Commits

- `0157a28` feat(20): reference-anchored comparison in vision scorer (Mode1)
- `3443696` feat(20): wire reference-anchored vision veto in pipeline (Mode1) + hold Mode3
- `d72928f` test(20): reference-anchored veto — comparison adapter + Mode1/Mode3 pipeline
