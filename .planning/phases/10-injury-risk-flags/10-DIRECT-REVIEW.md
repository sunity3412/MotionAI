# Phase 10 Direct Plan Review — Codex

**Reviewed:** 2026-06-29  
**Mode:** Direct self-contained review, no external AI  
**Plans reviewed:** `10-01-PLAN.md`, `10-02-PLAN.md`, `10-03-PLAN.md`, `10-04-PLAN.md`  
**Verdict:** Conditional hold. The architecture is strong, but one HIGH-risk contract mismatch must be fixed before execution.

## Overall Assessment

The plan set is mostly well designed:

- It preserves the D-01 boundary: deterministic `SafetyFlag` layer independent from LLM `injuryRisk`.
- It uses the right vertical slicing: contract/scaffold first, then compute-persist-render, then backend-only flag additions.
- The no-false-positive strategy is correctly centered on D-02: posture condition AND control-loss.
- Prior high-risk areas are mostly addressed in the current plan text: locality, DTW-aligned reference comparison, Mode-3 previous-angle plumbing, D-05 conservative geometry gates, scalar-only Firestore shape, and warning-only UI copy.

However, D-05 still contains one implementation-critical mismatch with the existing codebase: the fourth channel of `keypoints_4ch` is not confidence. It is `uncertainty_proxy`. If implemented literally from the current plan wording, the confidence gate can invert.

## Findings

### HIGH — D-05 treats `keypoints_4ch[:, :, 3]` as confidence, but the code stores uncertainty

Evidence:

- `10-03-PLAN.md` describes `keypoints_4ch` channel 3 as keypoint confidence and asks the gate to reject values below `MIN_KP_CONF`.
- `10-01-PLAN.md` also asks fixtures to use a "realistic ch3 confidence channel".
- Existing code says the opposite: `to_coco17_array()` writes `(x, y, z, uncertainty_proxy)`, defaulting missing keypoints to `1.0`.
- The pipeline has an explicit guard documenting that channel 3 is `uncertainty_proxy`, where `> 0.5` means low-confidence/refinement target.
- Later synthesis wiring converts it back with `confidence = 1.0 - kp_arr[:, :, 3]`.

Impact:

If an executor writes `if keypoints_4ch[..., 3] < MIN_KP_CONF: no_flag`, good keypoints with low uncertainty can be rejected, while missing or unreliable keypoints with uncertainty near `1.0` can pass. That directly threatens the D-05 safety behavior: either true reverse-bend detections disappear, or bad geometry is allowed into a high-stakes warning flag.

What I would do:

1. Revise all Phase 10 plan text to call channel 3 `uncertainty_proxy`, not confidence.
2. In `safety_flags.py`, derive:

   ```python
   uncertainty = keypoints_4ch[..., 3]
   confidence = np.clip(1.0 - uncertainty, 0.0, 1.0)
   ```

   or gate directly with `uncertainty <= MAX_KP_UNCERTAINTY`.
3. Make fixtures explicit:

   - high confidence / valid geometry: channel 3 around `0.05` or `0.1`
   - low confidence / missing: channel 3 around `0.8` or `1.0`

4. Add a lockstep regression test, for example `test_d05_uncertainty_channel_not_inverted`, that proves low uncertainty can flag and high uncertainty cannot flag even with the same reverse-bend coordinates and control-loss.
5. Add a grep/acceptance gate that forbids new D-05 code comments from saying `keypoints_4ch[:, :, 3]` is confidence.

### MEDIUM — Phase/window colocation is conceptually right but should be pinned to `ForceSignalsReport.phase_boundaries`

The current plans correctly require joint/region-local and temporally co-located control-loss. The remaining risk is executability: `dimensions._select_window()` returns frame indices, while `StabilityMetric.phase` is a phase label. The plan says to map the selected hold window to a phase identity, but does not pin the exact helper.

What I would do:

- Add `_phase_for_window(fsr.phase_boundaries, s, e) -> MotionPhase | None`.
- Use max-overlap between `[s, e)` and each `PhaseBoundary`; require a minimum overlap, e.g. 50% of the selected window.
- If no phase can be derived, localized flags should no-op rather than widening to any phase.
- Add tests for wrong-phase and boundary-overlap cases.

This is not a blocker if executed carefully, because `ForceSignalsReport` already carries `phase_boundaries`; it just needs to be made explicit in the plan.

### MEDIUM — "multiple real elite clips" is required but source paths/IDs are not fixed

`10-03-PLAN.md` requires a multi-clip real-elite regression set including mirrored orientation, spin-around-pole, and both limbs. That is the right requirement. The weak part is that it does not name which local files or motion IDs are canonical.

What I would do:

- Pin the fixture sources in the plan before execution.
- If using root reference artifacts, specify exact filenames and whether they contain 2D reports, 3D `joints3d`, or enough data to reconstruct `(T,17,4)`.
- If the available reference keypoint reports are only 2D, do not use them to claim D-05 3D cross-product validation. Use the source reference video plus the existing RTMW extraction path, or generate a checked-in compact 3D fixture from it with provenance.

Without this, an executor can accidentally satisfy the test requirement with synthetic-only data while believing the real-video risk has been covered.

### LOW/MEDIUM — Validation document is stale relative to the revised plans

`10-VALIDATION.md` still says `status: draft`, `nyquist_compliant: false`, `wave_0_complete: false`, and its Wave 0 checklist wording is not fully aligned with the current xfail discipline in `10-01-PLAN.md`.

What I would do:

- Update the validation document after the plan text is corrected.
- Make it explicitly say: no-flag invariants are GREEN immediately; only future positive behavior is `xfail(strict=True)`.
- Include the D-05 uncertainty-channel regression in the verification map.

## Verdict

I would not execute Phase 10 as-is because the D-05 channel semantics mismatch is high-risk and easy to implement incorrectly. After fixing that one issue and pinning the phase-window helper/source fixture IDs, the plan is otherwise solid enough to execute.


---

## Resolution — round 3 revision + Codex verification pass (2026-06-29)

**HIGH (D-05 uncertainty_proxy inversion): RESOLVED.** Plans now treat `keypoints_4ch[:,:,3]` as `uncertainty_proxy` everywhere; gate = `uncertainty <= MAX_KP_UNCERTAINTY` (high uncertainty rejected); `MIN_KP_CONF` forbidden by grep gate; fixtures valid≈0.05–0.1 / missing≈0.8–1.0; `test_d05_uncertainty_channel_not_inverted` (identical reverse-bend coords, low ch3 CAN flag / high ch3 CANNOT) added. Grounded in pose_frame.py:326,335 / app.py:452-466 / app.py:3709.

**MEDIUM-1 (_phase_for_window): RESOLVED.** Helper pinned to `ForceSignalsReport.phase_boundaries`, max-overlap ≥50%, returns None with no widening; D-03/D-04/D-05 reuse it.
**MEDIUM-2 (real-elite D-05 fixture sources): RESOLVED.** Pinned ref-sideway-spin / ref-invert / ref-foxtop-split, real (T,17,4) via RTMW or checked-in provenance; angle-only reference-angles.json forbidden for 3D claims.
**MEDIUM/LOW (VALIDATION refresh): RESOLVED.** GREEN/xfail discipline section + uncertainty-channel regression + real-elite-source rows added.

**Codex verification verdict: No HIGH-severity concerns remaining. Overall Risk: LOW.** No new HIGH introduced. Only residual is intentional (D-05 fails conservative when no clear flexion calibration frame → possible false-negative, which protects the elite no-false-positive core value).

Committed: 3d1b61d (plans), this resolution note follows.

---

## Direct Review Round 2 (2026-06-29)

### HIGH — D-05 real-elite 3D fixture source is still unsafe

`10-03-PLAN.md` now correctly says the D-05 real-elite regression MUST use actual 3D `(T,17,4)` keypoints and MUST NOT use angle-only `reference-angles.json`. That is the right requirement.

However, the plan still names `backend/scripts/extract_reference_keypoint_reports.py` / `referenceKeypointReport` as the path that can produce real `(T,17,4)` fixtures. That is not what the current code produces:

- `extract_reference_keypoint_reports.py` documents its output as `version`, `joints`, `frames`, `fps`, `data`, `confidence`, `reliability`, `axisData`, `axisMask`, `warnings`.
- `_process_motion()` runs RTMW, then immediately calls `build_keypoint_report(pose_frames, fps=target_fps)`.
- `build_keypoint_report()` consumes `frame.keypoints_2d`, writes 8 body keypoints, flattens `data` as x/y pairs, and validates `len(data) == T * J * 2` and `len(confidence) == T * J`.
- The actual `(T,17,4)` 3D source is `pose_frame.to_coco17_array()`, which writes COCO-17 `(x, y, z, uncertainty_proxy)`.

Impact:

An executor can follow the plan, use `referenceKeypointReport`, and believe D-05 has real 3D elite coverage while the test is actually backed by 2D overlay data or a converted/partial substitute. That weakens the most important safety invariant for D-05: no false positive on real elite motions under inversion, spin, and extreme split geometry.

What I would do:

1. Amend `10-03-PLAN.md` to remove `referenceKeypointReport` as a valid D-05 3D fixture artifact.
2. Add or require a dedicated extractor, e.g. `backend/scripts/extract_reference_coco17_4ch.py`, or an explicit `--out-coco17-4ch` mode.
3. That extractor should reuse the existing reference-video download/frame extraction/RTMW estimate path, but persist `to_coco17_array(pose_frames)` directly.
4. The checked-in fixture should record: source motion ID, fps, frame count, `skeleton.KEYPOINT_NAMES` order, coordinate space, extractor version/commit, extraction date, and the fact that channel 3 is `uncertainty_proxy`.
5. The D-05 real-elite test should assert shape `(T,17,4)`, joint count 17, and key order equals `skeleton.KEYPOINT_NAMES`. It should reject `KeypointReport`-style artifacts with `joints` length 8 or `data` length `T*J*2`.
6. Add an acceptance grep/fixture schema gate forbidding `referenceKeypointReport` / `reference-keypoint-reports` as satisfying D-05 3D coverage. The existing script can be cited only as a pattern for fetching/extracting reference frames, not as the output artifact.

### Resolved From Round 1

- D-05 channel semantics are now corrected: Phase 10 plans call channel 3 `uncertainty_proxy`, gate with `MAX_KP_UNCERTAINTY`, and require `test_d05_uncertainty_channel_not_inverted`.
- `_phase_for_window(fsr.phase_boundaries, s, e)` is now pinned with max-overlap semantics and no widening when phase cannot be derived.
- Validation text now reflects GREEN/strict-xfail discipline and includes the uncertainty-channel regression.

## Round 2 Verdict

I would still hold execution until the D-05 real-elite fixture-source language is corrected. The previous HIGH uncertainty-channel issue is resolved, but this remaining D-05 source issue is high-risk because it can create false confidence in the exact regression set meant to protect elite no-false-positive behavior.

---

## Resolution 2 — D-05 3D fixture source HIGH (round 4) + Codex verify (2026-06-29)

**HIGH (D-05 real-elite 3D fixture cited a 2D-output script): RESOLVED.** Verified: `extract_reference_keypoint_reports.py:113` → `build_keypoint_report` → 2D KeypointReport (`data`=T*J*2, J=8 + axisData; assemble.py:781,924), NOT (T,17,4). The real 3D path is `to_coco17_array` (pose_frame.py:325) → (x,y,z,uncertainty_proxy), 17 keypoints in `skeleton.KEYPOINT_NAMES` order.

Fix (10-03 + 10-01 + 10-VALIDATION):
- `referenceKeypointReport` (2D) AND `reference-angles.json` (angle-only) BOTH explicitly forbidden as D-05 3D sources.
- Required a dedicated 3D extractor (`extract_reference_coco17_4ch.py` / `--out-coco17-4ch` running `frames→engine.estimate→pose_frames→to_coco17_array`) OR a checked-in compact (T,17,4) fixture via `to_coco17_array` with conftest provenance. Pinned source IDs (ref-sideway-spin / ref-invert / ref-foxtop-split) preserved — only the extraction PATH corrected.
- `test_d05_real_elite_fixture_schema` added: asserts shape (T,17,4), 17 joints, `skeleton.KEYPOINT_NAMES` order, ch3=uncertainty_proxy ∈ [0,1] (NaN→1.0). Plus provenance grep gate forbidding both 2D sources.

**Codex verification verdict: No HIGH remaining. Overall Risk: LOW.** Prior fixes (uncertainty_proxy gate, _phase_for_window, xfail discipline) confirmed NOT regressed. Minor residual (compact-fixture provenance enforced by comment/acceptance rather than cryptographically tied to extractor output) — not HIGH; schema gate blocks the 2D/8-joint mistake.

Committed plans: fix in this session (10-01/10-03/10-VALIDATION).

---

## Direct Review Round 3 (2026-06-29)

### HIGH — D-05 helper contract cannot derive the hold window it must phase-localize

The previous HIGH items remain fixed: channel 3 is now `uncertainty_proxy`, and the real-elite 3D fixture source now points to `to_coco17_array` instead of the 2D `referenceKeypointReport` artifact.

The remaining high-risk issue is an internal contract mismatch inside D-05:

- `10-03-PLAN.md` says the D-05 firing function receives only `keypoints_4ch + fsr`.
- The implementation action then specifies `_joint_hyperextension_flag(keypoints_4ch, fsr) -> SafetyFlag | None`.
- The same paragraph requires the D-05 hold window `(s,e)` to come from `dimensions._select_window`.
- Existing code shows `dimensions._select_window(angles, profile=None)` needs `angles` and optional `profile` to return `(s,e)`.
- The locked public `compute_safety_flags(...)` signature already has `angles` and `profile`, so the data is available, but the D-05 private helper contract drops it.

Impact:

An executor following the plan literally has no valid way inside `_joint_hyperextension_flag(keypoints_4ch, fsr)` to call `dimensions._select_window(angles, profile)`. They will either hit an undefined variable, derive a different window from `keypoints_4ch`, use the whole clip, or skip phase mapping. Any of those reopens the D-02 false-positive path for D-05: reverse-bend posture can be paired with control-loss from the wrong phase/window, or a valid posture/control-loss pair can be silently no-oped. This is high-risk because D-05 is the phase's most safety-sensitive warning and its protection depends on joint-local + phase-co-located control-loss.

What I would do:

1. Change the D-05 helper contract to receive the same inputs it needs for windowing:

   ```python
   def _joint_hyperextension_flags(
       *,
       angles,
       keypoints_4ch,
       fsr,
       profile,
   ) -> list[SafetyFlag]:
       ...
   ```

   If the plan wants a singular helper, at minimum use `_joint_hyperextension_flag(angles, keypoints_4ch, fsr, profile)`.

2. Inside the helper, compute the phase exactly once via the pinned path:

   ```python
   _, (s, e) = dimensions._select_window(angles, profile)
   if np.asarray(keypoints_4ch).shape[0] != np.asarray(angles).shape[0]:
       return []  # fail-conservative; do not phase-map mismatched frames
   phase = _phase_for_window(fsr.phase_boundaries, s, e)
   if phase is None:
       return []
   ```

3. `compute_safety_flags(...)` should call the helper with `angles=angles` and `profile=profile`, then extend the returned list alongside the trunk/asymmetry/level flags.

4. Add explicit D-05 tests, not only grep gates:
   - `test_d05_wrong_phase_control_loss_no_flag`
   - `test_d05_missing_phase_boundaries_no_flag`
   - `test_d05_keypoints_angles_frame_mismatch_no_flag`
   - one positive test where reverse-bend and joint-local control-loss are in the same derived phase.

5. Update the acceptance criteria to grep for the helper consuming `angles`/`profile`, not just for `_phase_for_window`.

### MEDIUM — D-05 singular return type leaves multi-joint aggregation ambiguous

D-05 covers left/right knees and elbows, while the plan currently names `_joint_hyperextension_flag(...) -> SafetyFlag | None` and says to aggregate across left/right. It does not define whether multiple simultaneous joint findings become multiple scalar `SafetyFlag`s, a single "worst joint" flag, or one coarse `무릎·팔꿈치` card.

What I would do:

- Prefer `_joint_hyperextension_flags(...) -> list[SafetyFlag]`, one scalar-only flag per affected joint or per affected region.
- If product wants only one card, pin deterministic aggregation: choose highest severity, then stable tie-break order, and put the chosen side/joint in `posture_condition`.
- Add a test with both knee and elbow candidates so the aggregation behavior cannot drift.

## Round 3 Verdict

I would hold execution until the D-05 helper signature is corrected. The plan is now much stronger than round 1/2, but this input-contract mismatch is still high-risk because it undermines the exact phase-colocation gate that prevents elite false positives.

---

## Resolution 3 — D-05 helper contract HIGH (round 5) + Codex verify (2026-06-29)

**HIGH (D-05 helper dropped inputs needed for window/phase): RESOLVED.** Verified contradiction: helper was `_joint_hyperextension_flag(keypoints_4ch, fsr)` but had to call `dimensions._select_window(angles, profile)` (dimensions.py:292) → uncallable. Fixed: `_joint_hyperextension_flags(*, angles, keypoints_4ch, fsr, profile) -> list[SafetyFlag]`; window+phase computed ONCE; frame-mismatch (keypoints rows != angles rows) → []; phase None → []; `compute_safety_flags` threads angles/profile and `.extend()`s. Tests: wrong_phase / missing_phase_boundaries / frame_mismatch (no-flag, GREEN) + same_phase_positive + multi_joint_picks_worst_with_tiebreak. (10-02 trunk helper verified clean — already received angles/profile.)

**MEDIUM (multi-joint aggregation): RESOLVED.** Up to 4 candidates (L/R knee+elbow) → ONE consolidated `joint_hyperextension` card by highest severity, fixed tie-break (left_knee, right_knee, left_elbow, right_elbow), worst joint named in posture_condition — matches single UI copy-map key.

**Codex verification verdict: No HIGH remaining. Overall Risk: LOW.** Prior fixes (uncertainty_proxy, 3D fixture source = to_coco17_array only, _phase_for_window, xfail discipline) confirmed NOT regressed. Caveat: plan-contract review only — `safety_flags.py` / `backend/tests/phase10/` not yet implemented, so runtime not executed (expected — this is still planning).
