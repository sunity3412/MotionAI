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
