"""Plan 08.1-00 Wave 0 Task 2 — _validate_force_signals_report axis dict 검증.

본 plan 의 6 필드 axisMetrics dict + legacy 5 필드 dict (Phase 8 박제 doc) 둘 다
PASS (scalar fields are silently passed by the scoped validator). nested list/dict
in metric → ValueError (firestore-nested-array-flat invariant).

backwards-compat 근거: D-01 정합 — 기존 Firestore docs 의 distance 필드 = 무시
(read-side 가 안 읽음, backfill X). validator 변경 0 — scalar 필드는 자동
backwards-compat. legacy 5 필드 dict 는 read 시 frontend normalize 가 6 필드만
picks up (TS interface 정합 — 미존재 필드는 silently drop).

per Plan 08.1-00 must_haves.
"""

from __future__ import annotations

import pytest

from sunity_shared.firestore_admin import _validate_force_signals_report


# ── 1. 새 6 필드 PASS ─────────────────────────────────────────────────────


def test_axis_metric_six_fields_pass() -> None:
    """본 plan 의 6 필드 axisMetrics dict PASS — validator 변경 0 정합."""
    payload = {
        "version": "1.0",
        "overallConfidence": "low",
        "warnings": ["axis_metric_transitional"],
        "phaseBoundaries": [],
        "axisMetrics": [
            {
                "phase": "hold",
                "shoulderTilt": None,
                "hipTilt": None,
                "severity": "low",
                "confidence": "low",
                "warnings": ["phase_8_1_wave_0_transitional"],
            }
        ],
        "stabilityMetrics": [],
        "contactMetrics": [],
    }
    # 위반 없음 — exception X 강제.
    _validate_force_signals_report(payload)


# ── 2. warnings list[str] PASS (화이트리스트) ────────────────────────────


def test_axis_metric_warnings_list_str_pass() -> None:
    """warnings = ['tilt_unavailable'] → no exception (list[str] 화이트리스트)."""
    payload = {
        "version": "1.0",
        "overallConfidence": "low",
        "warnings": [],
        "phaseBoundaries": [],
        "axisMetrics": [
            {
                "phase": "hold",
                "shoulderTilt": 12.5,
                "hipTilt": 8.3,
                "severity": "medium",
                "confidence": "medium",
                "warnings": ["tilt_unavailable"],
            }
        ],
        "stabilityMetrics": [],
        "contactMetrics": [],
    }
    _validate_force_signals_report(payload)


# ── 3. legacy 5 필드 backwards-compat PASS ────────────────────────────────


def test_axis_metric_legacy_distance_field_backwards_compat() -> None:
    """legacy Phase 8 doc 의 5 distance 필드 = scalar → 자동 backwards-compat PASS.

    legacy doc 의 pelvisDistanceFromPoleAxis / chestDistanceFromPoleAxis /
    coordinateSpace / scaleDenominator / deviationDirection 5 필드 가 dict 안에
    들어 있어도 scalar (str/float/None) 이므로 validator 가 silently 통과. read 시
    frontend normalize 가 6 필드만 picks up.
    """
    payload = {
        "version": "1.0",
        "overallConfidence": "low",
        "warnings": [],
        "phaseBoundaries": [],
        "axisMetrics": [
            {
                # 새 6 필드.
                "phase": "hold",
                "shoulderTilt": 12.5,
                "hipTilt": 8.3,
                "severity": "low",
                "confidence": "low",
                "warnings": ["pole_line_missing"],
                # legacy 5 필드 (Phase 8 박제 doc).
                "pelvisDistanceFromPoleAxis": 3.05,
                "chestDistanceFromPoleAxis": 3.10,
                "coordinateSpace": "pole_aligned",
                "scaleDenominator": "observed_torso_length",
                "deviationDirection": "outward",
            }
        ],
        "stabilityMetrics": [],
        "contactMetrics": [],
    }
    # 위반 없음 — scalar 필드는 자동 backwards-compat.
    _validate_force_signals_report(payload)


# ── 4. nested list inside metric dict → reject ───────────────────────────


def test_axis_metric_nested_list_rejects() -> None:
    """axisMetrics[0].weird = [[1,2],[3,4]] 박제 ValueError raise.

    화이트리스트 미포함 key 의 list 박제 reject — Firestore nested array 보호.
    """
    payload = {
        "version": "1.0",
        "overallConfidence": "low",
        "warnings": [],
        "phaseBoundaries": [],
        "axisMetrics": [
            {
                "phase": "hold",
                "shoulderTilt": None,
                "hipTilt": None,
                "severity": "low",
                "confidence": "low",
                "warnings": [],
                "weird": [[1, 2], [3, 4]],  # 화이트리스트 미포함 + list[list]
            }
        ],
        "stabilityMetrics": [],
        "contactMetrics": [],
    }
    with pytest.raises(ValueError):
        _validate_force_signals_report(payload)


# ── 5. nested dict inside metric dict → reject ───────────────────────────


def test_axis_metric_nested_dict_rejects() -> None:
    """axisMetrics[0].nested = {a: 1} 박제 ValueError raise.

    metric dict 안 nested dict 박제 reject — firestore-nested-array-flat invariant.
    """
    payload = {
        "version": "1.0",
        "overallConfidence": "low",
        "warnings": [],
        "phaseBoundaries": [],
        "axisMetrics": [
            {
                "phase": "hold",
                "shoulderTilt": None,
                "hipTilt": None,
                "severity": "low",
                "confidence": "low",
                "warnings": [],
                "nested": {"a": 1},  # nested dict 박제 영구 금지.
            }
        ],
        "stabilityMetrics": [],
        "contactMetrics": [],
    }
    with pytest.raises((ValueError, TypeError)):
        _validate_force_signals_report(payload)
