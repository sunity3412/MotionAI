"""Phase 4 Wave 0 — POSE-03-f: G4 guard (is_reference=True → 합성 skip).

G4 = reference 영상 (정은지 모션 등록) 시 occlusion 합성 비활성화.
이유: reference 는 정확한 ground truth 가 필요한데 Gemini hallucinated
joints 가 섞이면 평가 기준 자체가 오염된다.

R2 fix — None 이 아니라 SynthesisResult(status="skipped",
warnings=("g4_reference_guard",)) 를 반환해야 한다 (HIGH-2 — None 분기
폐기 + status="skipped" enum 분기로 통일).

Wave 0 시점에서 _call_synthesis_adapter 미박제 → ImportError → pytest.skip.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _load_wrapper_and_result():
    """Wave 1 박제 후 wrapper + SynthesisResult."""
    try:
        from sunity_shared.analysis.synthesis.interfaces import SynthesisResult
    except ImportError:
        pytest.skip(
            "synthesis.interfaces.SynthesisResult — Wave 1 (04-01) 미박제"
        )

    wrapper = None
    try:
        from functions.pipeline.app import _call_synthesis_adapter as wrapper
    except ImportError:
        pass
    if wrapper is None:
        try:
            from sunity_shared.analysis.synthesis import (
                call_synthesis_adapter as wrapper,
            )
        except ImportError:
            pytest.skip(
                "_call_synthesis_adapter — Wave 1 (04-01 Task 2) 미박제"
            )
    return wrapper, SynthesisResult


def test_g4_guard_blocks_synthesis_for_reference() -> None:
    """is_reference=True → SynthesisResult(status='skipped',
    warnings=('g4_reference_guard',)). adapter.synthesize_occluded_joints 는
    호출되지 않아야 함."""
    wrapper, SynthesisResult = _load_wrapper_and_result()

    adapter = MagicMock()
    adapter.synthesize_occluded_joints.return_value = SynthesisResult(
        status="applied",
        joints=None,
        confidence=None,
        warnings=(),
    )

    result = wrapper(
        adapter=adapter,
        joint_sequence=None,
        confidence_sequence=None,
        occlusion_mask=None,
        scene_findings={},
        is_reference=True,
    )

    assert isinstance(result, SynthesisResult), (
        "R2 fix — None 반환 폐기, SynthesisResult 만 허용"
    )
    assert result.status == "skipped"
    assert "g4_reference_guard" in result.warnings
    # adapter 자체는 호출되지 않아야 함 — G4 가드 최우선.
    adapter.synthesize_occluded_joints.assert_not_called()


def test_g4_guard_allows_synthesis_for_user() -> None:
    """is_reference=False → adapter 호출 진행."""
    wrapper, SynthesisResult = _load_wrapper_and_result()

    expected = SynthesisResult(
        status="applied",
        joints=None,
        confidence=None,
        warnings=(),
    )

    adapter = MagicMock()
    adapter.synthesize_occluded_joints.return_value = expected

    result = wrapper(
        adapter=adapter,
        joint_sequence=None,
        confidence_sequence=None,
        occlusion_mask=None,
        scene_findings={},
        is_reference=False,
    )

    # G4 가드 미발동 → adapter 위임 결과 또는 동등한 status="applied" 반환.
    assert isinstance(result, SynthesisResult)
    assert result.status != "skipped" or "g4_reference_guard" not in result.warnings
