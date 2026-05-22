"""시간축 폐색 보간 — NLF 불확실도로 접힌·가려진 프레임을 복원 (#7-follow).

NLF 는 단일 프레임 3D 백본이라 가장 접힌 인버트 프레임은 점군이 덩어리로
뭉친다(plan.md #7-follow — 검증됨). 폴스포츠의 1~2초 폐색은 단일 프레임으론
못 풀고 *시퀀스*로 푼다(docs/research §D). 학습형 motion prior(TEMP3D) 대신
실용형 — NLF per-joint 불확실도를 신호로 한 시간축 가중 보간을 쓴다.

핵심: 절대 임계(보정 상수)를 두지 않는다. 한 관절의 불확실도 분포에서
*상대적으로* 튀는 프레임만 폐색으로 보고 인접 신뢰 프레임에서 선형 보간한
뒤, 신뢰도 가중 이동평균으로 지터를 다듬는다. 영상마다 불확실도 스케일이
달라도 동작한다.

입출력 모두 관절각 (T,J) — features.compute_joint_angles 출력. 불확실도
(T,J) 는 features.joint_uncertainty 출력. 코어(motiondtw/kismam)는 이
모듈을 거친 각도를 받는다.
"""

from __future__ import annotations

import numpy as np

# 불확실도 이상치 판정 — median + k·1.4826·MAD 초과를 폐색 의심으로.
DEFAULT_OUTLIER_K = 3.0
# 한 관절의 프레임 중 이 비율을 넘게 폐색으로 잡히면 상대 판정을 믿지 않는다
# (그 관절이 영상 내내 불확실한 것일 뿐) → NaN 프레임만 보간한다.
DEFAULT_MAX_BAD_FRAC = 0.4
# 신뢰도 가중 이동평균 창 크기(프레임). 1 이면 스무딩 생략.
DEFAULT_SMOOTH_WINDOW = 5
# 이동평균에서 폐색·보간 프레임에 주는 가중치(신뢰 프레임 1.0 대비).
DEFAULT_BAD_WEIGHT = 0.25


def _column_outliers(u: np.ndarray, k: float) -> np.ndarray:
    """불확실도 1열(T,) → 폐색 의심 bool(T,). NaN/inf 는 무조건, 나머지는 MAD.

    신뢰 프레임 불확실도가 거의 한 값으로 뭉치면 MAD 가 0 이 된다(폐색 프레임을
    못 잡는 MAD 의 고전적 붕괴). 그 경우 그 한 값보다 높은 프레임을 이상치로
    본다 — 일정한 bulk 위로 솟은 프레임이 곧 폐색 신호.
    """
    bad = ~np.isfinite(u)
    finite = u[np.isfinite(u)]
    if finite.size >= 4:
        med = float(np.median(finite))
        mad = float(np.median(np.abs(finite - med)))
        if mad > 0:
            bad = bad | (u > med + k * 1.4826 * mad)
        else:
            bad = bad | (u > med)
    return bad


def occluded_mask(
    angles,
    uncertainty=None,
    *,
    outlier_k: float = DEFAULT_OUTLIER_K,
    max_bad_frac: float = DEFAULT_MAX_BAD_FRAC,
) -> np.ndarray:
    """관절각 (T,J)[+ 불확실도 (T,J)] → 폐색 프레임 bool 마스크 (T,J).

    각 관절 열에서 NaN 각도 + (불확실도 주어지면) 상대 이상치를 폐색으로 본다.
    한 열의 폐색 비율이 max_bad_frac 초과면 상대 판정을 버리고 NaN 만 남긴다.
    """
    a = np.asarray(angles, dtype=float)
    if a.ndim != 2:
        raise ValueError("angles 는 (T,J) 2차원이어야 합니다.")
    mask = np.isnan(a)
    if uncertainty is None:
        return mask
    u = np.asarray(uncertainty, dtype=float)
    if u.shape != a.shape:
        raise ValueError("uncertainty 형상이 angles 와 같아야 합니다.")
    for c in range(a.shape[1]):
        nan_bad = mask[:, c]
        bad = nan_bad | _column_outliers(u[:, c], outlier_k)
        if bad.mean() > max_bad_frac:
            bad = nan_bad
        mask[:, c] = bad
    return mask


def _interp_column(col: np.ndarray, bad: np.ndarray) -> np.ndarray:
    """폐색 프레임을 인접 신뢰 프레임에서 선형 보간. 전부 폐색이면 0."""
    out = col.astype(float).copy()
    good = ~bad
    n_good = int(good.sum())
    if n_good == 0:
        out[:] = 0.0
    elif n_good < col.size:
        idx = np.arange(col.size)
        out[bad] = np.interp(idx[bad], idx[good], col[good])
    return out


def _smooth_column(
    col: np.ndarray, bad: np.ndarray, window: int, bad_weight: float
) -> np.ndarray:
    """신뢰도 가중 이동평균. 폐색·보간 프레임은 bad_weight 로 낮춰 섞는다."""
    if window <= 1:
        return col
    T = col.size
    rel = np.where(bad, bad_weight, 1.0)
    half = window // 2
    out = col.copy()
    for t in range(T):
        lo, hi = max(0, t - half), min(T, t + half + 1)
        w = rel[lo:hi]
        sw = float(w.sum())
        out[t] = float(np.dot(col[lo:hi], w) / sw) if sw > 0 else col[t]
    return out


def temporal_fill(
    angles,
    uncertainty=None,
    *,
    outlier_k: float = DEFAULT_OUTLIER_K,
    max_bad_frac: float = DEFAULT_MAX_BAD_FRAC,
    smooth_window: int = DEFAULT_SMOOTH_WINDOW,
    bad_weight: float = DEFAULT_BAD_WEIGHT,
) -> np.ndarray:
    """관절각 (T,J) → 폐색 보간 + 신뢰도 가중 스무딩한 각도 (T,J).

    uncertainty(T,J) 가 주어지면 불확실도 상대 이상치 + NaN 을 폐색으로 보고
    보간한다. 없으면 NaN 만 보간한다(features.fill_gaps 와 동등 + 스무딩).
    파이프라인은 fill_gaps 대신 이 함수를 쓴다.
    """
    a = np.asarray(angles, dtype=float)
    if a.ndim != 2:
        raise ValueError("angles 는 (T,J) 2차원이어야 합니다.")
    mask = occluded_mask(
        a, uncertainty, outlier_k=outlier_k, max_bad_frac=max_bad_frac
    )
    out = np.empty_like(a)
    for c in range(a.shape[1]):
        col = _interp_column(a[:, c], mask[:, c])
        out[:, c] = _smooth_column(col, mask[:, c], smooth_window, bad_weight)
    return out
