"""Task 3 (C8 fix) — _dataclass_to_camel_case_dict 4-case 명세 단위 테스트.

박제 정신:
  C8 fix (2026-06-08 reviews) — 4 case 명시:
    Case 1: None → None
    Case 2: dataclass → asdict + snake→camel key 변환 + value 재귀
    Case 3: list → recurse map
    Case 4: dict → snake→camel key 변환 + value 재귀
    Case 5: Enum / scalar → str(value) / 그대로

BodyComparisonReport 의 중첩 ScaleProfile + list[BodyComparisonFinding] 까지 모두
camelCase 변환.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _app():
    import importlib

    sys.modules.pop("app", None)
    import app  # noqa: WPS433

    return importlib.reload(app)


def test_dataclass_to_camel_case_dict_handles_none():
    """Test 6 (C8 Case 1) — None → None."""
    app = _app()
    assert app._dataclass_to_camel_case_dict(None) is None


def test_dataclass_to_camel_case_dict_recurses_nested_dataclass():
    """Test 7 (C8 Case 2) — 중첩 dataclass 변환.

    BodyComparisonReport(scale_profile=ScaleProfile(...)) →
    {"comparisonType": "...", "scaleProfile": {"estimatedHeightScale": 1.0, ...}, ...}.
    """
    app = _app()
    from sunity_shared.analysis.body_normalizer import (
        BodyComparisonReport,
        ScaleProfile,
    )

    sp = ScaleProfile(
        estimated_height_scale=1.0,
        arm_scale=0.9,
        leg_scale=0.85,
        torso_scale=1.0,
        shoulder_hip_ratio=1.1,
        shoulder_hip_ratio_applied=True,
    )
    bcr = BodyComparisonReport(
        comparison_type="mode1",
        body_normalization_confidence=0.8,
        scale_profile=sp,
        findings=[],
        warnings=[],
        used_reference_fallback=False,
    )
    result = app._dataclass_to_camel_case_dict(bcr)
    assert isinstance(result, dict)
    assert result["comparisonType"] == "mode1"
    assert result["bodyNormalizationConfidence"] == 0.8
    assert result["scaleProfile"]["estimatedHeightScale"] == 1.0
    assert result["scaleProfile"]["shoulderHipRatioApplied"] is True
    assert result["usedReferenceFallback"] is False


def test_dataclass_to_camel_case_dict_maps_list_of_dataclasses():
    """Test 8 (C8 Case 3 + 2) — list[BodyComparisonFinding] 변환."""
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
    )
    bcr = BodyComparisonReport(
        comparison_type="mode1",
        body_normalization_confidence=0.7,
        scale_profile=None,
        findings=[finding],
        warnings=[],
        used_reference_fallback=False,
    )
    result = app._dataclass_to_camel_case_dict(bcr)
    assert isinstance(result["findings"], list)
    assert len(result["findings"]) == 1
    f0 = result["findings"][0]
    assert f0["deficitCode"] == "knee_toe_alignment"
    assert f0["jointKey"] == "left_knee"
    assert f0["measuredValue"] == 160.0
    assert f0["deductionScore"] == -0.2
    assert f0["bodyTypeAdjusted"] is True


def test_dataclass_to_camel_case_dict_serializes_enum_literal():
    """Test 9 (C8 Case 5) — Enum 도 str(value) 로 직렬화."""
    app = _app()
    from enum import Enum

    class _Color(Enum):
        RED = "red"
        BLUE = "blue"

    result = app._dataclass_to_camel_case_dict(_Color.RED)
    assert result == "red"


def test_dataclass_to_camel_case_dict_passthrough_scalar():
    """Default case — scalar 는 그대로 반환."""
    app = _app()
    assert app._dataclass_to_camel_case_dict(42) == 42
    assert app._dataclass_to_camel_case_dict("hi") == "hi"
    assert app._dataclass_to_camel_case_dict(True) is True


def test_dataclass_to_camel_case_dict_dict_input():
    """Case 4 — dict input 도 key snake→camel 변환."""
    app = _app()
    result = app._dataclass_to_camel_case_dict(
        {"snake_case_key": 1, "nested_dict": {"inner_key": "v"}}
    )
    assert result == {
        "snakeCaseKey": 1,
        "nestedDict": {"innerKey": "v"},
    }


def test_snake_to_camel_helper():
    """_snake_to_camel 단일 단어 / 다중 단어 정합."""
    app = _app()
    assert app._snake_to_camel("a") == "a"
    assert app._snake_to_camel("a_b") == "aB"
    assert app._snake_to_camel("body_normalization_confidence") == "bodyNormalizationConfidence"
    assert app._snake_to_camel("comparison_type") == "comparisonType"
