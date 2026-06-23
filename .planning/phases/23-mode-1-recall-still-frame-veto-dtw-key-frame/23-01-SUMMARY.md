---
phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame
plan: 01
subsystem: api
tags: [gemini-vision, dtw, vision-veto, fault-key, mode1, faultkey, support-gate]

# Dependency graph
requires:
  - phase: 20-mode-1-vision-veto
    provides: vision veto core (apply_downward_cap, VisionVetoCache, _aggregate_comparison_verdict, VisionVerdict, _union_differences)
  - phase: 22-fault-zoom
    provides: fault_zoom._matched_ref_frame (DTW-matched ref frame selection), FfmpegFrameExtractor pattern
provides:
  - still-image upload path (_upload_image) + image mime branches + explicit still-pair API
  - FaultKey single serialization owner (to_dict/from_dict + locked enums, unknown rejected)
  - part-wise key-frame fan-out + canonical FaultKey N-of-K support gate (single-frame hallucination dropped)
  - resource bound (MAX_VETO_CALLS/UPLOADS/WALL_S) + fail-closed resource_limited status
  - global+local DTW-confidence gating helper + part-wise worst-frame selector
  - low_alignment_confidence + resource_limited score-free statuses (3-way lockstep)
  - collect/apply 2-function seam (Gemini ownership split) with keyword pre-build primitive signature
  - VisionFaultContext (pre-apply/pre-coach) + VisionQuantificationResult (post-geometry) + SelectedFramePair typed owners
  - _build_vision_quantification_result named production seam
  - cap_would_apply pre-coach computation via production cap function
affects: [23-02, 23-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FaultKey single serializer/validator owner (locked enum, from_dict raises on unknown)"
    - "collect/apply 2-function seam: Gemini owner = collect (pre-coach, once); apply reuses verdict (geminiCallCount=1)"
    - "Typed context objects split: pre-apply (VisionFaultContext) vs post-geometry (VisionQuantificationResult); to_audit_dict parameterized by final cap"
    - "fail-closed resource_limited: normal applied requires samplingComplete=true (Option A)"

key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
    - backend/shared/python/sunity_shared/analysis/vision_veto.py
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/models.py
    - app/src/types/analysis.ts
    - docs/contract.md
    - backend/tests/test_gemini_vision_scorer.py
    - backend/tests/test_vision_veto.py
    - backend/tests/test_pipeline_vision_gate.py

key-decisions:
  - "Defined RootCauseHypothesis in vision_veto.py (used by both Task 2 derive and Task 4 context) to avoid a forward dependency"
  - "select_worst_frame_candidates emits part-scope tokens with a shared global worst timestamp; actual per-part frame refinement is carried by the Gemini part-scope prompt fan-out"
  - "FaultKey curve-fit guard: keypoint_set/fault_kind are generic categories only (no motion names)"

patterns-established:
  - "vision_veto.py has no upward operators (no max() / min() outside apply_downward_cap) per the downward-only invariant"
  - "to_trace_dict emits the same fault-key dict vocabulary as FaultKey.to_dict (single vocabulary, drift 0) for 23-03 recall matching"

requirements-completed: [VETO-01, VETO-02, VETO-03]

# Metrics
duration: ~75min
completed: 2026-06-23
---

# Phase 23 Plan 01: Mode 1 Recall Still-Frame Veto + DTW Key-Frame Summary

**Mode 1 vision veto input swapped from whole-video to DTW worst-pose still-pair + part-wise key-frame fan-out with canonical FaultKey support gate, fail-closed resource bounds, and a collect/apply 2-function Gemini-ownership seam with typed pre-apply/post-geometry context owners.**

## Performance

- **Duration:** ~75 min
- **Tasks:** 4 (all TDD)
- **Files modified:** 9
- **Tests:** 112 passing across the vision suite (test_gemini_vision_scorer, test_vision_veto, test_pipeline_vision_gate, test_fault_zoom, test_motiondtw); app `tsc --noEmit` clean

## Accomplishments

- **Task 1 — still-image upload swap:** `_mime` png/jpeg branches (video fall-through preserved); `_upload_image` sibling of `_upload_video` with a path-existence guard before upload (D-10 HIGH-2); `assess_fault_severity` extended with explicit still-pair keyword args (student/reference_frame_path, part_scopes, frame_indices, selector_version); "side-by-side" stays two separate image handles (H3, not composite); `build_key` folds selector_version/frame_indices/top_k/window for cache collision avoidance.
- **Task 2 — FaultKey + support gate:** `FaultKey` single serialization owner with locked enums; `from_dict` raises on unknown enum values; `fault_key_from_difference` normalizes left/right arm aliases to one canonical key and maps ambiguous "팔" to side=unknown; `_filter_supported_differences` enforces N-of-K canonical support (single-frame hallucination dropped); `_derive_root_causes_from_supported_differences` is support-gated only; `_run_part_frame_fanout` bounds calls/uploads/wall-clock and returns fail-closed `resource_limited` when planned calls are not all completed (Option A); head/neck→shoulder and grip→hand part keywords added; PROMPT_VERSION v8.0 / SCHEMA_VERSION v6.0.
- **Task 3 — DTW-confidence gating + lockstep:** `assess_alignment_confidence` combines global distance + local (path density / ref-frame presence / keypoint visibility) into an adoption enum (single | window_union | low_alignment_confidence) — global-good-local-weak never adopts single; `select_worst_frame_candidates` exposes part-wise candidates + selector_version; `low_alignment_confidence` and `resource_limited` added to `models.VISION_VETO_STATUSES`, `analysis.ts` VisionVeto union (resource_limited telemetry-only), and `contract.md` §4 (3-way lockstep); `apply_downward_cap` untouched; DTW median kept out of the alignment helper.
- **Task 4 — collect/apply seam + typed owners:** `VisionFaultContext` (pre-apply/pre-coach only, `collection_status` pre-final enum rejecting applied/not_applicable, `eligible_for_coach` property, `to_coach_context`/`to_trace_dict` standalone, `to_audit_dict` requires `final_status`); `VisionQuantificationResult` (post-geometry); `SelectedFramePair`; pipeline `_collect_vision_fault_context` (Gemini owner, keyword pre-build primitive signature with no result dict, `cap_would_apply` via the production `apply_downward_cap`); `_build_selected_frame_pair` (DTW-matched ref frame, no DTW recompute, `finally` unlink); `_build_vision_quantification_result` named seam (missing inputs → unavailable, never None); `_apply_vision_veto` now accepts `vision_fault_context`/`quantification` and reuses the verdict without re-calling Gemini (geminiCallCount=1), with score-free statuses passed through unchanged.

## Task Commits

1. **Task 1: still-image upload swap + image mime + still-pair API** - `f46e2ca` (feat)
2. **Task 2: FaultKey single owner + part-wise fan-out + support gate + resource bound** - `4fe9765` (feat)
3. **Task 3: DTW-confidence gating + part-wise worst selector + lockstep** - `f9b9eac` (feat)
4. **Task 4: collect/apply 2-function seam + typed owners + quantification seam** - `aec325a` (feat)

_Note: each TDD task was committed as a single feat commit containing both the failing tests and the implementation that makes them pass; tests were written first (RED) then implemented (GREEN) within each task before staging._

## Files Created/Modified

- `backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py` - `_mime` image branches, `_upload_image`, still-pair signature, resource constants, `_filter_supported_differences`, `_derive_root_causes_from_supported_differences`, `_run_part_frame_fanout`, part-scope prompt, version bumps, `build_key` selector folding
- `backend/shared/python/sunity_shared/analysis/vision_veto.py` - `FaultKey` (to_dict/from_dict + locked enums), `fault_key_from_difference`, `RootCauseHypothesis`, head/neck/grip part keywords, `assess_alignment_confidence`, `select_worst_frame_candidates`, `VisionFaultContext`/`VisionQuantificationResult`/`SelectedFramePair`
- `backend/functions/pipeline/app.py` - `_collect_vision_fault_context`, `_build_selected_frame_pair`, `_pose_frame_keypoints`, `_build_vision_quantification_result`, `_apply_vision_veto` context branch + `_apply_vision_veto_from_context`
- `backend/shared/python/sunity_shared/models.py` - VISION_VETO_STATUSES += low_alignment_confidence + resource_limited
- `app/src/types/analysis.ts` - VisionVeto union score-free branches + VisionVetoTelemetry
- `docs/contract.md` - §4 visionVeto status definitions for the two new statuses
- `backend/tests/test_gemini_vision_scorer.py`, `test_vision_veto.py`, `test_pipeline_vision_gate.py` - TDD coverage for all four tasks

## Decisions Made

- Placed `RootCauseHypothesis` in `vision_veto.py` (the canonical fault-key home) so both the Task 2 support-gated derivation and the Task 4 context can reference it without a forward dependency.
- `_build_vision_quantification_result` is intentionally a seam that currently returns `quantificationStatus="unavailable"` for all inputs — the actual geometry/quantification production is owned by 23-02 Task 1/2/4. This plan only defines the named call-site, the never-None contract, and the missing-input handling.
- The pipeline call-site at app.py:2692 was left calling the legacy `_apply_vision_veto(result, local_video_path, ...)` path. Wiring the new collect→build_result→quantification→apply ordering into the pipeline body is explicitly 23-02 Task 5's responsibility (per the plan's `_collect_vision_fault_context` action note). This plan delivers the function contracts, typed owners, and seam — proven by unit tests — without changing the live ordering.

## Deviations from Plan

None - plan executed exactly as written. All four tasks implemented their specified contracts; no auto-fix rules (1-3) were triggered and no architectural checkpoints (Rule 4) were needed.

One test-only correction during RED→GREEN: the initial `test_no_toplevel_google_import` flagged the function-local `from google import genai` (because `.strip()` removed indentation); the test was tightened to only inspect module-level (non-indented) imports, matching the lazy-import contract. This is a test refinement within Task 1, not a plan deviation.

## Issues Encountered

- **vision_veto.py downward-only guard (`"max(" not in src`):** The existing `test_worst_pose_no_new_moment_call` asserts the source contains no `max(`. An explanatory comment I added used the literal "max(" and tripped the substring check; reworded the comment to "올림 연산자 미사용". All alignment/selector logic uses if/else comparisons only, preserving the invariant.
- **Worktree Bash cwd:** early `cd backend` Bash calls resolved against the main repo rather than the worktree, causing stale greps; resolved by always using the absolute worktree path in Bash. App `tsc` is not installed in the worktree, so typecheck was run by temporarily symlinking the main repo's `node_modules` (gitignored, removed after) — exit 0, clean.
- **Pre-existing unrelated collection errors:** `test_pole_detector.py` and several `test_spike_*`/`test_*_smoke.py` files fail to collect due to a missing `fixtures` module path — pre-existing and out of scope for this plan; not modified.

## User Setup Required

None - no external service configuration required. (Gemini API key and Pod env injection are pre-existing dependencies from Phase 20.)

## Next Phase Readiness

- 23-02 can consume: `VisionFaultContext`/`VisionQuantificationResult`/`SelectedFramePair`/`FaultKey`/`RootCauseHypothesis` typed owners; `_collect_vision_fault_context`/`_build_vision_quantification_result`/`_apply_vision_veto(vision_fault_context=, quantification=)` seam; `cap_would_apply` + `eligible_for_coach` coach-injection gate.
- 23-03 can consume: `FaultKey.from_dict`/`to_dict` for manifest `expected_recall_keys` validation and `recall_set` production; `to_trace_dict` emits the same fault-key vocabulary; `resource_limited` telemetry (samplingComplete) for determinism/budget-stress eval.
- **Blocker for full production effect:** the new collect→apply seam is defined and unit-tested but not yet wired into the live pipeline body (still uses the legacy `_apply_vision_veto` call at app.py:2692). 23-02 Task 5 must wire the ordering (overall_score → collect → coach → build_result → _build_vision_quantification_result → apply) for the still-frame path to run in production.

## Self-Check: PASSED

- SUMMARY file exists: `.planning/phases/23-mode-1-recall-still-frame-veto-dtw-key-frame/23-01-SUMMARY.md`
- All task commits found: f46e2ca, 4fe9765, f9b9eac, aec325a

---
*Phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame*
*Completed: 2026-06-23*
