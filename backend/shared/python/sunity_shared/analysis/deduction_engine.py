"""투명 감점-합산 채점 엔진 (Phase 24, ND-01~07).

점수 = baseline(100) − Σ(criterion별 측정편차 × 명시규칙 감점). 측정-기하 레이어(dimension/
kismam 편차 + Phase 23 정량화 substrate)를 소비해 criterion-grouped → rule → cap → sum 하고
DeductionBreakdown OBJECT 를 방출한다. severity→고정밴드(Phase 20)를 제거·교체 —
final = max(0, round(100 + Σ signed-negative points)), final 단위 clamp 은 max(0,…) 뿐
(final 밴드/severity 밴드 없음). record 단위로는 관절당 감점 상한
PER_RECORD_DEDUCTION_CAP(-20)이 적용된다(quick-260705-k8h — rawPoints/capApplied 로 투명).

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

# 관절(criterion record)당 감점 상한 (quick-260705-k8h, belle 승인 2026-07-05).
# why: belle 실기기 관측 — kip-up 잘못된 시연이 단일 대형 결함 record 의 폭주 감점으로
# 26점(split -36 + 왼어깨 -24.4 + 오른어깨 -13.2). run6 실데이터 4-누적규칙 비교에서
# 체감가중/RSS 는 작은-결함-다수 동작(elbow/pdshape)을 82~85로 역전시켜 변별 붕괴 — 탈락.
# 관절당 -20 상한 채택: kip-up 47, 작은-결함-다수 동작 무영향. 도메인 근거: IPSF 도
# 결함 유형별 감점 상한 구조. severity 밴드 재도입 아님 — record 단위 명시 규칙
# 클램프이지 final 밴드가 아니다(final 밴드 없음 그대로). 임계값 수치 라벨 = belle OK.
# 투명성: 클램프된 record 는 rawPoints(원 감점)/capApplied 를 방출해 감점-합산 내역 보존
# ([[scoring-must-be-transparent-deduction-tally]]).
# fallback record(dimension_overall_fallback, tally 상단 조기 return 경로)는 클램프
# 비대상 — whole-score 폴백이라 클램프하면 final == dimension_overall 불변식
# (contract.md §10.5)과 100+Σpoints==final 추적성이 동시에 깨진다.
PER_RECORD_DEDUCTION_CAP = 20.0


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
    # per-record 상한(-20) 메타 (quick-260705-k8h). default 필드라 기존 생성부(fallback
    # record 포함)는 무수정 호환. cap_applied=False 면 to_dict() 가 키 자체를 생략 —
    # 상한 미적용 record 는 기존 11키 형상 byte-동일(구 앱/legacy doc 무영향).
    raw_points: float | None = None  # 상한 전 원 감점(signed-negative) — cap_applied 시에만 방출
    cap_applied: bool = False

    def to_dict(self) -> dict:
        """flat camelCase dict (models.DEDUCTION_RECORD_KEYS [+OPTIONAL_KEYS],
        Firestore-flat scalar only)."""
        d = {
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
        if self.cap_applied:
            # 투명 내역 유지: 클램프된 record 만 원 감점 + 마커를 additive 방출.
            d["rawPoints"] = self.raw_points
            d["capApplied"] = True
        return d


@dataclass(frozen=True)
class DeductionBreakdown:
    """감점-합산 결과 OBJECT (HIGH-1). final = max(0, round(100 + Σ record.points)) —
    points 는 per-record 상한(-20, PER_RECORD_DEDUCTION_CAP) 적용 후 값(quick-260705-k8h).
    final 단위 밴드는 여전히 없음(max(0,…) 뿐)."""

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
    vision_measured: dict[str, float] = {}  # cid → vision-측정 편차(geometric 불가 결함)
    split_vision_candidates: list[float] = []  # 25-04 #3(a) — 멤버별 추정치 median 집계
    differences = _supported_differences(fault_context)
    for diff in differences:
        # 25-02 CR-01: fold 대표는 support 집계 산물일 뿐 — 라우팅은 그룹 멤버 전체의
        # RAW body_part/fault_state 로 수행한다. 같은 keypoint_set 의 서로 다른 결함
        # (스플릿 부족 vs 무릎 굽음)이 대표-선정 복권으로 소실되지 않게(라우터의
        # "keypoint_set 단독 매핑 불가" 불변 존중).
        for member in _routing_members(diff):
            res = ipsf_criteria.criteria_for_fault(_fault_key_for(member), member, md)
            if isinstance(res, ipsf_criteria.CoverageGap):
                gap = _gap_to_dict(res)
                if gap not in coverage_gaps:  # 멤버 fan-out 중복 방지(내용 동일 gap 1회)
                    coverage_gaps.append(gap)
                continue
            pointed.update(res)
            # split 은 geometric 측정이 confounded(kip-up keypoint saturate)라 substrate 가
            # 없다(gated). vision 이 split 을 짚으면(router→split_angle) vision 이 영상서 잰
            # reference-상대 편차를 md["split_angle"]로 주입해 split_angle(reference_relative)
            # 규칙이 감점하게 한다(belle 2026-06-29 결정 A: geometric 불가 결함은 vision-측정값
            # 으로 점수화). geometric md 가 이미 있으면(진짜 split-요구 동작) 그것을 우선 —
            # 덮어쓰지 않는다.
            if "split_angle" in res and "split_angle" not in md:
                dev = _vision_measured_deviation(member)
                if dev is None and member is not diff:
                    # 25-02 pod sweep FAIL fix (kip-up fault 100): 멤버가 vision 측정
                    # 편차 payload(approx_angle_deviation_deg)를 안 들고 있으면 부모
                    # (fold 대표) diff 의 것을 승계한다. 대표 = 그룹 내 최고 rank→dev
                    # record 라 그룹의 vision-측정값 보유자. 승계 없으면 md["split_angle"]
                    # 미주입 → criterion 미발화 → 측정-무감점 재발 (belle 결정 A 경로
                    # 유실). 라우팅 seam 전용 수정 — 집계/캐시 형상 무접촉.
                    dev = _vision_measured_deviation(diff)
                if dev is not None:
                    split_vision_candidates.append(dev)
    # 25-04 #3(a) 측정 강건화: split-라우팅 멤버의 vision 측정 추정치가 여럿이면 단일
    # first-wins 가 아니라 median(짝수 = lower-middle, gemini_vision_scorer 의 severity
    # rank-median 짝수 규칙과 동일 컨벤션 — 새 튜닝 상수 0)으로 집계 주입한다. 추정
    # 한 방이 tol 경계(20°)를 넘나드는 변동(run3 kip-up 20° vs production 30°)을 완화.
    # geometric md 존재 시 위 guard 로 candidates 자체가 비어 기존 우선순위 불변.
    if split_vision_candidates and "split_angle" not in md:
        dev = _median_lower(split_vision_candidates)
        md["split_angle"] = dev
        vision_measured["split_angle"] = dev
    activated = set(seeded) | pointed
    gemini_silent = not differences  # Gemini 무지목 관측 마커(measured seed 가 여전히 감점)

    # HIGH-5 cross-criterion exclusion: leg/arm extension 활성화 시 line 의 substrate 중복 제외.
    if activated & {"leg_extension", "arm_extension"} and "line" in activated:
        activated.discard("line")

    # HIGH-5 확장 (24-07 §3-2): 활성 ipsf_absolute extension(leg/arm/split)이 claim 한 관절은
    # reference_relative 동일관절(angle_vs_reference__{jk})을 discard — double-count 금지. 이들은
    # explicit joint_keys 를 보유하므로 엔진이 profile 없이 구성관절을 안다(profile-독립, testable).
    # line(collective, joint_keys=())은 엔진이 profile 부재로 구성관절을 모름 → seed-stage(builder,
    # Task 2)가 expects_extension 으로 reference_relative md 자체를 차단(line/leg/arm/split 모두
    # expects_extension 파생이므로 정확). 엔진-stage 는 leg/arm/split 만 추가 discard 보증.
    claimed_joints: set[str] = set()
    for cid in ("leg_extension", "arm_extension", "split_angle"):
        if cid in activated:
            claimed_joints.update(crit_by_id[cid]["joint_keys"])
    for jk in claimed_joints:
        activated.discard(f"angle_vs_reference__{jk}")

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
        # 관절당 감점 상한 -20 클램프 (quick-260705-k8h — PER_RECORD_DEDUCTION_CAP 주석
        # 참조). 반올림(0.1 단위) 후 비교 — float epsilon 이 rawPoints == points 인 가짜
        # capApplied 잡음 record 를 만들지 않게 한다. 경계(정확히 == 상한)는 상한 이하
        # 취급(필드 생략).
        capped_r = round(capped, 1)
        cap_hit = capped_r > PER_RECORD_DEDUCTION_CAP
        points_val = PER_RECORD_DEDUCTION_CAP if cap_hit else capped_r
        rec_baseline_kind = baseline_kind if cid == "body_relative_reach" else None
        records.append(DeductionRecord(
            criterion=cid,
            measured_value=round(measured_value, 2),
            baseline_value=baseline_value,
            baseline_kind=rec_baseline_kind,
            deviation=round(over, 2),
            rule_id=crit["rule_id"],
            points=-points_val,                        # signed-negative (capped)
            unit=unit,
            ipsf_anchor=crit["ipsf_anchor"],
            # provenance: geometric 측정이 기본. vision-측정값으로 점수화한 결함(split,
            # geometric 불가)은 source='vision' 으로 투명 표기(belle 2026-06-29 A — 보고서가
            # "split N° 좁음(vision 측정) −X" 출처 노출). 점수 산식은 동일 규칙(tol×slope).
            source="vision" if cid in vision_measured else "geometry",
            deviation_source=crit["deviation_source"],
            raw_points=(-capped_r if cap_hit else None),
            cap_applied=cap_hit,
        ))

    # (10) final = max(0, round(100 + Σ points)) — final 단위 clamp 은 max(0,…) 뿐
    # (points 는 이미 per-record 상한 적용값).
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

    # reference_relative (over_target) — 24-07 §3-1. measured_deviations[cid] = 정은지(reference)
    # 대비 per-joint median |Δ각도| 편차(deg, motiondtw.per_joint_deviation). 목표 = reference 대비
    # 0° 편차 → baseline_value=0.0, measured_value=편차. over = max(0, dev − tol). None → honest 0.
    # _IPSF_ABSOLUTE_BASELINE(180) 경로와 섞지 않는다(절대-신전 아님 = reference 상대).
    if crit["deviation_source"] == "reference_relative" and crit["direction"] == "over_target":
        d = _finite(md.get(cid))
        if d is None:
            return None
        tol = crit["tolerance"]
        over = max(0.0, d - tol)
        return over, d, 0.0, "deg", "reference_relative"

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


def _median_lower(values):
    """lower-middle median — 짝수 개수는 아래쪽 중앙값(보수적: 감점을 부풀리지 않는
    방향). gemini_vision_scorer 의 severity rank-median 짝수 규칙과 동일 컨벤션 재사용
    — 새 튜닝 상수 0."""
    s = sorted(values)
    return s[(len(s) - 1) // 2]


def _vision_measured_deviation(diff):
    """vision difference 의 측정 편차(deg) → float | None.

    geometric 측정이 불가한 결함(split: kip-up keypoint saturate, [[split-measurement-
    doesnt-discriminate-kipup]])을 vision-측정값으로 점수화하기 위한 추출(belle 2026-06-29
    결정 A). "Gemini 측정 + 규칙 점수" 원칙 정합([[scoring-must-be-transparent-deduction-tally]]).

    우선순위 (25-04 #3(a) 측정 강건화):
      1. 명시 각도쌍 — student_angle_deg/reference_angle_deg 둘 다 있으면 편차는 코드가
         산술 계산(vision_veto.explicit_measured_deviation_deg). "편차 한 방 추정"의
         앵커링 편향 우회. 산술 편차 0 은 "재봤더니 차이 없음" — approx 폴백으로 모순
         주입하지 않고 None(감점 0, honest).
      2. 폴백 — approx_angle_deviation_deg (각도쌍 미방출 구 캐시/비각도 관측 호환).

    dict/obj 모두 처리, 비수치/음수/비유한 → None(honest skip). 캐시 round-trip 이
    문자열화한 값도 float 캐스팅."""
    from .vision_veto import explicit_measured_deviation_deg

    explicit = explicit_measured_deviation_deg(diff)
    if explicit is not None:
        return explicit if explicit > 0.0 else None
    if isinstance(diff, dict):
        v = diff.get("approx_angle_deviation_deg")
    else:
        v = getattr(diff, "approx_angle_deviation_deg", None)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) and f > 0.0 else None


def _fault_key_for(diff):
    """difference → FaultKey(라우터의 keypoint_set fallback 입력). vision_veto 재사용."""
    try:
        from .vision_veto import fault_key_from_difference
        return fault_key_from_difference(diff)
    except Exception:  # noqa: BLE001 — 라우터는 raw body_part 우선이므로 fallback None 허용
        return None


def _routing_members(diff):
    """fold 대표 → 라우팅 대상 멤버 전체 (25-02 CR-01).

    `_filter_supported_differences` 의 keypoint_set fold 는 support 집계용 — 라우팅은
    그룹 멤버 원문(`_memberFaults`) 각각으로 수행해 split_angle 등 body_part-keyed 경로
    소실을 막는다. 멤버 메타 부재(구 캐시/직접 구성 diff)면 diff 자신 1개로 폴백."""
    if isinstance(diff, dict):
        members = diff.get("_memberFaults")
        if members:
            return list(members)
    return [diff]


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
    """fallback 경로에서도 coverage gap 을 수집(추적성) — 멤버 단위 (CR-01 정합)."""
    for diff in _supported_differences(fault_context):
        for member in _routing_members(diff):
            res = ipsf_criteria.criteria_for_fault(_fault_key_for(member), member, md)
            if isinstance(res, ipsf_criteria.CoverageGap):
                gap = _gap_to_dict(res)
                if gap not in out:
                    out.append(gap)


def _ordered(activated, criterion_groups):
    """CRITERION_GROUPS 정의 순서로 활성 criterion 순회(결정적 record 순서)."""
    return [c["id"] for c in criterion_groups if c["id"] in activated]
