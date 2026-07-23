---
phase: 33-result-trust-recovery
plan: 19
subsystem: analysis / M3 alignment spec
tags: [spec, m3, motiondtw, alignment, scoring-trust, doc-only]
requires: [33-01]
provides: ["33-M3-SPEC.md (locked M3 alignment contract)"]
affects: [33-05]
tech-stack:
  added: []
  patterns: ["spec-before-code (locked contract gates implementation)", "paired user+reference DTW range", "fail-closed alignment fallback"]
key-files:
  created: [".planning/phases/33-result-trust-recovery/33-M3-SPEC.md"]
  modified: []
decisions:
  - "COVERAGE_FLOOR=0.80: student clip < 80% of density-matched reference → do NOT window reference (fail-closed full-ref) so missing motion surfaces as deviation, never hidden"
  - "Structural floor: shared-base motions must keep ref_boundary_frame strictly interior to the window (both base+extension scored) — directly blocks the silent-hard-phase-drop inflation attack"
  - "Fail-closed always to full reference (r_s=0,r_e=nr) = current-behavior-equivalent, never a silently-truncated window"
  - "Paired-range API: MotionMatch gains ref_start/ref_end; find_action_segment returns ((u_s,u_e),(r_s,r_e)); path indices window-local"
  - "AMBIGUITY_EPSILON=0.02 / AMBIGUITY_OVERLAP_MIN=0.80 as alignment gate constants — explicitly NOT scoring thresholds (D-20/D-29 constants stay hash-identical)"
metrics:
  duration: "~15m"
  completed: 2026-07-23
---

# Phase 33 Plan 19: M3 Alignment Spec (LOCKED) Summary

Locked `33-M3-SPEC.md` — the paired user+reference DTW range API, a reference-phase coverage floor that forbids silently dropping hard reference phases, fail-closed ambiguity handling, and byte-identical-deviation invariants — so the eventual M3 implementation (33-05) is provably alignment-only and non-inflating (codex concern 4, the Core-Value-critical one).

## What was built

`33-M3-SPEC.md` (LOCKED, blocks 33-05), covering the exact codex concern 4 / suggestion 5 gap:

- **§1 Paired-range API** — `MotionMatch` gains `ref_start`/`ref_end`; `find_action_segment` new signature returns `((u_s,u_e),(r_s,r_e))`; `motion_dtw` consumes `dtw(F_user[u_s:u_e], F_ref[r_s:r_e])`; path indices window-local. This closes the API gap where `MotionMatch` carried no reference range and `F_ref` was consumed whole (motiondtw.py:73-100) — the reason SEED's "window the reference when nu<nr" was previously inexpressible.
- **§2 Coverage floor** — numeric `COVERAGE_FLOOR=0.80` (retained ref fraction `nu/nr`) + structural floor (shared-base boundary must stay strictly interior to the window). A below-floor window is rejected → no silent phase drop → no score inflation.
- **§3 Boundary rules** — `nu<nr` = new reference-windowing path (the one that makes 준비/대기 removal actually fire); `nu≈nr` (post-Task-1 dominant case) trims only head/tail; two-way symmetric slide (long side windowed to short side, no motion-key branch).
- **§4 Fail-closed** — floor violation / structural violation / ambiguous near-equal windows (Jaccard < 0.80 within distance 0.02) all fall back to full-reference `(0,nr)` = current-behavior-equivalent, never a silently-truncated window.
- **§5 Ripple** — the 3 production call sites (`pipeline/app.py:1770`, `:4015`, `safety_flags.py:245`) each must pass `a_ref[ref_start:ref_end]`; segments.py stays consistent via `boundary_win = boundary_full - ref_start`; safety-flag no-FP/no-FN regression obligation named.
- **§6/§7 Invariants + RED tests** — byte-identical-when-already-aligned, zero-on-identity, no-motion-key-branch (D-02), coverage-floor-fallback, constants-hash-identical (D-20/D-29), safety-flag regression. Exact 33-05 test list enumerated (10 items, incl. updating the 2 existing tests that pin current behavior).

## Invariants 33-05 must satisfy (D-18 "틀리면 걸리는 장치")

| ID | Invariant | Test |
|----|-----------|------|
| I1 | identical inputs → per_joint_deviation == 0 | test_m3_zero_on_identity_through_window |
| I2 | already-aligned → byte-identical deviations vs pre-M3 | test_m3_byte_identical_when_already_aligned |
| I3 | no motion-key / technique branch in window selection (D-02) | test_m3_no_motion_key_branch |
| I4 | below-floor window rejected → full-ref fallback; window actually fires when eligible | test_m3_coverage_floor_fallback / test_m3_shared_base_structural_floor / test_m3_window_actually_fires |
| I5 | scoring formula + constants (tol 20°/slope 1.2/cap 90/MEAN_EPSILON 0.1/P99_EPSILON 1.0) hash-identical (D-20/D-29) | test_m3_constants_hash_unchanged |
| — | safety_flags no new FP/FN (S3 ripple) | test_m3_safety_flags_no_regression |

## Coverage-floor values 33-05 must implement (alignment gate constants — NOT scoring thresholds)

- `COVERAGE_FLOOR = 0.80`
- `AMBIGUITY_EPSILON = 0.02`
- `AMBIGUITY_OVERLAP_MIN = 0.80`

## Deviations from Plan

None — plan executed exactly as written. Single doc-only task; no code changed; no Pod; no package installs.

## Requirements

D-02 (no motion-key branch — pinned as invariant I3), D-18 (틀리면 걸리는 장치 = the 6 RED invariants), D-20/D-29 (scoring constants hash-identical, alignment-only), D-27 (authored verbatim from the SEED's C+M3 Task 3 + 성공 판정 기준 + ripple 3 sites, no reinvention).

## Self-Check: PASSED

- FOUND: .planning/phases/33-result-trust-recovery/33-M3-SPEC.md
- FOUND commit 3ad0059 (spec)
- Automated verify (task <verify> block): OK (coverage floor / ref_start / byte-identical / fail-closed / 1770|4015|safety_flags all present)
