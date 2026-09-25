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


# ── (7) 대표 짝 (quick-260924-vw2) — 카드·영상 멈춤이 물려받을 한 순간 ─────────────────────────


def _rp_reports(T=40, stand=10, *, stu_hip, ref_hip, stu_side=-1, ref_side=-1, low_conf_frames=()):
    """창 안 프레임마다 엉덩이 높이를 주는 합성 보고서. 몸은 그립(오른)손의 stu_side/ref_side 쪽."""
    def build(hips, side, lowc):
        ys = _pose(T, stand, hip=0.6, low_ankle=0.79, high_ankle=0.7, hand=0.32)
        h = np.full(T, 0.65)
        h[stand:] = hips
        ys["left_hip"] = ys["right_hip"] = h
        rep = _report(ys, T)
        X = np.asarray(rep["data"]).reshape(T, len(_JOINTS), 2)
        X[:, _JOINTS.index("right_hand"), 0] = 0.5
        X[:, _JOINTS.index("left_hip"), 0] = X[:, _JOINTS.index("right_hip"), 0] = 0.5 + 0.1 * side
        rep["data"] = X.reshape(-1).tolist()
        C = np.asarray(rep["confidence"]).reshape(T, len(_JOINTS))
        for f in lowc:
            C[f, _JOINTS.index("left_elbow")] = hh.MIN_CONF - 0.05
        rep["confidence"] = C.reshape(-1).tolist()
        return rep
    return build(stu_hip, stu_side, low_conf_frames), build(ref_hip, ref_side, ())


def test_representative_pair_is_the_one_closest_to_the_window_constant():
    T, stand = 40, 10
    stu_hip = np.full(T - stand, 0.605)
    stu_hip[5] = 0.50            # 튀는 한 장(차이 최대) — 대표가 아니다
    ref_hip = np.full(T - stand, 0.56)
    stu, ref = _rp_reports(T, stand, stu_hip=stu_hip, ref_hip=ref_hip)
    pairs = [(u, u) for u in range(stand, T)]
    rp = hh.representative_pair(stu, ref, pairs, (stand, T), (stand, T), arm_side="left")
    assert rp is not None and rp["userFrame"] != stand + 5
    assert rp["userFrame"] == rp["refFrame"]


def test_stall_pairs_are_not_a_moment():
    """학생 한 장 ↔ 기준 여러 장(정체)은 같은 순간이라 말할 수 없다 — 1:1 짝만 후보."""
    T, stand = 40, 10
    stu, ref = _rp_reports(T, stand, stu_hip=np.full(T - stand, 0.605), ref_hip=np.full(T - stand, 0.56))
    pairs = [(20, r) for r in range(stand, T)]  # 전부 정체
    assert hh.representative_pair(stu, ref, pairs, (stand, T), (stand, T), arm_side="left") is None


def test_mirrored_side_of_the_pole_is_not_a_pair():
    """몸이 폴(그립 손)의 반대쪽이면 나란히 놓았을 때 비교가 헷갈린다 — 후보 아님(uff 후보 c)."""
    T, stand = 40, 10
    stu, ref = _rp_reports(T, stand, stu_hip=np.full(T - stand, 0.605), ref_hip=np.full(T - stand, 0.56),
                           stu_side=-1, ref_side=+1)
    pairs = [(u, u) for u in range(stand, T)]
    assert hh.representative_pair(stu, ref, pairs, (stand, T), (stand, T), arm_side="left") is None


def test_unreadable_marked_joint_excludes_the_frame():
    T, stand = 40, 10
    stu, ref = _rp_reports(T, stand, stu_hip=np.full(T - stand, 0.605), ref_hip=np.full(T - stand, 0.56),
                           low_conf_frames=range(stand, T - 1))
    pairs = [(u, u) for u in range(stand, T)]
    rp = hh.representative_pair(stu, ref, pairs, (stand, T), (stand, T), arm_side="left")
    assert rp is not None and rp["userFrame"] == T - 1   # 왼팔꿈치가 읽히는 유일한 프레임


def test_pairs_outside_the_window_are_ignored_and_bad_side_is_none():
    T, stand = 40, 10
    stu, ref = _rp_reports(T, stand, stu_hip=np.full(T - stand, 0.605), ref_hip=np.full(T - stand, 0.56))
    assert hh.representative_pair(stu, ref, [(2, 2), (5, 5)], (stand, T), (stand, T), arm_side="left") is None
    assert hh.representative_pair(stu, ref, [(20, 20)], (stand, T), (stand, T), arm_side="middle") is None


def test_kipup_fault_reproduces_the_pair_belle_approved():
    """uff 판정지 ○ 사진 = 학생 f21(2.11s) | 정은지 f38(2.53s). 그때는 한 장을 내 눈으로 뺐지만 이 규칙은 눈 없이 같은 짝을 고른다.
    저장 doc 재현은 오프라인 게이트(vw2 SUMMARY)가 맡고, 여기서는 규칙의 대표성 정의만 잠근다 — 차이 합이 최소인 짝."""
    T, stand = 40, 10
    stu_hip = np.linspace(0.62, 0.59, T - stand)
    ref_hip = np.linspace(0.57, 0.55, T - stand)
    stu, ref = _rp_reports(T, stand, stu_hip=stu_hip, ref_hip=ref_hip)
    pairs = [(u, u) for u in range(stand, T)]
    rp = hh.representative_pair(stu, ref, pairs, (stand, T), (stand, T), arm_side="left")
    s = hh._frame_series(stu, (stand, T)); r = hh._frame_series(ref, (stand, T))
    d_hip = np.median(s["hip"][stand:T]) - np.median(r["hip"][stand:T])
    d_low = np.median(s["lowFoot"][stand:T]) - np.median(r["lowFoot"][stand:T])
    scores = [abs((s["hip"][u] - r["hip"][u]) - d_hip) + abs((s["lowFoot"][u] - r["lowFoot"][u]) - d_low) for u in range(stand, T)]
    assert rp["score"] == pytest.approx(min(scores))


# ── (7) 몸 전체 패턴 — 낮은 위치에서 돈다 (quick-260925-nnt, 09-24 Pod L4 운영 창 실측, 엉덩이 1/3 차) ──────
# belle 09-25 봉인 정답(power-spin 실수): "도는 위치의 높이가 다르다". 잰 값 = hold heights 로그의 thirds hip 그대로.
# 그립 손은 조건 밖 — 회전 동작에서 "높은 손" 시계열이 검출 탈락으로 세 봉우리(1.3/0.6/0.1)라 중앙값이 탈락 비율을 잰다.


def _hip_thirds(hip3):
    return {"hip": {"thirds": [[0.8 + d, 0.8] for d in hip3]}}


_PS_FAULT = _hip_thirds((-0.225, -0.157, -0.180))     # 09-24 14:39 power-spin 실수
_PS_CORRECT = _hip_thirds((-0.037, -0.118, -0.038))   # 09-24 14:37 power-spin 정타(기준과 다른 창) — 앞·뒤 1/3 이 잡음 폭 안
_KIPUP_CORRECT_H = _hip_thirds((-0.009, -0.0, -0.009))
_CLIMB_CORRECT_H = _hip_thirds((-0.0, -0.005, -0.003))
_PETERPAN_CORRECT_H = _hip_thirds((-0.001, 0.012, 0.019))


def test_low_position_holds_for_the_power_spin_fault_and_no_correct_take():
    assert hh.body_low(_PS_FAULT) is True
    for facts in (_PS_CORRECT, _KIPUP_CORRECT_H, _CLIMB_CORRECT_H, _PETERPAN_CORRECT_H):
        assert hh.body_low(facts) is False


@pytest.mark.parametrize("noise", [0.04, 0.05, 0.06, 0.08, 0.10, 0.12])
def test_low_position_decision_does_not_depend_on_where_the_noise_band_sits(noise):
    """잡음 폭을 3배 범위에서 옮겨도 실수 True·정타 False — 이 값을 영상에 맞춰 고른 게 아니다."""
    assert hh.body_low(_PS_FAULT, noise=noise) is True
    assert hh.body_low(_PS_CORRECT, noise=noise) is False


def test_low_position_margin_on_the_correct_take_is_thin_and_recorded():
    """정타 power-spin 앞·뒤 1/3 = −0.037/−0.038 — 잡음 폭이 0.038 아래로 내려가면 정타가 뒤집힌다.
    이 여유가 얇다는 사실을 잠근다(새 테이크가 오면 여기부터 본다)."""
    assert hh.NOISE_BODY_LENGTH > 0.038
    assert hh.body_low(_PS_CORRECT, noise=0.03) is True   # 알려진 뒤집힘 — 그래서 기본값을 0.03 으로 내리지 않는다


@pytest.mark.parametrize(
    "facts",
    [
        _hip_thirds((-0.225, -0.157, -0.01)),   # 마지막 1/3 은 안 낮다 → "끝날 때까지" 자격 없음
        _hip_thirds((-0.225, float("nan"), -0.180)),
        {"grip": {"diff": -0.6}},               # 엉덩이 없음
        None,
    ],
)
def test_low_position_any_missing_condition_is_false(facts):
    assert hh.body_low(facts) is False


def test_low_position_ignores_the_arm_sign():
    assert hh.body_low(_PS_FAULT, -40.0) is True
    assert hh.body_low(_PS_FAULT, None) is True


# ── (8) 그립 손 쪽 — 몸 전체 패턴이 표식·대표 짝에 쓸 팔 ────────────────────────


def test_grip_side_is_the_hand_that_stays_higher_in_the_window():
    T, stand = 40, 10
    stu = _report(_pose(T, stand, hip=0.605, low_ankle=0.795, high_ankle=0.74, hand=0.325), T)
    assert hh.grip_side_majority(stu, (10, 40)) == "right"   # _pose: 오른손 = hand, 왼손 = hand + 0.1(더 낮다)


def test_grip_side_is_none_when_a_hand_is_unreadable_or_tied():
    T, stand = 40, 10
    ys = _pose(T, stand, hip=0.605, low_ankle=0.795, high_ankle=0.74, hand=0.325)
    low = _report(ys, T, conf={"left_hand": hh.MIN_CONF - 0.01})
    assert hh.grip_side_majority(low, (10, 40)) is None
    ys["left_hand"] = ys["right_hand"]
    assert hh.grip_side_majority(_report(ys, T), (10, 40)) is None
    assert hh.grip_side_majority(None, (10, 40)) is None
