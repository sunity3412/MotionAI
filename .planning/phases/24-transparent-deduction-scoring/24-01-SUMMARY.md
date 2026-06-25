---
phase: 24-transparent-deduction-scoring
plan: 01
subsystem: scoring
tags: [ipsf, deduction-tally, vision-veto, contract-lockstep, numpy, pure-function]

# Dependency graph
requires:
  - phase: 23-mode-1-recall-still-frame-veto-dtw-key-frame
    provides: Phase 23 quantification substrate (angleDeltas + bodyRelativeNotches.delta_notches, BASELINE_KINDS, VisionQuantificationResult)
  - phase: 20-v2-gemini
    provides: gemini_vision_scorer differences schema (body_part/fault_state/severity), FaultKey vocab, vision_veto FAULT_KEYPOINT_SETS
  - phase: 19-vision-hybrid
    provides: kismam.overall_score deduction accumulation core + _PENALTY_PER_DEG single slope + dimensions.line_score profile-gated substrate
provides:
  - deduction_engine.tally — pure transparent deduction-tally engine (measured-geometry substrate, criterion-routed, signed-negative points, max(0,…) only clamp, no band)
  - ipsf_criteria — 5-criterion grouping table + criteria_from_measured_deviations seed + public criteria_for_fault router + internal total-coverage _criterion_for_keypoint_set partition + COVERAGE_GAP_KEYPOINT_SETS
  - DEDUCTION_RECORD_KEYS / DEDUCTION_BREAKDOWN_KEYS (3-way contract Python side)
  - DeductionRecord / DeductionBreakdown TS interfaces + deductionBreakdown? on AnalysisResult
  - docs/contract.md §10 DeductionBreakdown
  - test_deduction_engine.py (24 pure unit gates)
affects: [24-02-pipeline-seam-wiring, 24-03-eval-gates, vision_veto-band-removal, gemini_vision_scorer-reframe]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure tally engine consuming measured-geometry layer (no profile, no Gemini number) — final = max(0, round(100 + Σ signed-negative points)), only clamp max(0,…)"
    - "Two-source criterion activation: measured-deviation seed (Gemini-silent defense) ∪ Gemini fault-context router, line/leg cross-exclusion after union"
    - "Direction-aware dead-zone: over_target vs insufficient_reach shortfall"
    - "3-way contract lockstep with baselineValue/baselineKind split (HIGH-3) + OBJECT breakdown shape"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/deduction_engine.py
    - backend/shared/python/sunity_shared/analysis/ipsf_criteria.py
    - backend/tests/test_deduction_engine.py
  modified:
    - backend/shared/python/sunity_shared/models.py
    - app/src/types/analysis.ts
    - docs/contract.md

key-decisions:
  - "Per-criterion cap raised from 25 to 90 so a single-criterion 0-90deg sweep stays monotonic (raw at 90deg = 84 < 90) while multi-criterion totals can still drive final to 0 — keeps both the monotonicity gate and the no-final-band invariant"
  - "DeductionRecord dataclass uses snake_case Python fields; camelCase contract keys emitted only via to_dict() (mirrors VisionQuantificationResult convention)"
  - "Engine treats a None/absent per-criterion measured input as 0 contribution (honest 0, ND-06) — never an arbitrary penalty"

patterns-established:
  - "criteria_for_fault routes on RAW body_part/fault_state (not normalized keypoint_set) to avoid the torso/line normalization trap"
  - "CoverageGap frozen value carries flat-scalar provenance so a visible-but-0 gap is triageable (MEDIUM-3)"

requirements-completed: [SCORE-10, SCORE-11, SCORE-12, SCORE-14, SCORE-15, SCORE-16]

# Metrics
duration: ~40min
completed: 2026-06-25
---

# Phase 24 Plan 01: Transparent Deduction-Tally Engine Summary

**Pure numpy deduction-tally engine that replaces the severity→fixed-ceiling band: consumes the measured dimension/kismam geometry + Phase 23 quantification, routes faults to 5 IPSF criteria, and emits a fully reverse-derivable DeductionBreakdown where final = max(0, round(100 + Σ signed-negative points)) with max(0,…) as the only clamp.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-06-25
- **Completed:** 2026-06-25
- **Tasks:** 3
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments
- 3-way deduction contract (models.py `DEDUCTION_*_KEYS` ↔ analysis.ts `DeductionRecord`/`DeductionBreakdown` ↔ contract.md §10) with the HIGH-3 `baselineValue`/`baselineKind` split and OBJECT breakdown shape; Python↔TS field sets verified equal.
- `ipsf_criteria.py`: FIVE measurable criteria (`leg_extension`, `arm_extension`, `split_angle`, `line` ipsf_absolute + `body_relative_reach` reference_relative), single LINEAR slope reused verbatim from `kismam._PENALTY_PER_DEG`, `[CITED]`/`[ASSUMED]` provenance, profile-gated line/leg honest-0 note (ND-06), measured-deviation seed (`criteria_from_measured_deviations`, HIGH-1 Gemini-silent defense), public `criteria_for_fault` router (split-not-leg, severity-invariant), internal total-coverage `_criterion_for_keypoint_set` partition over the 8 FaultKey keypoint_sets, and 5 tracked `COVERAGE_GAP_KEYPOINT_SETS`.
- `deduction_engine.tally`: two-source activation union, HIGH-5 line/leg cross-exclusion, direction-aware dead-zone (over_target vs insufficient-reach shortfall HIGH-2), per-criterion cap before sum, signed-negative points, traceable unavailable→dimension_overall fallback (MEDIUM-1, never 100), `gemini_silent` observability marker, NaN/Inf guard, no final band — and it never touches the technique profile (BLOCKER B, no NameError surface).
- 24 pure unit gates green (`test_deduction_engine.py`), covering every HIGH/MEDIUM/ND requirement; full backend suite shows zero new regressions vs the base commit.

## Task Commits

1. **Task 3 (RED): failing unit gates** - `3feb3a0` (test)
2. **Task 1: DEDUCTION_* contract + ipsf_criteria table & router** - `f812689` (feat)
3. **Task 2: deduction_engine.tally** - `5672691` (feat)
4. **Task 3 (GREEN): finalized unit gates** - `24e7939` (test)

_TDD: the RED test commit (`3feb3a0`) precedes the GREEN feat commits; the Task-3 test file was finalized after the engine landed._

## Files Created/Modified
- `backend/shared/python/sunity_shared/analysis/deduction_engine.py` (NEW) - Pure tally engine: measured-substrate aggregation, criterion routing, cap+sum, OBJECT `to_dict()`, frozen DeductionRecord/DeductionBreakdown.
- `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py` (NEW) - 5-criterion grouping table + measured seed + public router + internal total-coverage helper + coverage-gap allow-list.
- `backend/tests/test_deduction_engine.py` (NEW) - 24 pure unit gates.
- `backend/shared/python/sunity_shared/models.py` - `DEDUCTION_RECORD_KEYS` + `DEDUCTION_BREAKDOWN_KEYS` + lockstep comment block.
- `app/src/types/analysis.ts` - `DeductionRecord`/`DeductionBreakdown` interfaces + `deductionBreakdown?` on `AnalysisResult` + extended `unit`/`deviationSource` unions.
- `docs/contract.md` - §10 DeductionBreakdown.

## Decisions Made
- **Per-criterion cap 25 → 90.** The plan demanded both a monotonic single-criterion 0-90° sweep AND a final reachable to 0. With cap 25, one criterion saturates at ~50° (breaking the 60°/90° monotonicity step) and three angle criteria sum to at most 75 (floor 25). Raising the per-criterion ceiling to 90 (raw at 90° = 84 < 90) keeps the realistic-range sweep strictly monotonic while still bounding pathological inputs (500°) and letting accumulated multi-criterion deductions drive final to 0. The cap stays `[ASSUMED]`, documented as a per-fault ceiling, not a final band.
- **snake_case dataclass fields, camelCase only in `to_dict()`** — mirrors the existing `VisionQuantificationResult` convention; the contract-key equality is enforced against `to_dict()` output and `DEDUCTION_RECORD_KEYS`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Per-criterion cap value broke the monotonicity gate**
- **Found during:** Task 2 (engine GREEN)
- **Issue:** The initial `[ASSUMED]` cap of 25 caused `test_deadzone_and_slope` (60°→90° both saturate at −25) and `test_no_final_band` (3 angle criteria × 25 = 75 floor, final never 0) to fail — the two requirements are jointly unsatisfiable at cap 25.
- **Fix:** Raised `_ANGLE_CAP`/`_REACH_CAP` to 90 (raw at 90° deviation = 84 < cap) and documented the rationale inline.
- **Files modified:** `backend/shared/python/sunity_shared/analysis/ipsf_criteria.py`
- **Verification:** `test_deadzone_and_slope` + `test_no_final_band` pass; full deduction suite 24/24.
- **Committed in:** `5672691` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug).
**Impact on plan:** The fix is a single calibrated constant required for the plan's own gates to be jointly satisfiable; it preserves every invariant (no band, monotonic, traceable). No scope creep.

## Issues Encountered
- **`app` has no installed `node_modules`** — `npx tsc --noEmit` cannot run in this environment. Mitigation: verified the TS edits structurally by extracting the `DeductionRecord` interface fields and asserting set-equality against `DEDUCTION_RECORD_KEYS` (Python), confirmed `DeductionBreakdown` block + `deductionBreakdown?` field present. The TS is a mechanical interface addition mirroring the existing `VisionVeto`/`VisionAngleDelta` patterns. The `tsc --noEmit` gate is re-runnable once deps are installed (Plan 02/03 or CI).
- **Pre-existing backend test failures (51) + collection errors (11)** captured on the base commit and logged to `deferred-items.md` — all in pipeline-wiring / gemini-integration / spike-harness suites unrelated to this additive engine. No new failures introduced (baseline diff empty).
- **Incidental `.pyc` recompile** in `.planning/spikes/001-dataset-eval-harness/__pycache__/` (a separate, unrelated `ipsf_criteria.py` in a spike harness) was reverted to keep the worktree clean — no namespace collision with `sunity_shared.analysis.ipsf_criteria`.

## User Setup Required
None - no external service configuration required (pure in-process numpy math).

## Next Phase Readiness
- The pure engine + contract + criteria table are ready for the Plan 02 pipeline seam wiring (`_apply_vision_veto` → `deduction_engine.tally`, derive `baseline_kind` per-move, set `result['deductionBreakdown']`).
- Plan 03 eval gates build on the engine's traceability (`final == max(0, round(100 + Σ points))`) and the structural generalization checks.
- Open follow-up (not a blocker for this plan): run `cd app && npx tsc --noEmit` once `node_modules` is installed to close the TS static gate.

---
*Phase: 24-transparent-deduction-scoring*
*Completed: 2026-06-25*
