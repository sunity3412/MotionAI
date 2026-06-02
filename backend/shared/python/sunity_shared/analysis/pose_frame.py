"""PoseFrame + PoleAxis + Landmark3D 데이터 계약.

Phase 1 결정 박제:
  D-04: 원본 MediaPipe 33 전체 저장(raw_landmarks_33) + COCO-17 분석 계약
        (keypoints_3d, keypoints_3d_pole_aligned) + 폴 확장 landmarks 별도.
  D-05: confidence 변환 정책. raw_visibility / raw_presence 모두 별도 저장.
        confidence = visibility × presence (둘 다 있을 때), = visibility (presence=None).
        uncertainty_proxy = 1 - confidence.
        저신뢰 각도는 low_reliability 마킹; 리포트에서 단정형 문장 금지.
  D-11: PoleAxis 검출 실패 폴백 = 수직 가정 + confidence_level='low' 표기.
  D-12: raw + pole-aligned 둘 다 PoseFrame 에 저장. PoleAxis 메타도 저장.

RTMW pivot 박제 (2026-06-02, Plan 01-19):
  D-21: PoseFrame.body_shape: Optional[BodyNormalizationProfile] = None 필드 추가.
        RTMW 운영 path = body_shape=None (Phase 1 단계 측정기 없음).
        NLF_SMPLX R&D path = β 채워진 BodyNormalizationProfile (참고만).
  D-19: BodyNormalizationProfile 은 SMPL-X β 없이 segment 비율 기반
        (`backend/shared/python/sunity_shared/analysis/body_normalization.py`).

RTMW 133 원본 보존 (2026-06-02, Plan 01-21):
  D-20: PoseFrame.raw_keypoints_133 — RTMW 133 wholebody 원본 키포인트 dict 저장.
        RTMW path = {이름: Keypoint3D} 133개. MediaPipe path = None (raw_landmarks_33 사용).
        이 필드는 COCO-17 (keypoints_3d) 와 폴 확장 (pole_extension_landmarks) 의
        소스로서 원본 데이터 보존 목적. 알고리즘 스코어링에는 keypoints_3d 사용.

REVIEWS 박제:
  H-3: PoseFrame.pole_axis: PoleAxis | None 필드 추가 (D-12 완전 박제).
  H-4: PoseFrame.reliability: ReliabilityLevel + compute_frame_reliability 게이트.
  M-1: raw_visibility / raw_presence 정확 명명 (visibility / presence 단축명 없음).
  M-2: ConfidenceLevel = Literal['high','medium','low'] enum.

lockstep: app/src/types/analysis.ts PoseFrame/PoleAxis + docs/contract.md §6.
변경 시 TS + contract.md 동시 갱신 (CLAUDE.md Cross-cutting 룰).
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Literal, Optional

import numpy as np

from .skeleton import KEYPOINT_NAMES

if TYPE_CHECKING:
    # 단방향 import 규칙: pose_frame → body_normalization 만 가능.
    # body_normalization 은 pose_frame 을 import 하지 않는다 (순환 방지).
    from .body_normalization import BodyNormalizationProfile

# ── Type aliases ──────────────────────────────────────────────────────────

# M-2 D-11 박제: PoleAxis 와 frame-level reliability 둘 다 같은 값 도메인.
# 의도를 분리하기 위해 alias 두 개로 선언.
ConfidenceLevel = Literal["high", "medium", "low"]
ReliabilityLevel = Literal["high", "medium", "low"]

# H-3 reviewer 명세: 'detected' | 'vertical_fallback'.
# D-09/D-11 — Hough 검출 성공 → 'detected', 실패 → 'vertical_fallback'.
PoleAxisSource = Literal["detected", "vertical_fallback"]

# ── 신뢰도 임계값 상수 ────────────────────────────────────────────────────
# H-4 D-05 defensible default. belle 검토 후 갱신 가능.
#   mean visibility >= 0.7 → 'high'
#   mean visibility >= 0.4 → 'medium'
#   mean visibility <  0.4 → 'low'
RELIABILITY_HIGH_THRESHOLD: float = 0.7
RELIABILITY_MEDIUM_THRESHOLD: float = 0.4

# ConfidenceLevel / ReliabilityLevel 허용 값 집합 (literal 검증에 사용)
_CONFIDENCE_VALUES = frozenset({"high", "medium", "low"})
_POLE_AXIS_SOURCES = frozenset({"detected", "vertical_fallback"})


# ── Landmark3D ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Landmark3D:
    """MediaPipe 33 raw world landmark (metric 3D).

    M-1 D-05 박제: raw_visibility / raw_presence 두 필드 별도 저장.
    visibility / presence 단축명은 사용하지 않는다 — 어댑터 변환 시 정정.
    """

    x: float
    y: float
    z: float
    raw_visibility: float  # M-1 D-05 — MediaPipe API: Landmark.visibility
    raw_presence: float    # M-1 D-05 — MediaPipe API: Landmark.presence

    def __post_init__(self) -> None:
        if not (0.0 <= self.raw_visibility <= 1.0):
            raise ValueError(
                f"raw_visibility must be in [0, 1], got {self.raw_visibility}"
            )
        if not (0.0 <= self.raw_presence <= 1.0):
            raise ValueError(
                f"raw_presence must be in [0, 1], got {self.raw_presence}"
            )


# ── Keypoint3D ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Keypoint3D:
    """COCO-17 keypoint (world 3D + D-05 confidence).

    confidence = raw_visibility × raw_presence (D-05).
    uncertainty_proxy = 1 - confidence.
    """

    x: float
    y: float
    z: float
    confidence: float       # D-05: 0.0 ~ 1.0
    uncertainty_proxy: float  # D-05: 1 - confidence


# ── Keypoint3DAligned ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class Keypoint3DAligned:
    """폴 축 정렬 좌표 (D-12).

    신뢰도 메타는 keypoints_3d 의 같은 key 로 lookup.
    pole-aligned 는 좌표 변환만 — 별도 confidence 저장 불필요.
    """

    x: float
    y: float
    z: float


# ── Keypoint2D ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Keypoint2D:
    """image normalized 0~1 좌표 (D-03 UI 오버레이용).

    image landmark 에서는 raw_presence 가 MediaPipe API 에서 별도로
    제공되지 않을 수 있어 visibility 한 필드만 유지.
    raw_ prefix 는 PoseFrame level 정책이지만 image-landmark 에서는 의미 없음.
    """

    x: float
    y: float
    visibility: float  # image landmark visibility (0~1)


# ── PoseExtensionLandmark ─────────────────────────────────────────────────

@dataclass(frozen=True)
class PoseExtensionLandmark:
    """폴 확장 랜드마크 — toe / heel / grip (D-04).

    폴 확장은 가림 발생이 잦으므로 confidence 게이트를 별도 저장.
    """

    x: float
    y: float
    z: float
    confidence: float  # 0.0 ~ 1.0


# ── PoleAxis ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PoleAxis:
    """폴 축 메타 (H-3 reviewer 명세 + D-09/D-11/D-12 박제).

    axis_vector: 3D 단위 벡터 (norm ≈ 1.0).
    confidence_level: M-2 D-11 enum — 검출 실패 시 'low'.
    source: 'detected' | 'vertical_fallback' (D-09/D-11).
    frame_index: None 이면 video-level (D-10 영상 전체 평균 축 1개).
    """

    axis_vector: tuple[float, float, float]
    confidence_level: ConfidenceLevel
    source: PoleAxisSource
    frame_index: int | None = None  # D-10 — None = video-level

    def __post_init__(self) -> None:
        # M-2 D-11: literal 검증
        if self.confidence_level not in _CONFIDENCE_VALUES:
            raise ValueError(
                f"confidence_level must be one of {_CONFIDENCE_VALUES}, "
                f"got {self.confidence_level!r}"
            )
        # H-3 reviewer 명세: source literal 검증
        if self.source not in _POLE_AXIS_SOURCES:
            raise ValueError(
                f"source must be one of {_POLE_AXIS_SOURCES}, got {self.source!r}"
            )
        # 단위 벡터 norm 검증 (부동소수 허용 atol=1e-3)
        ax, ay, az = self.axis_vector
        norm = (ax * ax + ay * ay + az * az) ** 0.5
        if abs(norm - 1.0) > 1e-3:
            raise ValueError(
                f"axis_vector must be a unit vector (norm ≈ 1.0), got norm={norm}"
            )


# ── PoseFrame ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PoseFrame:
    """영상 한 프레임의 포즈 계약 (D-04/D-05/D-11/D-12 + H-3/H-4 박제).

    TS lockstep: app/src/types/analysis.ts PoseFrame interface.
    변경 시 양쪽 + docs/contract.md §6 동시 갱신 (CLAUDE.md Cross-cutting).

    필드 11개 (Plan 01-21 갱신 — raw_keypoints_133 추가, D-20 RTMW 원본 보존):
      frameIndex         / frame_index
      timestampMs        / timestamp_ms
      rawLandmarks33     / raw_landmarks_33      (D-04 MediaPipe 원본 보존, RTMW path = {})
      keypoints3D        / keypoints_3d          (COCO-17)
      keypoints3DPoleAligned / keypoints_3d_pole_aligned  (D-12 aligned)
      keypoints2D        / keypoints_2d          (D-03 UI 오버레이)
      poleExtensionLandmarks / pole_extension_landmarks   (D-04)
      poleAxis           / pole_axis             (H-3 D-12)
      reliability        / reliability           (H-4 D-05 게이트)
      bodyShape          / body_shape            (D-21 RTMW pivot — nullable)
      rawKeypoints133    / raw_keypoints_133     (D-20 RTMW 133 원본 보존 — nullable)

    TS lockstep: app/src/types/analysis.ts PoseFrame interface.
    변경 시 양쪽 + docs/contract.md §6 동시 갱신 (CLAUDE.md Cross-cutting).
    """

    frame_index: int
    timestamp_ms: int
    raw_landmarks_33: dict[str, Landmark3D] = field(default_factory=dict)
    keypoints_3d: dict[str, Keypoint3D] = field(default_factory=dict)
    keypoints_3d_pole_aligned: dict[str, Keypoint3DAligned] = field(default_factory=dict)
    keypoints_2d: dict[str, Keypoint2D] | None = None
    pole_extension_landmarks: dict[str, PoseExtensionLandmark] | None = None
    pole_axis: PoleAxis | None = None  # H-3 D-12 — video-level PoleAxis 공유
    reliability: ReliabilityLevel = "low"  # H-4 D-05 — frame-level 게이트
    # D-21 RTMW pivot 박제 — 본 필드는 nullable.
    #   RTMW 운영 path = None (Phase 1 측정기 미구현)
    #   NLF_SMPLX R&D path = body_normalization.BodyNormalizationProfile 채움
    # forward-ref 문자열로 둬 import 순서 의존 제거.
    body_shape: Optional["BodyNormalizationProfile"] = None
    # D-20 RTMW 133 원본 보존 (Plan 01-21) — nullable.
    #   RTMW path = {이름: Keypoint3D} 133개 (wholebody 원본)
    #   MediaPipe path = None (raw_landmarks_33 사용)
    #   알고리즘 스코어링에는 keypoints_3d(COCO-17) 사용 — 본 필드는 원본 보존 전용.
    raw_keypoints_133: dict[str, "Keypoint3D"] | None = None

    @classmethod
    def empty(
        cls,
        frame_index: int,
        timestamp_ms: int,
        pole_axis: PoleAxis | None = None,
        body_shape: Optional["BodyNormalizationProfile"] = None,
    ) -> "PoseFrame":
        """미감지 프레임 sentinel. 모든 dict 필드 empty, reliability='low'.

        pole_axis 는 인자 그대로 전달 — video-level axis 가 있으면 공유.
        body_shape 는 video-level 측정값이 있으면 공유 (RTMW path 에서는 None).
        """
        return cls(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            raw_landmarks_33={},
            keypoints_3d={},
            keypoints_3d_pole_aligned={},
            keypoints_2d=None,
            pole_extension_landmarks=None,
            pole_axis=pole_axis,
            reliability="low",
            body_shape=body_shape,
        )

    @staticmethod
    def compute_confidence(
        raw_visibility: float,
        raw_presence: float | None,
    ) -> tuple[float, float]:
        """D-05 공식: (confidence, uncertainty_proxy).

        둘 다 있으면 confidence = visibility × presence.
        raw_presence=None 이면 confidence = visibility.
        uncertainty_proxy = 1 - confidence.
        0~1 범위 validator 포함 (T-1-05 threat mitigation).
        """
        if not (0.0 <= raw_visibility <= 1.0):
            raise ValueError(
                f"raw_visibility must be in [0, 1], got {raw_visibility}"
            )
        if raw_presence is not None and not (0.0 <= raw_presence <= 1.0):
            raise ValueError(
                f"raw_presence must be in [0, 1], got {raw_presence}"
            )

        if raw_presence is not None:
            confidence = raw_visibility * raw_presence
        else:
            confidence = raw_visibility
        uncertainty_proxy = 1.0 - confidence
        return confidence, uncertainty_proxy


# ── module-level 함수 ──────────────────────────────────────────────────────

def compute_frame_reliability(mean_visibility: float) -> ReliabilityLevel:
    """H-4 D-05: mean visibility → ReliabilityLevel.

    >= RELIABILITY_HIGH_THRESHOLD (0.7)  → 'high'
    >= RELIABILITY_MEDIUM_THRESHOLD (0.4) → 'medium'
    else                                 → 'low'

    0~1 범위 검증 포함.
    """
    if not (0.0 <= mean_visibility <= 1.0):
        raise ValueError(
            f"mean_visibility must be in [0, 1], got {mean_visibility}"
        )
    if mean_visibility >= RELIABILITY_HIGH_THRESHOLD:
        return "high"
    if mean_visibility >= RELIABILITY_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def to_coco17_array(pose_frames: list[PoseFrame]) -> np.ndarray:
    """COCO-17 keypoints_3d_pole_aligned → (T, 17, 4) 배열 (x, y, z, uncertainty_proxy).

    skeleton.KEYPOINT_NAMES 17개 순서로 keypoints_3d_pole_aligned 에서 추출.
    빈 sentinel 또는 keypoint 없는 프레임은 NaN + uncertainty_proxy=1.0.
    기존 compute_joint_angles 가 그대로 받을 수 있는 형태.
    """
    T = len(pose_frames)
    J = len(KEYPOINT_NAMES)  # 17
    result = np.full((T, J, 4), fill_value=np.nan, dtype=np.float32)
    result[:, :, 3] = 1.0  # uncertainty_proxy default = 1.0 (미감지)

    for t, frame in enumerate(pose_frames):
        kp3d = frame.keypoints_3d
        aligned = frame.keypoints_3d_pole_aligned
        for j, name in enumerate(KEYPOINT_NAMES):
            if name in aligned:
                a = aligned[name]
                result[t, j, 0] = a.x
                result[t, j, 1] = a.y
                result[t, j, 2] = a.z
                # uncertainty_proxy 는 keypoints_3d 의 같은 key 에서 lookup
                if name in kp3d:
                    result[t, j, 3] = kp3d[name].uncertainty_proxy
                else:
                    result[t, j, 3] = 1.0
            # aligned 없으면 NaN + uncertainty_proxy=1.0 그대로

    return result
