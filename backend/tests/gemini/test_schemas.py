"""Plan 17-01 Task 1 — 4 영역 Pydantic schema 라운드트립 + 거부 케이스 단위 테스트.

박제 정신:
  · AI-SPEC §4b "Structured Outputs with Pydantic" 의 4 영역 schema 정의를 1:1 검증.
  · 정상 model_validate(payload) → 인스턴스 반환 + 필드 보존.
  · 경계 케이스 (length=1, length=upper bound) 통과.
  · 거부 케이스 (음수 / 길이 초과 / Literal 미스 / 사람 판단 어휘) → ValidationError.

mock 불필요 — pure pydantic + 정규식. 외부 의존 0.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sunity_shared.gemini import (
    CoachPayload,
    FindingFlags,
    KeypointRefinement,
    ReferenceRegistration,
)


# ─────────────────── ReferenceRegistration (영역 A) ───────────────────


class TestReferenceRegistration:
    def test_valid_payload_roundtrips(self) -> None:
        payload = {
            "motion_name_ipsf": "Inverted Butterfly",
            "motion_name_ko": "인버티드 버터플라이",
            "clip_start_seconds": 1.2,
            "clip_end_seconds": 4.8,
            "checkpoint_joints": [
                {"joint_key": "left_elbow", "expectation": "EXTEND"},
                {"joint_key": "right_knee", "expectation": "BENT_OK"},
            ],
            "confidence": 0.85,
        }
        ref = ReferenceRegistration.model_validate(payload)
        assert ref.motion_name_ipsf == "Inverted Butterfly"
        assert ref.motion_name_ko == "인버티드 버터플라이"
        assert ref.clip_start_seconds == 1.2
        assert len(ref.checkpoint_joints) == 2
        assert ref.checkpoint_joints[0].expectation == "EXTEND"

    def test_negative_clip_start_rejected(self) -> None:
        payload = {
            "motion_name_ipsf": "Inverted Butterfly",
            "motion_name_ko": "인버티드",
            "clip_start_seconds": -0.1,
            "clip_end_seconds": 4.0,
            "checkpoint_joints": [
                {"joint_key": "left_elbow", "expectation": "EXTEND"},
            ],
            "confidence": 0.9,
        }
        with pytest.raises(ValidationError):
            ReferenceRegistration.model_validate(payload)

    def test_checkpoint_joints_empty_rejected(self) -> None:
        payload = {
            "motion_name_ipsf": "X",
            "motion_name_ko": "엑스",
            "clip_start_seconds": 0.0,
            "clip_end_seconds": 1.0,
            "checkpoint_joints": [],
            "confidence": 0.5,
        }
        with pytest.raises(ValidationError):
            ReferenceRegistration.model_validate(payload)

    def test_checkpoint_joints_over_eight_rejected(self) -> None:
        nine_joints = [
            {"joint_key": "left_elbow", "expectation": "EXTEND"},
        ] * 9
        payload = {
            "motion_name_ipsf": "X",
            "motion_name_ko": "엑스",
            "clip_start_seconds": 0.0,
            "clip_end_seconds": 1.0,
            "checkpoint_joints": nine_joints,
            "confidence": 0.5,
        }
        with pytest.raises(ValidationError):
            ReferenceRegistration.model_validate(payload)

    def test_invalid_joint_key_literal_rejected(self) -> None:
        payload = {
            "motion_name_ipsf": "X",
            "motion_name_ko": "엑스",
            "clip_start_seconds": 0.0,
            "clip_end_seconds": 1.0,
            "checkpoint_joints": [
                {"joint_key": "left_ankle", "expectation": "EXTEND"},
            ],
            "confidence": 0.5,
        }
        with pytest.raises(ValidationError):
            ReferenceRegistration.model_validate(payload)

    def test_invalid_expectation_literal_rejected(self) -> None:
        payload = {
            "motion_name_ipsf": "X",
            "motion_name_ko": "엑스",
            "clip_start_seconds": 0.0,
            "clip_end_seconds": 1.0,
            "checkpoint_joints": [
                {"joint_key": "left_elbow", "expectation": "BOGUS"},
            ],
            "confidence": 0.5,
        }
        with pytest.raises(ValidationError):
            ReferenceRegistration.model_validate(payload)

    def test_confidence_out_of_range_rejected(self) -> None:
        payload = {
            "motion_name_ipsf": "X",
            "motion_name_ko": "엑스",
            "clip_start_seconds": 0.0,
            "clip_end_seconds": 1.0,
            "checkpoint_joints": [
                {"joint_key": "left_elbow", "expectation": "EXTEND"},
            ],
            "confidence": 1.5,
        }
        with pytest.raises(ValidationError):
            ReferenceRegistration.model_validate(payload)


# ─────────────────── CoachPayload (영역 B) ───────────────────


def _coach_cause(idx: int) -> dict:
    return {
        "title": f"원인 {idx}",
        "explanation": f"원인 {idx} 설명",
        "fix": f"원인 {idx} 교정",
    }


def _joint_coaching(joint_key: str, n_causes: int = 3) -> dict:
    return {
        "joint_key": joint_key,
        "detail": "어깨가 굽어있어 라인이 끊어집니다.",
        "detail2": {"causes": [_coach_cause(i + 1) for i in range(n_causes)]},
    }


class TestCoachPayload:
    def test_valid_three_causes_passes(self) -> None:
        payload = {
            "joints": [_joint_coaching("left_shoulder", n_causes=3)],
        }
        coach = CoachPayload.model_validate(payload)
        assert len(coach.joints) == 1
        assert len(coach.joints[0].detail2.causes) == 3

    def test_valid_five_causes_passes(self) -> None:
        payload = {
            "joints": [_joint_coaching("left_hip", n_causes=5)],
        }
        coach = CoachPayload.model_validate(payload)
        assert len(coach.joints[0].detail2.causes) == 5

    def test_two_causes_rejected(self) -> None:
        payload = {
            "joints": [_joint_coaching("left_hip", n_causes=2)],
        }
        with pytest.raises(ValidationError):
            CoachPayload.model_validate(payload)

    def test_six_causes_rejected(self) -> None:
        payload = {
            "joints": [_joint_coaching("left_hip", n_causes=6)],
        }
        with pytest.raises(ValidationError):
            CoachPayload.model_validate(payload)

    def test_missing_cause_field_rejected(self) -> None:
        payload = {
            "joints": [
                {
                    "joint_key": "left_hip",
                    "detail": "라인 끊김",
                    "detail2": {
                        "causes": [
                            {"title": "t", "explanation": "e"},  # fix 누락
                            _coach_cause(2),
                            _coach_cause(3),
                        ],
                    },
                },
            ],
        }
        with pytest.raises(ValidationError):
            CoachPayload.model_validate(payload)

    def test_empty_joints_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CoachPayload.model_validate({"joints": []})


# ─────────────────── FindingFlags (영역 C) ───────────────────


class TestFindingFlags:
    def test_valid_payload_roundtrips(self) -> None:
        payload = {
            "grip_visible": True,
            "backbend_present": False,
            "occlusion_severe": False,
            "camera_angle_problematic": True,
            "notes_ko": "측면 촬영 권장",
        }
        finding = FindingFlags.model_validate(payload)
        assert finding.grip_visible is True
        assert finding.camera_angle_problematic is True

    def test_notes_at_max_length_passes(self) -> None:
        payload = {
            "grip_visible": False,
            "backbend_present": False,
            "occlusion_severe": False,
            "camera_angle_problematic": False,
            "notes_ko": "가" * 200,
        }
        finding = FindingFlags.model_validate(payload)
        assert len(finding.notes_ko) == 200

    def test_notes_over_two_hundred_chars_rejected(self) -> None:
        payload = {
            "grip_visible": False,
            "backbend_present": False,
            "occlusion_severe": False,
            "camera_angle_problematic": False,
            "notes_ko": "가" * 201,
        }
        with pytest.raises(ValidationError):
            FindingFlags.model_validate(payload)


# ─────────────────── KeypointRefinement (영역 D) ───────────────────


class TestKeypointRefinement:
    def test_valid_payload_roundtrips(self) -> None:
        payload = {
            "refined": [
                {
                    "frame_index": 12,
                    "x_normalized": 0.5,
                    "y_normalized": 0.42,
                    "confidence": 0.78,
                },
            ],
        }
        ref = KeypointRefinement.model_validate(payload)
        assert ref.refined[0].frame_index == 12
        assert ref.refined[0].x_normalized == 0.5

    def test_negative_frame_index_rejected(self) -> None:
        payload = {
            "refined": [
                {
                    "frame_index": -1,
                    "x_normalized": 0.5,
                    "y_normalized": 0.5,
                    "confidence": 0.5,
                },
            ],
        }
        with pytest.raises(ValidationError):
            KeypointRefinement.model_validate(payload)

    def test_x_out_of_range_rejected(self) -> None:
        payload = {
            "refined": [
                {
                    "frame_index": 0,
                    "x_normalized": 1.1,
                    "y_normalized": 0.5,
                    "confidence": 0.5,
                },
            ],
        }
        with pytest.raises(ValidationError):
            KeypointRefinement.model_validate(payload)

    def test_over_two_hundred_refined_rejected(self) -> None:
        payload = {
            "refined": [
                {
                    "frame_index": i,
                    "x_normalized": 0.5,
                    "y_normalized": 0.5,
                    "confidence": 0.5,
                }
                for i in range(201)
            ],
        }
        with pytest.raises(ValidationError):
            KeypointRefinement.model_validate(payload)
