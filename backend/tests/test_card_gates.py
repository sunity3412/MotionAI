"""card_gates 순수 함수 단위 테스트 (quick-260811-kpo) — 합성 트랙, 판별 경계만.

수치 채우기 금지 (CLAUDE.md §7) — 케이스는 게이트가 갈라야 하는 경계 5+2종:
홀드 안정 PASS / 전환 3창 전부 높음 FAIL / 측정불가 FAIL(fail-closed) /
짝 원거리 포즈 FAIL / 폴 미검출 비차단 / 3창 최소(경계 정착) PASS /
기계 눈 2단 판정(마크-전위) 순수 verdict / 관절 종류 힌트 질문(jka) 조립 불변식.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

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


def test_claim_question_backward_compat():
    """expected_limb 미지정/off_pole — 오늘 질문과 byte-동일 (하위호환, vlu).

    off_pole 은 expected_limb 를 줘도 무변경 — 이번 수리 범위 밖 결정
    (quick-260901-vlu Task 1).
    """
    assert cg._claim_question("bent", None) == cg._CLAIM_QUESTION["bent"]
    assert cg._claim_question("extended", None) == cg._CLAIM_QUESTION["extended"]
    assert cg._claim_question("off_pole", "leg") == cg._CLAIM_QUESTION["off_pole"]
    assert cg._claim_question("off_pole", None) == cg._CLAIM_QUESTION["off_pole"]


def _assert_occlusion_question(q: str, target: str) -> None:
    """오클루전 반영 질문의 안정 불변식만 단정 — 전문(全文) 일치 금지.

    (a) 판정 대상 사지 명시 (b) 가림/겹침 언급 (c) 기대 사지 부재 시 실제
    보이는 사지 보고 지시 (d) 좌/우 해부학 이름 0 (e) off_body 이스케이프.
    _LIMB_QUESTION 접미 미부착 (limb 지시가 본문 내장 — 중복/모순 방지).
    """
    assert target in q
    assert ("가려" in q) or ("겹" in q)
    assert "실제" in q and "limb" in q
    low = q.lower()
    assert "왼" not in q and "오른" not in q
    assert "left" not in low and "right" not in low
    assert "off_body" in q
    assert cg._LIMB_QUESTION not in q


def test_claim_question_leg_occlusion_variant():
    """leg 변형 — 판정 대상이 다리, 오클루전 반영 (belle 09-01 오클루전 FP 수리)."""
    q = cg._claim_question("bent", "leg")
    _assert_occlusion_question(q, "다리")
    assert q != cg._CLAIM_QUESTION["bent"]


def test_claim_question_arm_occlusion_variant():
    """arm 변형 — 대칭 단정 (팔이 판정 대상)."""
    q = cg._claim_question("extended", "arm")
    _assert_occlusion_question(q, "팔")
    assert q != cg._CLAIM_QUESTION["extended"]


# 09-03 측정본 (quick-260903-jka PLAN, 운영 경로 eye_judge temperature 0 5회:
# 클라임 오클루전 2크롭 2/5·1/5 → 5/5·5/5, kneepath 마크-전위 회귀 0/5 유지).
# 이 문장이 그 성립 조건 — 문자 하나라도 바뀌면 측정과 다른 질문이다.
_KNEE_HINT_MEASURED = (
    "참고: 이 원은 무릎 관절 표시이며, 팔이 무릎 앞을 가로질러 가릴 수 있습니다. "
    "팔 뒤로 허벅지와 정강이가 이어지면 그 다리가 판정 대상입니다."
)


def test_claim_question_joint_kind_none_is_byte_identical():
    """joint_kind 미지정·미등록 — vlu 오클루전 변형과 byte-동일 (하위호환).

    운영 외 호출부(harvest/스크립트)는 kwarg 기본값 None 으로 종전 질문을
    계속 받는다 (quick-260903-jka Task 1 (a)).
    """
    assert cg._claim_question("bent", "leg") == cg._claim_question("bent", "leg", None)
    assert (cg._claim_question("extended", "arm")
            == cg._claim_question("extended", "arm", None))
    # 미등록 종류 → 힌트 미부착 (질문 무변경)
    assert cg._claim_question("bent", "leg", "코") == cg._claim_question("bent", "leg")
    # expected_limb 미지정이면 종류가 와도 _CLAIM_QUESTION 그대로
    assert cg._claim_question("bent", None, "무릎") == cg._CLAIM_QUESTION["bent"]


def test_claim_question_knee_leg_hint_matches_measured_sentence():
    """무릎/leg 힌트 = 09-03 측정본과 문자 동일, vlu 변형 뒤에 공백 1 + 1문장."""
    base = cg._claim_question("bent", "leg")
    q = cg._claim_question("bent", "leg", "무릎")
    assert q == base + " " + _KNEE_HINT_MEASURED
    assert q.count("참고:") == 1
    _assert_occlusion_question(q, "다리")  # vlu 불변식(좌/우 0 포함) 그대로 유지


def test_claim_question_elbow_arm_hint_is_symmetric():
    """팔꿈치/arm 힌트 — leg 문형의 대칭 (가리는 쪽=다리, 대상=팔), 좌/우 이름 0."""
    base = cg._claim_question("extended", "arm")
    q = cg._claim_question("extended", "arm", "팔꿈치")
    assert q == base + (
        " 참고: 이 원은 팔꿈치 관절 표시이며, 다리가 팔꿈치 앞을 가로질러 "
        "가릴 수 있습니다. 다리 뒤로 위팔과 아래팔이 이어지면 그 팔이 판정 대상입니다."
    )
    _assert_occlusion_question(q, "팔")


def test_claim_question_hint_particles_all_kinds():
    """힌트 종류(사지 중간 관절 4종) 전부 — 분절 받침에 따라 조사 가/이 가 맞게 붙는다.

    측정본(무릎 '정강이가') 과 같은 규칙이 다른 종류에도 일관 적용되는지 —
    조사가 틀리면 눈에 주는 문장이 비문이 된다. 힌트는 1문장("참고:" 1회)이고
    vlu 변형 뒤에 공백 1 로 이어진다 (quick-260903-jxn Task 1 (b)).
    """
    expect = {
        "무릎": ("leg", "허벅지와 정강이가"), "발목": ("leg", "정강이와 발이"),
        "팔꿈치": ("arm", "위팔과 아래팔이"), "손목": ("arm", "아래팔과 손이"),
    }
    assert set(expect) == set(cg._HINT_KINDS)
    assert cg._HINT_KINDS <= set(cg._KIND_SEGMENTS)
    for kind, (limb, seg_with_particle) in expect.items():
        base = cg._claim_question("bent", limb)
        q = cg._claim_question("bent", limb, kind)
        assert q.startswith(base + " 참고: ")
        assert q.count("참고:") == 1
        assert f"이 원은 {kind} 관절 표시이며" in q
        assert f"뒤로 {seg_with_particle} 이어지면" in q
        _assert_occlusion_question(q, "다리" if limb == "leg" else "팔")


def test_claim_question_torso_kinds_no_hint_byte_identical():
    """엉덩이·어깨(몸통 관절)는 힌트 0 — jka 이전(vlu) 질문과 byte-동일.

    09-03 측정: pdshape 엉덩이(기대 True) 힌트 없음 3/5 → 힌트 부착 1/5 로
    악화 (눈이 엉덩이 굽힘을 허벅지 방향으로 오독). 어깨는 5/5 였지만 같은
    몸통 관절이라 보수적으로 제외 (quick-260903-jxn Task 1 (a)).
    joint_kind_ko 는 여전히 엉덩이/어깨를 반환 — 호출측 무변경.
    """
    for claim in ("bent", "extended"):
        assert cg._claim_question(claim, "leg", "엉덩이") == cg._claim_question(claim, "leg")
        assert cg._claim_question(claim, "arm", "어깨") == cg._claim_question(claim, "arm")
        assert "참고:" not in cg._claim_question(claim, "leg", "엉덩이")
        assert "참고:" not in cg._claim_question(claim, "arm", "어깨")
    assert cg._joint_kind_hint("leg", "엉덩이") == ""
    assert cg._joint_kind_hint("arm", "어깨") == ""
    assert cg.joint_kind_ko("left_hip") == "엉덩이"
    assert cg.joint_kind_ko("right_shoulder") == "어깨"


def test_claim_question_hint_limb_mismatch_falls_back():
    """종류와 expected_limb 가 어긋나면(leg 에 '팔꿈치') 힌트 미부착 — 비문 방지."""
    assert cg._claim_question("bent", "leg", "팔꿈치") == cg._claim_question("bent", "leg")
    assert cg._claim_question("bent", "arm", "무릎") == cg._claim_question("bent", "arm")


def test_claim_question_off_pole_ignores_joint_kind():
    """off_pole 은 joint_kind 를 줘도 무변경 (vlu 결정 승계)."""
    assert cg._claim_question("off_pole", "leg", "무릎") == cg._CLAIM_QUESTION["off_pole"]
    assert cg._claim_question("off_pole", "arm", "팔꿈치") == cg._CLAIM_QUESTION["off_pole"]


def test_joint_kind_ko_mapping():
    """관절 이름 → 종류 한국어 — joint_limb 과 같은 접미 관례, hand=wrist 별칭."""
    assert cg.joint_kind_ko("right_knee") == "무릎"
    assert cg.joint_kind_ko("left_hand") == "손목"
    assert cg.joint_kind_ko("left_wrist") == "손목"
    assert cg.joint_kind_ko("right_hip") == "엉덩이"
    assert cg.joint_kind_ko("split") is None
    assert cg.joint_kind_ko("split_angle") is None
    # 종류의 사지는 joint_limb 과 일치 (힌트 문형 선택의 근거)
    for j in cg.POSE_BASIS_12:
        assert cg._KIND_LIMB[cg.joint_kind_ko(j)] == cg.joint_limb(j)


def test_eye_applicable_torso_joints_skipped():
    """몸통 관절(엉덩이·어깨) = 눈 검사 제외 — 좌/우 무관, 꼬리 = _LIMB_OF 키 공간."""
    assert cg.eye_applicable("left_hip") is False
    assert cg.eye_applicable("right_hip") is False
    assert cg.eye_applicable("right_shoulder") is False
    assert cg.eye_applicable("left_shoulder") is False
    assert cg.EYE_SKIP_KINDS <= set(cg._LIMB_OF)
    # jxn 힌트 집합과 정합: 힌트가 붙는 종류 = 눈 검사 대상, 몸통 종류 = 제외
    for suffix, ko in cg._KIND_KO.items():
        assert cg.eye_applicable(f"left_{suffix}") is (ko in cg._HINT_KINDS)


def test_eye_applicable_midlimb_joints_kept():
    """무릎·팔꿈치·발목·손목(hand 별칭 포함) = 종전대로 눈 검사."""
    for j in ("left_knee", "right_elbow", "left_ankle", "right_wrist", "left_hand"):
        assert cg.eye_applicable(j) is True


def test_eye_applicable_unknown_joint_defaults_true():
    """미등록 관절은 True — 종전 동작 (눈 여부는 호출측 기존 게이트가 정한다)."""
    assert cg.eye_applicable("left_foo") is True
    assert cg.eye_applicable("split") is True
    assert cg.eye_applicable("split_angle") is True


def test_machine_eye_unknown_claim():
    """미지 claim ValueError — 기존 검증 경로 무변경."""
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        cg.machine_eye(frame, (32.0, 32.0), "nonsense", api_key="unused")


# --- 다수결 (quick-260903-jxn Task 1 (c)(d)) — eye_judge 를 대본으로 대체,
# 네트워크 호출 0. 각 대본 항목: True/False = match, "error" = 호출 실패 판정.
def _scripted_eye_judge(monkeypatch, script):
    calls: list[dict] = []

    def fake(crop, claim, *, api_key, expected_limb=None, joint_kind=None,
             model=cg.DEFAULT_C_MODEL, timeout_s=60.0):
        i = len(calls)
        calls.append({"crop": crop, "claim": claim, "api_key": api_key,
                      "expected_limb": expected_limb, "joint_kind": joint_kind,
                      "model": model, "timeout_s": timeout_s})
        v = script[i]
        if v == "error":
            return {"observed": "error", "limb": None, "match": False,
                    "confidence": 0.0, "reason": f"r{i}:URLError"}
        return {"observed": "bent" if v else "extended", "limb": "leg",
                "match": bool(v), "confidence": 0.9, "reason": f"r{i}"}

    monkeypatch.setattr(cg, "eye_judge", fake)
    return calls


def test_eye_majority_first_match_no_extra_calls(monkeypatch):
    """첫 판정 일치 → 추가 호출 0, rounds=1, 형상 = eye_judge + rounds/votes."""
    calls = _scripted_eye_judge(monkeypatch, [True])
    res = cg.eye_judge_majority("crop", "bent", api_key="k", expected_limb="leg",
                                joint_kind="무릎")
    assert len(calls) == 1
    assert res["match"] is True and res["rounds"] == 1
    assert (res["votesTrue"], res["votesFalse"]) == (1, 0)
    assert res["reason"] == "r0"
    assert {"observed", "limb", "match", "confidence", "reason"} <= set(res)
    # kwarg 통과 — 운영 경로와 같은 질문(joint_kind)·사지·모델·타임아웃
    assert calls[0]["joint_kind"] == "무릎" and calls[0]["expected_limb"] == "leg"
    assert calls[0]["api_key"] == "k" and calls[0]["model"] == cg.DEFAULT_C_MODEL


def test_eye_majority_false_then_true_true_flips_to_true(monkeypatch):
    """[False, True, True] → 3회 다수결 True — 반환은 True 쪽 첫 결과(r1)."""
    calls = _scripted_eye_judge(monkeypatch, [False, True, True])
    res = cg.eye_judge_majority("crop", "bent", api_key="k", expected_limb="leg")
    assert len(calls) == 3
    assert res["match"] is True and res["rounds"] == 3
    assert (res["votesTrue"], res["votesFalse"]) == (2, 1)
    assert res["reason"] == "r1" and res["observed"] == "bent"
    # 같은 크롭·claim 을 세 번 모두 묻는다
    assert all(c["crop"] == "crop" and c["claim"] == "bent" for c in calls)


def test_eye_majority_false_false_true_stays_false(monkeypatch):
    """[False, False, True] → False 유지 — 반환은 False 쪽 첫 결과(r0)."""
    calls = _scripted_eye_judge(monkeypatch, [False, False, True])
    res = cg.eye_judge_majority("crop", "bent", api_key="k", expected_limb="leg")
    assert len(calls) == 3
    assert res["match"] is False and res["rounds"] == 3
    assert (res["votesTrue"], res["votesFalse"]) == (1, 2)
    assert res["reason"] == "r0"


def test_eye_majority_error_counts_as_false_vote(monkeypatch):
    """[False, error, True] → error 는 False 표 (fail-closed) → False."""
    calls = _scripted_eye_judge(monkeypatch, [False, "error", True])
    res = cg.eye_judge_majority("crop", "bent", api_key="k", expected_limb="leg")
    assert len(calls) == 3
    assert res["match"] is False and res["rounds"] == 3
    assert (res["votesTrue"], res["votesFalse"]) == (1, 2)
    assert res["reason"] == "r0"


def test_eye_majority_even_max_rounds_rejected(monkeypatch):
    """max_rounds 는 홀수만 — 짝수(동률 가능)·0 은 ValueError, 호출 0."""
    calls = _scripted_eye_judge(monkeypatch, [True, True, True, True])
    for n in (0, 2, 4):
        with pytest.raises(ValueError):
            cg.eye_judge_majority("crop", "bent", api_key="k", max_rounds=n)
    assert calls == []
    # 홀수 5 는 허용 — 첫 판정 일치면 여전히 1회
    res = cg.eye_judge_majority("crop", "bent", api_key="k", max_rounds=5)
    assert res["rounds"] == 1 and len(calls) == 1


def test_machine_eye_majority_kwarg(monkeypatch):
    """machine_eye(majority=False) 기본 = 종전 단발(추가 키 0); True 면 다수결 + rounds."""
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    calls = _scripted_eye_judge(monkeypatch, [False, False, True, True])
    single = cg.machine_eye(frame, (32.0, 32.0), "bent", api_key="k",
                            expected_limb="leg", joint_kind="무릎")
    assert len(calls) == 1 and single["match"] is False
    assert "rounds" not in single and "votesTrue" not in single
    assert "crop" in single
    maj = cg.machine_eye(frame, (32.0, 32.0), "bent", api_key="k",
                         expected_limb="leg", joint_kind="무릎", majority=True)
    assert len(calls) == 4
    assert maj["match"] is True and maj["rounds"] == 3
    assert (maj["votesTrue"], maj["votesFalse"]) == (2, 1)
    assert "crop" in maj
    assert calls[-1]["joint_kind"] == "무릎"


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
