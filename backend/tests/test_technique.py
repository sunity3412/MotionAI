"""기술 인식 fallback — 보수적 프로파일 검증. AWS·모델 불필요.

철학: 모르면 깎지 않는다. 명백히 펴진 팔꿈치/무릎만 EXTEND, 나머지는 BENT_OK.
대칭 가정 안 함(폴 동작은 비대칭이 정상).
"""

import numpy as np

from sunity_shared.analysis import technique
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS


def _pose(straight: list[str], t: int = 20) -> np.ndarray:
    base = np.full(NUM_JOINTS, 100.0)  # 기본은 굽은 상태
    for k in straight:
        base[JOINT_KEYS.index(k)] = 175.0
    return np.tile(base, (t, 1))


def test_straight_limbs_marked_extend():
    p = technique.FallbackRecognizer().recognize(_pose(["left_knee", "right_knee"]))
    assert p.expects_extension("left_knee")
    assert p.expects_extension("right_knee")


def test_bent_limbs_not_forced_to_extend():
    # 굽은 팔꿈치(100°)는 의도된 굽힘일 수 있어 신전 기대 안 함(위양성 방지).
    p = technique.FallbackRecognizer().recognize(_pose([]))
    assert not p.expects_extension("left_elbow")
    assert not p.expects_extension("left_knee")


def test_shoulders_hips_never_extend():
    # 어깨/고관절은 '폄' 의미가 모호 → 신전 평가 대상 아님(설령 175°라도).
    p = technique.FallbackRecognizer().recognize(_pose(["left_shoulder", "left_hip"]))
    assert not p.expects_extension("left_shoulder")
    assert not p.expects_extension("left_hip")


def test_fallback_is_not_symmetric_and_unknown():
    p = technique.FallbackRecognizer().recognize(_pose([]))
    assert p.is_symmetric is False
    assert p.category == "unknown"


def test_empty_input_does_not_crash():
    p = technique.FallbackRecognizer().recognize(np.zeros((0, NUM_JOINTS)))
    assert set(p.joint_expectations) == set(JOINT_KEYS)
