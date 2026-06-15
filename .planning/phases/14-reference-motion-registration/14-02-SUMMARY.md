---
phase: 14-reference-motion-registration
plan: 02
subsystem: reference-backfill
tags: [pod-orchestrator, rtmw, firestore, force-pattern, body-normalization, reference-motion, backfill, seeder, capture-guide]

# Dependency graph
requires:
  - phase: 14-reference-motion-registration
    plan: 01
    provides: REFERENCE_V1_FORCE_CONFIG parity RED target (test_reference_backfill.py) + 3-way contract lockstep + scoped validator fixtures
  - phase: 06-body-normalization
    provides: measure_body_profile + seed-reference-body-profile.mjs pattern + update_reference_body_data helper
  - phase: 09-force-direction-pattern
    provides: infer_force_direction_pattern + _validate_force_pattern_inference scoped validator
  - phase: 04-ux-occlusion-confidence
    provides: all 11 references RTMW phase4_v1 active (angles/anglesJointKeys/anglesFrames stored)
provides:
  - "Pod-run backfill orchestrator (compute_reference_downstream) — SAME sunity_shared fns under REFERENCE_V1_FORCE_CONFIG, makes the 14-01 D-01 parity test GREEN under PHASE14_REQUIRE_BACKFILL_HELPER=1"
  - "--check-firestore all-11 completeness gate (credential + activeVersion/angles/jointKeys/frames + frame-count) with no S3/RTMW (R2-3/R3-2)"
  - "firestore_admin.update_reference_downstream_data ADD-only merge helper (scoped force-pattern validator + generic flat validator, R3-1)"
  - "seed-reference-downstream.mjs — reads only seedPayload (R2-5), scoped+generic validation, complete/repair/overwrite split (R3), 11-id all-or-nothing (R5)"
  - "docs/reference-capture-guide.md — SC#3 촬영 조건/앵글/시점 수 + single-view baseline + R4-2 force-config caveat"
affects: [14-03, phase-15-mode1-comparison]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pod orchestrator split fixture: seedPayload (seedable) vs diagnostics (hashes/deltas/provenance, never seeded) (R2-5)"
    - "stored-vs-rerun angle integrity gate (EPSILON_DEG=1.0) — re-run angles are validation-only, never the source of meanAngles/EXTEND (R1)"
    - "conftest exposes backend/scripts for bare-import of orchestrator helpers (R4-1 strict import)"

key-files:
  created:
    - backend/scripts/backfill_reference_downstream.py
    - app/scripts/seed-reference-downstream.mjs
    - docs/reference-capture-guide.md
  modified:
    - backend/shared/python/sunity_shared/firestore_admin.py
    - backend/tests/conftest.py

key-decisions:
  - "Added backend/scripts to tests/conftest sys.path so the 14-01 bare `import backfill_reference_downstream` resolves under PHASE14_REQUIRE_BACKFILL_HELPER=1 (the parity RED target imports the orchestrator directly)"
  - "compute_reference_downstream returns a dataclass exposing the raw ForceSignalsReport (.force_signals_report) so the parity test compares the same object the direct-call reference produces"
  - "force fields resolve motion_id from getattr(profile,'motion_id',None) (FallbackRecognizer => None) for both compute_force_signals and infer_force_direction_pattern — known-reference contact/boost intentionally does NOT fire (R4-2)"

patterns-established:
  - "Reference downstream backfill = STORED phase4_v1 angles for meanAngles/EXTEND (R1) + ONE RTMW re-inference for body/force live frames (D-02 hybrid), gated by a stored-vs-rerun angle integrity check"

requirements-completed: [REF-01]

# Metrics
duration: 33min
completed: 2026-06-15
---

# Phase 14 Plan 02: Reference Downstream Backfill + Seed Summary

**A Pod-run orchestrator computes the 4 reference downstream fields (meanAngles + techniqueProfile from STORED phase4_v1 angles, bodyNormalizationProfile + forceDirectionPattern from ONE RTMW re-inference) via the exact `_process` functions under REFERENCE_V1_FORCE_CONFIG (motion_id=None), gated by a `--check-firestore` all-11 completeness check and a stored-vs-rerun angle integrity gate; an ADD-only firestore_admin helper + a seedPayload-only Node seeder (scoped force-pattern validation, 11-id all-or-nothing) write the fields without touching active pose; and an SC#3 capture guide ships — turning the 14-01 D-01 parity RED test GREEN under `PHASE14_REQUIRE_BACKFILL_HELPER=1` with no skips.**

## Performance

- **Duration:** ~33 min
- **Started:** 2026-06-15
- **Completed:** 2026-06-15
- **Tasks:** 3
- **Files:** 5 (3 created, 2 modified)

## Accomplishments

- **Task 1 — orchestrator (`backfill_reference_downstream.py`):** `compute_reference_downstream(pose_frames, *, pole_axis_measurement, angles, fps=9.0, motion_id=None, mode_context, force_config=REFERENCE_V1_FORCE_CONFIG)` derives `meanAngles` (nanmean) and `techniqueProfile` (FallbackRecognizer EXTEND) from the `angles` argument (STORED phase4_v1, R1), and `bodyNormalizationProfile` + `forceDirectionPattern` from the live `pose_frames` (D-02 hybrid). Force fields pin `preflight_label_gate_passed=None`, `technique_profile=None`, `motion_id=None` (R2/R4-2). The `--check-firestore` mode reads all requested docs via `auth._ensure_firebase()` (FIREBASE_SA_JSON/PATH/PARAM — no hand-rolled `credentials.Certificate`) and verifies `activeVersion`/`angles`/`anglesJointKeys`/`anglesFrames` + frame-count sanity, exiting before any S3/RTMW (R2-3/R3-2). A stored-vs-rerun angle integrity gate (`maxAngleDelta > 1.0` => abort) guards version integrity (R1). The emitted JSON is split into `seedPayload` (5 fields) and `diagnostics` (hashes/deltas/force-config provenance, never seeded — R2-5). All 11 motion IDs, all-or-nothing exit (R5).
- **Task 2 — merge helper + seeder:** `firestore_admin.update_reference_downstream_data(...)` ADD-only merges the 4 fields + `captureViews` with per-field `*UpdatedAt`, validating `forceDirectionPattern` via the scoped `_validate_force_pattern_inference` and the other 3 dicts via the generic `_validate_flat_dict_no_nested_array` (R3-1); the payload never contains joints3d/angles/activeVersion. `seed-reference-downstream.mjs` reads ONLY `seedPayload` (R2-5), applies a JS scoped forceDirectionPattern validator mirroring the Python rules (accepts `findings[].warnings:string[]`, rejects nested/unknown), keeps generic nested-array rejection for the flat dicts, separates skippedComplete/repairMissing/forceOverwrite (R3), enforces 11-id all-or-nothing on real-runs (R5), dry-runs ADC-safe, and verifies via `--verify`.
- **Task 3 — capture guide (`docs/reference-capture-guide.md`):** documents 시점 수 / 앵글 / 촬영 조건, the single-view v1 baseline + low-confidence flag policy (D-03/SC#4), the registration procedure, and the motion_id=None reference force-config caveat for Phase 15 (R4-2).

## Task Commits

Each task was committed atomically:

1. **Task 1: Backfill orchestrator + check-firestore gate (D-01 parity GREEN)** - `ab6b265` (feat)
2. **Task 2: Downstream merge helper + ADD-only seeder (R3-1 scoped validator)** - `635134a` (feat)
3. **Task 3: Multi-angle reference capture guide (SC#3)** - `ba3ff08` (docs)

## Files Created/Modified

- `backend/scripts/backfill_reference_downstream.py` (created) - Pod orchestrator: --check-firestore gate → STORED angles read → S3 download → RTMW re-inference → 4-field compute under REFERENCE_V1_FORCE_CONFIG → angle integrity gate → split seedPayload/diagnostics JSON
- `app/scripts/seed-reference-downstream.mjs` (created) - ADD-only seeder reading only seedPayload, scoped forceDirectionPattern + generic flat validation, complete/repair/overwrite split, 11-id all-or-nothing, dry-run/verify
- `docs/reference-capture-guide.md` (created) - SC#3 capture guide (촬영 조건·앵글·시점 수) + single-view baseline + R4-2 caveat
- `backend/shared/python/sunity_shared/firestore_admin.py` (modified) - added `update_reference_downstream_data` ADD-only merge helper + `_REF_TECHNIQUE_PROFILE_REQUIRED`
- `backend/tests/conftest.py` (modified) - added `backend/scripts` to sys.path so the 14-01 parity test's bare orchestrator import resolves (R4-1)

## Deviations from Plan

**1. [Rule 3 - Blocking] Added `backend/scripts` to `tests/conftest.py` sys.path**
- **Found during:** Task 1
- **Issue:** The 14-01 parity test does a bare `from backfill_reference_downstream import compute_reference_downstream`, but `tests/conftest.py` only injected `shared/python` — so under `PHASE14_REQUIRE_BACKFILL_HELPER=1` the import would raise `ModuleNotFoundError` even with the helper present, blocking the verification command from passing.
- **Fix:** Added a second `sys.path.insert` for `backend/scripts` in `tests/conftest.py` (the plan's verification command explicitly runs `cd backend && pytest`, which loads this conftest).
- **Files modified:** backend/tests/conftest.py
- **Commit:** ab6b265

## Issues Encountered

- The worktree venv lacks several optional ML/cloud deps (`google`, `mediapipe`, `rtmlib`, `imageio`), so `pytest tests/` collection shows pre-existing import errors and dep-gated failures in unrelated modules (gemini/spike/sweep/pole/phase06-pipeline-integration). These are **out of scope** (SCOPE BOUNDARY — pre-existing, not caused by this plan) and logged to `deferred-items.md`. The directly-relevant suites pass: `test_reference_backfill.py` 9/9 (no skips) and `tests/phase09` (force_pattern) 135/135. `firestore_admin` imports cleanly.
- `npm run typecheck` (app) is not applicable to this plan — Task 2/3 added only `.mjs`/`.py`/`.md` files and modified no `.ts` files; the worktree also has no `node_modules`. `node --check` on the new seeder passes.

## Known Stubs

None — no UI/data stubs. The orchestrator and seeder are operator-run CLIs whose live data path (S3/RTMW/Firestore writes) is a 14-03 Pod operational step; that is by design (REF-01 backfill is split Wave-0 harness → Wave-2 compute/seed → Wave-3 Pod run), not an unwired stub.

## Threat Flags

None — no new trust boundaries beyond the plan's threat_model (Pod→S3, Pod→Firestore read, fixture→seeder, seeder→Firestore). All assigned `mitigate` dispositions are implemented: keys-not-values logging (T-14-04), no active-pose writes (T-14-05/07), seedPayload-only + scoped validation + 11-id gate (T-14-06/18), --check-firestore fail-fast (T-14-15), no skipped parity (T-14-19).

## Self-Check: PASSED

Created files exist:
- FOUND: backend/scripts/backfill_reference_downstream.py
- FOUND: app/scripts/seed-reference-downstream.mjs
- FOUND: docs/reference-capture-guide.md
- FOUND (modified): backend/shared/python/sunity_shared/firestore_admin.py, backend/tests/conftest.py

Commits exist:
- FOUND: ab6b265 (Task 1)
- FOUND: 635134a (Task 2)
- FOUND: ba3ff08 (Task 3)

Verification:
- `PHASE14_REQUIRE_BACKFILL_HELPER=1 pytest tests/test_reference_backfill.py -x -q` → 9 passed, 0 skipped (D-01 parity GREEN, R4-1 strict)
- `backfill_reference_downstream.py --help` → exit 0 (lazy import on Mac)
- `grep check-firestore / seedPayload` → present both sides
- `node --check app/scripts/seed-reference-downstream.mjs` → OK
- JS scoped validator: valid forceDirectionPattern accepted; nested findings[].warnings + unknown finding key + meanAngles nested-array all rejected
- Python helper: VALID accepted with ADD-only payload (no joints3d/angles/activeVersion); nested warning rejected

---
*Phase: 14-reference-motion-registration*
*Completed: 2026-06-15*
