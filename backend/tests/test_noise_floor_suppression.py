"""측정 오차 미만 감점 억제 seam 게이트 (quick-260802-nse Task 2).

이 사이클은 **점수를 바꾼다** — 그래서 바꾸지 않는 것들을 먼저 잠근다:

1. **기본 off byte-동일** — `measurement_error` 미전달 시 산출이 도입 이전과 키·값 모두 같다.
2. **단조 상승** — `final(with) >= final(without)` 이 항상, `records(with) ⊆ records(without)`.
   억제는 record 를 지울 뿐 만들지 않으므로 점수가 내려갈 경로가 **없다**.
3. **activated 불변** — 억제된 criterion 이 claim 하던 관절이 되살아나지 않는다
   (cross-exclusion 의 입력이 바뀌면 점수가 내려갈 수 있는데, 그 자리가 여기다).
4. **밴드 아님** — 살아남은 record 의 `points` 가 byte-불변.
5. **fail-closed** — 구간을 못 구하면 종전대로 감점한다.
6. **억제 내역 재구성** — `Σ wouldBePoints` 로 점수 이동이 산술로 설명된다.

AWS/GPU/Pod/Gemini 불필요(순수 in-memory).
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from sunity_shared import models
from sunity_shared.analysis import (
    deduction_engine,
    ipsf_criteria,
    measurement_error,
    vision_veto,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS

_TOL = ipsf_criteria._ANGLE_TOLERANCE_DEG


def _quant():
    return vision_veto.VisionQuantificationResult(quantificationStatus="available")


def _md(**joints):
    """`{joint_key: deviation_deg}` → angle_vs_reference md."""
    return {f"angle_vs_reference__{jk}": v for jk, v in joints.items()}


def _tally(md, measurement_error=None):
    return deduction_engine.tally(
        _quant(), None,
        dimension_overall=80.0,
        measured_deviations=dict(md),
        dimension_scores=None,
        baseline_kind="hip_line",
        measurement_error=measurement_error,
    )


def _ci(low, high, n=120):
    return (low, high, n)


# ── 1. 기본 off = byte-동일 ──────────────────────────────────────────────────


def test_default_off_is_byte_identical_to_no_argument():
    """`measurement_error` 미전달 == None 전달 == 이 사이클 이전 산출."""
    md = _md(left_shoulder=25.0, right_elbow=32.0, left_knee=21.0)
    a = deduction_engine.tally(
        _quant(), None, dimension_overall=80.0, measured_deviations=dict(md),
        dimension_scores=None, baseline_kind="hip_line",
    ).to_dict()
    b = _tally(md, None).to_dict()
    assert a == b
    assert "suppressedRecords" not in a, "억제 0 인데 키가 실렸다"


def test_empty_measurement_error_dict_suppresses_nothing():
    md = _md(left_shoulder=25.0, right_elbow=32.0)
    base = _tally(md, None).to_dict()
    assert _tally(md, {}).to_dict() == base


def test_signature_has_keyword_only_measurement_error_defaulting_none():
    p = inspect.signature(deduction_engine.tally).parameters["measurement_error"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is None


# ── 2. 억제 규칙 — 하한이 허용치를 넘느냐만 본다 ─────────────────────────────


def test_interval_low_at_or_below_tolerance_suppresses_record():
    """`L <= tolerance` → 방출 안 함. record 는 사라지고 내역만 남는다."""
    md = _md(left_shoulder=20.67)
    me = {"angle_vs_reference__left_shoulder": _ci(16.70, 24.9)}
    with_ = _tally(md, me)
    assert [r.criterion for r in with_.records] == []
    assert len(with_.suppressed_records) == 1
    s = with_.suppressed_records[0]
    assert s.criterion == "angle_vs_reference__left_shoulder"
    assert s.rule_id == deduction_engine.SUPPRESSION_RULE_ID
    assert s.would_be_points < 0


def test_interval_low_above_tolerance_keeps_record_byte_identical():
    """`L > tolerance` → 종전과 **완전히 같은** record(밴드 아님)."""
    md = _md(right_elbow=30.29)
    me = {"angle_vs_reference__right_elbow": _ci(26.99, 34.0)}
    without = _tally(md, None)
    with_ = _tally(md, me)
    assert with_.to_dict()["records"] == without.to_dict()["records"]
    assert with_.final == without.final
    assert "suppressedRecords" not in with_.to_dict()


def test_boundary_interval_low_exactly_at_tolerance_suppresses():
    """경계(L == tolerance)는 억제 — 하한이 허용치를 **넘지 못했다**."""
    md = _md(left_hip=26.0)
    me = {"angle_vs_reference__left_hip": _ci(_TOL, 33.0)}
    assert _tally(md, me).records == ()


def test_engine_never_parses_joint_names_only_criterion_ids():
    """관절 이름이 아니라 criterion id 로만 조회한다(동작명 분기 0).

    관절 이름만 담긴 키는 아무 것도 억제하지 못한다.
    """
    md = _md(left_shoulder=25.0)
    me = {"left_shoulder": _ci(1.0, 2.0)}  # criterion id 가 아니다
    assert len(_tally(md, me).records) == 1


# ── 3. 단조 상승 + 부분집합 (hard invariant 1) ───────────────────────────────


def _random_case(rng):
    joints = list(rng.choice(JOINT_KEYS, size=rng.integers(1, 9), replace=False))
    md = {}
    me = {}
    for jk in joints:
        dev = float(rng.uniform(_TOL + 0.1, _TOL + 25.0))
        md[f"angle_vs_reference__{jk}"] = dev
        if rng.random() < 0.75:
            half = float(rng.uniform(0.5, 12.0))
            me[f"angle_vs_reference__{jk}"] = _ci(dev - half, dev + half)
    return md, me


@pytest.mark.parametrize("seed", range(30))
def test_score_never_decreases_and_records_are_a_subset(seed):
    """합성 입력 다수 — 점수는 오직 올라가거나 그대로, record 는 부분집합."""
    rng = np.random.default_rng(seed)
    md, me = _random_case(rng)
    without = _tally(md, None)
    with_ = _tally(md, me)
    assert with_.final >= without.final, f"seed={seed} 점수가 내려갔다"
    kept = {r.criterion for r in with_.records}
    all_ = {r.criterion for r in without.records}
    assert kept <= all_, f"seed={seed} 새 record 가 생겼다: {kept - all_}"
    # 살아남은 record 는 값까지 그대로(밴드 아님).
    by_cid = {r.criterion: r for r in without.records}
    for r in with_.records:
        assert r.to_dict() == by_cid[r.criterion].to_dict()


def test_suppressing_everything_yields_perfect_score_not_a_lower_one():
    """전부 억제 → records 0 → final 100. 내려가는 경로가 없음을 극단에서 확인."""
    md = _md(left_shoulder=21.0, right_hip=22.0, left_knee=21.5)
    me = {k: _ci(1.0, 30.0) for k in md}
    b = _tally(md, me)
    assert b.records == ()
    assert b.final == 100
    assert len(b.suppressed_records) == 3


# ── 4. activated / cross-exclusion 불변 ─────────────────────────────────────


def test_cross_exclusion_result_is_unchanged_by_suppression():
    """억제된 criterion 이 claim 하던 관절이 **되살아나지 않는다**.

    md 생산이나 activated 구성에서 갈랐다면 leg_extension 이 비활성화될 때
    angle_vs_reference__{무릎} 이 되살아나 record 가 늘고 점수가 내려갈 수 있다.
    방출 직전에서 가르므로 그런 일이 원리적으로 불가능함을 확인한다.
    """
    knee_keys = [jk for jk in JOINT_KEYS if "knee" in jk]
    assert knee_keys, "무릎 관절 키가 있어야 이 게이트가 의미를 가진다"
    md = {"leg_extension": 45.0}
    md.update({f"angle_vs_reference__{jk}": 40.0 for jk in knee_keys})
    me = {"leg_extension": _ci(1.0, 60.0)}  # leg_extension 억제
    without = _tally(md, None)
    with_ = _tally(md, me)
    # leg_extension 이 억제돼도 무릎 angle_vs_reference 는 여전히 방출되지 않는다.
    assert not any("knee" in r.criterion for r in with_.records)
    assert {r.criterion for r in with_.records} <= {
        r.criterion for r in without.records
    }
    assert with_.final >= without.final


# ── 5. fail-closed — 못 구하면 종전대로 감점 ────────────────────────────────


@pytest.mark.parametrize(
    "bad",
    [
        None,
        (float("nan"), 30.0),
        (float("inf"), 30.0),
        (5.0, float("nan")),
        (30.0, 5.0),          # L > U (형상 불량)
        (5.0,),               # 원소 부족
        (),
        "5,30",               # 문자열
        {"low": 5.0},         # dict
        5.0,                  # 스칼라
    ],
    ids=[
        "none", "nan_low", "inf_low", "nan_high", "inverted",
        "too_short", "empty", "string", "dict", "scalar",
    ],
)
def test_malformed_interval_falls_back_to_deducting_as_before(bad):
    md = _md(left_shoulder=25.0)
    me = {"angle_vs_reference__left_shoulder": bad}
    without = _tally(md, None)
    with_ = _tally(md, me)
    assert with_.to_dict() == without.to_dict()


def test_measurement_error_of_wrong_type_is_ignored():
    md = _md(left_shoulder=25.0)
    base = _tally(md, None).to_dict()
    for bad in ([("a", (1.0, 2.0))], "x", 3, object()):
        assert _tally(md, bad).to_dict() == base


def test_missing_key_deducts_as_before():
    """dict 에 없는 criterion 은 종전대로 감점 — 부재를 감점 0으로 번역하지 않는다."""
    md = _md(left_shoulder=25.0, right_elbow=30.0)
    me = {"angle_vs_reference__left_shoulder": _ci(1.0, 40.0)}
    with_ = _tally(md, me)
    assert [r.criterion for r in with_.records] == ["angle_vs_reference__right_elbow"]


def test_two_element_interval_is_accepted_with_sample_size_zero():
    """`(L, U)` 도 유효 — sampleSize 는 관측치일 뿐 판정에 쓰이지 않는다."""
    md = _md(left_shoulder=25.0)
    b = _tally(md, {"angle_vs_reference__left_shoulder": (1.0, 40.0)})
    assert b.records == ()
    assert b.suppressed_records[0].sample_size == 0


# ── 6. 억제 내역 재구성 (hard invariant 2) ──────────────────────────────────


@pytest.mark.parametrize("seed", range(20))
def test_suppressed_points_reconstruct_the_score_movement(seed):
    """`Σ wouldBePoints == executionRawTotal(without) − executionRawTotal(with)`."""
    rng = np.random.default_rng(1000 + seed)
    md, me = _random_case(rng)
    without = _tally(md, None)
    with_ = _tally(md, me)
    moved = round(
        (without.execution_raw_total or 0.0) - (with_.execution_raw_total or 0.0), 1
    )
    total_suppressed = round(
        sum(s.would_be_points for s in with_.suppressed_records), 1
    )
    assert abs(total_suppressed - moved) < 0.05, (
        f"seed={seed} 설명 안 되는 이동: Σwould={total_suppressed} vs 이동={moved}"
    )
    # final 항등식(INV-6)도 그대로 성립한다 — 산식은 안 바뀐다.
    d = with_.to_dict()
    assert d["final"] == int(max(
        d["scoreFloor"],
        round(100 + d["executionCappedTotal"] + d["criticalTotal"]),
    ))


def test_would_be_points_equals_the_points_it_would_have_had():
    """`wouldBePoints` == 억제 안 했을 때 그 record 의 `points` (그 값 그대로)."""
    md = _md(left_shoulder=25.0, right_hip=27.0)
    me = {k: _ci(1.0, 40.0) for k in md}
    without = {r.criterion: r.points for r in _tally(md, None).records}
    for s in _tally(md, me).suppressed_records:
        assert s.would_be_points == without[s.criterion]


def test_would_be_points_reflects_the_per_record_cap():
    """per-record 상한(-20)이 적용된 뒤의 값 — "방출됐다면 들어갔을 그 값"."""
    md = _md(left_shoulder=200.0)  # 상한을 확실히 넘기는 편차
    rec = _tally(md, None).records[0]
    assert rec.cap_applied is True
    s = _tally(md, {k: _ci(1.0, 400.0) for k in md}).suppressed_records[0]
    assert s.would_be_points == rec.points
    assert s.would_be_points == -deduction_engine.PER_RECORD_DEDUCTION_CAP


# ── 7. 방출 형상 — flat scalar + 계약 lockstep ──────────────────────────────


def test_suppressed_record_dict_is_flat_scalar_and_matches_contract_keys():
    md = _md(left_shoulder=25.0)
    d = _tally(md, {k: _ci(1.0, 40.0) for k in md}).to_dict()
    assert "suppressedRecords" in d
    assert isinstance(d["suppressedRecords"], list)
    for item in d["suppressedRecords"]:
        assert set(item) == set(models.SUPPRESSED_RECORD_KEYS)
        for v in item.values():
            assert isinstance(v, (str, int, float, bool)), (
                f"flat scalar 아님: {v!r}"
            )
            assert not isinstance(v, (list, dict, tuple))


def test_contract_lockstep_three_way():
    """models / analysis.ts / contract.md 세 곳에 suppressedRecords 가 있다."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1].parent
    assert "suppressedRecords" in models.DEDUCTION_BREAKDOWN_OPTIONAL_KEYS
    ts = (root / "app" / "src" / "types" / "analysis.ts").read_text(encoding="utf-8")
    m = re.search(
        r"export interface SuppressedDeductionRecord \{(.*?)\n\}", ts, re.S
    )
    assert m, "SuppressedDeductionRecord interface 부재"
    ts_fields = set(re.findall(r"^\s*(\w+)\??:", m.group(1), re.M))
    assert ts_fields == set(models.SUPPRESSED_RECORD_KEYS)
    assert "suppressedRecords?: SuppressedDeductionRecord[]" in ts
    contract = (root / "docs" / "contract.md").read_text(encoding="utf-8")
    assert "suppressedRecords" in contract
    assert "deviation_within_measurement_error" in contract


def test_firestore_validator_covers_suppressed_records():
    """nested array 가 이 키로 새지 않는다 ([[firestore-nested-array-flat]])."""
    from sunity_shared import firestore_admin

    firestore_admin._validate_deduction_breakdown({
        "records": [], "coverageGaps": [],
        "suppressedRecords": [{"criterion": "x", "wouldBePoints": -1.0}],
    })
    with pytest.raises((TypeError, ValueError)):
        firestore_admin._validate_deduction_breakdown({
            "suppressedRecords": [{"criterion": "x", "nested": [[1, 2]]}],
        })
    with pytest.raises(ValueError):
        firestore_admin._validate_deduction_breakdown({
            "suppressedRecords": "not-a-list",
        })


# ── 8. 모듈 통합 — 실제 구간이 실제 억제를 만든다 ──────────────────────────


def test_module_derived_intervals_drive_suppression_end_to_end():
    """`per_joint_median_ci` 가 낸 구간이 그대로 엔진 억제로 이어진다.

    합성 정렬: 편차가 허용치를 **아슬하게** 넘는 관절(구간 하한이 tol 이하)과
    허용치를 **크게** 넘는 관절(구간 하한이 tol 초과)을 한 표본에 같이 만든다.
    """
    from sunity_shared.analysis import motiondtw

    rng = np.random.default_rng(4)
    T, J = 200, len(JOINT_KEYS)
    ref = np.full((T, J), 150.0)
    user = ref.copy()
    noisy_idx = JOINT_KEYS.index("left_hip")
    clear_idx = JOINT_KEYS.index("right_elbow")
    # 허용치 바로 위 + 큰 산포 → 구간 하한이 tol 아래로 내려간다.
    user[:, noisy_idx] += (_TOL + 0.5) + rng.normal(0.0, 15.0, T)
    # 허용치 한참 위 + 작은 산포 → 구간 하한이 tol 위에 머무른다.
    user[:, clear_idx] += (_TOL + 12.0) + rng.normal(0.0, 1.0, T)
    path = [(t, t) for t in range(T)]

    dev = motiondtw.per_joint_deviation(path, user, ref)
    cis = measurement_error.per_joint_median_ci(path, user, ref)
    assert dev[noisy_idx] > _TOL and dev[clear_idx] > _TOL, "둘 다 감점 대상이어야 한다"
    assert cis[noisy_idx][0] <= _TOL < cis[clear_idx][0], "설계한 대비가 안 나왔다"

    md = _md(**{
        JOINT_KEYS[noisy_idx]: float(dev[noisy_idx]),
        JOINT_KEYS[clear_idx]: float(dev[clear_idx]),
    })
    me = {
        f"angle_vs_reference__{JOINT_KEYS[i]}": (cis[i][0], cis[i][1], len(path))
        for i in (noisy_idx, clear_idx)
    }
    without = _tally(md, None)
    with_ = _tally(md, me)
    assert len(without.records) == 2
    assert [r.criterion for r in with_.records] == [
        f"angle_vs_reference__{JOINT_KEYS[clear_idx]}"
    ]
    assert with_.final > without.final
    assert with_.suppressed_records[0].sample_size == len(path)
