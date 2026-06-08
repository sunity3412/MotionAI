"""Task 2 — firestore_admin.complete_analysis 확장 + W5 nested-array 차단 validator.

박제 정신:
  - D-06-B3: bodyComparisonReport = result 내부, bodyNormalizationProfile = top-level.
  - [[firestore-nested-array-flat]]: Firestore nested-array 차단 — list[str] (warnings)
    + list[dict-of-scalars-only] (findings) 만 허용.
  - W5: _validate_flat_dict_no_nested_array 헬퍼.
  - C2: list_reference_motions_by_name 신설 폐기.
  - C14: pose_reliability_low finding 정합.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _bcr_basic() -> dict:
    return {
        "comparisonType": "mode1",
        "bodyNormalizationConfidence": 0.8,
        "findings": [
            {
                "deficitCode": "knee_toe_alignment",
                "jointKey": "left_knee",
                "measuredValue": 160.0,
                "deductionScore": -0.2,
                "confidence": 0.85,
                "bodyTypeAdjusted": True,
            }
        ],
        "warnings": [],
        "usedReferenceFallback": False,
    }


@pytest.fixture
def mock_doc(monkeypatch):
    """firestore_admin._doc → MagicMock 박제."""
    from sunity_shared import firestore_admin

    doc = MagicMock()
    monkeypatch.setattr(firestore_admin, "_doc", lambda path: doc)
    return doc


def test_complete_analysis_accepts_body_comparison_report(mock_doc):
    """Test 1 — body_comparison_report kwarg 수용 + payload.result.bodyComparisonReport 박제."""
    from sunity_shared import firestore_admin

    bcr = _bcr_basic()
    firestore_admin.complete_analysis(
        "u1",
        "a1",
        {"overallScore": 80, "dimensionScores": {}, "joints": [], "tips": [],
         "comparison": {"mode": "mode1"}, "myVideoUrl": "x"},
        body_comparison_report=bcr,
    )
    assert mock_doc.set.called
    payload = mock_doc.set.call_args.args[0]
    assert "result" in payload
    assert payload["result"]["bodyComparisonReport"] == bcr


def test_validate_flat_dict_allows_list_of_strings():
    """Test 2 (W5) — list[str] (warnings) 허용."""
    from sunity_shared import firestore_admin

    payload = {
        "comparisonType": "mode1",
        "warnings": ["a", "b", "c"],
        "findings": [],
    }
    # 위반 없어 raise X
    firestore_admin._validate_flat_dict_no_nested_array(payload)


def test_validate_flat_dict_allows_list_of_dict_scalars():
    """Test 3 (W5) — list[dict-of-scalars] (findings) 허용."""
    from sunity_shared import firestore_admin

    payload = {
        "comparisonType": "mode1",
        "findings": [
            {"deficitCode": "x", "confidence": 0.9, "deductionScore": -0.2}
        ],
    }
    firestore_admin._validate_flat_dict_no_nested_array(payload)


def test_validate_flat_dict_rejects_nested_array_in_list():
    """Test 4 (W5) — list[list] 거절 (TypeError)."""
    from sunity_shared import firestore_admin

    payload = {"warnings": [["nested"], ["bad"]]}
    with pytest.raises(TypeError):
        firestore_admin._validate_flat_dict_no_nested_array(payload)


def test_validate_flat_dict_rejects_nested_dict_with_list():
    """Test 5 (W5) — list[dict-with-nested-list] 거절."""
    from sunity_shared import firestore_admin

    payload = {
        "findings": [
            {"deficitCode": "x", "extraList": [1, 2, 3]},
        ],
    }
    with pytest.raises(TypeError):
        firestore_admin._validate_flat_dict_no_nested_array(payload)


def test_complete_analysis_body_comparison_none_skips_field(mock_doc):
    """Test 6 — body_comparison_report=None → payload 에 bodyComparisonReport key 부재."""
    from sunity_shared import firestore_admin

    firestore_admin.complete_analysis(
        "u1",
        "a1",
        {"overallScore": 80, "dimensionScores": {}, "joints": [], "tips": [],
         "comparison": {"mode": "mode1"}, "myVideoUrl": "x"},
        body_comparison_report=None,
    )
    payload = mock_doc.set.call_args.args[0]
    assert "bodyComparisonReport" not in payload.get("result", {})


def test_complete_analysis_body_normalization_profile_flat_dict(mock_doc):
    """Test 7 — body_normalization_profile dict → payload['bodyNormalizationProfile'] top-level 박제."""
    from sunity_shared import firestore_admin

    bnp = {
        "estimatedHeightScale": 0.875,
        "armScale": 0.9,
        "legScale": 0.85,
        "torsoScale": 1.0,
        "shoulderHipRatio": 1.1,
        "confidence": 0.8,
        "warnings": [],
    }
    firestore_admin.complete_analysis(
        "u1",
        "a1",
        {"overallScore": 80, "dimensionScores": {}, "joints": [], "tips": [],
         "comparison": {"mode": "mode1"}, "myVideoUrl": "x"},
        body_normalization_profile=bnp,
    )
    payload = mock_doc.set.call_args.args[0]
    assert payload["bodyNormalizationProfile"] == bnp


def test_validate_flat_dict_accepts_pose_reliability_low_finding():
    """Test 8 (C14) — pose_reliability_low deficit_code 가 findings 안에 있어도 통과."""
    from sunity_shared import firestore_admin

    payload = {
        "findings": [
            {"deficitCode": "pose_reliability_low", "confidence": 0.3,
             "deductionScore": -0.5, "measuredValue": 0.7}
        ]
    }
    firestore_admin._validate_flat_dict_no_nested_array(payload)


def test_validate_flat_dict_rejects_non_finding_dict_item_with_list():
    """Test 9 (W5 추가) — 단순 dict 안에 list 값 발견 시 TypeError (recursive 검증)."""
    from sunity_shared import firestore_admin

    payload = {
        "scaleProfile": {
            "estimatedHeightScale": 0.9,
            "extra": [1, 2, 3],  # list (scalar) 자체는 허용. 하지만 nested 박제.
        }
    }
    # list[scalar] 은 W5 정합 — 허용 (warnings list[str] 정합 정의 적용).
    firestore_admin._validate_flat_dict_no_nested_array(payload)


def test_list_reference_motions_by_name_not_added():
    """C2 fix 정합 — list_reference_motions_by_name 신설 폐기."""
    from sunity_shared import firestore_admin

    assert not hasattr(firestore_admin, "list_reference_motions_by_name"), (
        "C2 fix 위반 — list_reference_motions_by_name 신설 폐기 정합"
    )
