---
phase: 10-injury-risk-flags
plan: 03
subsystem: analysis
tags: [safety-flags, d-05, cross-product, hyperextension, numpy, fail-conservative, pod-deferred]

# Dependency graph
requires:
  - phase: 10-injury-risk-flags (10-02)
    provides: compute_safety_flags (locked sig) + _phase_for_window + _control_loss_for_joint + amber InjuryRiskSection copy-map
  - phase: 10-injury-risk-flags (10-01)
    provides: SafetyFlag dataclass + locked _joint_hyperextension_flags helper contract + two-segment fixtures + xfail-strict positives
  - phase: 08-force-signals
    provides: ForceSignalsReport / StabilityMetric / PhaseBoundary (control-loss + phase substrate)
provides:
  - "D-05 _joint_hyperextension_flags(*, angles, keypoints_4ch, fsr, profile) -> list[SafetyFlag] (window-once + frame-align guard + multi-joint worst-severity consolidation)"
  - "_hyperextension_candidate: deterministic frontal-axis body frame + min-angle flexion calibration + cross-product sign discriminator + uncertainty_proxy-correct per-branch fail-conservative gate scoped to used keypoints"
  - "extract_reference_coco17_4ch.py (pod RTMW -> to_coco17_array .npz extractor — single valid (T,17,4) 3D path)"
  - "sagittal-plane synthetic clip geometry (y-z bend) so cross-product sign is non-degenerate"
affects: [10-04 asymmetry+level_mismatch]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-product hinge-axis sign projected on a deterministic frontal axis (hip/shoulder) to distinguish flexion from reverse-bend — direction not magnitude"
    - "Min included-angle whole-clip calibration frame fixes the per-side flexion sign deterministically (cannot silently invert)"
    - "Per-branch fail-conservative gate SCOPED to the used-keypoint set (hinge triplet + frontal pair + longitudinal centers) — unused face/contralateral NaN ignored"
    - "uncertainty_proxy gate (uncertainty <= MAX, never MIN_KP_CONF) — channel-not-inverted"
    - "Multi-joint consolidation to ONE flag by (severity desc, fixed hinge order)"
    - "Pod-deferred real-elite regression: skipif-gated tests auto-activate when the (T,17,4) npz fixture lands"

key-files:
  created:
    - backend/scripts/extract_reference_coco17_4ch.py
  modified:
    - backend/shared/python/sunity_shared/analysis/safety_flags.py
    - backend/tests/phase10/conftest.py
    - backend/tests/phase10/test_safety_flags_hyperextension.py
    - .planning/phases/10-injury-risk-flags/deferred-items.md

key-decisions:
  - "Synthetic fixture geometry rewritten from x-y-plane bending to sagittal (y-z) bending — the inherited 10-01 fixtures bent the limb in the same plane as the hip-to-hip frontal axis, making dot(cross(u,w), frontal)==0 for ALL frames (cross-product method structurally undiscriminating). Verified numerically before implementation."
  - "Real-elite (T,17,4) regression POD-DEFERRED (authorized): 4 tests skipif-gated on real_elite_coco17_4ch.npz; extractor script written; schema gate forbids 2D/8-keypoint/wrong-order data from satisfying it."
  - "Floors [CITED] (knee>5 genu recurvatum / elbow>10 Beighton); severity bands 10/20; gate constants [ASSUMED conservative gate] — no 13-video curve-fit."

patterns-established:
  - "Numeric pre-verification of synthetic fixture geometry against the algorithm's discriminator before writing detector code"
  - "skipif(not artifact.exists()) pod-gating keeps the local suite fully GREEN while preserving an un-fakeable real-data regression"

requirements-completed: [SAFE-01]

# Metrics
duration: 55min
completed: 2026-06-30
---

# Phase 10 Plan 03: D-05 Joint-Hyperextension Cross-Product Detector Summary

**Deterministic knee/elbow reverse-bend (genu recurvatum / elbow hyperextension) detector that discriminates direction (not just magnitude) via the sign of the hinge cross-product projected onto a fixed frontal-axis body frame, min-angle flexion-calibrated, with an uncertainty_proxy-correct per-branch fail-conservative gate scoped to used keypoints, a callable angles+profile-threaded helper computing window/phase once, and a pinned multi-joint worst-severity consolidation — all synthetic + helper-contract + per-branch-gate tests GREEN, real-elite regression pod-deferred (skipif-gated, auto-activating).**

## Performance
- **Duration:** ~55 min
- **Completed:** 2026-06-30
- **Tasks:** 2
- **Files created/modified:** 5

## Accomplishments
- **D-05 detector** (`_hyperextension_candidate`): per-frame `u=A-V`, `w=C-V`, `included=acos(dot/|u||w|)`, `hyperextension_amount=max(0,180-included)`, `n=cross(u,w)`; deterministic frontal axis `unit(right_hip-left_hip)` (knee) / `unit(right_shoulder-left_shoulder)` (elbow); `signed_proj=dot(n,frontal)`; whole-clip `argmin(included)` calibration frame fixes `s_flex`; hyperextension := `sign(signed_proj)==-s_flex AND amount>floor`.
- **Callable helper** `_joint_hyperextension_flags(*, angles, keypoints_4ch, fsr, profile) -> list[SafetyFlag]`: frame-align guard, single `dimensions._select_window(angles, profile)` + `_phase_for_window` (phase P computed ONCE, reused per joint), per-joint candidates in fixed order, D-02 joint-local + phase-co-located control-loss AND-gate, multi-joint consolidation to ONE `joint_hyperextension` flag by (severity desc, then `left_knee,right_knee,left_elbow,right_elbow`). `.extend()`-ed into `compute_safety_flags` (trunk stays singular-append).
- **Per-branch fail-conservative gate** scoped to the used-keypoint set (hinge triplet + frontal pair + longitudinal centers): (a) high uncertainty_proxy `> MAX_KP_UNCERTAINTY`, (b) segment-length inconsistency, (c) single-frame spike (majority required), (d) degenerate frontal axis, (e) frontal collinear with longitudinal (spin/inversion), (f) collinear hinge segments, (g) no clear-flexion calibration frame, (h) NaN/inf in a used keypoint — NaN in an UNUSED face keypoint is ignored.
- **Channel-not-inverted**: gate reads ch3 as `uncertainty_proxy` (reject `uncertainty > 0.5`), no `MIN_KP_CONF`; identical-geometry low-uncertainty (flags) vs high-uncertainty (no flag) lockstep test GREEN.
- **Fixture geometry fix** (root-cause): rewrote synthetic clips to bend in the sagittal (y-z) plane so the cross-product is non-degenerate (old x-y geometry gave `signed_proj==0` for all frames — the cross-product method could never fire). Verified numerically first.
- **Tests**: un-xfailed the 5 positives + added left/right symmetry, elbow path, determinism, window-aggregation, scoped-NaN both sides, one negative per gate branch. `tests/phase10` = 45 passed, 4 skipped (pod-deferred), 2 xfailed (10-04), 0 failed, 0 xpassed.

## Task Commits
1. **Task 1: D-05 detector + sagittal fixtures + extractor (TDD)** — `95ffdd1` (feat)
2. **Task 2: robustness + per-branch gates + pod-deferred real-elite** — `bd8844c` (test)

## Files Created/Modified
- `backend/shared/python/sunity_shared/analysis/safety_flags.py` — D-05 constants (floors [CITED], gate constants [ASSUMED]), `_unit`, `_hyperextension_candidate`, `_joint_hyperextension_flags`, `compute_safety_flags` extend
- `backend/tests/phase10/conftest.py` — sagittal base coords + override dicts, right-side mirror, `_two_segment_clip` right params, per-branch ambiguity fixtures, right-knee control-loss report, pod-deferred real-elite fixture loader + provenance
- `backend/tests/phase10/test_safety_flags_hyperextension.py` — un-xfail 5 positives + robustness/per-branch/pod-deferred real-elite + schema-gate tests
- `backend/scripts/extract_reference_coco17_4ch.py` — pod RTMW -> `to_coco17_array` -> `.npz` extractor (created)
- `.planning/phases/10-injury-risk-flags/deferred-items.md` — pod-deferred entry (pinned IDs + exact command)

## Decisions Made
- Sagittal-plane fixture geometry (see key-decisions) — a correctness fix, not a reduction; numerically pre-verified.
- Real-elite regression pod-deferred per the orchestrator's authorized directive; the un-fakeable schema gate + provenance comment remain intact.
- Floors `[CITED]` external clinical literature; gate constants `[ASSUMED conservative gate]`; no 13-video curve-fit.

## Deviations from Plan
**1. [Authorized deferral] Real-elite (T,17,4) regression pod-deferred**
- **Found during:** Task 1/2 (no RunPod GPU available this run, per orchestrator directive)
- **Issue:** The only valid `(T,17,4)` 3D source is `to_coco17_array(pose_frames)` which needs RTMW pose estimation on GPU; no checked-in source exists.
- **Resolution:** Implemented the FULL algorithm + all synthetic/helper-contract/per-branch tests GREEN; added the 4 real-elite tests + schema gate + provenance comment but `skipif`-gated on `real_elite_coco17_4ch.npz`; wrote the extractor script + documented the exact pod command in SUMMARY + deferred-items.md. Auto-activates when the npz lands. This is the orchestrator's explicitly authorized deviation from the "real-elite test GREEN" acceptance line; all other acceptance lines fully met.

**2. [Rule 1 - Bug] Inherited fixture geometry was degenerate for the cross-product method**
- **Found during:** Task 1 (pre-implementation numeric verification)
- **Issue:** 10-01's two-segment fixtures bent the limb in the x-y plane while the hip-to-hip frontal axis is also along x → `dot(cross(u,w), frontal)==0` for every frame → the detector could never fire (positive tests would be unreachable).
- **Fix:** Rewrote base coords + override dicts so the hinge bends in the sagittal (y-z) plane, frontal axis genuinely perpendicular to the bend plane. Verified `signed_proj` flips sign between calibration (-0.16) and reverse-bend (+0.06) before writing detector code.
- **Files modified:** `backend/tests/phase10/conftest.py`
- **Commit:** `95ffdd1`

## Pod-deferred
- **Artifact:** `backend/tests/phase10/fixtures/real_elite_coco17_4ch.npz` (not yet generated)
- **Pinned source motion IDs:** `ref-sideway-spin` (spin-around-pole), `ref-invert` (inverted/mirrored), `ref-foxtop-split` (extreme split, both limbs)
- **Extractor command (pod):**
  ```bash
  cd backend && source pod.env && export PYTHONPATH=$PWD:$PWD/shared/python
  python scripts/extract_reference_coco17_4ch.py \
      --motions ref-sideway-spin ref-invert ref-foxtop-split \
      --out tests/phase10/fixtures/real_elite_coco17_4ch.npz
  ```
- **Skipif-gated tests (currently SKIPPED, auto-activate on artifact):** `test_real_elite_clips_no_hyperextension`, `test_real_elite_mirrored_no_flag`, `test_real_elite_spin_no_flag`, `test_d05_real_elite_fixture_schema`.

## Issues Encountered
- Full `backend/tests` run: 54 failed / 2004 passed / 23 skipped / 2 xfailed / 11 collection errors. The 54 failures + 11 collection errors are **pre-existing and out of scope** (phase06/phase08 Gemini/vision-veto env-dependent integration + R&D spike ImportErrors — identical class documented in 10-01/10-02 deferred-items.md). My changes add +16 passes (new D-05 tests) and ZERO new failures; no phase10/safety_flags failures.

## User Setup Required
None this run. A later pod run is required to generate the real-elite fixture (command above) — not blocking.

## Known Stubs
None — the D-05 detector is fully wired into `compute_safety_flags`; the only deferred item is the real-elite regression fixture (documented, pod-gated, auto-activating).

## Next Phase Readiness
- 10-04 (asymmetry + level_mismatch) can append to `compute_safety_flags`; its 2 xfail-strict positives remain. `_control_loss_phase_level` reserved for D-06 whole-body overreach.
- D-05 flag auto-renders via the 10-02 amber `InjuryRiskSection` copy-map (zero UI change).
- No blockers.

## Self-Check: PASSED

---
*Phase: 10-injury-risk-flags*
*Completed: 2026-06-30*
