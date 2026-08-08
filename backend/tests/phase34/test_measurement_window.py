"""Phase 34 수술 ② — 측정창 ref-경계 마진 제외 불변식 (quick-260808-r82).

fixture 기대점수 curve-fit 금지 — 전부 fixture-무관 합성 입력. 대상 성질:

  불변식 2  self-compare: 동일 각도 행렬 + ref_fps 지정 → median 전관절 0.
  불변식 4  fail-open: 경계 제외로 잔여 스텝 < 하한이면 종전 전-경로 산출과
            np.array_equal (극소 표본 급변 금지).
  마스크 성질: 경계 스텝만 False, margin 초→프레임 환산(9fps→5, 18fps→9),
            대표 프레임이 제외 스텝의 user 프레임 집합에서 나오지 않음.
  lockstep: REF_BOUNDARY_EXCLUDE_S == compare_verify.REF_BOUNDARY_PIN_S —
            상수 중복 정의의 단일 출처 강제(채점 코어→리그 import 0 계층 규율
            때문에 값 자체는 두 곳에 있고, 이 assert 가 동기화를 강제한다).
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis import motiondtw
from sunity_shared.analysis.motiondtw import (
    REF_BOUNDARY_EXCLUDE_S,
    _boundary_keep_floor,
    motion_dtw,
    per_joint_deviation,
    per_joint_representative_frames,
    ref_boundary_step_mask,
)


def _identity_path(n: int) -> list[tuple[int, int]]:
    return [(i, i) for i in range(n)]


def _angles(n, j=3, seed=0):
    """결정적 각도 시퀀스 (T,J) — 단조 성분 + 관절별 위상 (M3 테스트와 동일 서식)."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 4 * np.pi, n)
    cols = [30.0 * np.sin(t + k) + 5.0 * k for k in range(j)]
    base = np.stack(cols, axis=1)
    return base + rng.normal(0, 0.01, size=base.shape)


# ── 불변식 2: self-compare median 0 (제외 창 도입 후에도) ─────────────────────

def test_self_compare_zero_with_exclusion_window():
    """동일 각도 행렬을 motion_dtw 경로로 통과 + ref_fps=9.0 → 전관절 median 0.

    어느 분기(마스크 적용/fail-open)든 모든 |Δ|=0 이므로 0 보장 — 구조가 지킨다."""
    A = _angles(40, j=3, seed=1)
    match = motion_dtw(A, A)
    a_ref_win = A[match.ref_start : match.ref_end]
    user_seg = A[match.start : match.end]
    dev = per_joint_deviation(match.path, user_seg, a_ref_win, ref_fps=9.0)
    assert np.allclose(dev, 0.0), f"self-compare with window must be 0, got {dev}"


# ── 불변식 4: fail-open — 잔여 < 하한이면 종전과 동일 산출 ────────────────────

def test_fail_open_short_input_identical_to_legacy():
    """짧은 합성 입력(경계 제외 후 잔여 < max(3, ceil(0.5*len(path)))) →
    ref_fps 지정 산출 == ref_fps=None 산출 (np.array_equal, 급변 금지)."""
    # T=12, 9fps → margin 5: kept r ∈ [5,7) = 2 스텝 < floor max(3, 6)=6 → fail-open.
    T = 12
    path = _identity_path(T)
    ref = _angles(T, j=4, seed=2)
    user = ref + np.linspace(1.0, 9.0, T)[:, None]  # 비상수 편차(자명 0 회피)
    dev_none = per_joint_deviation(path, user, ref)
    dev_fps = per_joint_deviation(path, user, ref, ref_fps=9.0)
    assert np.array_equal(dev_none, dev_fps)
    # 대표 프레임도 동일 fail-open — 동일 dict.
    reps_none = per_joint_representative_frames(path, user, ref)
    reps_fps = per_joint_representative_frames(path, user, ref, ref_fps=9.0)
    assert reps_none == reps_fps


def test_fail_open_all_excluded_degenerate():
    """ref_len <= 2*margin (전 스텝 제외) → 전 스텝 False 마스크를 fail-open 이
    받아내 종전과 동일 산출."""
    T = 8  # 9fps margin 5 → 전 스텝 r<5 또는 r>=3 → 전부 False
    path = _identity_path(T)
    ref = _angles(T, j=2, seed=3)
    user = ref + 5.0
    mask = ref_boundary_step_mask(path, T, 9.0)
    assert not mask.any()
    assert np.array_equal(
        per_joint_deviation(path, user, ref),
        per_joint_deviation(path, user, ref, ref_fps=9.0),
    )


# ── 마스크 성질 ──────────────────────────────────────────────────────────────

def test_mask_margin_conversion_and_boundary_only():
    """margin 환산(9fps→5프레임, 18fps→9프레임) + 경계 스텝만 False."""
    ref_len = 40
    path = _identity_path(ref_len)
    for fps, margin in ((9.0, 5), (18.0, 9)):
        mask = ref_boundary_step_mask(path, ref_len, fps)
        for k, (_u, r) in enumerate(path):
            expected = margin <= r < ref_len - margin
            assert mask[k] == expected, f"fps={fps} step r={r}"
        assert int((~mask).sum()) == 2 * margin


def test_mask_is_window_axis_not_user_axis():
    """마스크는 ref(window) 축 기준 — user 축 인덱스는 판정에 미기여."""
    # user 인덱스를 전부 내부값(10)으로 고정해도 r 이 경계면 False.
    path = [(10, r) for r in range(20)]
    mask = ref_boundary_step_mask(path, 20, 9.0)
    assert not mask[0] and not mask[-1]
    assert mask[5] and mask[14]


def test_keep_floor_structure():
    """fail-open 하한 = max(3, ceil(0.5*n)) — 구조 유도 확인."""
    assert _boundary_keep_floor(4) == 3
    assert _boundary_keep_floor(7) == 4
    assert _boundary_keep_floor(20) == 10
    assert _boundary_keep_floor(21) == 11


# ── 대표 프레임: 제외 스텝에서 절대 안 나옴 (측정 순간 계약) ──────────────────

def test_representative_frame_moves_out_of_boundary():
    """경계에만 "median 을 정확히 겨누는" 편차를 심은 합성 형상 — 종전이면 경계
    스텝(gap 0)을 고르고, 수술 후엔 내부 스텝을 고른다. 대표 프레임이 제외 스텝
    user 프레임 집합에서 나오지 않음을 직접 검증."""
    T = 20  # 9fps margin 5 → 제외 r ∈ {0..4, 15..19}, kept 10 == floor 10 → 적용
    path = _identity_path(T)
    J = 1
    ref = np.zeros((T, J))
    user = np.zeros((T, J))
    # 경계 스텝 |Δ|=10, 내부 |Δ| = {2,4,6,8,12,14,16,18,20,22} (10 비포함, 10 straddle).
    boundary = list(range(0, 5)) + list(range(15, 20))
    interior_vals = [2.0, 4.0, 6.0, 8.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0]
    for i in boundary:
        user[i, 0] = 10.0
    for k, i in enumerate(range(5, 15)):
        user[i, 0] = interior_vals[k]
    # 종전(전 경로): 전체 median = 10 → gap 0 인 경계 스텝이 뽑힘.
    reps_before = per_joint_representative_frames(path, user, ref)
    assert reps_before[0] in boundary, f"종전 형상 확인 실패: {reps_before}"
    # 수술 후: 마스크 적용 → median = 13(내부만) → 내부 스텝만 후보(제외 스텝 inf).
    reps_after = per_joint_representative_frames(path, user, ref, ref_fps=9.0)
    assert reps_after[0] not in boundary, (
        f"대표 프레임이 제외 스텝에서 나옴: {reps_after}"
    )
    assert 5 <= reps_after[0] < 15
    # 점수(median)도 같은 창: 전체 10 → 내부 13.
    dev_before = per_joint_deviation(path, user, ref)
    dev_after = per_joint_deviation(path, user, ref, ref_fps=9.0)
    assert dev_before[0] == 10.0
    assert dev_after[0] == 13.0


def test_representative_frame_start_offset_respected():
    """start(절대 오프셋) 가 마스크 경로에서도 그대로 더해진다."""
    T = 20
    path = _identity_path(T)
    ref = np.zeros((T, 1))
    user = np.ones((T, 1)) * 3.0
    start = 7
    reps = per_joint_representative_frames(path, user, ref, start, ref_fps=9.0)
    assert 0 in reps
    # 전 스텝 동일 편차 → 첫 kept 스텝(=5) + start.
    assert reps[0] == start + 5


# ── lockstep: 채점층 상수 == 리그층 상수 (단일 출처 강제) ─────────────────────

def test_lockstep_with_render_rig_pin():
    """motiondtw.REF_BOUNDARY_EXCLUDE_S == compare_verify.REF_BOUNDARY_PIN_S.

    채점 코어가 리그 모듈을 import 하지 않는 계층 규율(코어→리그 금지) 때문에 값이
    두 곳에 있다 — 리그 쪽이 바뀌면 여기가 트립해 동기화를 강제한다."""
    from sunity_shared.analysis import compare_verify

    assert REF_BOUNDARY_EXCLUDE_S == compare_verify.REF_BOUNDARY_PIN_S
    assert motiondtw.REF_BOUNDARY_EXCLUDE_S == 0.5
