"""Phase 1 H-4 게이트 — Success #4 '추정 표기 + 후속 단정 금지'를 코드로 닫는 wrapper.

각도(angle) 계산 시 필수 keypoint 가 저신뢰면 low_reliability=True 마킹.
다운스트림(coach_writer, dimensions) 단정형 코멘트 금지의 신호. D-05 박제.

단일 진실: 임계값은 pose_frame.RELIABILITY_MEDIUM_THRESHOLD 재사용.
  _LOW_THRESHOLD = RELIABILITY_MEDIUM_THRESHOLD (0.4)
  min_confidence < 0.4 → low_reliability=True (마킹이 목적 — 계산은 진행)

lockstep: 본 모듈을 임포트하는 다운스트림은 low_reliability=True 시 단정형 금지.
"""

from __future__ import annotations

from typing import Callable

from .pose_frame import Keypoint3D, RELIABILITY_MEDIUM_THRESHOLD

# ── 임계값 상수 (단일 진실: pose_frame 상수 재사용) ─────────────────────────
# Test 4 에서 _LOW_THRESHOLD == RELIABILITY_MEDIUM_THRESHOLD 를 검증.
_LOW_THRESHOLD: float = RELIABILITY_MEDIUM_THRESHOLD  # 0.4

# ── 각도 키 → 필수 COCO-17 keypoint name 목록 ────────────────────────────
# skeleton.JOINT_ANGLES 방향과 일치하도록 작성.
# 영문 key 는 각도 식별자 (features.py 에서 사용될 이름과 동기화 방향).
ANGLE_REQUIRED_KEYPOINTS: dict[str, list[str]] = {
    # 무릎 굴곡 — left_hip → left_knee → left_ankle
    "left_knee_flex": ["left_hip", "left_knee", "left_ankle"],
    # 무릎 굴곡 — right_hip → right_knee → right_ankle
    "right_knee_flex": ["right_hip", "right_knee", "right_ankle"],
    # 팔꿈치 굴곡 — left_shoulder → left_elbow → left_wrist
    "left_elbow_flex": ["left_shoulder", "left_elbow", "left_wrist"],
    # 팔꿈치 굴곡 — right_shoulder → right_elbow → right_wrist
    "right_elbow_flex": ["right_shoulder", "right_elbow", "right_wrist"],
    # 고관절 축 — left_hip, right_hip (폴 기준 좌우 대칭)
    "hip_axis": ["left_hip", "right_hip"],
    # 어깨 굴곡 — left_elbow → left_shoulder → left_hip
    "left_shoulder_flex": ["left_elbow", "left_shoulder", "left_hip"],
    # 어깨 굴곡 — right_elbow → right_shoulder → right_hip
    "right_shoulder_flex": ["right_elbow", "right_shoulder", "right_hip"],
    # 고관절 굴곡 — left_shoulder → left_hip → left_knee
    "left_hip_flex": ["left_shoulder", "left_hip", "left_knee"],
    # 고관절 굴곡 — right_shoulder → right_hip → right_knee
    "right_hip_flex": ["right_shoulder", "right_hip", "right_knee"],
}


def compute_angle_with_reliability(
    angle_key: str,
    keypoints: dict[str, Keypoint3D],
    compute_fn: Callable,
) -> dict:
    """D-05 H-4 게이트: 각도 계산 + 저신뢰 마킹.

    1) angle_key 가 ANGLE_REQUIRED_KEYPOINTS 에 없으면 ValueError.
    2) 필수 keypoint 미존재 시 {'value': None, 'low_reliability': True, 'reason': 'missing_keypoints'}.
    3) min_confidence = min(keypoints[k].confidence for k in required).
    4) low_reliability = min_confidence < _LOW_THRESHOLD (0.4).
    5) value = compute_fn(keypoints) 호출 (의존성 주입 — 게이트만 책임).
    6) 반환: {'value': value, 'low_reliability': bool, 'min_confidence': float}.

    TODO: 후속 phase 에서 features.py 각도 계산이 본 wrapper 를 호출하도록 wiring.
          Phase 1 종료 시 wrapper 자체는 stub — 다운스트림 phase 에서 enforce.
    """
    if angle_key not in ANGLE_REQUIRED_KEYPOINTS:
        raise ValueError(
            f"angle_key {angle_key!r} not in ANGLE_REQUIRED_KEYPOINTS. "
            f"Available: {list(ANGLE_REQUIRED_KEYPOINTS)}"
        )

    required = ANGLE_REQUIRED_KEYPOINTS[angle_key]

    # 필수 keypoint 존재 체크
    missing = [k for k in required if k not in keypoints]
    if missing:
        return {
            "value": None,
            "low_reliability": True,
            "reason": "missing_keypoints",
        }

    min_confidence = min(keypoints[k].confidence for k in required)
    low_reliability = min_confidence < _LOW_THRESHOLD

    value = compute_fn(keypoints)

    return {
        "value": value,
        "low_reliability": low_reliability,
        "min_confidence": min_confidence,
    }
