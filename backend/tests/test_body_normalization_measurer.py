"""measure_body_profile 단위 테스트 (Phase 2 BODY-01 박제).

5 fixture × profile assertion + MEDIUM-3 v5 image-y-order independence
+ MEDIUM-2 v5 positive-scale fallback.
"""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from typing import Any

import pytest

from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
from sunity_shared.analysis.body_normalization_measurer import (
    _is_inverted_frame,
    measure_body_profile,
)
from sunity_shared.analysis.pose_frame import (
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseFrame,
)

from tests.fixtures.body_normalization._factory import pose_frame_from_dict


_FIXTURES_DIR = (
    Path(__file__).resolve().parent / "fixtures" / "body_normalization"
)


def _load_fixture_frames(name: str) -> list[PoseFrame]:
    raw = json.loads(
        (_FIXTURES_DIR / f"{name}_pose_frames.json").read_text(encoding="utf-8")
    )
    return [pose_frame_from_dict(r) for r in raw]


# ── 단위 테스트 12 case ────────────────────────────────────────────────────


def test_normal_pose_profile_valid() -> None:
    """정상 fixture → warnings==[], finite + strictly positive."""
    frames = _load_fixture_frames("normal_pose")
    profile = measure_body_profile(frames)
    assert isinstance(profile, BodyNormalizationProfile)
    assert profile.warnings == []
    # 모든 scale 필드 finite + positive
    for fname in (
        "estimated_height_scale",
        "arm_scale",
        "leg_scale",
        "torso_scale",
        "shoulder_hip_ratio",
    ):
        v = getattr(profile, fname)
        assert math.isfinite(v) and v > 0.0, f"{fname}={v} not positive-finite"
    assert profile.confidence > 0.0


def test_inverted_pose_warning() -> None:
    """inverted fixture → pose_too_inverted ∈ warnings."""
    frames = _load_fixture_frames("inverted_pose")
    profile = measure_body_profile(frames)
    assert "pose_too_inverted" in profile.warnings


def _replace_pole_axis(
    frame: PoseFrame, new_axis: tuple[float, float, float]
) -> PoseFrame:
    """frame 의 pole_axis 만 교체 (axis_vector 변형 테스트용)."""
    new_pa = PoleAxis(
        axis_vector=new_axis,
        confidence_level=frame.pole_axis.confidence_level if frame.pole_axis else "medium",
        source=frame.pole_axis.source if frame.pole_axis else "vertical_fallback",
        frame_index=frame.pole_axis.frame_index if frame.pole_axis else None,
    )
    return dataclasses.replace(frame, pole_axis=new_pa)


def test_inversion_uses_image_y_order_not_pole_axis() -> None:
    """MEDIUM-3 v5 박제: normal_pose pole_axis 다양한 부호 → 동일 verdict (warning 미발화)."""
    frames = _load_fixture_frames("normal_pose")
    axis_variants = [
        (0.0, 1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    ]
    for ax in axis_variants:
        modified = [_replace_pole_axis(f, ax) for f in frames]
        profile = measure_body_profile(modified)
        assert "pose_too_inverted" not in profile.warnings, (
            f"normal_pose with axis_vector={ax} 가 인버트로 잘못 판정 (MEDIUM-3 v5)"
        )


def test_inversion_independent_of_pole_axis_sign() -> None:
    """MEDIUM-3 v5 핵심 sanity gate: inverted_pose axis_vector flip 시 verdict 불변."""
    frames = _load_fixture_frames("inverted_pose")
    for ax in ((0.0, 1.0, 0.0), (0.0, -1.0, 0.0)):
        modified = [_replace_pole_axis(f, ax) for f in frames]
        profile = measure_body_profile(modified)
        assert "pose_too_inverted" in profile.warnings, (
            f"inverted_pose with axis_vector={ax} 가 인버트로 잡히지 않음 "
            f"(MEDIUM-3 v5 axis-independence 박제 위반)"
        )


def test_occluded_leg_warning() -> None:
    """occluded_leg fixture → occluded_endpoint 발화."""
    frames = _load_fixture_frames("occluded_leg")
    profile = measure_body_profile(frames)
    assert "occluded_endpoint" in profile.warnings


def test_short_clip_warning() -> None:
    """short_clip fixture → insufficient_frames 발화 + MEDIUM-2 v5 validator 통과."""
    frames = _load_fixture_frames("short_clip")
    profile = measure_body_profile(frames)
    assert "insufficient_frames" in profile.warnings
    # MEDIUM-2 v5: 모든 scale 필드 strictly positive (validator 통과)
    for fname in (
        "estimated_height_scale",
        "arm_scale",
        "leg_scale",
        "torso_scale",
        "shoulder_hip_ratio",
    ):
        v = getattr(profile, fname)
        assert math.isfinite(v) and v > 0.0


def test_asymmetric_warning() -> None:
    """asymmetric_pose fixture → asymmetric_landmark_count 발화."""
    frames = _load_fixture_frames("asymmetric_pose")
    profile = measure_body_profile(frames)
    assert "asymmetric_landmark_count" in profile.warnings


def test_z_axis_ignored_when_zero() -> None:
    """z=0 override (image y-down 본 측정의 z 무시 박제). arm_scale ±1%."""
    frames = _load_fixture_frames("normal_pose")
    profile_orig = measure_body_profile(frames)

    # z 만 다른 값으로 override
    def _zify(frame: PoseFrame, new_z: float = 50.0) -> PoseFrame:
        new_kp3d = {
            name: Keypoint3D(
                x=kp.x,
                y=kp.y,
                z=new_z,
                confidence=kp.confidence,
                uncertainty_proxy=kp.uncertainty_proxy,
            )
            for name, kp in frame.keypoints_3d.items()
        }
        return dataclasses.replace(frame, keypoints_3d=new_kp3d)

    frames_z = [_zify(f) for f in frames]
    profile_z = measure_body_profile(frames_z)
    # z 무시 → arm_scale 변화 0 (또는 ±1%)
    assert abs(profile_orig.arm_scale - profile_z.arm_scale) / profile_orig.arm_scale < 0.01


def test_profile_validator_passes_for_normal_fixture() -> None:
    """정상 fixture profile 객체 생성 + __post_init__ 통과."""
    frames = _load_fixture_frames("normal_pose")
    profile = measure_body_profile(frames)
    # __post_init__ 통과 = 객체 생성 자체가 검증
    assert profile is not None


def test_fallback_scales_are_positive() -> None:
    """MEDIUM-2 v5: 합성 all-NaN fixture (T=3) → fallback path → 5 scale 필드 모두 >0."""
    frames: list[PoseFrame] = []
    for i in range(3):
        frame = PoseFrame(
            frame_index=i,
            timestamp_ms=i * 33,
            raw_landmarks_33={},
            keypoints_3d={},  # all missing
            keypoints_3d_pole_aligned={},
            keypoints_2d=None,
            pole_extension_landmarks=None,
            pole_axis=PoleAxis(
                axis_vector=(0.0, 1.0, 0.0),
                confidence_level="low",
                source="vertical_fallback",
                frame_index=None,
            ),
            reliability="low",
            body_shape=None,
        )
        frames.append(frame)
    profile = measure_body_profile(frames)
    for fname in (
        "estimated_height_scale",
        "arm_scale",
        "leg_scale",
        "torso_scale",
        "shoulder_hip_ratio",
    ):
        v = getattr(profile, fname)
        assert math.isfinite(v) and v > 0.0, f"fallback {fname}={v} not positive"
    assert profile.confidence == 0.0


def test_no_nan_or_inf_in_output_for_any_fixture() -> None:
    """MEDIUM-2 v5: 5 fixture 모두 → 모든 numeric 필드 finite + positive."""
    for name in (
        "normal_pose",
        "inverted_pose",
        "occluded_leg",
        "short_clip",
        "asymmetric_pose",
    ):
        frames = _load_fixture_frames(name)
        profile = measure_body_profile(frames)
        for fname in (
            "estimated_height_scale",
            "arm_scale",
            "leg_scale",
            "torso_scale",
            "shoulder_hip_ratio",
        ):
            v = getattr(profile, fname)
            assert math.isfinite(v) and v > 0.0, (
                f"{name}.{fname}={v} not positive-finite"
            )


def test_idempotent() -> None:
    """동일 fixture 2회 → 동일 profile."""
    frames = _load_fixture_frames("normal_pose")
    p1 = measure_body_profile(frames)
    p2 = measure_body_profile(frames)
    assert p1 == p2


# ── MEDIUM-3 v5 박제: _is_inverted_frame 시그너처 검증 ───────────────────


def test_is_inverted_frame_signature_no_pole_axis() -> None:
    """MEDIUM-3 v5: _is_inverted_frame 시그너처에서 pole_axis 인자 부재."""
    import inspect

    sig = inspect.signature(_is_inverted_frame)
    assert "pole_axis" not in sig.parameters, (
        f"pole_axis 인자 폐기 위반: {sig}"
    )


def test_is_inverted_frame_docstring_medium3v5_marker() -> None:
    """MEDIUM-3 v5 박제: docstring 에 'image y-down' + 'MEDIUM-3 v5' 표기."""
    doc = _is_inverted_frame.__doc__ or ""
    assert "image y-down" in doc
    assert "MEDIUM-3 v5" in doc
    assert "PoleAxis.axis_vector" in doc
