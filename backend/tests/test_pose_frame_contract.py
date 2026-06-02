"""Phase 1 D-04, D-05, D-11, D-12 계약 검증 + REVIEWS H-3/H-4/M-1/M-2 박제 확인.

lockstep with app/src/types/analysis.ts.

D-04: 원본 MediaPipe 33 전체 보존 + COCO-17 분석 계약.
D-05: raw_visibility/raw_presence 별도 저장. confidence = visibility × presence.
D-11: PoleAxis confidence_level = 'low'|'medium'|'high' enum.
D-12: raw + pole-aligned + PoleAxis 메타 모두 PoseFrame에 저장.
H-3: PoseFrame.pole_axis 필드 (D-12 박제).
H-4: PoseFrame.reliability 필드 + compute_frame_reliability 함수.
M-1: raw_visibility / raw_presence 정확 명명 (visibility / presence 단축명 없음).
M-2: ConfidenceLevel enum ('high'|'medium'|'low').
"""

from dataclasses import fields

import pytest

from sunity_shared.analysis.pose_frame import (
    ConfidenceLevel,
    Landmark3D,
    PoleAxis,
    PoleAxisSource,
    PoseFrame,
    ReliabilityLevel,
    compute_frame_reliability,
)

# Task 7 에서 TS PoseFrame interface 와 lockstep 검증에 사용하는 기대 필드 집합.
# TS camelCase 필드를 snake_case 로 변환하면 이 집합과 일치해야 함.
# 2026-06-02 Plan 01-19 갱신: body_shape 추가 (D-21 RTMW pivot — nullable).
EXPECTED_POSE_FRAME_FIELDS = frozenset(
    {
        "frame_index",
        "timestamp_ms",
        "raw_landmarks_33",
        "keypoints_3d",
        "keypoints_3d_pole_aligned",
        "keypoints_2d",
        "pole_extension_landmarks",
        "pole_axis",
        "reliability",
        "body_shape",  # D-21 RTMW pivot (Plan 01-19) — nullable
    }
)


def _camel_to_snake(name: str) -> str:
    """TS camelCase → Python snake_case 변환 (간단 구현)."""
    import re

    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# ── Test 1 ────────────────────────────────────────────────────────────────

def test_pose_frame_empty_sentinel():
    """PoseFrame.empty() sentinel: 기대 필드값 검증 (H-3 D-12 + H-4)."""
    frame = PoseFrame.empty(frame_index=5, timestamp_ms=555, pole_axis=None)
    assert frame.frame_index == 5
    assert frame.timestamp_ms == 555
    assert frame.raw_landmarks_33 == {}
    assert frame.keypoints_3d == {}
    assert frame.keypoints_3d_pole_aligned == {}
    assert frame.pole_axis is None
    assert frame.reliability == "low"


# ── Test 2 ────────────────────────────────────────────────────────────────

def test_confidence_conversion_formula():
    """D-05 공식: visibility=0.8, presence=0.9 → confidence=0.72, uncertainty_proxy=0.28."""
    confidence, uncertainty = PoseFrame.compute_confidence(
        raw_visibility=0.8, raw_presence=0.9
    )
    assert abs(confidence - 0.72) < 1e-6
    assert abs(uncertainty - 0.28) < 1e-6

    # visibility만 있을 때 (raw_presence=None)
    confidence_v_only, uncertainty_v_only = PoseFrame.compute_confidence(
        raw_visibility=0.8, raw_presence=None
    )
    assert abs(confidence_v_only - 0.8) < 1e-6
    assert abs(uncertainty_v_only - 0.2) < 1e-6


# ── Test 3 ────────────────────────────────────────────────────────────────

def test_landmark3d_raw_field_names():
    """M-1 D-05 박제: Landmark3D 에 raw_visibility, raw_presence 존재.
    visibility/presence 단축명은 없어야 한다."""
    field_names = {f.name for f in fields(Landmark3D)}

    assert "raw_visibility" in field_names
    assert "raw_presence" in field_names
    # 단축명은 없어야 한다
    assert "visibility" not in field_names
    assert "presence" not in field_names


# ── Test 4 ────────────────────────────────────────────────────────────────

def test_pole_axis_confidence_level_enum():
    """M-2 + D-11: PoleAxis confidence_level enum 검증 + source literal 검증."""
    # valid case
    pa = PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="low",
        source="vertical_fallback",
    )
    assert pa.confidence_level == "low"
    assert pa.source == "vertical_fallback"

    # invalid confidence_level → ValueError
    with pytest.raises(ValueError):
        PoleAxis(
            axis_vector=(0.0, 0.0, 1.0),
            confidence_level="invalid",  # type: ignore[arg-type]
            source="vertical_fallback",
        )

    # invalid source → ValueError
    with pytest.raises(ValueError):
        PoleAxis(
            axis_vector=(0.0, 0.0, 1.0),
            confidence_level="low",
            source="invalid_source",  # type: ignore[arg-type]
        )


# ── Test 5 ────────────────────────────────────────────────────────────────

def test_pose_frame_has_pole_axis_field():
    """H-3 D-12 박제: PoseFrame.pole_axis 필드가 존재하고 sentinel에 None 저장."""
    frame_field_names = {f.name for f in fields(PoseFrame)}
    assert "pole_axis" in frame_field_names

    # sentinel에도 pole_axis 값이 저장됨
    frame = PoseFrame.empty(frame_index=0, timestamp_ms=0, pole_axis=None)
    assert frame.pole_axis is None

    # PoleAxis 인스턴스를 넣어도 frozen으로 저장됨
    pa = PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
    )
    frame_with_axis = PoseFrame.empty(frame_index=0, timestamp_ms=0, pole_axis=pa)
    assert frame_with_axis.pole_axis is pa


# ── Test 6 ────────────────────────────────────────────────────────────────

def test_pose_frame_reliability_field_and_threshold():
    """H-4 + D-05: compute_frame_reliability 임계값 + PoseFrame.reliability 필드."""
    assert compute_frame_reliability(0.85) == "high"
    assert compute_frame_reliability(0.55) == "medium"
    assert compute_frame_reliability(0.3) == "low"

    # 경계값
    assert compute_frame_reliability(0.7) == "high"
    assert compute_frame_reliability(0.4) == "medium"

    # PoseFrame 에 reliability 필드 존재
    field_names = {f.name for f in fields(PoseFrame)}
    assert "reliability" in field_names

    # sentinel 의 reliability = 'low'
    frame = PoseFrame.empty(frame_index=0, timestamp_ms=0)
    assert frame.reliability == "low"

    # 범위 밖 → ValueError
    with pytest.raises(ValueError):
        compute_frame_reliability(-0.1)
    with pytest.raises(ValueError):
        compute_frame_reliability(1.1)


# ── Test 7 ────────────────────────────────────────────────────────────────

def test_pose_frame_lockstep_fields():
    """TS PoseFrame interface 필드 set과 snake_case 매핑으로 일치 검증.

    기대 필드 10개 (EXPECTED_POSE_FRAME_FIELDS) — 2026-06-02 Plan 01-19 갱신:
      frame_index, timestamp_ms, raw_landmarks_33, keypoints_3d,
      keypoints_3d_pole_aligned, keypoints_2d, pole_extension_landmarks,
      pole_axis, reliability, body_shape (D-21 RTMW pivot — nullable)
    """
    actual_fields = {f.name for f in fields(PoseFrame)}
    assert actual_fields == EXPECTED_POSE_FRAME_FIELDS


# ── Test 8 ────────────────────────────────────────────────────────────────

def test_confidence_range_validation():
    """confidence 또는 visibility 가 0~1 범위 밖이면 ValueError."""
    with pytest.raises(ValueError):
        PoseFrame.compute_confidence(raw_visibility=-0.1, raw_presence=0.9)

    with pytest.raises(ValueError):
        PoseFrame.compute_confidence(raw_visibility=1.1, raw_presence=0.9)

    with pytest.raises(ValueError):
        PoseFrame.compute_confidence(raw_visibility=0.8, raw_presence=-0.1)

    with pytest.raises(ValueError):
        PoseFrame.compute_confidence(raw_visibility=0.8, raw_presence=1.1)

    # 경계값은 OK
    c, u = PoseFrame.compute_confidence(raw_visibility=0.0, raw_presence=0.0)
    assert c == 0.0
    assert u == 1.0

    c, u = PoseFrame.compute_confidence(raw_visibility=1.0, raw_presence=1.0)
    assert abs(c - 1.0) < 1e-9
    assert abs(u - 0.0) < 1e-9
