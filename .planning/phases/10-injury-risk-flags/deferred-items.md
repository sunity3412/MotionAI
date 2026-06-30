# Phase 10 — Deferred / Out-of-Scope Items

## Pre-existing test failures (NOT introduced by Phase 10, out of scope)

Discovered during 10-01 execution while running the full `backend/tests` regression
suite. These fail identically against the pre-Phase-10 commit (`102fbfe`, original
`models.py` without the additive `SafetyFlag` re-export) — proven by reverting
`models.py` and re-running. They are unrelated to the SafetyFlag scaffold (Gemini /
vision-veto env-dependent pipeline-integration tests + heavy-dependency R&D spike
collection errors). Per the executor SCOPE BOUNDARY, they are logged here and NOT
fixed in this plan.

### Pipeline-integration FAILED (10)
- `tests/phase06/test_phase06_integration_smoke.py::test_full_pipeline_mode1_ref_source_pose_missing_smoke`
- `tests/phase06/test_pipeline_body_comparison.py::test_process_mode1_with_full_ref_returns_mode1_report`
- `tests/phase06/test_pipeline_body_comparison.py::test_process_mode1_missing_ref_body_profile_emits_canary_warning`
- `tests/phase06/test_pipeline_body_comparison.py::test_process_mode1_missing_ref_source_pose_emits_canary_warning`
- `tests/phase06/test_pipeline_body_comparison.py::test_process_mode1_fetches_both_profile_and_source_pose`
- `tests/phase06/test_pipeline_firestore_integration.py::test_process_calls_complete_analysis_with_body_comparison_report`
- `tests/phase08/test_gemini_model_env_driven.py::test_gemini_moment_extractor_default_is_non_eol`
- (plus 3 more pipeline cases in the same phase06/phase08 group)

Root cause sample: `NotPoleMotionError` raised inside `_process` under the mocked
mode1 flow — a domain/env path (Gemini recognizer / vision-veto), not a contract or
import issue.

### Collection ERRORS — R&D spike/smoke modules (11, heavy optional deps)
`tests/test_compare_engines_smoke.py`, `tests/test_debug_gap_root_cause_smoke.py`,
`tests/test_gemini_motion_classify_spike.py`, `tests/test_mapping_audit.py`,
`tests/test_pole_detector.py`, `tests/test_spike_gemini_moment_smoke.py`,
`tests/test_spike_measurement_trace.py`, `tests/test_spike_measurement_trace_smoke.py`,
`tests/test_spike_mediapipe_to_h36m17.py`, `tests/test_spike_rtmpose_to_h36m17.py`,
`tests/test_sweep_rtmpose_smoke.py` — ImportError on optional ML deps
(mediapipe / rtmpose / gemini), unchanged by Phase 10.

**Phase 10 scope (phase06/07/08/08_1/09/10 substrate suites) regression = 0** beyond
these pre-existing items.
