# Phase 3 — Deferred Items (out-of-scope discoveries)

Out-of-scope failures/issues found during 03-01 execution. NOT fixed (SCOPE BOUNDARY rule).

## Pre-existing test failures (unrelated to Plan 03-01)

- `tests/phase08/test_gemini_model_env_driven.py::test_gemini_moment_extractor_default_is_non_eol`
  - Fails on pre-03-01 HEAD (`d3e2821`) too — confirmed via `git stash`.
  - Root cause: quick task `260615-cxe` changed default Gemini model
    (`gemini_moment_extractor.py` / `recognizer.py`) to `gemini-2.5-pro`; the
    `non_eol` assertion in this test expects a different default. Test, not code,
    is stale.
  - Owner: whoever owns the gemini-default-model quick task / Phase 8 follow-up.

- Spike/smoke test collection errors (`No module named 'backend'` / `'fixtures'`):
  `test_spike_*`, `test_compare_engines_smoke`, `test_debug_gap_root_cause_smoke`,
  `test_gemini_motion_classify_spike`, `test_mapping_audit`, `test_pole_detector`,
  etc. These depend on a different cwd/path bootstrap and fail to collect
  regardless of Plan 03-01 changes (pre-existing). Not in 03-01 verify scope.
