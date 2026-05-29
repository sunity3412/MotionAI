<!-- refreshed: 2026-05-29 -->
# Testing

**Analysis Date:** 2026-05-29

## Summary

Test coverage is **asymmetric by component**: the backend ML/scoring core is well covered by pytest; the React Native app has **no automated tests at all** (only a TypeScript typecheck gate); `/ml` is documentation only.

| Component | Framework | Coverage | Gate |
|---|---|---|---|
| `backend/` | pytest | Algorithm core well covered (16 files, ~99 test fns) | `pytest` |
| `app/` | none | No tests | `npm run typecheck` (`tsc --noEmit`, strict) |
| `ml/` | n/a | Docs only — code lives in backend, covered there | n/a |

## Backend (`backend/tests/`)

- **Framework:** pytest. ~16 test files / ~99 test functions, one `test_<module>.py` per source module in `analysis/`.
- **No AWS needed:** `backend/tests/conftest.py` injects `backend/shared/python` onto `sys.path`, so tests import `sunity_shared.*` directly without packaging the Lambda layer.
- **Pure-function design:** Most scoring/feature modules are pure functions, so the majority of tests need no mocking.
- **Synthetic ML inputs:** ML-facing tests build deterministic synthetic numpy poses with a seeded RNG (`np.random.default_rng(0)`) rather than running real models — keeps tests fast and GPU-free.
- **FastAPI server tests** (`backend/tests/test_runpod_server.py`): use `monkeypatch` + module reload + `fastapi.testclient.TestClient`; mock only env vars and `_load_pipeline_module`.
- **Run:**
  ```bash
  cd backend
  pip install -r requirements-dev.txt
  pytest
  ```
- **No coverage tool** configured (no `pytest-cov`/threshold).

### What is covered
Algorithm core: `features`, `temporal`, `motiondtw`, `kismam`, `dimensions`, `segments`, `selfmotion`, `technique`, plus shared helpers `auth`, `validation`, `s3keys`, `events`.

### What is NOT covered (backend)
- **ML adapters** (`coach_writer`, `frame_extractor`, `pose_estimator`, `interfaces`, `skeleton`) — excluded due to heavy deps / GPU. Expected gap.
- **Lambda handlers** (`functions/upload-url/app.py`, `functions/reference-api/app.py`) — thin wrappers over already-tested shared modules. Low risk.
- **Manual (non-pytest) smoke scripts:** `backend/scripts/_nlf_smoke.py`, `backend/scripts/verify_nlf_*.py` — run by hand for NLF verification, not part of the suite.

## App (`app/`)

- **No test runner.** No Jest, Vitest, or React Native Testing Library configured. No `*.test.*` / `*.spec.*` files under `app/src`.
- **Only quality gate:** `npm run typecheck` → `tsc --noEmit` (strict mode).
- **Partial runtime safety net:** `app/src/lib/userAnalyses.ts` has a defensive `normalize()` that hardens against malformed Firestore docs, partly compensating for the absence of contract tests.

### Untested behaviors (app — MEDIUM risk gap)
- App ↔ backend Firestore document contract
- Video upload flow (presigned URL → S3 PUT)
- Analysis status-machine rendering (`loading.tsx`)
- Result enrichment / reshape of flat angle arrays (`result.tsx`)

## `ml/`

Documentation only (`ml/ml_CLAUDE.md`). Executable ML code lives in `backend/shared/python/sunity_shared/analysis/` and is exercised by the backend pytest suite.

## Recommendations

1. Add app-side contract tests (or at least typed fixtures validated against `app/src/types/analysis.ts`) for the Firestore `AnalysisResult` shape — this is the highest-value untested boundary.
2. Add `pytest-cov` to surface backend coverage trends.
3. Consider a minimal smoke test for the upload flow (`api.ts`) given it spans presigned URL + content-type handling, a known pitfall area.
