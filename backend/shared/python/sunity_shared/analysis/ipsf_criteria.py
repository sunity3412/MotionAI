"""IPSF criterion 묶음 표 + fault-context 라우터 (Phase 24, ND-01~07).

투명 감점-합산 엔진(deduction_engine.tally)이 소비하는 **순수 config + 라우팅** 레이어.
numpy 외 의존이 0 — boto3/Gemini/네트워크/firestore import 절대 금지(순수, 결정적).

박제 (24-CONTEXT ND-03/ND-04/ND-06):
  · criterion = 상관 관절을 1회 측정으로 묶는 IPSF 단위(양다리 = 1 criterion → −60 폭주 차단).
  · 단일 LINEAR slope(kismam._PENALTY_PER_DEG) 전 criterion 공유 — 영상마다 자의적 X(curve-fit
    금지, [[scoring-redesign-must-generalize-no-overfit]]). gaussian 아님(MEDIUM-2).
  · 측정 substrate 가 실제로 먹일 수 있는 criterion 만 정의(ND-06 honesty) — 미측정 결함은
    COVERAGE_GAP_KEYPOINT_SETS 로 추적(silent 밴드 금지).

provenance 태그:
  [CITED]  tolerance 20° / split 160° 0-fail = IPSF Code of Points (19-IPSF §A 트랙1).
  [ASSUMED] slope / ipsf_cap = v1 엔지니어링 가정(IPSF fact 아님). 보유 sweep 재calibrate 금지.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import kismam
from .skeleton import JOINT_KEYS  # 24-07: per-joint reference_relative criterion 생성용
from .vision_veto import (  # 8 keypoint_set + baseline vocab + reach keypoints 단일 소스
    BASELINE_KINDS,  # noqa: F401 — 문서/계약 정합(직접 사용 X, 재방출 의도)
    FAULT_CATEGORIES,
    FAULT_KEYPOINT_SETS,
    _NOTCH_REACH_KEYPOINTS,
)

# ── provenance 상수 (dimensions.py:164-176 인용 스타일) ──────────────────────
_ANGLE_TOLERANCE_DEG = 20.0   # [CITED: 19-IPSF §A 트랙1] 완전신전(180°) 대비 IPSF 허용오차.
_SPLIT_FAIL_THRESHOLD_DEG = 160.0  # [CITED] micro-bent 요소 무효(0-fail) 임계.
# 현재 split_angle 은 reference_relative(정은지 대비) 채점 — 위 absolute 임계는
# per-move expects_split flag 도입 시(객관 180° 요구 동작) 재활성 예정의 deferred 상수.
_NOTCH_TOLERANCE = 0.5        # [ASSUMED] reach shortfall dead-zone(칸). 측정가능 유일 선택.
# 단일 LINEAR per-unit slope — kismam._PENALTY_PER_DEG=1.2 VERBATIM 재사용(MEDIUM-2).
# IPSF 는 fixed-flat — per-unit slope 가 monotonicity 를 주는 유일한 엔지니어링 선택.
# criterion 별 re-fit 금지(curve-fit 밴). raw = over * slope (LINEAR, gaussian 아님).
_SLOPE = kismam._PENALTY_PER_DEG  # [ASSUMED]
# [ASSUMED] per-criterion 상한 — fault 종류별 ceiling(ND-04b). 최종 점수 밴드 아님:
# 단일 criterion 의 LINEAR 누적이 병적 입력(500°)에서 무한 폭주하는 것만 막는다. 현실
# 범위(0~90° 편차)에서는 saturate 하지 않아 단조성이 유지되도록 충분히 크게(90)
# 잡았다 — 90° 편차(slope 1.2)=raw 84 < cap. 여러 criterion 이 동시 감점하면 합이
# 100 을 넘어 final 이 0 에 도달할 수 있다(상한 밴드 없음). IPSF fact 아님(보유 sweep
# 재calibrate 금지).
_ANGLE_CAP = 90.0
_REACH_CAP = 90.0


# ── criterion 묶음 표 (5 criteria — substrate-honest, ND-06) ────────────────
# 각 criterion: id / joint_keys|keypoint_set / tolerance / slope / ipsf_cap / rule_id /
#   ipsf_anchor / deviation_source ∈ {ipsf_absolute, reference_relative} /
#   direction ∈ {over_target, insufficient_reach}.
# NOTE provenance:
#   · line / leg_extension substrate(dimensions.line_score/extension_deviation)는
#     profile-gated on profile.expects_extension — 빈 joint_expectations(미등재 동작)면
#     None/no-joint → 0 편차 → 0 감점(ND-06 honest 0, 밴드도 거짓감점도 아님). 미등재
#     결함은 dimension_overall fallback + Gemini-located criteria 로 방어.
#   · line 은 keypoint_set=='line'/line-dominant fault 에서만 활성화되고, 활성화된
#     leg/arm extension criterion 이 already claimed 한 substrate 는 cross-criterion
#     exclude 한다(HIGH-5 — 단일 굽은 무릎 double-count 금지). 제외 seam = 엔진 union 이후.
#   · body_relative_reach 는 baseline-relative(delta_notches 소비), insufficient-reach
#     only(HIGH-2) — per-move baseline_kind 가 notch 편차를 바꿔 점수를 바꾼다(ND-05).
_CORE_CRITERION_GROUPS: tuple[dict, ...] = (
    {
        "id": "leg_extension",
        "joint_keys": ("left_knee", "right_knee"),  # ankle→hip line(양 무릎 1묶음)
        "keypoint_set": "leg",
        "tolerance": _ANGLE_TOLERANCE_DEG,   # [CITED]
        "slope": _SLOPE,                     # [ASSUMED] LINEAR
        "ipsf_cap": _ANGLE_CAP,              # [ASSUMED]
        "rule_id": "leg_extension_over_tol_linear",
        "ipsf_anchor": "19-IPSF §A 트랙2 (다리 신전 부족 누적 감점)",
        "deviation_source": "ipsf_absolute",
        "direction": "over_target",
    },
    {
        "id": "arm_extension",
        "joint_keys": ("left_elbow", "right_elbow"),  # wrist→shoulder
        "keypoint_set": "arm",
        "tolerance": _ANGLE_TOLERANCE_DEG,   # [CITED]
        "slope": _SLOPE,                     # [ASSUMED] LINEAR
        "ipsf_cap": _ANGLE_CAP,              # [ASSUMED]
        "rule_id": "arm_extension_over_tol_linear",
        "ipsf_anchor": "19-IPSF §A 트랙2 (팔 신전 부족 누적 감점)",
        "deviation_source": "ipsf_absolute",
        "direction": "over_target",
    },
    {
        # split — 객관 측정(features.split_angle_series, inter-thigh 사이각) 부족분을 소비.
        # deviation_source = reference_relative (정은지 max-split 대비 학생 부족분, mode1).
        # 설계 결정(15-SPLIT-MEASUREMENT-DESIGN §3): 객관 180°(ipsf_absolute) 강요 금지 —
        # full split 을 요구하지 않는 동작의 correct form 을 위양성으로 깎는 over-EXTEND
        # 실수 재발 위험. 정은지 자기 pair 는 correct≈reference→clean, fault<reference→감점.
        # = angle_vs_reference 미러(baseline 0, over=max(0, deficit−tol)). 객관 180°
        # (_SPLIT_FAIL_THRESHOLD_DEG 160° 0-fail)는 per-move expects_split flag 도입 시 후속.
        "id": "split_angle",
        "joint_keys": ("left_hip", "right_hip"),  # inner-thigh hip→knee, 양다리 1묶음
        "keypoint_set": "leg",
        "tolerance": _ANGLE_TOLERANCE_DEG,   # [CITED] kismam 재사용 — 새 임계 금지
        "slope": _SLOPE,                     # [ASSUMED] LINEAR
        "ipsf_cap": _ANGLE_CAP,              # [ASSUMED]
        "rule_id": "split_vs_reference_over_tol_linear",
        "ipsf_anchor": "expert_reference_deviation (정은지 대비 split 부족분)",
        "deviation_source": "reference_relative",
        "direction": "over_target",
    },
    {
        # clean_lines — COLLECTIVE 180°-신전-부족 criterion(dimensions.line_score 가 ALL
        # EXTEND joint 을 1 deficit 로 집계). IPSF "Clean Lines"=단일 collective criterion
        # (24-RESEARCH IPSF Finding 1). HIGH-5: line EXCLUDES leg/arm-claimed substrate.
        "id": "line",
        "joint_keys": (),  # collective — 특정 관절 묶음 아님(엔진이 line substrate 1값 소비)
        "keypoint_set": "line",
        "tolerance": _ANGLE_TOLERANCE_DEG,   # [CITED]
        "slope": _SLOPE,                     # [ASSUMED] LINEAR
        "ipsf_cap": _ANGLE_CAP,              # [ASSUMED]
        "rule_id": "line_clean_lines_over_tol_linear",
        "ipsf_anchor": "19-IPSF §A 트랙1 (Clean Lines collective 180° 신전)",
        "deviation_source": "ipsf_absolute",
        "direction": "over_target",
    },
    {
        # HIGH-4/HIGH-2 — 유일한 reference_relative criterion. delta_notches(학생−코치,
        # baseline-relative)를 insufficient-reach shortfall 로 소비. per-move baseline_kind
        # 가 점수 substrate(ND-05). hand/knee reach(_NOTCH_REACH_KEYPOINTS)만 활성화;
        # grip/head/torso 는 coverage gap.
        "id": "body_relative_reach",
        "joint_keys": _NOTCH_REACH_KEYPOINTS,
        "keypoint_set": "leg",  # reach 는 leg/arm 내 reach-keyed(별도 keypoint_set 아님)
        "tolerance": _NOTCH_TOLERANCE,       # [ASSUMED] notch
        "slope": _SLOPE,                     # [ASSUMED] LINEAR (per-notch)
        "ipsf_cap": _REACH_CAP,              # [ASSUMED]
        "rule_id": "body_relative_reach_insufficient_shortfall_linear",
        "ipsf_anchor": "engineering_interpretation (몸-상대 reach 부족, baseline-relative)",
        "deviation_source": "reference_relative",
        "direction": "insufficient_reach",
        "unit": "notch",
    },
)

# ── 24-07 ① fix: reference_relative per-joint 각도 criterion (JOINT_KEYS 순회 생성) ──
# 미등록 동작(인식기가 reference 동작 미등재 → expects_extension 전부 False → ipsf_absolute
# seed 빔 → dimension_overall_fallback)에서, 이미 측정 가능한 정은지(reference) 대비 per-joint
# 각도 편차(motiondtw.per_joint_deviation)를 deduction 엔진 granular seed 로 배선한다.
# 8개 criterion 을 손-작성하지 않고 JOINT_KEYS 순회로 프로그램 생성 — id 가 관절을 운반
# (angle_vs_reference__{joint}) → belle "−X 왼무릎 −Y 오른팔꿈치" 항목별 wish 직격(24-07 §3-1).
# calibration = kismam 재사용(tol _ANGLE_TOLERANCE_DEG=20° [CITED] + _SLOPE [ASSUMED] + cap
# _ANGLE_CAP [ASSUMED]) — 새 임계/슬로프 picking 0([[calibration-source-hard-gate]]).
# keypoint_set=None: router 대상 아님(_MEASURABLE_SEED_IDS seed 전용) → 153행 partition
# assert(mapped {leg,arm,line} ∪ gap == 8) 불변 보장(새 keypoint_set 문자열 도입 금지).
_REFERENCE_RELATIVE_CRITERIA: tuple[dict, ...] = tuple(
    {
        "id": f"angle_vs_reference__{jk}",
        "joint_keys": (jk,),
        "keypoint_set": None,
        "tolerance": _ANGLE_TOLERANCE_DEG,   # [CITED] kismam 재사용 — 새 임계 금지
        "slope": _SLOPE,                     # [ASSUMED] LINEAR (kismam._PENALTY_PER_DEG)
        "ipsf_cap": _ANGLE_CAP,              # [ASSUMED] 기존 상수 재사용(re-fit 금지)
        "rule_id": "angle_vs_reference_over_tol_linear",
        "ipsf_anchor": "expert_reference_deviation (정은지 대비 per-joint 편차)",
        "deviation_source": "reference_relative",
        "direction": "over_target",
    }
    for jk in JOINT_KEYS
)

# 5 core(ipsf_absolute leg/arm/split/line + reach) + 8 reference_relative per-joint.
CRITERION_GROUPS: tuple[dict, ...] = _CORE_CRITERION_GROUPS + _REFERENCE_RELATIVE_CRITERIA

_CRITERION_BY_ID = {c["id"]: c for c in CRITERION_GROUPS}
# 측정-가능 seed criterion: ipsf_absolute 3개(leg/arm/line) + split_angle(reference_relative,
# 정은지 대비 split 부족분) + reference_relative per-joint 8개 (reach 는 router-only 제외).
# reference_relative 는 criteria_from_measured_deviations 가 md[split_angle]/md[angle_vs_reference__{jk}] 로 seed.
_MEASURABLE_SEED_IDS = ("leg_extension", "arm_extension", "split_angle", "line") + tuple(
    c["id"] for c in _REFERENCE_RELATIVE_CRITERIA
)


# ── 추적된 deferred coverage gaps (측정 substrate 부재 — silent 아님, ND-06) ──
# 8 FaultKey keypoint_set 중 substrate 가 오늘 못 재는 5 — measurement-substrate phase 로
# 연기. 임시 감점 0 + coverage gap 로그(자의적 밴드 주입 금지 — belle 철학).
COVERAGE_GAP_KEYPOINT_SETS: dict[str, str] = {
    "head_neck": "no_head_neck_angle_substrate ([[spike-stillframe-recovers-upperbody]])",
    "grip": "no_grip_proximity_measurement ([[spike-stillframe-recovers-upperbody]])",
    "torso": "posture_axis_substrate_deferred",
    "shoulder": "shoulder_alignment_substrate_deferred",
    "hip": "hip_axis_substrate_deferred",
}

# partition 단언(주석 박제): criterion-mapped keypoint_sets {leg, arm, line} ∪ gap sets
# {head_neck, grip, torso, shoulder, hip} == FAULT_KEYPOINT_SETS(8), 교집합 ∅.
# body_relative_reach 는 leg/arm 내 reach-keyed(별도 keypoint_set 아님).
_MAPPED_KEYPOINT_SETS = frozenset({"leg", "arm", "line"})
assert _MAPPED_KEYPOINT_SETS | frozenset(COVERAGE_GAP_KEYPOINT_SETS) == frozenset(
    FAULT_KEYPOINT_SETS
), "keypoint_set partition drift (mapped ∪ gap != 8)"
assert _MAPPED_KEYPOINT_SETS & frozenset(COVERAGE_GAP_KEYPOINT_SETS) == frozenset()


@dataclass(frozen=True)
class CoverageGap:
    """라우터가 미측정 결함에 반환하는 sentinel — bare None 대신 provenance 운반(MEDIUM-3).

    keypoint_set/reason + 원 supported_difference 의 flat scalar(body_part/fault_state/
    rule_id)를 실어 호출자가 추적가능한 coverageGaps entry 를 만든다(silent 밴드 금지).
    """

    keypoint_set: str
    reason: str
    body_part: str = ""
    fault_state: str = ""
    rule_id: str | None = None


# ── fault_category 고정 enum 라우팅 (25-05, SCHEMA v8.1) ──────────────────────
# 어휘 드리프트 3연속 실측(v9 body_part "양다리 (스플릿 각도)" → v10.1 스플릿이
# fault_state 로 이동 → v11 "벌림"+fault_kind=extension_or_alignment 오분류)의 근본
# fix: Gemini 구조화 출력의 fault_category enum 을 라우터가 1순위로 소비한다.
# 단독-결정 값만 즉시 분기 — split_angle(→split_angle)/alignment(→line)/grip(→gap).
# limb_extension/pole_gap 은 부위(leg vs arm) 정보가 enum 에 없어 body_part 키워드
# 체인으로 세분화(기존 결과 동일), other/부재(구 캐시 하위호환)는 정보 0 → 키워드 폴백.
_CATEGORY_DECISIVE = frozenset({"split_angle", "alignment", "grip"})
assert _CATEGORY_DECISIVE <= frozenset(FAULT_CATEGORIES), (
    "fault_category enum drift — vision_veto.FAULT_CATEGORIES 단일 owner 와 불일치"
)

# ── 라우터 키워드 (vision_veto._KEYPOINT_SET_BY_KEYWORD 스타일, substring match) ──
# "벌림" (25-05): v11 실측 kip-up drift 어휘("양다리 벌림 각도가 기준에 비해 현저히
# 좁음")가 어느 마커에도 안 걸려 rule 8 폴백 → leg_extension 으로 새던 것의 폴백 방어.
# enum 부재(구 캐시) 항목 전용 — v8.1 이후 응답은 fault_category 가 1순위로 라우팅한다.
_SPLIT_KEYWORDS = ("스플릿", "split", "스트래들", "straddle", "벌림")
_KNEE_LEG_KEYWORDS = ("무릎", "knee", "다리", "leg", "허벅지", "thigh")
_ELBOW_ARM_KEYWORDS = ("팔꿈치", "elbow", "팔", "arm")
_HAND_KEYWORDS = ("손", "hand", "손목", "wrist")
_LINE_KEYWORDS = ("라인", "line", "정렬", "alignment")
_GRIP_KEYWORDS = ("그립", "grip", "손바닥")
# bend/extension-deficit fault_state (vision_veto.py:260 gap_markers 재사용).
_BEND_MARKERS = ("굽", "bent", "신전", "풀림", "풀려", "벌어", "떨어", "갭", "gap")
# reach/distance/height shortfall fault_state.
_REACH_MARKERS = ("거리", "높이", "reach", "부족", "멀", "짧", "닿", "도달")


def _contains(text: str, keywords: tuple[str, ...]) -> bool:
    t = str(text or "").lower()
    return any(k.lower() in t for k in keywords)


def _criterion_for_keypoint_set(keypoint_set: str) -> str:
    """INTERNAL total-coverage helper — 8 keypoint_set → criterion id OR gap-set 멤버.

    selection API 아님(split vs leg vs reach 를 구분 못 함). no-silent-gap 보장 + partition
    용. mapped {leg→leg_extension, arm→arm_extension, line→line} + gap 5는 자기 자신 반환.
    """
    if keypoint_set == "leg":
        return "leg_extension"
    if keypoint_set == "arm":
        return "arm_extension"
    if keypoint_set == "line":
        return "line"
    if keypoint_set in COVERAGE_GAP_KEYPOINT_SETS:
        return keypoint_set
    # 어휘 밖(방어) — torso gap 으로 수렴(silent None 금지).
    return "torso"


def criteria_from_measured_deviations(measured_deviations) -> frozenset[str]:
    """측정-편차 SEED (HIGH-1 — Gemini-silent 방어).

    measured_deviations 에서 측정 substrate 가 finite AND tolerance 초과인 측정-가능
    criterion(leg_extension/arm_extension/split_angle/line) id 집합을 Gemini 와 무관하게
    반환한다. supported_difference/FaultKey/severity 를 절대 읽지 않는다. body_relative_reach
    는 seed 대상 아님(Gemini-pointed reach fault 가 criteria_for_fault 로 라우팅돼야 함).
    profile-gated line/leg 가 None/부재면 그 criterion 은 seed 안 됨(honest 0, ND-06).
    """
    md = measured_deviations or {}
    out = set()
    for cid in _MEASURABLE_SEED_IDS:
        dev = md.get(cid)
        if dev is None:
            continue
        try:
            d = float(dev)
        except (TypeError, ValueError):
            continue
        if d != d or d in (float("inf"), float("-inf")):  # NaN/Inf guard
            continue
        if d > _CRITERION_BY_ID[cid]["tolerance"]:
            out.add(cid)
    return frozenset(out)


def _has_reach_substrate(measured_deviations) -> bool:
    md = measured_deviations or {}
    notches = md.get("body_relative_notches")
    return bool(notches)


def _finite_positive(value) -> bool:
    """측정 substrate 실재 판정 — finite float > 0 (None/비수치/NaN/Inf 거부, WR-04)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    if f != f or f in (float("inf"), float("-inf")):  # NaN/Inf guard
        return False
    return f > 0.0


def criteria_for_fault(fault_key, supported_difference, measured_deviations):
    """PUBLIC 라우터 (HIGH-1) — Gemini-pointed fault → 활성 criterion ids OR CoverageGap.

    1순위 = fault_category 고정 enum (25-05, SCHEMA v8.1 — vision_veto.FAULT_CATEGORIES).
    enum 부재(구 캐시)/비단독-결정 값은 body_part/fault_state(supported_difference 에서
    읽음, gemini_vision_scorer schema)+ measured substrate 키워드 체인으로 라우팅한다. keypoint_set 단독 매핑은 불가(split/straddle/knee-reach
    가 전부 keypoint_set='leg' 로 정규화됨 — vision_veto.py:238-239). NOTE(live-source trap):
    torso/line 둘 다 keypoint_set='line' 로 정규화되므로 gap/route 결정은 RAW body_part/
    fault_state 를 읽는다(정규화 keypoint_set 아님).

    INVARIANT(ND-02): supported_difference.severity 를 절대 읽지 않는다 — 활성 set 과 points
    는 (body_part, fault_state, substrate) 의 순수 함수(severity-invariant).
    """
    diff = supported_difference or {}
    body_part = str(diff.get("body_part", ""))
    fault_state = str(diff.get("fault_state", ""))
    combined = f"{body_part} {fault_state}"
    # 25-05 (SCHEMA v8.1): 고정 분류 enum — v8.1 이후 응답은 필수 필드, 구 캐시는 부재("").
    category = str(diff.get("fault_category", "")).strip().lower()

    # 0) fault_category enum 1순위 (25-05) — split_angle 이면 어휘와 무관하게 무조건
    #    split 분기. 키워드 파싱은 프롬프트 버전마다 어휘가 새는 두더지잡기(3연속 drift)
    #    — 구조화 enum 이 라우팅의 단일 근거다.
    if category == "split_angle":
        return ("split_angle",)

    # 1) split/straddle 키워드 폴백 — enum 부재(구 캐시 하위호환)/오분류 방어.
    #    combined(body_part+fault_state) 로 판정 (25-04 sweep FAIL #1 fix, 2026-07-04):
    #    Gemini v10.1 출력은 split 어휘를 body_part 가 아니라 fault_state 에 둔다
    #    (실캐시: body_part="양다리"/"오른쪽 다리", fault_state="...벌어짐(스플릿) 각도가
    #    좁게 형성됨" — phase24 production 은 body_part="양다리 (스플릿 각도)" 였음).
    #    body_part 단독 판정이면 split 결함이 rule 3/8 의 leg_extension 으로 새고,
    #    kip-up 은 leg_extension md substrate 가 없어 honest-0 → belle 결정 A(vision
    #    측정편차 주입) 경로가 통째로 유실된다. correct_state/ipsf_note 는 제외 —
    #    무릎-굽음 멤버의 ipsf_note 보일러플레이트가 '스플릿'을 상습 언급(과잉 라우팅 방지).
    #    split 키워드가 비-split enum(alignment 등)보다 먼저인 이유: 반복 재발 축이
    #    "split 감점 유실"이므로 split 어휘 방어를 enum 오분류 위에 둔다(split 만 예외).
    if _contains(combined, _SPLIT_KEYWORDS):
        return ("split_angle",)

    # 0b) 나머지 단독-결정 enum (split 방어 뒤) — alignment→line, grip→coverage gap.
    #     limb_extension/pole_gap/other/부재 는 여기서 분기하지 않고 기존 키워드 체인
    #     으로 계속(leg vs arm 세분화는 body_part 소관, 하위호환).
    if category == "alignment":
        return ("line",)
    if category == "grip":
        return CoverageGap(
            keypoint_set="grip", reason=COVERAGE_GAP_KEYPOINT_SETS["grip"],
            body_part=body_part, fault_state=fault_state,
        )

    # 2) hand OR knee + reach/distance/height shortfall → body_relative_reach.
    #    (substrate 있을 때만 의미있게 감점되지만 라우팅은 fault 의미로 결정.)
    is_reach_part = _contains(body_part, _HAND_KEYWORDS) or _contains(
        body_part, ("무릎", "knee")
    )
    if is_reach_part and _contains(combined, _REACH_MARKERS):
        return ("body_relative_reach",)

    # 3) knee/leg + bend/extension-deficit → leg_extension.
    if _contains(body_part, _KNEE_LEG_KEYWORDS) and _contains(combined, _BEND_MARKERS):
        return ("leg_extension",)

    # 4) elbow/arm + bend/extension-deficit → arm_extension.
    if _contains(body_part, _ELBOW_ARM_KEYWORDS) and _contains(combined, _BEND_MARKERS):
        return ("arm_extension",)

    # 5) line/alignment (line-dominant) → line. HIGH-5 cross-exclusion 은 엔진 union 이후.
    if _contains(body_part, _LINE_KEYWORDS):
        return ("line",)

    # 6) grip → coverage gap (자의적 감점 절대 금지).
    if _contains(body_part, _GRIP_KEYWORDS):
        return CoverageGap(
            keypoint_set="grip", reason=COVERAGE_GAP_KEYPOINT_SETS["grip"],
            body_part=body_part, fault_state=fault_state,
        )

    # 7) keypoint_set 이 gap set(head_neck/torso/shoulder/hip)으로 매핑 → coverage gap.
    ks = getattr(fault_key, "keypoint_set", None) if fault_key is not None else None
    # RAW body_part 로 head_neck/torso/shoulder/hip 재판정(line 정규화 trap 회피).
    if _contains(body_part, ("머리", "고개", "목", "head", "neck")):
        ks = "head_neck"
    elif _contains(body_part, ("어깨", "shoulder", "견갑")):
        ks = "shoulder"
    elif _contains(body_part, ("엉덩이", "골반", "hip", "pelvis", "둔부")):
        ks = "hip"
    elif _contains(body_part, ("몸통", "torso", "trunk", "허리")):
        ks = "torso"
    if ks in COVERAGE_GAP_KEYPOINT_SETS:
        # WR-04 (25-02 review): shoulder/hip 은 25-01 window seed 가 md 에
        # angle_vs_reference__{side}_{ks} 를 방출할 수 있다 — 측정 substrate 가 실재하면
        # "substrate deferred" gap 은 거짓(같은 결함을 측정해 감점했다면서 측정 못 했다고
        # 동시 보고하는 자기모순). gap 대신 측정된 criterion id 를 반환한다(억제).
        # tol 이내면 dead-zone 으로 record 미방출 — 활성화 자체는 무해(honest).
        if ks in ("shoulder", "hip"):
            measured_cids = tuple(
                cid for cid in (
                    f"angle_vs_reference__left_{ks}",
                    f"angle_vs_reference__right_{ks}",
                )
                if _finite_positive((measured_deviations or {}).get(cid))
            )
            if measured_cids:
                return measured_cids
        return CoverageGap(
            keypoint_set=ks, reason=COVERAGE_GAP_KEYPOINT_SETS[ks],
            body_part=body_part, fault_state=fault_state,
        )

    # 8) 미상 — keypoint_set 으로 total-coverage fallback(silent None 금지).
    resolved = _criterion_for_keypoint_set(ks or "torso")
    if resolved in COVERAGE_GAP_KEYPOINT_SETS:
        return CoverageGap(
            keypoint_set=resolved, reason=COVERAGE_GAP_KEYPOINT_SETS[resolved],
            body_part=body_part, fault_state=fault_state,
        )
    return (resolved,)
