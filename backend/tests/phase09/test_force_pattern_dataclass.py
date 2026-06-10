"""Plan 09-01 Wave 0 — ForcePatternFinding / ForcePatternInference __post_init__
validator (D-09-U3 / T-09-V5 input validation).

iter-3 R2 (warnings empty-string reject) + iter-4 R1 (phase ∈ _MOTION_PHASES) +
iter-4 R2 (tuple reject, contract = list) + iter-5 정합.

per Plan 09-01 must_haves + RESEARCH §"Pattern 1".
"""

from __future__ import annotations

import dataclasses

import pytest

from sunity_shared.analysis.force_pattern import (
    ForcePatternFinding,
    ForcePatternInference,
)


def _kwargs(**overrides) -> dict:
    """ForcePatternFinding 기본 kwargs — overrides 로 한 필드만 변형."""
    base = dict(
        pattern="release",
        phase="lock",
        source_signal="axis_tilt",
        reason="raw shoulder_tilt above ipsf 20deg",
        interpretation="canned KO 본문",
        confidence=0.72,
        joint_hint="코어",
        warnings=[],
    )
    base.update(overrides)
    return base


# ── ForcePatternFinding __post_init__ ────────────────────────────────────


def test_invalid_pattern_enum_raises() -> None:
    with pytest.raises(ValueError, match="pattern"):
        ForcePatternFinding(**_kwargs(pattern="nonsense"))


def test_invalid_source_signal_raises() -> None:
    with pytest.raises(ValueError, match="source_signal"):
        ForcePatternFinding(**_kwargs(source_signal="zzz"))


def test_confidence_above_one_raises() -> None:
    with pytest.raises(ValueError, match="confidence"):
        ForcePatternFinding(**_kwargs(confidence=1.01))


def test_confidence_below_zero_raises() -> None:
    with pytest.raises(ValueError, match="confidence"):
        ForcePatternFinding(**_kwargs(confidence=-0.1))


def test_empty_interpretation_raises() -> None:
    with pytest.raises(ValueError, match="interpretation"):
        ForcePatternFinding(**_kwargs(interpretation=""))


def test_warnings_non_str_element_raises() -> None:
    """R6 — warnings element 가 str 아님 (예: int)."""
    with pytest.raises(ValueError, match="warnings"):
        ForcePatternFinding(**_kwargs(warnings=[1]))


def test_warnings_empty_string_element_raises() -> None:
    """R6 / R2 iter-3 — warnings element 가 empty str 박제 reject."""
    with pytest.raises(ValueError, match="warnings"):
        ForcePatternFinding(**_kwargs(warnings=[""]))


def test_joint_hint_non_str_raises() -> None:
    """R6 — joint_hint 가 str | None 외 박제 (int)."""
    with pytest.raises(ValueError, match="joint_hint"):
        ForcePatternFinding(**_kwargs(joint_hint=123))


def test_invalid_phase_raises() -> None:
    """R1 iter-4 — phase 가 _MOTION_PHASES 에 없음 (downstream KeyError 차단)."""
    with pytest.raises(ValueError, match="phase"):
        ForcePatternFinding(**_kwargs(phase="other"))


def test_warnings_tuple_raises() -> None:
    """R2 iter-4 — warnings 가 tuple 박제 reject (contract = list[str])."""
    with pytest.raises(ValueError, match="warnings"):
        ForcePatternFinding(**_kwargs(warnings=("x",)))


def test_valid_finding_constructs_and_is_frozen() -> None:
    """정상 박제 + frozen instance 검증."""
    finding = ForcePatternFinding(**_kwargs())
    assert finding.pattern == "release"
    assert finding.confidence == 0.72

    # frozen 검증 — 속성 set 시도 시 FrozenInstanceError.
    with pytest.raises(dataclasses.FrozenInstanceError):
        finding.confidence = 0.5  # type: ignore[misc]


# ── ForcePatternInference __post_init__ ──────────────────────────────────


def _valid_finding_obj() -> ForcePatternFinding:
    return ForcePatternFinding(**_kwargs())


def test_findings_length_over_three_raises() -> None:
    findings = [_valid_finding_obj()] * 4
    with pytest.raises(ValueError, match="findings"):
        ForcePatternInference(
            version="1.0",
            findings=findings,
            overall_confidence="low",
            mode_context="mode1",
            warnings=[],
        )


def test_invalid_mode_context_raises() -> None:
    with pytest.raises(ValueError, match="mode_context"):
        ForcePatternInference(
            version="1.0",
            findings=[],
            overall_confidence="low",
            mode_context="other",
            warnings=[],
        )


def test_version_empty_raises() -> None:
    """R6 — version 이 empty str 박제 reject."""
    with pytest.raises(ValueError, match="version"):
        ForcePatternInference(
            version="",
            findings=[],
            overall_confidence="low",
            mode_context="mode1",
            warnings=[],
        )


def test_findings_non_force_pattern_finding_raises() -> None:
    """R6 — findings element 가 ForcePatternFinding 인스턴스 아님 박제 reject."""
    with pytest.raises(ValueError, match="findings|ForcePatternFinding"):
        ForcePatternInference(
            version="1.0",
            findings=[object()],  # type: ignore[list-item]
            overall_confidence="low",
            mode_context="mode1",
            warnings=[],
        )


def test_inference_warnings_non_str_raises() -> None:
    """R6 — top-level warnings element 가 str 아님 박제 reject."""
    with pytest.raises(ValueError, match="warnings"):
        ForcePatternInference(
            version="1.0",
            findings=[],
            overall_confidence="low",
            mode_context="mode1",
            warnings=[1],  # type: ignore[list-item]
        )


def test_inference_warnings_empty_string_raises() -> None:
    """R2 iter-3 — top-level warnings empty str 박제 reject."""
    with pytest.raises(ValueError, match="warnings"):
        ForcePatternInference(
            version="1.0",
            findings=[],
            overall_confidence="low",
            mode_context="mode1",
            warnings=[""],
        )


def test_inference_warnings_tuple_raises() -> None:
    """R2 iter-4 — top-level warnings 가 tuple 박제 reject."""
    with pytest.raises(ValueError, match="warnings"):
        ForcePatternInference(
            version="1.0",
            findings=[],
            overall_confidence="low",
            mode_context="mode1",
            warnings=("x",),  # type: ignore[arg-type]
        )


def test_inference_findings_tuple_raises() -> None:
    """R2 iter-4 — findings 가 tuple 박제 reject (contract = list[ForcePatternFinding])."""
    with pytest.raises(ValueError, match="findings"):
        ForcePatternInference(
            version="1.0",
            findings=(_valid_finding_obj(),),  # type: ignore[arg-type]
            overall_confidence="low",
            mode_context="mode1",
            warnings=[],
        )


def test_valid_inference_constructs() -> None:
    """정상 박제 — Wave 1 본체 함수가 산출할 canonical shape."""
    inference = ForcePatternInference(
        version="1.0",
        findings=[_valid_finding_obj()],
        overall_confidence="medium",
        mode_context="mode1",
        warnings=[],
    )
    assert inference.version == "1.0"
    assert len(inference.findings) == 1
    assert inference.mode_context == "mode1"
