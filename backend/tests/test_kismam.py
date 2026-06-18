"""KISMAM 점수/Top-3 — 결정적 검증. AWS 불필요."""

import numpy as np
import pytest

from sunity_shared.analysis import kismam
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS, PARTS


def test_zero_deviation_full_score():
    a = kismam.assess(np.zeros(NUM_JOINTS))
    assert all(j.score == 100 for j in a)
    assert kismam.overall_score(a) == 100
    ps = kismam.part_scores(a)
    assert set(ps) == set(PARTS)
    assert all(v == 100 for v in ps.values())


def test_score_monotonic_decreasing_with_deviation():
    # Phase 19 D-01 (모순 케이스 갱신): 재설계 감점식은 tolerance(20°) dead-zone 안에서는
    # 감점 0 — 따라서 단조성 검증은 dead-zone '밖' 의 편차로만 의미가 있다. 이전 15° 케이스는
    # tol=20° 미만이라 새 계약에서 감점 없이 동일 점수가 나올 수 있어 단조성이 깨진다.
    # 0°/30°/60° = 전부 tol=20° 초과 영역 → 편차가 커질수록 종합이 낮아져야 한다.
    dev0 = np.zeros(NUM_JOINTS)
    dev1 = np.full(NUM_JOINTS, 30.0)
    dev2 = np.full(NUM_JOINTS, 60.0)
    s0 = kismam.overall_score(kismam.assess(dev0))
    s1 = kismam.overall_score(kismam.assess(dev1))
    s2 = kismam.overall_score(kismam.assess(dev2))
    assert s0 > s1 > s2
    assert 0 <= s2 <= 100


def test_within_tolerance_remains_high():
    # Phase 19 D-01 (위양성 0 — sensitivity gate): 모든 관절 편차가 IPSF tolerance(20°)
    # 미만(10°)이면 자세는 '기준 안' 이므로 종합이 높게 유지돼야 한다 (감점 dead-zone).
    # IPSF Code of Points 각도 허용오차 20° 근거 (kismam._IPSF_TOLERANCE_DEG).
    dev = np.full(NUM_JOINTS, 10.0)
    score = kismam.overall_score(kismam.assess(dev))
    assert score >= 90


# ── Phase 19 D-01 신규 RED 케이스 (단독 실행 시 현재 평균식에 대해 behavior fail) ──


def test_single_major_fault_dominates():
    # SCORE-06: 한 관절만 큰 결함(50°), 나머지는 거의 정상(≈0°). 재설계 종합 점수는
    # 평균(희석)식이 낼 값보다 현저히 낮아야 한다 — 단일 major fault 가 종합을 지배.
    # 현재 평균식: 정상 7관절 ~100 + 결함 1관절 ~14 → (7*100 + 14)/8 ≈ 89. 평균은 결함을
    # 정상 관절에 희석한다 (Phase 15 94점 "거의 다 왔어요" 위양성의 근본원인,
    # 19-D05 known-answer 정합 — fault 1개가 종합을 끌어내려야 함).
    # 방향만 단언: 평균식 예상값(~89)에서 충분히 낮은 < 70 (보유 sweep 수치 타깃 아님).
    MEAN_FORMULA_EXPECTED = 89  # 현재 평균식이 내는 근사값 (희석 결과)
    dev = np.zeros(NUM_JOINTS)
    dev[JOINT_KEYS.index("left_knee")] = 50.0  # 단일 major fault
    score = kismam.overall_score(kismam.assess(dev))
    assert score < MEAN_FORMULA_EXPECTED - 19  # < 70 — major fault 지배(희석 금지)


def test_clean_pose_high_score():
    # SCORE-06 위양성 0 (sensitivity gate, above-cutoff): 모든 관절 편차가 tol(20°)
    # 미만이면 자세는 깨끗하므로 종합 high. 회귀 안전망 — 재설계가 정상 자세를 깎으면 FAIL.
    dev = np.full(NUM_JOINTS, 8.0)  # 전부 IPSF tolerance 안
    score = kismam.overall_score(kismam.assess(dev))
    assert score >= 90


def test_shoulder_focus_label():
    # TRUST-02: 어깨는 STATIC POSE ANGLE 차원이지 stability(떨림)가 아니다. 코칭 초점
    # 라벨이 '안정성'(stability=떨림 오인)이면 사용자에게 잘못된 교정 방향을 준다.
    # 현재 COACHING_FOCUS['left_shoulder']='안정성' → RED.
    for shoulder in ("left_shoulder", "right_shoulder"):
        focus = kismam.COACHING_FOCUS[shoulder]
        assert focus != "안정성"
        assert "떨림" not in focus
        # JOINT_LABEL_KO 에 이미 부위("어깨")가 있어 FOCUS 값에 부위 키워드 중복 금지.
        assert "어깨" not in focus


def test_tolerance_gaussian_value():
    # dev == tol → z=1 → 100*exp(-0.5) ≈ 61
    dev = np.zeros(NUM_JOINTS)
    j = JOINT_KEYS.index("left_knee")
    dev[j] = kismam.DEFAULT_TOLERANCE_DEG["left_knee"]
    a = kismam.assess(dev)
    assert a[j].score == pytest.approx(61, abs=1)


def test_top_issues_picks_worst_three():
    dev = np.zeros(NUM_JOINTS)
    dev[JOINT_KEYS.index("left_knee")] = 40
    dev[JOINT_KEYS.index("right_hip")] = 30
    dev[JOINT_KEYS.index("left_elbow")] = 20
    top = kismam.top_issues(kismam.assess(dev), n=3)
    assert [t.key for t in top] == ["left_knee", "right_hip", "left_elbow"]
    assert top[0].score <= top[1].score <= top[2].score


def test_assess_rejects_wrong_length():
    with pytest.raises(ValueError):
        kismam.assess(np.zeros(NUM_JOINTS + 1))


def test_part_scores_average_within_part():
    dev = np.zeros(NUM_JOINTS)
    # 하체(무릎)만 크게 → 하체 점수만 낮아야
    dev[JOINT_KEYS.index("left_knee")] = 60
    dev[JOINT_KEYS.index("right_knee")] = 60
    ps = kismam.part_scores(kismam.assess(dev))
    assert ps["하체"] < ps["상체"]
    assert ps["상체"] == 100 and ps["코어"] == 100
