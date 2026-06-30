---
phase: 10-injury-risk-flags
plan: 02
subsystem: api
tags: [safety-flags, dtw-alignment, force-signals, firestore-scalar, react-native, injury-risk, numpy]

# Dependency graph
requires:
  - phase: 10-injury-risk-flags (10-01)
    provides: SafetyFlag frozen dataclass + locked compute_safety_flags stub + warnAmberBg token + phase10 Nyquist scaffold
  - phase: 08-force-signals
    provides: ForceSignalsReport / StabilityMetric / PhaseBoundary (control-loss + phase substrate)
  - phase: 12-keypoint (pipeline)
    provides: _angles_to_dtw_median_dicts pattern mirrored by _dtw_aligned_joint_medians
provides:
  - "compute_safety_flags D-04 trunk firing rule (reference-anchored DTW-aligned + hip-local control-loss)"
  - "_phase_for_window (hold window -> phase, max-overlap >=50%, no-op on None)"
  - "_dtw_aligned_joint_medians (false-positive defense: DTW path-aligned reference comparison, not raw same-index)"
  - "_control_loss_for_joint LOCAL+TEMPORAL AND-gate + _control_loss_phase_level (D-06 reserve)"
  - "_process injection (mode1 a_ref / mode3 reshaped prev) + result['safetyFlags'] persistence"
  - "firestore_admin._validate_safety_flags single-path scalar-only validator"
  - "InjuryRiskSection/InjuryRiskFlagCard amber UI (all-4 copy map, omit-when-empty)"
affects: [10-03 D-05 joint hyperextension, 10-04 asymmetry+level_mismatch]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DTW-path-aligned reference comparison recomputed inside safety_flags (mirror pipeline _angles_to_dtw_median_dicts) — cancels intentional reference extension across timing shift"
    - "Window->phase deterministic bridge via max-overlap >=50% (_phase_for_window), no-op rather than widen"
    - "Joint-local + phase-level temporal AND-gate (control-loss substrate is phase-scoped — documented v1 limitation)"
    - "Single in-result persistence path for scalar-only list[dict] (no complete_analysis kwarg)"
    - "flagType copy-map UI so later backend rules render with zero UI change"

key-files:
  created:
    - app/src/components/InjuryRiskSection.tsx
  modified:
    - backend/shared/python/sunity_shared/analysis/safety_flags.py
    - backend/functions/pipeline/app.py
    - backend/shared/python/sunity_shared/firestore_admin.py
    - app/src/app/analysis/result.tsx
    - app/src/lib/userAnalyses.ts
    - backend/tests/phase10/test_safety_flags_firing_rule.py
    - backend/tests/phase10/test_safety_flags_contract.py

key-decisions:
  - "D-04 implemented reference-anchored ONLY (no absolute lumbar cutoff) — RESEARCH A3 resolution surfaced in plan, not a silent reduction; absolute trunk rule DEFERRED (needs mid-spine keypoint)"
  - "Temporal co-location granularity is PHASE-LEVEL (v1 limitation, documented in module) — stability substrate is phase-scoped, not per-frame"
  - "DTW alignment recomputed inside safety_flags (not threaded as kwarg) — Mode3 match is discarded before injection; matches _angles_to_dtw_median_dicts precedent"
  - "First Mode-3 video (no baseline) -> reference_angles=None -> trunk no-ops gracefully; surfaced as known limit (absolute D-05 carries Mode-3 promise)"

patterns-established:
  - "score_from_deviation(excess, tol=20) < 33 == excess > 1.5*tol — '허용 범위를 substantially 넘음' threshold tagged [ASSUMED], not 13-video curve-fit"
  - "Test reuses conftest timing_shifted fixtures + inline force_signals builders for wrong-phase-hip (conftest untouched)"

requirements-completed: [SAFE-01]

# Metrics
duration: 50min
completed: 2026-06-30
---

# Phase 10 Plan 02: Injury-Risk Trunk AND-Gate Vertical Slice Summary

**End-to-end D-04 trunk-hyperextension flag: reference-anchored DTW-path-aligned excess + hip-local phase-co-located control-loss AND-gate, persisted scalar-only via a single validator path, rendered as an amber expert-referral section — with 정은지 elite posture (alone / wrong-phase / timing-shifted-reference) locked to ZERO flags.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-06-30
- **Tasks:** 3
- **Files created/modified:** 8

## Accomplishments
- **D-02 LOCAL+TEMPORAL AND-gate core**: `_control_loss_for_joint(fsr, joint, phase=)` requires region-local (`joint in unstable_body_parts`) + severity medium/high + same-phase co-location; `_maybe_flag` fires only when posture AND control-loss both hold (posture alone never fires).
- **HIGH-A false-positive defense**: `_dtw_aligned_joint_medians` recomputes the pipeline's `motion_dtw` alignment so a student's extreme frames pair with the reference's extreme frames — the elite's own intentional extension cancels even under timing shift (`test_trunk_timing_shifted_same_extension_no_flag` GREEN).
- **MEDIUM-1 window→phase bridge**: `_phase_for_window` maps the shared `dimensions._select_window` frame window to the max-overlap `PhaseBoundary` (≥50% of the window) and NO-OPS to `None` rather than widening to "any phase".
- **D-04 trunk rule**: reference-anchored (no absolute lumbar cutoff, A3) + hip-local control-loss → `허리 부담 가능성` amber card. Mode 1 anchors on a_ref (정은지), Mode 3 on reshaped previous video, first-video gracefully no-ops (surfaced).
- **Single-path persistence**: `result['safetyFlags']` set in `_process` (scalar-only camelCase), validated by `firestore_admin._validate_safety_flags` at the single in-result write point — no `complete_analysis` kwarg, no duplicate path.
- **UI**: `InjuryRiskSection`/`InjuryRiskFlagCard` (amber `warnAmberBg`/`warnAmber`, no brand red) with a copy map for all 4 flag types (so 10-03/10-04 render automatically), omits the section when empty (no reassurance), D-04 rigid-body parenthetical inline.
- **Tests**: `tests/phase10` = 29 passed, 7 xfailed (the 7 are 10-03/10-04 must-fire rules), 0 failed. App `npm run typecheck` clean.

## Task Commits

1. **Task 1: D-02 AND-gate + _phase_for_window + DTW-aligned trunk rule (TDD)** — `774e2ee` (feat)
2. **Task 2: _process injection + single-path _validate_safety_flags** — `e6f1b3b` (feat)
3. **Task 3: amber InjuryRiskSection on result.tsx** — `708464f` (feat)

## Files Created/Modified
- `backend/shared/python/sunity_shared/analysis/safety_flags.py` — `_phase_for_window`, `_dtw_aligned_joint_medians`, `_control_loss_for_joint`/`_control_loss_phase_level`, `_maybe_flag`, `_trunk_hyperextension_flag`, full `compute_safety_flags`
- `backend/functions/pipeline/app.py` — `_reshape_prev_angles` helper + Phase-10 injection (mode1 a_ref / mode3 reshaped prev, `result['safetyFlags']` set, graceful try/except)
- `backend/shared/python/sunity_shared/firestore_admin.py` — `_validate_safety_flags` scoped validator + single wired call on `result['safetyFlags']`
- `app/src/components/InjuryRiskSection.tsx` — amber section + flag card, all-4 copy map, severity-sorted, omit-when-empty
- `app/src/app/analysis/result.tsx` — import + conditional render after score gauge, before 동작 비교
- `app/src/lib/userAnalyses.ts` — `safetyFlags` null-guard in `normalize()`
- `backend/tests/phase10/test_safety_flags_firing_rule.py` — un-xfailed positive + timing-shift/wrong-phase/phase-window regression tests
- `backend/tests/phase10/test_safety_flags_contract.py` — un-xfailed validator tests

## Decisions Made
- D-04 reference-anchored-only (no absolute lumbar cutoff) per RESEARCH A3 — explicitly surfaced as a refinement of D-04, not a silent reduction; the absolute trunk rule is DEFERRED.
- Temporal co-location is phase-level for v1 (the StabilityMetric substrate is phase-scoped); documented as a known limitation in the module.
- DTW alignment recomputed inside `safety_flags` rather than threaded as a kwarg (Mode-3 match is out of scope at the injection point; matches the established `_angles_to_dtw_median_dicts` precedent).
- The `injuryRisk` token appears only in D-01 boundary-documentation comments (stating independence), never as data flow — the LLM/deterministic boundary is preserved.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1-4 deviations were required; all per-task verification gates passed and the headline elite-no-FP gates are GREEN.

## Issues Encountered
- The full `backend/tests` run shows 54 pre-existing failures + 11 R&D spike collection errors. **Proven pre-existing and out of scope:** reverting only my two modified source files (`pipeline/app.py`, `firestore_admin.py`) to HEAD reproduces 56 failures / 1986 passes; with my changes restored it is 54 failures / 1988 passes — my changes turn the 2 contract tests GREEN and add ZERO regressions. The 54 stem from a test-harness `app` module-name collision (`importorskip("app")` resolving the wrong `app.py`) and missing gemini/knee env fixtures, identical on clean HEAD. The Phase-10 + pipeline + force_signals substrate suites pass cleanly.

## User Setup Required
None — no external service configuration required (pure deterministic layer + synthetic fixtures; no GPU/pod needed this plan).

## Next Phase Readiness
- 10-03 (D-05 joint hyperextension, absolute/reference-free) can append to `compute_safety_flags`; its xfail-strict must-fire tests + two-segment fixtures are ready, and the amber UI already copy-maps `joint_hyperextension` → renders with zero UI change.
- 10-04 (asymmetry + level_mismatch) similarly auto-renders; `_control_loss_phase_level` is reserved for D-06 whole-body overreach.
- No blockers.

## Self-Check: PASSED

---
*Phase: 10-injury-risk-flags*
*Completed: 2026-06-30*
