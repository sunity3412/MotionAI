"""GeometricCriterion — IPSF Code of Points 기반 객관 임계값 단위 (JUDGE-DATA-01).

Plan 01-15 도입 (2026-06-01, belle 결정 박제):
  · Plan 01-12 verdict (c) NLF baseline 편차 strong → NLF 갭 baseline 영구 폐기.
  · 새 채점 baseline = IPSF Code of Points (국제폴스포츠연맹) 단일 기준.
    KPSA(한국폴스포츠협회) 도 IPSF 따름. 다른 단체 기준 도입 금지.
  · 사람 점수 라벨링 (belle/강사/심사자) ground truth 영구 금지 —
    belle 가 본 plan 에서 채우는 값은 "점수" 가 아니라 "IPSF 객관 임계값 수치".
  · memory 박제:
      - analysis-objectivity-no-human-scores.md
      - judging-baseline-ipsf-code-of-points.md

사용처:
  · Plan 01-13 — Gemini 가 추출한 key moment 시점에서 측정 각도 lookup 후
    `angle_target ± tolerance_full` 비교 → 갭 산출 → 감점 계산.
  · Plan 01-14 게이트 — 측정 각도 ↔ `angle_target` 갭 ≤ `tolerance_full`.

스키마 핵심 (REQUIREMENTS.md JUDGE-DATA-01:74):
  motion          기준 동작 ID (sweep 5영상 ref-* 와 동일)
  moment_key      phase 키 — setup / hold / peak / release (Plan 13 호환)
  joint_key       skeleton.JOINT_KEYS 와 같은 관절 키 (예: left_knee)
  angle_target    IPSF 규정 phase별 target angle (degree)
  tolerance_full  IPSF Full Mark tolerance (degree, ±). 폴스포츠-지식.md:311 기본 20°
  deduction_per_step  tolerance 초과 1° 당 감점값 (IPSF 기본 0.2점)
  minimum_requirement IPSF minimum 충족 각도 — 이 값 미만 = 동작 실패
  source_ref      IPSF Code of Points 인용 (섹션 명시). 비어있으면 객관성 위반
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# IPSF Code of Points 기반 4 phase — Plan 13 Gemini key moment 분류와 동일.
VALID_MOMENT_KEYS: Final[tuple[str, ...]] = ("setup", "hold", "peak", "release")


@dataclass(frozen=True)
class GeometricCriterion:
    """단일 (motion × moment × joint) 객관 임계값 entry.

    frozen=True — 한번 로드된 IPSF 기준이 런타임에 변경되지 않도록 불변.
    validate() 는 belle 라벨링 정합성을 IPSF 객관성 기준으로 점검 (단위 테스트 가드).
    """

    motion: str
    moment_key: str
    joint_key: str
    angle_target: float
    tolerance_full: float
    deduction_per_step: float
    minimum_requirement: float
    source_ref: str

    def validate(self) -> None:
        """IPSF 객관성 가드. 위반 시 명확한 한국어 메시지로 ValueError.

        belle 가 사람 점수를 매기지 않고 IPSF 규정 인용을 보장하기 위한 5+1 항목 가드:
          1. tolerance_full > 0  (IPSF Full Mark tolerance 표준)
          2. deduction_per_step > 0
          3. 0 ≤ angle_target ≤ 360
          4. 0 ≤ minimum_requirement ≤ angle_target
             (최소 충족이 target 보다 클 수 없음)
          5. source_ref.strip() 비어있지 않음 (객관 인용 의무화)
          6. moment_key ∈ {setup, hold, peak, release}
        """
        # 1. tolerance_full > 0
        if self.tolerance_full <= 0:
            raise ValueError(
                f"tolerance_full 은 0 보다 커야 합니다 (IPSF Full Mark tolerance 표준). "
                f"motion={self.motion} moment={self.moment_key} joint={self.joint_key} "
                f"tolerance_full={self.tolerance_full}"
            )

        # 2. deduction_per_step > 0
        if self.deduction_per_step <= 0:
            raise ValueError(
                f"deduction_per_step 은 0 보다 커야 합니다 (IPSF 감점 step 표준 0.2). "
                f"motion={self.motion} moment={self.moment_key} joint={self.joint_key} "
                f"deduction_per_step={self.deduction_per_step}"
            )

        # 3. 0 ≤ angle_target ≤ 360
        if self.angle_target < 0 or self.angle_target > 360:
            raise ValueError(
                f"angle_target 은 [0, 360] 범위여야 합니다. "
                f"motion={self.motion} moment={self.moment_key} joint={self.joint_key} "
                f"angle_target={self.angle_target}"
            )

        # 4. 0 ≤ minimum_requirement ≤ angle_target
        if self.minimum_requirement < 0:
            raise ValueError(
                f"minimum_requirement 는 0 이상이어야 합니다. "
                f"motion={self.motion} moment={self.moment_key} joint={self.joint_key} "
                f"minimum_requirement={self.minimum_requirement}"
            )
        if self.minimum_requirement > self.angle_target:
            raise ValueError(
                f"minimum_requirement 는 angle_target 보다 클 수 없습니다 "
                f"(최소 충족 각도가 IPSF target 보다 크면 불가능). "
                f"motion={self.motion} moment={self.moment_key} joint={self.joint_key} "
                f"minimum_requirement={self.minimum_requirement} > angle_target={self.angle_target}"
            )

        # 5. source_ref 비어있지 않음 — 객관 인용 의무화
        if not self.source_ref or not self.source_ref.strip():
            raise ValueError(
                f"source_ref 비어있음 — IPSF Code of Points 객관 인용 의무화 (사람 점수 라벨링 금지). "
                f"motion={self.motion} moment={self.moment_key} joint={self.joint_key} "
                f"source_ref 에 IPSF 섹션 명시 필요 (예: 'IPSF Code of Points 2024 §4.2.1')."
            )

        # 6. moment_key ∈ VALID_MOMENT_KEYS
        if self.moment_key not in VALID_MOMENT_KEYS:
            raise ValueError(
                f"moment_key 부정확. 유효 값 = {VALID_MOMENT_KEYS}. "
                f"motion={self.motion} joint={self.joint_key} "
                f"moment_key={self.moment_key!r}"
            )
