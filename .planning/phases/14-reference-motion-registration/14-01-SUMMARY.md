---
phase: 14-reference-motion-registration
plan: 01
subsystem: testing
tags: [pytest, firestore, contract-lockstep, force-pattern, body-normalization, reference-motion, backfill, typescript]

# Dependency graph
requires:
  - phase: 06-body-normalization
    provides: measure_body_profile + seed-reference-body-profile.mjs pattern + bodyNormalizationProfile contract field
  - phase: 09-force-direction-pattern
    provides: infer_force_direction_pattern + _validate_force_pattern_inference scoped validator + ForcePatternInference TS interface
  - phase: 04-ux-occlusion-confidence
    provides: all 11 references RTMW phase4_v1 active (joints3d/angles/keypointReport stored)
provides:
  - "Read-only Firestore audit of all 11 references (resolves A2 — which already carry which downstream fields + completeRequiredSet count)"
  - "Wave-0 pytest harness pinning reference-v1 pinned-config D-01 parity (RED target for 14-02 helper) + env-flip divergence + R3-1 scoped-validator fixtures + SC#4 graceful + D-02 verdict"
  - "3-way contract lockstep: ReferenceMotion gains techniqueProfile/forceDirectionPattern/captureViews (+ meanAngles/bodyNormalizationProfile in contract.md §3) and normalize() surfaces them null-safely"
affects: [14-02, 14-03, phase-15-mode1-comparison]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "REFERENCE_V1_FORCE_CONFIG pinned-config parity (provably exact for the pinned config, NOT student-path-exact)"
    - "Env-gated strict import (PHASE14_REQUIRE_BACKFILL_HELPER) — importorskip unset / hard-fail when =1"
    - "Scoped Firestore validator per field type (force-pattern scoped vs generic flat)"

key-files:
  created:
    - app/scripts/audit-reference-fields.mjs
    - backend/tests/phase14/__init__.py
    - backend/tests/test_reference_backfill.py
  modified:
    - app/src/types/analysis.ts
    - docs/contract.md
    - app/src/lib/referenceMotions.ts

key-decisions:
  - "R8 recheck: no Python typed ReferenceMotion mirror/validator (reference-api/app.py is a passthrough) → 3-way lockstep, not 4-way"
  - "Parity RED-target gate scoped to the single helper-using test; SC#4/D-02/R3-1/env-flip/motion_id tests run unconditionally against the real library"
  - "node_modules symlinked from main repo for typecheck only (worktree has none), removed before commit — gitignored, never staged"

patterns-established:
  - "REFERENCE_V1_FORCE_CONFIG: recognizer=FallbackRecognizer, technique_profile=None, preflight_label_gate_passed=None, layer-2 off, fallback/null motion_id — recorded as a config object AND machine-checked"
  - "Reference backfill validator split: _validate_force_pattern_inference for forceDirectionPattern, generic flat validator for the other three dicts (R3-1)"

requirements-completed: [REF-01]

# Metrics
duration: 38min
completed: 2026-06-15
---

# Phase 14 Plan 01: Reference Backfill Verification + Contract Foundation Summary

**Wave-0 no-GPU foundation: a read-only 11-reference Firestore audit (A2), a pytest harness pinning reference-v1 pinned-config D-01 parity (RED target) + env-flip divergence + R3-1 force-pattern scoped-validator fixtures + SC#4 graceful + D-02 verdict, and a 3-way contract lockstep adding techniqueProfile/forceDirectionPattern/captureViews surfaced through normalize().**

## Performance

- **Duration:** ~38 min
- **Started:** 2026-06-15
- **Completed:** 2026-06-15
- **Tasks:** 3
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments
- A2 resolved-by-construction: `audit-reference-fields.mjs` reads all 11 references (5 originals + 6 later-added) and prints per-field presence + `completeRequiredSet` count, distinguishing skipComplete vs repairMissing for 14-02. Read-only (`.get()` only, zero `set(`), keys-not-values (T-14-01).
- Wave-0 pytest harness (`test_reference_backfill.py`) collects clean: 8 passed + 1 skipped (the parity RED target skips while the 14-02 helper does not yet exist). Verified that with `PHASE14_REQUIRE_BACKFILL_HELPER=1` the parity test FAILs (ModuleNotFoundError) rather than silently skipping (R4-1).
- D-01 reference-v1 pinned-config parity asserts the production call boundary (injected `pole_axis_measurement` + STORED `angles`, R6); R4-2 machine-checks `FallbackRecognizer().recognize(angles).motion_id is None`; R2 env-flip test proves `preflight_label_gate_passed=True` diverges (preflight_gate_pending warning present/absent); R3-1 fixtures prove the scoped `_validate_force_pattern_inference` accepts a valid `findings[].warnings:list[str]` and rejects nested/unknown-key payloads.
- 3-way contract lockstep (R8 = 3-way confirmed): `analysis.ts` ReferenceMotion + `docs/contract.md §3` + `referenceMotions.ts normalize()` all declare AND surface the new optional fields; `normalize()` no longer silently strips bodyNormalizationProfile/techniqueProfile/forceDirectionPattern/captureViews (R2-4). Typecheck clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: Read-only Firestore audit of all 11 references (A2)** - `640b79d` (feat)
2. **Task 2: Wave-0 backfill test harness** - `760ea0f` (test)
3. **Task 3: 3-way contract lockstep + normalize() surfacing** - `c5c3167` (feat)

_Task 2 is a TDD Wave-0 scaffold (RED target for 14-02) committed as a single `test` commit; the parity test is intentionally skip-or-fail-gated, the SC#4/D-02/R3-1/env-flip assertions are GREEN against the real library._

## Files Created/Modified
- `app/scripts/audit-reference-fields.mjs` - Read-only audit of 11 reference docs; per-field presence table + completeRequiredSet count (D-04 admin CLI, A2)
- `backend/tests/phase14/__init__.py` - Package marker
- `backend/tests/test_reference_backfill.py` - Wave-0 harness: REFERENCE_V1_FORCE_CONFIG parity (R4-1 env-gated, R4-2 motion_id=None, R6 call boundary), env-flip divergence, R3-1 scoped-validator fixtures, SC#4 graceful, D-02 stored-sufficient vs hybrid
- `app/src/types/analysis.ts` - ReferenceMotion gains techniqueProfile?/forceDirectionPattern?/captureViews? (optional/nullable)
- `docs/contract.md` - §3 ReferenceMotion table lists meanAngles + bodyNormalizationProfile + techniqueProfile + forceDirectionPattern + captureViews (Open-Q3 gap closed)
- `app/src/lib/referenceMotions.ts` - normalize() null-safely surfaces the four new/previously-stripped fields (R2-4)

## Decisions Made
- R8 recheck via `rg "ReferenceMotion|forceDirectionPattern|techniqueProfile|captureViews"` confirmed there is no Python typed ReferenceMotion mirror or validator (`reference-api/app.py` is a thin `firestore_admin.list_reference_motions()` passthrough). Therefore a 3-way lockstep (contract.md + analysis.ts + reuse of the Python `ForcePatternInference`/`TechniqueProfile` source shapes), not 4-way. No Python edit required.
- The R4-1 RED-target gate is scoped to the single test that uses the helper (`_load_helper()` at test entry) so SC#4/D-02/R3-1/env-flip/motion_id tests assert the production library unconditionally (no env-gated skip), per the plan.
- TS `techniqueProfile` modeled as an inline `{ name; category; jointExpectations }` shape (no standalone TS TechniqueProfile interface exists) mirroring the Python TechniqueProfile EXTEND surface that the backfill writes.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' acceptance criteria and the overall `<verification>` block pass.

## Issues Encountered
- The worktree has no `node_modules`, so `tsc` was unavailable. Resolved by symlinking the main repo's `node_modules` into `app/` for the typecheck run and removing the symlink before staging (gitignored, never committed). Typecheck is clean.

## User Setup Required
None - this plan installs no external packages (T-14-SC: accept, RESEARCH Package Legitimacy Audit N/A) and writes nothing to Firestore. The audit script requires the operator's ADC (`gcloud auth application-default login`, sunity3412@gmail.com) only when run; that is a 14-02/14-03 operational step.

## Next Phase Readiness
- 14-02 can now implement `backfill_reference_downstream.compute_reference_downstream(...)` against a stable RED target. Its verification command MUST run with `PHASE14_REQUIRE_BACKFILL_HELPER=1` so the D-01 parity + (helper-independent) env-flip context can no longer silently SKIP (R4-1).
- 14-02's `update_reference_downstream_data` + the JS seeder MUST apply `_validate_force_pattern_inference` to `forceDirectionPattern` and the generic flat validator to meanAngles/techniqueProfile/bodyNormalizationProfile (R3-1).
- 14-02/14-03 must cover all 11 references (`--motions` = 11-union; Pitfall 1), keep `versions/phase4_v1` active `joints3d`/`angles` read-only (Pitfall 4), and treat reference force fields as REFERENCE_V1_FORCE_CONFIG-produced when Phase 15 compares to students (R2/R4-2 — no selected-referenceMotionId force semantics).
- Open: the audit script's actual run output (which of the 6 later-added references lack bodyNormalizationProfile) is an operator run with ADC — not executed here (no ADC in CI/worktree); the script is verified syntactically and read-only.

## Self-Check: PASSED

Created files exist:
- FOUND: app/scripts/audit-reference-fields.mjs
- FOUND: backend/tests/phase14/__init__.py
- FOUND: backend/tests/test_reference_backfill.py
- FOUND (modified): app/src/types/analysis.ts, docs/contract.md, app/src/lib/referenceMotions.ts

Commits exist:
- FOUND: 640b79d (Task 1)
- FOUND: 760ea0f (Task 2)
- FOUND: c5c3167 (Task 3)

Verification:
- `python3 -m pytest tests/test_reference_backfill.py -q` → 8 passed, 1 skipped (parity RED target)
- `PHASE14_REQUIRE_BACKFILL_HELPER=1 pytest ...parity` → FAILS (ModuleNotFoundError, R4-1 strict)
- `node --check app/scripts/audit-reference-fields.mjs` → OK
- `npm run typecheck` → clean

---
*Phase: 14-reference-motion-registration*
*Completed: 2026-06-15*
