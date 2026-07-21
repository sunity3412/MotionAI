"""Phase 32 Plan 32-14 (D-22 1단) — keypointReport.joints 8→12 표시 승격.

RTMW 백본이 이미 검출하는 발목·팔꿈치 좌표를 표시층(keypointReport)으로 승격한다.
감점 반영(2단)은 관절별 신뢰도 실측 게이트 뒤 — 이 플랜은 표시·측정 승격과
하위호환만 (32-14-PLAN must_haves).

behavior 5건:
  Test 1: build_keypoint_report 방출 joints == 12 (+left/right_ankle,
          +left/right_elbow) + data 길이 T×12×2 정합.
  Test 2: firestore_admin._validate_keypoint_report 길이 정합 신설 —
          12관절 신규 doc + 8관절 legacy doc 형상 모두 통과(하위호환),
          joints 길이 {8,12} 밖(7·13)이거나 data 길이 ≠ frames×J×2 는
          ValueError (강화 양방 증명).
  Test 3: confidence 배열도 frames×J 정합 (J=12).
  Test 4: JOINT_KEY_TO_ANGLE_KEY 에 ankle/elbow 1:1 매핑.
  Test 5: keypoint_augmenter._SCHEMA_TO_REPORT_JOINT 의 elbow 가 None 이
          아니라 report 키로 매핑 (audit 비교·mirror hint 확충 — 채점 무접촉은
          Task 3 스윕 diff 0 가 증명).

LOCAL ONLY — AWS/Firestore/Gemini 네트워크 0 (순수 함수 + validator 만).
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.assemble import build_keypoint_report
from sunity_shared.analysis.keypoint_frame import (
    JOINT_KEY_TO_ANGLE_KEY,
    NUM_KEYPOINTS_PHASE12,
    _KEYPOINT_NAMES,
)
from sunity_shared.analysis.pose_frame import Keypoint2D, PoseFrame
from sunity_shared.firestore_admin import _validate_keypoint_report


# 32-14 신규 승격 4관절 (wrist 는 left/right_hand 로 기존재 — RESEARCH 확장 절차 1).
_NEW_JOINTS: tuple[str, ...] = (
    "left_ankle",
    "right_ankle",
    "left_elbow",
    "right_elbow",
)

# legacy 8관절 (phase12 원본 순서 — 하위호환 fixture 용).
_LEGACY_JOINTS: tuple[str, ...] = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_hand",
    "right_hand",
)


# ── fixture helpers (phase12 conftest 패턴 self-contained 복제) ────────────

# COCO-17 전수 좌표 — 좌측 x=0.3대, 우측 x=0.7대. 발목 y=0.95, 팔꿈치 y=0.35.
_COCO17_POS: dict[str, tuple[float, float]] = {
    "nose": (0.5, 0.1),
    "left_eye": (0.45, 0.08),
    "right_eye": (0.55, 0.08),
    "left_ear": (0.40, 0.10),
    "right_ear": (0.60, 0.10),
    "left_shoulder": (0.3, 0.2),
    "right_shoulder": (0.7, 0.2),
    "left_elbow": (0.25, 0.35),
    "right_elbow": (0.75, 0.35),
    "left_wrist": (0.20, 0.50),
    "right_wrist": (0.80, 0.50),
    "left_hip": (0.35, 0.5),
    "right_hip": (0.65, 0.5),
    "left_knee": (0.35, 0.8),
    "right_knee": (0.65, 0.8),
    "left_ankle": (0.35, 0.95),
    "right_ankle": (0.65, 0.95),
}


def _full_frame(frame_idx: int) -> PoseFrame:
    """COCO-17 전수 keypoints_2d 박힌 PoseFrame (RTMW 어댑터 출력 형상)."""
    kp = {
        name: Keypoint2D(x=x, y=y, visibility=0.9)
        for name, (x, y) in _COCO17_POS.items()
    }
    return PoseFrame(
        frame_index=frame_idx,
        timestamp_ms=frame_idx * 111,
        raw_landmarks_33={},
        keypoints_3d={},
        keypoints_3d_pole_aligned={},
        keypoints_2d=kp,
        pole_extension_landmarks=None,
        pole_axis=None,
        reliability="high",
        body_shape=None,
    )


def _validator_payload(joints: list[str], frames: int = 2) -> dict:
    """_validate_keypoint_report 통과 형상 (camelCase, 길이 정합) 생성."""
    J = len(joints)
    T = frames
    return {
        "version": "1.1",
        "joints": list(joints),
        "frames": T,
        "fps": 9.0,
        "data": [0.5] * (T * J * 2),
        "confidence": [0.9] * (T * J),
        "reliability": ["high"] * T,
        "axisData": [0.5] * (T * 3 * 2),
        "axisMask": [True] * (T * 3),
        "warnings": [],
    }


# ── Test 1: 방출 12관절 + data 길이 정합 ──────────────────────────────────


class TestEmissionTwelveJoints:
    def test_joints_length_twelve_with_new_names(self) -> None:
        """방출 joints == 12 (+ankle 2 +elbow 2) — NUM_KEYPOINTS_PHASE12 파생 추종."""
        report = build_keypoint_report([_full_frame(0), _full_frame(1)], fps=9.0)
        assert report is not None
        assert len(report.joints) == 12
        assert NUM_KEYPOINTS_PHASE12 == 12
        assert len(_KEYPOINT_NAMES) == 12
        for name in _NEW_JOINTS:
            assert name in report.joints, f"신규 관절 미방출: {name}"
        # legacy 8 도 전부 유지 (하위 소비처 이름 안정성).
        for name in _LEGACY_JOINTS:
            assert name in report.joints, f"legacy 관절 소실: {name}"

    def test_data_confidence_lengths_follow_twelve(self) -> None:
        """data 길이 T×12×2 + confidence 길이 T×12 정합."""
        T = 3
        frames = [_full_frame(i) for i in range(T)]
        report = build_keypoint_report(frames, fps=9.0)
        assert report is not None
        assert len(report.data) == T * 12 * 2
        assert len(report.confidence) == T * 12

    def test_new_joint_coords_extracted_from_backbone(self) -> None:
        """발목·팔꿈치 좌표가 COCO-17 keypoints_2d 에서 실제 추출됨 (placeholder 0 아님)."""
        report = build_keypoint_report([_full_frame(0)], fps=9.0)
        assert report is not None
        J = len(report.joints)
        for name in _NEW_JOINTS:
            j = report.joints.index(name)
            x = report.data[(0 * J + j) * 2]
            y = report.data[(0 * J + j) * 2 + 1]
            exp_x, exp_y = _COCO17_POS[name]
            assert x == pytest.approx(exp_x), f"{name} x 추출 실패"
            assert y == pytest.approx(exp_y), f"{name} y 추출 실패"
            assert report.confidence[0 * J + j] == pytest.approx(0.9), (
                f"{name} confidence 추출 실패"
            )


# ── Test 2: validator 길이 정합 신설 (하위호환 + 강화 양방) ───────────────


class TestValidatorLengthCoherence:
    def test_new_twelve_doc_passes(self) -> None:
        """12관절 신규 doc 형상 통과."""
        joints = list(_LEGACY_JOINTS) + list(_NEW_JOINTS)
        _validate_keypoint_report(_validator_payload(joints))

    def test_legacy_eight_doc_passes(self) -> None:
        """8관절 legacy doc 형상 통과 — 하위호환 증명 (T-32-36)."""
        _validate_keypoint_report(_validator_payload(list(_LEGACY_JOINTS)))

    def test_joints_length_seven_rejects(self) -> None:
        """joints 길이 7 (∉ {8,12}) → ValueError."""
        joints = list(_LEGACY_JOINTS)[:7]
        with pytest.raises(ValueError, match="joints"):
            _validate_keypoint_report(_validator_payload(joints))

    def test_joints_length_thirteen_rejects(self) -> None:
        """joints 길이 13 (∉ {8,12}) → ValueError."""
        joints = list(_LEGACY_JOINTS) + list(_NEW_JOINTS) + ["extra_joint"]
        with pytest.raises(ValueError, match="joints"):
            _validate_keypoint_report(_validator_payload(joints))

    def test_data_length_mismatch_rejects(self) -> None:
        """data 길이 ≠ frames×J×2 → ValueError (신설 강화)."""
        payload = _validator_payload(list(_LEGACY_JOINTS) + list(_NEW_JOINTS))
        payload["data"] = payload["data"][:-2]  # 1 좌표쌍 절단
        with pytest.raises(ValueError, match="data"):
            _validate_keypoint_report(payload)

    def test_legacy_data_length_mismatch_rejects(self) -> None:
        """legacy 8 형상도 data 길이 정합은 강제 (신설 검사가 J 파생)."""
        payload = _validator_payload(list(_LEGACY_JOINTS))
        payload["data"] = payload["data"] + [0.5, 0.5]  # 초과
        with pytest.raises(ValueError, match="data"):
            _validate_keypoint_report(payload)

    def test_frames_absent_legacy_shape_passes(self) -> None:
        """frames 스칼라 부재 legacy 형상은 기존 그대로 통과 (정합 검사 skip)."""
        payload = _validator_payload(list(_LEGACY_JOINTS))
        del payload["frames"]
        _validate_keypoint_report(payload)


# ── Test 3: confidence 길이 정합 (J=12) ───────────────────────────────────


class TestValidatorConfidenceCoherence:
    def test_confidence_length_mismatch_rejects(self) -> None:
        """confidence 길이 ≠ frames×J (J=12) → ValueError."""
        payload = _validator_payload(list(_LEGACY_JOINTS) + list(_NEW_JOINTS))
        payload["confidence"] = payload["confidence"][:-1]
        with pytest.raises(ValueError, match="confidence"):
            _validate_keypoint_report(payload)

    def test_confidence_length_coherent_passes(self) -> None:
        """confidence 길이 frames×12 정합 통과 (T=4 별도 형상)."""
        joints = list(_LEGACY_JOINTS) + list(_NEW_JOINTS)
        _validate_keypoint_report(_validator_payload(joints, frames=4))


# ── Test 4: JOINT_KEY_TO_ANGLE_KEY ankle/elbow 1:1 ────────────────────────


class TestAngleKeyMapping:
    def test_ankle_elbow_one_to_one(self) -> None:
        """신규 4관절은 COCO 키와 1:1 (hand→wrist loose 매핑과 달리 동명)."""
        for name in _NEW_JOINTS:
            assert JOINT_KEY_TO_ANGLE_KEY[name] == name, (
                f"{name} 1:1 매핑 아님: {JOINT_KEY_TO_ANGLE_KEY.get(name)!r}"
            )

    def test_legacy_hand_mapping_preserved(self) -> None:
        """legacy loose hand 매핑 무변경 (left_hand→left_wrist)."""
        assert JOINT_KEY_TO_ANGLE_KEY["left_hand"] == "left_wrist"
        assert JOINT_KEY_TO_ANGLE_KEY["right_hand"] == "right_wrist"


# ── Test 5: keypoint_augmenter elbow 매핑 활성 ────────────────────────────


class TestAugmenterElbowMapping:
    def test_schema_to_report_elbow_mapped(self) -> None:
        """_SCHEMA_TO_REPORT_JOINT 의 elbow 가 report 키로 매핑 (None 폐기)."""
        from sunity_shared.gemini.keypoint_augmenter import _SCHEMA_TO_REPORT_JOINT

        assert _SCHEMA_TO_REPORT_JOINT["left_elbow"] == "left_elbow"
        assert _SCHEMA_TO_REPORT_JOINT["right_elbow"] == "right_elbow"

    def test_schema_to_report_legacy_six_preserved(self) -> None:
        """shoulder/hip/knee 6개 기존 매핑 무변경."""
        from sunity_shared.gemini.keypoint_augmenter import _SCHEMA_TO_REPORT_JOINT

        for name in (
            "left_shoulder",
            "right_shoulder",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
        ):
            assert _SCHEMA_TO_REPORT_JOINT[name] == name
