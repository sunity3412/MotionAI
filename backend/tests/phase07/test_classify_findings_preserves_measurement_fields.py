"""Plan 07-02 INF-01 fix — primary behavioral safety property.

dataclasses.replace 부재 AST grep (test_classify_findings.py::
test_classify_findings_uses_replace_pattern_zero) 은 secondary convention 검증.
본 test 가 측정 필드 보존의 actual contract 검증.

박제 정신:
  - 6 원본 측정 필드 (deficit_code / joint_key / measured_value /
    deduction_score / confidence / body_type_adjusted) 가 input → output
    정확 일치 (immutable preservation).
  - 신규 4 필드 (category / phase / body_type_interpretation /
    recommendation) 만 새로 박제.
  - output 은 new object (id 다름 — dataclasses.replace 우회 X 의 behavioral 증명).
"""

from __future__ import annotations

from sunity_shared.analysis.body_normalizer import (
    BodyComparisonFinding,
    classify_findings,
)


def test_classify_findings_preserves_measurement_fields() -> None:
    """INF-01 fix — primary behavioral safety property.

    classify_findings 가 6 원본 측정 필드를 변형 없이 보존하고,
    신규 4 필드만 새로 박제하는지 검증. AST grep 은 secondary convention —
    본 test 가 actual contract.
    """
    input_f = BodyComparisonFinding(
        deficit_code="knee_toe_alignment",
        joint_key="left_knee",
        measured_value=120.5,
        deduction_score=-0.2,
        confidence=0.85,
        body_type_adjusted=True,
        category="uncertain",  # Plan 01 WR-01 placeholder
    )
    classified, _, _, _ = classify_findings(
        [input_f],
        body_normalization_confidence=0.85,
        comparison_type="mode1",
    )
    out = classified[0]

    # 6 원본 측정 필드 정확 일치 — immutable preservation
    assert out.deficit_code == input_f.deficit_code
    assert out.joint_key == input_f.joint_key
    assert out.measured_value == input_f.measured_value
    assert out.deduction_score == input_f.deduction_score
    assert out.confidence == input_f.confidence
    assert out.body_type_adjusted == input_f.body_type_adjusted

    # 신규 4 필드 박제 확인
    assert out.category in ("body_type_allowed", "needs_adjustment", "uncertain")
    assert out.phase == "hold"
    # mode1 정상 path → body_type_interpretation non-None (canned 카피 lookup)
    assert out.body_type_interpretation is not None
    assert out.recommendation is not None

    # output 은 new object (dataclasses.replace 우회 X 의 behavioral 증명)
    assert id(out) != id(input_f)
