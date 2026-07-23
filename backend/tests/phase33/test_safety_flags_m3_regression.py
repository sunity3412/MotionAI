"""33-05 M3 ripple S3 — safety_flags 회귀 (33-M3-SPEC.md §5 S3 / §6.1).

`safety_flags._dtw_aligned_joint_medians`(:222) 는 점수 경로와 동일한 `motion_dtw`
를 INTERNAL 로 재계산한다(D-07). M3 가 path 의 ref 인덱스를 window-local 로 바꾸므로
이 소비자도 windowed reference 를 써야 한다 — 안 그러면 잘못된 프레임을 읽어 안전
플래그가 조용히 위양성/위음성으로 회귀한다.

이 테스트는 window 변경 전후 안전 정렬 medians 가 **정렬 불변 케이스에서 byte-identical**
임을 증명해 "신규 FP/FN 0"(SEED 성공판정 #6)을 고정한다:
  - nu==nr(이미 정렬) → window = 전체 → medians 가 전체-기준 재현과 동일.
  - nu<nr coverage 미달 → fail-closed 전체 기준 → 역시 전체와 동일.
  - nu<nr window 발동 → windowed ref 로 일관 산출(인덱스 어긋남·NaN 0).
"""

from __future__ import annotations

import numpy as np

from sunity_shared.analysis import safety_flags
from sunity_shared.analysis.features import feature_vector
from sunity_shared.analysis.motiondtw import dtw, motion_dtw
from sunity_shared.analysis.skeleton import JOINT_KEYS, NUM_JOINTS


def _angles(n, seed=0, offset=0.0):
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 4 * np.pi, n)
    cols = [40.0 * np.sin(t + k) + 3.0 * k + offset for k in range(NUM_JOINTS)]
    base = np.stack(cols, axis=1)
    return base + rng.normal(0, 0.02, size=base.shape)


def _ref_medians_full(a_user, a_ref):
    """pre-M3 등가: 전체 기준으로 DTW 정렬 후 관절별 finite median(ref).

    `_dtw_aligned_joint_medians` 의 회귀 기준값. window 가 전체일 때 두 값이 같아야 한다.
    """
    match = motion_dtw(feature_vector(a_user), feature_vector(a_ref))
    seg = a_user[match.start : match.end]
    # pre-M3 는 ref 통째 인덱싱 — nu==nr / fail-closed 케이스는 ref_start==0 이므로 동일.
    a_ref_win = a_ref[match.ref_start : match.ref_end]
    J = min(a_ref_win.shape[1], seg.shape[1], len(JOINT_KEYS))
    ref_vals: list[list[float]] = [[] for _ in range(J)]
    for u, r in match.path:
        if u >= seg.shape[0] or r >= a_ref_win.shape[0]:
            continue
        for j in range(J):
            rv = a_ref_win[r, j]
            if np.isfinite(rv):
                ref_vals[j].append(float(rv))
    out: dict[str, float] = {}
    for j in range(J):
        if ref_vals[j]:
            out[JOINT_KEYS[j]] = float(np.median(ref_vals[j]))
    return out


def test_safety_medians_byte_identical_when_aligned():
    """nu==nr(이미 정렬) → S3 medians 가 전체-기준 재현과 완전히 동일(신규 FP/FN 0)."""
    a_user = _angles(50, seed=10)
    a_ref = _angles(50, seed=10, offset=5.0)  # nu==nr
    user_med, ref_med = safety_flags._dtw_aligned_joint_medians(
        a_user, a_ref, JOINT_KEYS
    )
    ref_expected = _ref_medians_full(a_user, a_ref)
    assert set(ref_med) == set(ref_expected)
    for k in ref_expected:
        assert ref_med[k] == ref_expected[k], f"{k}: {ref_med[k]} != {ref_expected[k]}"
    assert user_med  # non-empty


def test_safety_medians_stable_under_coverage_floor_fallback():
    """nu<nr coverage<0.80 → fail-closed 전체 기준 → medians 가 전체 재현과 동일."""
    a_user = _angles(30, seed=11)
    a_ref = _angles(50, seed=11, offset=2.0)  # 30/50 = 0.60 < floor
    user_med, ref_med = safety_flags._dtw_aligned_joint_medians(
        a_user, a_ref, JOINT_KEYS
    )
    ref_expected = _ref_medians_full(a_user, a_ref)
    assert set(ref_med) == set(ref_expected)
    for k in ref_expected:
        assert ref_med[k] == ref_expected[k]


def test_safety_medians_finite_when_window_fires():
    """nu<nr window 발동(coverage>=0.80) → windowed ref 로 finite median 산출.
    인덱스 어긋남/NaN 오염 0 (S3 ripple 이 windowed reference 를 정확히 소비)."""
    core = _angles(48, seed=12)
    pad = np.zeros((4, NUM_JOINTS))
    a_ref = np.concatenate([pad, core, pad])  # nr=56
    a_user = core.copy()  # nu=48, 48/56 ≈ 0.857
    match = motion_dtw(feature_vector(a_user), feature_vector(a_ref))
    assert match.ref_start > 0 or match.ref_end < len(a_ref)  # window 실제 발동
    user_med, ref_med = safety_flags._dtw_aligned_joint_medians(
        a_user, a_ref, JOINT_KEYS
    )
    assert ref_med and user_med
    assert all(np.isfinite(v) for v in ref_med.values())
    assert all(np.isfinite(v) for v in user_med.values())


def test_safety_medians_no_index_error_on_windowed_path():
    """windowed path 의 ref 인덱스가 window-local 이므로 전체 ref 로 인덱싱하면
    IndexError/오채점. S3 가 windowed ref 를 쓰면 예외 없이 통과."""
    core = _angles(46, seed=13)
    a_ref = np.concatenate([np.zeros((6, NUM_JOINTS)), core])  # nr=52, 앞 6 준비
    a_user = core.copy()  # nu=46, 46/52 ≈ 0.885
    # 예외 없이 완주 + 관절 medians present.
    user_med, ref_med = safety_flags._dtw_aligned_joint_medians(
        a_user, a_ref, JOINT_KEYS
    )
    assert ref_med
