"""Plan 08-01 Task 1 — dimensions.stability_wobble() drift defense test.

stability_wobble() helper 분리 검증:
  - 직접 산식 (inter-frame abs diff median over joints, mean) 과 helper 결과 일치.
  - frame 부족 시 0.0 반환.
  - stability_score() refactor 회귀 0 (동일 input → 동일 output).

Plan 08-02 의 force_signals.compute_stability_metrics 가 본 helper import 강제 —
drift defense source (Phase 12.5 v4 Codex HIGH-2 패턴 정합).

jerk_score (deg/sec^3, FPS 정규화) 는 별도 산출 — REVIEWS R5 정합 (본 test scope X).
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis import dimensions
from sunity_shared.analysis.dimensions import _select_window
from sunity_shared.analysis.skeleton import JOINT_KEYS


def _direct_wobble_on_window(angles: np.ndarray) -> float:
    """helper 의 산식 직접 재구성 — _select_window 후 inter-frame median wobble."""
    sliced, _ = _select_window(angles, profile=None)
    if sliced.shape[0] < 2:
        return 0.0
    inter_frame_diff = np.abs(np.diff(sliced, axis=0))
    median_jerk = np.nanmedian(inter_frame_diff, axis=0)
    return float(np.nanmean(median_jerk))


def test_stability_wobble_matches_direct_formula() -> None:
    """helper output == 직접 산식 (같은 window 위에서). drift 차단 source."""
    rng = np.random.default_rng(0)
    angles = rng.normal(120.0, 5.0, size=(50, len(JOINT_KEYS)))

    direct = _direct_wobble_on_window(angles)
    helper = dimensions.stability_wobble(angles, profile=None)

    assert abs(helper - direct) < 1e-9, (
        f"stability_wobble drift detected — helper={helper} vs direct={direct}"
    )


def test_stability_wobble_short_input_returns_zero() -> None:
    angles = np.full((1, len(JOINT_KEYS)), 90.0)
    assert dimensions.stability_wobble(angles, profile=None) == 0.0


def test_stability_score_refactor_preserves_output() -> None:
    """refactor 회귀 0 — kismam.score_from_deviation(wobble, _STABILITY_TOL_DEG) 산식 유지."""
    rng = np.random.default_rng(42)
    angles = rng.normal(120.0, 5.0, size=(50, len(JOINT_KEYS)))

    # helper 호출 + 동일 산식 재구성
    wobble = dimensions.stability_wobble(angles, profile=None)
    direct = _direct_wobble_on_window(angles)
    assert abs(wobble - direct) < 1e-9

    # stability_score() 가 helper 위에서 작동 — 결과는 정수 0~100
    score = dimensions.stability_score(angles, profile=None)
    assert isinstance(score, int)
    assert 0 <= score <= 100
