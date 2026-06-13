"""Phase 4 Wave 1 — POSE-03 R2 fix: SynthesisResult status 4-way enum 분기.

R2 fix — all-zero array sentinel 폐기. (zeros, zeros) 반환 영구 금지.
SynthesisResult(status='applied' / 'partial' / 'skipped' / 'failed') 만 허용.

본 테스트는 Wave 1 (Plan 04-01 Task 1) gate — dataclass 가 박힌 직후 GREEN
이어야 한다. Wave 0 시점에서 dataclass 미박제 → ImportError → pytest.skip.
"""

from __future__ import annotations

import numpy as np
import pytest


def _load_dataclass():
    try:
        from sunity_shared.analysis.synthesis.interfaces import SynthesisResult
    except ImportError:
        pytest.skip(
            "synthesis.interfaces.SynthesisResult — Wave 1 (04-01) 미박제"
        )
    return SynthesisResult


def test_synthesis_result_failed_has_none_joints() -> None:
    """status='failed' → joints/confidence 반드시 None (R2 fix — zeros sentinel
    영구 폐기)."""
    SynthesisResult = _load_dataclass()
    result = SynthesisResult(
        status="failed",
        warnings=("ai_synthesis_failed",),
    )
    assert result.status == "failed"
    assert result.joints is None, "R2 fix — failed 시 joints 는 반드시 None"
    assert result.confidence is None
    assert "ai_synthesis_failed" in result.warnings


def test_synthesis_result_skipped_no_warning_required() -> None:
    """status='skipped' → warnings 비울 수 있어야 함 (SYNTHESIS_ENABLED OFF /
    occlusion mask 비어있음 등 normal skip path)."""
    SynthesisResult = _load_dataclass()
    result = SynthesisResult(status="skipped")
    assert result.status == "skipped"
    assert result.warnings == ()


def test_synthesis_result_skipped_with_g4_guard_warning() -> None:
    """is_reference=True G4 가드 path 에서는 warnings=('g4_reference_guard',)
    를 갖고 skipped 로 반환된다 (raw reason — public surface X)."""
    SynthesisResult = _load_dataclass()
    result = SynthesisResult(
        status="skipped",
        warnings=("g4_reference_guard",),
    )
    assert result.status == "skipped"
    assert "g4_reference_guard" in result.warnings


def test_synthesis_result_applied_has_non_none_joints() -> None:
    """status='applied' → joints/confidence 모두 non-None ndarray."""
    SynthesisResult = _load_dataclass()
    joints = np.zeros((10, 17, 3), dtype=np.float32)
    conf = np.zeros((10, 17), dtype=np.float32)
    result = SynthesisResult(
        status="applied",
        joints=joints,
        confidence=conf,
    )
    assert result.status == "applied"
    assert result.joints is not None
    assert result.confidence is not None


def test_synthesis_result_partial_has_joints() -> None:
    """status='partial' → joints/confidence non-None (일부 관절 indeterminate
    영역은 confidence=0 으로 박힘 — merge_with_temporal 가 자동 제거)."""
    SynthesisResult = _load_dataclass()
    joints = np.zeros((10, 17, 3), dtype=np.float32)
    conf = np.zeros((10, 17), dtype=np.float32)
    conf[:, 5] = 0.8  # left_shoulder 만 정상 응답.
    result = SynthesisResult(
        status="partial",
        joints=joints,
        confidence=conf,
        warnings=("ai_synthesis_partial",),
    )
    assert result.status == "partial"
    assert result.joints is not None
    assert result.confidence is not None
    assert "ai_synthesis_partial" in result.warnings


def test_synthesis_result_is_frozen() -> None:
    """@dataclass(frozen=True) — 변경 시도 시 FrozenInstanceError."""
    SynthesisResult = _load_dataclass()
    from dataclasses import FrozenInstanceError

    result = SynthesisResult(status="skipped")
    with pytest.raises(FrozenInstanceError):
        result.status = "applied"  # type: ignore[misc]
