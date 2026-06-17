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

## Cross-test pollution under broad `-k` (discovered 2026-06-17, Plan 15-04)

`pytest backend/tests -k "mode3 or assemble"` reports 3 FAILs:
- `test_pipeline_phase8.py::test_pipeline_phase8_mode3_force_signals_emitted`
- `test_pipeline_phase9.py::test_mode3_first_path_emits_mode3_first_context`
- `test_pipeline_phase9.py::test_mode3_progress_path_emits_mode3_progress_context`

NOT a regression — repo code unchanged by 15-04. These pass when run in isolation
(`pytest <file>::<test>` = PASS) and when the two files run together
(`pytest test_pipeline_phase8.py test_pipeline_phase9.py` = 16/16 PASS). The broad `-k`
selection collects tests across many files that mutate module-level singletons (pipeline
adapters / recognizer caches), so a cross-file test-ordering artifact surfaces only under the
wide selector. Suggested owner: a test-hygiene quick task to add per-test singleton reset
fixtures. Not a Phase 15 blocker.

## SCORE-04 all-low success-severity gate scope (discovered 2026-06-17, Plan 15-04 → Phase 18)

`assert_falsepositive_gate.py` success gate (all axis severity == 'low') is the 08.1 25/25-low
invariant measured on 정은지 **reference-motion** clips. Phase 15 success videos are 정은지
**student-practice success** clips whose real axis tilt exceeds 08.1 cutoffs in some phases
(e.g. pdshape sh/hip 90°, power-spin sh/hip 80-88°), so 4/6 success videos legitimately show
medium/high severity (NOT a 41-style false positive — lowest overall=55 reflects a real
detected deficit). Automated per-input-class severity gating (reference-motion vs
student-practice success) requires the labeled eval set → **deferred to Phase 18** alongside
the fail per-fault gate. Threshold NOT re-calibrated (D-02 / calibration-source-hard-gate;
yaml sha256 c94bb8 unchanged).
