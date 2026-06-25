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
from .vision_veto import (  # 8 keypoint_set + baseline vocab + reach keypoints 단일 소스
    BASELINE_KINDS,  # noqa: F401 — 문서/계약 정합(직접 사용 X, 재방출 의도)
    FAULT_KEYPOINT_SETS,
    _NOTCH_REACH_KEYPOINTS,
)

# ── provenance 상수 (dimensions.py:164-176 인용 스타일) ──────────────────────
_ANGLE_TOLERANCE_DEG = 20.0   # [CITED: 19-IPSF §A 트랙1] 완전신전(180°) 대비 IPSF 허용오차.
_SPLIT_FAIL_THRESHOLD_DEG = 160.0  # [CITED] micro-bent 요소 무효(0-fail) 임계.
_NOTCH_TOLERANCE = 0.5        # [ASSUMED] reach shortfall dead-zone(칸). 측정가능 유일 선택.
# 단일 LINEAR per-unit slope — kismam._PENALTY_PER_DEG=1.2 VERBATIM 재사용(MEDIUM-2).
# IPSF 는 fixed-flat — per-unit slope 가 monotonicity 를 주는 유일한 엔지니어링 선택.
# criterion 별 re-fit 금지(curve-fit 밴). raw = over * slope (LINEAR, gaussian 아님).
_SLOPE = kismam._PENALTY_PER_DEG  # [ASSUMED]
# [ASSUMED] per-criterion 상한 — IPSF global −25 cap 의 해석(per-fault IPSF fact 아님).
# 최종 점수 밴드 아님(ND-04b) — fault 종류별 ceiling 으로 단일 criterion 폭주만 제한.
_ANGLE_CAP = 25.0
_REACH_CAP = 25.0


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
CRITERION_GROUPS: tuple[dict, ...] = (
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
        "id": "split_angle",
        "joint_keys": ("left_hip", "right_hip"),  # inner-thigh hip→knee, 양다리 1묶음
        "keypoint_set": "leg",
        "tolerance": _ANGLE_TOLERANCE_DEG,   # [CITED]
        "slope": _SLOPE,                     # [ASSUMED] LINEAR
        "ipsf_cap": _ANGLE_CAP,              # [ASSUMED]
        "rule_id": "split_angle_over_tol_linear",
        "ipsf_anchor": "19-IPSF §A 트랙1 (스플릿 180° 목표, 160° 미만 요소 무효)",
        "deviation_source": "ipsf_absolute",
        "direction": "over_target",
        "split_fail_threshold_deg": _SPLIT_FAIL_THRESHOLD_DEG,  # [CITED] 0-fail 불연속
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

_CRITERION_BY_ID = {c["id"]: c for c in CRITERION_GROUPS}
# 측정-가능 ipsf_absolute criterion (measured-deviation seed 대상; reach 는 제외 — router-only).
_MEASURABLE_SEED_IDS = ("leg_extension", "arm_extension", "split_angle", "line")


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


# ── 라우터 키워드 (vision_veto._KEYPOINT_SET_BY_KEYWORD 스타일, substring match) ──
_SPLIT_KEYWORDS = ("스플릿", "split", "스트래들", "straddle")
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


def criteria_for_fault(fault_key, supported_difference, measured_deviations):
    """PUBLIC 라우터 (HIGH-1) — Gemini-pointed fault → 활성 criterion ids OR CoverageGap.

    body_part/fault_state(supported_difference 에서 읽음, gemini_vision_scorer schema)+
    measured substrate 로 라우팅한다. keypoint_set 단독 매핑은 불가(split/straddle/knee-reach
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

    # 1) split/straddle → split_angle ONLY (keypoint_set='leg' 로 정규화되지만 leg 아님).
    if _contains(body_part, _SPLIT_KEYWORDS):
        return ("split_angle",)

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
