---
phase: 19-vision-hybrid
plan: 02
subsystem: scoring
tags: [ipsf, deduction, kismam, dimensions, scoring, contract-3way, tdd-green]

# Dependency graph
requires:
  - phase: 19-vision-hybrid (19-01 Wave 0)
    provides: RED test suite encoding the deduction-based contract (kismam/dimensions)
provides:
  - IPSF deduction-based overall_score (single major fault dominates, no mean dilution)
  - line_score micro-bent 0-point track (160° element-invalidation, IPSF track 1)
  - overall_from_dimensions = min-of-core (stability separated from overall input)
  - DimensionExplanation.contributesToOverall (OPTIONAL 3-way contract field) + weightPercent=0 for non-contributing
  - shoulder COACHING_FOCUS relabel (안정성 → 자세각, TRUST-02)
affects: [19-03 (pipeline scoring_basis wiring), Wave 2 display-score parity]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deduction aggregation: 100 − Σ over·penalty_per_deg (no averaging); single fault dominates"
    - "Element-invalidation track: micro-bent (<160°) returns 0, not proportional penalty"
    - "min-of-core overall: stability excluded from overall input but kept in dimension_scores display"
    - "OPTIONAL contract field (?: ) so legacy/sim docs don't break typecheck; UI defaults true"

key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/kismam.py
    - backend/shared/python/sunity_shared/analysis/dimensions.py
    - backend/shared/python/sunity_shared/analysis/assemble.py
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - app/src/types/analysis.ts
    - app/src/lib/simulatedResult.ts
    - backend/tests/test_assemble_dimension_explanation.py

key-decisions:
  - "_PENALTY_PER_DEG=1.2 [ASSUMED] v1 heuristic — chosen from IPSF basis + RED-case direction constraints, NOT from held-13-video sweep (D-05 boundary)"
  - "_SPLIT_FAIL_THRESHOLD_DEG=160.0 [CITED] 19-IPSF §A track 1 (180°−20° tol)"
  - "min-of-core for overall (not deduction-sum) — Task 1 owns angle-dim deduction; Task 2 owns cross-dimension min"
  - "contributesToOverall is OPTIONAL (?:) per ITER-2 BLOCKER-1 — required would break sim/legacy docs"

requirements-completed: [SCORE-06, SCORE-07, TRUST-02]

# Metrics
duration: ~14min
completed: 2026-06-18
---

# Phase 19 Plan 02: Deduction-Based Scoring Aggregation Summary

**Replaced the dual mean-based aggregation with IPSF deduction scoring (kismam.overall_score = cumulative over-tolerance penalty, dimensions.overall_from_dimensions = min-of-core with stability separated, line_score micro-bent 0-point track), turning all 6 RED scoring cases GREEN while keeping every guard case GREEN.**

## Performance

- **Duration:** ~14 min
- **Completed:** 2026-06-18
- **Tasks:** 2
- **Files modified:** 8 (0 created, 8 modified)

## Accomplishments

- **Task 1 (kismam):** `overall_score` rewritten from weighted-mean to IPSF cumulative deduction — `100 − Σ max(0, dev−tol)·weight·penalty_per_deg`, clamped 0..100. A single major fault now dominates the overall (no dilution across normal joints). Tolerance dead-zone (≤20°) yields zero penalty (no false positives on clean poses). Shoulder COACHING_FOCUS relabeled `안정성` → `자세각` (TRUST-02 — shoulder is a static pose-angle, not stability/jitter).
- **Task 2 (dimensions/assemble/contract):**
  - `line_score` micro-bent 0-point track: any extension-required joint below 160° invalidates the element (return 0), not proportional penalty (IPSF track 1). Intentional-bend joints (`expects_extension=False`) are exempt — no false positive.
  - `overall_from_dimensions` rewritten from simple-mean to `min(core dims angle/line)`; stability separated from overall input (no inflation) but kept in `dimension_scores` display.
  - `build_dimension_explanation` now emits `contributesToOverall` (core=True) and distributes `weightPercent` over contributing dims only (stability weightPercent=0) — HIGH-1 fix against false-contribution display.
  - 3-way contract lockstep: `DimensionExplanation.contributesToOverall?: boolean` (OPTIONAL) in analysis.ts + `DIMENSION_EXPLANATION_KEYS` in models.py + docs/contract.md, plus `simulatedResult.ts::buildExplanationForSim` updated to emit the new semantics.

## Task Commits

1. **Task 1: kismam IPSF deduction overall + shoulder relabel (SCORE-06/TRUST-02)** - `b2d88d3` (feat)
2. **Task 2: line micro-bent 0 + stability separation + contributesToOverall 3-way + simulatedResult (SCORE-07/TRUST-02)** - `a856fba` (feat)

## RED → GREEN evidence

Previously-RED cases (failed standalone against mean-based code, per 19-01-SUMMARY) now PASS:

**test_kismam.py**
- `test_single_major_fault_dominates` — one joint 50° + rest ≈0 → overall 64 (< 70). Was ~88 (mean dilution).
- `test_within_tolerance_remains_high` — all 10° (<tol) → 100 (≥90). Was 88 (Gaussian penalized inside tolerance).
- `test_shoulder_focus_label` — COACHING_FOCUS shoulders = '자세각' (not '안정성'/'떨림'/'어깨').

**test_dimensions.py**
- `test_overall_from_dimensions_uses_core_dimensions` — {angle:40,line:80,stability:99}→40, {stability:99}→99, {}→0.
- `test_micro_bent_zero_track` — extension joints @140° → 0.
- `test_stability_does_not_inflate` — {40,40,99} → ≤50 (was 60).

Guard cases still GREEN: `test_clean_pose_high_score` (8°→≥90), `test_anchor_known_answer::test_above_cutoff_synthetic_stays_high` (synthetic clean pose ≥90), plus all unrelated kismam/dimensions cases (score_from_deviation / assess / top_issues / part_scores / select_window / line_deficits / stability_wobble unchanged).

## Verification evidence

- `pytest tests/test_kismam.py tests/test_dimensions.py -x -q` → **30 passed** (was 6 failed / 24 passed at Wave 0).
- `pytest tests/test_assemble_dimension_explanation.py tests/test_dimensions.py tests/test_kismam.py -q` → **47 passed**.
- `pytest tests/test_anchor_known_answer.py` → 1 passed (synthetic above-cutoff guard) + 6 skipped (real-video pairs, env-gated).
- `pytest tests/test_assemble.py` (adjacent build_mode1) → 12 passed (no regression).
- `cd app && npm run typecheck` (`tsc --noEmit`) → **clean** (includes simulatedResult.ts with new optional field).
- **Regression isolation:** full backend suite (excluding pre-existing import-broken collection: gemini/* missing `google` SDK, spike/pole_detector missing deps) compared against a baseline run with Task-2 changes stashed. The two failure sets are identical EXCEPT `test_dimensions.py` (3 RED → now GREEN) and the temporarily-broken-then-fixed `test_assemble_dimension_explanation.py`. **Zero new regressions.** All other failures (phase06/08/11, pipeline_phase8/9, test_pipeline_mode3 Wave 19-03 RED cases, gemini wiring) are pre-existing or other-wave (e.g. `ModuleNotFoundError: 'google'`, `is_reference_free_motion`/`_apply_vision_veto` absent — future Wave 19-03).

## Grep gate evidence

- `kismam.overall_score` body: 0 `np.nanmean` / `/ den` patterns (mean removed).
- `dimensions.overall_from_dimensions` body: 0 `sum(vals) / len` patterns.
- `_PENALTY_PER_DEG` constant carries `[ASSUMED]` + "보유 sweep 재calibrate 금지" comment; `_IPSF_TOLERANCE_DEG` keeps IPSF [CITED] basis; no sweep numbers cited.
- `_SPLIT_FAIL_THRESHOLD_DEG = 160.0` carries `[CITED: 19-IPSF-DEDUCTION-NOTES §A 트랙1]`.
- `analysis.ts` declares `contributesToOverall?:` (OPTIONAL); 0 required form.
- `contributesToOverall` present in analysis.ts + models.py + contract.md + simulatedResult.ts (3-way contract + sim lockstep).

## Calibration boundary (memory compliance)

`_PENALTY_PER_DEG=1.2` was derived from (a) the IPSF deduction structure (19-IPSF §A track 2: single major fault must dominate, accumulating not averaging) and (b) the RED-case direction constraints (single over-30° must drop overall below 70; eight over-10° must stay above 0 for monotonicity). It was NOT fit against the held 13 videos — no D-05 anchor or sweep numbers were consulted as calibration targets ([[scoring-redesign-must-generalize-no-overfit]], [[calibration-source-hard-gate]]). `_SPLIT_FAIL_THRESHOLD_DEG=160.0` is the IPSF 180°−20° split tolerance, [CITED] only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test contract] Updated test_assemble_dimension_explanation.py to new weightPercent semantics**
- **Found during:** Task 2 (full-suite regression check)
- **Issue:** 3 Phase-12.5 tests (`test_weight_3_dims_sum_100` / `test_weight_2_dims_sum_100` / `test_weight_1_dim_sum_100`) asserted the OLD even-distribution weightPercent contract ([34,33,33], [50,50], stability=100), which Phase 19 HIGH-1 intentionally supersedes (weightPercent over contributing dims only; stability=0). These were not updated in Wave 0.
- **Fix:** Rewrote the 3 cases to the new contract (contributing dims sum 100, stability weightPercent=0) and added `contributesToOverall` assertions per the plan's acceptance criteria.
- **Files modified:** backend/tests/test_assemble_dimension_explanation.py
- **Commit:** a856fba

## Known Stubs

None. All changes are live algorithm/contract changes wired into the existing pipeline path.

## Threat Flags

None. Internal pure-function aggregation changes + one OPTIONAL contract field. No new endpoint/auth/network/PII surface (per plan threat_model — surface low). T-19-02 mitigated (deduction coefficients IPSF-basis only, sweep citations 0), T-19-03 mitigated (contributesToOverall + weightPercent=0), T-19-13 mitigated (OPTIONAL field + simulatedResult updated, typecheck clean).

## Deployment note

Schema change (DimensionExplanation gains optional `contributesToOverall`) — EAS rebuild + `sam build --use-container` needed for the new field to flow through the deployed pipeline and app. Backward-compatible (OPTIONAL; legacy docs default true on UI side).

## Self-Check: PASSED

- All 8 modified files exist on disk.
- Both task commits (b2d88d3, a856fba) present in git history.
- Previously-RED kismam/dimensions cases GREEN; guard cases GREEN; tsc clean; 3-way contract lockstep verified by grep.

---
*Phase: 19-vision-hybrid*
*Completed: 2026-06-18*
