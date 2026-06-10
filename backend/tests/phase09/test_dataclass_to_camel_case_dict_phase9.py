"""Plan 09-01 Wave 0 — _dataclass_to_camel_case_dict camelCase 변환 (D-09-U4).

신설 3 필드 (source_signal → sourceSignal / joint_hint → jointHint /
mode_context → modeContext) 가 Phase 6 C8 박제 helper 를 통해 자동 변환됨을 검증.
overall_confidence → overallConfidence 도 동행 박제.

per Plan 09-01 must_haves + RESEARCH "Don't Hand-Roll" 표.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _load_pipeline_app():
    """pipeline functions 의 app.py 를 import — _dataclass_to_camel_case_dict 박제 위치."""
    pipeline_dir = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
    if str(pipeline_dir) not in sys.path:
        sys.path.insert(0, str(pipeline_dir))
    sys.modules.pop("app", None)
    import app as pipeline_app  # noqa: WPS433

    return importlib.reload(pipeline_app)


def test_force_pattern_finding_camel_case_keys() -> None:
    """ForcePatternFinding 박제 8 필드 → camelCase 변환 검증."""
    pipeline_app = _load_pipeline_app()
    from sunity_shared.analysis.force_pattern import ForcePatternFinding

    finding = ForcePatternFinding(
        pattern="unknown",
        phase="lock",
        source_signal="high_jerk",
        reason="x",
        interpretation="y",
        confidence=0.5,
        joint_hint=None,
        warnings=[],
    )
    out = pipeline_app._dataclass_to_camel_case_dict(finding)

    # 변환된 camelCase 필드 박제.
    assert "sourceSignal" in out, f"sourceSignal 변환 실패: {sorted(out.keys())}"
    assert "jointHint" in out, f"jointHint 변환 실패: {sorted(out.keys())}"

    # snake_case 잔존 X.
    snake_present = [k for k in out if "_" in k]
    assert not snake_present, (
        f"snake_case 변환 잔존: {snake_present} (D-09-U4 위반)"
    )


def test_force_pattern_inference_camel_case_keys() -> None:
    """ForcePatternInference 박제 5 필드 → camelCase 변환 검증."""
    pipeline_app = _load_pipeline_app()
    from sunity_shared.analysis.force_pattern import (
        ForcePatternFinding,
        ForcePatternInference,
    )

    finding = ForcePatternFinding(
        pattern="unknown",
        phase="lock",
        source_signal="high_jerk",
        reason="x",
        interpretation="y",
        confidence=0.5,
        joint_hint=None,
        warnings=[],
    )
    inference = ForcePatternInference(
        version="1.0",
        findings=[finding],
        overall_confidence="low",
        mode_context="mode1",
        warnings=[],
    )
    out = pipeline_app._dataclass_to_camel_case_dict(inference)

    # 변환된 camelCase 필드.
    assert "modeContext" in out, f"modeContext 변환 실패: {sorted(out.keys())}"
    assert "overallConfidence" in out, (
        f"overallConfidence 변환 실패: {sorted(out.keys())}"
    )

    # snake_case 잔존 X.
    snake_present = [k for k in out if "_" in k]
    assert not snake_present, (
        f"snake_case 변환 잔존 (top-level): {snake_present} (D-09-U4 위반)"
    )

    # findings list 안 element 도 camelCase 박제.
    assert isinstance(out["findings"], list) and len(out["findings"]) == 1
    finding_dict = out["findings"][0]
    assert "sourceSignal" in finding_dict
    assert "jointHint" in finding_dict
    snake_in_finding = [k for k in finding_dict if "_" in k]
    assert not snake_in_finding, (
        f"findings[0] snake_case 잔존: {snake_in_finding}"
    )
