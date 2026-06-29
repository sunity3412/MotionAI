---
phase: 10
slug: injury-risk-flags
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-29
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `10-RESEARCH.md` §Validation Architecture. The headline gate is **elite (정은지) posture-alone → zero flags** (no-false-positive).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| **Config file** | `backend/tests/conftest.py` (no pytest.ini; phase dirs `backend/tests/phaseNN/`) |
| **Quick run command** | `python -m pytest backend/tests/phase10 -x -q` |
| **Full suite command** | `python -m pytest backend/tests -q` |
| **App static gate** | `cd app && npm run typecheck` (tsc --noEmit) — only app gate; covers the `SafetyFlag` 3-mirror addition |
| **Estimated runtime** | ~10 seconds (phase10 quick); full backend suite ~minutes |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest backend/tests/phase10 -x -q` (+ `cd app && npm run typecheck` for contract/UI tasks)
- **After every plan wave:** Run `python -m pytest backend/tests -q` (full backend — guards no regression in `force_signals`/`dimensions`/`assemble`)
- **Before `/gsd-verify-work`:** Full backend suite green + `npm run typecheck` green
- **Max feedback latency:** ~10 seconds (phase10 quick run)

---

## GREEN / xfail discipline (aligned with 10-01)

- **No-flag invariants are GREEN immediately at Wave 0** (the empty `compute_safety_flags` stub returns `[]`, which is the correct answer for every case whose answer is `[]`): elite-no-FP, determinism, posture-without-control, temporal-colocation (wrong-phase / different-window), flexed-knee, ambiguous-geometry, high-uncertainty, equal-asymmetry, no-reference, DTW timing-shift, Mode-3-level, level-without-control, spoof-experience.
- **Only positive future behavior is `xfail(strict=True)`** and flips GREEN in the wave that implements its rule: a flag SHOULD fire (trunk/joint/asymmetry/level positives), the validator SHOULD reject a nested list, and the D-05 uncertainty-channel regression (`test_d05_uncertainty_channel_not_inverted` — its "low-uncertainty CAN flag" half needs the 10-03 firing rule).
- **Never `xfail(strict)` a no-flag case** — it would XPASS against the stub and fail the suite.

---

## Per-Task Verification Map

| Req | Behavior | Threat Ref | Test Type | Automated Command | Wave | Status |
|-----|----------|------------|-----------|-------------------|------|--------|
| SAFE-01 / D-02 | **Elite no-FP:** 정은지 reference angles + all-`low` control-loss → **zero flags** | T-10-FP | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py::test_elite_posture_alone_no_flag -x` | W0 GREEN | ⬜ pending |
| SAFE-01 / D-02 | Posture met AND joint-local + phase-co-located control-loss → flag; posture + no/other-phase control-loss → no flag (`_phase_for_window` ≥50% overlap) | — | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py -x` | W0 GREEN (no-flag) / W1 flip (positive) | ⬜ pending |
| SAFE-01 / D-04 | DTW timing-shift: same extension in student+reference at shifted timing → no flag | T-10-FP | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py::test_trunk_timing_shifted_same_extension_no_flag -x` | W0 GREEN | ⬜ pending |
| D-05 | Cross-product: synthetic flexed knee → no flag; synthetic reverse-bend knee (low ch3 uncertainty) + control-loss → flag | — | unit | `pytest backend/tests/phase10/test_safety_flags_hyperextension.py -x` | W2 | ⬜ pending |
| D-05 channel | **uncertainty_proxy not inverted:** SAME reverse-bend coords + control-loss — LOW ch3 (≈0.05) CAN flag, HIGH ch3 (≈0.9) CANNOT flag (ch3 = uncertainty_proxy, pose_frame.py:326/app.py:452) | T-10-12 | unit | `pytest backend/tests/phase10/test_safety_flags_hyperextension.py::test_d05_uncertainty_channel_not_inverted -x` | W0 xfail-strict → W2 GREEN | ⬜ pending |
| D-05 real-elite | MULTIPLE pinned-source real-elite clips (ref-sideway-spin / ref-invert / ref-foxtop-split; mirrored + spin + both limbs) → zero hyperextension flags (real 3D keypoints via `to_coco17_array`, NOT `referenceKeypointReport` (2D) or `reference-angles.json` (angle-only)) | T-10-FP | unit | `pytest backend/tests/phase10/test_safety_flags_hyperextension.py -k "elite" -x` | W2 | ⬜ pending |
| D-05 schema | **Fixture schema gate:** every real-elite D-05 fixture is shape `(T,17,4)`, joint count == 17, order == `skeleton.KEYPOINT_NAMES`, ch3 ∈ [0,1] (NaN frames → 1.0) — blocks 2D / 8-keypoint / wrong-order data | T-10-FP | unit | `pytest backend/tests/phase10/test_safety_flags_hyperextension.py::test_d05_real_elite_fixture_schema -x` | W2 | ⬜ pending |
| D-03 | student_LR >> ref_LR (+pair-local control-loss) → asymmetry flag; equal asymmetry → none; timing-shifted → none (reference-anchored, DTW-aligned) | — | unit | `pytest backend/tests/phase10/test_safety_flags_asymmetry.py -x` | W0 GREEN (no-flag) / W3 flip (positive) | ⬜ pending |
| D-06 | Mode1 advanced ref × beginner experience (+control-loss) → level_mismatch; same in Mode3 → no flag (mode1-only); spoof experience → none | T-10-02 | unit | `pytest backend/tests/phase10/test_safety_flags_level.py -x` | W0 GREEN (no-flag) / W3 flip (positive) | ⬜ pending |
| SAFE-01 contract | `result["safetyFlags"]` scalar-only; `_validate_safety_flags` rejects nested list | T-10-01 | unit | `pytest backend/tests/phase10/test_safety_flags_contract.py -x` | W0 xfail-strict → W1 GREEN | ⬜ pending |
| SAFE-01 determinism | Same input → identical flags (LLM-free, D-01) | — | unit | `pytest backend/tests/phase10/test_safety_flags_firing_rule.py::test_deterministic -x` | W0 GREEN | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/phase10/__init__.py` — new phase test package (no Phase-10 tests exist yet)
- [ ] The 6 test files mapped above (`test_safety_flags_dataclass.py`, `_firing_rule.py`, `_hyperextension.py`, `_asymmetry.py`, `_level.py`, `_contract.py`) — collecting cleanly; no-flag invariants GREEN against the stub; positive behavior + `test_d05_uncertainty_channel_not_inverted` + the contract-validator test `xfail(strict=True)` until their wave lands.
- [ ] Shared fixture: 정은지 reference angle matrix + low control-loss `ForceSignalsReport` (the **elite-no-FP** fixture; `phase_boundaries` populated so `_phase_for_window` is exercisable). Reuse the success/fail pair dataset ([[jeongeunji-success-fail-pair-dataset]]) as a **known-answer regression set, NOT a fit target** ([[calibration-source-hard-gate]] — no 13-video curve-fit).
- [ ] Synthetic hyperextension fixtures: hand-built `(T,17,4)` arrays for flexed vs reverse-bent knee/elbow. **Channel 3 = `uncertainty_proxy`** (pose_frame.py:326,335 — 1.0 = undetected/worst, low = good): valid/high-quality → ch3 ≈ 0.05–0.1; missing/unreliable → ch3 ≈ 0.8–1.0. Include `uncertain_reverse_bent_4ch` (same reverse-bend coords, ch3 ≈ 0.9) as the channel-not-inverted partner.
- [ ] D-05 real-elite source provenance: real `(T,17,4)` 3D keypoints from pinned motion IDs (ref-sideway-spin / ref-invert / ref-foxtop-split). The ONLY valid `(T,17,4)` path is `to_coco17_array(pose_frames)` (pose_frame.py:325 → `(x,y,z,uncertainty_proxy)`, 17 keypoints in `skeleton.KEYPOINT_NAMES` order) — via a dedicated 3D extractor (`extract_reference_coco17_4ch.py` or a `--out-coco17-4ch` mode running `engine.estimate -> pose_frames -> to_coco17_array`) OR a checked-in compact `(T,17,4)` fixture generated by `to_coco17_array` WITH provenance. BOTH `referenceKeypointReport` (2D 8-keypoint overlay; `build_keypoint_report` / `extract_reference_keypoint_reports.py`, data=T*J*2, J=8 — assemble.py:781,924) AND `reference-angles.json` (angle-only, 8 joints) are FORBIDDEN as `(T,17,4)` 3D sources. Enforced by `test_d05_real_elite_fixture_schema`.
- No framework install needed (pytest present).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Amber warning section renders on result screen, distinct from white cards + neutral `AccuracyLimitBadge`, with possibility-only + expert-referral copy | SAFE-01 / D-08 | RN visual rendering not covered by typecheck; requires device/simulator | Run app, open a result with ≥1 active SafetyFlag, confirm amber section appears after score gauge, before "동작 비교"; confirm no "안전합니다" reassurance when no flags |

*App static gate (`npm run typecheck`) covers the contract type addition; visual render is the only manual item.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
