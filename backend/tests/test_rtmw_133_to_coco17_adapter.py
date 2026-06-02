"""RTMW 133 → COCO-17 + 폴 확장 어댑터 테스트 (Plan 01-21 Task 1 RED).

D-20: RTMW 133 원본 보존 + COCO-17 + 폴 확장 (toe/heel/grip).
D-22: rtmw_score 단일 값 → Keypoint3D.confidence. uncertainty_proxy = 1 - confidence.
H-3: pole_axis 인자 → PoseFrame.pole_axis 보존.
H-4: reliability = compute_frame_reliability(mean_score).

rtmlib import 0 — 어댑터는 backend-agnostic.
"""

from __future__ import annotations

import sys
import ast
from pathlib import Path

import numpy as np
import pytest

# 픽스처 경로
sys.path.insert(0, str(Path(__file__).parent))
from fixtures.rtmw_keypoints import make_mock_rtmw_keypoints_133

REPO_ROOT = Path(__file__).resolve().parents[2]


# ── 임포트 테스트 위한 모듈 경로 ──────────────────────────────────────────
def _get_adapter_source() -> str:
    adapter_path = (
        REPO_ROOT
        / "backend"
        / "shared"
        / "python"
        / "sunity_shared"
        / "analysis"
        / "adapters"
        / "rtmw_133_to_coco17.py"
    )
    return adapter_path.read_text(encoding="utf-8")


def _get_keypoints_source() -> str:
    kp_path = (
        REPO_ROOT
        / "backend"
        / "shared"
        / "python"
        / "sunity_shared"
        / "analysis"
        / "pose_engines"
        / "rtmw"
        / "wholebody_keypoints.py"
    )
    return kp_path.read_text(encoding="utf-8")


# ── 테스트 픽스처 ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def default_pole_axis():
    from sunity_shared.analysis.pose_frame import PoleAxis
    return PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
    )


@pytest.fixture(scope="module")
def rtmw_kp_indices():
    from sunity_shared.analysis.pose_engines.rtmw.wholebody_keypoints import RTMW_KEYPOINT_INDICES
    return RTMW_KEYPOINT_INDICES


# ── Test 1: 총 133개 키포인트 ─────────────────────────────────────────────

def test_rtmw_keypoint_indices_total_133(rtmw_kp_indices):
    """RTMW_KEYPOINT_INDICES dict 총 entry = 133 (body 17 + foot 6 + face 68 + hand 42)."""
    assert len(rtmw_kp_indices) == 133, (
        f"RTMW_KEYPOINT_INDICES 총 개수 = {len(rtmw_kp_indices)}, 133 이어야 함"
    )


# ── Test 2: body 17 인덱스 COCO 표준과 일치 ──────────────────────────────

def test_rtmw_body_17_indices_match_coco(rtmw_kp_indices):
    """body 17 부분 = COCO-17 표준 인덱스 (nose=0 ~ right_ankle=16)."""
    expected_body17 = {
        "nose": 0,
        "left_eye": 1,
        "right_eye": 2,
        "left_ear": 3,
        "right_ear": 4,
        "left_shoulder": 5,
        "right_shoulder": 6,
        "left_elbow": 7,
        "right_elbow": 8,
        "left_wrist": 9,
        "right_wrist": 10,
        "left_hip": 11,
        "right_hip": 12,
        "left_knee": 13,
        "right_knee": 14,
        "left_ankle": 15,
        "right_ankle": 16,
    }
    for name, expected_idx in expected_body17.items():
        assert name in rtmw_kp_indices, f"키포인트 '{name}' 누락"
        actual = rtmw_kp_indices[name]
        assert actual == expected_idx, (
            f"'{name}' 인덱스 = {actual}, COCO 표준 {expected_idx} 이어야 함"
        )


# ── Test 3: foot 6 키포인트 존재 ─────────────────────────────────────────

def test_rtmw_foot_6_indices_present(rtmw_kp_indices):
    """foot 6 keypoint = COCO-WholeBody 표준 인덱스 (17~22)."""
    expected_foot6 = {
        "left_big_toe": 17,
        "left_small_toe": 18,
        "left_heel": 19,
        "right_big_toe": 20,
        "right_small_toe": 21,
        "right_heel": 22,
    }
    for name, expected_idx in expected_foot6.items():
        assert name in rtmw_kp_indices, f"foot keypoint '{name}' 누락"
        actual = rtmw_kp_indices[name]
        assert actual == expected_idx, (
            f"'{name}' 인덱스 = {actual}, COCO-WholeBody 표준 {expected_idx} 이어야 함"
        )


# ── Test 4: hand root 인덱스 존재 ────────────────────────────────────────

def test_rtmw_hand_indices_present(rtmw_kp_indices):
    """left_hand_root=91, right_hand_root=112 존재 (COCO-WholeBody hand layout).

    COCO-WholeBody hand 순서 (thumb-first, mmpose 표준):
      91=wrist(root), 92=thumb_cmc, 93=thumb_mcp, 94=thumb_ip, 95=thumb_tip,
      96=index_mcp, 97=index_pip, 98=index_dip, 99=index_tip, ...
    """
    assert "left_hand_root" in rtmw_kp_indices, "left_hand_root 누락"
    assert "right_hand_root" in rtmw_kp_indices, "right_hand_root 누락"
    assert rtmw_kp_indices["left_hand_root"] == 91, (
        f"left_hand_root = {rtmw_kp_indices['left_hand_root']}, 91 이어야 함"
    )
    assert rtmw_kp_indices["right_hand_root"] == 112, (
        f"right_hand_root = {rtmw_kp_indices['right_hand_root']}, 112 이어야 함"
    )
    # 손가락 일부 검증 — thumb-first 순서: 92=thumb_cmc, 96=index_finger_mcp
    # [CITED: COCO-WholeBody + mmpose hand annotation format (thumb→index→middle→ring→little)]
    assert "left_thumb_cmc" in rtmw_kp_indices, "left_thumb_cmc 누락"
    assert rtmw_kp_indices["left_thumb_cmc"] == 92, (
        f"left_thumb_cmc = {rtmw_kp_indices['left_thumb_cmc']}, 92 이어야 함 (thumb-first)"
    )
    assert "left_index_finger_mcp" in rtmw_kp_indices, "left_index_finger_mcp 누락"
    assert rtmw_kp_indices["left_index_finger_mcp"] == 96, (
        f"left_index_finger_mcp = {rtmw_kp_indices['left_index_finger_mcp']}, "
        "96 이어야 함 (thumb 4개 후)"
    )


# ── Test 5: RTMW_133_TO_COCO17 정확히 17 entry ──────────────────────────

def test_rtmw133_to_coco17_mapping_exact():
    """RTMW_133_TO_COCO17 dict 정확히 17 entry — COCO 표준 1:1 매핑."""
    from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import RTMW_133_TO_COCO17
    assert len(RTMW_133_TO_COCO17) == 17, (
        f"RTMW_133_TO_COCO17 항목 = {len(RTMW_133_TO_COCO17)}, 17 이어야 함"
    )
    # COCO-17 body skeleton names 포함 검증
    from sunity_shared.analysis.skeleton import KEYPOINT_NAMES
    for name in KEYPOINT_NAMES:
        assert name in RTMW_133_TO_COCO17, f"RTMW_133_TO_COCO17 에 '{name}' 누락"


# ── Test 6: POLE_EXTENSION_MAP 6 entry (toe/heel/grip) ──────────────────

def test_rtmw_pole_extension_includes_toe_heel_grip():
    """POLE_EXTENSION_MAP 6 entry = heel 2 + foot_index 2 + grip 2."""
    from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import POLE_EXTENSION_MAP
    assert len(POLE_EXTENSION_MAP) == 6, (
        f"POLE_EXTENSION_MAP 항목 = {len(POLE_EXTENSION_MAP)}, 6 이어야 함"
    )
    # toe = left_big_toe RTMW 인덱스 17, right_big_toe 인덱스 20
    assert "left_foot_index" in POLE_EXTENSION_MAP
    assert "right_foot_index" in POLE_EXTENSION_MAP
    assert POLE_EXTENSION_MAP["left_foot_index"] == 17, (
        "left_foot_index = left_big_toe RTMW 인덱스 17 이어야 함"
    )
    assert POLE_EXTENSION_MAP["right_foot_index"] == 20, (
        "right_foot_index = right_big_toe RTMW 인덱스 20 이어야 함"
    )
    # heel
    assert "left_heel" in POLE_EXTENSION_MAP
    assert "right_heel" in POLE_EXTENSION_MAP
    assert POLE_EXTENSION_MAP["left_heel"] == 19
    assert POLE_EXTENSION_MAP["right_heel"] == 22
    # grip derived (tuple)
    assert "pole_grip_left" in POLE_EXTENSION_MAP
    assert "pole_grip_right" in POLE_EXTENSION_MAP
    assert isinstance(POLE_EXTENSION_MAP["pole_grip_left"], tuple)
    assert isinstance(POLE_EXTENSION_MAP["pole_grip_right"], tuple)


# ── Test 7: pole grip derived from hand root ─────────────────────────────

def test_pole_grip_derived_from_hand_root():
    """GRIP_LEFT_SOURCE_INDICES / GRIP_RIGHT_SOURCE_INDICES 가 hand root + finger 인덱스 포함."""
    from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import (
        GRIP_LEFT_SOURCE_INDICES,
        GRIP_RIGHT_SOURCE_INDICES,
    )
    # left hand root = 91
    assert 91 in GRIP_LEFT_SOURCE_INDICES, (
        f"GRIP_LEFT_SOURCE_INDICES 에 left_hand_root(91) 포함 필요: {GRIP_LEFT_SOURCE_INDICES}"
    )
    # right hand root = 112
    assert 112 in GRIP_RIGHT_SOURCE_INDICES, (
        f"GRIP_RIGHT_SOURCE_INDICES 에 right_hand_root(112) 포함 필요: {GRIP_RIGHT_SOURCE_INDICES}"
    )
    # 최소 2개 이상 소스 (평균 의미 있도록)
    assert len(GRIP_LEFT_SOURCE_INDICES) >= 2
    assert len(GRIP_RIGHT_SOURCE_INDICES) >= 2


# ── Test 8: convert_keypoints_basic ─────────────────────────────────────

def test_convert_keypoints_basic(default_pole_axis):
    """score=0.9 mock 133 키포인트 → PoseFrame 반환. keypoints_3d 17개."""
    from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import (
        convert_rtmw_keypoints_to_coco17_and_pole_ext,
    )
    from sunity_shared.analysis.pose_frame import PoseFrame

    keypoints, scores = make_mock_rtmw_keypoints_133(scores=0.9)
    result = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=keypoints,
        scores_133=scores,
        image_width=640,
        image_height=480,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=default_pole_axis,
    )

    assert isinstance(result, PoseFrame), f"PoseFrame 반환 필요, got {type(result)}"
    assert len(result.keypoints_3d) == 17, (
        f"keypoints_3d 17개 필요, got {len(result.keypoints_3d)}"
    )
    # D-20 원본 133 보존 확인
    assert result.raw_keypoints_133 is not None, "raw_keypoints_133 필드 없음 (D-20)"
    assert len(result.raw_keypoints_133) == 133, (
        f"raw_keypoints_133 133개 필요, got {len(result.raw_keypoints_133)}"
    )
    # D-22 confidence = score
    for kp in result.keypoints_3d.values():
        assert abs(kp.confidence - 0.9) < 1e-6, (
            f"confidence = score(0.9) 이어야 함, got {kp.confidence}"
        )


# ── Test 9: low score → high uncertainty_proxy ──────────────────────────

def test_convert_low_score_keypoint_marked(default_pole_axis):
    """score=0.1 keypoint → uncertainty_proxy > 0.85."""
    from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import (
        convert_rtmw_keypoints_to_coco17_and_pole_ext,
        RTMW_133_TO_COCO17,
    )

    # 모든 score 0.1
    keypoints, scores = make_mock_rtmw_keypoints_133(scores=0.1)
    result = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=keypoints,
        scores_133=scores,
        image_width=640,
        image_height=480,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=default_pole_axis,
    )

    for name, kp in result.keypoints_3d.items():
        assert kp.uncertainty_proxy > 0.85, (
            f"{name} uncertainty_proxy = {kp.uncertainty_proxy}, score 0.1 시 > 0.85 필요"
        )


# ── Test 10: pole_axis 보존 ──────────────────────────────────────────────

def test_convert_pole_axis_preserved(default_pole_axis):
    """pole_axis 인자 → PoseFrame.pole_axis 동일 (H-3 정합)."""
    from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import (
        convert_rtmw_keypoints_to_coco17_and_pole_ext,
    )

    keypoints, scores = make_mock_rtmw_keypoints_133(scores=0.9)
    result = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=keypoints,
        scores_133=scores,
        image_width=640,
        image_height=480,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=default_pole_axis,
    )

    assert result.pole_axis is default_pole_axis, (
        "pole_axis 인자를 PoseFrame.pole_axis 에 그대로 보존해야 함 (H-3)"
    )


# ── Test 11: reliability from mean score ─────────────────────────────────

def test_convert_reliability_from_mean_score(default_pole_axis):
    """score=0.9 (mean>=0.7) → reliability='high'. score=0.1 → reliability='low'."""
    from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import (
        convert_rtmw_keypoints_to_coco17_and_pole_ext,
    )

    # high reliability (score 0.9, mean >= 0.7)
    kp_high, sc_high = make_mock_rtmw_keypoints_133(scores=0.9)
    result_high = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=kp_high,
        scores_133=sc_high,
        image_width=640,
        image_height=480,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=default_pole_axis,
    )
    assert result_high.reliability == "high", (
        f"score=0.9 → reliability='high', got '{result_high.reliability}'"
    )

    # low reliability (score 0.1, mean < 0.4)
    kp_low, sc_low = make_mock_rtmw_keypoints_133(scores=0.1)
    result_low = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=kp_low,
        scores_133=sc_low,
        image_width=640,
        image_height=480,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=default_pole_axis,
    )
    assert result_low.reliability == "low", (
        f"score=0.1 → reliability='low', got '{result_low.reliability}'"
    )


# ── Test 12: body_shape = None (D-21) ────────────────────────────────────

def test_convert_body_shape_none(default_pole_axis):
    """PoseFrame.body_shape == None (D-21 — RTMW 는 SMPL-X β 없음)."""
    from sunity_shared.analysis.adapters.rtmw_133_to_coco17 import (
        convert_rtmw_keypoints_to_coco17_and_pole_ext,
    )

    keypoints, scores = make_mock_rtmw_keypoints_133(scores=0.9)
    result = convert_rtmw_keypoints_to_coco17_and_pole_ext(
        keypoints_133=keypoints,
        scores_133=scores,
        image_width=640,
        image_height=480,
        frame_index=0,
        timestamp_ms=0,
        pole_axis=default_pole_axis,
    )

    assert result.body_shape is None, (
        f"RTMW path: body_shape = None 이어야 함 (D-21), got {result.body_shape}"
    )


# ── 추가: rtmlib import 없는지 검증 ─────────────────────────────────────

def test_adapter_no_rtmlib_import():
    """rtmw_133_to_coco17.py 는 rtmlib/mmpose module-level (top-level) import 0.

    어댑터는 backend-agnostic — rtmlib 의존 없음.
    """
    source = _get_adapter_source()
    tree = ast.parse(source)
    # module-level = ast.Module.body 직접 자식만 (함수 내 lazy import 허용)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.lower()
                assert "rtmlib" not in mod, f"rtmlib module-level import 금지: {alias.name}"
                assert "mmpose" not in mod, f"mmpose module-level import 금지: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.lower()
                assert "rtmlib" not in mod, f"rtmlib module-level import 금지: {node.module}"
                assert "mmpose" not in mod, f"mmpose module-level import 금지: {node.module}"
