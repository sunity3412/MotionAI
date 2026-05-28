"""mode3 자기 성장 분기 (_mode3_comparison) — 순수 로직. NLF·S3·Firestore 불필요.

첫 분석=절대 3차원 + delta 없음, 두 번째+=절대 3 + angle(이전영상 대비) + 발전 델타.
같은 영상이면 angle 일관성이 높고, 절대 차원은 입력이 같아 동일 점수가 나온다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

import app  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS  # noqa: E402


def _video(seed: int = 0, t: int = 40) -> np.ndarray:
    """그럴듯한 자세 시퀀스 (T, J). seed 로 다른 영상 흉내."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(120, 175, size=NUM_JOINTS)
    return base + rng.normal(0, 3, size=(t, NUM_JOINTS))


def _as_prev(angles: np.ndarray, analysis_id: str, dim_scores: dict) -> dict:
    """get_previous_analysis 반환 모양 (doc dict)."""
    return {
        "analysisId": analysis_id,
        "angles": np.asarray(angles, dtype=float).reshape(-1).tolist(),
        "anglesJointKeys": list(JOINT_KEYS),
        "anglesFrames": int(angles.shape[0]),
        "result": {"dimensionScores": dim_scores},
    }


def test_first_analysis_absolute_only_no_delta():
    assessments, dims, overall, comparison = app._mode3_comparison(_video(1), None)
    assert comparison == {"mode": "mode3", "isFirst": True}
    assert set(dims) == {"line", "balance", "stability"}
    assert 0 <= overall <= 100
    assert len(assessments) == NUM_JOINTS


def test_second_analysis_has_progress_delta_and_angle():
    cur = _video(2)
    prev_angles = _video(7)
    prev = _as_prev(
        prev_angles, "prevA",
        {"line": 60, "balance": 70, "stability": 65},
    )
    _, dims, overall, comparison = app._mode3_comparison(cur, prev)
    # 두 번째+ = angle(이전영상 일관성) 표시 + 절대 3차원.
    assert set(dims) == {"angle", "line", "balance", "stability"}
    assert comparison["mode"] == "mode3" and comparison["isFirst"] is False
    assert comparison["previousAnalysisId"] == "prevA"
    # 발전 델타는 절대 3차원만 (각도 제외 — 척도 안정).
    assert set(comparison["deltaFromPrevious"]) == {"line", "balance", "stability"}


def test_same_video_is_consistent():
    # 같은 영상 = 이전과 각도 일관성 매우 높음 + 절대 차원 델타 0.
    v = _video(3)
    prev_abs = app.dimensions.absolute_dimension_scores(v)
    prev = _as_prev(v, "selfprev", prev_abs)
    _, dims, _, comparison = app._mode3_comparison(v, prev)
    assert dims["angle"] >= 95  # 자기 자신과 정렬 → 편차 ~0
    assert comparison["deltaFromPrevious"] == {"line": 0, "balance": 0, "stability": 0}
