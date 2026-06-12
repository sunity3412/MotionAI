"""MotionDTW 2단계 (ml_CLAUDE.md).

1단계: 슬라이딩 윈도우로 사용자 영상에서 동작 구간 탐색(준비/대기 제거).
2단계: 그 구간을 기준 모션과 정렬(매칭 경로) → 관절별 편차 산출.

MVP 는 Sakoe-Chiba 밴드 제약 DTW(반경 r) — 정통 FastDTW(Salvador&Chan)의
근사 대체. 반경 안에서는 정확하고 비용은 O(r·N). 추후 fastdtw 로 교체 가능
(인터페이스 동일).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _band(i: int, n: int, m: int, radius: int) -> tuple[int, int]:
    """행 i(1-base)에서 허용 열 범위. 대각선 ± radius, 길이비 보정."""
    center = (i - 1) * m / max(n, 1)
    lo = max(1, int(np.floor(center - radius)))
    hi = min(m, int(np.ceil(center + radius)) + 1)
    return lo, hi


def dtw(X, Y, radius: int | None = None):
    """DTW. X(n,D),Y(m,D) → (정규화거리, path[(i,j)...]).

    정규화거리 = 누적비용/(n+m) — 길이가 달라도 비교 가능.
    radius=None 이면 전역 DTW. band 가 너무 좁아 경로가 막히면 자동 확장.
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    n, m = len(X), len(Y)
    if n == 0 or m == 0:
        raise ValueError("빈 시퀀스는 DTW 불가")
    if radius is None:
        r = max(n, m)
    else:
        r = max(int(radius), abs(n - m) + 1)

    INF = np.inf
    D = np.full((n + 1, m + 1), INF)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        lo, hi = _band(i, n, m, r)
        xi = X[i - 1]
        for j in range(lo, hi + 1):
            cost = float(np.linalg.norm(xi - Y[j - 1]))
            D[i, j] = cost + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])

    if not np.isfinite(D[n, m]):
        # 밴드가 좁아 도달 실패 → 전역으로 재시도(드묾)
        return dtw(X, Y, radius=None)

    # 역추적
    path = []
    i, j = n, m
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        step = np.argmin([D[i - 1, j - 1], D[i - 1, j], D[i, j - 1]])
        if step == 0:
            i, j = i - 1, j - 1
        elif step == 1:
            i -= 1
        else:
            j -= 1
    path.reverse()
    return D[n, m] / (n + m), path


@dataclass(frozen=True)
class MotionMatch:
    start: int          # 사용자 시퀀스 동작 구간 시작 (프레임)
    end: int            # 끝 (exclusive)
    distance: float     # 정규화 DTW 거리 (작을수록 유사)
    path: list          # [(user_idx, ref_idx)...] (구간 로컬 인덱스 기준)


def find_action_segment(F_user, F_ref, radius: int = 12) -> tuple[int, int]:
    """1단계: ref 길이 윈도우를 사용자에 슬라이딩 → 최소거리 구간 (start,end)."""
    nu, nr = len(F_user), len(F_ref)
    if nu <= nr:
        return 0, nu  # 더 짧으면 통째로 사용
    step = max(1, (nu - nr) // 60)  # 비용 상한 (~60 윈도우)
    best = (0, nr, np.inf)
    for s in range(0, nu - nr + 1, step):
        d, _ = dtw(F_user[s : s + nr], F_ref, radius=radius)
        if d < best[2]:
            best = (s, s + nr, d)
    return best[0], best[1]


def motion_dtw(F_user, F_ref, radius: int = 12) -> MotionMatch:
    """2단계 포함 전체: 동작 구간 탐색 후 기준 모션과 정렬."""
    F_user = np.asarray(F_user, dtype=float)
    F_ref = np.asarray(F_ref, dtype=float)
    s, e = find_action_segment(F_user, F_ref, radius=radius)
    dist, path = dtw(F_user[s:e], F_ref, radius=radius)
    return MotionMatch(start=s, end=e, distance=float(dist), path=path)


def per_joint_deviation(path, A_user_seg, A_ref):
    """정렬 경로에서 관절별 median |Δ각도|(도). A_*: (T,J) 각도 행렬.

    KISMAM 입력. path 의 (u,r) 쌍마다 관절별 차이를 모아 **중앙값** 반환.

    Phase 17-debug (2026-06-12, gsd-debug same-video-score-mismatch):
      평균 → median 전환. RTMW 가 inverted/occluded 폴 자세에서 인접 frame 간
      10°+ jitter 를 만들고, p99 이 35~50° 에 달하는 outlier frame 이 다수.
      평균은 outlier 에 끌려가 mean angles 가 5° 차이여도 deviation = 20° 가
      산출 → KISMAM tol=20° 가 z=1.0 → score ≈ 60 으로 깎임 ("같은 영상인데
      만점이 안 나옴" 증상).
      Median 은 RTMW jitter 의 50% 이상이 noise 일 때 그 noise 의 중앙값을 반환
      (climb 5°, elbow-twist 12°) — clean 자세에선 영향 미미하고 noisy 자세에선
      mean angle 동일성을 충실히 반영. 같은 영상 self-compare 시 median(0) → 0
      보장 (DTW path 가 identity 면 모든 |Δ|=0).
      신호 (mean angles 가 일관적으로 다름) 는 median 으로도 잡힘 (path 의 모든
      frame 에서 같은 부호 차이 → median 도 그 차이값).
    """
    A_user_seg = np.asarray(A_user_seg, dtype=float)
    A_ref = np.asarray(A_ref, dtype=float)
    J = A_ref.shape[1]
    if not path:
        return np.zeros(J)
    # path 따라 (len(path), J) 차이 행렬 구축 → 관절별 median.
    diffs = np.empty((len(path), J), dtype=float)
    for k, (u, r) in enumerate(path):
        diffs[k] = np.abs(A_user_seg[u] - A_ref[r])
    return np.median(diffs, axis=0)
