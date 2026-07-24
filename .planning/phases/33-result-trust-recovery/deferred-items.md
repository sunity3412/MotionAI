# Phase 33 — Deferred Items (out-of-scope discoveries)

## Pre-existing backend test failures (NOT caused by 33-22)

During 33-22 execution, the full backend `pytest` run surfaced 45 pre-existing
failures + 12 pre-existing collection errors, confirmed present at the baseline
commit `bdfe4a0` (before any 33-22 change) via a throwaway worktree comparison.
These are unrelated to the scoring redesign and are logged here, NOT fixed.

Baseline `bdfe4a0`: 45 failed / 3401 passed / 21 skipped (deselecting the 12
collection-error files). After 33-22: 45 failed / 3417 passed / 20 skipped —
same failure set, +16 passing (new two-track tests + updated gate tests).

### Collection errors (12 files — import-path / heavy ML deps not installed locally)
`ModuleNotFoundError: No module named 'backend'` and missing mediapipe/rtmlib/torch:
- test_compare_engines_smoke, test_debug_gap_root_cause_smoke,
  test_gemini_motion_classify_spike, test_mapping_audit, test_pole_detector,
  test_rtmw_133_to_coco17_adapter, test_spike_gemini_moment_smoke,
  test_spike_measurement_trace(+_smoke), test_spike_mediapipe_to_h36m17,
  test_spike_rtmpose_to_h36m17, test_sweep_rtmpose_smoke

### Failures (45 — Gemini SDK/env, missing Pod fixtures, recognizer substrate)
- phase06/* (10): body-profile / firestore-integration / motion-query — Gemini/env
- phase08/test_gemini_model_env_driven (1), phase31/test_visual_jobs (1)
- test_compare_body_profile_smoke (4), test_compare_rtmw_vs_ipsf_recognizer_flag (1)
- test_estimated_height_scale_consumer_semantics (2)
- test_gemini_moment_extractor (1), test_gemini_technique_recognizer (2),
  test_gemini_vision_scorer (6)
- test_p1_objective_knee_decontamination (4) — `expects_extension False` /
  `per_joint_deviation 0.0` (recognizer/profile substrate, upstream of deduction_engine)
- test_pipeline_geminic_wiring (6), test_pipeline_geminid_wiring (8)

All require Gemini SDK / GPU-recognizer data / Pod fixtures absent from the local
dev environment. Out of scope for the scoring-redesign plan.
