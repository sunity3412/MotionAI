---
phase: 08-jerk-jitter
reviewer: Codex
date: 2026-06-09
scope: architecture-and-plan-review
status: high-risk-revise-before-execution
smpl_policy: excluded
---

# Phase 8 Direct Review

## Executive Verdict

Phase 8의 방향성 자체는 맞다. Phase 9가 "힘 방향 패턴"을 추론하려면 중심축 이탈, 흔들림, 접촉 안정성, phase boundary가 필요하다. 다만 현재 08-01/08-02/08-03 계획을 그대로 실행하면 "측정값은 나오지만 물리적으로 틀린 신호"가 downstream으로 흘러갈 가능성이 크다.

내 판정은 **as-is 실행 보류**다. 특히 아래 3개는 구현 전에 먼저 고쳐야 한다.

1. 현재 `PoleAxis`에는 폴의 위치가 없고 방향만 있다. 그런데 Phase 8은 "폴축까지 거리"를 핵심 metric으로 삼는다.
2. `BodyNormalizationProfile.torsoScale`은 실제 좌표계 길이가 아니라 torso-relative 비율이다. 거리 정규화 denominator로 쓰면 안 된다.
3. `ContactStabilityMetric.estimatedStable`은 현재 입력 신호만으로는 과신하기 쉽다. 특히 inner thigh/hip 접촉은 COCO-17 keypoint 하나로 판정할 수 없다.

저라면 08-01 전에 짧은 **08-00 coordinate/contact correction plan**을 추가한다. 먼저 pole line 위치와 body scale을 정의하고, contact는 boolean 안정 판정이 아니라 `nearPoleRatio`, `distanceToPole`, `lostNearPoleAtMs`, `confidence` 중심의 신호로 낮춰서 시작한다.

## Reviewed Inputs

- `.planning/phases/08-jerk-jitter/08-CONTEXT.md`
- `.planning/phases/08-jerk-jitter/08-RESEARCH.md`
- `.planning/phases/08-jerk-jitter/08-01-PLAN.md`
- `.planning/phases/08-jerk-jitter/08-02-PLAN.md`
- `.planning/phases/08-jerk-jitter/08-03-PLAN.md`
- `.planning/phases/08-jerk-jitter/08-VALIDATION.md`
- `backend/shared/python/sunity_shared/analysis/pose_frame.py`
- `backend/shared/python/sunity_shared/analysis/pole/detector.py`
- `backend/shared/python/sunity_shared/analysis/pole/aligner.py`
- `backend/shared/python/sunity_shared/analysis/body_normalization.py`
- `backend/functions/pipeline/app.py`
- `backend/shared/python/sunity_shared/firestore_admin.py`
- `app/src/types/analysis.ts`

Current state: `backend/shared/python/sunity_shared/analysis/force_signals.py` does not exist yet, and `08-VALIDATION.md` is still `status: draft`, `nyquist_compliant: false`.

## High-Risk Findings

### R1. Pole distance is not physically defined yet

Severity: **BLOCKER**

Phase 8 depends on "pelvis/chest/contact point to pole axis distance". Current code does not provide enough information for that measurement.

Local evidence:

- `PoseFrame.PoleAxis` has `axis_vector`, `confidence_level`, `source`, `frame_index`, but no line origin, base point, image endpoints, or 3D pole centerline. See `backend/shared/python/sunity_shared/analysis/pose_frame.py:166`.
- `pole/aligner.py` rotates keypoints so the pole direction aligns to Z, but it does not translate the coordinate system to the pole centerline. See `backend/shared/python/sunity_shared/analysis/pole/aligner.py:29` and `:63`.
- `pole/detector.py` explicitly documents that the pole axis is detected in image 2D while world landmarks use a different origin. See `backend/shared/python/sunity_shared/analysis/pole/detector.py:17` and `:123`.

Risk:

If `distance_to_pole_axis = sqrt(x^2 + y^2)` or similar is implemented on `keypoints_3d_pole_aligned`, the result may be distance to an arbitrary rotated world origin, not distance to the actual pole. This would poison both `AxisDeviationMetric` and `ContactStabilityMetric`.

Recommendation:

Add a pole-position contract before implementing metrics:

- Option A, minimal: add `PoleLine2D` with normalized image line endpoints and compute proximity in image plane, normalized by observed torso pixel length.
- Option B, better: add `PoleCoordinateFrame` / `PoleAxisMeasurement` with `axis_vector`, `point_on_axis`, and `source_coordinate_space`, then translate + rotate keypoints into pole-centered coordinates.
- If 3D point-on-axis is not reliable from monocular video, do not pretend it is 3D. Store `axisDistance2DNorm` and mark `coordinateSpace="image_2d"`.

If I were implementing this, I would start with image-plane pole line distance and confidence, not pseudo-3D pole distance.

### R2. `BodyNormalizationProfile.torsoScale` is the wrong distance denominator

Severity: **HIGH**

Phase 8 context says distance unit = body-scale normalization using `BodyNormalizationProfile.torsoScale`. That conflicts with the actual contract.

Local evidence:

- `BodyNormalizationProfile` documents scale fields as torso-relative proportions, not absolute lengths. See `backend/shared/python/sunity_shared/analysis/body_normalization.py:65`.
- Pipeline already has a body-length extraction pattern via `_extract_target_torso_px()`, and `measure_body_profile()` computes per-frame segment lengths before converting them into ratios.

Risk:

`torsoScale` is often near 1.0 by design. Using it as "meters/pixels/world units" makes `pelvisDistance > 0.30 * torsoScale` arbitrary. This will not generalize across camera distance, crop, lifter scale, or coordinate backend.

Recommendation:

Introduce a separate helper:

```python
def median_torso_length(pose_frames: list[PoseFrame], *, space: Literal["image_2d", "aligned_3d"]) -> float | None:
    ...
```

Use that length as the denominator for axis/contact distances. Keep `BodyNormalizationProfile` for body proportion hints only.

### R3. Contact stability is over-specified for the available signal

Severity: **HIGH**

The plan wants 12 contact points and `estimatedStable=true/false/null`. Some contact points are not direct keypoints in the current scoring contract.

Problems:

- `left_inner_thigh` / `right_inner_thigh` are not COCO-17 keypoints. They require segment-to-pole distance between hip and knee, not point distance.
- `hip` contact is also a segment/region contact, not a single point.
- Hands/ankles can be near the pole in projection without real contact.
- True contact is often occluded by body/pole overlap. Proximity alone can mark false positives.

Recommendation:

Change v1 schema from a confident contact boolean to a measurable signal:

- `contactPoint`
- `measurementKind: "keypoint" | "segment" | "region_proxy"`
- `distanceToPoleNorm`
- `nearPoleRatio`
- `lostNearPoleAtMs`
- `estimatedStable: bool | null`
- `confidence`
- `warnings`

For inner thigh, compute segment-to-pole distance against `left_hip -> left_knee` and `right_hip -> right_knee`. For hand/ankle, keypoint distance is acceptable. For hip, start with region proxy and lower confidence.

If I were doing it, I would not let Phase 9 consume contact as a hard truth. I would pass "near-pole evidence" and let Phase 9 phrase causes as possibilities.

### R4. Five-phase segmentation is valid as a goal, but the current Layer 1 heuristic is not validated enough

Severity: **HIGH**

The 5 phases are domain-correct: `entry`, `lock`, `transition`, `final_shape`, `hold`. The risky part is assuming a universal heuristic can reliably split all pole videos with foot vertical position, hand-pole distance, and keypoint velocity.

Likely failure cases:

- already-airborne clips that start after entry
- floorwork / low-flow transitions
- spins where velocity stays high into the final shape
- side-view vs front-view differences
- occluded hands during lock
- unsupported motions with no clean "ground -> grab -> lift" pattern

Recommendation:

Keep 5 phases in the contract, but make v1 conservative:

- Always emit `phaseBoundaries`, but allow `source="heuristic_fallback"` and low confidence.
- Treat `hold` and `final_shape` as the most important production phases.
- Add a required pre-flight label set before execution: 5 videos x 5 boundaries = 25 timestamps minimum; better 10 videos x 5 = 50.
- Do not use Layer 2 Gemini as a correctness source until the timestamp sanity check passes.

I would insert a gate: "Layer 1 boundary median absolute error <= 300ms on labeled clips, otherwise Phase 9 cannot use phase-specific force patterns."

### R5. Jerk/jitter design will be fragile unless raw vs smoothed signals are separated

Severity: **HIGH**

Pipeline already calls `temporal_fill()` before the angles reach scoring. See `backend/functions/pipeline/app.py:431`.

Phase 8 also says `compute_force_signals()` will call `temporal_fill()` before metric calculation. That risks double smoothing. For jitter/jerk, this is not a harmless detail: third derivatives are highly sensitive to smoothing, frame rate, and noise.

Additional issue:

The plan uses examples like `np.diff(angles, n=3, axis=0)` and thresholds like deg/frame^3. This is frame-rate dependent. If extraction FPS changes, severity changes with no movement change.

Recommendation:

- Pass both `raw_angles` and `filled_angles` if Phase 8 needs derivatives.
- Call `temporal_fill()` once, at the pipeline input boundary.
- Compute derivatives with `dt = 1 / fps`, then report `deg/s`, `deg/s^2`, `deg/s^3` or explicitly call it frame-normalized.
- For v1, keep `jerkScore` diagnostic and do not use it as a high-severity trigger until sweep calibration passes.
- Add tests where the same movement sampled at 9fps and 18fps produces comparable normalized jerk.

### R6. Gemini Layer 2 duplicates an existing expensive path

Severity: **MEDIUM-HIGH**

Pipeline already runs the recognizer with `recognizer.recognize(angles, frames=local_video_path)`. Phase 8 plans another Gemini moment extraction call.

Risk:

- double video upload / double multimodal latency
- inconsistent timestamps between recognizer and force signal layer
- model availability drift
- production cost drift

Current model note:

Local code currently has `DEFAULT_GEMINI_MODEL = "gemini-3.1-pro-preview"`, while the official Gemini model docs currently list `gemini-3-pro-preview`, `gemini-2.5-pro`, and `gemini-2.5-flash` families. This should be validated with `models.list` before production wiring, not hardcoded in Phase 8.

Recommendation:

- Prefer reusing Phase 5 recognized `motion_id` and timestamps if available.
- If Phase 5 does not expose timestamps, extend `TechniqueProfile` or recognizer result once.
- Keep Phase 8 Gemini Layer 2 default-off and use it as a reviewer/corrector, not as the only boundary source.
- Use model name from config/env and validate at startup.

### R7. Firestore schema needs one flatness decision before coding

Severity: **MEDIUM**

The current validator rejects nested lists inside `list[dict]`. Phase 8 plans to allow `warnings: list[str]` inside each metric dict.

This may be technically serializable, but it weakens the local `firestore-nested-array-flat` invariant and makes future schema drift easier.

Recommendation:

Pick one:

- Conservative: per-metric `warningCode: string | null`, report-level `warnings: string[]`.
- Flexible: allow `list[scalar]` in metric dicts, but add explicit tests against Firestore serialization and keep `list[dict]` / `list[list]` rejected.

If this is only for warning codes, I would choose the conservative version.

### R8. Wave 0 fixture strategy is too heavy and may encode fake certainty

Severity: **MEDIUM**

The plan creates many synthetic JSON fixtures before the measurement contract is settled. That can lock in assumptions that are wrong: pole origin, torso scale, contact point definitions, phase timings.

Recommendation:

- Use programmatic fixture factories for unit tests.
- Add 1-2 real-video smoke fixtures or saved pose traces for contract-level validation.
- Delay large synthetic fixture JSON until after R1/R2 are fixed.

## What I Would Do Instead

I would not start with 08-01 as written. I would add this small correction slice first.

### Proposed 08-00: Coordinate and Contact Foundation

Files likely touched:

- `backend/shared/python/sunity_shared/analysis/pose_frame.py`
- `backend/shared/python/sunity_shared/analysis/pole/detector.py`
- `backend/shared/python/sunity_shared/analysis/pole/aligner.py`
- `docs/contract.md`
- `app/src/types/analysis.ts`
- `backend/tests/phase08/test_pole_distance_contract.py`

Tasks:

1. Define pole position, not only direction.
   - Add `PoleLine2D` or `PoleAxisMeasurement`.
   - Store image-space line endpoints or a point-on-axis.
   - Mark coordinate space explicitly.

2. Define distance scale.
   - Add `median_torso_length()` helper.
   - Use observed pose length, not `BodyNormalizationProfile.torsoScale`.

3. Define contact measurement primitives.
   - `keypoint_to_pole_distance_norm`
   - `segment_to_pole_distance_norm`
   - `near_pole_ratio`
   - `first_loss_ms`

4. Make Phase 8 output confidence-first.
   - Contact can be `estimatedStable=null` unless the signal is strong.
   - Phase 9 must treat low-confidence contact as a hypothesis input.

After that, I would execute a revised 08-01/02/03.

### Revised Execution Shape

08-01 revised:

- schema lockstep
- `PoleLine2D` / `PoleAxisMeasurement`
- `ForceSignalsReport` with coordinate-space fields
- smaller fixture factory

08-02 revised:

- `compute_axis_deviation()` uses explicit pole distance contract
- `compute_contact_stability()` uses keypoint/segment/region proxy measurement
- `compute_stability_metrics()` uses one smoothing pass and FPS-normalized derivatives
- all metrics emit confidence and warnings without hard overclaim

08-03 revised:

- pipeline wiring after body comparison is fine
- Gemini Layer 2 should reuse Phase 5 result or be default-off
- Firestore schema flatness decision locked before writing
- real-video smoke before "done"

## Technology Recommendations, SMPL Excluded

SMPL / SMPL-X is intentionally excluded because of cost/licensing constraints.

### Keep RTMW as the primary whole-body backbone

RTMW is still a reasonable backbone for this project because it targets real-time whole-body pose and includes body/hands/face/feet. The RTMW paper describes RTMW as a 2D/3D whole-body model series built on RTMPose and released through MMPose. This matches the current project direction better than returning to SMPL-style mesh fitting.

Recommendation:

- Keep RTMW whole-body as primary.
- For Phase 8, exploit RTMW 133 raw keypoints where available, not only COCO-17.
- Use COCO-17 for stable scoring, but use raw whole-body keypoints/segments for contact proxy if the adapter exposes useful points.

### Consider SAM 2 for pole/person masks, not for force inference

SAM 2 is useful if Phase 8 needs a better pole/person spatial signal. It can support video segmentation and the Meta repository states code/checkpoints are Apache 2.0.

Practical use:

- segment pole mask / person mask
- derive image-space pole centerline and occlusion confidence
- detect when a limb region overlaps the pole mask

Do not use SAM 2 to infer force direction. Use it only to improve geometry and confidence.

### Consider Depth Anything V2 / Video Depth Anything as weak depth confidence

Depth Anything V2 is a strong monocular depth family and has efficient model variants. But monocular depth is not reliable metric depth in arbitrary sports video without calibration.

Practical use:

- confidence feature for "body in front of pole vs behind pole"
- occlusion/depth-order warning
- not a source for exact contact or force

License note: verify the exact checkpoint license before adopting. Some Depth Anything V2 variants differ by model size/distribution.

### MotionBERT remains useful, but not sufficient for contact

MotionBERT is useful as a temporal human-motion prior from noisy 2D observations. It can help smooth or lift pose, but it does not solve pole contact because contact depends on the pole's position/mask and body-pole spatial relationship.

Recommendation:

- Use MotionBERT/temporal priors for pose stability only.
- Do not let MotionBERT output become the only evidence for contact stability.

## Manual Gates I Would Require

1. Pole line overlay check on 5 videos.
   - The detected pole line must visually overlap the actual pole.
   - If not, axis/contact metrics are disabled or low-confidence.

2. 25 timestamp phase-boundary check.
   - 5 videos x 5 phases.
   - Boundary error target: <= 300ms median, no catastrophic phase ordering errors.

3. Contact sanity check.
   - 5 videos, expected contact points labeled by a human.
   - v1 only needs "near-pole signal matches obvious contact/loss" rather than exact force.

4. Jerk FPS-invariance check.
   - Same motion sampled at different FPS should not change severity class.

5. Firestore write/read smoke.
   - Actual saved `forceSignalsReport` round-trips through `userAnalyses.normalize()`.

## Plan-by-Plan Review

### 08-01

Good:

- 3-way lockstep is the right pattern.
- `stability_wobble()` extraction is a good drift-defense idea.
- contact YAML is useful as a motion-to-expected-contact declaration.

Needs change before execution:

- Do not create a schema that assumes valid pole distance until pole position is defined.
- Do not use `torsoScale` as distance scale.
- Avoid per-metric `warnings: list[str]` unless Firestore flatness decision is locked.
- Use programmatic fixture factories first; large JSON fixtures after coordinate contract is stable.

### 08-02

Good:

- Pure `force_signals.py` module is the right boundary.
- Reusing `dimensions` helpers is correct.
- Keeping Phase 9 out of scope is correct.

Needs change before execution:

- `compute_axis_deviation()` must require a valid pole-distance coordinate contract.
- `compute_contact_stability()` must support segment/region proxy, not only keypoint proximity.
- `compute_stability_metrics()` must use FPS-normalized derivatives.
- `compute_force_signals()` should not blindly call `temporal_fill()` again if pipeline already passed filled angles.

### 08-03

Good:

- Pipeline wiring after existing comparison is acceptable.
- Default Gemini-off fallback is good.

Needs change before execution:

- Reuse Phase 5 Gemini outputs rather than doing a second independent video call.
- Validate Gemini model availability through config/startup checks.
- Keep Layer 2 as optional evidence until manual timestamp sanity passes.
- SAM build is not enough; add a real analysis write/read smoke for `forceSignalsReport`.

## Final Recommendation

Do Phase 8, but do not implement it as currently planned. The goal is valuable; the current measurement substrate is not yet strong enough.

My preferred path:

1. Add 08-00 to define pole position + distance scale + contact primitives.
2. Revise 08-01 schema around explicit coordinate space and confidence.
3. Implement 08-02 with conservative signals, not hard contact truth.
4. Make Gemini Layer 2 default-off and reuse Phase 5 timestamps if possible.
5. Only let Phase 9 consume Phase 8 outputs with confidence gating.

If Phase 8 ships without these changes, the highest risk is not crashes. The highest risk is worse: plausible-looking coaching cards that are confidently wrong.

## External Sources Checked

- RTMW paper: https://arxiv.org/abs/2407.08634
- RTMPose paper: https://arxiv.org/abs/2303.07399
- MotionBERT paper: https://arxiv.org/abs/2210.06551
- SAM 2 paper: https://arxiv.org/abs/2408.00714
- SAM 2 GitHub/license note: https://github.com/facebookresearch/sam2
- Depth Anything V2 paper: https://arxiv.org/abs/2406.09414
- Depth Anything V2 GitHub/license note: https://github.com/DepthAnything/Depth-Anything-V2
- Gemini model docs: https://ai.google.dev/gemini-api/docs/models
