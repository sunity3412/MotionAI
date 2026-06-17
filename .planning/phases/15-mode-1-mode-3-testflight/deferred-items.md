# Phase 15 — Deferred / Out-of-Scope Items

Logged during execution (Plan 15-01). These are pre-existing failures NOT caused by this
plan's changes — Plan 15-01 adds 3 import-only scripts under `backend/scripts/` that no test
in `backend/tests/` imports. Per the executor scope boundary rule, these are logged, not fixed.

## Pre-existing backend pytest failures (discovered 2026-06-17, Plan 15-01)

Verified unrelated to Plan 15-01: `grep -rl 'sweep_phase15|assert_falsepositive_gate|upload_phase15|phase15_keys' backend/tests/` returns nothing.

1. **`backend/tests/test_pole_detector.py` — collection ImportError**
   - `ModuleNotFoundError: No module named 'fixtures'` (line 21, `from fixtures.synthetic_frames import ...`).
   - Test-path/conftest issue (missing `backend/tests` on sys.path for the `fixtures` package). Pre-existing.

2. **`backend/tests/test_pipeline_geminid_wiring.py` — 4+ failures**
   - `assert hasattr(pipeline_app, "augment_low_confidence")` → False, plus related Gemini-D Wave 2 wiring asserts.
   - Pipeline Gemini-D symbol not present on current HEAD. Pre-existing, unrelated to Phase 15 tooling.

3. **`backend/tests/test_spike_gemini_moment_smoke.py` — failure(s)**
   - `TestReportOnlyMode::test_runs_when_labeled` and related. Pre-existing Gemini moment smoke breakage.

Aggregate at time of logging: `37 failed, 1858 passed, 13 skipped` (excluding the pole_detector
collection error). None touch `backend/scripts/` Phase 15 tooling.

Suggested owner: a separate quick/debug task for the Gemini-D wiring + test-path fix; not a
Phase 15 (validation-only) blocker.
