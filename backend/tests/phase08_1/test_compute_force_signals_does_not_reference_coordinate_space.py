"""Plan 08.1-00 Wave 0 — C-B1 grep guard.

compute_force_signals 본체 안 `coordinate_space == 'unavailable'` 참조 영구 부재.
AxisDeviationMetric 에서 coordinate_space 필드 제거 후 본 block 잔존 시
AttributeError 발생 — Codex iteration 1 사전 예측 박제.

본 grep guard 는 회귀 0 강제 (Wave 1 cleanup 시 동일 invariant 유지).

per Plan 08.1-00 must_haves (C-B1).
"""

from __future__ import annotations

import inspect
import re

from sunity_shared.analysis import force_signals
from sunity_shared.analysis.force_signals import compute_force_signals


def test_compute_force_signals_body_no_coordinate_space_unavailable_reference() -> None:
    """compute_force_signals 본체 안 coordinate_space == 'unavailable' 참조 0건.

    AxisDeviationMetric 에서 coordinate_space 필드 영구 제거 → 본 참조 잔존 시
    AttributeError. C-B1 fix 박제 회귀 0 강제.
    """
    src = inspect.getsource(compute_force_signals)
    # 'coordinate_space == "unavailable"' 또는 "coordinate_space == 'unavailable'" 또는
    # m.coordinate_space (attribute access on metric) 박제 영구 부재.
    forbidden_patterns = [
        r'coordinate_space\s*==\s*["\']unavailable["\']',
        r'\.coordinate_space',  # m.coordinate_space attribute access
    ]
    for pat in forbidden_patterns:
        matches = re.findall(pat, src)
        assert not matches, (
            f"compute_force_signals 본체 안 forbidden pattern {pat!r} 잔존: {matches}"
        )


def test_axis_metric_transitional_warning_top_level_emit() -> None:
    """compute_force_signals umbrella 가 axis_metric_transitional warning emit 박제.

    C-B1 fix — coordinate_space 검출 로직 → axis_metric_transitional 검출 로직 교체.
    모든 axis_metric 의 warnings 박제 'phase_8_1_wave_0_transitional' 포함 시
    top-level warnings 박제 'axis_metric_transitional' 동행.

    source-level grep — 본체 안 'axis_metric_transitional' literal 박제 존재.
    """
    src = inspect.getsource(compute_force_signals)
    assert "axis_metric_transitional" in src, (
        "compute_force_signals 본체 안 'axis_metric_transitional' literal 부재 — "
        "C-B1 fix 박제 회귀 검출"
    )
    assert "phase_8_1_wave_0_transitional" in src, (
        "compute_force_signals 본체 안 'phase_8_1_wave_0_transitional' literal 부재 — "
        "C-B1 박제 stub detection 회귀 검출"
    )


def test_compute_axis_deviation_emits_phase_8_1_transitional_warning() -> None:
    """compute_axis_deviation stub 의 warning emit 박제 source-level grep.

    Wave 1 가 본 stub 을 실 본체 로 교체 시 본 test RED → 동시에 본 grep guard
    제거 박제 plan 정합 (Wave 1 plan 박제 cleanup item).
    """
    from sunity_shared.analysis.force_signals import compute_axis_deviation

    src = inspect.getsource(compute_axis_deviation)
    assert "phase_8_1_wave_0_transitional" in src, (
        "compute_axis_deviation stub 본체 안 'phase_8_1_wave_0_transitional' literal 부재"
    )
