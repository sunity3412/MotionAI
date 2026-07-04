"""v2 비전 결함-짚기의 순수 코어 (Phase 20-01 + Phase 24 밴드 제거, ND-01/ND-02).

이 모듈은 numpy 외 의존이 0 이다 — boto3/Gemini/네트워크/firestore import 절대 금지.
Gemini 호출/파이프라인 wiring 은 후속 plan 이 별도 모듈로 맡는다. 여기서는 measurement/
FaultKey/baseline/worst-pose helpers 와 정량화(칸/각도) substrate 만 못 박는다.

Phase 24 (ND-01/ND-02) — severity→고정천장 밴드 제거:
  비전은 점수를 절대 내지 않는다 — **측정대상/criterion 만 짚는다**.

과거(Phase 20)의 severity→고정천장 밴드(severity enum 을 고정 ceiling 으로 min() 하던
경로)는 belle 가 철학적으로 거부(2026-06-24 [[scoring-must-be-transparent-deduction-tally]]):
severity→고정밴드는 영상마다 자의적 = 사람 판단 주입 = AI 존재이유 무효. 채점은
deduction_engine.tally(측정편차→명시규칙 감점→합산)로 교체됐고, severity 는 더 이상
점수 입력이 아니다(coachRootCauseEligible continuity 용 non-scoring 라벨일 뿐).
이 모듈의 helper(FaultKey/body_relative_notches/build_quantification_result/worst_pose/
BASELINE_KINDS)는 그 엔진의 측정 substrate 로 보존·재사용된다.
"""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# FAULT_CATEGORIES — Gemini 구조화 출력의 결함 분류 고정 enum (25-05, 단일 owner).
#
# 어휘 드리프트 3연속 실측(v9 body_part "양다리 (스플릿 각도)" → v10.1 스플릿이
# fault_state 로 이동 → v11 "벌림"+fault_kind=extension_or_alignment 오분류)의 근본
# fix: 자유-텍스트 키워드 파싱은 프롬프트 버전마다 새는 두더지잡기 — 스키마
# (gemini_vision_scorer.build_schema v8.1)가 응답을 이 enum 으로 강제하고, 라우터
# (ipsf_criteria.criteria_for_fault)가 enum 을 1순위로 소비한다.
#
# 기존 criterion/FaultKey 체계와 1:1 대응 — 새 분류 발명 금지:
#   split_angle    → criterion split_angle (양다리 벌림/찢기 각도 부족)
#   limb_extension → leg_extension/arm_extension (leg vs arm 은 body_part 소관)
#   pole_gap       → FaultKey fault_kind pole_gap_or_bent (폴 이탈/밀착 풀림)
#   alignment      → criterion line (전체 라인/정렬)
#   grip           → grip coverage gap (COVERAGE_GAP_KEYPOINT_SETS)
#   other          → 분류 정보 0 — 라우터 키워드 폴백 체인
# ---------------------------------------------------------------------------
FAULT_CATEGORIES = (
    "split_angle",
    "limb_extension",
    "pole_gap",
    "alignment",
    "grip",
    "other",
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


# 25-02 review WR-03 — 보수적 매핑: torso-성("허리"/"코어")·grip-성("손"/"손목") 언급을
# hip/arm 으로 승격하지 않는다. keypoint_set=hip/arm 은 pointed 감점 게이트(window-측정
# eligible)로 이어지므로, 의미상 몸통/그립 결함이 hip/elbow 각도 감점으로 둔갑하는 우회를
# 차단한다. 허리/코어는 어느 행에도 없음 → default "torso" (CoverageGap 종착, 감점 0).
_KEYPOINT_SET_BY_KEYWORD: tuple[tuple[tuple[str, ...], str], ...] = (
    # grip 행이 head_neck 보다 먼저 — "손목" 이 "목" substring 으로 head_neck 에 오분류되는
    # 것을 방지 (substring match 순서 의존).
    (("그립", "grip", "손바닥", "손목", "wrist", "손", "hand"), "grip"),
    (("머리", "고개", "목", "head", "neck"), "head_neck"),
    (("팔꿈치", "elbow", "팔", "arm"), "arm"),
    (("어깨", "shoulder", "견갑"), "shoulder"),
    (("무릎", "knee", "허벅지", "thigh", "종아리", "정강이", "다리", "leg",
      "발목", "ankle", "발", "foot", "스플릿", "split", "스트래들", "straddle"), "leg"),
    (("엉덩이", "골반", "hip", "pelvis", "둔부"), "hip"),
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


def explicit_measured_deviation_deg(difference) -> float | None:
    """명시 각도쌍(student_angle_deg, reference_angle_deg) → 산술 편차 |ref − student| (deg).

    25-04 #3(a) 측정 강건화의 단일 owner: Gemini 는 학생/기준 각도를 **각각** 명시
    추정하고(measurement rubric, gemini_vision_scorer PROMPT v11.0/SCHEMA v8.0), 편차는
    코드가 산술로 계산한다 — "Gemini 는 측정대상을 짚고 각도를 읽되, 숫자 규칙은 코드
    소관" 원칙([[scoring-must-be-transparent-deduction-tally]]) 정합. "편차 한 방 추정"
    은 앵커링 편향으로 tol 경계(20°)를 넘나드는 변동을 냈다(run3 kip-up: v9 30° → v10.1
    20°) — 산술화가 그 변동 축을 제거한다.

    둘 중 하나라도 부재/비수치/NaN/Inf → None (honest skip — approx_angle_deviation_deg
    폴백 여부는 소비자 소관). 편차 0.0 도 유효한 측정 결과로 반환한다(= "재봤더니 차이
    없음"; 소비자는 >0 만 감점 주입). dict/obj 모두 처리, 캐시 round-trip 이 문자열화한
    값도 float 캐스팅. 순수 함수 — 새 튜닝 상수 0.
    """
    def _get(key):
        if isinstance(difference, dict):
            return difference.get(key)
        return getattr(difference, key, None)

    try:
        student = float(_get("student_angle_deg"))
        reference = float(_get("reference_angle_deg"))
    except (TypeError, ValueError):
        return None
    for v in (student, reference):
        if v != v or v in (float("inf"), float("-inf")):  # NaN/Inf guard
            return None
    return abs(reference - student)


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


# ---------------------------------------------------------------------------
# VisionFaultContext / VisionQuantificationResult / SelectedFramePair (Task 4).
#
# 계약 경계 (D-12 HIGH-1 + D-11 MED-2): context/quant/audit 객체를 분리한다.
#   · VisionFaultContext   = pre-apply/pre-coach 데이터만. final-audit status 도 geometry
#                            payload 도 들지 않는다(final 은 apply 가 deduction tally 후 확정,
#                            geometry 는 23-02 가 이후 산출).
#   · VisionQuantificationResult = post-geometry (23-02 Task1/2/4 산출, apply 가 audit 주입).
#   · audit 직렬화 = ctx.to_audit_dict(final_status, breakdown_final, quantification) — apply 의
#                    deduction tally 계산 후에만 final-audit 필드 방출(Phase 24, 밴드 제거).
# collection_status 는 pre-final enum 전용 — applied/not_applicable(final) 로 생성 불가
# (D-13 MED-2). final status 와 vocabulary 가 겹치지 않는다.
# ---------------------------------------------------------------------------
VISION_FAULT_COLLECTION_STATUSES = (
    "candidate_verdict",          # 정식 verdict 후보 (cap_would_apply 와 함께 coach 게이트)
    "no_fault",                   # 정타/none — 결함 없음
    "low_alignment_confidence",   # 정렬 신뢰도 낮음 — collect 가 Gemini 호출 전 bail.
                                  # 24-04(Option A): apply seam 에서는 measured-seed
                                  # tally-eligible(RTMW 측정 편차는 정렬-독립). Gemini
                                  # fault 는 부재(supported_differences=[]) — fabricate 금지.
    "resource_limited",           # 예산 소진 fail-closed (보류)
    "disabled",                   # 토글 OFF
    "mode3_held",                 # Mode3 보류
    "missing_reference",          # Mode1 기준 영상 부재
    "missing_current_video",      # 학생 local 영상 부재
    "skipped_error",              # adapter None/예외 graceful
)
# final-audit status (collection_status 와 vocabulary 겹침 금지) — to_audit_dict 만 방출.
_FINAL_AUDIT_STATUSES = ("applied", "not_applicable")


@dataclass(frozen=True)
class VisionQuantificationResult:
    """post-geometry 정량화 결과 (D-12 HIGH-1). 23-02 Task1/2/4 가 산출, apply 가 주입.

    pre-coach VisionFaultContext 는 이 payload 를 들지 않는다(pre-apply audit drift 차단).
    """

    quantificationStatus: str  # available | unavailable
    angleDeltas: object = None
    bodyRelativeNotches: object = None
    windowMedianAngleDeltas: object = None
    warnings: tuple | list = ()


@dataclass(frozen=True)
class SelectedFramePair:
    """still 프레임 추출/정리 계약 (D-10 HIGH-2).

    student/reference frame path + idx + 양 프레임 keypoints/confidence + cleanup handles.
    cleanup_paths 는 생성된 로컬 이미지 파일 경로 — 호출자 finally 가 unlink(Gemini File
    API delete 와 독립). ref frame 은 fault_zoom._matched_ref_frame(DTW match)로 선택
    (DTW 재계산 금지).
    """

    student_frame_path: str | None
    reference_frame_path: str | None
    user_frame_idx: int
    ref_frame_idx: int
    student_keypoints: object = None
    reference_keypoints: object = None
    student_confidence: float | None = None
    reference_confidence: float | None = None
    cleanup_paths: tuple = ()


# ---------------------------------------------------------------------------
# FramePairMeasurementContext — 결정적 칸/각도 정량화 입력 계약 (23-02 Task 2, D-09/D-10 HIGH-3).
#
# 칸·각도는 verdict 를 낸 **그 still 프레임 쌍**의 keypoints 에서만 계산한다(same-frame
# 강제). 이 객체가 그 계약을 못 박는다 — user_frame_idx/ref_frame_idx + 그 인덱스의
# keypoints + baseline kind(동작별: 바닥/폴/엉덩이-라인) + 가시성/selector_version. static
# bodyComparisonSourcePose / video-level 폴라인 / body-profile 요약으로 폴백하면
# polished-but-wrong 수치가 나오므로(틀린 프레임), 그런 입력은 받지 않는다.
#
# keypoints 형상은 (NUM_KEYPOINTS, 2|3) — (x, y[, z]). COCO-17 순서(skeleton.KEYPOINT_NAMES).
# baseline_kind ∈ {floor, pole_vertical, hip_line} — 동작 맥락 인자로 분기(kip-up 류=바닥,
# 공중 동작=폴 수직/엉덩이-라인). pole_line = image-2D PoleLine2D(폴 baseline 일 때만 필요).
# ---------------------------------------------------------------------------
BASELINE_KINDS = ("floor", "pole_vertical", "hip_line")


@dataclass(frozen=True)
class FramePairMeasurementContext:
    """결정적 칸/각도 정량화 입력 (verdict 프레임 쌍 same-frame 강제, D-09/D-10 HIGH-3).

    user_frame_idx/ref_frame_idx = verdict 를 낸 그 프레임. student/reference_keypoints =
    그 인덱스의 keypoints (COCO-17, (K,2|3)). baseline_kind = 동작 맥락(floor/pole_vertical/
    hip_line). pole_line = 폴 baseline 일 때 image-2D PoleLine2D. visibility = 가시성 신호.
    selector_version = worst-frame selector 버전(캐시 키 입력).
    """

    user_frame_idx: int
    ref_frame_idx: int
    student_keypoints: object  # (K,2|3) ndarray-like 또는 None
    reference_keypoints: object
    baseline_kind: str
    pole_line: object = None  # pole_geometry.PoleLine2D | None
    floor_y: float | None = None  # 바닥 baseline 의 y (image-2D, normalized 또는 px)
    visibility: float | None = None
    selector_version: str | None = None


# 칸 reach 시각 proxy → COCO-17 실제 keypoint (손=손목 proxy, fault_joints 선례 정합).
_NOTCH_KEYPOINT_ALIAS = {
    "left_hand": "left_wrist",
    "right_hand": "right_wrist",
}


def _kp_xy(keypoints, name: str):
    """COCO-17 keypoints 에서 name 의 (x, y) 추출. 손=손목 proxy. 결측/NaN → None (순수)."""
    import numpy as np

    if keypoints is None:
        return None
    from . import skeleton

    name = _NOTCH_KEYPOINT_ALIAS.get(name, name)
    try:
        arr = np.asarray(keypoints, dtype=float)
    except (TypeError, ValueError):
        return None
    if arr.ndim != 2 or arr.shape[0] < skeleton.NUM_KEYPOINTS or arr.shape[1] < 2:
        return None
    try:
        idx = skeleton.kp_index(name)
    except KeyError:
        return None
    x, y = float(arr[idx, 0]), float(arr[idx, 1])
    if not (np.isfinite(x) and np.isfinite(y)):
        return None
    return (x, y)


def _baseline_unit_length(keypoints) -> float | None:
    """body-normalization 보조 단위 — 어깨중점↔엉덩이중점 torso 길이를 1칸 단위로 환산.

    체형(arm/leg/torso) 차이를 정규화하는 보조 단위(D-08: body_normalization 은 칸 환산
    내부 단위, 출력 표기는 칸). torso 길이 = sqrt 거리. keypoint 결측 → None.
    """
    import numpy as np

    ls = _kp_xy(keypoints, "left_shoulder")
    rs = _kp_xy(keypoints, "right_shoulder")
    lh = _kp_xy(keypoints, "left_hip")
    rh = _kp_xy(keypoints, "right_hip")
    if not (ls and rs and lh and rh):
        return None
    sh_mid = ((ls[0] + rs[0]) / 2.0, (ls[1] + rs[1]) / 2.0)
    hip_mid = ((lh[0] + rh[0]) / 2.0, (lh[1] + rh[1]) / 2.0)
    length = float(np.hypot(sh_mid[0] - hip_mid[0], sh_mid[1] - hip_mid[1]))
    if not np.isfinite(length) or length <= 0:
        return None
    return length


def _reach_to_baseline(point, ctx: "FramePairMeasurementContext", keypoints) -> float | None:
    """point 의 baseline 까지 reach (image-2D 거리). baseline_kind 별 분기 (D-08 H2).

    · floor         — point.y 에서 floor_y 까지 수직 거리.
    · pole_vertical — point 에서 pole_line 까지 점-직선 거리.
    · hip_line      — point.y 에서 엉덩이중점.y 까지 수직 거리(엉덩이-라인 baseline).
    baseline 입력 결측 시 None (호출자가 unavailable 처리). Gemini 입력 없이 keypoint·
    baseline 만으로 재현 가능 — 같은 입력=같은 reach(결정적).
    """
    if point is None:
        return None
    kind = ctx.baseline_kind
    if kind == "floor":
        if ctx.floor_y is None:
            return None
        return abs(float(point[1]) - float(ctx.floor_y))
    if kind == "pole_vertical":
        if ctx.pole_line is None:
            return None
        from . import pole_geometry

        return float(
            pole_geometry.point_to_pole_line_distance_2d(
                (float(point[0]), float(point[1])), ctx.pole_line
            )
        )
    if kind == "hip_line":
        lh = _kp_xy(keypoints, "left_hip")
        rh = _kp_xy(keypoints, "right_hip")
        if not (lh and rh):
            return None
        hip_y = (lh[1] + rh[1]) / 2.0
        return abs(float(point[1]) - hip_y)
    return None


def _quantize_notches(value: float) -> float:
    """reach/unit 비율 → ⅓ 단위 칸 수치 (정수 또는 분수 칸). 음수는 0. percent 금지(D-08)."""
    if value <= 0:
        return 0.0
    return round(value * 3.0) / 3.0


# 칸 측정 대상 reach keypoint — 결함 위치 시각 proxy (8 highlight keypoint 부분집합).
_NOTCH_REACH_KEYPOINTS = ("left_hand", "right_hand", "left_knee", "right_knee")


def body_relative_notches(
    measurement: "FramePairMeasurementContext",
) -> list[dict] | None:
    """결정적 칸/층 — keypoint + baseline 만으로 정수/분수 칸 산출 (H2, Gemini 미산출).

    정은지 reach = N칸 을 기준으로 두고 학생을 같은 baseline·body-normalization 단위로
    환산("정은지 3칸, 너 2칸 ⅔"). 칸 = reach / torso 보조 단위 를 ⅓ 단위로 양자화. **percent
    표기 절대 금지**(D-08 — gemini_vision_scorer._SCORE_PATTERN 누수). 각 항목 source='geometry'.

    same-frame(D-09/D-10 HIGH-3): measurement 의 그 프레임 keypoints 에서만 계산. 필수
    per-frame 입력(keypoint/baseline) 결측 → None(호출자가 quantificationStatus="unavailable").
    같은 입력=같은 칸(결정적, Gemini 인자 부재).
    """
    if measurement is None:
        return None
    if measurement.baseline_kind not in BASELINE_KINDS:
        return None
    s_kp = measurement.student_keypoints
    r_kp = measurement.reference_keypoints
    if s_kp is None or r_kp is None:
        return None
    s_unit = _baseline_unit_length(s_kp)
    r_unit = _baseline_unit_length(r_kp)
    if s_unit is None or r_unit is None:
        return None

    out: list[dict] = []
    for name in _NOTCH_REACH_KEYPOINTS:
        s_pt = _kp_xy(s_kp, name)
        r_pt = _kp_xy(r_kp, name)
        if s_pt is None or r_pt is None:
            continue
        s_reach = _reach_to_baseline(s_pt, measurement, s_kp)
        r_reach = _reach_to_baseline(r_pt, measurement, r_kp)
        if s_reach is None or r_reach is None:
            # baseline 입력 결측 — 칸 계산 불가 (전체 unavailable).
            return None
        student_notches = _quantize_notches(s_reach / s_unit)
        reference_notches = _quantize_notches(r_reach / r_unit)
        out.append({
            "keypoint": name,
            "student_notches": student_notches,
            "reference_notches": reference_notches,
            "delta_notches": round(student_notches - reference_notches, 4),
            "baseline_kind": measurement.baseline_kind,
            "source": "geometry",
        })
    if not out:
        return None
    return out


def build_quantification_result(
    *,
    measurement: "FramePairMeasurementContext | None",
    student_angles=None,
    reference_angles=None,
    window: int = 2,
) -> "VisionQuantificationResult":
    """frame-specific 각도(Task 1) + 결정적 칸(Task 2) → VisionQuantificationResult (D-12 HIGH-1).

    available 시 angleDeltas(features.frame_pair_angle_deltas, 같은 user/ref_frame_idx)/
    bodyRelativeNotches(body_relative_notches)/windowMedianAngleDeltas 를 채운다. 필수
    per-frame 입력(measurement/keypoint/baseline/angles) 결측 시 **crash·강등 없이**
    quantificationStatus="unavailable" + warnings 반환(D-11 MED-1). pre-coach
    VisionFaultContext 에는 geometry 가 들지 않는다 — apply 가 to_audit_dict(quantification=)
    로 주입(D-12 HIGH-1).
    """
    warnings: list[str] = []
    if measurement is None:
        return VisionQuantificationResult(
            quantificationStatus="unavailable",
            warnings=("measurement_context_missing",),
        )

    angle_deltas = None
    window_median = None
    if student_angles is not None and reference_angles is not None:
        try:
            from . import features

            angle_deltas = features.frame_pair_angle_deltas(
                student_angles, reference_angles,
                user_frame_idx=measurement.user_frame_idx,
                ref_frame_idx=measurement.ref_frame_idx,
            )
            window_median = features.window_median_angle_deltas(
                student_angles, reference_angles,
                user_frame_idx=measurement.user_frame_idx,
                ref_frame_idx=measurement.ref_frame_idx,
                window=window,
            )
        except (ValueError, IndexError):
            angle_deltas = None
            window_median = None
            warnings.append("angle_deltas_unavailable")
    else:
        warnings.append("angle_inputs_missing")

    notches = body_relative_notches(measurement)
    if notches is None:
        warnings.append("notches_unavailable")

    # available = 각도 또는 칸 중 최소 하나라도 산출됨.
    if angle_deltas or notches:
        return VisionQuantificationResult(
            quantificationStatus="available",
            angleDeltas=angle_deltas,
            bodyRelativeNotches=notches,
            windowMedianAngleDeltas=window_median,
            warnings=tuple(warnings),
        )
    return VisionQuantificationResult(
        quantificationStatus="unavailable",
        warnings=tuple(warnings) or ("quantification_inputs_missing",),
    )


def alignment_summary(alignment: dict | None) -> dict | None:
    """alignment 진단 dict 에서 관찰 키만 추린 요약 (24-06 §3 진단).

    관찰 전용 — 채점/tally 무관(alignment 는 메타데이터일 뿐, score 입력 아님). assess_
    alignment_confidence 반환 키(adoption/distance/visibility/localPathCount/refFramePresent)
    와 정합. 빈 dict/None 이면 None 을 반환해 audit 에 'alignment' 키를 미방출한다. 새
    import 없음 — 순수 dict-shaping 으로 analysis core 순수성(numpy 외 의존 0)을 보존한다.
    """
    if not alignment:
        return None
    return {
        "adoption": alignment.get("adoption"),
        "distance": alignment.get("distance"),
        "visibility": alignment.get("visibility"),
        "localPathCount": alignment.get("localPathCount"),
        "refFramePresent": alignment.get("refFramePresent"),
    }


@dataclass(frozen=True)
class VisionFaultContext:
    """pre-apply/pre-coach 비전 결함 컨텍스트 (D-12 HIGH-1 + D-13 MED-2).

    collection_status 는 pre-final enum 전용 — final applied/not_applicable 로 생성 불가.
    final-audit status / geometry payload 는 보유하지 않는다(to_audit_dict 가 인자로 받음).
    """

    collection_status: str
    verdict: object  # VisionVerdict | None
    supported_differences: list
    root_cause_hypotheses: list
    selected_frame_pairs: list
    alignment: dict
    telemetry: dict
    cap_would_apply: bool

    def __post_init__(self):
        if self.collection_status in _FINAL_AUDIT_STATUSES:
            raise ValueError(
                f"collection_status 는 pre-final enum 전용 — final "
                f"{self.collection_status!r} 로 생성 불가 (D-13 MED-2)"
            )
        if self.collection_status not in VISION_FAULT_COLLECTION_STATUSES:
            raise ValueError(
                f"unknown collection_status: {self.collection_status!r}"
            )

    @property
    def eligible_for_coach(self) -> bool:
        """coach root-cause 주입 게이트 = candidate_verdict AND cap_would_apply (D-13 MED-2)."""
        return self.collection_status == "candidate_verdict" and self.cap_would_apply is True

    # ── serializer 3종 ──

    def to_coach_context(self) -> dict:
        """pre-coach 직렬화 (ctx 단독) — root_cause/supported diffs/cap_would_apply."""
        return {
            "rootCauseHypotheses": [
                {
                    "text": rc.text,
                    "faultKey": rc.fault_key.to_dict(),
                    "supportCount": rc.support_count,
                }
                for rc in (self.root_cause_hypotheses or [])
            ],
            "supportedDifferences": [
                {k: v for k, v in (d or {}).items() if not str(k).startswith("_")}
                for d in (self.supported_differences or [])
            ],
            "capWouldApply": self.cap_would_apply,
            "collectionStatus": self.collection_status,
        }

    def to_trace_dict(self) -> dict:
        """eval trace 직렬화 (ctx 단독) — fault key 는 FaultKey.to_dict 어휘 (D-17 MED-3).

        WR-02 (25-02 review): fold 대표 `_faultKey` 만 방출하면 좌+우 혼재 그룹이
        side=unknown 단일 키로 붕괴돼 recall manifest 의 (left,arm)+(right,arm) 동시
        기대가 구조적으로 미충족된다. recall trace 는 표시/감점과 분리된 관측 채널이므로
        fold 전 멤버 원본 FaultKey(`_memberFaultKeys`)를 함께 방출한다 (대표 키도 유지
        — superset, dedup. manifest 자체는 무접촉).
        """
        fault_keys = []

        def _add(fk):
            if fk is None:
                return
            fk_dict = fk.to_dict() if hasattr(fk, "to_dict") else dict(fk)
            if fk_dict not in fault_keys:
                fault_keys.append(fk_dict)

        for d in (self.supported_differences or []):
            for mfk in (d or {}).get("_memberFaultKeys") or ():
                _add(mfk)
            _add((d or {}).get("_faultKey"))
        for rc in (self.root_cause_hypotheses or []):
            _add(rc.fault_key)
        return {
            "collectionStatus": self.collection_status,
            "selectorVersion": (self.alignment or {}).get("selector_version"),
            "alignmentAdoption": (self.alignment or {}).get("adoption"),
            "geminiCallCount": (self.telemetry or {}).get("completedCalls"),
            "samplingComplete": (self.telemetry or {}).get("samplingComplete"),
            "capWouldApply": self.cap_would_apply,
            "faultKeys": fault_keys,
        }

    def to_audit_dict(
        self, *, final_status: str, breakdown_final: int | None = None,
        quantification: "VisionQuantificationResult | None" = None,
    ) -> dict:
        """final-audit 직렬화 — apply 의 deduction tally 계산 후에만 (D-12 HIGH-1).

        Phase 24 (ND-01/ND-02): Gemini 은 점수를 절대 내지 않는다 — 측정대상/criterion
        만 짚는다; 밴드(cap)는 제거됐고 tally final(deduction_engine.tally 출력)만 audit
        에 방출한다. final_status 인자가 있어야 final-audit 필드(status/tallyFinal/
        quantificationStatus)를 방출한다. 인자 없이 호출하면 TypeError(fail-fast) —
        pre-apply 후보가 applied-looking audit 를 emit 하지 못한다.
        """
        if final_status not in _FINAL_AUDIT_STATUSES:
            raise ValueError(f"unknown final_status: {final_status!r}")
        audit: dict = {"status": final_status}
        # collect-side provenance 보존 (24-04) — final status(applied/not_applicable) 는
        # 채점 실행 여부지만, collectionStatus 는 그 채점이 어떤 수집 경로에서 왔는지를 남긴다.
        # low_alignment_confidence 가 measured-only 감점으로 applied 됐을 때 리포트가
        # "Gemini-located fault 없이 측정만으로 감점" 임을 투명하게 보여준다(must_have #3).
        audit["collectionStatus"] = self.collection_status
        # 24-06 §3 진단 — alignment 텔레메트리를 applied/not_applicable 양쪽에 방출한다
        # (분기 밖에 두는 이유 = collectionStatus 처럼 양쪽 노출). 관찰 메타데이터일 뿐,
        # tally/score 와 무관(밴드 제거 후 채점은 deduction_engine.tally 가 소유).
        _align = alignment_summary(self.alignment)
        if _align is not None:
            audit["alignment"] = _align
        if final_status == "applied":
            if breakdown_final is not None:
                audit["tallyFinal"] = breakdown_final
            verdict = self.verdict
            if verdict is not None:
                audit["severity"] = getattr(verdict, "severity", None)
                pf = getattr(verdict, "primary_fault", None)
                if pf:
                    audit["primaryFault"] = pf
            # root-cause 가설 (support-gated, D-13 MED-1). applied 면 tallyFinal 와
            # 함께 유지된다 — quantification unavailable 이어도 root-cause 는 살아남는다.
            root_causes = [
                {
                    "text": rc.text,
                    "faultKey": rc.fault_key.to_dict(),
                    "supportCount": rc.support_count,
                }
                for rc in (self.root_cause_hypotheses or [])
            ]
            if root_causes:
                audit["rootCauseHypotheses"] = root_causes
            # 정량화 (23-02 Task1/2/4) — apply 의 tally 계산 후 주입(D-12 HIGH-1).
            # quantificationStatus 는 applied audit 에 **필수**(D-11 MED-1). unavailable
            # 이면 angleDeltas/bodyRelativeNotches 부재 + status='applied'+tallyFinal 유지
            # (not_applicable 강등 금지). window median 은 still 정확 각도와 혼동 방지로
            # 별도 키(windowMedianAngleDeltas, D-10 HIGH-3).
            if quantification is not None:
                audit["quantificationStatus"] = quantification.quantificationStatus
                if quantification.quantificationStatus == "available":
                    if quantification.angleDeltas is not None:
                        audit["angleDeltas"] = quantification.angleDeltas
                    if quantification.bodyRelativeNotches is not None:
                        audit["bodyRelativeNotches"] = quantification.bodyRelativeNotches
                    if quantification.windowMedianAngleDeltas is not None:
                        audit["windowMedianAngleDeltas"] = quantification.windowMedianAngleDeltas
        return audit


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


# pointed(감점용) 매퍼 전용 — canonical keypoint_set → JOINT_KEYS base 이름.
# 명시 4종만 등재: line/torso/head_neck/grip 은 의도적으로 부재 (broad 확장 금지).
_POINTED_BASE_BY_KEYPOINT_SET = {
    "shoulder": "shoulder",
    "arm": "elbow",
    "leg": "knee",
    "hip": "hip",
}


def pointed_joints_from_supported_differences(supported) -> tuple[str, ...]:
    """supported_differences → 감점 window-측정 eligible 관절 (좁은 pointed 매퍼, 순수).

    감점용(pointed) 매퍼 — 표시용 fault_joints_from_differences 와 **분리**(25-RESEARCH
    함정 ⑥): 표시용의 broad(trunk/양다리) 확장을 감점 게이트에 쓰면 line fault 하나가
    양어깨+양엉덩이 4관절을 "짚은" 것으로 만들어 vision 게이트가 무력화된다. 여기서는
    명시 keypoint_set 4종(shoulder/arm/leg/hip)만 매핑하고 line/torso/head_neck/grip
    은 방출 0 (해당 관절은 기존 full-path DTW median seed 유지).

    규칙 (25-01 Task 1, OD-1):
      · record 의 canonical `_faultKey`(FaultKey) 만 소비 — body_part 자유텍스트
        재파싱 금지 (T-25-01: canonical enum 이 단일 owner). dict 이면
        FaultKey.from_dict 시도, enum 밖/형상불량은 graceful skip.
      · side "left"/"right" → 해당 측만. "unknown" → 양측 eligible — 판정은
        측정+tol 20° 게이트가 하며 clean 쪽은 편차<tol 이라 자연히 감점 0
        (fail-closed 버리기 금지 = motion-routing-generalize 원칙).
      · 출력 = JOINT_KEYS 순서 안정 tuple, 중복 제거, JOINT_KEYS 외 방출 0.
      · 동작명/kip-up 특정 분기 0 (일반화 — locked).
    """
    from .skeleton import JOINT_KEYS

    eligible: set[str] = set()
    for rec in supported or ():
        if not isinstance(rec, dict):
            continue
        fk = rec.get("_faultKey")
        if isinstance(fk, dict):
            try:
                fk = FaultKey.from_dict(fk)
            except (ValueError, TypeError):
                continue  # enum 밖 값 — graceful skip (T-25-01)
        if not isinstance(fk, FaultKey):
            continue
        base = _POINTED_BASE_BY_KEYPOINT_SET.get(fk.keypoint_set)
        if base is None:
            continue  # line/torso/head_neck/grip — broad 확장 금지 (함정 ⑥)
        sides = (fk.side,) if fk.side in ("left", "right") else ("left", "right")
        for s in sides:
            jk = f"{s}_{base}"
            if jk in JOINT_KEYS:  # spurious 키 방출 0
                eligible.add(jk)
    return tuple(jk for jk in JOINT_KEYS if jk in eligible)


def fault_joint_deficits_from_differences(differences) -> dict[str, float]:
    """Gemini differences → {keypoint: approx_angle_deviation_deg} (시각 추정 deficit).

    fault-zoom 의 deficit 숫자 source. kismam 각도 delta 는 veto 가 발동한 결함을
    구조적으로 못 잡으므로(그래서 veto 발동) 작게 나온다 → Gemini 의 visual 추정을
    쓴다. 한 body_part 가 여러 keypoint 로 확장되면 같은 deviation 을 부여하고,
    여러 difference 가 같은 keypoint 를 가리키면 **최대** deviation 을 남긴다. 0/미상은
    제외(숫자 안 그림). 순수.

    25-04 #3(a): 명시 각도쌍(student/reference)이 있으면 산술 편차를 우선한다 —
    보고서 deficit 숫자와 감점 경로(deduction_engine)가 같은 측정을 읽게(출처 단일).
    """
    out: dict[str, float] = {}
    for d in differences or ():
        dev = explicit_measured_deviation_deg(d)
        if dev is None:
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
