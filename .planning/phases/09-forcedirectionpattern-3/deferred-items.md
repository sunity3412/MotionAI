# Phase 9 — Deferred Items

Discovered during Wave 1 execution but out of scope (not introduced by this plan).

## Pre-existing test collection errors — `from backend.research.*` import path

`pytest tests/ -q` from inside `backend/` fails to collect 11 smoke/spike test
files because they import via the absolute `from backend.research.*` path,
which doesn't resolve when pytest is launched from inside the `backend/`
directory (the parent — `backend/` itself — is the package, so `backend.*` is
not on `sys.path`). The same import also fails from the repo root because
there's no top-level `backend/__init__.py`.

Affected files (all added in Phase 1, commits 6255380 / 84c249a / b87fe7c / 6e1d328):

- `tests/test_compare_engines_smoke.py`
- `tests/test_debug_gap_root_cause_smoke.py`
- `tests/test_gemini_motion_classify_spike.py`
- `tests/test_mapping_audit.py`
- `tests/test_pole_detector.py`
- `tests/test_spike_gemini_moment_smoke.py`
- `tests/test_spike_measurement_trace.py`
- `tests/test_spike_measurement_trace_smoke.py`
- `tests/test_spike_mediapipe_to_h36m17.py`
- `tests/test_spike_rtmpose_to_h36m17.py`
- `tests/test_sweep_rtmpose_smoke.py`

Why deferred: pre-existing (Phase 1) — not introduced by Phase 9. Fix requires
either (a) adding `backend/__init__.py` and running pytest from repo root, or
(b) rewriting the imports to use the installed-package path
(`sunity_shared.research.*`). Both are scope-out from a Phase 9 Wave 1 fix.

T5 full-regression gate verified via subset path:

```
cd backend && pytest tests/phase06/ tests/phase07/ tests/phase08/ tests/phase08_1/ tests/phase09/ tests/pipeline/ -q
# → 550 passed, 1 skipped
```

This subset covers all production-pertinent test suites. The deferred smoke/spike
suites are research-only and do not gate production behavior.
