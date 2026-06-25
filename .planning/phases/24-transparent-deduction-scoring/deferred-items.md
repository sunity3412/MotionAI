# Phase 24 — Deferred / Out-of-Scope Items

Discovered during 24-01 execution. NOT caused by this plan's changes (engine is additive: 3 new files + 2 contract edits). Logged per executor scope boundary — not fixed here.

## Pre-existing backend test failures (51) + collection errors (11)

Captured on the plan base commit `2155721` BEFORE any 24-01 edit.

### Collection errors (11) — missing modules / heavy deps
- `tests/test_compare_engines_smoke.py` — `ModuleNotFoundError: No module named 'backend'` (imports `backend.research.evaluations.compare_engines`).
- `tests/test_debug_gap_root_cause_smoke.py`, `tests/test_gemini_motion_classify_spike.py`, `tests/test_mapping_audit.py`, `tests/test_pole_detector.py`, `tests/test_spike_gemini_moment_smoke.py`, `tests/test_spike_measurement_trace{,_smoke}.py`, `tests/test_spike_mediapipe_to_h36m17.py`, `tests/test_spike_rtmpose_to_h36m17.py`, `tests/test_sweep_rtmpose_smoke.py` — import-time failures (research/spike harnesses, heavy deps absent locally).

### Failures (51) — pipeline-wiring / gemini-integration suites
- `tests/test_pipeline_geminid_wiring.py::*` (multiple)
- `tests/test_pipeline_mode3.py::test_vision_veto_called_both_modes`
- plus other `test_pipeline_*` / vision-integration suites.

Full baseline snapshot: `/tmp/baseline_failures.txt` (regenerable). These are unrelated to the pure deduction engine (`deduction_engine.py` / `ipsf_criteria.py`) added in 24-01; the seam wiring that would touch `pipeline/app.py` is Plan 02. Re-evaluate at Plan 02/03.
