"""측정 불확실도 모듈 게이트 (quick-260802-nse Task 1).

문턱이 임의 상수가 아니라 **유도된 것**임을 되읽는 테스트다. 세 축을 잠근다:

1. **신뢰수준의 정의적 성질(커버리지)** — 참 median 을 아는 합성 표본을 반복 생성해
   구간이 참값을 덮는 비율이 `1-CI_ALPHA` 이상. 정규·두꺼운꼬리(라플라스/혼합) 두
   분포에서 성립해야 한다(분포무관임을 실증 — 그것이 이 방법을 고른 이유다).
2. **최소표본이 유도된다** — 경계값을 리터럴로 쓰지 않고 `CI_ALPHA` 에서 닫힌 식으로
   계산해 구현(탐색)과 대조한다.
3. **window 경로가 구조적으로 미달** — `features.window_median_angle_deltas` 의 기본
   window 를 `inspect` 로 읽어 최대 표본수를 계산하고 그것이 최소표본 미만임을 단언.
   숫자 5·6 을 손으로 쓰지 않는다.

난수는 **이 파일 안에서만** 고정 시드로 쓴다 — 프로덕션 모듈은 난수 0이다.
AWS/GPU/Pod 불필요(순수 numpy in-memory).
"""

from __future__ import annotations

import inspect
import math

import numpy as np
import pytest

from sunity_shared.analysis import features, measurement_error, motiondtw
from sunity_shared.analysis.measurement_error import (
    CI_ALPHA,
    median_ci,
    median_ci_order_index,
    min_sample_size,
    per_joint_median_ci,
)


# ── 1. 신뢰수준의 정의적 성질 — 커버리지 ──────────────────────────────────────


def _coverage(draw, n, trials, seed):
    """참 median 0 인 표본을 `trials` 번 뽑아 구간이 0 을 덮은 비율."""
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(trials):
        ci = median_ci(draw(rng, n))
        assert ci is not None, "n 이 최소표본 이상인데 구간이 없다"
        lo, hi = ci
        if lo <= 0.0 <= hi:
            hits += 1
    return hits / trials


def _normal(rng, n):
    return rng.normal(0.0, 1.0, n)


def _laplace(rng, n):
    """두꺼운 꼬리 — 이 방법을 고른 이유(outlier 지배)를 그대로 재현한다."""
    return rng.laplace(0.0, 1.0, n)


def _outlier_mix(rng, n):
    """median 0 인 본체 + 큰 outlier 30% — `per_joint_deviation` 이 median 을 고른
    바로 그 상황(포즈 jitter 로 상위 백분위가 튀는 열)."""
    base = rng.normal(0.0, 1.0, n)
    mask = rng.random(n) < 0.3
    # 부호 대칭으로 오염 — 참 median 은 0 그대로.
    base[mask] += rng.choice([-1.0, 1.0], int(mask.sum())) * rng.normal(40.0, 10.0, int(mask.sum()))
    return base


@pytest.mark.parametrize(
    "draw,seed",
    [(_normal, 11), (_laplace, 12), (_outlier_mix, 13)],
    ids=["normal", "laplace", "outlier_mix"],
)
@pytest.mark.parametrize("n", [8, 31, 120])
def test_coverage_meets_confidence_level_distribution_free(draw, seed, n):
    """구간이 참 median 을 덮는 비율 >= 1-CI_ALPHA — 분포 종류와 무관하게.

    이것이 CI_ALPHA 를 임의 상수가 아니게 만드는 성질이다. 순서통계 구간은 보수적
    (이산 이항이라 실제 피복은 명목 수준 이상)이므로 하한만 단언한다.
    """
    trials = 600
    cov = _coverage(draw, n, trials, seed + n)
    # 유한 반복의 몬테카를로 오차 허용 — 이항 표준오차 3배.
    se = math.sqrt((1 - CI_ALPHA) * CI_ALPHA / trials)
    assert cov >= (1.0 - CI_ALPHA) - 3 * se, (
        f"n={n} 커버리지 {cov:.4f} < 명목 {1 - CI_ALPHA}"
    )


def test_coverage_is_conservative_not_wildly_over():
    """보수성이 "항상 전부 덮는다"로 붕괴하지 않는다 — 구간이 무한대가 아님을 확인.

    n 이 커지면 이산성 여유가 줄어 피복이 명목에 수렴한다. 아주 넓은 구간(=억제가
    항상 걸림)이면 이 단언이 깨진다.
    """
    cov = _coverage(_normal, 400, 600, 99)
    assert cov < 0.999, f"n=400 에서도 피복 {cov:.4f} — 구간이 과대하게 넓다"


# ── 2. 최소표본이 유도된다 ────────────────────────────────────────────────────


def test_min_sample_size_matches_closed_form_derivation():
    """구현(탐색) == 닫힌 식 `ceil(log2(2/alpha))`.

    k=1 조차 성립하려면 `2^-n <= alpha/2`. 리터럴 6 을 쓰지 않고 CI_ALPHA 에서 낸다.
    """
    derived = math.ceil(math.log2(2.0 / CI_ALPHA))
    assert min_sample_size(CI_ALPHA) == derived


def test_order_index_none_below_minimum_and_present_at_or_above():
    """최소표본 미만 전부 None, 그 이상 전부 not-None (경계가 유도로 갈린다)."""
    m = min_sample_size(CI_ALPHA)
    for n in range(0, m):
        assert median_ci_order_index(n, CI_ALPHA) is None, f"n={n} 이 구간을 냈다"
    for n in range(m, m + 40):
        k = median_ci_order_index(n, CI_ALPHA)
        assert k is not None and k >= 1, f"n={n} 이 구간을 못 냈다"


@pytest.mark.parametrize("n", [6, 7, 12, 41, 100, 331])
def test_order_index_binomial_tail_is_exact_and_maximal(n):
    """반환 k 는 꼬리 조건을 만족하는 **최대** k — k 는 되고 k+1 은 안 된다."""
    k = median_ci_order_index(n, CI_ALPHA)
    assert k is not None

    def tail(kk):
        return sum(math.comb(n, i) for i in range(kk)) / 2.0**n

    assert tail(k) <= CI_ALPHA / 2 + 1e-15
    if k + 1 <= (n + 1) // 2:
        assert tail(k + 1) > CI_ALPHA / 2


@pytest.mark.parametrize("n", [6, 9, 50, 101])
def test_interval_brackets_numpy_median_both_parities(n):
    """구간이 `np.median` 을 실제로 묶는다 — 홀수/짝수 모두."""
    rng = np.random.default_rng(7 + n)
    x = rng.normal(3.0, 2.0, n)
    lo, hi = median_ci(x)
    assert lo <= float(np.median(x)) <= hi


# ── 3. window 경로는 구조적으로 미달 ─────────────────────────────────────────


def test_window_path_sample_is_structurally_below_minimum():
    """`window_median_angle_deltas` 기본 window 의 최대 표본수 < 최소표본.

    5·6 을 손으로 쓰지 않는다 — window 기본값은 inspect 로, 최소표본은 모듈에서 읽는다.
    이 단언이 깨진다면 window 경로에 구간을 적용할 수 **있게** 된 것이고, 그때는
    fail-closed 처분을 다시 판단해야 한다(설계 문서 갱신 대상).
    """
    w = inspect.signature(
        features.window_median_angle_deltas
    ).parameters["window"].default
    max_samples = 2 * int(w) + 1
    assert max_samples < min_sample_size(CI_ALPHA), (
        f"window={w} 최대표본 {max_samples} 가 최소표본 "
        f"{min_sample_size(CI_ALPHA)} 이상 — window fail-closed 근거가 사라졌다"
    )
    assert median_ci_order_index(max_samples, CI_ALPHA) is None


# ── 4. per_joint 값과의 정합 ─────────────────────────────────────────────────


def _synthetic_alignment(T=60, J=8, seed=3):
    rng = np.random.default_rng(seed)
    ref = rng.normal(150.0, 15.0, (T, J))
    user = ref + rng.normal(0.0, 8.0, (T, J))
    path = [(t, t) for t in range(T)]
    return path, user, ref


def test_interval_brackets_per_joint_deviation_for_every_joint():
    """모든 관절에서 `L <= per_joint_deviation <= U` — 구간이 자기가 묶는 값을 묶는다."""
    path, user, ref = _synthetic_alignment()
    dev = motiondtw.per_joint_deviation(path, user, ref)
    cis = per_joint_median_ci(path, user, ref)
    assert len(cis) == ref.shape[1], "모든 관절에서 구간이 나와야 한다(전부 유한 표본)"
    for j, (lo, hi) in cis.items():
        assert lo <= float(dev[j]) <= hi, f"joint {j}: {lo} <= {dev[j]} <= {hi} 실패"


def test_per_joint_intervals_are_deterministic():
    """같은 입력 → 같은 구간(난수 0). 결정성은 점수 결정성의 전제다."""
    path, user, ref = _synthetic_alignment(seed=5)
    assert per_joint_median_ci(path, user, ref) == per_joint_median_ci(path, user, ref)


# ── 5. fail-closed ──────────────────────────────────────────────────────────


def test_empty_path_returns_empty_mapping():
    _, user, ref = _synthetic_alignment()
    assert per_joint_median_ci([], user, ref) == {}
    assert per_joint_median_ci(None, user, ref) == {}


def test_all_nan_column_yields_no_key():
    """전부 NaN 인 관절은 키 부재 — 그 관절은 종전대로 감점된다."""
    path, user, ref = _synthetic_alignment()
    user = user.copy()
    user[:, 2] = np.nan
    cis = per_joint_median_ci(path, user, ref)
    assert 2 not in cis
    assert 0 in cis and 1 in cis


def test_partial_nan_column_uses_only_finite_samples():
    """유한값만 쓴다 — 유한 표본이 최소 이상이면 구간이 나오고, 미만이면 안 나온다."""
    path, user, ref = _synthetic_alignment(T=60)
    user = user.copy()
    m = min_sample_size(CI_ALPHA)
    user[m:, 3] = np.nan          # 유한 m 개 → 구간 있음
    user[m - 1:, 4] = np.nan      # 유한 m-1 개 → 구간 없음
    cis = per_joint_median_ci(path, user, ref)
    assert 3 in cis
    assert 4 not in cis


def test_short_sample_and_degenerate_inputs_return_none_without_raising():
    m = min_sample_size(CI_ALPHA)
    assert median_ci(list(range(m - 1))) is None
    assert median_ci(list(range(m))) is not None
    assert median_ci([]) is None
    assert median_ci([float("nan")] * 50) is None
    assert median_ci([float("inf"), float("-inf")] * 50) is None


def test_shape_mismatch_returns_empty_mapping_without_raising():
    """형상 mismatch 는 예외가 아니라 항목 부재(fail-closed)."""
    path, user, ref = _synthetic_alignment(T=20, J=8)
    assert per_joint_median_ci([(0, 999)], user, ref) == {}
    assert per_joint_median_ci(path, user, ref[:, :3]) == {}


def test_invalid_alpha_yields_no_interval():
    for bad in (0.0, 1.0, -0.1, 1.5):
        assert median_ci_order_index(50, bad) is None


# ── 6. 프로덕션 모듈에 난수·해석적 근사가 없다 ───────────────────────────────


def _executable_source(mod) -> str:
    """모듈 소스에서 주석·문자열(독스트링 포함)을 제거한 **실행되는 코드**만.

    설명 문장에 등장하는 단어("1.253 을 쓰지 않는 이유")가 금지 검사에 걸리면 안 되고,
    반대로 주석 처리만으로 검사를 우회할 수도 없어야 한다. 그래서 라인 필터가 아니라
    tokenize 로 COMMENT/STRING 토큰을 걷어낸다.
    """
    import io
    import tokenize

    src = inspect.getsource(mod)
    out: list[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        out.append(tok.string)
    return " ".join(out)


def test_module_executable_code_has_no_randomness_or_normal_approximation():
    """실행 코드에 `1.253`(해석적 근사 상수)·부트스트랩·난수가 0건.

    설명은 있어도 되고 **동작에는 없어야 한다** — 그것이 "난수 0, 결정적" 주장의 내용이다.
    """
    body = _executable_source(measurement_error)
    for banned in ("1.253", "random", "bootstrap", "seed", "shuffle", "choice"):
        assert banned not in body, f"프로덕션 실행 코드에 {banned!r} 가 있다"


def test_module_does_not_import_beyond_numpy_and_stdlib_math():
    """numpy 외 무거운 의존 0 — boto3/firestore/네트워크 import 금지(엔진과 같은 규율)."""
    import ast

    tree = ast.parse(inspect.getsource(measurement_error))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    assert mods <= {"numpy", "fractions", "functools", "math", "__future__"}, mods
