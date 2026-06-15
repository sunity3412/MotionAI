# Phase 14 Deferred Items

## Out-of-scope test-env dep failures (logged 14-02, not fixed)

The worktree venv lacks optional ML/cloud deps, so `pytest tests/` (full suite) shows
pre-existing collection errors + dep-gated failures in modules unrelated to Plan 14-02:

- `ModuleNotFoundError: No module named 'google'` — gemini/* tests, phase06 pipeline
  integration, phase08 gemini-model tests (needs `google-genai`)
- `mediapipe` / `rtmlib` / `imageio` missing — spike/sweep/compare-engines/pole-detector tests

These are pre-existing (not caused by Plan 14-02) and dep-related, not code defects.
Directly-relevant suites pass: `test_reference_backfill.py` 9/9 (no skips), `tests/phase09`
(force_pattern) 135/135. Resolve by installing the optional deps in the Pod/CI venv before
running the full suite; do NOT treat as a 14-02 regression.
