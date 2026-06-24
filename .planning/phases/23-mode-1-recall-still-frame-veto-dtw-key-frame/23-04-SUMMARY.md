---
phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame
plan: 04-gapfix
subsystem: api
tags: [gemini-vision, vision-veto, fault-key, still-frame, gap-fix, recall, mode1]

# Dependency graph
requires:
  - phase: 23-01
    provides: _run_part_frame_fanout, _filter_supported_differences, _upload_image, FaultKey, VisionFaultContext, VisionVetoCache, INPUT_GRANULARITY_FRAME_PAIR
  - phase: 23-02
    provides: root-cause provenance, SelectedFramePair, _build_vision_quantification_result
provides:
  - assess_fault_context (production still-pair entry that runs part-wise fan-out and returns the rich dict)
  - VisionVetoCache.store_rich/lookup_rich (FaultKey + RootCauseHypothesis + telemetry round-trip)
  - _collect_vision_fault_context still-pair branch wired to fan-out (faultKeys + geminiCallCount now populated)
affects: [eval_stillframe_veto Pod gate, coach root-cause injection, visionVeto audit]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rich-dict cache round-trip: canonical FaultKey.to_dict/from_dict + RootCauseHypothesis flat serialization for cold/warm determinism"
    - "Production still-pair = part-wise fan-out (assess_fault_context); whole-video fallback (pair None) keeps assess_fault_severity"
    - "fail-closed Option A preserved at the wiring seam: resource_limited never yields a candidate verdict"

key-files:
  created:
    - .planning/phases/23-mode-1-recall-still-frame-veto-dtw-key-frame/23-04-SUMMARY.md
  modified:
    - backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py
    - backend/functions/pipeline/app.py
    - backend/tests/test_gemini_vision_scorer.py
    - backend/tests/test_pipeline_vision_gate.py

decisions:
  - "New public entry assess_fault_context rather than overloading assess_fault_severity — keeps the whole-video aggregator (which strips _-prefixed keys) untouched for back-compat, and gives the rich dict a single owner."
  - "Cache the FULL rich dict (not just VisionVerdict) under a frame_pair-granularity key so warm runs reproduce supported_differences + telemetry byte-stable; FaultKey/RootCauseHypothesis serialized via canonical to_dict/from_dict (single-owner vocabulary)."
  - "resource_limited stored in cache too — identical input deterministically re-yields resource_limited (Option A fail-closed) rather than re-sampling."

metrics:
  duration: ~50m
  completed: 2026-06-24
  tasks: 3
  files: 4
---

# Phase 23 Plan 04 (gap-fix): Wire still-frame part-wise fan-out into production scoring

Wired the 23-01/02 still-frame part-wise fan-out (built + unit-tested but never called in production) into the production scoring path so canonical FaultKeys, support-gated differences, root-cause hypotheses, and Gemini call telemetry now reach the eval trace — fixing the Pod eval regression where `recall_set=[]`, `call_count=0`, `geminiCallCount=None`.

## What changed

**The diagnosis (confirmed):** production still-pair path called `assess_fault_severity(...)`, which — when given a reference — ran `_aggregate_comparison_verdict` → `_union_differences`, and `_union_differences` strips every `_`-prefixed key (`if not k.startswith("_")`). So `verdict.differences` never carried `_faultKey`, and `_collect_vision_fault_context` built the context with empty `supported_differences`, no `root_cause_hypotheses`, and no telemetry. The correct function `_run_part_frame_fanout` (which attaches canonical FaultKeys + N-of-K support gating + root causes) was only ever called by tests.

**The fix (3 atomic commits):**

1. `feat(23-gapfix)` — `gemini_vision_scorer.assess_fault_context(student_frame_path, reference_frame_path, *, at_seconds, part_scopes, frame_indices, reference_frame_indices, selector_version)`:
   - Reuses `_ensure_client` (graceful skipped_error on failure), file-byte hashing, and the VisionVetoCache.
   - Uploads the two STILL IMAGES via `_upload_image` (NOT `_upload_video`), one each.
   - Calls `_run_part_frame_fanout(...)` and returns its rich dict `{status, verdict, supported_differences, root_cause_hypotheses, telemetry}`.
   - Caches the rich dict under a still-granularity key (`INPUT_GRANULARITY_FRAME_PAIR` + student/reference hash PAIR + `at_seconds` + `selector_version` + `frame_indices`) via new `VisionVetoCache.store_rich`/`lookup_rich`. These serialize `FaultKey` via `to_dict`/`from_dict` and `RootCauseHypothesis` (text/faultKeyDict/sourceIds/supportCount) as flat list-of-dict (Firestore nested-array ban). Cold miss → store; warm hit → identical dict (re-sampling 0).
   - Preserves the Gemini File API DELETE cleanup (finally) and the `_SCORE_PATTERN` leak guard (inside fan-out per-call).
   - `assess_fault_severity` + `_aggregate_comparison_verdict` left UNCHANGED.

2. `feat(23-gapfix)` — `pipeline/app.py::_collect_vision_fault_context`: the `pair is not None` branch now calls `assess_fault_context(...)` and maps the rich dict: `resource_limited` → `_ctx("resource_limited", telemetry=...)` (fail-closed, no candidate); `candidate_verdict` → `_ctx("candidate_verdict", verdict=, supported=, root_causes=, telemetry=, cap=cap_would_apply)`; severity `none` → `no_fault`; else `skipped_error`. `cap_would_apply` still computed via `vision_veto.apply_downward_cap` (downward-only body untouched). Whole-video fallback (`pair is None`) keeps `assess_fault_severity`.

3. `test(23-gapfix)` — regression tests (all mock Gemini).

## Verification

- `python3 -m pytest tests/test_gemini_vision_scorer.py tests/test_vision_veto.py tests/test_pipeline_vision_gate.py tests/test_coach_writer.py tests/gemini/test_coach_writer_v2.py tests/test_features.py -q` → **164 passed**.
- New regression `TestStillPairFanoutWiring::test_faultkeys_and_gemini_call_count_flow_through`: with the still-pair path and a mock fan-out returning a support-passed difference carrying `_faultKey`, `to_trace_dict()["faultKeys"]` is NON-EMPTY (`== fk.to_dict()`) and `geminiCallCount == telemetry.completedCalls`.
- New `test_resource_limited_is_fail_closed`: resource_limited status preserved, `cap_would_apply False`, no candidate verdict.
- New scorer tests: `assess_fault_context` uploads IMAGES (mimes `["image/png","image/png"]`, 2 File API deletes), cold/warm determinism (warm = cache hit, no fan-out re-run, byte-stable `_faultKey`), missing-frame → graceful `skipped_error`.

## Invariants held

- Objectivity: `_SCORE_PATTERN` leak guard preserved; no score-bearing fields added.
- Downward-only cap: `apply_downward_cap` body untouched; `grep "max("` in cap region → none.
- Determinism: rich cache round-trips supported_differences + telemetry byte-stable (test-proven).
- resource_limited fail-closed (Option A): partial sampling never yields a candidate verdict at the wiring seam.
- FaultKey single-owner vocabulary: cache serialization uses `FaultKey.to_dict/from_dict` exclusively.
- Firestore nested-array ban: rich doc stored as flat list-of-dict.
- App contract: no TS/contract change — `rootCauseHypotheses` (`{text, faultKey, supportCount}`) already existed in `to_audit_dict`/`analysis.ts`; this fix simply populates it for the still-pair path (was empty). Internal trace fields (`faultKeys`, `geminiCallCount`) are eval-only, not in the app contract.

## Deviations from Plan

None — gap-fix executed exactly as scoped. No architectural changes, no auth gates.

## Known Stubs

None. The still-pair production path is now fully wired end-to-end.

## Pre-existing failures (NOT introduced here)

`tests/test_pipeline_geminic_wiring.py` / `tests/test_pipeline_geminid_wiring.py`: 14 failures, all due to a missing `augment_low_confidence` symbol — identical at base `ef7d54a`, unrelated to vision-veto wiring. Left untouched per scope boundary.

## Self-Check: PASSED

- FOUND: backend/shared/python/sunity_shared/analysis/gemini_vision_scorer.py (assess_fault_context, store_rich/lookup_rich)
- FOUND: backend/functions/pipeline/app.py (still-pair branch → assess_fault_context)
- FOUND commit 6908f33 (scorer entry), 9a37043 (pipeline wiring), 816bfb4 (tests)
