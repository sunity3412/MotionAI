# Phase 13 Deferred Items

Out-of-scope discoveries during execution. Not fixed by the executor (SCOPE BOUNDARY).

## Pre-existing test failure (out of scope for Plan 13-A)

- **`backend/tests/phase08/test_gemini_model_env_driven.py::test_gemini_moment_extractor_default_is_non_eol`**
  - Status: FAILING on base commit (unrelated to Plan 13-A changes).
  - Cause: quick-task `260615-cxe` set the Gemini moment-extractor default to `gemini-2.5-pro`,
    but this phase08 test asserts the default must be a non-EOL model and rejects `gemini-2.5-pro`
    (memory `gemini-latest-model-versions` bans 2.5; recommended Pro = `gemini-3.1-pro-preview`).
  - Not touched by Plan 13-A (corrective exercises) — no Gemini model edits in this plan.
  - Suggested follow-up: align the moment-extractor default with the non-EOL model policy
    (`gemini-3.1-pro-preview`) or update the test/quick-task decision. Owner: belle.

## Pre-existing pipeline-wiring failures (out of scope for Plan 13-B)

Discovered during 13-B Task 3 regression run (2026-06-16). Confirmed pre-existing by running
them against the 13-B Task 2 commit (db252c9) BEFORE any Task 3 change — they fail identically.
Root cause unrelated to motion_ipsf_map / coach branch wiring.

- `tests/test_pipeline_geminic_wiring.py` (TestWave1Helper, TestProcessImportsFindSceneFlags)
  - `AttributeError: module 'app' has no attribute 'find_scene_flags'` — test monkeypatches a
    module-level symbol not exposed as a top-level attribute in this local env.
- `tests/test_pipeline_geminid_wiring.py` (TestCallWave2HelperGates, TestB2HardGate3DCocoArrayInvariant,
  TestImportSymbol) — `augment_low_confidence` import-symbol assertions, same module-attribute reason.

These are Phase 17 (geminiC/geminiD wave) wiring tests, not Phase 13 surface. 14 failed total.

### Pre-existing collection errors (missing local deps / `fixtures` package)

These modules error at COLLECTION time (heavy ML deps or a `fixtures` package not installed
locally) — not run, not affected by 13-B: test_compare_engines_smoke, test_debug_gap_root_cause_smoke,
test_gemini_motion_classify_spike, test_mapping_audit, test_pole_detector, test_spike_gemini_moment_smoke,
test_spike_measurement_trace(_smoke), test_spike_mediapipe_to_h36m17, test_spike_rtmpose_to_h36m17,
test_sweep_rtmpose_smoke.

Action: none in 13-B. Full pipeline regression should run on Pod/CI (also the Task 4 Cerebras E2E env)
where these deps + module symbols resolve. Owner: belle / verifier.
