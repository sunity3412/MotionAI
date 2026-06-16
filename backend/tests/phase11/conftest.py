"""Phase 11 Wave 0 — shared golden fixtures.

실제 측정값을 가진 `ForcePatternFinding` 1개 + `BodyComparisonFinding` 1개를
**실 생성자 시그니처**로 빌드한다 (임의 dict mock 아님 — Wave 1 builder 가 받을
실 finding 타입과 동일). builder/resolver 가 이 finding 들을 입력으로 받아
CoachCommentHook 로 변환할 때 Wave 0 테스트가 RED, Wave 1 구현이 GREEN.
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.body_normalizer import BodyComparisonFinding
from sunity_shared.analysis.force_pattern import ForcePatternFinding


@pytest.fixture
def golden_force_finding() -> ForcePatternFinding:
    """force_pattern.py 실 생성자 — pull pattern / hold phase / axis_tilt signal.

    interpretation 은 '가능성' canned KO (D-09-D3 정합), reason 은 EN 1 sentence
    (Phase 11 LLM 번역 입력 source).
    """
    return ForcePatternFinding(
        pattern="pull",
        phase="hold",
        source_signal="axis_tilt",
        reason="Pelvis tilt suggests latissimus engagement during the hold.",
        interpretation="홀드 구간에서 광배근으로 당기는 힘이 부족할 가능성이 있어요.",
        confidence=0.62,
        joint_hint="광배",
        warnings=[],
    )


@pytest.fixture
def golden_body_finding() -> BodyComparisonFinding:
    """body_normalizer.py 실 생성자 — needs_adjustment 분류 IPSF deficit.

    body_type_interpretation 은 KO canned (Phase 11 LLM 번역 입력 source).
    """
    return BodyComparisonFinding(
        deficit_code="line_not_straight",
        joint_key="left_knee",
        measured_value=23.0,
        deduction_score=-0.5,
        confidence=0.7,
        body_type_adjusted=True,
        category="needs_adjustment",
        phase="hold",
        body_type_interpretation="무릎 라인이 곧게 펴지지 않을 가능성이 있어요.",
        recommendation="무릎을 끝까지 펴는 연습을 해보세요.",
    )
