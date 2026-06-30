---
phase: 10-injury-risk-flags
plan: 01
subsystem: testing
tags: [safety-flags, contract-3-mirror, numpy, pytest, xfail-strict, firestore-scalar, react-native]

# Dependency graph
requires:
  - phase: 08-force-signals
    provides: ForceSignalsReport / StabilityMetric (control-loss substrate D-02 consumes)
  - phase: 09-force-pattern
    provides: frozen-dataclass + bottom-of-file re-export pattern mirrored by SafetyFlag
provides:
  - SafetyFlag frozen dataclass (enum-guarded, scalar-only) + compute_safety_flags(...) Wave-0 stub
  - SafetyFlag contract 3-mirror (analysis.ts SafetyFlag/SafetyFlagType + AnalysisResult.safetyFlags, models.py tuples + re-export, contract.md §9.13)
  - warnAmberBg (#FFF6E5) theme token
  - backend/tests/phase10/ Nyquist scaffold (16 fixtures + 6 test files) with GREEN no-flag invariants + xfail-strict positive contracts
affects: [10-02 trunk AND-gate, 10-03 D-05 joint hyperextension, 10-04 asymmetry+level, pipeline _process wiring, result.tsx warning banner]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure firing-rule module (numpy-only, no AWS/network) mirroring kismam/force_pattern"
    - "Two-segment positive fixture (calibration fold + reverse-bend hold) satisfying D-05 calibration premise"
    - "GREEN/xfail discipline: answer-is-[] cases GREEN against stub, must-fire cases xfail(strict)"
    - "Single-variable gate-isolator fixtures (wrong-phase vs wrong-joint) with assert-precondition-first"

key-files:
  created:
    - backend/shared/python/sunity_shared/analysis/safety_flags.py
    - backend/tests/phase10/conftest.py
    - backend/tests/phase10/test_safety_flags_dataclass.py
    - backend/tests/phase10/test_safety_flags_firing_rule.py
    - backend/tests/phase10/test_safety_flags_hyperextension.py
    - backend/tests/phase10/test_safety_flags_asymmetry.py
    - backend/tests/phase10/test_safety_flags_level.py
    - backend/tests/phase10/test_safety_flags_contract.py
  modified:
    - app/src/types/analysis.ts
    - backend/shared/python/sunity_shared/models.py
    - docs/contract.md
    - app/src/theme/colors.ts

key-decisions:
  - "ch3 = uncertainty_proxy (NOT confidence): 1.0=undetected/worst, ~0.05=good — locked in module docstring + conftest + fixtures"
  - "D-05 helper signature locked: _joint_hyperextension_flags(*, angles, keypoints_4ch, fsr, profile) -> list"
  - "compute_safety_flags(...) signature locked (consumed by 10-02 _process); D-05 sagittal frame + DTW alignment derived INTERNALLY, no extra kwargs"
  - "SafetyFlag fields scalar-only (Firestore nested-array ban); enum guards on flag_type/severity/confidence/mode_scope"

patterns-established:
  - "Two-segment reverse-bend fixture: argmin(included_angle) lands in calibration (<90deg), profile.hold_window targets reverse-bend hold"
  - "Single-variable D-05 isolators assert their precondition (joint-hit / phase-overlap) before asserting == []"

requirements-completed: [SAFE-01]

# Metrics
duration: 38min
completed: 2026-06-30
---

# Phase 10 Plan 01: Injury-Risk-Flags Foundation Summary

**Deterministic SafetyFlag layer scaffold — frozen dataclass + locked compute_safety_flags stub, 3-mirror contract (analysis.ts/models.py/contract.md §9.13), warnAmberBg token, and a 33-test phase10 Nyquist scaffold where every no-flag invariant is GREEN against the empty stub and only must-fire rules are xfail-strict.**

## Performance

- **Duration:** ~38 min
- **Completed:** 2026-06-30
- **Tasks:** 3
- **Files modified/created:** 12

## Accomplishments
- `safety_flags.py`: `SafetyFlag` frozen dataclass (scalar-only, enum-guarded `__post_init__`) + `compute_safety_flags(...)` Wave-0 stub returning `[]` with a LOCKED signature and full channel-semantics + D-05 helper-contract docstring.
- Contract 3-mirror in lockstep: `SafetyFlagType`/`SafetyFlag` interface + `AnalysisResult.safetyFlags` (TS), `SAFETY_FLAG_TYPES`/`SAFETY_FLAG_MODE_SCOPES` tuples + bottom-of-file `SafetyFlag` re-export (Python, no import cycle), `§9.13` table + changelog (docs). `warnAmberBg #FFF6E5` added; brand `#FF4B33` and LLM `injuryRisk` untouched (D-01).
- phase10 scaffold: 16 programmatic fixtures + 6 test files. `python3 -m pytest tests/phase10 -q` = **23 passed, 10 xfailed, 0 failed, 0 xpassed**. Two-segment positive fixtures verified forward-correct (knee min 72.1° < 90° calibration premise; reverse-bend hold ~167°).

## Task Commits

1. **Task 1: safety_flags.py scaffold (dataclass + enum guards + stub)** — `22caaab` (feat)
2. **Task 2: contract 3-mirror + warnAmberBg token** — `1e8d7f0` (feat)
3. **Task 3: phase10 Nyquist test scaffold + fixtures** — `39382a0` (test)

## Files Created/Modified
- `backend/shared/python/sunity_shared/analysis/safety_flags.py` — SafetyFlag dataclass + enum tuples + compute_safety_flags stub (channel-semantics + D-05 helper contract docstring)
- `app/src/types/analysis.ts` — SafetyFlagType + SafetyFlag interface (reuse SeverityLevel/MetricConfidence) + AnalysisResult.safetyFlags
- `backend/shared/python/sunity_shared/models.py` — SAFETY_FLAG_TYPES/MODE_SCOPES tuples + SafetyFlag re-export (one-directional)
- `docs/contract.md` — §9.13 SafetyFlag table + changelog footer
- `app/src/theme/colors.ts` — warnAmberBg #FFF6E5
- `backend/tests/phase10/conftest.py` — 16 fixtures (elite-no-FP, temporal-disjoint, DTW timing-shift, two-segment reverse-bent knee/elbow, multi-joint, uncertain/ambiguous, single-variable wrong-phase/wrong-joint, no-phase-boundaries)
- `backend/tests/phase10/test_safety_flags_{dataclass,firing_rule,hyperextension,asymmetry,level,contract}.py` — GREEN no-flag + xfail-strict positives
- `.planning/phases/10-injury-risk-flags/deferred-items.md` — pre-existing out-of-scope failures logged

## Decisions Made
None beyond the plan — executed as specified. The channel-semantics (ch3 = uncertainty_proxy), the locked `compute_safety_flags` / `_joint_hyperextension_flags` signatures, and scalar-only SafetyFlag fields were all plan-mandated and applied verbatim.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1-4 deviations were required; the scaffold built cleanly and all per-task verification gates passed on first run.

## Issues Encountered

The full `backend/tests` regression run surfaced 10 FAILED pipeline-integration tests (phase06/phase08) + 11 R&D spike collection ERRORS. **Proven pre-existing and out of scope:** reverting my additive `models.py` re-export to the original (`102fbfe`) reproduces the identical failures (`NotPoleMotionError` in the mocked mode1 Gemini/vision-veto flow; ImportError on optional ML deps). Logged to `deferred-items.md`; not fixed (SCOPE BOUNDARY). The Phase 10 substrate suites (phase06/07/08/08_1/09/10) otherwise pass with **zero new regressions**.

## User Setup Required
None — no external service configuration required (pure scaffold + synthetic fixtures; no GPU/pod needed this wave).

## Next Phase Readiness
- 10-02 (trunk AND-gate) can extend `compute_safety_flags` against the locked signature; `test_posture_and_control_loss_emits_flag` + the contract-validator tests flip GREEN there.
- 10-03 (D-05 joint hyperextension) has its callable helper contract, two-segment fixtures, and uncertainty/scoped-NaN regression tests scaffolded and xfail-strict.
- 10-04 (asymmetry + level) has DTW timing-shift + level-scope fixtures ready.
- No blockers.

## Self-Check: PASSED

---
*Phase: 10-injury-risk-flags*
*Completed: 2026-06-30*
