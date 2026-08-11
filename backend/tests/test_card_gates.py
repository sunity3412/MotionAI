"""card_gates 순수 함수 단위 테스트 (quick-260811-kpo) — 합성 트랙, 판별 경계만.

수치 채우기 금지 (CLAUDE.md §7) — 케이스는 게이트가 갈라야 하는 경계 5+2종:
홀드 안정 PASS / 전환 3창 전부 높음 FAIL / 측정불가 FAIL(fail-closed) /
짝 원거리 포즈 FAIL / 폴 미검출 비차단 / 3창 최소(경계 정착) PASS /
기계 눈 2단 판정(마크-전위) 순수 verdict.
"""

from __future__ import annotations

import math

import numpy as np

from sunity_shared.analysis import card_gates as cg

FPS = 15.0
JOINTS = list(cg.POSE_BASIS_12)


def _make_report(frames: int, angle_of, conf: float = 0.9) -> dict:
    """left_knee(hip-knee-ankle) 사이각이 angle_of(f)를 따르는 합성 트랙.

    나머지 관절은 프레임 무관 고정 배치 — 홀드 게이트가 보는 축(left_knee)만
    움직인다. 좌표는 정규화 (0..1) 공간.
    """
    data = np.zeros((frames, len(JOINTS), 2), dtype=float)
    confs = np.full((frames, len(JOINTS)), conf, dtype=float)
    base = {
        "left_shoulder": (0.45, 0.20), "right_shoulder": (0.55, 0.20),
        "left_elbow": (0.40, 0.30), "right_elbow": (0.60, 0.30),
        "left_wrist": (0.38, 0.40), "right_wrist": (0.62, 0.40),
        "left_hip": (0.45, 0.50), "right_hip": (0.55, 0.50),
        "left_knee": (0.45, 0.65), "right_knee": (0.55, 0.65),
        "left_ankle": (0.45, 0.80), "right_ankle": (0.55, 0.80),
    }
    for f in range(frames):
        for j, name in enumerate(JOINTS):
            data[f, j] = base[name]
        # left_knee 사이각 = angle_of(f): 무릎을 꼭짓점으로 발목을 회전 배치.
        # hip(0.45,0.50) → knee(0.45,0.65) 수직 하강 — 발목을 사이각만큼 연다.
        ang = math.radians(angle_of(f))
        knee = np.array(base["left_knee"])
        # hip→knee 방향 (아래) 기준, 사이각 ang 로 발목 방향 회전
        down = np.array([0.0, 1.0])
        rot = np.array([
            [math.cos(math.pi - ang), -math.sin(math.pi - ang)],
            [math.sin(math.pi - ang), math.cos(math.pi - ang)],
        ])
        limb = rot @ (-down)  # knee→hip 반대 방향에서 ang 만큼 연다
        data[f, JOINTS.index("left_ankle")] = knee + limb * 0.15
    return {
        "joints": JOINTS,
        "frames": frames,
        "fps": FPS,
        "data": data.reshape(-1).tolist(),
        "confidence": confs.reshape(-1).tolist(),
    }


def test_hold_stable_pass():
    """안정 구간 (각도 고정) — 홀드 PASS."""
    rep = _make_report(9, lambda f: 90.0)
    res = cg.hold_gate(rep, 4, "left_knee")
    assert res.passed
    assert res.reason == "hold"
    assert res.speed_dps is not None and res.speed_dps < cg.HOLD_MAX_DPS


def test_hold_transition_fail():
    """전환 구간 (3창 전부 임계 위) — FAIL. fresh 왼골반 111도/초 판별의 합성판."""
    # 15fps 에서 프레임당 10도 = 150도/초 — 과거/대칭/미래창 전부 높다.
    rep = _make_report(9, lambda f: 40.0 + 10.0 * f)
    res = cg.hold_gate(rep, 4, "left_knee")
    assert not res.passed
    assert res.reason == "moving"
    assert res.speed_dps is not None and res.speed_dps >= cg.HOLD_MAX_DPS


def test_hold_boundary_settle_pass():
    """경계 정착 (직전 전이 + 이후 안정) — 3창 최소 판정으로 PASS.

    ii0 구조 수리 ① 의 근거 케이스: 대칭창은 전이를 물어 높지만 미래창이 안정.
    """
    rep = _make_report(9, lambda f: (40.0 + 25.0 * f) if f < 4 else 140.0)
    res = cg.hold_gate(rep, 4, "left_knee")
    assert res.passed
    assert "future" in res.window_speeds
    assert res.window_speeds["future"] < cg.HOLD_MAX_DPS


def test_hold_unmeasurable_fail_closed():
    """저신뢰 (전 좌표 conf < 하한) — 측정불가 = FAIL (fail-closed)."""
    rep = _make_report(9, lambda f: 90.0, conf=cg.HOLD_CONF_MIN - 0.05)
    res = cg.hold_gate(rep, 4, "left_knee")
    assert not res.passed
    assert res.reason == "unmeasurable"
    assert res.speed_dps is None


def test_pair_pose_far_fail():
    """다른 국면 짝 (관절 배치 상이) — pose_far FAIL."""
    rep_a = _make_report(3, lambda f: 90.0)
    # 국면이 다른 포즈: 관절 절반의 상하를 뒤집어 정규화 후에도 멀게.
    rep_b = _make_report(3, lambda f: 90.0)
    data_b = np.asarray(rep_b["data"], dtype=float).reshape(3, len(JOINTS), 2)
    for name in ("left_wrist", "right_wrist", "left_ankle", "right_ankle",
                 "left_elbow", "right_elbow"):
        j = JOINTS.index(name)
        data_b[:, j, 1] = 1.0 - data_b[:, j, 1]
    rep_b["data"] = data_b.reshape(-1).tolist()
    res = cg.pair_gate(rep_a, 1, rep_b, 1, None, None)
    assert not res.passed
    assert res.reason == "pose_far"
    assert res.pose_dist is not None and res.pose_dist >= cg.PAIR_POSE_MAX


def test_pair_pole_unmeasured_nonblocking():
    """같은 국면 + 폴 미검출 — PASS (pole_unmeasured 비차단)."""
    rep = _make_report(3, lambda f: 90.0)
    res = cg.pair_gate(rep, 1, rep, 1, None, None)
    assert res.passed
    assert res.reason == "pole_unmeasured"
    assert res.pole_diff is None


def test_eye_verdict_limb_mismatch():
    """기계 눈 2단 판정 (순수) — 마크-전위 구멍 (ii0 kneepath 실측).

    상태(bent)가 우연 일치해도 사지 종류가 확정 상충(arm vs leg)이면 불일치.
    'other'/'unclear' 는 적극 모순이 아니므로 비차단.
    """
    assert cg._eye_verdict("bent", "leg", "bent", "leg")
    assert not cg._eye_verdict("bent", "arm", "bent", "leg")  # 마크-전위 차단
    assert cg._eye_verdict("bent", "unclear", "bent", "leg")  # 모순 아님 — 비차단
    assert cg._eye_verdict("bent", "other", "bent", "leg")
    assert not cg._eye_verdict("extended", "leg", "bent", "leg")  # 상태 불일치
    assert cg._eye_verdict("bent", "arm", "bent", None)  # 기대 미지정 = 상태만


def test_claim_and_limb_helpers():
    """claim 이분 (중간각 침묵) + 사지 종류 매핑 + 벌림 축 매핑."""
    assert cg.track_claim(74.0) == "bent"
    assert cg.track_claim(178.0) == "extended"
    assert cg.track_claim(127.0) is None  # 중간각 — 정직한 침묵
    assert cg.track_claim(None) is None
    assert cg.joint_limb("left_knee") == "leg"
    assert cg.joint_limb("right_elbow") == "arm"
    assert cg.joint_limb("split") is None
    assert cg.crit_joint("split_angle") == "split"
    assert cg.crit_joint("leg_extension") == "split"
    assert cg.crit_joint("left_knee") == "left_knee"
