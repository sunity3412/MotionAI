"""Plan 08-03 Task 1 — Firestore scoped validator + complete_analysis kwarg test.

REVIEWS Cycle 2 §3 NEW HIGH #3 차단:
  · `_validate_dict_only_scalars` 본체 변경 영구 0 ([[firestore-nested-array-flat]]
    project-wide 보존).
  · 신설 scoped validator `_validate_force_signals_report` — `forceSignalsReport`
    안 metric dict 의 `warnings` / `unstableBodyParts` list[str] 박제만 허용.
    다른 list[scalar] 박제 시 ValueError.
  · complete_analysis(force_signals_report=...) kwarg 박제 — body_comparison_report
    의 strict validator 경로 박제 X.

5 신설 test:
  1. test_validate_force_signals_report_passes_warnings_list_of_str
  2. test_validate_force_signals_report_rejects_nested_list_inside_metric_dict
  3. test_validate_dict_only_scalars_remains_strict_for_body_comparison_report
  4. test_complete_analysis_uses_scoped_validator_only_for_force_signals
  5. test_camel_case_conversion_force_signals_report
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sunity_shared.firestore_admin import (
    _validate_dict_only_scalars,
    _validate_force_signals_report,
)


# ── 1. force_signals scoped validator — list[str] warnings PASS ────────────


def test_validate_force_signals_report_passes_warnings_list_of_str():
    """forceSignalsReport.axisMetrics[0].warnings = ['pole_line_missing'] 박제 PASS.

    metric dict 의 화이트리스트 key (warnings, unstableBodyParts) 만 list[str] 박제 허용.
    """
    payload = {
        "version": "1.0",
        "overallConfidence": "medium",
        "warnings": ["fps_normalization_applied", "preflight_gate_pending"],
        "phaseBoundaries": [
            {
                "phase": "entry",
                "startFrameIdx": 0,
                "endFrameIdx": 12,
                "startMs": 0,
                "endMs": 1333,
                "confidence": "low",
                "source": "heuristic",
                "preflightLabelGatePassed": None,
            }
        ],
        "axisMetrics": [
            {
                "phase": "entry",
                "pelvisDistanceFromPoleAxis": None,
                "warnings": ["pole_line_missing"],
            }
        ],
        "stabilityMetrics": [
            {
                "phase": "entry",
                "jitterScore": 5.0,
                "jerkScore": 1000.0,
                "jerkUnit": "deg_per_sec_cubed",
                "unstableBodyParts": ["left_knee", "right_knee"],
                "warnings": [],
            }
        ],
        "contactMetrics": [
            {
                "phase": "entry",
                "contactPoint": "left_hand",
                "measurementKind": "keypoint",
                "warnings": ["contact_evidence_only"],
            }
        ],
    }
    # 위반 없음 — exception X 강제.
    _validate_force_signals_report(payload)


# ── 2. nested list inside metric dict — reject ─────────────────────────────


def test_validate_force_signals_report_rejects_nested_list_inside_metric_dict():
    """forceSignalsReport.axisMetrics[0].weird = [[1,2],[3,4]] 박제 ValueError raise.

    화이트리스트 미포함 key 의 list 박제 reject — Firestore nested array 보호.
    """
    payload = {
        "version": "1.0",
        "overallConfidence": "low",
        "warnings": [],
        "phaseBoundaries": [],
        "axisMetrics": [
            {
                "phase": "entry",
                "weird": [[1, 2], [3, 4]],  # 화이트리스트 미포함 + list[list]
            }
        ],
        "stabilityMetrics": [],
        "contactMetrics": [],
    }
    with pytest.raises(ValueError, match="not in force_signals whitelist"):
        _validate_force_signals_report(payload)


# ── 3. `_validate_dict_only_scalars` 본체 변경 영구 0 박제 (Cycle 2 NEW HIGH #3) ──


def test_validate_dict_only_scalars_remains_strict_for_body_comparison_report():
    """REVIEWS Cycle 2 §3 NEW HIGH #3 차단 — `_validate_dict_only_scalars` 본체
    변경 영구 0 박제 ([[firestore-nested-array-flat]] project-wide 보존).

    bodyComparisonReport 안 list[str] 박제 시도 → strict reject (TypeError) 박제.
    body_comparison_report path 박제 회귀 0.
    """
    # bodyComparisonReport.findings[0] 안 list[str] 박제 시도 — strict reject 강제.
    finding_with_list = {
        "jointKey": "left_knee",
        "warnings": ["some_warning"],  # list[str] 박제 = nested 박제 영구 금지.
    }
    with pytest.raises(TypeError, match="list-of-dict entry 안에서는 nested 금지"):
        _validate_dict_only_scalars(
            finding_with_list, path="bodyComparisonReport.findings[0]"
        )


# ── 4. complete_analysis 박제 scoped validator 만 호출 + strict 미호출 ──────


def test_complete_analysis_uses_scoped_validator_only_for_force_signals():
    """complete_analysis(force_signals_report=...) 박제 호출 시
    `_validate_force_signals_report` 박제 호출 + `_validate_dict_only_scalars` 박제
    호출 X (mock 박제 검증).

    REVIEWS Cycle 2 §3 NEW HIGH #3 정합 — 다른 path 박제 strict 유지.
    """
    from sunity_shared import firestore_admin

    force_signals_payload = {
        "version": "1.0",
        "overallConfidence": "low",
        "warnings": [],
        "phaseBoundaries": [],
        "axisMetrics": [],
        "stabilityMetrics": [],
        "contactMetrics": [],
    }

    with patch.object(
        firestore_admin, "_doc"
    ) as mock_doc, patch.object(
        firestore_admin, "_validate_force_signals_report"
    ) as mock_scoped, patch.object(
        firestore_admin, "_validate_dict_only_scalars"
    ) as mock_strict, patch.object(
        firestore_admin, "_validate_flat_dict_no_nested_array"
    ) as mock_flat:
        mock_doc.return_value.set = MagicMock()
        firestore_admin.complete_analysis(
            uid="u",
            analysis_id="a",
            result={},
            force_signals_report=force_signals_payload,
        )
        # scoped validator 박제 호출 1회 강제.
        assert mock_scoped.call_count == 1, (
            f"scoped validator 박제 호출 1회 강제 — call_count={mock_scoped.call_count}"
        )
        # strict validator (_validate_dict_only_scalars) 박제 호출 X 강제.
        assert mock_strict.call_count == 0, (
            f"_validate_dict_only_scalars 박제 호출 영구 X — "
            f"call_count={mock_strict.call_count}"
        )
        # _validate_flat_dict_no_nested_array 박제 호출 X (force_signals 박제 path 외 미사용).
        assert mock_flat.call_count == 0, (
            f"_validate_flat_dict_no_nested_array 박제 force_signals 호출 X — "
            f"call_count={mock_flat.call_count}"
        )


def test_complete_analysis_body_comparison_report_still_uses_strict_validator():
    """body_comparison_report path 박제 _validate_flat_dict_no_nested_array 박제
    호출 박제 회귀 0 — Phase 6 박제 정합 유지.
    """
    from sunity_shared import firestore_admin

    body_payload = {
        "version": "1.0",
        "warnings": ["fallback_reference_not_found"],
        "findings": [],
    }
    with patch.object(
        firestore_admin, "_doc"
    ) as mock_doc, patch.object(
        firestore_admin, "_validate_flat_dict_no_nested_array"
    ) as mock_flat, patch.object(
        firestore_admin, "_validate_force_signals_report"
    ) as mock_scoped:
        mock_doc.return_value.set = MagicMock()
        firestore_admin.complete_analysis(
            uid="u",
            analysis_id="a",
            result={},
            body_comparison_report=body_payload,
        )
        # body_comparison_report path 박제 strict validator 박제 호출 1회 강제 (회귀 0).
        assert mock_flat.call_count == 1, (
            f"body_comparison_report 박제 _validate_flat_dict_no_nested_array 박제 "
            f"호출 1회 강제 — call_count={mock_flat.call_count}"
        )
        # scoped validator 박제 호출 X (force_signals 박제 path 박제 미사용).
        assert mock_scoped.call_count == 0


# ── 5. camelCase 변환 — _dataclass_to_camel_case_dict 박제 정합 ─────────────


def test_camel_case_conversion_force_signals_report():
    """ForceSignalsReport dataclass → camelCase dict 박제 변환 정합 검증.

    pipeline._dataclass_to_camel_case_dict 박제 helper 사용:
      phase_boundaries → phaseBoundaries
      axis_metrics → axisMetrics
      jerk_unit → jerkUnit
      measurement_kind → measurementKind
      preflight_label_gate_passed → preflightLabelGatePassed
    """
    # pipeline app import — _dataclass_to_camel_case_dict 박제 위치.
    import sys
    from pathlib import Path

    pipeline_dir = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
    if str(pipeline_dir) not in sys.path:
        sys.path.insert(0, str(pipeline_dir))
    sys.modules.pop("app", None)
    import app as pipeline_app  # noqa: WPS433
    import importlib

    pipeline_app = importlib.reload(pipeline_app)

    from sunity_shared.analysis.force_signals import (
        ForceSignalsReport,
        PhaseBoundary,
        StabilityMetric,
    )

    report = ForceSignalsReport(
        version="1.0",
        overall_confidence="low",
        warnings=["fps_normalization_applied"],
        phase_boundaries=[
            PhaseBoundary(
                phase="entry",
                start_frame_idx=0,
                end_frame_idx=12,
                start_ms=0,
                end_ms=1333,
                confidence="low",
                source="heuristic",
                preflight_label_gate_passed=None,
            ),
        ],
        axis_metrics=[],
        stability_metrics=[
            StabilityMetric(
                phase="entry",
                jitter_score=5.0,
                jerk_score=1000.0,
                jerk_unit="deg_per_sec_cubed",
            ),
        ],
        contact_metrics=[],
    )
    result = pipeline_app._dataclass_to_camel_case_dict(report)

    assert "phaseBoundaries" in result
    assert "axisMetrics" in result
    assert "stabilityMetrics" in result
    assert "contactMetrics" in result
    assert "overallConfidence" in result
    pb = result["phaseBoundaries"][0]
    assert "startFrameIdx" in pb
    assert "preflightLabelGatePassed" in pb
    sm = result["stabilityMetrics"][0]
    assert "jerkUnit" in sm
    assert sm["jerkUnit"] == "deg_per_sec_cubed"
