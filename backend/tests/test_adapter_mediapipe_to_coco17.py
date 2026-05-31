"""단위 테스트: MediaPipe33 → COCO-17 + 폴 확장 어댑터 (Plan 01-02 Task 1).

REVIEWS 박제:
  M-1: 어댑터가 MediaPipe visibility/presence → raw_visibility/raw_presence 변환
  M-3: pole_grip_left / pole_grip_right 추가 (derived landmark)
  H-3: pole_axis 인자가 PoseFrame.pole_axis에 그대로 보존
  H-4: reliability가 mean_visibility 기반으로 어댑터에서 산출
"""

from __future__ import annotations

import math

import pytest

from tests.fixtures.mediapipe_landmarks import (
    make_mock_world_landmarks_33,
    make_mock_image_landmarks_33,
)
from sunity_shared.analysis.adapters.mediapipe_to_coco17 import (
    convert_landmarks_to_coco17_and_pole_ext,
    MEDIAPIPE_33_TO_COCO17,
    POLE_EXTENSION_MAP,
    GRIP_LEFT_SOURCE_INDICES,
    GRIP_RIGHT_SOURCE_INDICES,
)
from sunity_shared.analysis.pose_frame import PoleAxis, Keypoint3D
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES


# ── Helpers ───────────────────────────────────────────────────────────────


def _default_pole_axis() -> PoleAxis:
    return PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
    )


def _convert_default(
    visible_indices=None,
    default_visibility: float = 0.9,
    default_presence: float = 0.9,
    pole_axis: PoleAxis | None = None,
):
    """기본값으로 convert 호출하는 헬퍼."""
    world_lms = make_mock_world_landmarks_33(
        visible_indices=visible_indices,
        default_visibility=default_visibility,
        default_presence=default_presence,
    )
    image_lms = make_mock_image_landmarks_33()
    pa = pole_axis or _default_pole_axis()
    return convert_landmarks_to_coco17_and_pole_ext(
        frame_index=0,
        timestamp_ms=0,
        world_landmarks=world_lms,
        image_landmarks=image_lms,
        pole_axis=pa,
    )


# ── Test 1: COCO-17 인덱스 매핑 ───────────────────────────────────────────


def test_coco17_index_mapping_exact():
    """MEDIAPIPE_33_TO_COCO17 dict가 정확히 17 엔트리이고 매핑이 올바른지 확인.

    RESEARCH §Pattern 3 매핑 표 박제. A1 belle 확정 보류 항목.
    """
    assert len(MEDIAPIPE_33_TO_COCO17) == 17, (
        f"COCO-17 매핑은 17개여야 함, 현재 {len(MEDIAPIPE_33_TO_COCO17)}개"
    )
    expected = {
        "nose": 0,
        "left_eye": 2,
        "right_eye": 5,
        "left_ear": 7,
        "right_ear": 8,
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_elbow": 13,
        "right_elbow": 14,
        "left_wrist": 15,
        "right_wrist": 16,
        "left_hip": 23,
        "right_hip": 24,
        "left_knee": 25,
        "right_knee": 26,
        "left_ankle": 27,
        "right_ankle": 28,
    }
    for name, idx in expected.items():
        assert MEDIAPIPE_33_TO_COCO17[name] == idx, (
            f"{name}: expected {idx}, got {MEDIAPIPE_33_TO_COCO17.get(name)}"
        )


# ── Test 2: 폴 확장 6 엔트리 ─────────────────────────────────────────────


def test_pole_extension_includes_toe_heel_grip():
    """POLE_EXTENSION_MAP이 6 엔트리(heel+toe+grip)를 포함하는지 확인.

    REVIEWS M-3: pole_grip_left / pole_grip_right derived landmark 추가.
    D-04: 폴 확장 = toe/heel/grip.
    """
    required_keys = {
        "left_heel", "right_heel",
        "left_foot_index", "right_foot_index",
        "pole_grip_left", "pole_grip_right",
    }
    assert required_keys == set(POLE_EXTENSION_MAP.keys()), (
        f"POLE_EXTENSION_MAP 키 불일치. expected={required_keys}, "
        f"got={set(POLE_EXTENSION_MAP.keys())}"
    )
    assert POLE_EXTENSION_MAP["left_heel"] == 29
    assert POLE_EXTENSION_MAP["right_heel"] == 30
    assert POLE_EXTENSION_MAP["left_foot_index"] == 31
    assert POLE_EXTENSION_MAP["right_foot_index"] == 32


# ── Test 3: grip derived landmark ─────────────────────────────────────────


def test_pole_grip_derived_from_wrist_pinky_thumb():
    """pole_grip_left 위치 = left_wrist(15)+left_pinky(17)+left_thumb(21) 좌표 평균.

    GRIP_LEFT_SOURCE_INDICES = [15, 17, 21] (M-3 / A2 belle 확정 필요).
    """
    assert tuple(GRIP_LEFT_SOURCE_INDICES) == (15, 17, 21), (
        f"GRIP_LEFT_SOURCE_INDICES: expected (15, 17, 21), got {GRIP_LEFT_SOURCE_INDICES}"
    )
    assert tuple(GRIP_RIGHT_SOURCE_INDICES) == (16, 18, 22), (
        f"GRIP_RIGHT_SOURCE_INDICES: expected (16, 18, 22), got {GRIP_RIGHT_SOURCE_INDICES}"
    )

    world_lms = make_mock_world_landmarks_33()
    image_lms = make_mock_image_landmarks_33()
    pa = _default_pole_axis()
    frame = convert_landmarks_to_coco17_and_pole_ext(
        frame_index=0,
        timestamp_ms=0,
        world_landmarks=world_lms,
        image_landmarks=image_lms,
        pole_axis=pa,
    )
    ext = frame.pole_extension_landmarks or {}
    assert "pole_grip_left" in ext, "pole_grip_left이 pole_extension_landmarks에 없음"

    # 좌표가 source 인덱스의 평균인지 확인
    expected_x = sum(world_lms[i].x for i in GRIP_LEFT_SOURCE_INDICES) / len(GRIP_LEFT_SOURCE_INDICES)
    expected_y = sum(world_lms[i].y for i in GRIP_LEFT_SOURCE_INDICES) / len(GRIP_LEFT_SOURCE_INDICES)
    grip = ext["pole_grip_left"]
    assert abs(grip.x - expected_x) < 1e-6, f"grip.x={grip.x}, expected={expected_x}"
    assert abs(grip.y - expected_y) < 1e-6, f"grip.y={grip.y}, expected={expected_y}"


# ── Test 4: convert 기본 반환 구조 ────────────────────────────────────────


def test_convert_landmarks_basic():
    """모든 33 landmark 가시 → PoseFrame 반환. keypoints_3d 17개, raw_landmarks_33 33개.

    confidence = default_visibility × default_presence = 0.9 × 0.9 = 0.81.
    """
    frame = _convert_default(visible_indices=None, default_visibility=0.9, default_presence=0.9)

    assert len(frame.keypoints_3d) == 17, (
        f"keypoints_3d: expected 17, got {len(frame.keypoints_3d)}"
    )
    assert len(frame.raw_landmarks_33) == 33, (
        f"raw_landmarks_33: expected 33, got {len(frame.raw_landmarks_33)}"
    )

    # COCO-17 키 이름이 skeleton.KEYPOINT_NAMES와 일치
    for name in KEYPOINT_NAMES:
        assert name in frame.keypoints_3d, f"keypoints_3d에 {name} 없음"

    # confidence = 0.9 × 0.9 = 0.81
    for name, kp in frame.keypoints_3d.items():
        assert abs(kp.confidence - 0.81) < 1e-6, (
            f"{name}.confidence: expected 0.81, got {kp.confidence}"
        )


# ── Test 5: raw_visibility / raw_presence 명명 (M-1 박제) ─────────────────


def test_convert_raw_visibility_presence_named_correctly():
    """어댑터가 MediaPipe visibility → raw_visibility, presence → raw_presence 변환.

    M-1 D-05 박제: bare visibility / presence 속성 없음. raw_ prefix 필수.
    """
    vis = 0.8
    pres = 0.7
    world_lms = make_mock_world_landmarks_33(
        default_visibility=vis,
        default_presence=pres,
    )
    image_lms = make_mock_image_landmarks_33()
    pa = _default_pole_axis()
    frame = convert_landmarks_to_coco17_and_pole_ext(
        frame_index=0,
        timestamp_ms=0,
        world_landmarks=world_lms,
        image_landmarks=image_lms,
        pole_axis=pa,
    )

    # raw_landmarks_33 에서 임의 landmark 확인
    lm = frame.raw_landmarks_33["nose"]
    assert abs(lm.raw_visibility - vis) < 1e-6, (
        f"raw_visibility: expected {vis}, got {lm.raw_visibility}"
    )
    assert abs(lm.raw_presence - pres) < 1e-6, (
        f"raw_presence: expected {pres}, got {lm.raw_presence}"
    )

    # bare visibility / presence 속성이 없는지 확인
    assert not hasattr(lm, "visibility"), "Landmark3D에 bare visibility 속성이 있어서는 안 됨 (M-1)"
    assert not hasattr(lm, "presence"), "Landmark3D에 bare presence 속성이 있어서는 안 됨 (M-1)"


# ── Test 6: 폴 확장 6개 존재 ─────────────────────────────────────────────


def test_convert_pole_extension_present():
    """heel + toe + grip source 모두 가시 → pole_extension_landmarks에 6개 키 존재."""
    # visible_indices는 grip source 인덱스 포함해야 함
    grip_indices = set(GRIP_LEFT_SOURCE_INDICES) | set(GRIP_RIGHT_SOURCE_INDICES)
    toe_heel_indices = {29, 30, 31, 32}
    visible_indices = grip_indices | toe_heel_indices
    frame = _convert_default(visible_indices=visible_indices)

    ext = frame.pole_extension_landmarks or {}
    required = {"left_heel", "right_heel", "left_foot_index", "right_foot_index",
                "pole_grip_left", "pole_grip_right"}
    for key in required:
        assert key in ext, f"pole_extension_landmarks에 {key} 없음"
    for key, lm in ext.items():
        assert lm.confidence > 0, f"{key}.confidence should be > 0"


# ── Test 7: 저신뢰 keypoint uncertainty_proxy ─────────────────────────────


def test_convert_low_confidence_keypoint_marked():
    """visible_indices 밖의 landmark → confidence 낮음 → uncertainty_proxy > 0.9."""
    # 극히 일부만 visible: 인덱스 [5, 12, 14, 16, 24, 26, 28]
    visible_indices = [5, 12, 14, 16, 24, 26, 28]
    frame = _convert_default(visible_indices=visible_indices, default_visibility=0.9, default_presence=0.9)

    # left_elbow = MediaPipe 13 → visible_indices에 없음 → 0.1 * 0.1 = 0.01 confidence
    # uncertainty_proxy = 1 - 0.01 = 0.99
    left_elbow = frame.keypoints_3d.get("left_elbow")
    assert left_elbow is not None, "left_elbow가 keypoints_3d에 없음"
    assert left_elbow.uncertainty_proxy > 0.9, (
        f"left_elbow.uncertainty_proxy: expected > 0.9, got {left_elbow.uncertainty_proxy}"
    )


# ── Test 8: pole_axis 보존 (H-3 박제) ────────────────────────────────────


def test_pole_axis_preserved_in_pose_frame():
    """pole_axis 인자가 PoseFrame.pole_axis에 그대로 보존되는지 확인 (H-3 박제)."""
    pa = PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
    )
    frame = _convert_default(pole_axis=pa)

    assert frame.pole_axis is not None, "PoseFrame.pole_axis가 None"
    assert frame.pole_axis.axis_vector == pa.axis_vector, (
        f"axis_vector 불일치: {frame.pole_axis.axis_vector} != {pa.axis_vector}"
    )
    assert frame.pole_axis.confidence_level == pa.confidence_level
    assert frame.pole_axis.source == pa.source


# ── Test 9: reliability = compute_frame_reliability (H-4 박제) ────────────


def test_reliability_computed_from_mean_visibility():
    """mean visibility 기반으로 reliability가 산출되는지 확인 (H-4 박제).

    모두 0.9 visibility → mean=0.9 → 'high'
    소수만 0.9, 나머지 0.1 → mean 낮음 → 'low'
    """
    # 모두 0.9 visibility → 'high'
    frame_high = _convert_default(visible_indices=None, default_visibility=0.9, default_presence=0.9)
    assert frame_high.reliability == "high", (
        f"expected 'high', got {frame_high.reliability!r}"
    )

    # 3개만 visible, 나머지 0.1 → mean visibility ≈ (3×0.9 + 30×0.1)/33 ≈ 0.173 → 'low'
    frame_low = _convert_default(
        visible_indices=[0, 1, 2],
        default_visibility=0.9,
        default_presence=0.9,
    )
    assert frame_low.reliability == "low", (
        f"expected 'low', got {frame_low.reliability!r}"
    )


# ── Test 10: pole alignment (Plan 03 완성 후 통과) ──────────────────────


def test_pole_alignment_applied_when_aligner_available():
    """pole.aligner가 설치돼 있을 때 keypoints_3d_pole_aligned가 비어있지 않음.

    Plan 03이 완성되기 전까지는 pole.aligner import 불가 → skip.
    pole_axis=identity(0,0,1)이면 raw와 동일해야 함.
    """
    pytest.importorskip("sunity_shared.analysis.pole.aligner")

    pa = PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
    )
    frame = _convert_default(pole_axis=pa)

    assert len(frame.keypoints_3d_pole_aligned) > 0, (
        "keypoints_3d_pole_aligned가 비어있음 (aligner 설치됐는데 빈 dict)"
    )

    # identity 회전이면 raw keypoints_3d와 좌표가 동일해야 함
    for name, aligned in frame.keypoints_3d_pole_aligned.items():
        raw = frame.keypoints_3d[name]
        assert abs(aligned.x - raw.x) < 1e-4, f"{name}.x mismatch after identity rotation"
        assert abs(aligned.y - raw.y) < 1e-4, f"{name}.y mismatch after identity rotation"
        assert abs(aligned.z - raw.z) < 1e-4, f"{name}.z mismatch after identity rotation"
