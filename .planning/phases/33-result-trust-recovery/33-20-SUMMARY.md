---
phase: 33-result-trust-recovery
plan: 20
subsystem: planning-coverage
tags: [coverage-matrix, D-18, D-23, D-27, codex-suggestion-10]
requires: [33-01]
provides: ["33-COVERAGE-MATRIX.md (single cited coverage source for 33-06/08/09/16)"]
affects: [33-06, 33-08, 33-09, 33-16]
tech-stack:
  added: []
  patterns: ["single-source-of-truth coverage inventory grounded against code"]
key-files:
  created: [".planning/phases/33-result-trust-recovery/33-COVERAGE-MATRIX.md"]
  modified: []
decisions:
  - "combo is the reconciled 5th non-paired motion the four plans dropped"
  - "combo stays UNREGISTERED by design (REGISTERED_MOTIONS frozen at 10, P1 2026-06-27)"
  - "climb is a scoreless mode1 comparison-gate motion — verified by gate behavior + M8 eyeball, NOT margin"
metrics:
  duration: "~15m"
  completed: 2026-07-23
  tasks: 1
  files: 1
---

# Phase 33 Plan 20: Canonical Coverage Matrix Summary

Produced the ONE canonical 11-motion coverage matrix (`33-COVERAGE-MATRIX.md`) that
reconciles the four disagreeing coverage inventories in 33-06/08/09/16 and forces
climb / sideway-spin / combo to explicit resolution — the D-23 "6동작 전수" obligation is
now checkable against a single grep-grounded source (codex suggestion 10 / D-23 / D-18).

## What was built

A single canonical matrix with one row per the 11 reference documents. Columns:
motionId, lineage, registered, paired fixture, success/fault availability, self-comparison
substitute, M8 visual-check, presentation coverage (A-1/A-2/A-5), verification owner.
Every citing plan now has one source to cite instead of carrying its own inventory.

## Reconciled counts (grounded against code, not prose)

- **`REGISTERED_MOTIONS` = 10** — verified against `gemini_motion_classifier.py:26` and
  `test_gemini_motion_classifier.py:28` (`assert len == 10`). `combo` is NOT in it.
- **phase25 fixtures = 6** — verified against
  `backend/evals/phase25/baseline/phase25_sweep_report.json` `results[]` motion_id:
  {climb, elbow-twist-sister, kip-up, pdshape, peter-pan, power-spin}, each success + fault.
- **reference library = 11** — from the substrate-gap 재처리 위험도 표.
- **Non-paired = 11 − 6 = 5** (not 4): `foxtop`, `foxtop-split`, `invert`, `sideway-spin`,
  **`combo`**. The plans' "four" was missing `combo`.
- **Registered = 10 + unregistered = 1** (`combo`).
- **M8 original-5 lineage** (bukuroo-06-06 `(x,0,y)` → re-processed `(x,y,0)`):
  climb, foxtop, foxtop-split, invert, sideway-spin — these 5 need a Simulator eyeball.

## The three ambiguous motions — resolved

- **climb** — registered, has a fixture, but **SCORELESS** (mode1 comparison-gate only,
  substrate rescore ran "climb 제외"). It lacks the margin/separation substrate 33-06
  assumed. Resolution: verify climb at the **comparison-gate level** (gate behaves; no
  fabricated score) + **M8 Simulator eyeball** (original-5 lineage). It gets NO margin
  number. 33-06 must not list climb among the margin-sweep motions.
- **sideway-spin** — registered, **fixture-less**, non-inversion. The motion 33-06 dropped
  and 33-16 kept. Resolution: it is one of the five fixture-less motions and MUST be covered
  via `verify_self_comparison.py` (coverage obligation D-23 applies even though the PR-
  regression concern R-3 does not). Original-5 lineage → M8 eyeball.
- **combo** — **UNREGISTERED** (absent from `REGISTERED_MOTIONS`; intentional per the P1
  2026-06-27 freeze). Fixture-less, inversion-positive, longest clip (931f) with a non-
  determinism history. Resolution: verified via `verify_self_comparison.py` **plus R-4
  2-run determinism** (`RTMW_DETERMINISTIC=1`). Presentation = **A-2 `__common__` only**
  (not in A-1; no A-5 crop). Recorded as intentional, not a silent skip.

## Consumer contract embedded in the matrix

- 33-06: margin sweep on the 5 scoring fixtures; climb by comparison-gate; 5 fixture-less
  via self-comparison; combo adds R-4 determinism.
- 33-08: A-1 covers the 10 registered; combo out of A-1 by design.
- 33-09: A-2 motion-specific cues for 10 registered; combo → `__common__`.
- 33-16: re-sweep 6 fixtures; 5 fixture-less via substitute; M8 eyeball on original-5.

## Deviations from Plan

None — plan executed exactly as written (single doc-only task, no code, no Pod).

## Self-Check: PASSED

- FOUND: `.planning/phases/33-result-trust-recovery/33-COVERAGE-MATRIX.md`
- FOUND commit: 5dc9aac (coverage matrix)
- Automated verify (plan `<verify>`): OK (climb + sideway-spin + combo + self-comparison all present).
