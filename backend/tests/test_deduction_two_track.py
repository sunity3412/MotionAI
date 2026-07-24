"""Wave R 채점 재설계 — 2트랙 IPSF 감점 상한 산식 단위 게이트 (33-SPEC.md R1~R4).

`deduction_engine.tally` 의 무제한 per-joint 감점 누적(elbow-twist Σ ≈ −111.4 → 0)을
2트랙 산식으로 교체한다:

    final = max(SCORE_FLOOR, round(100 − min(EXECUTION_DEDUCTION_CAP, Σ|실행|) − Σ|치명|))
          = max(25,         round(100 − min(40, Σ|실행|)                 − Σ|치명|))

- 실행 트랙(track='execution', 라인/각도 편차) = 합산 후 −40 집계캡 → 바닥 60 (INV-2/INV-7).
- 치명 트랙(track='critical', 필수 완전신전 미달 = 요소 미인정) = −40 집계캡 + −20 관절캡
  둘 다 우회, 절대 바닥 25 (INV-3/INV-8, D-36). **현재 DORMANT** — 활성 criterion 0
  (split_fail_threshold_deg 보유 criterion 0개, D-35) → 이 트랙은 SYNTHETIC 단위테스트로만
  검증된다(D-38). 6 fixture 는 전부 execution-only.

모든 단언은 구조/방향 — 보유 sweep 수치 타깃·fixture별 목표점 금지
([[scoring-redesign-must-generalize-no-overfit]], [[judgment-must-not-fixate-on-recent-fixture]]).
INV-7 앵커는 33-SCORING-REDESIGN-HANDOFF.md 의 8관절 감점값을 VERBATIM 사용(편차 산술
재구성 아님 — 기록된 값에 앵커). AWS/GPU/Pod/fixture 데이터 불필요(순수 numpy in-memory).
"""

import ast
import pathlib

import pytest

from sunity_shared.analysis import deduction_engine
from sunity_shared.analysis.deduction_engine import (
    EXECUTION_DEDUCTION_CAP,
    SCORE_FLOOR,
    DeductionRecord,
    _two_track_final,
)
from sunity_shared.analysis.vision_veto import VisionQuantificationResult


# ── synthetic record helpers (순수 in-memory, substrate 무관) ──────────────────


def _rec(points, track="execution", criterion="synthetic"):
    """단위테스트용 최소 DeductionRecord — 산식은 track + points 만 읽는다.

    points 는 SIGNED NEGATIVE (감점). 나머지 필드는 계약 형상 유지용 placeholder.
    """
    return DeductionRecord(
        criterion=criterion,
        measured_value=0.0,
        baseline_value=180.0,
        baseline_kind=None,
        deviation=abs(points),
        rule_id="synthetic_rule",
        points=float(points),
        unit="deg",
        ipsf_anchor="unit_test",
        source="geometry",
        deviation_source="ipsf_absolute",
        track=track,
    )


# 33-SCORING-REDESIGN-HANDOFF.md 8관절 감점값 VERBATIM (편차 산술 재구성 금지 — 앵커).
# 왼어깨 −18.1 / 오른어깨 −19.3 / 왼팔꿈치 −17.2 / 오른팔꿈치 −8.2 /
# 왼엉덩이 −16.3 / 오른엉덩이 −8.1 / 왼무릎 −12.5 / 오른무릎 −11.7 = Σ −111.4.
_ELBOW_TWIST_POINTS = (-18.1, -19.3, -17.2, -8.2, -16.3, -8.1, -12.5, -11.7)


# ── constants ────────────────────────────────────────────────────────────────


def test_new_constants_are_named_and_correct():
    # 산식 상수 2개는 project-level 단일 상수 (fixture별 re-fit 금지, R3/D-34).
    assert EXECUTION_DEDUCTION_CAP == 40.0
    assert SCORE_FLOOR == 25.0


# ── INV-7 elbow-twist 앵커 (execution-only, Σ ≈ −111.4 → 정확히 60) ────────────


def test_two_track_final_elbow_twist_anchor_is_60():
    assert round(sum(_ELBOW_TWIST_POINTS), 1) == -111.4  # 앵커 무결성 (HANDOFF 표)
    records = [_rec(p) for p in _ELBOW_TWIST_POINTS]
    exec_raw, exec_capped, crit, final = _two_track_final(records)
    assert final == 60  # min(40, 111.4) = 40 → 100 − 40 (INV-7)
    assert exec_raw == pytest.approx(-111.4)
    assert exec_capped == -40.0  # 집계캡 적중
    assert crit == 0.0  # 치명 record 없음


# ── INV-2 execution floor (실행 전용은 60 밑으로 안 내려감) ─────────────────────


def test_two_track_final_execution_floor_60():
    over_cap = [_rec(-30.0), _rec(-30.0)]  # Σ −60 > 40 캡
    assert _two_track_final(over_cap)[3] == 60
    at_cap = [_rec(-20.0), _rec(-20.0)]  # Σ 정확히 −40
    assert _two_track_final(at_cap)[3] == 60
    huge = [_rec(-90.0), _rec(-90.0), _rec(-90.0)]  # Σ −270
    assert _two_track_final(huge)[3] == 60  # never below 60 for execution-only


def test_two_track_final_no_cap_under_40_unchanged():
    # Σ|실행| = 15 (캡 미달) → 100 − 15 = 85 (pre-cap 산술과 동일, 캡 미발동).
    records = [_rec(-10.0), _rec(-5.0)]
    exec_raw, exec_capped, crit, final = _two_track_final(records)
    assert final == 85
    assert exec_capped == -15.0  # 캡 미적중 → raw 그대로


# ── INV-3 critical descent (SYNTHETIC/dormant — 60 밑으로 하강) ────────────────


def test_two_track_final_critical_descends_below_60():
    # 치명 record |90| (−20 관절캡 우회) + 실행 0 → 60 밑으로 하강 (INV-3).
    heavy = [_rec(-90.0, track="critical")]
    assert _two_track_final(heavy)[3] < 60
    # 완화된 치명 |50| → 25 와 60 사이.
    mild = [_rec(-50.0, track="critical")]
    final = _two_track_final(mild)[3]
    assert 25 < final < 60
    assert final == 50


def test_critical_bypasses_execution_aggregate_cap():
    # 치명은 −40 집계캡을 우회 — 실행이었다면 캡에 걸려 60이 됐을 |90| 이 치명이면 10→25.
    as_execution = _two_track_final([_rec(-90.0, track="execution")])[3]
    as_critical = _two_track_final([_rec(-90.0, track="critical")])[3]
    assert as_execution == 60  # 실행: −40 캡 → 60
    assert as_critical == 25  # 치명: 캡 우회 → 100−90=10 → 바닥 25


# ── INV-8 absolute floor 25 ────────────────────────────────────────────────────


def test_two_track_final_absolute_floor_25():
    # 치명 |90| + 실행 Σ40 → 100 − 40 − 90 = −30 → 바닥 25 (INV-8).
    records = [_rec(-20.0), _rec(-20.0), _rec(-90.0, track="critical")]
    assert _two_track_final(records)[3] == 25
    # 임의로 25 밑 산술이 나오는 어떤 조합도 25 로 floor.
    below = [_rec(-90.0, track="critical"), _rec(-90.0, track="critical")]
    assert _two_track_final(below)[3] == 25


def test_two_track_final_never_below_floor_or_above_baseline():
    # 무감점 → 100 상한 유지 (INV-1 elite 앵커: 캡이 near-zero 점수를 안 움직임).
    assert _two_track_final([])[3] == 100
    assert _two_track_final([_rec(-0.4)])[3] == 100  # round(99.6) = 100


# ── INV-6 reconstructability (breakdown 만으로 final 재구성) ────────────────────


def test_two_track_final_reconstructable_from_aggregates():
    records = [
        _rec(-12.5), _rec(-16.3), _rec(-8.1),          # execution
        _rec(-50.0, track="critical"),                  # critical (synthetic)
    ]
    exec_raw, exec_capped, crit, final = _two_track_final(records)
    # 재구성: final == max(25, round(100 + exec_capped + crit)).
    reconstructed = max(SCORE_FLOOR, round(100 + exec_capped + crit))
    assert final == int(reconstructed)
    # 방출 aggregate 로도 재구성 가능해야 한다 (INV-6, R4).
    assert exec_capped == -round(min(EXECUTION_DEDUCTION_CAP, abs(exec_raw)), 1)


# ── breakdown to_dict emits additive-optional aggregate fields (D-37) ──────────


def test_breakdown_to_dict_emits_aggregate_fields():
    records = [_rec(p) for p in _ELBOW_TWIST_POINTS]
    exec_raw, exec_capped, crit, final = _two_track_final(records)
    breakdown = deduction_engine.DeductionBreakdown(
        baseline=100, records=tuple(records), final=final,
        coverage_gaps=(), fallback=None,
        execution_raw_total=exec_raw, execution_capped_total=exec_capped,
        critical_total=crit, execution_cap=EXECUTION_DEDUCTION_CAP,
        score_floor=SCORE_FLOOR,
    )
    d = breakdown.to_dict()
    assert d["final"] == 60
    assert d["executionRawTotal"] == pytest.approx(-111.4)
    assert d["executionCappedTotal"] == -40.0
    assert d["criticalTotal"] == 0.0
    assert d["executionCap"] == 40.0
    assert d["scoreFloor"] == 25.0


def test_record_to_dict_emits_track_only_when_critical():
    # 실행 record 는 track 키 생략(execution 기본, 기존 11키 byte-호환) — 치명만 방출.
    assert "track" not in _rec(-10.0, track="execution").to_dict()
    crit = _rec(-90.0, track="critical").to_dict()
    assert crit["track"] == "critical"


# ── tally() 실 seam 이 2트랙 산식을 쓰는지 (execution-only floor 60) ────────────


def _seed_tally(md, dimension_overall=80, quant=None):
    """실 tally seam 을 md substrate 로 구동(치명은 dormant 라 실 seam 은 execution-only)."""
    if quant is None:
        quant = VisionQuantificationResult(quantificationStatus="available")
    return deduction_engine.tally(
        quant, {"supported_differences": []},
        dimension_overall=dimension_overall,
        measured_deviations=dict(md),
        dimension_scores=None,
        baseline_kind="hip_line",
    )


def test_tally_execution_only_floors_at_60():
    # 3개 관절 각각 60° 편차 → 각 −20 관절캡 → exec Σ −60 → 집계캡 −40 → final 60.
    md = {
        "angle_vs_reference__left_hip": 60.0,
        "angle_vs_reference__right_hip": 60.0,
        "angle_vs_reference__left_shoulder": 60.0,
    }
    b = _seed_tally(md)
    assert len([r for r in b.records if r.points < 0]) == 3
    assert b.final == 60
    d = b.to_dict()
    assert d["executionCappedTotal"] == -40.0
    assert d["criticalTotal"] == 0.0
    assert d["final"] == 60


def test_tally_execution_under_cap_unchanged_86():
    # 단일 관절 32° 편차 → over 12 × slope 1.2 = 14.4 (캡 미달) → 100 − 14.4 → 86.
    b = _seed_tally({"angle_vs_reference__left_hip": 32.0})
    assert b.final == 86


def test_tally_fallback_path_honors_floor_25():
    # quant 불가 + seed 전무 + dimension_overall < 25 → fallback record, final = 바닥 25 (INV-8).
    quant = VisionQuantificationResult(
        quantificationStatus="unavailable", warnings=("inputs_missing",)
    )
    b = _seed_tally({}, dimension_overall=10, quant=quant)
    assert b.fallback == "quantification_unavailable"
    assert b.final == 25  # max(25, round(10))


# ── engine numpy-purity (치명적 constraint — 네트워크/Gemini import 금지, R4) ────


def test_deduction_engine_is_numpy_pure():
    src = pathlib.Path(deduction_engine.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
    forbidden = {"boto3", "requests", "google", "firebase",
                 "firestore", "cerebras", "urllib"}
    assert not (forbidden & mods), f"엔진에 heavy import 유입: {forbidden & mods}"
