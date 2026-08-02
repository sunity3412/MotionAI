"""측정 불확실도 — 감점 record 가 하는 단정을 그 값 자신의 표본으로 검정한다.

quick-260802-nse.

감점 record 가 하는 주장은 하나다: **"이 관절의 편차가 허용치를 넘는다."** 그 주장의
근거인 `measuredValue` 는 점추정(median)이고, 점추정에는 불확실도가 따라붙는다.
이 모듈은 그 불확실도를 **그 값을 만든 바로 그 표본**에서 유도한다. 판정 규칙은
호출부(deduction_engine)에 있고 여기는 구간만 낸다.

## 방법 — 순서통계 기반 분포무관(부호검정) median 신뢰구간

정렬 경로 각 스텝의 `|Δ각도|` 열이 표본이다. 그 열의 순서통계 `x_(k)` 와 `x_(n+1-k)`
를 양 끝으로 쓰는 구간의 피복확률은 정확히

    P(x_(k) <= median <= x_(n+1-k)) = 1 - 2 * Σ_{i<k} C(n,i) / 2^n

이다(부호검정의 이항 꼬리). 이 값이 `1-alpha` 이상이 되는 **최대** k 를 고른다.

### 해석적 근사(`1.253 * sigma / sqrt(N)`)를 쓰지 않는 이유 — 자기모순이다

`motiondtw.per_joint_deviation` 이 mean 대신 median 을 고른 근거가 그 함수 독스트링에
적혀 있다: 포즈 추정이 inverted/occluded 자세에서 프레임간 큰 jitter 를 만들고 상위
백분위 outlier 가 흔해서 mean 이 끌려간다는 것. 표준편차는 **바로 그 outlier 가
지배하는 통계량**이다. median 이 무시하려고 고른 것으로 median 의 오차를 재는 셈이
된다. 그 근사가 요구하는 정규성 가정도 같은 문장과 정면으로 충돌한다.

### 부트스트랩을 쓰지 않는 이유

프로덕션에 난수 시드라는 새 임의 상수가 들어오고 결정성이 시드에 매달린다. 스칼라
median 하나에 대해 정확한 순서통계 구간보다 나은 정확도를 주지도 않는다.

### 순서통계를 쓰는 이유

정확(이항, 점근 근사 0) · 분포무관 · 결정적(난수 0) · `np.median` 이 이미 하는 정렬
한 번 · 그리고 구간의 양 끝이 **실제로 관측된 `|Δ|` 값**이다(외삽한 숫자가 아니다).

## 알려진 한계 — 독립 가정 위반, 그리고 그 편향의 방향

부호검정 피복확률은 표본이 독립일 때의 값이다. DTW 경로 스텝은 독립이 아니다 — 같은
학생 프레임을 여러 스텝이 가리키고 인접 프레임은 상관이 크다. 따라서 유효 표본수는 n
보다 작고, 이 구간은 **참 구간보다 좁다**. 좁은 구간 → 하한이 높음 → 억제가 덜 걸림
= 종전대로 감점하는 쪽. 즉 이 편향은 **fail-closed 방향**이다. 자기상관 보정을 넣지
않는 것은 그것이 곧 새 튜닝 상수이기 때문이다.

numpy 외 의존 0 — boto3/firestore/네트워크 import 금지(deduction_engine 과 같은 규율).
난수 0, 전역 상태 0, 순수 함수만.
"""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from math import comb

import numpy as np

# 신뢰수준 = 양측 95% (alpha = 0.05).
#
# **왜 이 수준인가:** 감점 record 는 "이 관절의 편차가 허용치를 넘는다"는 **단정**을
# 한다. 95% 는 단정을 세울 때 쓰는 관례 수준이다. 이 값은 fixture 결과를 보고 고른
# 것이 **아니다** — 어떤 실측 표에서도 유도되지 않았고, 효과가 기대와 다르게 나오면
# 그것은 보고할 발견이지 돌릴 손잡이가 아니다.
#
# 이 수준이 임의 상수가 아님을 무엇이 지키는가: 신뢰수준의 **정의적 성질**(참 median
# 을 덮는 비율이 1-alpha 이상)을 `backend/tests/test_measurement_error.py` 의 커버리지
# 테스트가 정규·두꺼운꼬리 두 분포에서 되읽는다. `moment.RECORD_VALUE_DECIMALS` 가
# 엔진 출력에서 자릿수를 되읽는 것과 같은 종류의 잠금이다.
CI_ALPHA = 0.05


@lru_cache(maxsize=None)
def median_ci_order_index(n: int, alpha: float = CI_ALPHA) -> int | None:
    """양측 `1-alpha` 분포무관 median 구간의 1-indexed 순서통계 k.

    구간은 `[x_(k), x_(n+1-k)]`(정렬 오름차순, 1-indexed). 정확 이항 꼬리
    `Σ_{i<k} C(n,i) / 2^n <= alpha/2` 를 만족하는 **최대** k 를 반환한다.
    정규 근사를 쓰지 않는다 — 비교는 전부 정수 산술이라 부동소수 오차가 0이다.

    k <= (n+1)//2 로 제한한다. 이 상한은 구간이 `np.median` 을 실제로 **묶는다**는
    것을 홀·짝 양쪽에서 보장한다(짝수 n 의 median 은 가운데 두 값의 평균이므로
    k <= n/2 여야 하고, (n+1)//2 는 짝수 n 에서 정확히 n/2 다). 꼬리 조건이 이미
    훨씬 작은 k 를 주므로 실제로 발동하지 않지만, 성질을 코드가 지키게 둔다.

    n 이 최소표본 미만이면 `None`(fail-closed). 최소표본은 상수가 아니라 이 조건에서
    유도된다 — k=1 조차 성립하려면 `2^-n <= alpha/2`, 즉 `n >= log2(2/alpha)`.
    `min_sample_size` 참조.
    """
    if n < 1:
        return None
    # alpha 를 정확한 유리수로 — float 리터럴은 이진 유리수라 Fraction 변환이 무손실.
    af = Fraction(alpha)
    if af <= 0 or af >= 1:
        return None
    # 조건 `cum / 2^n <= alpha/2` 를 정수 교차곱으로: cum * 2 * den <= num * 2^n.
    lhs_mult = 2 * af.denominator
    rhs = af.numerator * (1 << n)
    best: int | None = None
    cum = 0  # Σ_{i<k} C(n,i)
    k_max = (n + 1) // 2
    for k in range(1, k_max + 1):
        cum += comb(n, k - 1)
        if cum * lhs_mult <= rhs:
            best = k
        else:
            break  # 꼬리 합은 k 에 대해 단조 증가 — 한 번 깨지면 이후 전부 깨진다.
    return best


@lru_cache(maxsize=None)
def min_sample_size(alpha: float = CI_ALPHA) -> int:
    """구간이 존재하기 시작하는 최소 표본수 — 닫힌 식이 아니라 **탐색**으로 얻는다.

    `median_ci_order_index` 를 n=1 부터 올려 처음 not-None 이 되는 n. 테스트가
    이 값을 `ceil(log2(2/alpha))` 와 대조해 유도를 되읽는다(구현이 닫힌 식을 그대로
    돌려주면 그 대조가 공허해지므로 일부러 탐색으로 둔다).

    이 값이 **구조적으로** 무엇을 차단하는지: window 경로(features.
    window_median_angle_deltas)의 표본은 최대 `2*window+1` 개다. 기본 window 에서
    그 수가 이 최소표본에 미달하므로, 방법 자신이 "이 median 은 못 묶는다"고 선언한다
    → window 경로는 종전대로 감점한다(fail-closed). 임의 배제가 아니다.
    """
    n = 1
    while median_ci_order_index(n, alpha) is None:
        n += 1
        if n > 4096:  # 도달 불가(alpha>0 이면 유한 n 에서 성립) — 무한루프 방어.
            raise ValueError("min_sample_size: alpha 가 유효 범위를 벗어났다")
    return n


def median_ci(sample, alpha: float = CI_ALPHA) -> tuple[float, float] | None:
    """표본 1개의 median 신뢰구간 `(L, U)`. 못 구하면 `None`(fail-closed).

    유한값만 추려 정렬한 뒤 순서통계로 잘라낸다. 유한 표본수가 `min_sample_size`
    미만이거나 유한값이 0이면 `None` — "못 구했다"를 "감점 0"으로 번역하지 않기 위해
    호출부가 이 `None` 을 종전 감점으로 처리해야 한다.

    예외를 던지지 않는다. 형상 불량/비수치 입력도 `None` 으로 흡수한다.
    """
    try:
        arr = np.asarray(sample, dtype=float).ravel()
    except (TypeError, ValueError):
        return None
    if arr.size == 0:
        return None
    finite = arr[np.isfinite(arr)]
    n = int(finite.size)
    k = median_ci_order_index(n, alpha)
    if k is None:
        return None
    s = np.sort(finite)
    return float(s[k - 1]), float(s[n - k])


def per_joint_median_ci(path, A_user_seg, A_ref, alpha: float = CI_ALPHA) -> dict:
    """정렬 경로에서 관절별 median `|Δ각도|` 의 신뢰구간 `{관절 인덱스: (L, U)}`.

    `motiondtw.per_joint_deviation` 이 median 을 만든 **바로 그 표본**(경로 스텝별
    `|Δ|` 열)에서 구간을 낸다. 그 함수 본체는 한 글자도 건드리지 않는다 — 소스의
    SHA-256 이 `backend/tests/phase33/test_m3_alignment_only.py` 에 박제돼 있어
    반환값 확장이나 out-param 추가가 전부 그 게이트를 깬다.
    `per_joint_representative_frames` 가 만든 선례대로 같은 diffs 순회를 sibling 으로
    복제한다(중복이지만 박제를 우회하지 않고 통과하는 유일한 길).

    Args:
        path: [(user_local, ref_idx), ...] — per_joint_deviation 과 동일 입력.
        A_user_seg: (T,J) 학생 구간 각도.
        A_ref: (T,J) 기준 각도.
        alpha: 양측 유의수준(기본 CI_ALPHA).

    Returns:
        구간을 구한 관절만 담긴 dict. path 가 비면 `{}`. 어떤 관절이든 구간이
        없으면(유한 표본 미달) **키 부재** — 그 관절은 호출부에서 종전대로 감점된다.
        예외를 던지지 않는다.
    """
    if not path:
        return {}
    try:
        A_user_seg = np.asarray(A_user_seg, dtype=float)
        A_ref = np.asarray(A_ref, dtype=float)
        J = A_ref.shape[1]
        diffs = np.empty((len(path), J), dtype=float)
        for k, (u, r) in enumerate(path):
            diffs[k] = np.abs(A_user_seg[u] - A_ref[r])
    except (TypeError, ValueError, IndexError, AttributeError):
        return {}  # 형상 mismatch 는 항목 부재로만 반영(fail-closed)
    out: dict[int, tuple[float, float]] = {}
    for j in range(J):
        ci = median_ci(diffs[:, j], alpha)
        if ci is not None:
            out[j] = ci
    return out
