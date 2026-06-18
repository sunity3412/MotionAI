---
phase: 19-vision-hybrid
plan: 01
subsystem: testing
tags: [pytest, scoring, ipsf, red-tests, tdd, kismam, dimensions, pipeline]

# Dependency graph
requires:
  - phase: 19-vision-hybrid (D-05 spike)
    provides: 6 fault/correct anchor pairs (known-answer direction labels, no numeric score targets)
provides:
  - RED test suite for the re-designed scorer (SCORE-06/07, TRUST-01/02/03/05) that fails by behavior against current mean-based code
  - 2 contradiction-case updates (overall_from_dimensions uses_core_dimensions, monotonic beyond-tolerance) defining Wave 1 regression contract
  - Mode1 scoringBasis serialized-contract assertion (build_mode1 comparison["scoringBasis"]=="reference_motion") separated from the Mode3 gate
  - Mode3 4-value scoringBasis gate (reference_free_absolute / recognized_motion_absolute / previous_analysis_plus_absolute / previous_analysis_plus_reference_free_absolute) + reference_motion-never-emitted invariant
  - per-test env-gated D-05 anchor file with always-on synthetic above-cutoff sensitivity gate
affects: [19-02, 19-03, 19-04, Wave 1 scorer redesign, Wave 2 display-score parity]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED-by-behavior (not collection): new cases assert the future contract and fail standalone against current code"
    - "per-test @requires_anchor_env (module-level pytestmark forbidden) so GPU-free synthetic cases always run"
    - "direction-only assertions (fault<correct, dominant dim, 160° threshold) — no curve-fit numeric targets (D-05 boundary)"

key-files:
  created:
    - backend/tests/test_anchor_known_answer.py
  modified:
    - backend/tests/test_kismam.py
    - backend/tests/test_dimensions.py
    - backend/tests/test_pipeline_mode3.py

key-decisions:
  - "test_within_tolerance_remains_high is intentionally RED today (dead-zone contract Wave 1 will satisfy); test_clean_pose_high_score / synthetic above-cutoff pass today as regression guards"
  - "Mode1 reference_motion basis asserted on serialized build_mode1 output (ITER-4 HIGH-1), kept out of the Mode3 4-value gate (ITER-3 MEDIUM-1)"

patterns-established:
  - "Pattern 1: RED proven by standalone behavioral failure with collection clean (errored 0)"
  - "Pattern 2: anchor fixtures + per-pair dominant-dimension meta preserved as constants so Pod-resume activation is mechanical"

requirements-completed: [SCORE-06, SCORE-07, TRUST-01, TRUST-02, TRUST-03, TRUST-05]

# Metrics
duration: 18min
completed: 2026-06-18
---

# Phase 19 Plan 01: Wave 0 RED Tests Summary

**RED test suite (10 new cases + 2 contradiction-case updates + env-gated D-05 anchor file) that fails by behavior against the current mean-based scorer, locking the re-designed contract for SCORE-06/07 and TRUST-01/02/03/05.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-06-18
- **Tasks:** 2
- **Files modified:** 4 (3 modified, 1 created)

## Accomplishments
- Updated 2 contradiction cases to the new semantics contract (mean → core-dimensions; monotonic → beyond-tolerance dead-zone).
- Added 6 scoring-core RED cases + 5 pipeline RED cases that fail standalone against current code.
- Created `test_anchor_known_answer.py` with per-test env-gating (6 real-video pairs skip; synthetic above-cutoff always runs).
- Verified RED by actual behavioral failure (not mere collection); confirmed collection is clean (errored 0).

## Task Commits

1. **Task 1: scoring-core RED + 2 contradiction-case updates (SCORE-06/07/TRUST-02)** - `292a404` (test)
2. **Task 2: pipeline RED + Mode1 basis split + build_mode3 compat + vision identity + anchor file (TRUST-01/03/05)** - `7a5cf5a` (test)

## Files Created/Modified
- `backend/tests/test_kismam.py` - monotonic → 0/30/60° beyond-tolerance; + within_tolerance_remains_high, single_major_fault_dominates, clean_pose_high_score, shoulder_focus_label
- `backend/tests/test_dimensions.py` - is_mean → uses_core_dimensions; + micro_bent_zero_track, intentional_bend_not_penalized, stability_does_not_inflate
- `backend/tests/test_pipeline_mode3.py` - + display_matches_score_source, mode1_scoring_basis_reference_motion, unknown_move_gate (Mode3 4-value parametrize), build_mode3_backward_compat, vision_hook_passthrough
- `backend/tests/test_anchor_known_answer.py` (new) - per-test @requires_anchor_env over 6 pairs + always-on synthetic above-cutoff; fixture S3 keys + per-pair dominant-dimension meta as constants

## RED Cases — standalone failure (behavior, not collection)

Cases that FAIL today against current mean/proportional code, with one-line failure reason:

**test_kismam.py**
1. `test_single_major_fault_dominates` — current mean dilutes 1 fault to ~88; new contract needs < 70 (single major fault must dominate).
2. `test_within_tolerance_remains_high` — current Gaussian gives 88 at dev=10°/tol=20°; new dead-zone contract needs >= 90 (no penalty inside tolerance).
3. `test_shoulder_focus_label` — COACHING_FOCUS['left/right_shoulder'] currently '안정성' (stability mislabel); contract forbids '안정성'/'떨림'/부위 키워드.

**test_dimensions.py**
4. `test_overall_from_dimensions_uses_core_dimensions` — current mean returns 73 for {angle:40,line:80,stability:99}; contract needs 40 (core min, stability non-contributing).
5. `test_micro_bent_zero_track` — current line_score is proportional, 140° → non-zero; contract needs 0 (micro-bent below 160° invalidates the element).
6. `test_stability_does_not_inflate` — current mean returns 60 for {40,40,99}; contract needs <= 50 (stability must not inflate).

**test_pipeline_mode3.py**
7. `test_display_matches_score_source` — `_angles_to_dtw_median_dicts` helper absent (Wave 2 path-aligned median source).
8. `test_mode1_scoring_basis_reference_motion` — build_mode1 does not emit serialized comparison["scoringBasis"].
9. `test_unknown_move_gate[4 params]` — `assemble.is_reference_free_motion` absent + Mode3 comparison emits no scoringBasis field (gate absent).
10. `test_build_mode3_backward_compat` — build_mode3 has no `scoring_basis` arg (TypeError) + reference_motion ValueError unimplemented.
11. `test_vision_hook_passthrough` — `_apply_vision_veto` absent (Wave 1 v1 pass-through hook).

**Always-on (NOT RED — regression/sensitivity guards, pass today):**
- `test_kismam.py::test_clean_pose_high_score` (dev=8° → ~92 >= 90)
- `test_anchor_known_answer.py::test_above_cutoff_synthetic_stays_high` (synthetic clean pose → overall >= 90)
- 6 real-video anchor pairs: SKIP without `RUN_PHASE19_ANCHORS=1` (GPU/S3 + harness pending Pod resume).

## Verification evidence

- `pytest tests/test_kismam.py tests/test_dimensions.py` → 6 failed (behavior RED), 24 passed; `--collect-only` → 30 collected, errored 0.
- `pytest tests/test_pipeline_mode3.py::<5 cases>` → 8 failed (parametrize-expanded), collection clean (11 collected total in file).
- `pytest tests/test_anchor_known_answer.py` (env unset) → 1 passed (synthetic), 6 skipped (real-video pairs).
- grep gates: module-level `pytestmark` 0; `@requires_anchor_env` per-test only; `is score_result` present; serialized `["scoringBasis"]` access present; `reference_motion` absent from `_MODE3_BASES` parametrize.
- Pre-existing failing tests (test_pole_detector / test_pipeline_geminid_wiring / test_spike_gemini_moment_smoke) untouched.

## Decisions Made
- `test_within_tolerance_remains_high` left intentionally RED (it encodes the dead-zone semantics Wave 1 will implement) — distinct from the always-on above-cutoff guards which pass today.
- Mode1 basis assertion uses the serialized `build_mode1` comparison dict (result-contract field), not an internal/global variable, per ITER-4 HIGH-1.

## Deviations from Plan

None - plan executed exactly as written. All new cases fail by behavior; contradiction cases updated to the new contract; anchor file uses per-test env-gating with no module-level skip.

## Issues Encountered
- Local interpreter: system `python` absent; used `backend/.venv/bin/python` (Python 3.14.5) for pytest. No code impact.

## Next Phase Readiness
- Wave 1 (scorer redesign) now has explicit pass criteria: every RED case above defines the target contract.
- Wave 2 (display-score parity) gated on `_angles_to_dtw_median_dicts`.
- D-05 anchors are mechanical to activate post-Pod-resume (`RUN_PHASE19_ANCHORS=1`) once `analyze_fixture_for_anchor` harness lands.

## Self-Check: PASSED

- All 4 test files + SUMMARY.md exist on disk.
- Both task commits (292a404, 7a5cf5a) present in git history.

---
*Phase: 19-vision-hybrid*
*Completed: 2026-06-18*
