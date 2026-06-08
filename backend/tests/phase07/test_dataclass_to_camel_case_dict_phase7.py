"""Plan 07-02 Task 2 — Phase 7 신설 4+3 필드 _dataclass_to_camel_case_dict 자동 변환.

Phase 6 C8 5-case helper 가 dataclass.asdict + snake→camel + 재귀 적용 — 코드 변경
0 으로 신설 필드 자동 처리. 본 test 가 회귀 차단.

Phase 6 패턴 (test_dataclass_to_camel_case_dict.py) 미러:
  - importlib reload pipeline.app 모듈
  - sys.modules.pop("app", None) → reimport
  - app._dataclass_to_camel_case_dict 직접 호출

검증 (1 test):
  test_phase7_new_fields_camel_case_automatic — BodyComparisonReport (with 신설 7 필드)
  → dict[str, Any] 에 doNotOverCorrect / recommendedFocus / recommendedFocusFallback
  + findings[0] 의 category / phase / bodyTypeInterpretation / recommendation 정상 변환.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _app():
    """Phase 6 패턴 정합 — importlib reload 로 신선한 module 로딩."""
    import importlib

    sys.modules.pop("app", None)
    import app  # noqa: WPS433

    return importlib.reload(app)


def test_phase7_new_fields_camel_case_automatic() -> None:
    """Phase 6 C8 helper 가 신설 7 필드 자동 camelCase 변환 — 코드 변경 0.

    Plan 02 Task 2 acceptance criterion:
      - doNotOverCorrect (BodyComparisonReport list[str])
      - recommendedFocus (BodyComparisonReport list[str])
      - recommendedFocusFallback (BodyComparisonReport str | None) — WR-03 fix
      - findings[0].category (BodyComparisonFinding Literal)
      - findings[0].phase (BodyComparisonFinding str | None)
      - findings[0].bodyTypeInterpretation (BodyComparisonFinding str | None)
      - findings[0].recommendation (BodyComparisonFinding str | None)
    """
    app = _app()
    from sunity_shared.analysis.body_normalizer import (
        BodyComparisonFinding,
        BodyComparisonReport,
    )

    finding = BodyComparisonFinding(
        deficit_code="knee_toe_alignment",
        joint_key="left_knee",
        measured_value=160.0,
        deduction_score=-0.2,
        confidence=0.85,
        body_type_adjusted=True,
        # Phase 7 신설 4 필드
        category="body_type_allowed",
        phase="hold",
        body_type_interpretation="다리 길이 비율 차이로 무릎-발끝 정렬에 작은 차이가 보일 수 있어요.",
        recommendation="정은지 선수 영상 기준으로 보면 지금 자세는 체형 범위 안에서 자연스러워 보이네요.",
    )
    report = BodyComparisonReport(
        comparison_type="mode1",
        body_normalization_confidence=0.85,
        scale_profile=None,
        findings=[finding],
        warnings=[],
        used_reference_fallback=False,
        # Phase 7 신설 2+1 필드
        do_not_over_correct=[
            "정은지 선수 영상 기준으로 보면 지금 자세는 체형 범위 안에서 자연스러워 보이네요.",
        ],
        recommended_focus=[],
        recommended_focus_fallback=(
            "현재 영상에서 즉시 보정할 항목이 명확히 보이지 않아요. "
            "강사와 함께 다음 단계를 정해보세요."
        ),
    )
    result = app._dataclass_to_camel_case_dict(report)

    # BodyComparisonReport 의 신설 3 필드 — 자동 camelCase
    assert "doNotOverCorrect" in result
    assert isinstance(result["doNotOverCorrect"], list)
    assert result["doNotOverCorrect"][0].startswith("정은지 선수 영상 기준으로 보면")

    assert "recommendedFocus" in result
    assert result["recommendedFocus"] == []

    assert "recommendedFocusFallback" in result
    assert result["recommendedFocusFallback"] is not None
    assert "강사" in result["recommendedFocusFallback"]

    # BodyComparisonFinding 신설 4 필드 — 자동 camelCase
    f0 = result["findings"][0]
    assert f0["category"] == "body_type_allowed"
    assert f0["phase"] == "hold"
    assert "bodyTypeInterpretation" in f0
    assert "다리 길이" in f0["bodyTypeInterpretation"]
    assert "recommendation" in f0
    assert f0["recommendation"].startswith("정은지 선수 영상 기준으로 보면")


def test_phase7_fallback_none_round_trips() -> None:
    """recommended_focus_fallback=None 케이스도 자동 변환 — None 통과."""
    app = _app()
    from sunity_shared.analysis.body_normalizer import BodyComparisonReport

    report = BodyComparisonReport(
        comparison_type="mode1",
        body_normalization_confidence=0.85,
        scale_profile=None,
        findings=[],
        warnings=[],
        used_reference_fallback=False,
        do_not_over_correct=[],
        recommended_focus=["x"],
        recommended_focus_fallback=None,
    )
    result = app._dataclass_to_camel_case_dict(report)
    assert result["recommendedFocusFallback"] is None
