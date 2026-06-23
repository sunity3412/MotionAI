"""v2 비전 거부권의 순수 코어 (Phase 20-01, D-01/D-02/D-05 + HIGH-3).

이 모듈은 numpy 외 의존이 0 이다 — boto3/Gemini/네트워크/firestore import 절대 금지.
Gemini 호출/파이프라인 wiring 은 후속 plan(20-02 adapter / 20-03 wiring)이 별도 모듈로
맡는다. 여기서는 phase 의 가장 중요한 안전 성질만 코드로 못 박는다:

  비전은 점수를 절대 올리지 않는다 (하향 전용, D-01).

왜 min() 으로 인코딩하나: kip-up 100/100 위양성(신뢰를 깬 사고)을 구조적으로 차단하기
위해서다. 가중블렌드/하한/상향연산은 비전이 점수를 올릴 수 있어 위양성을 재발시킨다 — 그래서
거부권은 오직 terminal min() 캡이다 (dimensions.overall_from_dimensions 의 min-of-core
overall 위에 합성된다, dimensions.py:384 정합).

cap 수치 출처도 데이터로 박제한다 (SEVERITY_CAP_PROVENANCE). 6페어에 curve-fit 하는
경로를 fail-closed 로 막기 위해, sensitivity manifest 의 실 sha256 가 없는 동안 cap 을
채우면 단위테스트(test_cap_fill_requires_real_manifest_sha)가 거부한다.

---
cap 활성화 모드 (provenance.method)
---
20-04 는 cap 수치를 **spec-anchored** 로 박는다 (belle 결정 2026-06-20):

  - major = 50  — belle 스펙 "잘못된 동작 ≤50" (CLAUDE.md core value /
    [[score-spec-95-100-elite-vision-fix]]) 을 그대로 못 박는다.
  - moderate = 75 — IPSF moderate-fault 의 원칙적 상한 (severity 의미 기반).
  - minor = 90 — 미세하지만 실재하는 결함도 천장 100 에서 내려준다 (Phase 20
    robustify, belle 2026-06-20: 고급 수강생은 미세 차이만 다르므로 mild fault 가
    100 으로 남으면 안 된다). 정타(none)는 여전히 무캡 → 100 보존.
  - none = None — 정타 무캡 (D-01 95~100 보존, 영구 None).

이 수치들은 데이터에 curve-fit 한 것이 아니라 belle 스펙 + IPSF severity 의미에서
나온다 (provenance.method == "spec_anchored", provenance.spec_basis 가 출처를
데이터로 박제). 6 deliberate-fault 페어는 회귀 검증(known-answer gate) 전용으로만
유지되며 cap 도출 입력으로 절대 쓰이지 않는다
(phase18_pairs_used_for_derivation == False, 영구 INVARIANT).

DEFERRED (후속 단계): 미보유 sensitivity 셋(온라인 영상)에서 cap 을 도출하는
generalization-tested eval — method == "sensitivity_derived" 경로. 그 경로에서는
sensitivity_manifest_sha256 가 실 sha 여야 cap 을 채울 수 있다 (HIGH-3 fail-closed).
현재는 미구현(derive_caps.py / sensitivity.yaml / eval_manifest 없음).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SEVERITY_CAP — severity → overall 상한 (20-04 spec-anchored 활성화).
#
# 수치는 데이터 curve-fit 이 아니라 belle 스펙 + IPSF severity 의미에서 나온다
# (provenance.method == "spec_anchored", provenance.spec_basis 가 데이터 출처):
#
#   - major = 50      — belle 스펙 "잘못된 동작 ≤50" 그대로 못 박음.
#   - moderate = 75   — IPSF moderate-fault 원칙적 상한 (severity 의미 기반).
#   - minor = 90      — 미세하지만 실재하는 결함도 천장 100 해제 (Phase 20 robustify).
#   - none = None     — 정타 무캡, 영구 None (D-01 95~100 보존).
#
# 6페어(정은지 단일 선수 + fault)에 curve-fit 하는 것은 절대 금지다 — 6페어는
# 회귀 검증(known-answer gate) 전용이며 cap 도출 입력이 아니다
# (D-02 / [[scoring-redesign-must-generalize-no-overfit]] / [[sensitivity-gate-not-just-elite-low]]).
#
# DEFERRED: 미보유 sensitivity 셋 derive 경로(method=="sensitivity_derived")는
# 후속 단계에서 보강한다. 그 경로에서만 sensitivity_manifest_sha256 가 실 sha 여야
# cap 을 채울 수 있다 (HIGH-3 fail-closed). spec_anchored 모드는 sha 없이 cap 가능하되
# spec_basis 데이터가 출처를 박제한다.
# ---------------------------------------------------------------------------
SEVERITY_CAP: dict[str, int | None] = {
    "minor": 90,       # 미세 결함도 천장 100 해제 (Phase 20 robustify, spec_anchored)
    "moderate": 75,    # IPSF moderate-fault 원칙적 상한 (spec_anchored)
    "major": 50,       # belle 스펙 "잘못된 동작 ≤50" (spec_anchored)
    "none": None,      # 정타 무캡 — 영구 None (D-01 95~100 보존)
}

# ---------------------------------------------------------------------------
# SEVERITY_CAP_PROVENANCE — cap 도출 출처를 주석이 아닌 **데이터**로 박제 (HIGH-3).
#
# - method: cap 활성화 모드. "spec_anchored" = belle 스펙 + IPSF severity 의미로
#   박은 값(현재). "sensitivity_derived" = 미보유 sensitivity 셋 eval 도출(후속,
#   미구현). method 별로 fail-closed 가드가 다르다 (아래 spec_basis / sha 참조).
# - source: cap 수치의 출처 라벨. spec_anchored 모드에서는 belle 스펙 + IPSF severity.
# - spec_basis: cap 수치 근거를 **데이터**로 박제 (주석 아님). belle 스펙
#   "잘못된 동작 ≤50" 을 명시 — test_provenance_is_data_not_comment 가 검사.
# - sensitivity_manifest_sha256: sensitivity_derived 경로에서만 의미. derive 가
#   sensitivity manifest 의 실 sha256 으로 채운다. spec_anchored 모드에서는 None
#   (도출 입력 아님). cap 을 sensitivity_derived 로 채우려면 실 sha 여야 한다
#   (TODO/None 금지) — test_cap_fill_requires_real_manifest_sha 가 강제 (fail-closed).
# - phase18_pairs_used_for_derivation: 영구 False (INVARIANT). 6페어는 회귀 검증
#   (known-answer gate) 전용이며 derive 입력이 아니다 — 어떤 method 도 이 값을
#   True 로 바꿀 수 없다 (6페어 curve-fit fail-closed).
# ---------------------------------------------------------------------------
SEVERITY_CAP_PROVENANCE: dict[str, object] = {
    "method": "spec_anchored",
    "source": "belle_spec_ipsf_severity",
    "spec_basis": (
        'belle spec "잘못된 동작 ≤50" '
        "(CLAUDE.md core value / score-spec-95-100-elite-vision-fix); "
        "moderate=75 from IPSF moderate-fault severity meaning; "
        "minor=90 — 미세 결함도 천장 100 해제, 정타(none)는 100 보존 "
        "(Phase 20 robustify, belle 2026-06-20)"
    ),
    "sensitivity_manifest_sha256": None,
    "phase18_pairs_used_for_derivation": False,
}


def apply_downward_cap(overall: int, severity: str | None) -> int:
    """v1 overall 을 vision severity 로 **하향만** 한다 (D-01 코어 invariant).

    severity → SEVERITY_CAP lookup 후 cap 이 있으면 min(overall, cap), 없으면 불변.
    None / 미지 키 / none → 불변 (정타 95~100 보존). minor 는 90 cap 적용 (Phase 20
    robustify — 미세하지만 실재하는 결함은 천장 100 에서 내려간다).

    invariant: 반환값 ≤ overall 항상. 올림 경로(상향연산/하한/가중블렌드) 절대 금지 —
    비전이 점수를 올리면 위양성(kip-up 100/100)이 재발한다.
    """
    cap = SEVERITY_CAP.get(severity)  # 미지 severity → None (불변)
    if cap is None:
        return overall
    # 하향 전용: 입력보다 cap 이 높아도 절대 올리지 않는다 (min only).
    return min(overall, cap)


# ---------------------------------------------------------------------------
# fault_joints_from_differences — Gemini verdict.differences[].body_part(자유 텍스트
# 한국어) → 앱이 강조 가능한 정식 keypoint 이름으로 매핑 (Phase 20 #3, 2026-06-21).
#
# 왜 backend 매핑인가: 마커 강조는 backend 산출(KeypointOverlay "산출 출처=backend만"
# 원칙). 앱은 NLP 0 — faultJoints 를 그대로 강조한다. 마커가 각도편차 최대 관절(어깨/
# 팔꿈치)에 찍히던 버그의 진짜 fix — Gemini 가 본 실제 결함 위치를 강조한다.
#
# 출력 keypoint 집합은 KeypointOverlay 가 그리는 8개로 제한:
#   left/right_shoulder, left/right_hip, left/right_knee, left/right_hand.
# (손=elbow/wrist 시각 proxy. ankle/torso 등 미표시 keypoint 는 최근접으로 매핑.)
# ---------------------------------------------------------------------------
_HIGHLIGHT_KEYPOINTS = (
    "left_shoulder", "right_shoulder",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_hand", "right_hand",
)

# base joint(좌우 없는) → 적용할 side-suffixed keypoint 생성용 base 이름.
# 'leg' 류는 무릎+엉덩이 둘 다, 'trunk' 류는 양 어깨+양 엉덩이(전신 라인).
_PART_KEYWORDS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    # (keyword 들, base joint 들) — 먼저 매칭되는 항목 우선 아님(전부 union).
    (("스트래들", "straddle", "스플릿", "split", "가랑이", "벌려"), ("__legs_both__",)),
    # 머리/목 (Task 2 D-09 H1) → 최근접 keypoint = 어깨 (미표시 keypoint 선례 ankle→knee).
    (("머리", "고개", "목", "head", "neck"), ("shoulder",)),
    (("어깨", "shoulder"), ("shoulder",)),
    (("팔꿈치", "elbow"), ("hand",)),
    # 그립/손바닥 (Task 2) → 손 (그립 풀림/손 떨어짐 결함 위치).
    (("그립", "grip", "손바닥"), ("hand",)),
    (("손목", "wrist", "손", "hand"), ("hand",)),
    (("팔", "arm"), ("hand", "shoulder")),
    (("무릎", "knee"), ("knee",)),
    (("엉덩이", "골반", "hip", "pelvis", "둔부"), ("hip",)),
    (("허벅지", "thigh", "종아리", "정강이", "shin", "calf"), ("knee", "hip")),
    (("다리", "leg", "하체"), ("knee", "hip")),
    (("발목", "ankle", "발", "foot"), ("knee",)),  # 미표시 keypoint → 최근접 무릎
    (("코어", "core", "몸통", "torso", "허리", "등", "back",
      "라인", "line", "정렬", "alignment", "상체", "trunk"), ("__trunk__",)),
)


# ---------------------------------------------------------------------------
# FaultKey — canonical 결함 키 단일 직렬화 owner (Task 2, D-17 MED-3 + D-09 HIGH-2).
#
# support/recall 집계가 raw body_part 문자열이 아니라 canonical FaultKey 로 센다 —
# "왼팔/left arm/왼쪽 팔꿈치" alias 가 한 키로 합쳐지고(좌/우팔 recall 손실 방지),
# 모호한 "팔"은 side="unknown"(양쪽 부풀림 방지). 23-03 manifest expected_recall_keys
# 와 result recall_set 이 이 단일 어휘를 공유한다(VisionFaultContext.to_trace_dict 도
# FaultKey.to_dict 어휘를 방출). from_dict 가 enum 밖 값을 거부(raise)해 Pod 결과를
# 보기 전 unknown fault_kind 를 차단한다.
#
# 어휘는 generic — 동작명/curve-fit 금지(D-06). fault_kind 는 결함 종류의 거친 분류만.
# ---------------------------------------------------------------------------
FAULT_PART_SCOPES = ("upper_body", "core", "lower_body", "line")
FAULT_SIDES = ("left", "right", "unknown")
FAULT_KEYPOINT_SETS = (
    "arm", "shoulder", "leg", "hip", "head_neck", "grip", "torso", "line",
)
FAULT_KINDS = (
    "pole_gap_or_bent",        # 폴-갭/굽음 (팔/그립이 폴에서 떨어짐·굽음)
    "extension_or_alignment",  # 신전 부족/정렬 흐트러짐
)


def _faultkey_validate(part_scope, side, keypoint_set, fault_kind):
    """locked enum 검증 — 밖 값이면 ValueError (D-17 MED-3)."""
    if part_scope not in FAULT_PART_SCOPES:
        raise ValueError(f"unknown part_scope: {part_scope!r}")
    if side not in FAULT_SIDES:
        raise ValueError(f"unknown side: {side!r}")
    if keypoint_set not in FAULT_KEYPOINT_SETS:
        raise ValueError(f"unknown keypoint_set: {keypoint_set!r}")
    if fault_kind not in FAULT_KINDS:
        raise ValueError(f"unknown fault_kind: {fault_kind!r}")


from dataclasses import dataclass  # noqa: E402 — FaultKey 정의 직전 local import


@dataclass(frozen=True)
class FaultKey:
    """canonical 결함 키 (단일 직렬화 owner). part_scope/side/keypoint_set/fault_kind."""

    part_scope: str
    side: str
    keypoint_set: str
    fault_kind: str

    def to_dict(self) -> dict:
        """정규화 dict (enum 검증 후). to_trace_dict 어휘와 동일 (D-17 MED-3)."""
        _faultkey_validate(
            self.part_scope, self.side, self.keypoint_set, self.fault_kind
        )
        return {
            "part_scope": self.part_scope,
            "side": self.side,
            "keypoint_set": self.keypoint_set,
            "fault_kind": self.fault_kind,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FaultKey":
        """dict → FaultKey. enum 밖 값(unknown fault_kind 등)은 raise (D-17 MED-3)."""
        part_scope = str((d or {}).get("part_scope", ""))
        side = str((d or {}).get("side", ""))
        keypoint_set = str((d or {}).get("keypoint_set", ""))
        fault_kind = str((d or {}).get("fault_kind", ""))
        _faultkey_validate(part_scope, side, keypoint_set, fault_kind)
        return cls(part_scope, side, keypoint_set, fault_kind)


_KEYPOINT_SET_BY_KEYWORD: tuple[tuple[tuple[str, ...], str], ...] = (
    (("머리", "고개", "목", "head", "neck"), "head_neck"),
    (("그립", "grip", "손바닥"), "grip"),
    (("팔꿈치", "elbow", "손목", "wrist", "손", "hand", "팔", "arm"), "arm"),
    (("어깨", "shoulder", "견갑"), "shoulder"),
    (("무릎", "knee", "허벅지", "thigh", "종아리", "정강이", "다리", "leg",
      "발목", "ankle", "발", "foot", "스플릿", "split", "스트래들", "straddle"), "leg"),
    (("엉덩이", "골반", "hip", "pelvis", "둔부", "코어", "core", "허리"), "hip"),
    (("라인", "line", "정렬", "alignment", "몸통", "torso", "trunk"), "line"),
)


def _keypoint_set_for(body_part: str) -> str:
    """body_part → canonical keypoint_set (FaultKey 집계용). 미상은 'torso'."""
    part = str(body_part or "").lower()
    for keywords, kp_set in _KEYPOINT_SET_BY_KEYWORD:
        if any(kw.lower() in part for kw in keywords):
            return kp_set
    return "torso"


def _fault_kind_for(difference: dict) -> str:
    """difference → canonical fault_kind. 폴-갭/떨어짐/풀림 → pole_gap_or_bent, 그 외 신전/정렬."""
    text = " ".join(
        str((difference or {}).get(k, ""))
        for k in ("body_part", "fault_state", "ipsf_note", "correct_state")
    ).lower()
    gap_markers = ("떨어", "갭", "gap", "풀림", "풀려", "굽", "bent", "벌어")
    if any(m in text for m in gap_markers):
        return "pole_gap_or_bent"
    return "extension_or_alignment"


def fault_key_from_difference(difference: dict, *, part_scope_hint: str = "line") -> FaultKey:
    """Gemini difference → canonical FaultKey (support/recall 집계 키, D-09 HIGH-2)."""
    body_part = str((difference or {}).get("body_part", ""))
    sides = _sides_for(body_part.lower())
    side = sides[0] if len(sides) == 1 else "unknown"
    keypoint_set = _keypoint_set_for(body_part)
    part_scope = part_scope_hint if part_scope_hint in FAULT_PART_SCOPES else "line"
    fault_kind = _fault_kind_for(difference)
    return FaultKey(
        part_scope=part_scope, side=side,
        keypoint_set=keypoint_set, fault_kind=fault_kind,
    )


@dataclass(frozen=True)
class RootCauseHypothesis:
    """support 게이트 통과분에서만 유도된 원인 가설 (provenance 보존, D-13 MED-1).

    text = 원인 설명(자연어, 숫자 점수 금지). fault_key = canonical FaultKey.
    source_difference_ids = 이 가설을 뒷받침한 difference 식별자 tuple. support_count =
    canonical 키 support 수. support 게이트가 drop 한 환각 difference 의 root cause 는
    여기 도달하지 않는다(one-frame 설명 재발 방지).
    """

    text: str
    fault_key: FaultKey
    source_difference_ids: tuple
    support_count: int


def _sides_for(text: str) -> tuple[str, ...]:
    """body_part 문자열에서 좌/우를 추정. 명시 없으면 ('left','right') 양쪽."""
    has_left = ("왼" in text) or ("좌" in text) or ("left" in text)
    has_right = ("오른" in text) or ("우측" in text) or ("right" in text)
    if has_left and not has_right:
        return ("left",)
    if has_right and not has_left:
        return ("right",)
    return ("left", "right")


def _keypoints_for_part(body_part: str) -> list[str]:
    """단일 body_part(한국어 자유텍스트) → 정식 keypoint list (순서 안정·중복 제거).

    keyword 매핑 + 좌/우 추정. 스트래들/스플릿=양 다리(무릎+엉덩이), 라인/전신/상체
    =trunk(양 어깨+양 엉덩이). 매핑 불가면 빈 list.
    """
    out: list[str] = []

    def _add(name: str) -> None:
        if name in _HIGHLIGHT_KEYPOINTS and name not in out:
            out.append(name)

    part = str(body_part or "").lower()
    if not part.strip():
        return out
    sides = _sides_for(part)
    for keywords, bases in _PART_KEYWORDS:
        if not any(kw.lower() in part for kw in keywords):
            continue
        for base in bases:
            if base == "__legs_both__":
                for s in ("left", "right"):
                    _add(f"{s}_knee")
                    _add(f"{s}_hip")
            elif base == "__trunk__":
                for s in ("left", "right"):
                    _add(f"{s}_shoulder")
                    _add(f"{s}_hip")
            else:
                for s in sides:
                    _add(f"{s}_{base}")
    return out


def fault_joints_from_differences(differences) -> list[str]:
    """Gemini differences → 강조할 keypoint 이름 list (순서 안정·중복 제거, 순수).

    각 difference 의 body_part 를 _keypoints_for_part 로 변환 후 union. 결과 없으면
    빈 list (호출측이 기존 편차-기반 폴백 사용).
    """
    out: list[str] = []
    for d in differences or ():
        for kp in _keypoints_for_part((d or {}).get("body_part", "")):
            if kp not in out:
                out.append(kp)
    return out


def fault_joint_deficits_from_differences(differences) -> dict[str, float]:
    """Gemini differences → {keypoint: approx_angle_deviation_deg} (시각 추정 deficit).

    fault-zoom 의 deficit 숫자 source. kismam 각도 delta 는 veto 가 발동한 결함을
    구조적으로 못 잡으므로(그래서 veto 발동) 작게 나온다 → Gemini 의 visual 추정을
    쓴다. 한 body_part 가 여러 keypoint 로 확장되면 같은 deviation 을 부여하고,
    여러 difference 가 같은 keypoint 를 가리키면 **최대** deviation 을 남긴다. 0/미상은
    제외(숫자 안 그림). 순수.
    """
    out: dict[str, float] = {}
    for d in differences or ():
        try:
            dev = float((d or {}).get("approx_angle_deviation_deg") or 0.0)
        except (TypeError, ValueError):
            dev = 0.0
        if dev <= 0:
            continue
        for kp in _keypoints_for_part((d or {}).get("body_part", "")):
            if dev > out.get(kp, 0.0):
                out[kp] = dev
    return out


# ---------------------------------------------------------------------------
# DTW 정렬 신뢰도 게이팅 (Task 3, D-03 + H4) — 글로벌 + 로컬 신호 결합.
#
# 글로벌(MotionMatch.distance)만으로는 시작점/템포가 다른 정상 Mode1 케이스에서 잘못된
# 프레임을 비교에 넣을 수 있다(H4). 로컬 신호 3개를 함께 본다:
#   ① 선택 프레임 주변 path 밀도/대응 분산, ② 매칭 ref-frame 존재 여부,
#   ③ 선택 프레임 keypoint 가시성/confidence.
# 채택 경로 enum: single | window_union | low_alignment_confidence.
# 임계는 generic 상수 — 특정 영상 튜닝 금지(D-06). DTW median(per_joint_deviation)은
# scoring 경로이므로 본 helper 와 섞지 않는다(D-10 HIGH-3). 하향-전용 모듈 규칙(상향 연산
# 금지)에 따라 비교는 if/else 로만 표현한다(올림 연산자 미사용).
# ---------------------------------------------------------------------------
_ALIGN_GLOBAL_T1 = 8.0     # 글로벌 distance 1차 임계 (초과 시 window_union 고려)
_ALIGN_GLOBAL_T2 = 25.0    # 글로벌 distance 2차 임계 (초과 시 low_alignment 후보)
_ALIGN_LOCAL_PATH_MIN = 2  # 선택 프레임 주변 path 대응 최소 개수
_ALIGN_VIS_MIN = 0.35      # keypoint 가시성/confidence 최소


def assess_alignment_confidence(
    *,
    match,
    selected_user_frame: int,
    keypoint_visibility: float,
    window: int = 2,
) -> dict:
    """글로벌+로컬 정렬 신뢰도 → 채택 경로 enum (순수, H4).

    반환 dict: {adoption, global_ok, local_ok, localPathCount, refFramePresent,
    visibility}. adoption ∈ {single, window_union, low_alignment_confidence}.
    글로벌 양호 + 로컬 약함이면 single 을 채택하지 않는다(window_union 또는 보류).
    """
    distance = float(getattr(match, "distance", 0.0) or 0.0)
    path = getattr(match, "path", None) or []
    start = int(getattr(match, "start", 0) or 0)
    local = selected_user_frame - start

    # 로컬: 선택 프레임 ±window 안의 path 대응 개수 + ref-frame 존재.
    near = [j for (i, j) in path if abs(i - local) <= window]
    local_path_count = len(near)
    ref_present = local_path_count > 0
    visibility = float(keypoint_visibility or 0.0)

    if distance > _ALIGN_GLOBAL_T2:
        global_ok = False
        global_weak = True
    elif distance > _ALIGN_GLOBAL_T1:
        global_ok = True
        global_weak = True  # 1차 초과 → window_union 고려.
    else:
        global_ok = True
        global_weak = False

    local_ok = (
        local_path_count >= _ALIGN_LOCAL_PATH_MIN
        and ref_present
        and visibility >= _ALIGN_VIS_MIN
    )

    if not global_ok and not local_ok:
        adoption = "low_alignment_confidence"
    elif not global_ok:
        # 글로벌 2차 실패지만 로컬은 견고 → ±윈도우 union 으로 보강.
        adoption = "window_union"
    elif not local_ok:
        # 글로벌 양호인데 로컬 약함 → single 채택 금지(H4). 가시성/path 둘 다 바닥이면 보류.
        if visibility < _ALIGN_VIS_MIN and not ref_present:
            adoption = "low_alignment_confidence"
        else:
            adoption = "window_union"
    elif global_weak:
        adoption = "window_union"
    else:
        adoption = "single"

    return {
        "adoption": adoption,
        "global_ok": global_ok,
        "local_ok": local_ok,
        "localPathCount": local_path_count,
        "refFramePresent": ref_present,
        "visibility": visibility,
        "distance": distance,
    }


# 부위별 worst 후보 selector 버전 — 캐시 키 입력. 변경 시 stale 무효화.
WORST_SELECTOR_VERSION = "v1"


def select_worst_frame_candidates(profile) -> dict:
    """글로벌 worst timestamp + 부위별(상체/하체/라인) worst 후보 list (H4/MEDIUM).

    상체 결함 프레임이 글로벌 worst 와 다를 수 있으므로 부위별 후보를 함께 낸다. 현재는
    key_moments(hold/peak) 재사용으로 글로벌 worst 를 잡고 부위 스코프 토큰을 부착한다
    (실제 부위별 프레임 정밀화는 Gemini fan-out 이 부위 프롬프트로 보강). selector_version
    을 노출(캐시 키 입력).
    """
    global_ts = worst_pose_timestamp(profile)
    candidates = []
    for scope in ("upper_body", "lower_body", "line"):
        candidates.append({
            "part_scope": scope,
            "worst_seconds": global_ts,
        })
    return {
        "selector_version": WORST_SELECTOR_VERSION,
        "global_worst_seconds": global_ts,
        "candidates": candidates,
    }


def worst_pose_timestamp(profile) -> float | None:
    """지배 결함 pose 시점을 key_moments 재사용으로 고른다 (D-05).

    우선순위: hold > peak > 전체. 각 그룹에서 가장 이른(min) timestamp 를 고른다.
    IPSF phase 평균 거부 — 평균은 Phase 19 에서 고친 "결함이 정상 관절에 희석되는"
    바로 그 버그다. 단일 지배 pose 만 선택한다.

    신규 Gemini moment 호출 0 — profile.key_moments(Phase 8/11 technique profile)
    만 읽는다 (순수). key_moments None/빈/속성 부재 → None (graceful).

    timestamp 단위는 초(영상 시작점 기준). frame_extractor.py target_fps = 9.0
    이지만 본 함수는 초 단위만 다룬다 (frame 변환은 호출 측 책임).
    """
    moments = getattr(profile, "key_moments", None) or ()
    if not moments:
        return None

    def _ts(group_key: str | None) -> float | None:
        if group_key is None:
            chosen = moments
        else:
            chosen = [
                m for m in moments if getattr(m, "moment_key", None) == group_key
            ]
        timestamps = [
            float(getattr(m, "timestamp_seconds"))
            for m in chosen
            if getattr(m, "timestamp_seconds", None) is not None
        ]
        return min(timestamps) if timestamps else None

    # 명시적 None 검사 — `or` 는 timestamp 0.0(영상 시작 hold)을 falsy 로 떨어뜨려
    # hold→peak 로 잘못 폴백한다. None 만 폴백 신호로 쓴다.
    for group in ("hold", "peak", None):
        ts = _ts(group)
        if ts is not None:
            return ts
    return None
