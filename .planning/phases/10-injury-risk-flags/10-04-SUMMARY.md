---
phase: 10-injury-risk-flags
plan: 04
subsystem: analysis
tags: [safety-flags, d-03, d-06, asymmetry, level-mismatch, dtw-aligned, reference-anchored, numpy]

# Dependency graph
requires:
  - phase: 10-injury-risk-flags (10-02)
    provides: compute_safety_flags (locked sig) + _dtw_aligned_joint_medians + _phase_for_window + _control_loss_for_joint/_control_loss_phase_level + amber InjuryRiskSection copy-map + reference_angles/experience/reference_level plumbing
  - phase: 10-injury-risk-flags (10-03)
    provides: D-05 joint-hyperextension + sagittal-plane synthetic fixture geometry + per-branch gate precedent
  - phase: 10-injury-risk-flags (10-01)
    provides: SafetyFlag dataclass + xfail-strict asymmetry/level positives + timing-shifted fixtures
  - phase: 08-force-signals
    provides: ForceSignalsReport / StabilityMetric / PhaseBoundary (control-loss + phase substrate)
provides:
  - "D-03 _asymmetry_flag(angles, reference_angles, fsr, profile) -> SafetyFlag | None (DTW-path-aligned reference-anchored excess, explicit L/R pairs, MAX aggregation, pair-local + phase-co-located control-loss)"
  - "_max_control_loss_severity(fsr) helper (max medium/high instability severity for D-06 scaling)"
  - "D-06 _level_mismatch_flag(mode, experience, reference_level, fsr) -> SafetyFlag | None (Mode-1 only, enum-guarded ladder, rank-gap x instability severity)"
  - "All four SafetyFlag types complete in compute_safety_flags (trunk + joint + asymmetry + level) -> SAFE-01 satisfied"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DTW-path-aligned reference-anchored asymmetry: excess = max(0, student_LR - ref_LR) from _dtw_aligned_joint_medians so intentional reference asymmetry cancels even at shifted timing (HIGH-A — not raw same-index)"
    - "Explicit L/R joint pairs + MAX aggregation: single most-asymmetric pair drives the flag (averaging would dilute one bad joint), responsible pair named in audit string"
    - "Pair-local + phase-co-located control-loss AND-gate (D-02): worst pair's two joints checked via _control_loss_for_joint at the asymmetry hold-window phase"
    - "Enum-guarded level ladder inside the module (do not trust upstream normalize blindly): non-enum experience/reference_level -> fail-safe None (T-10-02)"
    - "Severity = rank-gap x instability: gap=1+medium -> low (no over-warn), gap>=2+high -> high"

key-files:
  created: []
  modified:
    - backend/shared/python/sunity_shared/analysis/safety_flags.py
    - backend/tests/phase10/test_safety_flags_asymmetry.py
    - backend/tests/phase10/test_safety_flags_level.py
    - backend/tests/phase10/conftest.py

key-decisions:
  - "Asymmetry reuses the 10-02 _dtw_aligned_joint_medians + _phase_for_window helpers (alignment and window->phase mapping NOT re-rolled) — the DTW path pairs student extreme frames with the reference's corresponding frames so a timing-shifted reference asymmetry cancels (test_timing_shifted_same_asymmetry_no_flag GREEN with real impl)."
  - "MAX aggregation over explicit _ASYMMETRY_PAIRS (elbow/shoulder/hip/knee) rather than averaging: a single severely-asymmetric joint is the actionable risk signal; the responsible pair is named in posture_condition."
  - "Asymmetry posture threshold = score_from_deviation(excess, tol=20) < 33 (1.5x tol, same provenance as the trunk threshold) — reference-anchored KISMAM, no 13-video curve-fit (D-07)."
  - "D-06 ladder guards enum membership INSIDE safety_flags.py (basic/beginner=0, intermediate=1, advanced=2); spoofed/None -> None. Severity scales with BOTH rank gap and instability so gap=1 does not over-warn intermediate users on advanced references."
  - "MODE_EXPERT mirrored as a local _MODE_EXPERT='mode1' constant to avoid a models->safety_flags import cycle (single-direction dependency preserved)."

patterns-established:
  - "TDD per task: RED commit (flip xfail positives to real-impl asserts + add MAX-pair/severity-scaling assertions) then GREEN commit (implementation), gates visible in git log."
  - "Pre-existing full-suite failures isolated by reverting only safety_flags.py to its pre-change state and re-running the same suite: identical 54-failed/1959-passed count proves zero regression from this plan."

requirements-completed: [SAFE-01]

# Metrics
duration: 45min
completed: 2026-06-30
---

# Phase 10 Plan 04: D-03 Asymmetry + D-06 Level-Mismatch Summary

**Completes the four-flag deterministic SafetyFlag set: a DTW-path-aligned reference-anchored left/right asymmetry flag (explicit L/R pairs, MAX aggregation, pair-local + phase-co-located control-loss, intentional asymmetry cancels even at shifted timing, absolute L/R never flagged) and a Mode-1-only level-mismatch flag (enum-guarded ladder, severity scaling with rank-gap x instability so a gap of exactly 1 does not over-warn) — both fire via the D-02 LOCAL+TEMPORAL AND-gate and auto-render through the existing amber InjuryRiskSection, satisfying SAFE-01.**

## What Was Built

### Task 1 — D-03 DTW-aligned reference-anchored asymmetry flag
`_asymmetry_flag(angles, reference_angles, fsr, profile)` in `safety_flags.py`:
- Computes `excess = max(0, student_LR - ref_LR)` for each pair in the module-level `_ASYMMETRY_PAIRS` (elbow/shoulder/hip/knee), where `student_LR`/`ref_LR` are absolute L/R differences of the **DTW-path-aligned per-joint medians** from the reused 10-02 `_dtw_aligned_joint_medians` helper — never raw same-index frames. This is exactly why a reference's own intentional asymmetry cancels even when student/reference timing differs (HIGH-A).
- **MAX aggregation** over pairs (not average): the single most-asymmetric pair drives the flag; the responsible pair is named in `posture_condition` (e.g. "좌우 고관절 비대칭이 기준 대비 45° 초과").
- Posture threshold reuses `kismam.score_from_deviation(excess, tol=20) < 33` (1.5x tol) — reference-anchored, same provenance as the trunk threshold, no curve-fit (D-07).
- **Pair-local + phase-co-located control-loss** via `dimensions._select_window` -> `_phase_for_window` -> `_control_loss_for_joint(worst pair's two joints, phase=P)`. When the phase is underivable (`_phase_for_window` -> None) the flag no-ops.
- `reference_angles=None` (first Mode-3 video / absent) -> graceful no-op (surfaced limitation T-10-11). Absolute L/R asymmetry is never flagged.
- Added `_max_control_loss_severity(fsr)` helper (max medium/high instability) feeding D-06.

### Task 2 — D-06 Mode-1-only level-mismatch flag
`_level_mismatch_flag(mode, experience, reference_level, fsr)` in `safety_flags.py`:
- Returns None immediately unless `mode == _MODE_EXPERT` ("mode1") — Mode 3 move difficulty is unknown, so D-02 control-loss catches overreach there.
- **Enum-guarded ladder** inside the module (`_LEVEL_LADDER`: basic/beginner=0, intermediate=1, advanced=2); a spoofed/None `experience` or `reference_level` -> fail-safe None (T-10-02), not trusting upstream `normalize_body_profile` blindly.
- `gap = reference_rank - experience_rank`; `posture_met = gap >= 1`. **Severity scales with BOTH gap and instability**: gap==1 + medium -> 'low', gap>=2 + high -> 'high', else 'medium'. A gap of exactly 1 does not over-warn intermediate users on advanced references.
- Control-loss partner is the whole-body `_control_loss_phase_level(fsr)` (the one legitimate phase-level case, per 10-02). `mode_scope='mode1_only'`.

Both flags wired into `compute_safety_flags` (asymmetry singular-append alongside trunk; level singular-append after the joint-hyperextension extend).

## Tests

- `test_safety_flags_asymmetry.py`: 7 tests — equal-asymmetry/no-reference/timing-shifted/no-control-loss/wrong-phase negatives + positive fire + MAX-pair-drives-flag-with-audit. The timing-shifted negative now passes against the **real** implementation, proving the DTW-aligned medians cancel a shifted-timing reference asymmetry (would false-positive under raw same-index).
- `test_safety_flags_level.py`: 7 tests — mode3/no-control/spoof/None/gap=0 negatives + positive fire + severity-scaling (gap=1+medium < gap=2+high).
- Added `medium_control_loss_report` fixture to `conftest.py` for the severity-scaling assertion.
- Full phase10 suite: **54 passed, 4 skipped** (pod-deferred real-elite), 0 failed, 0 xfailed, 0 xpassed.

## Deviations from Plan

None — plan executed as written. The two remaining xfail positives were flipped to real-implementation asserts as specified, and the new MAX-aggregation + severity-scaling assertions were added per the acceptance criteria.

## Deferred / Out-of-Scope (pre-existing, NOT introduced)

- Full backend suite (`python3 -m pytest tests`) has **11 pre-existing collection errors** (spike/smoke modules importing a `backend.`/`fixtures` namespace not on the test path) and **54 pre-existing order-dependent failures** (phase06/08, pipeline_phase8/9, gemini-wiring, body-profile, height-scale) caused by module-global singleton pollution across modules. Proven unrelated to this plan: reverting only `safety_flags.py` to its pre-change state yields the identical 54-failed/1959-passed count, and each affected file passes in isolation. Logged for a future test-isolation cleanup; out of scope per the deviation scope boundary.

## App / Contract

- No TypeScript touched. `app/src/types/analysis.ts` already carries `asymmetry`/`level_mismatch` in `SafetyFlagType` and the `InjuryRiskSection` copy-map covers all four types, so the new flags auto-render with zero UI change. `npm run typecheck` GREEN.
- No contract change (SafetyFlag shape unchanged); 3-mirror rule untouched.

## Verification

- `python3 -m pytest tests/phase10 -q` -> 54 passed, 4 skipped (pod-deferred), 0 failed/xfailed/xpassed.
- `python3 -m pytest tests/phase10/test_safety_flags_firing_rule.py::test_elite_posture_alone_no_flag` -> GREEN (정은지 elite no-FP preserved across the full four-flag rule set).
- `cd app && npm run typecheck` -> GREEN.
- Grep gates: `_dtw_aligned_joint_medians` / `_ASYMMETRY_PAIRS` / `score_from_deviation` / `_phase_for_window` / `_control_loss_for_joint` present in `_asymmetry_flag`; `_MODE_EXPERT` / `mode1_only` / `_LEVEL_LADDER` (`experience ... in`) present in `_level_mismatch_flag`.

## Commits

- `675d4f1` test(10-04): D-03 asymmetry firing tests (RED)
- `4dae0fa` feat(10-04): D-03 DTW-aligned reference-anchored asymmetry flag (GREEN)
- `8c214f3` test(10-04): D-06 level-mismatch firing tests (RED)
- `4778471` feat(10-04): D-06 mode1-only level-mismatch flag (GREEN)

## Self-Check: PASSED

- Created file `10-04-SUMMARY.md` — FOUND.
- Commits `675d4f1`, `4dae0fa`, `8c214f3`, `4778471` — all FOUND in git log.
