"""투명 감점-합산 채점 엔진 (Phase 24, ND-01~07).

점수 = baseline(100) − Σ(criterion별 측정편차 × 명시규칙 감점). 측정-기하 레이어(dimension/
kismam 편차 + Phase 23 정량화 substrate)를 소비해 criterion-grouped → rule → cap → sum 하고
DeductionBreakdown OBJECT 를 방출한다. severity→고정밴드(Phase 20)를 제거·교체 —
final = max(0, round(100 + Σ signed-negative points)), 유일한 clamp 은 max(0,…)(상한 밴드 없음).

numpy 외 의존이 0 — boto3/Gemini/네트워크/firestore import 절대 금지(순수, 결정적).
24-CONTEXT ND-01(엔진 교체)/ND-02(Gemini 강등=측정대상 짚기)/ND-03(substrate=전 차원)/
ND-04(criterion 묶음 no-runaway + cap + sum)/ND-05(baseline=점수 substrate)/ND-06(honest 0 +
coverage gap)/ND-07(추적성·단조성·결정성·일반화 게이트).

24-05: unavailable-fallback 게이트를 criterion 선택 *뒤로* 이동(ND-01). measured seed(정렬-독립
RTMW 각도 편차)는 quantification 이 unavailable 이어도 살아 granular 감점을 내야 하며, 폴백은
quant 불가 AND 활성 criterion 0(양쪽 substrate 빔)일 때만 발화한다. reach 칸 측정 불가는
coverage gap(reach_substrate_unavailable_low_alignment)으로 투명 노출(ND-06).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import ipsf_criteria

_BASELINE = 100.0


@dataclass(frozen=True)
class DeductionRecord:
    """단일 criterion 감점 record (역산 가능 — 모든 −점이 명명 편차 + 명명 규칙).

    points 는 SIGNED NEGATIVE(UX −X). baseline_value = 수치 측정 기준(180/160/ref_notches/
    100), baseline_kind = reach 의 per-move baseline(else None — 항상 방출).
    """

    criterion: str
    measured_value: float
    baseline_value: float
    baseline_kind: str | None
    deviation: float
    rule_id: str
    points: float          # signed-negative
    unit: str              # deg | notch | score_delta
    ipsf_anchor: str
    source: str            # 'geometry'
    deviation_source: str  # ipsf_absolute | reference_relative | dimension_overall

    def to_dict(self) -> dict:
        """flat camelCase dict (models.DEDUCTION_RECORD_KEYS, Firestore-flat scalar only)."""
        return {
            "criterion": self.criterion,
            "measuredValue": self.measured_value,
            "baselineValue": self.baseline_value,
            "baselineKind": self.baseline_kind,
            "deviation": self.deviation,
            "ruleId": self.rule_id,
            "points": self.points,
            "unit": self.unit,
            "ipsfAnchor": self.ipsf_anchor,
            "source": self.source,
            "deviationSource": self.deviation_source,
        }


@dataclass(frozen=True)
class DeductionBreakdown:
    """감점-합산 결과 OBJECT (HIGH-1). final = max(0, round(100 + Σ record.points))."""

    baseline: int
    records: tuple
    final: int
    coverage_gaps: tuple
    fallback: str | None

    def to_dict(self) -> dict:
        """OBJECT {baseline, records, final, coverageGaps, fallback} — records/coverageGaps
        는 flat dict 의 list(Firestore nested-array 금지)."""
        return {
            "baseline": self.baseline,
            "records": [r.to_dict() for r in self.records],
            "final": self.final,
            "coverageGaps": [dict(g) for g in self.coverage_gaps],
            "fallback": self.fallback,
        }

    def to_records(self) -> list:
        """INTERNAL helper — to_dict()['records'] 만."""
        return self.to_dict()["records"]


def _finite(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v):
        return None
    return v


def _notch_shortfall(quantification, criterion):
    """reach criterion 의 insufficient-reach shortfall(HIGH-2) + record meta 산출.

    shortfall = max(0, reference_notches − student_notches − tol) ≡ max(0, −delta − tol).
    _NOTCH_REACH_KEYPOINTS 전체에 대해 per-keypoint shortfall 합. SHORT reach 만 감점,
    over-reach 는 0. 반환 (total_shortfall, measured_value, baseline_value) 또는 None(substrate 부재).
    """
    notches = getattr(quantification, "bodyRelativeNotches", None)
    if not notches:
        return None
    tol = criterion["tolerance"]
    total = 0.0
    measured_sum = 0.0
    baseline_sum = 0.0
    used = False
    from .vision_veto import _NOTCH_REACH_KEYPOINTS
    reach_set = set(_NOTCH_REACH_KEYPOINTS)
    for n in notches:
        if n.get("keypoint") not in reach_set:
            continue
        ref = _finite(n.get("reference_notches"))
        stu = _finite(n.get("student_notches"))
        if ref is None or stu is None:
            continue
        used = True
        shortfall = max(0.0, ref - stu - tol)
        total += shortfall
        measured_sum += stu
        baseline_sum += ref
    if not used:
        return None
    return total, measured_sum, baseline_sum


def tally(
    quantification,
    fault_context,
    *,
    dimension_overall,
    measured_deviations,
    dimension_scores,
    baseline_kind,
    criterion_groups=ipsf_criteria.CRITERION_GROUPS,
):
    """측정-기하 substrate → 투명 감점-합산 DeductionBreakdown.

    Args:
      quantification: VisionQuantificationResult|None — bodyRelativeNotches(reach substrate)
        + quantificationStatus. None/'unavailable' → dimension_overall fallback(+traceable record).
      fault_context: supported_differences 보유 객체/dict — Gemini 가 짚은 결함을 라우팅(ND-02
        — 측정대상 LOCATE + vision-only fault ADD, severity 미사용). criterion selection 은
        criteria_from_measured_deviations | criteria_for_fault — profile 받지 않음(BLOCKER B).
      dimension_overall: 미-veto score_result['overallScore'](measured-geometry overall, substrate).
      measured_deviations: per-criterion 측정 편차(ipsf_absolute id→deg) + 'body_relative_notches'.
        None/부재 criterion 은 0 기여(profile-gated honest 0, ND-06).
      dimension_scores: per-dimension 점수(예약 — 현 경로 미사용).
      baseline_kind: per-move baseline string(floor|pole_vertical|hip_line) — record 라벨 +
        reach notch 편차 구동(ND-05). 엔진은 profile 을 받지 않는다(no NameError surface).
    """
    md = measured_deviations or {}
    crit_by_id = {c["id"]: c for c in criterion_groups}
    coverage_gaps: list[dict] = []

    status = getattr(quantification, "quantificationStatus", None)
    quant_unavailable = quantification is None or status == "unavailable"

    # (2) CRITERION SELECTION — FIRST (ND-01). measured seed(RTMW 각도 편차)는 정렬-독립이므로
    # quantification 이 unavailable 이어도 먼저 평가한다. 폴백을 문 앞에 두면 측정-seed 가
    # 폐기되던 결함을 닫는다(24-05: 폴백 결정을 criterion 선택 뒤로 이동).
    seeded = ipsf_criteria.criteria_from_measured_deviations(md)  # measured seed (Gemini-silent)
    pointed: set[str] = set()
    differences = _supported_differences(fault_context)
    for diff in differences:
        res = ipsf_criteria.criteria_for_fault(_fault_key_for(diff), diff, md)
        if isinstance(res, ipsf_criteria.CoverageGap):
            coverage_gaps.append(_gap_to_dict(res))
            continue
        pointed.update(res)
    activated = set(seeded) | pointed
    gemini_silent = not differences  # Gemini 무지목 관측 마커(measured seed 가 여전히 감점)

    # HIGH-5 cross-criterion exclusion: leg/arm extension 활성화 시 line 의 substrate 중복 제외.
    if activated & {"leg_extension", "arm_extension"} and "line" in activated:
        activated.discard("line")

    # (1') UNAVAILABLE FALLBACK — quant 불가 AND 활성 criterion 0(양쪽 substrate 빔)일 때만
    # (MEDIUM-1 traceable). 100 으로 리셋 금지(BLOCKER A). 측정 각도 seed 가 살아있으면 건너뛴다.
    if quant_unavailable and not activated:
        dim = _finite(dimension_overall)
        dim = 0.0 if dim is None else dim
        fallback_record = DeductionRecord(
            criterion="dimension_overall_fallback",
            measured_value=round(dim, 1),
            baseline_value=100,
            baseline_kind=None,
            deviation=round(100.0 - dim, 1),
            rule_id="quantification_unavailable_dimension_overall",
            points=round(dim - 100.0, 1),  # signed-negative
            unit="score_delta",
            ipsf_anchor="engineering_interpretation",
            source="geometry",
            deviation_source="dimension_overall",
        )
        _collect_coverage_gaps(fault_context, md, crit_by_id, coverage_gaps)
        final = max(0, round(dim))
        return DeductionBreakdown(
            baseline=int(_BASELINE), records=(fallback_record,), final=final,
            coverage_gaps=tuple(coverage_gaps), fallback="quantification_unavailable",
        )

    # quant 불가 BUT 각도 seed 있음 → reach/notch substrate 측정 못 했음을 coverage gap 으로
    # 투명 노출(honest, ND-06/07). reach criterion 은 _notch_shortfall 가 notches 부재로 None
    # 반환 → 자연 honest-0(별도 처리 불필요).
    if quant_unavailable:
        coverage_gaps.append({
            "faultType": "body_relative_reach",
            "reason": "quantification_unavailable",
            "bodyPart": "reach",
            "faultState": None,
            "keypointSet": "body_relative_reach",
            "ruleId": "reach_substrate_unavailable_low_alignment",
        })

    # (3)-(8) per-criterion 감점 누적.
    records: list[DeductionRecord] = []
    for cid in _ordered(activated, criterion_groups):
        crit = crit_by_id.get(cid)
        if crit is None:
            continue
        meta = _criterion_deduction(cid, crit, md, quantification, baseline_kind)
        if meta is None:
            continue  # substrate 부재/None → 0 기여(honest 0, ND-06)
        over, measured_value, baseline_value, unit, dev_kind = meta
        if not np.isfinite(over):  # NaN/Inf guard (Security V5)
            continue
        if over <= 0.0:
            continue  # dead-zone — 감점 0(record 미방출)
        raw = over * crit["slope"]                     # LINEAR (MEDIUM-2 — gaussian 아님)
        capped = min(raw, crit["ipsf_cap"])            # per-criterion cap BEFORE sum (ND-04b)
        rec_baseline_kind = baseline_kind if cid == "body_relative_reach" else None
        records.append(DeductionRecord(
            criterion=cid,
            measured_value=round(measured_value, 2),
            baseline_value=baseline_value,
            baseline_kind=rec_baseline_kind,
            deviation=round(over, 2),
            rule_id=crit["rule_id"],
            points=-round(capped, 1),                  # signed-negative
            unit=unit,
            ipsf_anchor=crit["ipsf_anchor"],
            source="geometry",
            deviation_source=crit["deviation_source"],
        ))

    # (10) final = max(0, round(100 + Σ points)) — 유일한 clamp.
    final = max(0, round(_BASELINE + sum(r.points for r in records)))
    fallback = "gemini_silent" if (gemini_silent and records) else None
    return DeductionBreakdown(
        baseline=int(_BASELINE), records=tuple(records), final=final,
        coverage_gaps=tuple(coverage_gaps), fallback=fallback,
    )


# ── helpers ─────────────────────────────────────────────────────────────────


_IPSF_ABSOLUTE_BASELINE = {
    "leg_extension": 180.0,
    "arm_extension": 180.0,
    "line": 180.0,
    "split_angle": 180.0,
}


def _criterion_deduction(cid, crit, md, quantification, baseline_kind):
    """ACTIVATED criterion 1개의 (over, measured_value, baseline_value, unit, dev_kind).

    ipsf_absolute(angle/line): over = max(0, dev − tol); split 은 160° 0-fail 불연속.
    reference_relative(reach): insufficient-reach shortfall(HIGH-2). substrate 부재 → None.
    """
    if crit["direction"] == "insufficient_reach":
        sf = _notch_shortfall(quantification, crit)
        if sf is None:
            return None
        total_shortfall, measured_sum, baseline_sum = sf
        return total_shortfall, measured_sum, baseline_sum, crit.get("unit", "notch"), "reach"

    # ipsf_absolute — measured_deviations[cid] = student-angle-vs-target deficit(deg).
    dev = md.get(cid)
    if dev is None:
        return None  # profile-gated 부재 → honest 0
    d = _finite(dev)
    if d is None:
        return None
    tol = crit["tolerance"]
    baseline_value = _IPSF_ABSOLUTE_BASELINE.get(cid, 180.0)
    measured_value = baseline_value - d  # student angle ≈ target − deficit
    # split 160° 0-fail 불연속(요소 무효) — dimensions.line_score 선례. measured_value 는
    # 추정 student angle; 그 각이 160° 미만이면 요소 무효(최대 감점 = cap 까지).
    fail_thr = crit.get("split_fail_threshold_deg")
    if fail_thr is not None and measured_value < fail_thr:
        # 0-fail → cap 도달하도록 충분히 큰 over (cap 이 min 으로 제한).
        big_over = crit["ipsf_cap"] / max(crit["slope"], 1e-6)
        return big_over, measured_value, baseline_value, "deg", "ipsf_absolute"
    over = max(0.0, d - tol)
    return over, measured_value, baseline_value, "deg", "ipsf_absolute"


def _supported_differences(fault_context):
    if fault_context is None:
        return []
    if isinstance(fault_context, dict):
        return list(fault_context.get("supported_differences") or [])
    return list(getattr(fault_context, "supported_differences", None) or [])


def _fault_key_for(diff):
    """difference → FaultKey(라우터의 keypoint_set fallback 입력). vision_veto 재사용."""
    try:
        from .vision_veto import fault_key_from_difference
        return fault_key_from_difference(diff)
    except Exception:  # noqa: BLE001 — 라우터는 raw body_part 우선이므로 fallback None 허용
        return None


def _gap_to_dict(gap):
    """CoverageGap → flat coverageGaps entry(MEDIUM-3 provenance)."""
    return {
        "faultType": gap.keypoint_set,
        "reason": gap.reason,
        "bodyPart": gap.body_part,
        "faultState": gap.fault_state,
        "keypointSet": gap.keypoint_set,
        "ruleId": gap.rule_id,
    }


def _collect_coverage_gaps(fault_context, md, crit_by_id, out):
    """fallback 경로에서도 coverage gap 을 수집(추적성)."""
    for diff in _supported_differences(fault_context):
        res = ipsf_criteria.criteria_for_fault(_fault_key_for(diff), diff, md)
        if isinstance(res, ipsf_criteria.CoverageGap):
            out.append(_gap_to_dict(res))


def _ordered(activated, criterion_groups):
    """CRITERION_GROUPS 정의 순서로 활성 criterion 순회(결정적 record 순서)."""
    return [c["id"] for c in criterion_groups if c["id"] in activated]
