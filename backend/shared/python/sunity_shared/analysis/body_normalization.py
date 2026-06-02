"""BodyNormalizationProfile — 체형 정규화 메타 (D-19 / RTMW pivot 박제).

Phase 1 RTMW pivot (2026-06-02 belle 결정) 박제:

  D-19: 체형 정규화 = **SMPL-X 없이 세그먼트 길이 비율**.
        파라미터형 메시(SMPL-X β) 없음. estimated_height_scale /
        arm_scale / leg_scale / torso_scale / shoulder_hip_ratio +
        confidence + warnings 만으로 표현.

  D-21: PoseFrame.body_shape 필드 nullable —
        - RTMW 운영 path = body_shape=None (Phase 1 에는 측정기 없음)
        - NLF_SMPLX R&D path = β 채워진 BodyNormalizationProfile (참고만)

Consumer 예고 (Phase 2 BODY-01):
  본 dataclass 는 Phase 2 의 segment-ratio measurement
  module 이 채운 profile 을 PoseFrame.body_shape 로 주입한다.
  Phase 1 (본 plan 19~25) 단계에서는 contract 박제만 — 측정기 미구현.

lockstep:
  - TS 미러: app/src/types/analysis.ts BodyNormalizationProfile
  - contract.md §6.x 또는 §7 BodyNormalizationProfile 명세
  - 변경 시 3-way 동시 갱신 (CLAUDE.md Cross-cutting).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BodyNormalizationProfile:
    """체형 정규화 프로파일 (D-19 segment 비율 기반).

    필드 7개 (TS camelCase ↔ Python snake_case 1:1):
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

    confidence 의미:
      RTMW 키포인트 score 또는 측정기의 자체 신뢰도 (0=불신, 1=확신).
      Phase 2 측정기가 채움. Phase 1 contract 단계에서는 임의의 값 허용.

    warnings 의미:
      측정 과정에서 감지한 품질 이슈 (예: 'short_arm_clip', 'occluded_torso').
      list[str], 기본값 []. Phase 2 측정기가 채움.
    """

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
