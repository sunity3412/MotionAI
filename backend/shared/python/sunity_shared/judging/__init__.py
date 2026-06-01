"""sunity_shared.judging — IPSF Code of Points 기반 객관 채점 baseline.

Plan 01-15 (JUDGE-DATA-01) 도입. NLF 갭 baseline 폐기 (Plan 01-12 verdict) 후
IPSF Code of Points 단일 기준으로 채점/게이트를 통합. 본 패키지는 데이터 스키마와
로더만 담당하며, 측정값 ↔ 임계값 비교 점수 계산은 Plan 01-13 책임.

핵심 원칙 (변경 금지):
  · 사람 점수 라벨링 영구 금지 (belle/강사/심사자 누구도 점수 ground truth 작성 불가).
    memory: analysis-objectivity-no-human-scores
  · 채점 baseline = IPSF Code of Points 단일 기준. KPSA 도 IPSF 따름.
    memory: judging-baseline-ipsf-code-of-points
  · 본 패키지가 다루는 belle 라벨링 = 객관 임계값 수치만
    (target angle / tolerance / deduction / minimum). 인용 출처(source_ref) 필수.
"""

from __future__ import annotations

from .geometric_criterion import GeometricCriterion
from .gemini_moment_extractor import (
    GeminiMomentExtractor,
    KeyMoment,
    assign_frame_indices,
)
from .loader import load_criteria, load_grouped_criteria

__all__ = (
    "GeometricCriterion",
    "GeminiMomentExtractor",
    "KeyMoment",
    "assign_frame_indices",
    "load_criteria",
    "load_grouped_criteria",
)
