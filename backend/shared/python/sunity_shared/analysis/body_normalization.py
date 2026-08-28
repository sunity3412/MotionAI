"""BodyNormalizationProfile — 체형 정규화 메타 (D-19 / RTMW pivot 박제).

Phase 1 RTMW pivot (2026-06-02 belle 결정) 박제:

  D-19: 체형 정규화 = **SMPL-X 없이 세그먼트 길이 비율**.
        # torso-relative proportion heuristic — 절대 키 아님 (Phase 2 Task 1 lockstep).
        파라미터형 메시(SMPL-X β) 없음. estimated_height_scale /
        arm_scale / leg_scale / torso_scale / shoulder_hip_ratio +
        confidence + warnings 만으로 표현.

  D-21: PoseFrame.body_shape 필드 nullable —
        - RTMW 운영 path = body_shape=None (Phase 1 에는 측정기 없음)
        - NLF_SMPLX R&D path = β 채워진 BodyNormalizationProfile (참고만)

Consumer 예고 (Phase 2 BODY-01):
  본 dataclass 는 Phase 2 의 segment-ratio measurement
  module 이 채운 profile 을 PoseFrame.body_shape 로 주입한다.
  Phase 2 plan 01 (RTMW segment 측정기) 에서 measure_body_profile 박제.

lockstep:
  - TS 미러: app/src/types/analysis.ts BodyNormalizationProfile
  - contract.md §7 BodyNormalizationProfile 명세
  - 변경 시 3-way 동시 갱신 (CLAUDE.md Cross-cutting).

Phase 2 v5 박제 (MEDIUM-2 v5):
  # torso-relative proportion heuristic — 절대 키 아님 (Phase 2 Task 1 lockstep).
  __post_init__ 가 5 numeric scale 필드 (estimated_height_scale, arm_scale,
  leg_scale, torso_scale, shoulder_hip_ratio) finite + strictly positive 강제.
  NaN/inf/0/negative 입력은 ValueError 로 거절. 신체 segment 비율은 본질적으로
  양수 — 0 도 부적격. measurer fallback path 는 1.0 emit 으로 validator 통과.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# Phase 2 v5 (MEDIUM-2 v5): __post_init__ 가 강제하는 5 numeric scale 필드.
# fallback path 가 1.0 emit 하므로 strictly positive 통과.
_NUMERIC_SCALE_FIELDS: tuple[str, ...] = (
    # torso-relative proportion heuristic — 절대 키 아님 (Phase 2 Task 1 lockstep).
    "estimated_height_scale",
    "arm_scale",
    "leg_scale",
    "torso_scale",
    "shoulder_hip_ratio",
)


@dataclass(frozen=True)
class BodyNormalizationProfile:
    """체형 정규화 프로파일 (D-19 segment 비율 기반).

    필드 7개 (TS camelCase ↔ Python snake_case 1:1):
      # torso-relative proportion heuristic — 절대 키 아님 (Phase 2 Task 1 lockstep).
      estimatedHeightScale  / estimated_height_scale
      armScale              / arm_scale
      legScale              / leg_scale
      torsoScale            / torso_scale
      shoulderHipRatio      / shoulder_hip_ratio
      confidence            / confidence            (0.0 ~ 1.0)
      warnings              / warnings              (list[str])

    SMPL-X β / shape_params / betas 필드는 **영구히 도입하지 않는다** (D-19).
    NLF_SMPLX R&D path 에서 β 가 필요하면 R&D 전용 별도 dataclass 를 둘 것 —
    본 contract 에는 들어오지 않는다.

    Scale 필드 의미 (Phase 2 v5 — torso-relative proportion heuristic):
      estimated_height_scale / arm_scale / leg_scale 모두 절대 키가 아니라
      torso 길이 대비 사지 비율 (torso self-reference 1.0).
      estimated_height_scale = (arm_scale + leg_scale + 1.0) / 3.
      Phase 6 coarse normalizer hint 로만 사용 — 다운스트림 절대 키 추정 금지.

    confidence 의미:
      RTMW 키포인트 score 또는 측정기의 자체 신뢰도 (0=불신, 1=확신).
      Phase 2 측정기가 채움. fallback path = 0.0.

    warnings 의미 (5종 enum):
      - 'low_keypoint_confidence': 평균 conf < 0.4.
      - 'occluded_endpoint': endpoint conf<0.5 in >60% frame.
      - 'insufficient_frames': frame<30 — fallback 진입.
      - 'asymmetric_landmark_count': 좌우 valid frame 차이>30%.
      - 'pose_too_inverted': 인버트 자세 frame>50% (image y-down 좌표 직접 비교,
        PoleAxis.axis_vector 부호와 독립적 — MEDIUM-3 v5).

    Phase 2 v5 박제 (MEDIUM-2 v5):
      __post_init__ 가 5 numeric scale 필드 finite + strictly positive 강제.
      NaN/inf/0/negative ValueError. measurer fallback path 는 1.0 emit
      (strictly positive 통과 보장).
    """

    # torso-relative proportion heuristic — 절대 키 아님 (Phase 2 Task 1 lockstep).
    estimated_height_scale: float
    arm_scale: float
    leg_scale: float
    torso_scale: float
    shoulder_hip_ratio: float
    confidence: float
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # confidence 범위 검증 (T-19 contract gate)
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )

        # warnings 타입 검증 — list[str] 만 허용
        if not isinstance(self.warnings, list):
            raise TypeError(
                "warnings must be a list[str], "
                f"got {type(self.warnings).__name__}"
            )
        for i, w in enumerate(self.warnings):
            if not isinstance(w, str):
                raise TypeError(
                    f"warnings[{i}] must be str, got {type(w).__name__}"
                )

        # Phase 2 v5 (MEDIUM-2 v5): 5 numeric scale 필드 finite + strictly positive.
        # 신체 segment 비율은 본질적으로 양수 — NaN/inf/0/negative 거절.
        # measurer fallback path 는 1.0 emit 으로 본 validator 통과.
        for field_name in _NUMERIC_SCALE_FIELDS:
            v = getattr(self, field_name)
            if not math.isfinite(v):
                raise ValueError(
                    f"{field_name} must be finite (no NaN/inf), got {v}"
                )
            if v <= 0.0:
                raise ValueError(
                    f"{field_name} must be strictly positive (>0), got {v}"
                )
