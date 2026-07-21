"""Phase 12 Wave 0B (Plan 12-01) — _dataclass_to_camel_case_dict 변환 검증.

신설 2 snake_case 필드 (axis_data → axisData / axis_mask → axisMask)
camelCase 변환 정합 (Phase 9 C8 helper 박제).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _load_pipeline_app():
    """pipeline functions 의 app.py import (Phase 9 test 패턴 mirror)."""
    pipeline_dir = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
    if str(pipeline_dir) not in sys.path:
        sys.path.insert(0, str(pipeline_dir))
    sys.modules.pop("app", None)
    import app as pipeline_app  # noqa: WPS433

    return importlib.reload(pipeline_app)


def _make_minimal_keypoint_report():
    """T=1, J=NUM_KEYPOINTS_PHASE12 최소 KeypointReport — camelCase 변환 source.

    32-14: joints 를 _KEYPOINT_NAMES 파생으로 구성 — 8→12 확장 자동 추종.
    """
    from sunity_shared.analysis.keypoint_frame import (
        NUM_KEYPOINTS_PHASE12,
        KeypointReport,
        _KEYPOINT_NAMES,
    )

    J = NUM_KEYPOINTS_PHASE12
    return KeypointReport(
        version="1.0",
        joints=list(_KEYPOINT_NAMES),
        frames=1,
        fps=9.0,
        data=[0.5] * (1 * J * 2),
        confidence=[0.9] * (1 * J),
        reliability=["high"],
        axis_data=[0.5] * (1 * 3 * 2),
        axis_mask=[True, True, False],
        warnings=[],
    )


def test_keypoint_report_camel_case_keys() -> None:
    """KeypointReport 박제 10 필드 → camelCase 변환 검증.

    axis_data → axisData, axis_mask → axisMask (R6 iter-2 / R7 iter-2).
    다른 8 필드는 이미 camelCase (변환 X).
    """
    pipeline_app = _load_pipeline_app()
    report = _make_minimal_keypoint_report()
    out = pipeline_app._dataclass_to_camel_case_dict(report)

    # axisData / axisMask 변환 확인.
    assert "axisData" in out, f"axisData 변환 실패: {sorted(out.keys())}"
    assert "axisMask" in out, f"axisMask 변환 실패: {sorted(out.keys())}"

    # snake_case 잔존 0.
    snake_present = [k for k in out if "_" in k]
    assert not snake_present, (
        f"snake_case 변환 잔존: {snake_present} (D-12-U4 위반)"
    )


def test_keypoint_report_all_ten_fields_present() -> None:
    """변환 후 10 필드 모두 박제 (R10 정합)."""
    pipeline_app = _load_pipeline_app()
    report = _make_minimal_keypoint_report()
    out = pipeline_app._dataclass_to_camel_case_dict(report)

    expected_keys = {
        "version",
        "joints",
        "frames",
        "fps",
        "data",
        "confidence",
        "reliability",
        "axisData",
        "axisMask",
        "warnings",
    }
    assert set(out.keys()) == expected_keys, (
        f"키 집합 불일치 — expected {sorted(expected_keys)}, got {sorted(out.keys())}"
    )


def test_keypoint_report_none_returns_none() -> None:
    """None 입력 → None 반환 (Phase 9 패턴 정합)."""
    pipeline_app = _load_pipeline_app()
    assert pipeline_app._dataclass_to_camel_case_dict(None) is None


def test_keypoint_report_flat_list_types_preserved() -> None:
    """list 안의 scalar 타입 유지 (flat list → flat list, nested 안 됨)."""
    pipeline_app = _load_pipeline_app()
    report = _make_minimal_keypoint_report()
    out = pipeline_app._dataclass_to_camel_case_dict(report)

    # data / confidence / axisData = list[float].
    assert isinstance(out["data"], list)
    assert all(isinstance(v, (int, float)) for v in out["data"])
    # axisMask = list[bool] strict.
    assert isinstance(out["axisMask"], list)
    assert all(isinstance(v, bool) for v in out["axisMask"])
    # joints / reliability / warnings = list[str].
    assert all(isinstance(v, str) for v in out["joints"])
