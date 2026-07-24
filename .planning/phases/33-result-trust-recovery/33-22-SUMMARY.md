---
phase: 33-result-trust-recovery
plan: 22
subsystem: scoring-core
tags: [scoring, ipsf, deduction-engine, two-track, tdd, contract]
requires:
  - deduction_engine.tally (single scoring seam, Phase 24)
  - ipsf_criteria.CRITERION_GROUPS (byte-unchanged thresholds)
provides:
  - two-track deduction final (execution -40 aggregate cap + critical bypass + floor 25)
  - DeductionRecord.track + DeductionBreakdown aggregate reconstruction fields
  - three-file additive-optional contract mirror (analysis.ts + models.py + contract.md)
affects:
  - backend/functions/pipeline/app.py (overallScore = breakdown.final — inherits new formula, no edit)
  - backend/runpod_inference/server.py (same _process seam — inherits)
tech-stack:
  added: []
  patterns: [additive-optional-contract-key, numpy-pure-engine, tdd-red-green]
key-files:
  created:
    - backend/tests/test_deduction_two_track.py
    - .planning/phases/33-result-trust-recovery/deferred-items.md
  modified:
    - backend/shared/python/sunity_shared/analysis/deduction_engine.py
    - backend/shared/python/sunity_shared/models.py
    - app/src/types/analysis.ts
    - docs/contract.md
    - backend/evals/phase24/assert_gates.py
    - backend/tests/test_deduction_engine.py
    - backend/tests/test_pipeline_deduction_seam.py
decisions:
  - "Execution cap -40 as single project-level constant (IPSF total-cap -25 ~42% of ~60 IPSF scale), never re-fit per fixture (D-34/R3)"
  - "Critical track structurally implemented but DORMANT — no criterion carries split_fail_threshold_deg; verified by synthetic tests only (D-35)"
  - "SCORE_FLOOR 25 applied path-independently — two-track tally AND dimension_overall fallback both floor at 25 (INV-8/D-36)"
  - "track emitted only when critical (execution omitted) to preserve exact-key byte-compat with existing record tests"
metrics:
  duration_min: 55
  completed: 2026-07-24
  tasks: 3
  commits: 5
---

# Phase 33 Plan 22: Two-Track IPSF Deduction Redesign Summary

Replaced `deduction_engine.tally`'s unbounded per-joint deduction accumulation — which collapsed multi-joint execution faults to 0 (elbow-twist Σ ≈ −111.4 → final 0, while its own angle dimension scored 58) — with a two-track IPSF-anchored model: execution deductions aggregate-capped at −40 (floor 60), a dormant critical track bypasses both caps to an absolute score floor of 25. `final = max(25, 100 − min(40, Σ|execution|) − Σ|critical|)`. Contract mirrored across all three files as additive-optional.

## What was built

**Task 1 (RED, `test`):** 15 synthetic numpy-pure unit tests encoding INV-1/2/3/6/7/8 + no-cap-under-40 + the elbow-twist anchor (points verbatim from HANDOFF, not reconstructed) + a numpy-purity AST gate. All RED via `ImportError: EXECUTION_DEDUCTION_CAP` (not a no-op pass).

**Task 2 (GREEN, `feat`):** Two-track engine.
- `EXECUTION_DEDUCTION_CAP = 40.0` (IPSF-provenance comment; single constant) and `SCORE_FLOOR = 25.0`.
- `_two_track_final(records)` — pure helper: execution points summed → `−min(40, |Σ|)`; critical points summed separately (bypass both the −40 aggregate cap and the −20 per-record clamp, preserving ipsf_cap-90 magnitude); `final = max(25, round(100 + exec_capped + critical))`.
- `DeductionRecord.track` (default `'execution'`; emitted in `to_dict` only when `'critical'`). Classified `'critical'` only on the full-extension 0-fail branch in `_criterion_deduction` — **DORMANT** (no criterion carries `split_fail_threshold_deg`, D-35; never fires in real runs).
- `DeductionBreakdown` aggregate fields (`execution_raw_total`/`execution_capped_total`/`critical_total`/`execution_cap`/`score_floor`) emitted additive-optional on the two-track path.
- `dimension_overall` fallback early-return floored: `max(0, round(dim))` → `max(SCORE_FLOOR, round(dim))` (INV-8 path-independent).

**Task 3 (`feat`):** Three-file contract mirror — `track` in `DEDUCTION_RECORD_OPTIONAL_KEYS`, new `DEDUCTION_BREAKDOWN_OPTIONAL_KEYS`, TS interface fields, contract.md §10.1/§10.2/§10.5. Required key sets untouched (legacy docs still parse).

## Verification (opened the artifacts — D-19)

**Elbow-twist synthetic `tally().to_dict()` (execution-only, 8 joints, Σ=−111.4):**
```
final=60  executionRawTotal=-111.4  executionCappedTotal=-40.0
criticalTotal=0  executionCap=40.0  scoreFloor=25.0
```
**Dormant-critical synthetic (|90| critical + exec Σ40):**
```
final=25  executionRawTotal=-40.0  executionCappedTotal=-40.0  criticalTotal=-90.0
```
- critical record `to_dict()` has `track='critical'`; execution record omits `track` (byte-compat).
- `tally()` real seam: execution-only Σ>40 → final 60; under-cap (32° → −14.4) → final 86; unavailable-fallback dim=10 → final 25.

**Existing thresholds byte-unchanged (D-29 residual):** `ipsf_criteria.py` has **zero diff** (tol 20° / slope 1.2 / ipsf_cap 90 untouched). In `deduction_engine.py` the only "deletions" are the −20 clamp lines relocated verbatim into the execution branch (same `PER_RECORD_DEDUCTION_CAP` constant, same comparison); no threshold value changed. `git diff --stat bdfe4a0 HEAD` touches 4 files (analysis.ts, deduction_engine.py, models.py, contract.md) — `ipsf_criteria.py` absent.

**Numpy-purity:** AST gate green — no boto3/requests/google/firebase/firestore/cerebras/urllib import.

**Contract lockstep + typecheck:** `test_contract_lockstep` green (record key union == TS fields); `npm run typecheck` (tsc --noEmit) clean; `_validate_deduction_breakdown` accepts the new scalar keys (permissive scalar validator).

**Full backend suite:** baseline `bdfe4a0` = 45 failed / 3401 passed / 21 skipped; after 33-22 = **45 failed / 3417 passed / 20 skipped** (deselecting 12 pre-existing collection-error files). Failure set byte-identical to baseline (pre-existing Gemini-SDK/env, missing-Pod-fixture, recognizer-substrate failures — logged to `deferred-items.md`). +16 passing = new two-track + updated gate tests. Owned files: `test_deduction_two_track.py` 15/15, and the deduction/seam/seed suite all green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Regression] phase24/phase25 traceability gate embedded the OLD formula**
- **Found during:** Task 2 full-suite run — `test_phase24_gates` + `test_phase25_eval_gates` regressed (pass→fail), confirmed against baseline `bdfe4a0`.
- **Issue:** `evals/phase24/assert_gates.py::check_traceability` reconstructed `final == max(0, round(100 + Σpoints))`; the two-track aggregate cap legitimately breaks this (elbow-twist final=60 vs raw-sum recon=48/40). phase25 reuses phase24's gate.
- **Fix:** Reconstruct via emitted aggregates when present — `final == max(scoreFloor, round(100 + executionCappedTotal + criticalTotal))`; fallback/legacy (no aggregates) use `max(scoreFloor, round(100 + Σpoints))` so INV-8 holds on the fallback path too. Planted-mismatch / null-rule / nonnumeric-baseline checks unchanged.
- **Files modified:** `backend/evals/phase24/assert_gates.py`
- **Commit:** 375230a

**2. [Rule 1 - Test update] two existing tests encoded the pre-redesign formula/shape**
- **Found during:** Task 2. `test_no_final_band` asserted Σ=−60 → final 40 (< 50); `test_breakdown_serializes_flat` and seam `test_breakdown_object_set_on_result_and_flat` asserted the exact 5-key breakdown set. Both are exactly the semantic surface the redesign changes (plan file-list omitted them).
- **Fix:** Updated `test_no_final_band` → `test_no_severity_ceiling_band_execution_cap_floors_at_60` (asserts final 60 via the aggregate cap, keeps the `min(100`/`min(final` source guards); updated both breakdown-shape tests to require the base 5 keys + the 5 additive aggregate keys and to assert the INV-6 reconstruction. Only over-40 / shape assertions changed; execution-only-under-40 assertions untouched.
- **Files modified:** `backend/tests/test_deduction_engine.py`, `backend/tests/test_pipeline_deduction_seam.py`
- **Commits:** 116c2bd

## Known Stubs

None. The critical track is intentionally DORMANT (D-35) — not a stub: it is structurally implemented and verified by synthetic unit tests (INV-3/INV-8). Wiring split 0-fail is a documented follow-up (would re-introduce the resolved kip-up split FP; no clean fixture). The 6-fixture Pod re-verification of INV-1/2/4/5 is deferred to 33-23 (per plan success criteria).

## Self-Check: PASSED

- `backend/tests/test_deduction_two_track.py` — FOUND
- `.planning/phases/33-result-trust-recovery/deferred-items.md` — FOUND
- Commits eab29e2 / 116c2bd / 375230a / 410e986 — FOUND on HEAD
