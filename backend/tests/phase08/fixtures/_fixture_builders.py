"""Plan 08-01 Task 2 — programmatic fixture builders (REVIEWS R9 정합).

Plan 08-00 박제 _factory.py 위에 6 build_*() 함수 박제. JSON fixture 박제 영구
차단 — 각 builder 는 Plan 08-02 의 force_signals.py 단위 test 가 assertion 박제하는
(pose_frames, pole_axis_measurement, body_profile, expected_dict) tuple 반환.

6 시나리오:
  - build_clean_invert         : 정상 인버트, severity all 'low'
  - build_pelvis_drop          : hold 구간 pelvis outward drift (axis severity high)
  - build_occluded_lock        : lock 구간 6/10 frame reliability='low'
  - build_motion_id_unrecognized: motion_id=None, expected_contact_points=[]
  - build_jerk_high            : transition 안 angles 3차 미분 > 15 deg/sec^3
  - build_layback_release      : hold frame 40 시점 left_hand 폴축 거리 > 0.20

모든 builder = Plan 08-00 _factory.py 박제 함수 호출 (make_pose_frame /
make_body_profile / make_pole_axis_measurement). REVIEWS R9 권고 정합.
"""

from __future__ import annotations

from typing import Any

from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.pole_geometry import PoleAxisMeasurement
from sunity_shared.analysis.pose_frame import PoseFrame

from ._factory import (
    make_body_profile,
    make_keypoint2d,
    make_pole_axis_measurement,
    make_pole_line_2d,
    make_pose_frame,
)

# fps=9 (Phase 1 frame extractor 박제). frame N 의 timestamp_ms = N * (1000/9) ≈ 111 * N.
_FPS = 9
_FRAME_MS = 1000.0 / _FPS  # ≈ 111.111ms

# image normalized 좌표 — pole 은 image x=0.5 vertical 가정 (default factory line).
_POLE_X = 0.5
_SHOULDER_Y = 0.30
_HIP_Y = 0.60  # observed torso length (image_2d) = 0.30


def _make_frame_basic(
    frame_index: int,
    *,
    pelvis_x_offset: float = 0.0,
    left_hand_x_offset: float = 0.0,
    reliability: str = "high",
) -> PoseFrame:
    """단일 frame 박제 — shoulder + hip + left_hand 4 keypoint 채움.

    pelvis_x_offset: hip x 좌표를 polo axis 로부터 outward 이동 (axis distance 측정 source).
    left_hand_x_offset: left_hand x 좌표를 pole axis 로부터 이동 (contact distance 측정 source).
    """
    kp2d = {
        "left_shoulder": make_keypoint2d(_POLE_X - 0.05, _SHOULDER_Y),
        "right_shoulder": make_keypoint2d(_POLE_X + 0.05, _SHOULDER_Y),
        "left_hip": make_keypoint2d(_POLE_X - 0.04 + pelvis_x_offset, _HIP_Y),
        "right_hip": make_keypoint2d(_POLE_X + 0.04 + pelvis_x_offset, _HIP_Y),
        "left_wrist": make_keypoint2d(_POLE_X + left_hand_x_offset, _SHOULDER_Y - 0.10),
        "right_wrist": make_keypoint2d(_POLE_X + 0.02, _SHOULDER_Y - 0.10),
    }
    return make_pose_frame(
        frame_index=frame_index,
        timestamp_ms=int(round(frame_index * _FRAME_MS)),
        keypoints_2d=kp2d,
        reliability=reliability,
    )


def _line_available_measurement() -> PoleAxisMeasurement:
    line = make_pole_line_2d(point_image=(_POLE_X, 0.5), direction_image=(0.0, 1.0))
    return make_pole_axis_measurement(line=line)


def _line_unavailable_measurement() -> PoleAxisMeasurement:
    return make_pole_axis_measurement(line=None)


# ── 6 builders ────────────────────────────────────────────────────────────


def build_clean_invert() -> tuple[
    list[PoseFrame], PoleAxisMeasurement, BodyNormalizationProfile, dict[str, Any]
]:
    """정상 인버트 — severity all 'low', estimated_stable=true, line 가용."""
    frames = [_make_frame_basic(i, reliability="high") for i in range(60)]
    pole = _line_available_measurement()
    profile = make_body_profile()
    expected = {
        "motion_id": "ref-invert",
        "fps": _FPS,
        "axis_severity": "low",
        "stability_severity": "low",
        "contact_estimated_stable": True,
        "contact_near_pole_ratio_min": 0.9,
        "contact_lost_near_pole_at_ms": None,
        "coordinate_space": "image_2d",
        "scale_denominator": "observed_torso_length",
    }
    return frames, pole, profile, expected


def build_pelvis_drop() -> tuple[
    list[PoseFrame], PoleAxisMeasurement, BodyNormalizationProfile, dict[str, Any]
]:
    """hold phase frame 30~50 사이 pelvis x-coord +0.35 outward drift.

    expected: axis_metrics[hold].severity='high', deviation_direction='outward',
    pelvisDistanceFromPoleAxis ≈ 0.35 (scaleDenominator='observed_torso_length').
    """
    frames = []
    for i in range(60):
        offset = 0.35 if 30 <= i < 50 else 0.0
        frames.append(_make_frame_basic(i, pelvis_x_offset=offset))
    pole = _line_available_measurement()
    profile = make_body_profile()
    expected = {
        "motion_id": "ref-foxtop",
        "fps": _FPS,
        "axis_severity_hold": "high",
        "deviation_direction_hold": "outward",
        "pelvis_distance_from_pole_axis_mean": 0.35,
        "coordinate_space": "image_2d",
        "scale_denominator": "observed_torso_length",
    }
    return frames, pole, profile, expected


def build_occluded_lock() -> tuple[
    list[PoseFrame], PoleAxisMeasurement, BodyNormalizationProfile, dict[str, Any]
]:
    """lock 구간 (frame 5~15) 6/10 frame reliability='low'.

    expected: warning 'occlusion_high_in_phase', lock metric confidence='low'.
    """
    frames = []
    for i in range(60):
        # lock 구간 frame 5~15 중 6 frame (5, 6, 8, 10, 12, 14) → reliability=low.
        if i in (5, 6, 8, 10, 12, 14):
            rel = "low"
        else:
            rel = "high"
        frames.append(_make_frame_basic(i, reliability=rel))
    pole = _line_available_measurement()
    profile = make_body_profile()
    expected = {
        "motion_id": "ref-foxtop",
        "fps": _FPS,
        "warning_emitted": "occlusion_high_in_phase",
        "lock_confidence": "low",
        "coordinate_space": "image_2d",
    }
    return frames, pole, profile, expected


def build_motion_id_unrecognized() -> tuple[
    list[PoseFrame], PoleAxisMeasurement, BodyNormalizationProfile, dict[str, Any]
]:
    """motion_id=None — expected_contact_points=[], measurementKind=null,
    estimated_stable=null, warning='motion_unrecognized'.
    """
    frames = [_make_frame_basic(i) for i in range(60)]
    pole = _line_available_measurement()
    profile = make_body_profile()
    expected = {
        "motion_id": None,
        "fps": _FPS,
        "expected_contact_points": [],
        "contact_estimated_stable": None,
        "contact_measurement_kind": None,
        "warning_emitted": "motion_unrecognized",
        "coordinate_space": "image_2d",
    }
    return frames, pole, profile, expected


def build_jerk_high() -> tuple[
    list[PoseFrame], PoleAxisMeasurement, BodyNormalizationProfile, dict[str, Any]
]:
    """transition (frame 15~25) 안 angles 3차 미분 > 15 deg/sec^3 (FPS-normalized, fps=9).

    expected: stability_metrics[transition].jerk_score > 15,
    jerkUnit='deg_per_sec_cubed', severity='high'.

    Note: pose_frame 의 angles 산출은 Plan 08-02 본체가 keypoints 로부터 derive.
    본 builder 는 angles wobble 이 high 한 frame sequence 의 keypoint sequence 만 박제 —
    expected 의 jerk_score>15 는 Plan 08-02 assertion 의 도메인 박제 가이드.
    """
    frames = []
    for i in range(60):
        # transition 구간 (15~25) 안 keypoint 진동 — frame 별 +/- 0.04 alternation.
        if 15 <= i < 25:
            jitter = 0.04 if (i % 2 == 0) else -0.04
        else:
            jitter = 0.0
        frames.append(_make_frame_basic(i, pelvis_x_offset=jitter))
    pole = _line_available_measurement()
    profile = make_body_profile()
    expected = {
        "motion_id": "ref-foxtop",
        "fps": _FPS,
        "stability_severity_transition": "high",
        "jerk_score_transition_min": 15.0,
        "jerk_unit": "deg_per_sec_cubed",
        "coordinate_space": "image_2d",
    }
    return frames, pole, profile, expected


def build_layback_release() -> tuple[
    list[PoseFrame], PoleAxisMeasurement, BodyNormalizationProfile, dict[str, Any]
]:
    """hold phase frame 40 시점 left_hand 폴축 거리 > 0.20 observed_torso_length.

    observed_torso_length (image_2d) = 0.30 (HIP_Y - SHOULDER_Y).
    left_hand 가 frame 40 부터 pole axis (x=0.5) 로부터 +0.10 → distance_norm = 0.10/0.30 ≈ 0.33.

    expected: contact_metrics["left_hand"][hold].lostNearPoleAtMs ≈ 4444 (frame 40 × 111ms),
    nearPoleRatio < 0.5, warning='abnormal_release_during_hold'.
    """
    frames = []
    for i in range(60):
        if i >= 40:
            left_hand_offset = 0.10  # outward
        else:
            left_hand_offset = 0.0
        frames.append(_make_frame_basic(i, left_hand_x_offset=left_hand_offset))
    pole = _line_available_measurement()
    profile = make_body_profile()
    expected = {
        "motion_id": "ref-foxtop",
        "fps": _FPS,
        "contact_lost_near_pole_at_ms": int(round(40 * _FRAME_MS)),  # ≈ 4444
        "contact_near_pole_ratio_max": 0.5,
        "warning_emitted": "abnormal_release_during_hold",
        "coordinate_space": "image_2d",
    }
    return frames, pole, profile, expected


__all__ = (
    "build_clean_invert",
    "build_pelvis_drop",
    "build_occluded_lock",
    "build_motion_id_unrecognized",
    "build_jerk_high",
    "build_layback_release",
)
