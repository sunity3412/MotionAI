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

from . import moment
from .skeleton import JOINT_KEYS


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


# ── M3 정렬 게이트 상수 (33-M3-SPEC.md §8 — 정렬 substrate, 채점 상수 아님) ──────
# D-20/D-29 재확인: 아래 3상수는 **정렬 게이트**다. 감점 산식·tol 20°·slope 1.2·cap·
# epsilon 은 전부 불변(재fit 0). gate 가 걸리면 임계를 올리지 말고 원인을 조사한다.
COVERAGE_FLOOR = 0.80        # nu/nr 이 미만이면 기준 미트리밍(전체 정렬) — §2.1
AMBIGUITY_EPSILON = 0.02     # 근-동률 window 판정(정규화 DTW 거리) — §4-3
AMBIGUITY_OVERLAP_MIN = 0.80  # 근-동률 후보 프레임 집합 겹침(Jaccard) 하한 — §4-3


@dataclass(frozen=True)
class MotionMatch:
    start: int          # 사용자 시퀀스 동작 구간 시작 (프레임, inclusive)
    end: int            # 사용자 끝 (exclusive)
    ref_start: int      # 기준 window 시작 (프레임, inclusive) — 33-M3-SPEC.md §1.1 NEW
    ref_end: int        # 기준 window 끝 (exclusive) — NEW
    distance: float     # 정규화 DTW 거리 (작을수록 유사)
    path: list          # [(user_local_idx, ref_local_idx)...]
                        #   두 인덱스 모두 **window-local**:
                        #   user_local ∈ [0, end-start), ref_local ∈ [0, ref_end-ref_start).
                        #   ref 통째면(ref_start=0, ref_end=nr) 현행과 byte-identical.


def _slide_windows(long_seq, short_seq, radius: int) -> list[tuple[int, float]]:
    """긴 시퀀스에서 short 길이 window 를 슬라이딩 → [(start, 정규화DTW거리), ...] 전체 후보.

    step 상한은 현행과 동일(~60 window). best 지표도 현행과 같은 dtw 정규화 거리 —
    새 지표 도입 금지(33-M3-SPEC.md §1.2). window 는 연속(contiguous) 구간만.
    """
    nlong, nshort = len(long_seq), len(short_seq)
    step = max(1, (nlong - nshort) // 60)
    cands: list[tuple[int, float]] = []
    for s in range(0, nlong - nshort + 1, step):
        d, _ = dtw(long_seq[s : s + nshort], short_seq, radius=radius)
        cands.append((s, float(d)))
    return cands


def _window_ambiguous(
    cands: list[tuple[int, float]], best_start: int, best_dist: float, win: int
) -> bool:
    """best window 와 AMBIGUITY_EPSILON 이내인 다른 후보가 **실질적으로 다른 기준
    프레임 집합**(Jaccard 겹침 < AMBIGUITY_OVERLAP_MIN)을 선택하면 True(모호).

    근-동률 후보가 서로 다른 국면을 남기면(준비 vs 기술) min-distance 임의 선택이
    팽창 window 를 고를 수 있어 §4 fail-closed 로 전체 기준 폴백한다.
    """
    b0, b1 = best_start, best_start + win
    for s, d in cands:
        if s == best_start:
            continue
        if abs(d - best_dist) > AMBIGUITY_EPSILON:
            continue
        inter = max(0, min(b1, s + win) - max(b0, s))
        union = (b1 - b0) + win - inter
        jaccard = inter / union if union > 0 else 1.0
        if jaccard < AMBIGUITY_OVERLAP_MIN:
            return True
    return False


def find_action_segment(
    F_user, F_ref, radius: int = 12, ref_boundary: int | None = None
) -> tuple[tuple[int, int], tuple[int, int]]:
    """1단계: (사용자 (u_s,u_e), 기준 (r_s,r_e)) paired range 를 함께 반환.

    긴 쪽을 짧은 쪽 길이로 min-DTW 슬라이딩(양방향 대칭), 짧은 쪽은 통째. 준비/대기
    제거는 긴 쪽에서 발생한다. 어느 쪽도 통째면 (0, n). 33-M3-SPEC.md §1.2/§2/§3/§4.

    ref_boundary: 공유 베이스 기술의 base/확장 경계(전체 ref 프레임 인덱스). 주어지면
      nu<nr window 가 경계를 내부에 엄격히 두지 못할 때 §4 fail-closed(§2.2 구조 바닥).
      None 이면 구조 바닥 미적용(일반 reference).

    동작 id/technique 로 분기하지 않는다(D-02, I3) — 전역 규칙의 두 방향일 뿐이다.
    """
    F_user = np.asarray(F_user, dtype=float)
    F_ref = np.asarray(F_ref, dtype=float)
    nu, nr = len(F_user), len(F_ref)

    if nu == nr:
        return (0, nu), (0, nr)  # 둘 다 통째

    if nu > nr:
        # 현행 유지: 사용자를 nr 길이로 슬라이딩, 기준 통째(이미 발동하는 경로).
        cands = _slide_windows(F_user, F_ref, radius)
        best_s = min(cands, key=lambda c: c[1])[0]
        return (best_s, best_s + nr), (0, nr)

    # nu < nr — 신규 경로(핵심 수정): 기준을 nu 길이로 슬라이딩. §2 두 바닥 통과 시에만.
    # §2.1 수치 바닥 — coverage floor. nu<nr 에서 유지 기준 비율 = nu/nr.
    if nu / nr < COVERAGE_FLOOR:
        return (0, nu), (0, nr)  # fail-closed 전체 기준 (팽창 불가)
    cands = _slide_windows(F_ref, F_user, radius)
    best_rs, best_dist = min(cands, key=lambda c: c[1])
    # §4-3 모호 window → fail-closed.
    if _window_ambiguous(cands, best_rs, best_dist, nu):
        return (0, nu), (0, nr)
    # §2.2 구조 바닥 — 공유 베이스 경계가 window 내부에 엄격히.
    if ref_boundary is not None and not (best_rs < ref_boundary < best_rs + nu):
        return (0, nu), (0, nr)
    return (0, nu), (best_rs, best_rs + nu)


def motion_dtw(
    F_user, F_ref, radius: int = 12, ref_boundary: int | None = None
) -> MotionMatch:
    """2단계 포함 전체: paired 동작 구간 탐색 후 windowed 양쪽을 DTW 정렬.

    33-M3-SPEC.md §1.3 — dtw 는 windowed 양쪽(F_ref[r_s:r_e])을 받으므로 path 의 ref
    인덱스는 자동으로 window-local 이다. ref 통째면 현행과 byte-identical.
    """
    F_user = np.asarray(F_user, dtype=float)
    F_ref = np.asarray(F_ref, dtype=float)
    (u_s, u_e), (r_s, r_e) = find_action_segment(
        F_user, F_ref, radius=radius, ref_boundary=ref_boundary
    )
    dist, path = dtw(F_user[u_s:u_e], F_ref[r_s:r_e], radius=radius)
    return MotionMatch(
        start=u_s, end=u_e, ref_start=r_s, ref_end=r_e,
        distance=float(dist), path=path,
    )


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


def per_joint_representative_frames(
    path, A_user_seg, A_ref, start=0, *, frame_confidence=None
):
    """관절별 "그 관절이 보고한 median 에 가장 가까운" 정렬 스텝의 학생 프레임.

    quick-260801-gbk — 감점 record 가 보고한 집계값을 **어느 프레임에서 쟀는지**
    되돌려 준다. per_joint_deviation 은 관절별 median 만 반환하고 그것을 만든 시계열
    축을 버리는데, 확대비교 카드가 써야 할 순간이 바로 그 버려진 축에 있다.

    **per_joint_deviation 본체는 건드리지 않는다.** 그 함수 소스의 SHA-256 이
    backend/tests/phase33/test_m3_alignment_only.py 에 박제돼 있어 반환값 확장이나
    out-param 추가는 전부 그 게이트를 깬다. 같은 diffs 순회를 sibling 으로 복제한다
    (중복이지만 박제를 우회하지 않고 통과하는 유일한 길).

    **argmax(최대 편차 프레임)를 쓰지 않는다.** 근거는 이 파일 198-209행 — 인접
    프레임 간 각도 jitter 가 크고 상위 백분위 outlier 가 흔하다. 최대 편차 프레임은
    그 outlier 프레임일 확률이 높고, 그것을 "여기가 감점 부분"이라며 확대해 보여주면
    지금보다 나빠진다. median 에 가장 가까운 스텝을 고르면 record 가 실제로 보고한
    값과 같은 순간을 가리킨다.

    Args:
        path: [(user_local, ref_idx), ...] — per_joint_deviation 과 동일 입력.
        A_user_seg: (T,J) 학생 구간 각도 = angles[start:end].
        A_ref: (T,J) 기준 각도.
        start: 학생 구간 시작 절대 인덱스(MotionMatch.start). path 의 user 축은
            구간-로컬이라 절대 프레임으로 되돌리려면 이 값을 더해야 한다.
        frame_confidence (quick-260802-tie): `(절대 프레임, joint_keys) -> 0..1 | None`.
            median 과의 거리가 **동점인 스텝들 사이에서만** 쓰인다
            (`moment.TIE_EPS`). DTW path 는 같은 학생 프레임을 여러 스텝이 가리킬 수
            있고 인접 스텝의 각도차가 소수점 아래에서 갈리는 일이 잦아, 어느 스텝이
            뽑히느냐가 keypoint 신뢰도와 무관하게 정해지던 자리다. None(default)=
            종전 argmin 과 byte-동일.

    Returns:
        {joint_index: 학생 절대 프레임 인덱스}. path 가 비면 빈 dict. 유한 diff 가
        없거나 median 이 비유한인 관절은 키 부재(fail-closed) — 그 관절은 감점
        record 도 방출되지 않으므로 순간만 남는 일이 없다.
    """
    A_user_seg = np.asarray(A_user_seg, dtype=float)
    A_ref = np.asarray(A_ref, dtype=float)
    J = A_ref.shape[1]
    if not path:
        return {}
    diffs = np.empty((len(path), J), dtype=float)
    for k, (u, r) in enumerate(path):
        diffs[k] = np.abs(A_user_seg[u] - A_ref[r])
    base = int(start)
    out: dict[int, int] = {}
    for j in range(J):
        col = diffs[:, j]
        finite = np.isfinite(col)
        if not finite.any():
            continue
        med = float(np.median(col))
        if med != med:  # NaN median — 그 관절 record 자체가 방출되지 않는다.
            continue
        # 비유한 스텝은 후보에서 제외(inf 로 밀어냄). 동점은 argmin 이 첫 스텝을
        # 고르므로 결정론적 — quick-260802-tie 는 그 동점 구간에서만 신뢰도를 본다.
        gaps = np.where(finite, np.abs(col - med), np.inf)
        jk = JOINT_KEYS[j] if j < len(JOINT_KEYS) else None
        k_star = moment.select_moment_index(
            gaps,
            confidence=(
                None
                if frame_confidence is None or jk is None
                else (
                    lambda k, _jk=jk: frame_confidence(
                        base + int(path[int(k)][0]), (_jk,)
                    )
                )
            ),
        )
        if k_star is None:
            continue
        out[j] = base + int(path[int(k_star)][0])
    return out
