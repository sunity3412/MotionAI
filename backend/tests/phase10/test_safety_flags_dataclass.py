"""Phase 10 Wave 0 — SafetyFlag frozen dataclass + enum guard 검증.

phase09/test_force_pattern_dataclass.py 의 `_kwargs` factory + pytest.raises 패턴
미러. 본 테스트는 stub 위에서 즉시 GREEN (dataclass 구성 + 3 enum-violation).

per Plan 10-01 Task 1 + RESEARCH §"Pattern 1".
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.safety_flags import (
    SafetyFlag,
    compute_safety_flags,
)


def _kwargs(**overrides) -> dict:
    """SafetyFlag 기본 kwargs — overrides 로 한 필드만 변형."""
    base = dict(
        flag_type="trunk_hyperextension",
        body_region="허리",
        severity="medium",
        posture_condition="trunk_femur_angle reverse-bend in hold window",
        control_loss_signal="left_hip instability medium in hold phase",
        confidence="low",
        mode_scope="both",
    )
    base.update(overrides)
    return base


# ── 정상 구성 ──────────────────────────────────────────────────────────────


def test_constructs_with_valid_fields() -> None:
    flag = SafetyFlag(**_kwargs())
    assert flag.flag_type == "trunk_hyperextension"
    assert flag.body_region == "허리"
    assert flag.severity == "medium"
    assert flag.confidence == "low"
    assert flag.mode_scope == "both"


def test_is_frozen() -> None:
    flag = SafetyFlag(**_kwargs())
    with pytest.raises(Exception):
        flag.severity = "high"  # type: ignore[misc]


# ── __post_init__ enum 검증 ─────────────────────────────────────────────────


def test_invalid_flag_type_raises() -> None:
    with pytest.raises(ValueError, match="flag_type"):
        SafetyFlag(**_kwargs(flag_type="nonsense"))


def test_invalid_severity_raises() -> None:
    with pytest.raises(ValueError, match="severity"):
        SafetyFlag(**_kwargs(severity="extreme"))


def test_invalid_mode_scope_raises() -> None:
    with pytest.raises(ValueError, match="mode_scope"):
        SafetyFlag(**_kwargs(mode_scope="mode3_only"))


def test_invalid_confidence_raises() -> None:
    with pytest.raises(ValueError, match="confidence"):
        SafetyFlag(**_kwargs(confidence="certain"))


# ── compute_safety_flags stub ───────────────────────────────────────────────


def test_compute_safety_flags_stub_returns_list() -> None:
    out = compute_safety_flags(
        angles=None,
        keypoints_4ch=None,
        force_signals_report=None,
        dimension_scores=None,
        reference_angles=None,
        experience=None,
        reference_level=None,
        mode="mode1",
        profile=None,
    )
    assert out == []
    assert isinstance(out, list)
