"""Phase 4 Wave 0 — POSE-03-b: SynthesisAdapter graceful degrade.

SynthesisAdapter.synthesize_occluded_joints 가 예외를 던질 때 degrade wrapper
(_call_synthesis_adapter / pipeline 측 helper) 가
  SynthesisResult(status="failed", joints=None, confidence=None,
                  warnings=("ai_synthesis_failed",))
를 반환해야 한다.

R2 fix — all-zero array sentinel 폐기. 실패 시 joints/confidence 는 반드시 None.

Wave 0 시점에서 SynthesisResult / SynthesisAdapter / degrade wrapper 미박제 →
ImportError → pytest.skip (collect error 방지).

POSE-03-b 2개 케이스:
  1. GeminiViewReasoner (Stage 1 PRIMARY) Exception → degrade
  2. CylindricalMeshAdapter (Stage 3 backend) Exception → degrade
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _load_synthesis_result():
    """SynthesisResult dataclass — Wave 1 박제 위치에서 lazy import."""
    try:
        from sunity_shared.analysis.synthesis.interfaces import SynthesisResult
    except ImportError:
        pytest.skip(
            "synthesis.interfaces.SynthesisResult — Wave 1 (04-01) 미박제"
        )
    return SynthesisResult


def _load_degrade_wrapper():
    """degrade wrapper — Wave 1 pipeline._call_synthesis_adapter 또는 동등 helper."""
    # Wave 1 박제 후보 위치 (04-01 Task 2):
    #   1. backend/functions/pipeline/app.py::_call_synthesis_adapter
    #   2. sunity_shared.analysis.synthesis 패키지 내 helper
    # 둘 다 미존재 시 skip.
    try:
        # 우선순위 1: pipeline 측 _call_synthesis_adapter (04-01 Task 2 박제 위치)
        from functions.pipeline.app import _call_synthesis_adapter as wrapper
        return wrapper
    except ImportError:
        pass
    try:
        from sunity_shared.analysis.synthesis import call_synthesis_adapter as wrapper
        return wrapper
    except ImportError:
        pytest.skip(
            "degrade wrapper (_call_synthesis_adapter) — Wave 1 (04-01 Task 2) 미박제"
        )


def test_gemini_degrade() -> None:
    """GeminiViewReasoner 가 Exception 을 raise 하면 SynthesisResult(status=failed,
    joints=None, confidence=None) 반환. all-zero array sentinel 금지 (R2 fix)."""
    SynthesisResult = _load_synthesis_result()
    wrapper = _load_degrade_wrapper()

    gemini_adapter = MagicMock()
    gemini_adapter.synthesize_occluded_joints.side_effect = Exception("api fail")

    result = wrapper(
        adapter=gemini_adapter,
        joint_sequence=None,
        confidence_sequence=None,
        occlusion_mask=None,
        scene_findings={},
    )

    assert isinstance(result, SynthesisResult)
    assert result.status == "failed"
    assert result.joints is None, (
        "R2 fix — all-zero array sentinel 금지, 실패 시 joints=None"
    )
    assert result.confidence is None
    assert "ai_synthesis_failed" in result.warnings


def test_cylindrical_degrade() -> None:
    """CylindricalMeshAdapter (Stage 3 backend) Exception 시 동일 SynthesisResult
    (status=failed, joints=None, confidence=None) 반환."""
    SynthesisResult = _load_synthesis_result()
    wrapper = _load_degrade_wrapper()

    cylindrical_adapter = MagicMock()
    cylindrical_adapter.synthesize_occluded_joints.side_effect = RuntimeError(
        "mesh build failed"
    )

    result = wrapper(
        adapter=cylindrical_adapter,
        joint_sequence=None,
        confidence_sequence=None,
        occlusion_mask=None,
        scene_findings={},
    )

    assert isinstance(result, SynthesisResult)
    assert result.status == "failed"
    assert result.joints is None
    assert result.confidence is None
    assert "ai_synthesis_failed" in result.warnings
