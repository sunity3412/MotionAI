"""quick-260924-vj1 — 유지 구간 몸 높이(hold_height) + belle kip-up 판독의 측정판 판정기.

belle 2026-09-24: kip-up 실수는 "k24 부터 다리 뜨임 … 발의 높이 … 끝까지 연속". 8관절 각도에 없는 축이라
저장 2D 키포인트로 직접 잰다. 이 테스트가 단언하는 것 (수치 채우기 아님 — 구조와 판정):
  (1) 단위·바닥·손 기준 계산이 정의대로다 (합성 좌표 → 정확값)
  (2) 앞/중/뒤 1/3 이 각 영상 자기 창에서 나온다
  (3) 못 재면 None — 호출측이 문장을 안 만든다 (fail-closed 6종)
  (4) 판정기 네 조건이 **하나씩** 빠질 때마다 False
  (5) 잡음 폭을 0.03~0.12 어디에 둬도 uff 실측(kip-up 실수·정타)의 결론이 같다 — 짜맞춘 문턱이 아니라는 잠금
  (6) 신뢰 하한·창 최소 프레임이 이웃 모듈 값과 갈라지지 않는다
실 Gemini/Pod/S3/Firestore 호출 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import hold_height as hh  # noqa: E402

_JOINTS = [
    "left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_knee", "right_knee",
    "left_hand", "right_hand", "left_ankle", "right_ankle", "left_elbow", "right_elbow",
]


def _report(ys: dict, T: int, conf: dict | None = None) -> dict:
    """관절별 y 배열(또는 상수)로 keypointReport dict 를 만든다. x 는 0.5 고정, 신뢰도 기본 0.9."""
    X = np.zeros((T, len(_JOINTS), 2))
    C = np.full((T, len(_JOINTS)), 0.9)
    X[:, :, 0] = 0.5
    for name, y in ys.items():
        X[:, _JOINTS.index(name), 1] = y
    for name, c in (conf or {}).items():
        C[:, _JOINTS.index(name)] = c
    return {"joints": list(_JOINTS), "frames": T, "data": X.reshape(-1).tolist(), "confidence": C.reshape(-1).tolist()}


def _pose(T: int, stand: int, *, hip: float, low_ankle: float, high_ankle: float, hand: float) -> dict:
    """앞 `stand` 프레임은 서 있음(어깨 0.5 · 발목 0.8 → 몸길이 0.3, 바닥 0.8), 이후는 창 자세."""
    def seq(standing, window):
        v = np.full(T, window, dtype=float)
        v[:stand] = standing
        return v
    return {
        "left_shoulder": seq(0.5, 0.35), "right_shoulder": seq(0.5, 0.35),
        "left_hip": seq(0.65, hip), "right_hip": seq(0.65, hip),
        "left_ankle": seq(0.8, low_ankle), "right_ankle": seq(0.8, high_ankle),
        "left_hand": seq(0.6, hand + 0.1), "right_hand": seq(0.3, hand),
    }


# ── (1)(2) 정의대로 ──────────────────────────────────────────────────────────


def test_heights_follow_the_definition():
    T, stand = 40, 10
    stu = _report(_pose(T, stand, hip=0.605, low_ankle=0.795, high_ankle=0.74, hand=0.325), T)
    ref = _report(_pose(T, stand, hip=0.56, low_ankle=0.73, high_ankle=0.70, hand=0.32), T)
    h = hh.hold_window_heights(stu, ref, (stand, T), (stand, T))
    body, floor = 0.3, 0.8
    assert h["hip"]["student"] == pytest.approx((floor - 0.605) / body)
    assert h["hip"]["reference"] == pytest.approx((floor - 0.56) / body)
    assert h["lowFoot"]["diff"] == pytest.approx(((floor - 0.795) - (floor - 0.73)) / body)
    assert h["grip"]["student"] == pytest.approx((floor - 0.325) / body)  # 높은 손 = 오른손(y 작음)
    assert h["hipBelowHand"]["student"] == pytest.approx((0.325 - 0.605) / body)
    assert h["lowFootBelowHand"]["reference"] == pytest.approx((0.32 - 0.73) / body)


def test_thirds_come_from_each_videos_own_window():
    T, stand = 40, 10
    ys = _pose(T, stand, hip=0.6, low_ankle=0.79, high_ankle=0.7, hand=0.32)
    hip = np.full(T, 0.65)
    hip[10:20], hip[20:30], hip[30:40] = 0.62, 0.60, 0.58  # 학생 창 [10,40) 앞/중/뒤
    ys["left_hip"] = ys["right_hip"] = hip
    stu = _report(ys, T)
    ref = _report(_pose(T, stand, hip=0.56, low_ankle=0.73, high_ankle=0.7, hand=0.32), T)
    h = hh.hold_window_heights(stu, ref, (stand, T), (stand, T))
    got = [s for s, _r in h["hip"]["thirds"]]
    assert got == pytest.approx([(0.8 - 0.62) / 0.3, (0.8 - 0.60) / 0.3, (0.8 - 0.58) / 0.3])


# ── (3) fail-closed ──────────────────────────────────────────────────────────


def _pair(T=40, stand=10):
    stu = _report(_pose(T, stand, hip=0.605, low_ankle=0.795, high_ankle=0.74, hand=0.325), T)
    ref = _report(_pose(T, stand, hip=0.56, low_ankle=0.73, high_ankle=0.70, hand=0.32), T)
    return stu, ref


def test_no_standing_frames_before_window_is_none():
    stu, ref = _pair()
    assert hh.hold_window_heights(stu, ref, (hh.MIN_STAND_FRAMES - 1, 40), (10, 40)) is None


def test_short_window_is_none():
    stu, ref = _pair()
    assert hh.hold_window_heights(stu, ref, (10, 10 + hh.MIN_WINDOW_FRAMES - 1), (10, 40)) is None


def test_window_past_the_report_is_none():
    stu, ref = _pair()
    assert hh.hold_window_heights(stu, ref, (10, 41), (10, 40)) is None


def test_missing_joint_is_none():
    stu, ref = _pair()
    i = stu["joints"].index("right_hand")
    stu["joints"][i] = "nose"
    assert hh.hold_window_heights(stu, ref, (10, 40), (10, 40)) is None


def test_shape_mismatch_is_none():
    stu, ref = _pair()
    stu["data"] = stu["data"][:-2]
    assert hh.hold_window_heights(stu, ref, (10, 40), (10, 40)) is None


def test_unreadable_standing_frames_is_none():
    """서 있는 프레임의 발목이 전부 신뢰 하한 미만 → 바닥을 못 정한다."""
    T, stand = 40, 10
    ys = _pose(T, stand, hip=0.605, low_ankle=0.795, high_ankle=0.74, hand=0.325)
    stu = _report(ys, T)
    C = np.asarray(stu["confidence"]).reshape(T, len(_JOINTS))
    C[:stand, _JOINTS.index("left_ankle")] = hh.MIN_CONF - 0.01
    C[:stand, _JOINTS.index("right_ankle")] = hh.MIN_CONF - 0.01
    stu["confidence"] = C.reshape(-1).tolist()
    _s, ref = _pair()
    assert hh.hold_window_heights(stu, ref, (10, 40), (10, 40)) is None


# ── (4) 판정기 — 조건 하나씩 ─────────────────────────────────────────────────


def _facts(hip3=(-0.15, -0.15, -0.15), low3=(-0.2, -0.2, -0.2), grip=-0.02, below=-0.13):
    return {
        "hip": {"thirds": [[0.8 + d, 0.8] for d in hip3]},
        "lowFoot": {"thirds": [[0.24 + d, 0.24] for d in low3]},
        "grip": {"diff": grip},
        "hipBelowHand": {"diff": below},
    }


def test_all_four_conditions_hold():
    assert hh.body_low_arm_open(_facts(), 33.9) is True


@pytest.mark.parametrize(
    "facts, arm",
    [
        (_facts(hip3=(-0.15, -0.15, -0.01)), 33.9),   # ① 마지막 1/3 은 안 낮다 → "끝날 때까지" 자격 없음
        (_facts(low3=(-0.2, 0.0, -0.2)), 33.9),       # ① 낮은발 가운데 1/3
        (_facts(grip=-0.12), 33.9),                    # ② 손을 낮게 잡았다 → "손 높이는 같은데" 거짓
        (_facts(below=-0.01), 33.9),                   # ③ 손 기준으로는 안 처졌다
        (_facts(), -5.0),                              # ④ 팔-몸통 각이 오히려 닫혔다
        (_facts(), 0.0),
        (_facts(), float("nan")),
        (None, 33.9),
        (_facts(), None),
    ],
)
def test_any_missing_condition_is_false(facts, arm):
    assert hh.body_low_arm_open(facts, arm) is False


# ── (5) 문턱 둔감성 — uff 실측(운영 창, 저장 doc dacc4467 · e6264535) ───────────────────

_KIPUP_FAULT = {
    "hip": {"diff": -0.1452, "thirds": [[0.6602, 0.7899], [0.6518, 0.8005], [0.649, 0.7987]]},
    "lowFoot": {"diff": -0.2199, "thirds": [[0.0152, 0.2247], [0.0281, 0.2498], [0.0129, 0.242]]},
    "grip": {"diff": -0.0207},
    "hipBelowHand": {"diff": -0.1258},
}
_KIPUP_CORRECT = {
    "hip": {"diff": -0.0083, "thirds": [[0.7807, 0.7899], [0.8, 0.8005], [0.7899, 0.7987]]},
    "lowFoot": {"diff": 0.0003, "thirds": [[0.2205, 0.2247], [0.2533, 0.2498], [0.2504, 0.242]]},
    "grip": {"diff": -0.0147},
    "hipBelowHand": {"diff": 0.0047},
}


@pytest.mark.parametrize("noise", [0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12])
def test_decision_does_not_depend_on_where_the_noise_band_sits(noise):
    """잡음 폭을 4배 범위에서 옮겨도 실수는 True, 정타는 False — 이 값을 영상에 맞춰 고른 게 아니다."""
    assert hh.body_low_arm_open(_KIPUP_FAULT, 33.86, noise=noise) is True
    assert hh.body_low_arm_open(_KIPUP_CORRECT, -1.72, noise=noise) is False


def test_default_noise_sits_inside_the_insensitive_range():
    assert 0.03 <= hh.NOISE_BODY_LENGTH <= 0.12


# ── (6) 이웃 모듈과 같은 값 ──────────────────────────────────────────────────


def test_min_conf_matches_card_gates_measurement_floor():
    from sunity_shared.analysis import card_gates

    assert hh.MIN_CONF == card_gates.HOLD_CONF_MIN


def test_min_window_matches_pipeline_constant_window():
    pipeline = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
    if str(pipeline) not in sys.path:
        sys.path.insert(0, str(pipeline))
    import app  # noqa: E402

    assert hh.MIN_WINDOW_FRAMES == app._CONSTANT_WINDOW_MIN_FRAMES
