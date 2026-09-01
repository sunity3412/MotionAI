"""Firestore Admin 클라이언트 (백엔드 전용 — 보안 규칙 우회).

용도:
  - pipeline: users/{uid}/analyses/{id} 의 status/result/error 갱신
  - reference-api: reference 컬렉션 목록 조회

앱은 절대 Admin 권한을 갖지 않는다. 서비스 계정은 auth.py 와 동일하게
Parameter Store(FIREBASE_SA_PARAM)에서 로드 — 코드/.env 하드코딩 금지.
"""

from __future__ import annotations

import math
import time

from . import auth as _auth
from . import models

_client = None


def _db():
    """firestore 클라이언트 1회 생성 (firebase-admin 초기화 재사용)."""
    global _client
    if _client is not None:
        return _client
    _auth._ensure_firebase()  # firebase_admin app 보장
    from firebase_admin import firestore

    _client = firestore.client()
    return _client


def _doc(path: str):
    return _db().document(path)


def update_analysis_status(uid: str, analysis_id: str, status: str) -> None:
    """진행 단계 갱신. status 는 models.PIPELINE_SEQUENCE 중 하나."""
    _doc(models.analysis_doc_path(uid, analysis_id)).set(
        {"status": status, "updatedAt": int(time.time() * 1000)},
        merge=True,
    )


def _validate_flat_dict_no_nested_array(payload: dict, *, path: str = "") -> None:
    """W5 (2026-06-08, Plan 06-02). Firestore nested-array 금지 보장.

    [[firestore-nested-array-flat]] 정합 — BodyComparisonReport.warnings (list[str]) +
    BodyComparisonReport.findings (list[dict-of-scalars-only]) 허용. list[list] /
    list[dict-with-nested-list] reject. store_gemini_cache:186-199 의 기존 검증을
    일반화. 위반 시 TypeError + path 정보. caller (pipeline) 가 catch →
    fail_analysis(server_error) 진입.

    명세:
      - dict 입력 → 각 (key, value) 순회
      - value 가 scalar (str, int, float, bool, None) → PASS
      - value 가 dict → 재귀 (top-level dict 안에서는 list[scalar] 도 허용)
      - value 가 list →
        * list 원소가 scalar → PASS
        * list 원소가 dict → 각 원소는 _validate_dict_only_scalars (list / nested 금지)
        * list 원소가 list → TypeError raise
        * 빈 list / None → PASS
    """
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise TypeError(
            f"_validate_flat_dict_no_nested_array: dict 입력만 허용. "
            f"path={path!r} got {type(payload).__name__}"
        )
    for key, value in payload.items():
        sub_path = f"{path}.{key}" if path else key
        if value is None or isinstance(value, (str, int, float, bool)):
            continue
        if isinstance(value, dict):
            _validate_flat_dict_no_nested_array(value, path=sub_path)
            continue
        if isinstance(value, list):
            for i, item in enumerate(value):
                item_path = f"{sub_path}[{i}]"
                if item is None or isinstance(item, (str, int, float, bool)):
                    continue
                if isinstance(item, list):
                    raise TypeError(
                        f"{item_path} contains nested list "
                        f"(firestore-nested-array-flat): got nested list"
                    )
                if isinstance(item, dict):
                    _validate_dict_only_scalars(item, path=item_path)
                    continue
                # 기타 타입 (tuple 등) — Firestore 가 직렬화하지 못함.
                raise TypeError(
                    f"{item_path} must be scalar / dict / null "
                    f"(firestore-nested-array-flat): got {type(item).__name__}"
                )
            continue
        # scalar / dict / list / None 외 — Firestore 직렬화 불가.
        raise TypeError(
            f"{sub_path} must be flat (firestore-nested-array-flat): "
            f"got nested {type(value).__name__}"
        )


def _validate_dict_only_scalars(d: dict, *, path: str) -> None:
    """list[dict] 의 dict 원소 안에서는 nested list / nested dict 금지.

    [[firestore-nested-array-flat]] 정합 — findings entry 의 dict 는 flat scalar 만.
    store_gemini_cache:186-199 의 moments[i] 검증 패턴 재사용.

    Plan 08-03 (REVIEWS Cycle 2 §3 NEW HIGH #3) — 본 validator 본체 변경 영구 0.
    project-wide [[firestore-nested-array-flat]] 영구 보존. body_comparison_report 등
    다른 path 박제 strict 유지. force_signals_report 전용 relaxation 은 신설
    scoped validator `_validate_force_signals_report` 에서만 활성.
    """
    if not isinstance(d, dict):
        raise TypeError(
            f"{path} must be flat dict (firestore-nested-array-flat): "
            f"got {type(d).__name__}"
        )
    for k, v in d.items():
        sub_path = f"{path}.{k}"
        if v is None or isinstance(v, (str, int, float, bool)):
            continue
        # findings entry 의 dict 안에서는 list / dict 도 모두 금지.
        raise TypeError(
            f"{sub_path} must be scalar (firestore-nested-array-flat — "
            f"list-of-dict entry 안에서는 nested 금지): got {type(v).__name__}"
        )


# ── Phase 11 (Plan 11-01, iter-2 BLOCKER-1) — CoachCommentHook 전용 strict validator ──
#
# generic `_validate_flat_dict_no_nested_array` 는 list[dict] (scalar-only) 를 허용
# (line 88-90 의 _validate_dict_only_scalars 라우팅) — hook 의 list[str] 계약에 미달.
# 본 전용 validator 가 명시 화이트리스트로 list[str]-only 를 강제한다. force scoped
# 브랜치 + body precheck 둘 다 본 함수를 호출 (generic 위임 금지).

# scalar-or-null hook 키 (camelCase — Firestore 직렬화 후 검증).
_COACH_HOOK_SCALAR_KEYS: frozenset[str] = frozenset(
    {"autoFindingsSummary", "coachComment", "reviewedBy", "sourceReport"}
)
# list[str] hook 키.
_COACH_HOOK_LIST_KEYS: frozenset[str] = frozenset(
    {"openQuestionsForCoach", "suggestedCues"}
)


def _validate_coach_comment_hook(payload, *, path: str) -> None:
    """coachCommentHook 전용 strict 화이트리스트 (iter-2 BLOCKER-1).

    generic validator 위임 금지 — list[dict]/list[list]/tuple/unknown-key 를 명시
    reject. force scoped 브랜치 + body precheck 가 공통 호출.

    명세:
      · payload None → return (옵셔널 필드).
      · payload dict 아님 → ValueError.
      · scalar 키 (autoFindingsSummary/coachComment/reviewedBy/sourceReport): str/None.
      · list 키 (openQuestionsForCoach/suggestedCues): list, 각 원소 non-empty str.
      · 화이트리스트 외 key → ValueError (unknown hook key reject).

    Raises:
        ValueError: 계약 위반 (list[dict]/nested/unknown-key/non-str scalar 등).
    """
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(
            f"{path} coachCommentHook must be dict | null, "
            f"got {type(payload).__name__}"
        )
    for key, value in payload.items():
        sub = f"{path}.{key}"
        if key in _COACH_HOOK_SCALAR_KEYS:
            if value is not None and not isinstance(value, str):
                raise ValueError(
                    f"{sub} must be str | null (coachCommentHook scalar), "
                    f"got {type(value).__name__}"
                )
            continue
        if key in _COACH_HOOK_LIST_KEYS:
            if not isinstance(value, list):
                raise ValueError(
                    f"{sub} must be list[str] (coachCommentHook), "
                    f"got {type(value).__name__}"
                )
            for i, item in enumerate(value):
                # list[dict] / list[list] / tuple 명시 reject (BLOCKER-1 핵심).
                if isinstance(item, (list, dict, tuple)):
                    raise ValueError(
                        f"{sub}[{i}] nested {type(item).__name__} reject "
                        f"(coachCommentHook list[str] only — iter-2 BLOCKER-1)"
                    )
                if not isinstance(item, str) or not item:
                    raise ValueError(
                        f"{sub}[{i}] must be non-empty str, "
                        f"got {type(item).__name__}={item!r}"
                    )
            continue
        # 화이트리스트 외 key → reject (unknown hook key).
        raise ValueError(
            f"{sub} unknown coachCommentHook key — 허용 키: "
            f"{sorted(_COACH_HOOK_SCALAR_KEYS | _COACH_HOOK_LIST_KEYS)}"
        )


# ── Plan 08-03 (REVIEWS Cycle 2 §3 NEW HIGH #3) — force_signals 전용 scoped validator ──
#
# `_validate_dict_only_scalars` 본체 변경 영구 0 — project-wide
# [[firestore-nested-array-flat]] 보존. 본 scoped validator 만 `forceSignalsReport`
# 안 metric dict 의 list[str] (`warnings`, `unstableBodyParts`) 박제 허용.
# 다른 path (bodyComparisonReport 등) 박제 strict 유지.

# `forceSignalsReport` 안에서만 list[scalar] inside list[dict] 박제 허용되는 필드.
# 본 화이트리스트가 아닌 list[scalar] 박제 시 reject.
_FORCE_SIGNALS_SCALAR_LIST_KEYS_IN_METRIC: frozenset[str] = frozenset(
    {
        "warnings",  # 모든 metric dict 의 list[str] warning 박제
        "unstableBodyParts",  # StabilityMetric.unstable_body_parts → camelCase
    }
)


def _validate_force_signals_report(
    payload: dict, *, path: str = "forceSignalsReport"
) -> None:
    """force_signals_report 전용 scoped validator — Plan 08-03 (REVIEWS Cycle 2 §3 NEW HIGH #3).

    `_validate_dict_only_scalars` 본체 변경 영구 0 박제 정합 — 본 validator 만
    forceSignalsReport 안 metric dict 의 list[str] (warnings, unstableBodyParts) 박제
    허용. 다른 list[scalar] 박제 시 ValueError (Firestore nested-array 보호 유지).

    명세:
      · top-level forceSignalsReport.warnings: list[str] PASS
      · phaseBoundaries / axisMetrics / stabilityMetrics / contactMetrics: list[dict] 박제
      · 각 metric dict 안:
        - scalar (str/int/float/bool/None) → PASS
        - list[str] 박제이고 키가 화이트리스트 (warnings, unstableBodyParts) → PASS
        - list[scalar] 박제이고 키가 화이트리스트 미포함 → reject
        - list[list] / list[dict] / nested dict → reject

    위반 시 ValueError + path 정보 (caller 가 catch → fail_analysis 진입).
    """
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(
            f"_validate_force_signals_report: dict 입력만 허용. "
            f"path={path!r} got {type(payload).__name__}"
        )
    for key, value in payload.items():
        sub_path = f"{path}.{key}"
        if value is None or isinstance(value, (str, int, float, bool)):
            continue
        if isinstance(value, dict):
            # nested dict — top-level forceSignalsReport 안에는 dict scalar 박제 X
            # (모든 metric 은 list[dict] 박제). 보수적 reject.
            raise ValueError(
                f"{sub_path} unexpected nested dict at force_signals top-level "
                f"(forceSignalsReport schema: scalar / list[dict] / list[str] only)"
            )
        if isinstance(value, list):
            # top-level list — top-level forceSignalsReport.warnings 박제 list[str] 박제 허용.
            if key == "warnings":
                for i, item in enumerate(value):
                    if not isinstance(item, (str, int, float, bool)) and item is not None:
                        raise ValueError(
                            f"{sub_path}[{i}] warnings list 원소는 scalar 박제 강제: "
                            f"got {type(item).__name__}"
                        )
                continue
            # 그 외 top-level list = metric list (phaseBoundaries / axisMetrics /
            # stabilityMetrics / contactMetrics). list[dict] 박제 강제.
            for i, item in enumerate(value):
                item_path = f"{sub_path}[{i}]"
                if not isinstance(item, dict):
                    raise ValueError(
                        f"{item_path} metric list 원소는 dict 박제 강제: "
                        f"got {type(item).__name__}"
                    )
                _validate_metric_dict_with_scalar_lists(item, path=item_path)
            continue
        raise ValueError(
            f"{sub_path} unexpected type at force_signals top-level: "
            f"got {type(value).__name__}"
        )


def _validate_safety_flags(flags, *, path: str = "safetyFlags") -> None:
    """SafetyFlag list[dict] 전용 scoped validator — Plan 10-02 (T-10-01 방어).

    `result['safetyFlags']` 의 단일 persistence path 에서만 호출 (complete_analysis 에
    신규 kwarg 추가 X — 플래그는 result 안으로 흐른다). force_signals 와 달리 SafetyFlag
    의 모든 필드는 scalar (str/int/float/bool/None) — 화이트리스트 list 필드 없음
    (stricter). 각 flag dict 를 `_validate_dict_only_scalars` 로 검증해 nested list/dict
    (예: causes[]) 를 reject 한다. [[firestore-nested-array-flat]] 보존.
    """
    if flags is None:
        return
    if not isinstance(flags, list):
        raise TypeError(
            f"{path} must be list[dict] (firestore-nested-array-flat): "
            f"got {type(flags).__name__}"
        )
    for i, flag in enumerate(flags):
        _validate_dict_only_scalars(flag, path=f"{path}[{i}]")


def _validate_motion_alignment(
    payload, *, path: str = "motionAlignment"
) -> None:
    """motionAlignment scoped validator — Phase 28 (ALGN-01, T-28-05 + MEDIUM-3).

    `result['motionAlignment']` 단일 persistence path 전용 — complete_analysis 에 신규
    kwarg 없음 (safetyFlags 선례, "result 안으로 흐른다"). None/부재 graceful(legacy doc).
    검증:
      · dict 강제, 키는 `models.MOTION_ALIGNMENT_KEYS` 화이트리스트(reason optional).
      · `anchors` = flat list[숫자 scalar] — nested list/dict → TypeError
        ([[firestore-nested-array-flat]]). 짝수 길이 + 전수 finite(NaN/inf 금지) +
        `len <= models.MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS` (40k index-entry 방어, T-28-05,
        [[firestore-index-entry-limit]]).
      · u strictly increasing, r non-decreasing (단조성).
      · `tier` ∈ MOTION_ALIGNMENT_TIERS, `source` ∈ MOTION_ALIGNMENT_SOURCES.
      · `anchorCount` == len(anchors)//2.
    tier↔anchors 역불변식 (리뷰 MEDIUM-3): `tier=='disabled'` 일 때만 `anchors==[]` 허용
    (degenerate 방출 형상, 28-02 W3). `tier in ('warped','trim_only')` → `len(anchors)>=4`
    AND `anchorCount>=2` 강제 — "warped 인데 anchors 빈" 모순 상태를 저장 전에 거부해 앱
    normalizer(`alignmentWarp.normalizeMotionAlignment`, 같은 규칙으로 null 폴백)와 대칭
    유지 + malformed Firestore 상태 진단 가능. 위반 시 TypeError/ValueError + path
    (caller 가 catch → fail_analysis). generic `_validate_dict_only_scalars` 본체 무변경.
    """
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(
            f"{path} must be dict (motionAlignment): got {type(payload).__name__}"
        )
    # 키 화이트리스트 (reason optional — MOTION_ALIGNMENT_KEYS 에 포함).
    extra = set(payload) - set(models.MOTION_ALIGNMENT_KEYS)
    if extra:
        raise ValueError(f"{path}: 화이트리스트 밖 키 {sorted(extra)}")

    # tier / source / version / distance scalar 검증.
    tier = payload.get("tier")
    if tier not in models.MOTION_ALIGNMENT_TIERS:
        raise ValueError(f"{path}.tier 미등재값: {tier!r}")
    source = payload.get("source")
    if source not in models.MOTION_ALIGNMENT_SOURCES:
        raise ValueError(f"{path}.source 미등재값: {source!r}")
    if not isinstance(payload.get("version"), str):
        raise ValueError(f"{path}.version 은 str 필수")
    distance = payload.get("distance")
    if isinstance(distance, bool) or not isinstance(distance, (int, float)):
        raise ValueError(f"{path}.distance 는 숫자 scalar 필수: {distance!r}")
    if not _math_kr.isfinite(distance):
        raise ValueError(f"{path}.distance 는 finite 여야 함")

    # anchors — flat list[숫자 scalar], nested → TypeError (firestore-nested-array-flat).
    anchors = payload.get("anchors")
    if not isinstance(anchors, list):
        raise TypeError(
            f"{path}.anchors must be flat list: got {type(anchors).__name__}"
        )
    for i, x in enumerate(anchors):
        if isinstance(x, (list, dict)):
            raise TypeError(
                f"{path}.anchors[{i}] nested (firestore-nested-array-flat): "
                f"{type(x).__name__}"
            )
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise ValueError(f"{path}.anchors[{i}] 는 숫자 scalar 필수: {x!r}")
        if not _math_kr.isfinite(x):
            raise ValueError(f"{path}.anchors[{i}] 는 finite 여야 함 (NaN/inf 금지)")
    if len(anchors) > models.MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS:
        raise ValueError(
            f"{path}.anchors 길이 {len(anchors)} > 상한 "
            f"{models.MOTION_ALIGNMENT_MAX_ANCHOR_FLOATS} (40k index-entry 방어)"
        )
    if len(anchors) % 2 != 0:
        raise ValueError(f"{path}.anchors 홀수 길이 {len(anchors)} — 쌍 미형성")

    anchor_count = payload.get("anchorCount")
    if anchor_count != len(anchors) // 2:
        raise ValueError(
            f"{path}.anchorCount {anchor_count!r} != len(anchors)//2 "
            f"{len(anchors) // 2}"
        )

    # tier↔anchors 역불변식 (MEDIUM-3) — disabled 만 빈/부족 anchors 허용.
    if tier != "disabled" and (len(anchors) < 4 or (anchor_count or 0) < 2):
        raise ValueError(
            f"{path}.tier={tier!r} 는 최소 2쌍(4 float) 필수 — "
            f"빈/부족 anchors 모순 데이터 (MEDIUM-3)"
        )

    # 단조성 — u strictly increasing, r non-decreasing.
    us = anchors[0::2]
    rs = anchors[1::2]
    for k in range(len(us) - 1):
        if not (us[k] < us[k + 1]):
            raise ValueError(
                f"{path}.anchors u 비단조(strictly increasing 위반) @pair{k}"
            )
        if not (rs[k] <= rs[k + 1]):
            raise ValueError(
                f"{path}.anchors r 비단조(non-decreasing 위반) @pair{k}"
            )


# ── Phase 32 (Plan 32-06) — 미션 루프 + 번역 레이어 scoped validator 4종 ──
#
# D-19/D-26/D-27/D-14 + D-28/D-29 + 리뷰 blocker 1·5. motionAlignment 선례 뼈대
# 복제 — result 안 단일 persistence path 전용, complete_analysis 신규 kwarg 0
# ("result 안으로 흐른다", SP-1). None/부재 graceful(legacy doc — 방출은 32-09
# 부터). generic `_validate_dict_only_scalars` 본체 변경 영구 0. records 확장 키
# (recordId/3단 문구/tolerance)는 flat scalar 라 기존 record 검증 경로
# (_validate_deduction_breakdown → _validate_dict_only_scalars)를 자동 통과 —
# 별도 validator 불필요 (계약은 contract.md §12.3).
# 3-way lockstep: models.py MISSION_KEYS 블록 + analysis.ts + contract.md §12.

# 상한 상수 — 리뷰 반영 (T-32-12 Tampering mitigate).
_MISSION_STREAK_MIN = 1
_MAX_PRAISE_HEADLINE_CHARS = 200
_MAX_COACH_QUESTIONS = 10
_MAX_COACH_QUESTION_TEXT_CHARS = 200

# 백엔드 방출 가능 coach question source — 'user' 는 클라이언트 로컬 전용
# (사용자 담기, 백엔드 방출·validator 에 도달하지 않음 — contract.md §12.5).
# 백엔드 코드가 'user' 를 방출하면 계약 위반이므로 여기서 거부한다.
_BACKEND_COACH_QUESTION_SOURCES: tuple[str, ...] = tuple(
    s for s in models.COACH_QUESTION_SOURCES if s != "user"
)


def _require_finite_number(value, *, path: str, allow_none: bool = False):  # noqa: ANN001
    """finite 숫자 강제 (bool 명시 거부). allow_none 시 None graceful 통과."""
    if value is None and allow_none:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} 는 숫자 scalar 필수: {value!r}")
    if not _math_kr.isfinite(value):
        raise ValueError(f"{path} 는 finite 여야 함 (NaN/inf 금지)")


def _require_str_or_none(value, *, path: str) -> None:  # noqa: ANN001
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{path} 는 str|None 필수: {type(value).__name__}")


def _validate_mission(payload, *, path: str = "mission") -> None:  # noqa: ANN001
    """mission scoped validator — Phase 32 (Plan 32-06, T-32-12).

    `result['mission']` 단일 persistence path 전용. 검증:
      · dict 강제, 키는 models.MISSION_KEYS 화이트리스트.
      · faultKey/criterion 비어있지 않은 str, ruleId/recordId/motionId/unit str|None.
      · selectedBy ∈ MISSION_SELECTED_BY, escalation ∈ MISSION_ESCALATIONS.
      · streak int 1..MISSION_STREAK_MAX(99) — mission._STREAK_CAP lockstep.
      · baselinePoints finite ≥ 0, baselineDeviation/targetValue finite|None.
      · isSafety bool. D-14 정합(isSafety→streak 1·escalation 'none')은 산출
        순수 함수(analysis/mission.py)가 소유 — 저장층은 형식·범위만 강제.
    위반 시 ValueError + path (caller 가 catch → fail_analysis).
    """
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(
            f"{path} must be dict (mission): got {type(payload).__name__}"
        )
    extra = set(payload) - set(models.MISSION_KEYS)
    if extra:
        raise ValueError(f"{path}: 화이트리스트 밖 키 {sorted(extra)}")
    for key in ("faultKey", "criterion"):
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{path}.{key} 는 비어있지 않은 str 필수: {value!r}")
    for key in ("ruleId", "recordId", "motionId", "unit"):
        _require_str_or_none(payload.get(key), path=f"{path}.{key}")
    selected_by = payload.get("selectedBy")
    if selected_by not in models.MISSION_SELECTED_BY:
        raise ValueError(f"{path}.selectedBy 미등재값: {selected_by!r}")
    escalation = payload.get("escalation")
    if escalation not in models.MISSION_ESCALATIONS:
        raise ValueError(f"{path}.escalation 미등재값: {escalation!r}")
    streak = payload.get("streak")
    if isinstance(streak, bool) or not isinstance(streak, int):
        raise ValueError(f"{path}.streak 는 int 필수: {streak!r}")
    if not (_MISSION_STREAK_MIN <= streak <= models.MISSION_STREAK_MAX):
        raise ValueError(
            f"{path}.streak 범위 위반 ({_MISSION_STREAK_MIN}.."
            f"{models.MISSION_STREAK_MAX}): {streak}"
        )
    if not isinstance(payload.get("isSafety"), bool):
        raise ValueError(f"{path}.isSafety 는 bool 필수")
    baseline_points = payload.get("baselinePoints")
    _require_finite_number(baseline_points, path=f"{path}.baselinePoints")
    if baseline_points < 0:
        raise ValueError(f"{path}.baselinePoints 는 ≥0 필수: {baseline_points!r}")
    _require_finite_number(
        payload.get("baselineDeviation"),
        path=f"{path}.baselineDeviation",
        allow_none=True,
    )
    _require_finite_number(
        payload.get("targetValue"), path=f"{path}.targetValue", allow_none=True
    )


def _validate_mission_outcome(
    payload, *, path: str = "missionOutcome"
) -> None:  # noqa: ANN001
    """missionOutcome scoped validator — _validate_mission 동형 (수치 finite).

    `result['missionOutcome']` 단일 persistence path 전용 (mode3 전용 산출물 —
    mode1/prev 부재는 키 생략이라 None graceful). 수치·bool·키만 — 사람 문장
    필드는 화이트리스트에 없다 (계산/카피 책임 분리).
    """
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(
            f"{path} must be dict (missionOutcome): got {type(payload).__name__}"
        )
    extra = set(payload) - set(models.MISSION_OUTCOME_KEYS)
    if extra:
        raise ValueError(f"{path}: 화이트리스트 밖 키 {sorted(extra)}")
    if not isinstance(payload.get("improved"), bool):
        raise ValueError(f"{path}.improved 는 bool 필수")
    for key in ("faultKey", "criterion"):
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{path}.{key} 는 비어있지 않은 str 필수: {value!r}")
    for key in ("baselinePoints", "currentPoints", "deltaPoints"):
        _require_finite_number(payload.get(key), path=f"{path}.{key}")
    for key in ("baselineDeviation", "currentDeviation", "deltaDeviation"):
        _require_finite_number(
            payload.get(key), path=f"{path}.{key}", allow_none=True
        )


def _validate_summary_praise(
    payload, *, path: str = "summaryPraise"
) -> None:  # noqa: ANN001
    """summaryPraise scoped validator — 잘한 점 단일 원천 (리뷰 blocker 5).

    headline 은 사람 말 상한 200자 — D-09 수치 invariant 자체는 phrasebook 조립
    (32-09)의 금지어 게이트가 소유하고, 저장층은 형식·상한만 강제한다.
    """
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(
            f"{path} must be dict (summaryPraise): got {type(payload).__name__}"
        )
    extra = set(payload) - set(models.SUMMARY_PRAISE_KEYS)
    if extra:
        raise ValueError(f"{path}: 화이트리스트 밖 키 {sorted(extra)}")
    source = payload.get("source")
    if source not in models.SUMMARY_PRAISE_SOURCES:
        raise ValueError(f"{path}.source 미등재값: {source!r}")
    headline = payload.get("headline")
    if not isinstance(headline, str) or not headline.strip():
        raise ValueError(f"{path}.headline 는 비어있지 않은 str 필수")
    if len(headline) > _MAX_PRAISE_HEADLINE_CHARS:
        raise ValueError(
            f"{path}.headline 길이 {len(headline)} > 상한 "
            f"{_MAX_PRAISE_HEADLINE_CHARS}"
        )
    _require_finite_number(
        payload.get("evidenceValue"), path=f"{path}.evidenceValue", allow_none=True
    )
    _require_str_or_none(payload.get("evidenceUnit"), path=f"{path}.evidenceUnit")


def _validate_coach_questions(
    payload, *, path: str = "coachQuestions"
) -> None:  # noqa: ANN001
    """coachQuestions scoped validator — _validate_safety_flags 형태 (D-28/D-29).

    각 항목 scalar-only dict (`_validate_dict_only_scalars` 라우팅 — generic
    본체 무변경) + source 백엔드 enum + text 1..200자 + recordId str|None.
    항목 수 ≤ 10 (리뷰 상한). **source='user' 거부** — 클라이언트 로컬 전용
    ('강사님께 물어보기' 담기)이라 백엔드 방출에 나타나면 계약 위반이다
    (contract.md §12.5).
    """
    if payload is None:
        return
    if not isinstance(payload, list):
        raise TypeError(
            f"{path} must be list[dict] (firestore-nested-array-flat): "
            f"got {type(payload).__name__}"
        )
    if len(payload) > _MAX_COACH_QUESTIONS:
        raise ValueError(
            f"{path} 항목 수 {len(payload)} > 상한 {_MAX_COACH_QUESTIONS}"
        )
    for i, item in enumerate(payload):
        item_path = f"{path}[{i}]"
        _validate_dict_only_scalars(item, path=item_path)
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{item_path}.text 는 비어있지 않은 str 필수")
        if len(text) > _MAX_COACH_QUESTION_TEXT_CHARS:
            raise ValueError(
                f"{item_path}.text 길이 {len(text)} > 상한 "
                f"{_MAX_COACH_QUESTION_TEXT_CHARS}"
            )
        source = item.get("source")
        if source not in _BACKEND_COACH_QUESTION_SOURCES:
            raise ValueError(
                f"{item_path}.source 미등재값(백엔드 방출 불가 'user' 포함 거부): "
                f"{source!r}"
            )
        _require_str_or_none(item.get("recordId"), path=f"{item_path}.recordId")


def _validate_metric_dict_with_scalar_lists(d: dict, *, path: str) -> None:
    """metric dict 안 검증 — scalar / list[str] (화이트리스트 한정) 박제 허용.

    list[list] / list[dict] / nested dict 박제 영구 reject ([[firestore-nested-array-flat]]
    project-wide 보존 정합).
    """
    if not isinstance(d, dict):
        raise ValueError(
            f"{path} must be dict, got {type(d).__name__}"
        )
    for k, v in d.items():
        sub_path = f"{path}.{k}"
        if v is None or isinstance(v, (str, int, float, bool)):
            continue
        if isinstance(v, dict):
            # metric dict 안에는 nested dict 박제 X.
            raise ValueError(
                f"{sub_path} nested dict in metric entry not allowed "
                f"(firestore-nested-array-flat — metric dict 안에는 scalar / "
                f"list[scalar] 박제만 허용)"
            )
        if isinstance(v, list):
            # 화이트리스트 키만 list[scalar] 박제 허용.
            if k not in _FORCE_SIGNALS_SCALAR_LIST_KEYS_IN_METRIC:
                raise ValueError(
                    f"{sub_path} list field not in force_signals whitelist "
                    f"({sorted(_FORCE_SIGNALS_SCALAR_LIST_KEYS_IN_METRIC)}); "
                    f"non-whitelist list in metric dict 영구 reject "
                    f"(firestore-nested-array-flat 보존)"
                )
            # 화이트리스트 list 의 원소는 scalar 박제 강제 — list[list] / list[dict] reject.
            for i, item in enumerate(v):
                if isinstance(item, (list, dict)):
                    raise ValueError(
                        f"{sub_path}[{i}] nested {type(item).__name__} in "
                        f"force_signals list field reject "
                        f"(firestore-nested-array-flat 보존)"
                    )
                if item is not None and not isinstance(item, (str, int, float, bool)):
                    raise ValueError(
                        f"{sub_path}[{i}] must be scalar / None: "
                        f"got {type(item).__name__}"
                    )
            continue
        raise ValueError(
            f"{sub_path} unexpected type in metric dict: "
            f"got {type(v).__name__}"
        )


# ── Plan 09-01 (2026-06-10, Phase 9) — force_pattern_inference scoped validator ──
#
# D-09-U5 + RESEARCH Pattern 5. `_validate_force_signals_report` 패턴 직접 mirror —
# nested-array 금지 + 화이트리스트 list field 만 허용. forcePatternInference 안에서만
# list[dict-of-scalars] (findings) + list[str] (warnings) 박제 가능.
#
# scope: 본 validator 만 `result.forcePatternInference` path 박제 호출. 다른 path
# (body_comparison_report 등) 박제 strict 유지 ([[firestore-nested-array-flat]]
# project-wide 보존).

# finding entry 안 list 허용 키 화이트리스트 (camelCase — validator 는
# _dataclass_to_camel_case_dict 호출 후 dict 입력 받음).
_FORCE_PATTERN_FINDING_SCALAR_LIST_KEYS: frozenset[str] = frozenset({"warnings"})

# R2 (Codex iter-5) — finding dict 전체 key whitelist (camelCase only).
# schema lockstep 강제: 미정의 key (예: 'unexpectedScalar') reject.
_FORCE_PATTERN_FINDING_KEYS: frozenset[str] = frozenset(
    {
        "pattern",
        "phase",
        "sourceSignal",
        "reason",
        "interpretation",
        "confidence",
        "jointHint",
        "warnings",
    }
)


def _validate_force_pattern_finding_dict(d: dict, *, path: str) -> None:
    """Phase 9 finding entry dict 검증 — 8 필드 strict whitelist (camelCase).

    D-09-U5 + RESEARCH Pattern 5 — nested dict/list reject + warnings strict
    list[str] only.
    """
    if not isinstance(d, dict):
        raise ValueError(
            f"{path} must be dict, got {type(d).__name__}"
        )
    for k, v in d.items():
        sub = f"{path}.{k}"
        # R2 (Codex iter-5) — schema lockstep 강제, 미정의 key reject.
        if k not in _FORCE_PATTERN_FINDING_KEYS:
            raise ValueError(
                f"{sub} key not in force_pattern_finding whitelist "
                f"({sorted(_FORCE_PATTERN_FINDING_KEYS)}); reject"
            )
        if v is None or isinstance(v, (str, int, float, bool)):
            continue
        if isinstance(v, dict):
            raise ValueError(
                f"{sub} nested dict in finding entry not allowed "
                f"(forcePatternInference schema: scalar fields + 'warnings' list[str] only)"
            )
        if isinstance(v, list):
            if k not in _FORCE_PATTERN_FINDING_SCALAR_LIST_KEYS:
                raise ValueError(
                    f"{sub} list field not in force_pattern_finding whitelist "
                    f"({sorted(_FORCE_PATTERN_FINDING_SCALAR_LIST_KEYS)}); reject"
                )
            # R2 (Codex iter-2) — `warnings` 는 contract 상 list[str] only.
            # Phase 8 의 permissive scalar 허용을 mirror 하지 X — Phase 9 는 더 strict.
            for i, item in enumerate(v):
                if isinstance(item, (list, dict)):
                    raise ValueError(
                        f"{sub}[{i}] nested {type(item).__name__} reject "
                        f"(firestore-nested-array-flat 보존)"
                    )
                if not isinstance(item, str) or not item:
                    raise ValueError(
                        f"{sub}[{i}] must be non-empty str warning code "
                        f"(contract list[str]), got {type(item).__name__}={item!r}"
                    )
            continue
        raise ValueError(
            f"{sub} unexpected type at force_pattern_finding: {type(v).__name__}"
        )


def _validate_force_pattern_inference(
    payload: dict, *, path: str = "forcePatternInference"
) -> None:
    """force_pattern_inference top-level scoped validator (D-09-U5).

    Plan 09-01 (Phase 9) — `_validate_force_signals_report` 패턴 직접 mirror.
    `_validate_dict_only_scalars` 본체 변경 영구 0 박제 정합 — 본 validator 만
    forcePatternInference 안 finding dict 의 list[str] (warnings) 박제 허용.

    명세:
      · top-level forcePatternInference.warnings: list[str] strict (non-empty str only)
      · findings: list[dict] 박제 (Top-3 cap, length <= 3)
      · 각 finding dict: _validate_force_pattern_finding_dict 위임
      · 기타 nested dict / nested list / 화이트리스트 외 list → reject

    위반 시 ValueError + path 정보 (caller 가 catch → fail_analysis 진입).
    """
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(
            f"_validate_force_pattern_inference: dict 입력만 허용. "
            f"path={path!r} got {type(payload).__name__}"
        )
    for key, value in payload.items():
        sub = f"{path}.{key}"
        if value is None or isinstance(value, (str, int, float, bool)):
            continue
        # Phase 11 (Plan 11-01, iter-2 BLOCKER-1) — coachCommentHook 전용 strict validator.
        # 일반 nested-dict reject 브랜치 위에서 먼저 처리 (generic 위임 금지).
        if key == "coachCommentHook":
            _validate_coach_comment_hook(value, path=sub)
            continue
        if isinstance(value, dict):
            raise ValueError(
                f"{sub} unexpected nested dict at forcePatternInference top-level"
            )
        if isinstance(value, list):
            if key == "warnings":
                # R2 (Codex iter-2) — top-level warnings 도 non-empty str only.
                for i, item in enumerate(value):
                    if isinstance(item, (list, dict)):
                        raise ValueError(
                            f"{sub}[{i}] nested {type(item).__name__} reject"
                        )
                    if not isinstance(item, str) or not item:
                        raise ValueError(
                            f"{sub}[{i}] must be non-empty str warning code "
                            f"(contract list[str]), got {type(item).__name__}={item!r}"
                        )
                continue
            if key == "findings":
                if len(value) > 3:
                    raise ValueError(
                        f"{sub} length > 3 — D-09-B4 fabrication 금지 "
                        f"(len={len(value)})"
                    )
                for i, item in enumerate(value):
                    _validate_force_pattern_finding_dict(item, path=f"{sub}[{i}]")
                continue
            raise ValueError(
                f"{sub} unexpected list at forcePatternInference top-level "
                f"(only 'warnings' and 'findings' allowed)"
            )
        raise ValueError(
            f"{sub} unexpected type at forcePatternInference: {type(value).__name__}"
        )


# ── Plan 13-A (2026-06-16, Phase 13) — recommended_exercises scoped validator ──
#
# PERS-03. `_validate_force_pattern_inference` 1:1 mirror — `_validate_dict_only_scalars`
# 본체 변경 영구 0 박제 정합. recommendedExercises 는 result 내부 list[dict] 이며
# 각 dict 는 flat scalar (name/setsReps/purpose/sourceRef) 만 — 본 validator 만
# 이 list[dict] path 를 박제 허용한다. [[firestore-nested-array-flat]] 보존.


def _validate_recommended_exercises(
    payload, *, path: str = "recommendedExercises"
) -> None:
    """recommended_exercises scoped validator (Plan 13-A / PERS-03).

    명세:
      · None graceful (미산출 분석 — return).
      · list 아니면 reject.
      · len > MAX_RECOMMENDED_EXERCISES(5) reject (criteria 2 cap — fabrication 금지).
      · 각 item: dict + flat scalar 만 (`_validate_dict_only_scalars` 위임,
        nested list / nested dict reject — firestore-nested-array-flat 보존).

    위반 시 ValueError + path 정보 (caller 가 catch → fail_analysis 진입).
    """
    if payload is None:
        return
    if not isinstance(payload, list):
        raise ValueError(
            f"_validate_recommended_exercises: list 입력만 허용. "
            f"path={path!r} got {type(payload).__name__}"
        )
    if len(payload) > models.MAX_RECOMMENDED_EXERCISES:
        raise ValueError(
            f"{path} length > {models.MAX_RECOMMENDED_EXERCISES} — criteria 2 cap "
            f"(len={len(payload)})"
        )
    for i, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(
                f"{path}[{i}] must be dict, got {type(item).__name__}"
            )
        _validate_dict_only_scalars(item, path=f"{path}[{i}]")


def _validate_deduction_breakdown(
    breakdown, *, path: str = "deductionBreakdown"
) -> None:
    """deductionBreakdown scoped validator (Phase 24, ND-01/HIGH-1).

    result['deductionBreakdown'] 은 OBJECT {baseline, records, final, coverageGaps,
    fallback} — records/coverageGaps 는 flat scalar dict 의 list(Firestore nested-array
    금지). recommendedExercises/forcePatternInference 패턴 mirror — 각 record/gap 을
    `_validate_dict_only_scalars` 로 라우팅(nested list/dict reject). None/부재 graceful
    (legacy doc). 위반 시 ValueError + path(caller 가 catch → fail_analysis).
    """
    if breakdown is None:
        return
    if not isinstance(breakdown, dict):
        raise ValueError(
            f"_validate_deduction_breakdown: dict 입력만 허용. "
            f"path={path!r} got {type(breakdown).__name__}"
        )
    # quick-260802-nse: suppressedRecords 도 flat scalar dict 의 list 다 — 검증 대상에
    # 넣지 않으면 nested array 가 이 키를 통해 그대로 새어 Firestore 쓰기가 실패한다
    # ([[firestore-nested-array-flat]]).
    for list_key in ("records", "coverageGaps", "suppressedRecords"):
        items = breakdown.get(list_key)
        if items is None:
            continue
        if not isinstance(items, list):
            raise ValueError(
                f"{path}.{list_key} must be list, got {type(items).__name__}"
            )
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(
                    f"{path}.{list_key}[{i}] must be dict, got {type(item).__name__}"
                )
            _validate_dict_only_scalars(item, path=f"{path}.{list_key}[{i}]")


# ── Plan 12-01 (2026-06-10, Phase 12) — keypoint_report scoped validator ──
#
# D-12-E3 + RESEARCH Pattern 5. Phase 9 `_validate_force_pattern_inference` 1:1
# mirror — nested-array 금지 + 화이트리스트 list field 만 허용. keypointReport
# 안에서만 list[float] (data/confidence/axisData) + list[bool] (axisMask) +
# list[str] (joints/reliability/warnings) 박제 가능.
#
# scope: 본 validator 만 `result.keypointReport` path 박제 호출. 다른 path
# 박제 strict 유지 ([[firestore-nested-array-flat]] project-wide 보존).

# H3 iter-4 (Codex) — finite + range 강제 import.
import math as _math_kr  # noqa: E402 — scope-local 박제, 다른 path 영향 X

_KEYPOINT_REPORT_KEYS: frozenset[str] = frozenset(
    {
        "version",
        "joints",
        "frames",
        "fps",
        "data",
        "confidence",
        "reliability",
        "axisData",
        "axisMask",
        "warnings",
    }
)
"""R10 + R7 iter-2 — 10 키 strict whitelist (camelCase only)."""

_KEYPOINT_VALID_RELIABILITY: frozenset[str] = frozenset({"high", "medium", "low"})


def _validate_keypoint_report(
    payload: dict, *, path: str = "keypointReport"
) -> None:
    """keypoint_report top-level scoped validator (D-12-E3).

    Plan 12-01 (Phase 12) — `_validate_force_pattern_inference` 패턴 1:1 mirror.
    `_validate_dict_only_scalars` 본체 변경 영구 0 박제 정합 — 본 validator 만
    keypointReport 안 flat list (data/confidence/axisData/axisMask/joints/
    reliability/warnings) 박제 허용.

    명세:
      · top-level keypointReport.version/frames/fps: scalar.
      · joints: list[non-empty str] (nested list/dict reject).
      · data: list[number] flat — finite only (H3 iter-4).
      · confidence: list[number] flat — finite + [0, 1] (H3 iter-4).
      · axisData: list[number] flat — finite only (R7 iter-2).
      · axisMask: list[bool strict] — type(item) is bool 강제 (R7 iter-2 / H3).
      · reliability: list[str ∈ {"high","medium","low"}].
      · warnings: list[non-empty str].
      · 화이트리스트 외 key 박제 시 reject.
      · [32-14 신설 — 길이 정합] joints 길이 ∈ {8(legacy), 12(phase32)} +
        frames 스칼라 존재 시 data 길이 == frames×J×2, confidence 길이 ==
        frames×J (frames 부재 legacy 형상은 기존 그대로 통과 — T-32-36).
        기존 per-key 검사(현행)는 길이를 비검사했음 — 이 블록이 신설이며
        legacy 8 doc green 테스트(test_keypoint_report_expansion)로 하위호환 증명.

    위반 시 ValueError + path 정보 (caller 가 catch → fail_analysis 진입).
    """
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise ValueError(
            f"_validate_keypoint_report: dict 입력만 허용. "
            f"path={path!r} got {type(payload).__name__}"
        )
    for key, value in payload.items():
        sub = f"{path}.{key}"
        if key not in _KEYPOINT_REPORT_KEYS:
            raise ValueError(
                f"{sub} key not in keypointReport whitelist "
                f"({sorted(_KEYPOINT_REPORT_KEYS)}); reject"
            )
        if value is None or isinstance(value, (str, int, float, bool)):
            # scalar (version/frames/fps) — type guard 는 dataclass __post_init__
            # 가 산출 시점에 강제. validator 는 nested 차단이 핵심.
            continue
        if isinstance(value, dict):
            raise ValueError(
                f"{sub} unexpected nested dict at keypointReport top-level "
                f"(schema: scalar + flat list only)"
            )
        if isinstance(value, list):
            if key == "joints":
                for i, item in enumerate(value):
                    if isinstance(item, (list, dict)):
                        raise ValueError(
                            f"{sub}[{i}] nested {type(item).__name__} reject "
                            f"(firestore-nested-array-flat 보존)"
                        )
                    if not isinstance(item, str) or not item:
                        raise ValueError(
                            f"{sub}[{i}] must be non-empty str (joint name), "
                            f"got {type(item).__name__}={item!r}"
                        )
                continue
            if key == "reliability":
                for i, item in enumerate(value):
                    if isinstance(item, (list, dict)):
                        raise ValueError(
                            f"{sub}[{i}] nested {type(item).__name__} reject"
                        )
                    if item not in _KEYPOINT_VALID_RELIABILITY:
                        raise ValueError(
                            f"{sub}[{i}] must be one of "
                            f"{sorted(_KEYPOINT_VALID_RELIABILITY)}, got {item!r}"
                        )
                continue
            if key == "warnings":
                for i, item in enumerate(value):
                    if isinstance(item, (list, dict)):
                        raise ValueError(
                            f"{sub}[{i}] nested {type(item).__name__} reject"
                        )
                    if not isinstance(item, str) or not item:
                        raise ValueError(
                            f"{sub}[{i}] must be non-empty str warning code, "
                            f"got {type(item).__name__}={item!r}"
                        )
                continue
            if key == "data":
                # H3 iter-4 — finite only.
                for i, item in enumerate(value):
                    if isinstance(item, (list, dict)):
                        raise ValueError(
                            f"{sub}[{i}] nested {type(item).__name__} reject "
                            f"(firestore-nested-array-flat 보존)"
                        )
                    if not isinstance(item, (int, float)) or isinstance(item, bool):
                        raise ValueError(
                            f"{sub}[{i}] must be number (flat float), "
                            f"got {type(item).__name__}={item!r}"
                        )
                    if not _math_kr.isfinite(float(item)):
                        raise ValueError(
                            f"{sub}[{i}] data finite required (H3 iter-4 — "
                            f"no NaN/Inf), got {item!r}"
                        )
                continue
            if key == "confidence":
                # H3 iter-4 — finite + [0, 1].
                for i, item in enumerate(value):
                    if isinstance(item, (list, dict)):
                        raise ValueError(
                            f"{sub}[{i}] nested {type(item).__name__} reject"
                        )
                    if not isinstance(item, (int, float)) or isinstance(item, bool):
                        raise ValueError(
                            f"{sub}[{i}] must be number, "
                            f"got {type(item).__name__}={item!r}"
                        )
                    fv = float(item)
                    if not _math_kr.isfinite(fv) or not (0.0 <= fv <= 1.0):
                        raise ValueError(
                            f"{sub}[{i}] confidence range [0, 1] finite required "
                            f"(H3 iter-4), got {item!r}"
                        )
                continue
            if key == "axisData":
                # R7 iter-2 — finite only.
                for i, item in enumerate(value):
                    if isinstance(item, (list, dict)):
                        raise ValueError(
                            f"{sub}[{i}] nested {type(item).__name__} reject"
                        )
                    if not isinstance(item, (int, float)) or isinstance(item, bool):
                        raise ValueError(
                            f"{sub}[{i}] must be number, "
                            f"got {type(item).__name__}={item!r}"
                        )
                    if not _math_kr.isfinite(float(item)):
                        raise ValueError(
                            f"{sub}[{i}] axisData finite required (R7 iter-2 — "
                            f"no NaN/Inf), got {item!r}"
                        )
                continue
            if key == "axisMask":
                # R7 iter-2 + H3 iter-4 — type(item) is bool strict (int 0/1 reject).
                for i, item in enumerate(value):
                    if isinstance(item, (list, dict)):
                        raise ValueError(
                            f"{sub}[{i}] nested {type(item).__name__} reject"
                        )
                    if type(item) is not bool:
                        raise ValueError(
                            f"{sub}[{i}] axisMask must be bool strict (H3 — "
                            f"int 0/1 reject), got {type(item).__name__}={item!r}"
                        )
                continue
            # 그 외 list 키 (whitelist 통과했지만 list 핸들러 없음 — 방어적 fallback).
            raise ValueError(
                f"{sub} unexpected list field — no list handler defined"
            )
        raise ValueError(
            f"{sub} unexpected type at keypointReport: {type(value).__name__}"
        )

    # ── 32-14 (D-22 1단) — 길이 정합 검사 신설 ────────────────────────────
    # scoped validator 내부에만 추가 (_validate_dict_only_scalars 본체 무변경
    # 박제 유지). per-key 검사 통과 후 cross-field 정합만 여기서 강제.
    joints_val = payload.get("joints")
    if isinstance(joints_val, list):
        J = len(joints_val)
        if J not in (8, 12):
            raise ValueError(
                f"{path}.joints length must be 8 (legacy) or 12 (phase32), "
                f"got {J} — 32-14 길이 정합"
            )
        frames_val = payload.get("frames")
        # frames 스칼라 존재 시에만 data/confidence 길이 정합 강제.
        # 부재 legacy 형상은 기존 그대로 통과 (T-32-36 하위호환).
        if isinstance(frames_val, int) and not isinstance(frames_val, bool):
            T = frames_val
            data_val = payload.get("data")
            if isinstance(data_val, list) and len(data_val) != T * J * 2:
                raise ValueError(
                    f"{path}.data length must be frames*joints*2 = {T * J * 2}, "
                    f"got {len(data_val)} — 32-14 길이 정합"
                )
            conf_val = payload.get("confidence")
            if isinstance(conf_val, list) and len(conf_val) != T * J:
                raise ValueError(
                    f"{path}.confidence length must be frames*joints = {T * J}, "
                    f"got {len(conf_val)} — 32-14 길이 정합"
                )


# ── Plan 04-01 (Phase 4 Wave 1, 2026-06-13) — joints3d 전용 validator ─────
#
# R3 fix + BLOCKER-4 — 범용 _validate_flat_dict_no_nested_array 우회 아님. flat
# length, finite-only, coord_dim==3, space ∈ allowed set 강제. 04-02 가
# `doc.result.joints3d` 를 reshapePose3dData 로 소비 — 본 validator 가
# Firestore 저장 단계의 회귀 차단.

_VALID_JOINTS3D_SPACES: frozenset[str] = frozenset({"rtmw3d", "pole_aligned"})


def _validate_joints3d_payload(
    joints3d: list,
    joints3d_keys: list,
    joints3d_frames: int,
    coord_dim: int,
    space: str,
) -> None:
    """R3 fix + BLOCKER-4 — joints3d flat 저장 invariant 검증.

    invariant:
      · joints3d (list[float]) 길이 == joints3d_frames × len(joints3d_keys) × coord_dim
      · joints3d 의 모든 원소 finite (NaN/Inf 금지 — 04-02 reshape 시 viewer 폭주 방지)
      · joints3d_keys 길이 == 17 (COCO-17)
      · coord_dim == 3
      · space ∈ {"rtmw3d", "pole_aligned"}

    raises:
      ValueError: 위 invariant 위반 시.
      TypeError: 잘못된 타입 (e.g. nested list) 전달 시.
    """
    import math

    if not isinstance(joints3d, list):
        raise TypeError(
            f"joints3d must be flat list[float] (firestore-nested-array-flat): "
            f"got {type(joints3d).__name__}"
        )
    if not isinstance(joints3d_keys, list):
        raise TypeError(
            f"joints3d_keys must be list[str]: got {type(joints3d_keys).__name__}"
        )
    if len(joints3d_keys) != 17:
        raise ValueError(
            f"joints3d_keys length must be 17 (COCO-17): got {len(joints3d_keys)}"
        )
    if not isinstance(joints3d_frames, int) or joints3d_frames <= 0:
        raise ValueError(
            f"joints3d_frames must be positive int: got {joints3d_frames!r}"
        )
    if coord_dim != 3:
        raise ValueError(
            f"coord_dim must be 3 (joints3d xyz only): got {coord_dim!r}"
        )
    if space not in _VALID_JOINTS3D_SPACES:
        raise ValueError(
            f"space must be one of {sorted(_VALID_JOINTS3D_SPACES)}: got {space!r}"
        )
    expected_len = joints3d_frames * len(joints3d_keys) * coord_dim
    if len(joints3d) != expected_len:
        raise ValueError(
            f"joints3d length must be frames * keys * coord_dim = {expected_len}, "
            f"got {len(joints3d)}"
        )
    # finite-only 검증 — nested list 가 들어왔다면 TypeError, 그 외 NaN/Inf 는
    # ValueError. 빈 list 는 위 길이 검증에서 이미 reject (expected_len > 0).
    for i, v in enumerate(joints3d):
        if isinstance(v, list):
            raise TypeError(
                f"joints3d[{i}] is nested list (firestore-nested-array-flat): "
                f"flat list[float] 만 허용"
            )
        if not isinstance(v, (int, float)):
            raise TypeError(
                f"joints3d[{i}] must be scalar float: got {type(v).__name__}"
            )
        if not math.isfinite(float(v)):
            raise ValueError(
                f"joints3d[{i}] must be finite (no NaN/Inf): got {v!r}"
            )


def complete_analysis(
    uid: str,
    analysis_id: str,
    result: dict,
    *,
    angles: list | None = None,
    angles_joint_keys: list | None = None,
    angles_frames: int | None = None,
    body_comparison_report: dict | None = None,
    body_normalization_profile: dict | None = None,
    force_signals_report: dict | None = None,
    force_pattern_inference: dict | None = None,
    recommended_exercises: list | None = None,
    keypoint_report: dict | None = None,
    gemini_b: dict | None = None,
    gemini_c: dict | None = None,
    gemini_d: dict | None = None,
    ai_synthesis_meta: dict | None = None,
    joints3d: list | None = None,
    joints3d_keys: list | None = None,
    joints3d_frames: int | None = None,
    coord_dim: int | None = None,
    space: str | None = None,
) -> None:
    """status='done' + result (contract.md §4 AnalysisResult).

    angles 가 주어지면 추출된 관절각을 doc top-level 에 flat 저장한다 — mode3(자기
    성장)가 '이전 분석 영상'을 기준 시퀀스로 DTW 비교할 때 읽는다. Firestore 는
    nested-array 금지라 flat list + anglesJointKeys(길이 J) + anglesFrames(T) 로
    저장하고 읽는 쪽에서 reshape ([[firestore-nested-array-flat]]). get_previous_analysis
    는 to_dict() 로 이 필드를 자동 반환한다.

    Phase 6 (2026-06-08, Plan 06-02) — D-06-B3 + [[firestore-nested-array-flat]] +
    W5 validator + C14 (pose_reliability_low):
      - body_comparison_report = result 내부 (AnalysisResult.bodyComparisonReport 정합)
      - body_normalization_profile = top-level (mode3 progress prev fetch path).
      - 두 dict 모두 _validate_flat_dict_no_nested_array 통과 강제 — 위반 시 TypeError.

    Phase 8 (2026-06-09, Plan 08-03 — REVIEWS Cycle 2 §3 NEW HIGH #3):
      - force_signals_report = result 내부 (AnalysisResult.forceSignalsReport 정합).
      - **`_validate_force_signals_report` 전용 scoped validator** 박제 호출
        (`_validate_dict_only_scalars` 본체 변경 영구 0 — project-wide
        [[firestore-nested-array-flat]] 보존). force_signals 안 metric dict 의
        `warnings` / `unstableBodyParts` list[str] 박제만 허용, 다른 list[scalar]
        박제 시 ValueError. 다른 path 박제 strict 유지.

    Phase 28 (2026-07-08, Plan 28-03 — ALGN-01 동작 기반 비교 정렬):
      - motion_alignment = result 내부 (AnalysisResult.motionAlignment 정합, 신규 kwarg
        없음 — safetyFlags 선례). **`_validate_motion_alignment` 전용 scoped validator**
        호출 — anchors flat/finite/짝수 + 상한 512(40k index-entry 방어, T-28-05) + 단조성
        + tier↔anchors 역불변식(MEDIUM-3: disabled 만 빈 anchors). generic
        `_validate_dict_only_scalars` 본체 변경 영구 0 유지.
    """
    # Phase 24 (ND-01/HIGH-1) — deductionBreakdown 은 seam 에서 result 안에 OBJECT 로
    # 들어온다(visionVeto persistence analog, NO 신규 kwarg). payload['result']=dict(result)
    # 전에 scoped validator 로 records/coverageGaps flat 검증(firestore-nested-array-flat).
    if result:
        _validate_deduction_breakdown((result or {}).get("deductionBreakdown"))
        # Plan 10-02 (T-10-01) — safetyFlags 단일 persistence path. result 안으로
        # 흘러온 list[dict] 를 scalar-only scoped validator 로 검증 (신규 kwarg 없음).
        _flags = (result or {}).get("safetyFlags")
        if isinstance(_flags, list):
            _validate_safety_flags(_flags)
        # Phase 28 (ALGN-01) — motionAlignment 단일 persistence path. result 안으로
        # 흘러온 dict 를 scoped validator 로 검증 (상한/flat/단조 + tier↔anchors 역불변식,
        # 신규 kwarg 없음 — safetyFlags 선례).
        _validate_motion_alignment((result or {}).get("motionAlignment"))
        # Phase 32 (Plan 32-06) — 미션 루프 + 번역 레이어 단일 persistence path.
        # 전부 result 안으로 흐른다 (신규 kwarg 0 — SP-1, safetyFlags 선례).
        # None/부재 graceful — 방출은 32-09 부터 (contract.md §12).
        _validate_mission((result or {}).get("mission"))
        _validate_mission_outcome((result or {}).get("missionOutcome"))
        _validate_summary_praise((result or {}).get("summaryPraise"))
        _validate_coach_questions((result or {}).get("coachQuestions"))
    payload: dict = {
        "status": models.STATUS_DONE,
        "result": dict(result) if result else {},
        "updatedAt": int(time.time() * 1000),
    }
    if angles is not None:
        payload["angles"] = angles
        payload["anglesJointKeys"] = angles_joint_keys
        payload["anglesFrames"] = angles_frames
    if body_comparison_report is not None:
        # Phase 11 (Plan 11-01, iter-2 BLOCKER-1) — coachCommentHook body precheck.
        # generic _validate_flat_dict_no_nested_array 는 list[dict] hook 을 허용해버리므로
        # (scalar-only dict 라우팅) 전용 strict validator 로 먼저 hook 만 검증한 뒤
        # 나머지 (findings/warnings) 를 generic 으로 검증한다.
        _hook = body_comparison_report.get("coachCommentHook")
        if _hook is not None:
            _validate_coach_comment_hook(
                _hook, path="bodyComparisonReport.coachCommentHook"
            )
        _validate_flat_dict_no_nested_array(
            body_comparison_report, path="bodyComparisonReport"
        )
        payload["result"]["bodyComparisonReport"] = body_comparison_report
    if body_normalization_profile is not None:
        _validate_flat_dict_no_nested_array(
            body_normalization_profile, path="bodyNormalizationProfile"
        )
        payload["bodyNormalizationProfile"] = body_normalization_profile
    if force_signals_report is not None:
        # Plan 08-03 (REVIEWS Cycle 2 §3 NEW HIGH #3) — scoped validator 박제.
        # `_validate_dict_only_scalars` 호출 X (다른 path 박제 strict 유지).
        _validate_force_signals_report(force_signals_report)
        payload["result"]["forceSignalsReport"] = force_signals_report
    if force_pattern_inference is not None:
        # Plan 09-01 (Phase 9, 2026-06-10) — D-09-U5 scoped validator.
        # top-level forcePatternInference 만 nested list[dict] 허용,
        # [[firestore-nested-array-flat]] 보존. Phase 8 패턴 1:1 mirror.
        _validate_force_pattern_inference(force_pattern_inference)
        payload["result"]["forcePatternInference"] = force_pattern_inference
    if recommended_exercises is not None:
        # Plan 13-A (Phase 13, 2026-06-16) — PERS-03 scoped validator.
        # result 내부 list[dict] (3~5 보완 운동). force_pattern_inference 블록
        # mirror — len <= 5 cap + flat scalar 만. [[firestore-nested-array-flat]] 보존.
        _validate_recommended_exercises(recommended_exercises)
        payload["result"]["recommendedExercises"] = recommended_exercises
    if keypoint_report is not None:
        # Plan 12-01 (Phase 12, 2026-06-10) — D-12-E3 scoped validator.
        # `_validate_keypoint_report` 가 flat 강제 + nested list reject.
        # [[firestore-nested-array-flat]] 보존. Phase 9 패턴 1:1 mirror.
        _validate_keypoint_report(keypoint_report)
        payload["result"]["keypointReport"] = keypoint_report
    if gemini_b is not None:
        # Plan 17-04 — 영역 B Coach 박제 (flat audit object, WARNING-3 정합).
        # user-visible result.tips/coach 와 분리 — Firestore top-level `geminiB` 박힘.
        # flat object 강제 — scalar (model / latencyMs / fallback / fallbackReason /
        # judgeScore=null) + list[dict-of-scalars] (causes) 만 박제. nested list /
        # nested dict 영구 0. 기존 W5 validator 재사용으로 회귀 차단.
        _validate_flat_dict_no_nested_array(gemini_b, path="geminiB")
        payload["geminiB"] = gemini_b
    if gemini_c is not None:
        # Plan 17-02 — 영역 C Finding flag 박제 (flat object).
        # [[firestore-nested-array-flat]] 정합 — 4 boolean + str (notes_ko) +
        # scalar meta (model / tokens_used / latency_ms) + nullable guardrail_triggered
        # 만 박힘. nested list / nested dict 영구 0. 기존 W5 validator 재사용으로
        # 회귀 차단.
        _validate_flat_dict_no_nested_array(gemini_c, path="geminiC")
        payload["geminiC"] = gemini_c
    if gemini_d is not None:
        # Plan 17-03 — 영역 D Keypoint 보강 audit (flat object 박제).
        # WARNING-3 정합 — user-visible result.keypointReport 와 audit top-level
        # geminiD 분리. flat object 박제 — scalar (model / guardrail_blocked_count)
        # + list[scalar] (augmentedFrames / originalRtmwUncertaintyProxy) + dict[str, str]
        # (mirrorHint) 박제. nested list / nested dict 영구 0. 기존 W5 validator
        # 재사용으로 회귀 차단.
        _validate_flat_dict_no_nested_array(gemini_d, path="geminiD")
        payload["geminiD"] = gemini_d
    if ai_synthesis_meta is not None:
        # Plan 04-01 Wave 1 (Phase 4) — POSE-03 D-08 / R3 fix.
        # 합성 메타 — result 내부 박제 (AnalysisResult.aiSynthesisMeta 정합).
        # warnings 필드는 public enum (ai_synthesis_failed / ai_synthesis_partial),
        # debugWarnings 필드는 raw reason — 둘 다 list[str] 로 W5 validator 통과.
        # BLOCKER-3 canonical surface — pipeline 이 raw → public 분류 매핑 후 주입.
        _validate_flat_dict_no_nested_array(
            ai_synthesis_meta, path="aiSynthesisMeta"
        )
        payload["result"]["aiSynthesisMeta"] = ai_synthesis_meta
    if joints3d is not None:
        # Plan 04-01 Wave 1 (Phase 4) — R3 fix + BLOCKER-1/4. flat 저장.
        # 04-02 가 doc.result.joints3d 를 reshapePose3dData 로 소비. 위치 = result
        # 내부 (angles 가 top-level 인 건 reference doc 호환 quirk, joints3d 는
        # analysis 산출물이라 result 박제).
        if (
            joints3d_keys is None
            or joints3d_frames is None
            or coord_dim is None
            or space is None
        ):
            raise ValueError(
                "joints3d 저장 시 joints3d_keys / joints3d_frames / coord_dim / "
                "space 모두 필수"
            )
        _validate_joints3d_payload(
            joints3d, joints3d_keys, joints3d_frames, coord_dim, space
        )
        payload["result"]["joints3d"] = joints3d
        payload["result"]["joints3dKeys"] = joints3d_keys
        payload["result"]["joints3dFrames"] = joints3d_frames
        payload["result"]["coordDim"] = coord_dim
        payload["result"]["space"] = space
    _doc(models.analysis_doc_path(uid, analysis_id)).set(payload, merge=True)


def update_analysis_fault_zoom(
    uid: str,
    analysis_id: str,
    comparisons: list[dict],
    status: str,
) -> None:
    """fault_zoom 사후 부분 업데이트 (Phase 27 SPD-04 / D-06 — 27-RESEARCH Pattern 5).

    complete_analysis(status='done') **이후** 같은 BackgroundTask 에서 호출한다.
    점수/verdict/감점 내역은 이미 확정됐고(D-03 경계), zoom PNG 는 표현물이라 사후 도착이
    허용된다(contract.md faultZoomStatus 절 + D-06). result.faultZoom* **두 필드만**
    field-path 로 부분 갱신한다 — zoom 외 어떤 result.* 필드도 사후 변경 금지
    (T-27-18 / D-03). status='pending' 마커는 complete_analysis 시 result 안에 실려
    이미 저장되므로, 본 함수는 done/failed 전이만 쓴다.

    검증: 각 comparisons item 을 `_validate_dict_only_scalars` 로 라우팅해 nested
    list/dict 를 거부한다(complete_analysis 의 `_validate_safety_flags` 선례와 동형 —
    validator 본체 무수정, [[firestore-nested-array-flat]] 보존). status 는
    models.FAULT_ZOOM_STATUSES 로 강제한다.

    firebase-admin 표준 `.update()` field-path 사용 — 본 모듈은 `set(merge=True)` 가
    정본이지만 merge 는 dict 병합이라 **배열 교체 의미가 모호**하다(부분 병합 위험).
    zoom 은 매번 통째 교체이므로 명시적 field-path `.update()` 채택 (27-PATTERNS
    부분-무선례 메모).

    Args:
      comparisons: FaultZoomComparison camelCase dict 리스트(flat scalar). status='failed'
        시 빈 리스트 허용.
      status: models.FAULT_ZOOM_STATUSES 중 하나 (pending/done/failed).

    Raises:
      ValueError: status 가 FAULT_ZOOM_STATUSES 밖.
      TypeError: comparisons item 에 nested list/dict (scoped validator).
    """
    if status not in models.FAULT_ZOOM_STATUSES:
        raise ValueError(
            f"faultZoomStatus must be one of {list(models.FAULT_ZOOM_STATUSES)}, "
            f"got {status!r}"
        )
    _comparisons = list(comparisons or [])
    for i, c in enumerate(_comparisons):
        # nested list/dict 거부 — validator 본체 무수정 재사용 (safetyFlags 선례).
        _validate_dict_only_scalars(c, path=f"faultZoomComparisons[{i}]")
    _doc(models.analysis_doc_path(uid, analysis_id)).update(
        {
            "result.faultZoomComparisons": _comparisons,
            "result.faultZoomStatus": status,
            "updatedAt": int(time.time() * 1000),
        }
    )


def _validate_coach_audio(payload, *, path: str = "coachAudio") -> None:  # noqa: ANN001
    """coachAudio scoped validator (Phase 32 Plan 32-16, D-18 — contract.md §12.7).

    형상: {status: 'done'|'failed', items: list[{recordId, key}]}. generic
    `_validate_dict_only_scalars` 본체 변경 영구 0 — 각 item 을 그 validator 로
    라우팅해 nested list/dict 를 거부하고(safetyFlags 선례), 본 validator 는
    키 화이트리스트 + enum + 타입만 추가로 강제한다 (stricter):
      · 최상위 키 = models.COACH_AUDIO_KEYS 정확히 (누락/여분 거부)
      · status ∈ models.COACH_AUDIO_STATUSES
      · items = list, 각 item 키 = models.COACH_AUDIO_ITEM_KEYS 정확히
      · recordId/key 비어있지 않은 str + key 는 'results/' prefix
        (H-02 — 오염 key 가 doc 에 실리는 것 자체를 차단)
    실패 시 TypeError/ValueError raise (caller 가 graceful 처리).
    """
    if not isinstance(payload, dict):
        raise TypeError(
            f"_validate_coach_audio: dict 입력만 허용. path={path or '<root>'}, "
            f"got={type(payload).__name__}"
        )
    if set(payload.keys()) != set(models.COACH_AUDIO_KEYS):
        raise ValueError(
            f"{path}: 키는 {list(models.COACH_AUDIO_KEYS)} 정확히여야 함. "
            f"got={sorted(payload.keys())}"
        )
    status = payload["status"]
    if status not in models.COACH_AUDIO_STATUSES:
        raise ValueError(
            f"{path}.status: {list(models.COACH_AUDIO_STATUSES)} 중 하나여야 함. "
            f"got={status!r}"
        )
    items = payload["items"]
    if not isinstance(items, list):
        raise TypeError(
            f"{path}.items: list 만 허용. got={type(items).__name__}"
        )
    for i, item in enumerate(items):
        item_path = f"{path}.items[{i}]"
        # nested list/dict 거부 — generic validator 라우팅 (본체 무수정).
        _validate_dict_only_scalars(item, path=item_path)
        if set(item.keys()) != set(models.COACH_AUDIO_ITEM_KEYS):
            raise ValueError(
                f"{item_path}: 키는 {list(models.COACH_AUDIO_ITEM_KEYS)} 정확히여야 함. "
                f"got={sorted(item.keys())}"
            )
        record_id = item["recordId"]
        key = item["key"]
        if not isinstance(record_id, str) or not record_id:
            raise ValueError(f"{item_path}.recordId: 비어있지 않은 str 이어야 함")
        if not isinstance(key, str) or not key.startswith("results/"):
            raise ValueError(
                f"{item_path}.key: 'results/' prefix 의 str 이어야 함 (H-02)"
            )


def update_analysis_coach_audio(
    uid: str,
    analysis_id: str,
    items: list[dict],
    status: str,
) -> None:
    """coach_audio 사후 부분 업데이트 (Phase 32 Plan 32-16, D-18 — fault_zoom 뼈대 복제).

    complete_analysis(status='done') **이후** 같은 분석 태스크에서 호출한다. 점수/
    verdict/감점 내역은 이미 확정됐고(D-03 경계), 큐 오디오 mp3 는 표현물이라 사후
    도착이 허용된다 (update_analysis_fault_zoom 과 동일 규율). `result.coachAudio`
    **단일 field-path** 만 부분 갱신 — 그 외 어떤 result.* 필드도 사후 변경 금지
    (T-27-18 / D-03).

    검증: `_validate_coach_audio` (키 화이트리스트 + status enum + item scalar-only
    + key results/ prefix). 오디오 목록은 매번 통째 교체이므로 fault_zoom 선례대로
    명시적 field-path `.update()` 채택 (merge 의 배열 병합 모호성 회피).

    Args:
      items: [{recordId, key}] scalar dict 리스트. status='failed' 또는 큐 없음
        분석은 빈 리스트 허용.
      status: models.COACH_AUDIO_STATUSES 중 하나 (done/failed).

    Raises:
      ValueError/TypeError: 형상 위반 (_validate_coach_audio).
    """
    payload = {"status": status, "items": list(items or [])}
    _validate_coach_audio(payload)
    _doc(models.analysis_doc_path(uid, analysis_id)).update(
        {
            "result.coachAudio": payload,
            "updatedAt": int(time.time() * 1000),
        }
    )


# ── quick-260901-wbo — coach 텍스트 사후 분리 (coach_dual + hook 사후화) ─────────
#
# 코칭 문장은 표현물 — complete(status='done') 이후 도착 허용 (fault_zoom D-06 선례).
# tips 는 required 필드라 complete 시점에 수치 폴백으로 이미 유효하고, 본 부분 갱신은
# 코칭 텍스트(detail/detail2)로의 **승격**이다. 허용 field-path 는
# update_analysis_coach_text docstring 의 5개뿐 — 점수/verdict/감점 tally
# (deductionBreakdown)/records 문구는 사후 변경 영구 금지 (D-03 경계,
# contract.md coachStatus 절).

# tip dict 허용 키 — build_tips / build_result angle>=95 일반 팁 산출 형상.
_COACH_TIP_KEYS: frozenset[str] = frozenset({"joint", "title", "detail", "detail2"})
# detail2 허용 키 — 13-C 섹션 조립 산출 형상 (assemble.assemble_dual_coach_sections).
_COACH_TIP_DETAIL2_KEYS: frozenset[str] = frozenset(
    {"causes", "injuryRisk", "coachNote"}
)


def _validate_coach_tips(tips, *, path: str = "tips") -> None:  # noqa: ANN001
    """result.tips 통째 교체용 scoped validator (quick-260901-wbo).

    형상: list[{joint: str|None, title: str, detail: str, detail2?: dict}].
    detail2 = {causes: list[dict-of-scalars], injuryRisk?: str, coachNote?: str}
    (assemble_dual_coach_sections 산출 — complete_analysis 가 오늘도 같은 형상 저장).

    Firestore nested-array 금지 준수 — tips[].detail2.causes 는
    array→map→map→array 라 합법. causes 의 각 원소는 `_validate_dict_only_scalars`
    라우팅으로 nested list/dict 를 거부한다 (validator 본체 무수정 — safetyFlags
    선례). 키 화이트리스트(누락 detail/title, 여분 키)는 본 validator 가 강제.

    Raises:
        TypeError: tips 가 list 아님 / tip 이 dict 아님 / causes 원소 nested
          (firestore-nested-array-flat).
        ValueError: 화이트리스트 밖 키 / 빈 title·detail / joint 타입 위반 /
          detail2 형상 위반.
    """
    if not isinstance(tips, list):
        raise TypeError(
            f"{path} must be list (coach tips), got {type(tips).__name__}"
        )
    for i, tip in enumerate(tips):
        tip_path = f"{path}[{i}]"
        if not isinstance(tip, dict):
            raise TypeError(
                f"{tip_path} must be dict, got {type(tip).__name__}"
            )
        unknown = set(tip.keys()) - _COACH_TIP_KEYS
        if unknown:
            raise ValueError(
                f"{tip_path} unknown tip key(s) {sorted(unknown)} — 허용 키: "
                f"{sorted(_COACH_TIP_KEYS)}"
            )
        joint = tip.get("joint")
        if joint is not None and not isinstance(joint, str):
            raise ValueError(
                f"{tip_path}.joint must be str | null, got {type(joint).__name__}"
            )
        for req in ("title", "detail"):
            v = tip.get(req)
            if not isinstance(v, str) or not v.strip():
                raise ValueError(
                    f"{tip_path}.{req} must be non-empty str, got {v!r}"
                )
        if "detail2" not in tip:
            continue
        d2 = tip["detail2"]
        if not isinstance(d2, dict):
            raise ValueError(
                f"{tip_path}.detail2 must be dict, got {type(d2).__name__}"
            )
        d2_unknown = set(d2.keys()) - _COACH_TIP_DETAIL2_KEYS
        if d2_unknown:
            raise ValueError(
                f"{tip_path}.detail2 unknown key(s) {sorted(d2_unknown)} — "
                f"허용 키: {sorted(_COACH_TIP_DETAIL2_KEYS)}"
            )
        causes = d2.get("causes")
        if not isinstance(causes, list):
            raise ValueError(
                f"{tip_path}.detail2.causes must be list, "
                f"got {type(causes).__name__}"
            )
        for j, cause in enumerate(causes):
            # nested list/dict 거부 — validator 본체 무수정 라우팅 (safetyFlags 선례).
            _validate_dict_only_scalars(
                cause, path=f"{tip_path}.detail2.causes[{j}]"
            )
        for opt in ("injuryRisk", "coachNote"):
            if opt in d2 and not isinstance(d2[opt], str):
                raise ValueError(
                    f"{tip_path}.detail2.{opt} must be str, "
                    f"got {type(d2[opt]).__name__}"
                )


def update_analysis_coach_text(
    uid: str,
    analysis_id: str,
    *,
    status: str,
    tips: list | None = None,
    force_hook: dict | None = None,
    body_hook: dict | None = None,
    gemini_b: dict | None = None,
) -> None:
    """coach 텍스트 사후 부분 업데이트 (quick-260901-wbo — fault_zoom/coach_audio 뼈대).

    complete_analysis(status='done') **이후** 같은 분석 태스크에서 호출한다. 점수/
    verdict/감점 내역은 이미 확정됐고(D-03 경계), 코칭 문장은 표현물이라 사후 도착이
    허용된다. status='pending' 마커는 complete_analysis 시 result 안에 실려 이미
    저장되므로, 본 함수는 done/failed 전이만 쓴다 (update_analysis_fault_zoom 서술
    미러). 허용 field-path 는 아래 5개**뿐** — 그 외 어떤 result.* 필드도 사후 변경
    금지 (T-27-18 / D-03 / T-wbo-01):

      · result.coachStatus (필수)
      · result.tips (통째 교체 — tips 가 None 아니면)
      · result.forcePatternInference.coachCommentHook (force_hook 이 None 아니면)
      · result.bodyComparisonReport.coachCommentHook (body_hook 이 None 아니면)
      · top-level geminiB (gemini_b 가 None 아니면)

    **hook 값이 None 이면 해당 field-path 를 payload 에서 생략한다** — `.update()`
    field-path 는 중간 map 이 없으면 새로 만들어버리므로, complete 시점 doc 에
    forcePatternInference/bodyComparisonReport 가 없는 분석에 hook 만 보내면
    findings 없는 stub 리포트가 doc 에 박힌다 (260901-wbo 체커 warning 1 — caller
    도 동기 attach 조건을 미러해 리포트 실린 doc 에만 보낼 것).

    status='failed' 시 tips/hook/gemini_b 는 선택(부재 허용) — complete 시점의 수치
    폴백 tips 가 최후 바닥으로 잔존한다 (coach_audio failed-마킹 선례).

    검증: tips 는 `_validate_coach_tips`(키 화이트리스트 + nested 거부), hook 은
    기존 `_validate_coach_comment_hook`, gemini_b 는 기존
    `_validate_flat_dict_no_nested_array` 재사용. 코칭 텍스트는 매번 통째 교체이므로
    fault_zoom 선례대로 명시적 field-path `.update()` 채택 (merge 의 배열 병합
    모호성 회피).

    Raises:
      ValueError: status 가 COACH_STATUSES 밖 / tips·hook 형상 위반.
      TypeError: tips·gemini_b 에 nested list/dict (scoped validator).
    """
    if status not in models.COACH_STATUSES:
        raise ValueError(
            f"coachStatus must be one of {list(models.COACH_STATUSES)}, "
            f"got {status!r}"
        )
    payload: dict = {
        "result.coachStatus": status,
        "updatedAt": int(time.time() * 1000),
    }
    if tips is not None:
        _validate_coach_tips(tips)
        payload["result.tips"] = list(tips)
    if force_hook is not None:
        _validate_coach_comment_hook(
            force_hook, path="forcePatternInference.coachCommentHook"
        )
        payload["result.forcePatternInference.coachCommentHook"] = force_hook
    if body_hook is not None:
        _validate_coach_comment_hook(
            body_hook, path="bodyComparisonReport.coachCommentHook"
        )
        payload["result.bodyComparisonReport.coachCommentHook"] = body_hook
    if gemini_b is not None:
        _validate_flat_dict_no_nested_array(gemini_b, path="geminiB")
        payload["geminiB"] = gemini_b
    _doc(models.analysis_doc_path(uid, analysis_id)).update(payload)


def _validate_rendered_compare(payload, *, path: str = "renderedCompare") -> None:  # noqa: ANN001
    """renderedCompare scoped validator (Phase 35 quick-260808-jix — contract.md §12.9).

    형상: {status: 'done'|'failed', key: str, freezes?: [{rid, outSec}]}.
    coachAudio validator 선례 — 키 화이트리스트 + enum + 상태별 불변식 (T-35J-02):
      · 최상위 키 = RENDERED_COMPARE_KEYS(필수 정확히) + OPTIONAL_KEYS(허용)
      · status ∈ models.RENDERED_COMPARE_STATUSES
      · done → key 는 'results/' prefix + '.mp4' suffix 비어있지 않은 str
        (H-02 — 오염 key 가 doc 에 실리는 것 자체를 차단)
      · failed → key == '' (stale key 잔존 금지) + freezes 금지 (표현물 부재)
      · freezes(UI 라운드) → list[{rid: 비어있지 않은 str, outSec: 유한 수 ≥0}]
        정확 키 집합 + scalar-only (nested 거부 — safetyFlags 선례)
    실패 시 TypeError/ValueError raise (caller 가 graceful 처리).
    """
    if not isinstance(payload, dict):
        raise TypeError(
            f"_validate_rendered_compare: dict 입력만 허용. path={path or '<root>'}, "
            f"got={type(payload).__name__}"
        )
    required = set(models.RENDERED_COMPARE_KEYS)
    allowed = required | set(models.RENDERED_COMPARE_OPTIONAL_KEYS)
    keys = set(payload.keys())
    if not required.issubset(keys) or not keys.issubset(allowed):
        raise ValueError(
            f"{path}: 필수 키 {sorted(required)} + 선택 키 "
            f"{list(models.RENDERED_COMPARE_OPTIONAL_KEYS)} 만 허용. "
            f"got={sorted(keys)}"
        )
    status = payload["status"]
    if status not in models.RENDERED_COMPARE_STATUSES:
        raise ValueError(
            f"{path}.status: {list(models.RENDERED_COMPARE_STATUSES)} 중 하나여야 함. "
            f"got={status!r}"
        )
    key = payload["key"]
    if not isinstance(key, str):
        raise TypeError(f"{path}.key: str 만 허용. got={type(key).__name__}")
    if status == models.RENDERED_COMPARE_STATUS_DONE:
        if not key or not key.startswith("results/") or not key.endswith(".mp4"):
            raise ValueError(
                f"{path}.key: done 은 'results/' prefix + '.mp4' suffix 의 "
                f"비어있지 않은 str 이어야 함 (H-02). got={key!r}"
            )
    else:  # failed
        if key != "":
            raise ValueError(
                f"{path}.key: failed 는 빈 문자열이어야 함 (stale key 잔존 금지). "
                f"got={key!r}"
            )
        if "freezes" in payload:
            raise ValueError(
                f"{path}.freezes: failed 에는 허용 안 됨 (표현물 부재 — done 전용)"
            )
    if "freezes" in payload:
        freezes = payload["freezes"]
        if not isinstance(freezes, list):
            raise TypeError(
                f"{path}.freezes: list 만 허용. got={type(freezes).__name__}"
            )
        for i, item in enumerate(freezes):
            item_path = f"{path}.freezes[{i}]"
            _validate_dict_only_scalars(item, path=item_path)
            if set(item.keys()) != set(models.RENDERED_COMPARE_FREEZE_KEYS):
                raise ValueError(
                    f"{item_path}: 키는 {list(models.RENDERED_COMPARE_FREEZE_KEYS)} "
                    f"정확히여야 함. got={sorted(item.keys())}"
                )
            rid = item["rid"]
            out_sec = item["outSec"]
            if not isinstance(rid, str) or not rid:
                raise ValueError(f"{item_path}.rid: 비어있지 않은 str 이어야 함")
            if not isinstance(out_sec, (int, float)) or isinstance(out_sec, bool) \
                    or not math.isfinite(float(out_sec)) or float(out_sec) < 0:
                raise ValueError(
                    f"{item_path}.outSec: 0 이상 유한 수여야 함. got={out_sec!r}"
                )


def update_analysis_rendered_compare(
    uid: str,
    analysis_id: str,
    key: str,
    status: str,
    freezes: list[dict] | None = None,
) -> None:
    """renderedCompare 사후 부분 업데이트 (Phase 35 quick-260808-jix — coach_audio 뼈대 복제).

    complete_analysis(status='done') **이후** 같은 분석 태스크에서 호출한다. 점수/
    verdict/감점 내역은 이미 확정됐고(D-03 경계), 합성 비교 mp4 는 표현물이라 사후
    도착이 허용된다 (update_analysis_coach_audio 와 동일 규율). `result.renderedCompare`
    **단일 field-path** 만 부분 갱신 — 그 외 어떤 result.* 필드도 사후 변경 금지
    (T-27-18 / D-03).

    검증: `_validate_rendered_compare` (키 화이트리스트 + status enum + done/failed
    별 key 불변식). 명시적 field-path `.update()` 채택 (fault_zoom/coach_audio 선례).

    Args:
      key: done 시 s3keys.build_rendered_compare_key 산출 canonical 키.
        failed 시 빈 문자열 (stale key 잔존 금지).
      status: models.RENDERED_COMPARE_STATUSES 중 하나 (done/failed).
      freezes: done 전용 optional (UI 라운드) — [{rid, outSec}] 정지 틱 데이터.
        None = 필드 생략 (additive — 기존 호출측 무변경).

    Raises:
      ValueError/TypeError: 형상 위반 (_validate_rendered_compare).
    """
    payload = {"status": status, "key": key}
    if freezes is not None:
        payload["freezes"] = list(freezes)
    _validate_rendered_compare(payload)
    _doc(models.analysis_doc_path(uid, analysis_id)).update(
        {
            "result.renderedCompare": payload,
            "updatedAt": int(time.time() * 1000),
        }
    )


def _validate_discovery(payload, *, path: str = "discovery") -> None:  # noqa: ANN001
    """discovery scoped validator (quick-260814-di7 — contract.md §12.10).

    형상: {items: list[{rid, joint, userSec, refSec, pairSrc, text, mp3Key,
    adoptedAt}]}. coachAudio validator 뼈대 복제 — 각 item 을
    `_validate_dict_only_scalars` 로 라우팅해 nested list/dict 를 거부하고
    (Firestore 중첩 배열 금지 정합), 본 validator 는 추가로 강제한다 (T-di7-04):
      · 최상위 키 = models.DISCOVERY_KEYS 정확히 (누락/여분 거부)
      · items = list, 각 item 키 = models.DISCOVERY_ITEM_KEYS 정확히
      · rid/joint/text/adoptedAt 비어있지 않은 str
      · userSec/refSec 유한 수 >= 0
      · pairSrc == models.DISCOVERY_PAIR_SRC (enum — 사칭 라벨 차단)
      · mp3Key 'results/' prefix + '.mp3' suffix
        (s3keys.build_discover_audio_key 단일 출처 — H-02 계열)
      · items 간 mp3Key 중복 거부 (같은 rid+joint 복수 채택 = 키 규약 확장
        의제 — 지금은 fail-closed)
    실패 시 TypeError/ValueError raise (caller 가 graceful 처리).
    """
    if not isinstance(payload, dict):
        raise TypeError(
            f"_validate_discovery: dict 입력만 허용. path={path or '<root>'}, "
            f"got={type(payload).__name__}"
        )
    if set(payload.keys()) != set(models.DISCOVERY_KEYS):
        raise ValueError(
            f"{path}: 키는 {list(models.DISCOVERY_KEYS)} 정확히여야 함. "
            f"got={sorted(payload.keys())}"
        )
    items = payload["items"]
    if not isinstance(items, list):
        raise TypeError(
            f"{path}.items: list 만 허용. got={type(items).__name__}"
        )
    seen_keys: set[str] = set()
    for i, item in enumerate(items):
        item_path = f"{path}.items[{i}]"
        # nested list/dict 거부 — generic validator 라우팅 (본체 무수정).
        _validate_dict_only_scalars(item, path=item_path)
        if set(item.keys()) != set(models.DISCOVERY_ITEM_KEYS):
            raise ValueError(
                f"{item_path}: 키는 {list(models.DISCOVERY_ITEM_KEYS)} 정확히여야 함. "
                f"got={sorted(item.keys())}"
            )
        for field in ("rid", "joint", "text", "adoptedAt"):
            v = item[field]
            if not isinstance(v, str) or not v:
                raise ValueError(f"{item_path}.{field}: 비어있지 않은 str 이어야 함")
        for field in ("userSec", "refSec"):
            v = item[field]
            if not isinstance(v, (int, float)) or isinstance(v, bool) \
                    or not math.isfinite(float(v)) or float(v) < 0:
                raise ValueError(
                    f"{item_path}.{field}: 0 이상 유한 수여야 함. got={v!r}"
                )
        if item["pairSrc"] != models.DISCOVERY_PAIR_SRC:
            raise ValueError(
                f"{item_path}.pairSrc: {models.DISCOVERY_PAIR_SRC!r} 만 허용. "
                f"got={item['pairSrc']!r}"
            )
        mp3_key = item["mp3Key"]
        if not isinstance(mp3_key, str) or not mp3_key.startswith("results/") \
                or not mp3_key.endswith(".mp3"):
            raise ValueError(
                f"{item_path}.mp3Key: 'results/' prefix + '.mp3' suffix 의 str "
                f"이어야 함 (s3keys.build_discover_audio_key 단일 출처). "
                f"got={mp3_key!r}"
            )
        if mp3_key in seen_keys:
            raise ValueError(
                f"{item_path}.mp3Key: items 간 중복 금지 (렌더 basename 조인이 "
                f"모호해짐 — fail-closed). dup={mp3_key!r}"
            )
        seen_keys.add(mp3_key)


def update_analysis_discovery(
    uid: str,
    analysis_id: str,
    items: list[dict],
) -> None:
    """discovery 사후 부분 업데이트 (quick-260814-di7 — coach_audio 뼈대 복제).

    발굴 채택은 분석 **사후** belle 승인 산출물이다 — complete_analysis 무접촉,
    점수/verdict/감점 내역 불변 (T-27-18 / D-03 경계). `result.discovery`
    **단일 field-path** 만 부분 갱신하며 목록은 매번 통째 교체 (merge 의 배열
    병합 모호성 회피 — update_analysis_coach_audio 선례 그대로).

    Args:
      items: [{rid, joint, userSec, refSec, pairSrc, text, mp3Key, adoptedAt}]
        scalar dict 리스트 (models.DISCOVERY_ITEM_KEYS).

    Raises:
      ValueError/TypeError: 형상 위반 (_validate_discovery).
    """
    payload = {"items": list(items or [])}
    _validate_discovery(payload)
    _doc(models.analysis_doc_path(uid, analysis_id)).update(
        {
            "result.discovery": payload,
            "updatedAt": int(time.time() * 1000),
        }
    )


def get_analysis_discovery(uid: str, analysis_id: str) -> list[dict]:
    """`update_analysis_discovery` 의 **read 짝** (quick-260814-ghs).

    발굴 채택은 분석 **사후** belle 승인 산출물이라 어떤 파이프라인 실행에도
    in-memory 근거가 원리적으로 없다 — coachAudio 는 "그 분석이 방금 합성한"
    목록을 손에 쥐고 있지만 discovery 는 그렇지 않다. 따라서 **Firestore 가
    유일 진실**이고, 재분석/재렌더 스테이지는 이 함수로만 조달한다.

    구현이 신규 SDK 표면(field projection / select())을 쓰지 않고 검증된
    `get_analysis` 위에 얹는 이유: analysis doc 은 Firestore 1 MiB 상한이라
    전체 읽기 비용이 유계이고, 프로젝션 도입은 별건 최적화다 (표면 최소).
    `get_analysis` 정의가 이 함수보다 파일 뒤에 있지만 모듈 전역은 **호출
    시점**에 해석되므로 배치는 무해하다.

    Returns:
      items 리스트 (부재 = `[]` — 발굴 없는 절대다수 분석의 정상 경로).

    Raises:
      ValueError/TypeError: 형상 위반 (`_validate_discovery`). **삼키지 않는다**
        — 여기서 조용히 [] 로 흘리면 갭 A 와 같은 침묵이 다시 생긴다. caller
        (렌더 스테이지)가 fail-open + log.warning 으로 graceful 처리한다.
    """
    data = get_analysis(uid, analysis_id) or {}
    payload = (data.get("result") or {}).get("discovery")
    if payload is None:
        return []
    _validate_discovery(payload)
    return list(payload.get("items") or [])


def _validate_spot_check(payload, *, path: str = "spotCheck") -> None:  # noqa: ANN001
    """spotCheck scoped validator (Phase 32 Plan 32-13, D-23 — contract.md §12.8).

    형상: {status, hiddenRecordIds, verdicts, praiseMismatch, model, promptVersion}.
    generic `_validate_dict_only_scalars` 본체 변경 영구 0 — 각 verdict item 을 그
    validator 로 라우팅해 nested list/dict 를 거부하고(coachAudio 선례), 본
    validator 는 키 화이트리스트 + enum + 상한 + 숨김-정합 불변식을 추가 강제한다:
      · 최상위 키 = models.SPOT_CHECK_KEYS 정확히 (누락/여분 거부)
      · status ∈ models.SPOT_CHECK_STATUSES
      · hiddenRecordIds = list[str 비어있지 않음], ≤ SPOT_CHECK_MAX_VERDICTS
      · verdicts = list ≤ SPOT_CHECK_MAX_VERDICTS, 각 item 키 =
        models.SPOT_CHECK_VERDICT_KEYS 정확히, verdict ∈ SPOT_CHECK_VERDICTS,
        reason str ≤ SPOT_CHECK_REASON_MAX_LEN
      · praiseMismatch bool / model·promptVersion 비어있지 않은 str
      · **숨김-정합 불변식 (T-32-30):** hiddenRecordIds 의 모든 id 는 verdicts 에
        verdict='mismatch' 로 존재해야 한다 — 숨김 권한은 명백 불일치 판정에만.
    실패 시 TypeError/ValueError raise (caller 가 graceful 처리).
    """
    if not isinstance(payload, dict):
        raise TypeError(
            f"_validate_spot_check: dict 입력만 허용. path={path or '<root>'}, "
            f"got={type(payload).__name__}"
        )
    if set(payload.keys()) != set(models.SPOT_CHECK_KEYS):
        raise ValueError(
            f"{path}: 키는 {list(models.SPOT_CHECK_KEYS)} 정확히여야 함. "
            f"got={sorted(payload.keys())}"
        )
    status = payload["status"]
    if status not in models.SPOT_CHECK_STATUSES:
        raise ValueError(
            f"{path}.status: {list(models.SPOT_CHECK_STATUSES)} 중 하나여야 함. "
            f"got={status!r}"
        )
    hidden = payload["hiddenRecordIds"]
    if not isinstance(hidden, list):
        raise TypeError(
            f"{path}.hiddenRecordIds: list 만 허용. got={type(hidden).__name__}"
        )
    if len(hidden) > models.SPOT_CHECK_MAX_VERDICTS:
        raise ValueError(
            f"{path}.hiddenRecordIds: {models.SPOT_CHECK_MAX_VERDICTS} 건 초과"
        )
    for i, rid in enumerate(hidden):
        if not isinstance(rid, str) or not rid:
            raise ValueError(
                f"{path}.hiddenRecordIds[{i}]: 비어있지 않은 str 이어야 함"
            )
    verdicts = payload["verdicts"]
    if not isinstance(verdicts, list):
        raise TypeError(
            f"{path}.verdicts: list 만 허용. got={type(verdicts).__name__}"
        )
    if len(verdicts) > models.SPOT_CHECK_MAX_VERDICTS:
        raise ValueError(
            f"{path}.verdicts: {models.SPOT_CHECK_MAX_VERDICTS} 건 초과"
        )
    mismatch_ids: set[str] = set()
    for i, item in enumerate(verdicts):
        item_path = f"{path}.verdicts[{i}]"
        # nested list/dict 거부 — generic validator 라우팅 (본체 무수정).
        _validate_dict_only_scalars(item, path=item_path)
        if set(item.keys()) != set(models.SPOT_CHECK_VERDICT_KEYS):
            raise ValueError(
                f"{item_path}: 키는 {list(models.SPOT_CHECK_VERDICT_KEYS)} "
                f"정확히여야 함. got={sorted(item.keys())}"
            )
        rid = item["recordId"]
        verdict = item["verdict"]
        reason = item["reason"]
        if not isinstance(rid, str) or not rid:
            raise ValueError(f"{item_path}.recordId: 비어있지 않은 str 이어야 함")
        if verdict not in models.SPOT_CHECK_VERDICTS:
            raise ValueError(
                f"{item_path}.verdict: {list(models.SPOT_CHECK_VERDICTS)} 중 "
                f"하나여야 함. got={verdict!r}"
            )
        if not isinstance(reason, str):
            raise ValueError(f"{item_path}.reason: str 이어야 함")
        if len(reason) > models.SPOT_CHECK_REASON_MAX_LEN:
            raise ValueError(
                f"{item_path}.reason: {models.SPOT_CHECK_REASON_MAX_LEN}자 초과"
            )
        if verdict == "mismatch":
            mismatch_ids.add(rid)
    if not isinstance(payload["praiseMismatch"], bool):
        raise TypeError(f"{path}.praiseMismatch: bool 만 허용")
    for key in ("model", "promptVersion"):
        value = payload[key]
        if not isinstance(value, str) or not value:
            raise ValueError(f"{path}.{key}: 비어있지 않은 str 이어야 함")
    # 숨김-정합 불변식 — 숨김은 mismatch verdict 로 뒷받침돼야 함 (T-32-30).
    orphan = [rid for rid in hidden if rid not in mismatch_ids]
    if orphan:
        raise ValueError(
            f"{path}.hiddenRecordIds: mismatch verdict 없는 id {orphan} — "
            "숨김 권한은 명백 불일치 판정에만"
        )


def update_analysis_spot_check(
    uid: str,
    analysis_id: str,
    spot_check: dict,
) -> None:
    """spot_check 사후 부분 업데이트 (Phase 32 Plan 32-13, D-23 — fault_zoom 뼈대 복제).

    complete_analysis(status='done') **이후** 같은 분석 태스크에서 호출한다. 점수/
    verdict/감점 내역은 이미 확정됐고(D-03 경계), 스팟체크 판정은 표시-레이어
    메타라 사후 도착이 허용된다 (update_analysis_fault_zoom 과 동일 규율).
    `result.spotCheck` **단일 field-path** 만 부분 갱신 — 그 외 어떤 result.*
    필드도 사후 변경 금지 (T-27-18 / D-03 / T-32-33).

    검증: `_validate_spot_check` (키 화이트리스트 + status/verdict enum +
    hiddenRecordIds str 검증 + verdicts scalar dict ≤8 + reason ≤120자 +
    숨김-정합 불변식). 판정은 매번 통째 교체이므로 fault_zoom 선례대로 명시적
    field-path `.update()` 채택 (merge 의 배열 병합 모호성 회피).

    Raises:
      ValueError/TypeError: 형상 위반 (_validate_spot_check).
    """
    _validate_spot_check(spot_check)
    _doc(models.analysis_doc_path(uid, analysis_id)).update(
        {
            "result.spotCheck": dict(spot_check),
            "updatedAt": int(time.time() * 1000),
        }
    )


# ─────────────────── Plan 06-03 (2026-06-08, R2 fix round-2) ─────────────
#
# Phase 6 (2026-06-08, Plan 06-03) — D-06-B2 + R2 fix (round-2). mode1 silently
# OFF 차단 (두 canary: reference_profile_missing + reference_source_pose_missing) +
# Phase 14 정은지 reference 등록 helper. 두 필드 atomic merge.

# estimatedHeightScale = torso-relative proportion heuristic (절대 키 아님 —
# 몸통 길이 대비 사지 비율. Phase 2 Task 1 lockstep).
_REF_BODY_PROFILE_REQUIRED: tuple[str, ...] = (
    "estimatedHeightScale",
    "armScale",
    "legScale",
    "torsoScale",
    "shoulderHipRatio",
    "confidence",
    "warnings",
)

_REF_SOURCE_POSE_REQUIRED: tuple[str, ...] = (
    "jointKeys",
    "values",
    "frameIndex",
    "torsoPx",
    "confidence",
    "measuredAt",
)


def update_reference_body_data(
    motion_id: str,
    body_profile: dict,
    source_pose: dict | None = None,
) -> None:
    """R2 fix (2026-06-08 round-2, Plan 06-03). 정은지 reference 의 두 필드
    (bodyNormalizationProfile + bodyComparisonSourcePose) atomic 백필 + Phase 14
    정은지 reference 등록 helper (단일 진입점, D-06-B2). idempotent — 동일 입력 2회
    실행 시 동일 결과. source_pose=None 시 body_profile 만 merge (partial backfill
    허용 — 백필 도중 일부 motion 의 대표 frame 추출 실패 graceful).

    Args:
      motion_id: reference/{motion_id} doc id. 빈 문자열 거부.
      body_profile: BodyNormalizationProfile camelCase dict (7 필수 필드).
      source_pose: BodyComparisonSourcePose camelCase dict (6 필수 필드) 또는 None.
        values 길이 == 4 × len(jointKeys) 강제.

    Raises:
      ValueError: motion_id 빈 / 필수 필드 누락 / values 길이 불일치.
      TypeError: nested-array 위반 (W5 validator 재사용).

    [[firestore-nested-array-flat]] + Plan 06-02 Task 2 validator 정합.
    """
    if not motion_id:
        raise ValueError("motion_id required")

    # body_profile 필수 필드 검증.
    missing_bp = [k for k in _REF_BODY_PROFILE_REQUIRED if k not in body_profile]
    if missing_bp:
        raise ValueError(
            f"body_profile missing required fields: {missing_bp}"
        )
    _validate_flat_dict_no_nested_array(
        body_profile, path="bodyNormalizationProfile"
    )

    # source_pose 검증 — None-aware.
    if source_pose is not None:
        missing_sp = [k for k in _REF_SOURCE_POSE_REQUIRED if k not in source_pose]
        if missing_sp:
            raise ValueError(
                f"source_pose missing required fields: {missing_sp}"
            )
        joint_keys = source_pose["jointKeys"]
        values = source_pose["values"]
        expected_len = 4 * len(joint_keys)
        if len(values) != expected_len:
            raise ValueError(
                f"source_pose.values length must be 4 × len(jointKeys) = "
                f"{expected_len}, got {len(values)}"
            )
        # nested-array gate — values 가 list[float] flat 임을 보장.
        _validate_flat_dict_no_nested_array(
            source_pose, path="bodyComparisonSourcePose"
        )

    now_ms = int(time.time() * 1000)
    payload: dict = {
        "bodyNormalizationProfile": body_profile,
        "bodyNormalizationProfileUpdatedAt": now_ms,
    }
    if source_pose is not None:
        payload["bodyComparisonSourcePose"] = source_pose
        payload["bodyComparisonSourcePoseUpdatedAt"] = now_ms

    _doc(models.reference_motion_path(motion_id)).set(payload, merge=True)

    import logging

    log = logging.getLogger(__name__)
    log.info(
        "update_reference_body_data ok motion_id=%s body_conf=%s "
        "source_pose_present=%s",
        motion_id,
        body_profile.get("confidence"),
        source_pose is not None,
    )


# ── Plan 14-02 (Phase 14) — downstream 4필드 ADD-only merge helper ───────────
#
# meanAngles + techniqueProfile + bodyNormalizationProfile + forceDirectionPattern.
# R3-1 — forceDirectionPattern 만 EXISTING scoped `_validate_force_pattern_inference`
# (firestore_admin.py:343) 로 검증 (findings[].warnings: list[str] 정합 허용); 나머지
# 3개 flat dict (meanAngles / techniqueProfile / bodyNormalizationProfile) 는 generic
# `_validate_flat_dict_no_nested_array`. 이는 result.forcePatternInference (:751-755) 에
# 이미 적용된 sanctioned exception 을 reference mirror path 에 동일 적용하는 것이며,
# project-wide [[firestore-nested-array-flat]] 정책을 약화시키지 않는다. ADD-only —
# joints3d/angles/activeVersion 은 절대 payload 에 포함하지 않는다 (Pitfall 4 / D-02).

# meanAngles 는 JOINT_KEYS → float|None flat dict — 필수 key 강제는 비어있지 않음만.
# techniqueProfile EXTEND surface 필수 key.
_REF_TECHNIQUE_PROFILE_REQUIRED: tuple[str, ...] = (
    "name",
    "category",
    "jointExpectations",
)


def update_reference_downstream_data(
    motion_id: str,
    *,
    mean_angles: dict,
    technique_profile: dict,
    body_normalization_profile: dict,
    force_direction_pattern: dict,
    capture_views: int = 1,
) -> None:
    """Plan 14-02 (Phase 14, D-02 hybrid 백필) — downstream 4필드 atomic ADD-only merge.

    update_reference_body_data 패턴 mirror. R3-1 검증 분기:
      · mean_angles / technique_profile / body_normalization_profile →
        generic `_validate_flat_dict_no_nested_array` (flat scalar / list[scalar]).
      · force_direction_pattern → EXISTING scoped `_validate_force_pattern_inference`
        (firestore_admin.py:343). ForcePatternInference contract 는 top-level
        `warnings: list[str]` + `findings[].warnings: list[str]` (analysis.ts:846)
        를 허용하는데, generic validator 는 finding dict 를 `_validate_dict_only_scalars`
        로 라우팅해 list[str] 를 reject 하므로 VALID forceDirectionPattern 을 거부한다.
        production scoped validator 재사용 (이미 result.forcePatternInference :751-755
        에 적용) → project-wide [[firestore-nested-array-flat]] 약화 없음 (R3-1).

    ADD-only — joints3d/angles/activeVersion 을 절대 payload 에 포함하지 않는다
    (Pitfall 4 / D-02). set(merge=True) + per-field *UpdatedAt. idempotent.

    Raises:
      ValueError: motion_id 빈 / 필수 필드 누락 / forceDirectionPattern scoped 검증 실패.
      TypeError: 3 flat dict 의 nested-array 위반.
    """
    if not motion_id:
        raise ValueError("motion_id required")

    if not mean_angles:
        raise ValueError("mean_angles required (non-empty)")
    missing_tp = [
        k for k in _REF_TECHNIQUE_PROFILE_REQUIRED if k not in technique_profile
    ]
    if missing_tp:
        raise ValueError(
            f"technique_profile missing required fields: {missing_tp}"
        )
    missing_bp = [
        k for k in _REF_BODY_PROFILE_REQUIRED if k not in body_normalization_profile
    ]
    if missing_bp:
        raise ValueError(
            f"body_normalization_profile missing required fields: {missing_bp}"
        )

    # R3-1 — 3 flat dict 은 generic validator, forceDirectionPattern 만 scoped.
    _validate_flat_dict_no_nested_array(mean_angles, path="meanAngles")
    _validate_flat_dict_no_nested_array(technique_profile, path="techniqueProfile")
    _validate_flat_dict_no_nested_array(
        body_normalization_profile, path="bodyNormalizationProfile"
    )
    # forceDirectionPattern → EXISTING scoped validator (findings[].warnings 허용).
    _validate_force_pattern_inference(
        force_direction_pattern, path="forceDirectionPattern"
    )

    now_ms = int(time.time() * 1000)
    payload: dict = {
        "meanAngles": mean_angles,
        "meanAnglesUpdatedAt": now_ms,
        "techniqueProfile": technique_profile,
        "techniqueProfileUpdatedAt": now_ms,
        "bodyNormalizationProfile": body_normalization_profile,
        "bodyNormalizationProfileUpdatedAt": now_ms,
        "forceDirectionPattern": force_direction_pattern,
        "forceDirectionPatternUpdatedAt": now_ms,
        "captureViews": int(capture_views),
        "captureViewsUpdatedAt": now_ms,
    }
    # ADD-only — joints3d/angles/activeVersion 은 절대 포함 X (Pitfall 4 / D-02).
    _doc(models.reference_motion_path(motion_id)).set(payload, merge=True)

    import logging

    log = logging.getLogger(__name__)
    log.info(
        "update_reference_downstream_data ok motion_id=%s body_conf=%s "
        "capture_views=%s force_findings=%s",
        motion_id,
        body_normalization_profile.get("confidence"),
        capture_views,
        len(force_direction_pattern.get("findings") or []),
    )


# ─────────────────── Plan 17-05 — 영역 A reference 자동 등록 helper ──────────
#
# reference/{motion_id} 에 Gemini A 결과 박제. idempotent 박제 — 기존 doc 있으면
# isActive/inactiveReason 보존 (belle 검수 결과 유지), 새 doc 이면 분기 라우팅에
# 따라 isActive 결정. T-17-25 mitigation — 동일 motion_id 재호출 시 belle 검수
# 결과 덮어쓰기 차단.

def set_reference_motion_with_gemini(
    motion_id: str,
    gemini_a: dict,
    *,
    idempotent: bool = True,
) -> None:
    """reference/{motion_id} 에 Gemini A 결과 박제 (idempotent upsert).

    Plan 17-05 박제 정합:
      · 새 doc (exists=False) 면 — geminiA + isActive + inactiveReason 박힘.
        isActive = (routing_branch != 'branch_3_auto'). G3 trigger 시 false.
      · 기존 doc (exists=True) + idempotent=True 면 — geminiA 만 갱신, isActive/
        inactiveReason 은 기존 보존 (belle 검수 결과 유지). G3 trigger 시 inactiveReason
        도 갱신 (G3 발동을 audit 용으로 박는다).
      · idempotent=False 면 — 새 doc 처럼 isActive/inactiveReason 강제 갱신.

    Args:
      motion_id: Firestore reference doc id. 빈 string reject.
      gemini_a: extract_reference_metadata 결과 dict. routing_branch /
        inactive_reason / motion_name_ipsf / clip_range / checkpoint_joints /
        confidence / model / registered_at / raw_response 박힘.
      idempotent: True (default) = 기존 doc 의 isActive/inactiveReason 보존.

    Raises:
      ValueError: motion_id 빈 / gemini_a 빈 / routing_branch 박혀있지 X.
    """
    if not motion_id:
        raise ValueError("motion_id required")
    if not gemini_a:
        raise ValueError("gemini_a required")
    routing_branch = gemini_a.get("routing_branch")
    if not routing_branch:
        raise ValueError("gemini_a.routing_branch required")

    doc = _doc(models.reference_motion_path(motion_id))
    snap = doc.get()
    exists = snap.exists if snap else False

    now_ms = int(time.time() * 1000)
    is_g3 = routing_branch == "branch_3_auto"

    payload: dict = {
        "motionId": motion_id,
        "geminiA": gemini_a,
        "geminiAUpdatedAt": now_ms,
    }

    if not exists or not idempotent:
        # 새 doc 또는 force override — 분기 라우팅에 따라 isActive/inactiveReason 결정.
        payload["isActive"] = not is_g3
        payload["inactiveReason"] = (
            gemini_a.get("inactive_reason") if is_g3 else None
        )
    else:
        # 기존 doc + idempotent — belle 검수 결과 보존.
        existing = snap.to_dict() or {}
        # G3 trigger 시 inactiveReason 만 audit 박제 (isActive 는 기존 보존).
        if is_g3:
            payload["inactiveReason"] = gemini_a.get("inactive_reason")
        # isActive 는 기존 값 그대로 박는다 (merge=True 가 미박제 필드 보존).
        if "isActive" in existing:
            payload["isActive"] = existing["isActive"]

    doc.set(payload, merge=True)

    import logging

    log = logging.getLogger(__name__)
    log.info(
        "set_reference_motion_with_gemini ok motion_id=%s routing_branch=%s "
        "exists=%s is_active=%s",
        motion_id,
        routing_branch,
        exists,
        payload.get("isActive"),
    )


def fail_analysis(uid: str, analysis_id: str, code: str, message: str) -> None:
    """status='failed' + error{code,message} (contract.md §5)."""
    _doc(models.analysis_doc_path(uid, analysis_id)).set(
        {
            "status": models.STATUS_FAILED,
            "error": {"code": code, "message": message},
            "updatedAt": int(time.time() * 1000),
        },
        merge=True,
    )


def list_reference_motions() -> list[dict]:
    """reference 컬렉션 전체 (기준 모션 선택 화면 #9). 읽기 전용."""
    col = _db().collection(models.REFERENCE_MOTIONS_COLLECTION)
    out: list[dict] = []
    for snap in col.stream():
        data = snap.to_dict() or {}
        data.setdefault("motionId", snap.id)
        out.append(data)
    return out


def get_analysis(uid: str, analysis_id: str) -> dict | None:
    """앱이 만든 분석 문서 읽기 (mode, referenceMotionId, fileName 등)."""
    snap = _doc(models.analysis_doc_path(uid, analysis_id)).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    data.setdefault("analysisId", analysis_id)
    return data


# ─── 33-17: shadow-reference resolver + 전역 release 포인터 (codex concern 3 / suggestion 7) ───

# reference/_release.activeCandidate = 단일 authoritative 활성 candidate 버전.
# 활성화는 이 포인터 1회 write 로 원자적으로 이뤄진다 (reprocess 스크립트 _flip_active_pointer).
_RELEASE_POINTER_PATH = "reference/_release"
_RELEASE_POINTER_FIELD = "activeCandidate"

# eval 이 production top-level 을 flip 하지 않고 candidate 버전을 소비하도록 하는 shadow env.
# run_sweep.py / verify_self_comparison.py 의 --reference-version 이 in-process 로 세팅한다.
_SHADOW_REFERENCE_ENV = "SUNITY_SHADOW_REFERENCE_VERSION"

# 후속 파이프라인이 소비하는 candidate consumer 필드 (top-level meta 위에 overlay).
_REFERENCE_CONSUMER_FIELDS = (
    "angles", "anglesJointKeys", "anglesFrames",
    "joints3d", "joints3dKeys", "joints3dFrames",
    "coordDim", "space",
    "keypointReport",
    "pipelineVersion", "reprocessedAt",
)


def _angles_content_hash(angles) -> str:
    """소비된 angles 의 content hash (8 hex). 어떤 candidate 를 읽었는지 증명 (concern 3)."""
    import hashlib

    blob = repr(angles).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:8]


def get_reference_motion(motion_id: str) -> dict | None:
    """기준 모션 1건. keyframe 각도 데이터(angles) + 메타 포함(ml_CLAUDE.md 등록).

    33-17 해석 순서 (codex concern 3 / suggestion 7):
      (1) SUNITY_SHADOW_REFERENCE_VERSION 이 세팅되면 reference/{id}/versions/{v} 를 읽어
          consumer 필드를 top-level meta 위에 overlay 하고, version+anglesHash 를 로깅한다.
          top-level 문서는 절대 write 하지 않는다 (read-only — eval 이 production 을 안 건드림).
      (2) 아니면 reference/_release.activeCandidate (전역 포인터) 로 해석 —
          reference/{id}/versions/{activeCandidate} 를 읽는다.
      (3) 둘 다 없으면 기존 top-level 읽기 (하위호환).
    """
    import logging
    import os

    log = logging.getLogger(__name__)

    base_snap = _doc(models.reference_motion_path(motion_id)).get()
    base = base_snap.to_dict() if base_snap.exists else None

    # 해석할 candidate version 결정 (shadow env → 전역 포인터 → None).
    shadow = os.environ.get(_SHADOW_REFERENCE_ENV)
    resolved_version = None
    source = None
    if shadow:
        resolved_version = shadow
        source = "shadow_env"
    else:
        release_snap = _doc(_RELEASE_POINTER_PATH).get()
        if release_snap.exists:
            rel = release_snap.to_dict() or {}
            if rel.get(_RELEASE_POINTER_FIELD):
                resolved_version = rel[_RELEASE_POINTER_FIELD]
                source = "release_pointer"

    if resolved_version:
        vsnap = _doc(
            f"{models.REFERENCE_MOTIONS_COLLECTION}/{motion_id}/versions/{resolved_version}"
        ).get()
        if vsnap.exists:
            overlay = vsnap.to_dict() or {}
            merged = dict(base or {})
            for k in _REFERENCE_CONSUMER_FIELDS:
                if k in overlay:
                    merged[k] = overlay[k]
            merged.setdefault("motionId", motion_id)
            log.info(
                "resolved shadow reference %s version=%s anglesHash=%s source=%s",
                motion_id, resolved_version,
                _angles_content_hash(overlay.get("angles")), source,
            )
            return merged
        # candidate 버전 문서가 없으면 안전하게 top-level 로 폴백 (조용한 무효화 방지 로깅).
        log.warning(
            "reference %s: resolved version=%s (source=%s) 문서 부재 → top-level 폴백",
            motion_id, resolved_version, source,
        )

    if base is None:
        return None
    base.setdefault("motionId", motion_id)
    return base


def get_previous_analysis(
    uid: str, current_id: str, mode: str | None = None
) -> dict | None:
    """Mode3 비교용: 가장 최근 완료(done) 분석 1건 (현재 건 제외).

    박제 (2026-06-07 belle): mode 인자 박제. mode3 first 판정 시 mode1 (정은지)
    분석을 prev 로 잡는 함정 fix — belle 의 mode3 첫 시도가 직전 mode1 분석을
    prev 로 잡아 second+ 처리됨. mode 박제 = "같은 mode" 박제 안에서만 prev 검색.

    박제 함정 (2026-06-07): mode + status + createdAt 박제 composite index
    Firestore 자동 생성 X. query 박제 status + createdAt 만 (기존 index 박제)
    in-memory filter 박제 mode 박제.
    """
    from firebase_admin import firestore

    col = _db().collection(f"users/{uid}/analyses")
    q = (
        col.where("status", "==", models.STATUS_DONE)
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .limit(20)  # mode filter 박제 충분 박제
    )
    for snap in q.stream():
        if snap.id == current_id:
            continue
        data = snap.to_dict() or {}
        if mode is not None and data.get("mode") != mode:
            continue  # in-memory filter
        data.setdefault("analysisId", snap.id)
        return data
    return None


# ─────────────────── Plan 5-02 (2026-06-04) Gemini 캡싱 helper ───────────────────
#
# D-14 박제 — 영상 hash 캡싱 (gemini_cache/{hash} top-level 전역 공유).
# D-09 case 3 박제 — TERM-DATA-01 분기 3 자동 수집 (term_collection/{keyword}).
# [[firestore-nested-array-flat]] 정합 — moments[i] flat dict array 강제.
# D-16 lazy import — firebase_admin.firestore 는 record_unregistered_keyword
# 안에서만 import (Increment / ArrayUnion 만 필요).

_GEMINI_CACHE_COLLECTION = "gemini_cache"  # top-level, uid 비의존 전역 공유
_TERM_COLLECTION = "term_collection"  # TERM-DATA-01 분기 3 자동 수집 (D-09 case 3)


def get_gemini_cache(video_hash: str) -> dict | None:
    """gemini_cache/{hash} document → dict 또는 None.

    Plan 5-02 박제. TechniqueCache.lookup 가 호출.
    """
    snap = _doc(f"{_GEMINI_CACHE_COLLECTION}/{video_hash}").get()
    if not snap.exists:
        return None
    return snap.to_dict() or None


def store_gemini_cache(video_hash: str, payload: dict) -> None:
    """gemini_cache/{hash} document 박제. video_hash + timestamps 자동 추가.

    Plan 5-02 박제. TechniqueCache.store 가 호출.

    [[firestore-nested-array-flat]] 정합 — moments entry 가 flat dict 아니거나
    value 가 list/tuple 이면 TypeError raise (Firestore crash 1차 차단선).

    timestamps 박제:
      · created_at — payload 에 이미 있으면 보존 (재박제 시 첫 박제 시각 유지)
      · updated_at — 항상 현재 시각 박제

    Raises:
      TypeError: moments entry 가 flat dict 아님 또는 value 가 list/tuple.
    """
    # nested-array 정합 검증 ([[firestore-nested-array-flat]])
    if "moments" in payload and payload["moments"]:
        for i, m in enumerate(payload["moments"]):
            if not isinstance(m, dict):
                raise TypeError(
                    f"moments[{i}] must be flat dict "
                    f"(firestore-nested-array-flat): got {type(m).__name__}"
                )
            for k, v in m.items():
                if isinstance(v, (list, tuple)):
                    raise TypeError(
                        f"moments[{i}][{k}] must be scalar "
                        f"(firestore nested array 금지): got {type(v).__name__}"
                    )

    now_ms = int(time.time() * 1000)
    doc = {
        **payload,
        "video_hash": video_hash,
        "created_at": payload.get("created_at", now_ms),
        "updated_at": now_ms,
    }
    _doc(f"{_GEMINI_CACHE_COLLECTION}/{video_hash}").set(doc)


def record_unregistered_keyword(keyword: str, *, uid: str, video_hash: str) -> None:
    """TERM-DATA-01 분기 3 자동 수집 트리거 (D-09 case 3 — Plan 5-02 박제).

    Phase 16 TERM-DATA-01 schema 정합 (uid 익명 + 누적 카운트):
      · keyword: 박제 keyword string
      · count: Increment(1) — 호출마다 +1
      · unique_users: ArrayUnion([uid]) — set 정합 (같은 uid 멱등)
      · last_video_hash: 마지막 박제 영상 hash
      · promotion_status: "pending" (Phase 16 16-AUTOCOLLECT-SCHEMA 박제 워크플로:
        pending → reviewing → approved)
      · created_at / updated_at: ms timestamps

    UI 카피 TERM-COPY-01 = Phase 12 책임 (본 helper = 데이터 트리거만).

    멱등: 같은 (keyword, uid) 재호출 시 unique_users set 박제 = 1 (중복 무시).
    """
    from firebase_admin import firestore as _firestore  # lazy import (D-16)

    ref = _doc(f"{_TERM_COLLECTION}/{keyword}")
    now_ms = int(time.time() * 1000)
    ref.set(
        {
            "keyword": keyword,
            "count": _firestore.Increment(1),
            "unique_users": _firestore.ArrayUnion([uid]),
            "last_video_hash": video_hash,
            "updated_at": now_ms,
            "created_at": now_ms,  # set merge=True 가 첫 박제만 사용
            "promotion_status": "pending",  # Phase 16 schema 박제 정합
        },
        merge=True,
    )


# ─────────────────── Plan 22-03 (Phase 22) — Gemini shadow 로깅 helper ──────────
#
# D-10c — 프로덕션 판정 로그가 그대로 증류 라벨로 적재됨 (shadow 로깅 즉시 시작).
# D-13 — 같은 입력을 Gemini/자체 모델 양쪽에 태워 역할별(veto/recognizer/coach)
#        verdict 비교 로그를 축적, 게이트 통과 시 swap.
# D-12 — shadow 로그에 사용자 식별자 금지. analysis 참조는 video_hash 로만
#        (T-22-07 mitigation). 아래 PII 키 거부 목록이 이를 강제한다.
# [[firestore-nested-array-flat]] — nested array 저장 전 차단(기존 W5 validator 재사용).
#   대형 (T,J) 배열은 반드시 flat list 로 넣어야 하며, index-entry 40k 한도에 걸리는
#   경우 index 면제가 필요하다 ([[firestore-index-entry-limit]]).

_VLM_SHADOW_COLLECTION = "vlm_shadow"  # top-level, gemini_cache 형제 (uid 비의존)
_VLM_SHADOW_ROLES: frozenset[str] = frozenset({"veto", "recognizer", "coach"})

# D-12 — shadow 로그에서 거부하는 PII/식별자 키 (normalize 후 정확 매칭).
# normalize = lowercase + 영숫자만 → "userId"/"user_id" 등 표기 변형 흡수.
# 정확 매칭이라 도메인 키(motionName→"motionname", jointName→"jointname")는
# 오탐 없이 통과한다. 화이트리스트로 전 측정 스칼라를 열거하는 것은 비현실적이므로
# (open-ended domain scalars), 실제 불변식("사용자 식별자 금지")을 거부 목록으로 강제.
_VLM_SHADOW_PII_KEYS: frozenset[str] = frozenset(
    {
        "uid",
        "userid",
        "username",
        "email",
        "mail",
        "name",
        "displayname",
        "fullname",
        "firstname",
        "lastname",
        "nickname",
        "phone",
        "phonenumber",
        "mobile",
        "address",
        "ip",
        "ipaddress",
        "deviceid",
        "sessionid",
        "authtoken",
        "accesstoken",
        "idtoken",
        "analysisid",
        "birthdate",
        "dob",
        "ssn",
    }
)


def _normalize_pii_key(key: str) -> str:
    """PII 키 매칭용 정규화 — 소문자 + 영숫자만 (표기 변형 흡수)."""
    return "".join(ch for ch in key.lower() if ch.isalnum())


def _reject_pii_keys(payload, *, path: str) -> None:
    """D-12 — shadow payload 안 PII/식별자 키를 재귀 거부 (T-22-07 mitigation).

    dict 는 각 key 를 normalize 해 `_VLM_SHADOW_PII_KEYS` 와 정확 매칭, 매치 시
    ValueError. 값이 dict/list 면 재귀 순회해 중첩 식별자도 잡는다. analysis 참조는
    video_hash 로만 해야 하므로 uid/email/analysisId 등은 저장 전에 차단된다.

    Raises:
      ValueError: PII/식별자 키 발견 시 (path 정보 포함).
    """
    if isinstance(payload, dict):
        for k, v in payload.items():
            if isinstance(k, str) and _normalize_pii_key(k) in _VLM_SHADOW_PII_KEYS:
                raise ValueError(
                    f"{path}.{k} 는 PII/식별자 키 — shadow 로그 저장 금지 "
                    f"(D-12; analysis 참조는 video_hash 로만)"
                )
            sub = f"{path}.{k}" if isinstance(k, str) else f"{path}.<key>"
            _reject_pii_keys(v, path=sub)
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            _reject_pii_keys(item, path=f"{path}[{i}]")


def store_vlm_shadow(video_hash: str, role: str, payload: dict) -> None:
    """vlm_shadow/{video_hash} 에 역할별 Gemini 판정을 복제 저장 (D-10c / D-13).

    Plan 22-03 Task 1. pipeline 이 veto verdict / recognizer 프로파일 / coach 출력을
    소비하는 지점에서 재호출 0 으로 복제 저장한다(Task 2 배선). 본 helper 는 Firestore
    규율(flat / ms epoch / merge / PII 금지)을 강제하는 단일 진입점이다.

    문서 구조:
      { video_hash, created_at, updated_at, roles: { veto: {...}, recognizer: {...},
        coach: {...} } }
    set(merge=True) 의 nested-map deep merge 로 role 별 누적 — 다른 role 데이터 미파괴.
    created_at 은 첫 기록만 남기고(선행 doc.get() 으로 보존, set_reference_motion_with_gemini
    선례), updated_at 은 매 호출 ms epoch 로 갱신.

    검증 순서(저장 전):
      1. video_hash 빈 값 / role 미등재 → ValueError.
      2. D-12 PII 키 재귀 거부 → ValueError (T-22-07).
      3. [[firestore-nested-array-flat]] nested array 사전 차단 → TypeError
         (기존 `_validate_flat_dict_no_nested_array` 재사용). 대형 (T,J) 배열은
         flat list 로 전달해야 하며 index 면제 필요 시 [[firestore-index-entry-limit]].

    Raises:
      ValueError: video_hash 빈 / role 미등재 / PII 키 포함.
      TypeError:  payload dict 아님 / nested array 포함.
    """
    if not video_hash:
        raise ValueError("video_hash required")
    if role not in _VLM_SHADOW_ROLES:
        raise ValueError(
            f"role must be one of {sorted(_VLM_SHADOW_ROLES)}: got {role!r}"
        )
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise TypeError(f"payload must be dict: got {type(payload).__name__}")

    # D-12 — PII/식별자 키 거부 (저장 전, T-22-07 mitigation).
    _reject_pii_keys(payload, path=f"roles.{role}")
    # [[firestore-nested-array-flat]] — nested array 사전 차단 (기존 W5 validator 재사용).
    _validate_flat_dict_no_nested_array(payload, path=f"roles.{role}")

    now_ms = int(time.time() * 1000)
    ref = _doc(f"{_VLM_SHADOW_COLLECTION}/{video_hash}")

    # created_at 첫 기록 보존 — 선행 read 로 기존 시각 유지 (재호출에도 불변).
    snap = ref.get()
    created_at = now_ms
    if snap is not None and getattr(snap, "exists", False):
        existing = snap.to_dict() or {}
        created_at = existing.get("created_at", now_ms)

    ref.set(
        {
            "video_hash": video_hash,
            "created_at": created_at,
            "updated_at": now_ms,
            "roles": {role: payload},
        },
        merge=True,
    )


# ══════════════════════ Phase 31: visual job 데이터 계약 ══════════════════════
#
# 근거: 31-02-PLAN + 외부 리뷰 3~11차.
#   B3-01 outbox instance / B3-02 원자 finalize / B3-03 reserve
#   B4-01 outboxSeq CAS / B4-03 retry_ready
#   B5-01 claim 4상태 + owner/lease CAS / H5-03 fresh requestKey / H5-06 durable cursor
#   B6-01 새 seq claim clear / B6-04 cleanup_blocked 비-terminal / H6-01 sent-recovery 필터
#   B7-03 cleanup_verified_at_ms 파라미터 병합
#   B8-01 begin_visual_job_create / B8-02 unconditional privacy gate / B8-03 blocker clear
#   B8-05 create-only reservation / B8-06 reservation claim 배타
#   B9-01 janitor claim lease 복구 / B9-02 cross-reservation ownership / H9-04 nested tx 금지
#   B10-01~03 self-ref 소비 / active|deleting fence / ref release
#   B11-01 deleting 은 항상 acquire fence + commit_key_delete fencing token
#   B11-04 job ref 는 expireAt 무시 — 항상 live
#
# 핵심 불변식 3개:
#   1. 모든 nonterminal 전이는 단일 transaction 으로 {state 검증 + 다음 state + nextAction
#      + dispatchState='pending' + nextDispatchAtMs + 새 outboxSeq + claim clear} 를 원자
#      기록하고 **갱신된 snapshot 을 반환**한다. 후속 단계는 이 snapshot 만 쓴다 —
#      인바운드 SQS 메시지 값을 재사용하지 않는다.
#   2. 외부 side-effect 는 claim_visual_job_action() 이 'claimed' 를 준 뒤에만 나간다.
#      'busy' 는 정상 ACK 금지(batchItemFailures) — 그래야 SQS 중복 전달이 유료 action 을
#      두 번 실행하지 않는다.
#   3. terminal 종결은 finalize_visual_job() 하나뿐이다. job terminal 과 analysis 표시
#      상태가 같은 multi-document transaction 이라 둘이 영구 불일치할 수 없다.


# ── Firestore seam (테스트가 in-memory 로 교체하는 지점) ────────────────────
#
# 본 모듈의 기존 함수들은 `_doc()` 만 쓰지만 visual job 계약은 transaction/query 가
# 필수다. 아래 4개를 얇은 seam 으로 분리해 두면 backend/tests/phase31/conftest.py 의
# FakeFirestore 가 **실제 optimistic concurrency 를 재현**하며 CAS 를 검증할 수 있다
# (mock 이 통과시켜 주는 게 아니라 진짜 conflict/재시도가 난다).


def _collection(name: str):
    return _db().collection(name)


def _field_filter(field: str, op: str, value):
    """where(filter=FieldFilter(...)) — positional where 는 deprecated."""
    from google.cloud.firestore_v1.base_query import FieldFilter

    return FieldFilter(field, op, value)


def _query_start_after_name(query, collection_name: str, doc_id: str):
    """__name__ 정렬 cursor. dict cursor 의 __name__ 은 DocumentReference 를 요구한다.

    추가 read 없이 ref 만 만들어 넘긴다(cursor 용 get() 은 낭비).
    """
    return query.start_after({"__name__": _doc(f"{collection_name}/{doc_id}")})


def _run_in_transaction(fn):
    """fn(transaction) 을 Firestore transaction 으로 실행. 충돌 시 SDK 가 재시도한다."""
    from firebase_admin import firestore

    return firestore.transactional(fn)(_db().transaction())


def _now_ms() -> int:
    return int(time.time() * 1000)


def _as_ts(ms: int):
    """Firestore TTL policy 대상 expireAt — **timestamp 타입** 필수 (10차 H10-02).

    millisecond number 로 저장하면 TTL policy 가 문서를 영영 지우지 않는다.
    """
    import datetime

    return datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc)


_VISUAL_JOBS_COLLECTION = "visualJobs"


def _snap_dict(snap) -> dict | None:
    if snap is None or not getattr(snap, "exists", False):
        return None
    return snap.to_dict() or {}


# ═══════════════ (10) key-level ownership — active|deleting delete fence ═══════════════
#
# "참조 수를 세고 0이면 지운다" 는 **세고 나서 지우기 직전에 producer 가 acquire 하는**
# 창이 남는다 (T-31-90). key 마다 문서를 두고 2상태 fence 를 건다.


def _object_ref(bucket: str, key: str):
    return _doc(models.visual_input_object_doc_path(bucket, key))


def _is_live_ref(entry: dict, now_ms: int) -> bool:
    """job ref 는 **항상 live** (11차 B11-04).

    job ref 에 expireAt 만료를 적용하면 살아있는 nonterminal job 의 입력을 janitor 가
    지운다 (T-31-94). job ref 는 worker/reconciler 의 explicit release 로만 사라진다.
    reservation ref 만 expireAt 만료 판정 대상이다.
    """
    if entry.get("kind") == "job":
        return True
    return int(entry.get("expireAt") or 0) > now_ms


def live_ref_count(bucket: str, key: str, *, now_ms: int) -> int:
    """진단/테스트용 — live ref 수. 삭제 판정은 claim_key_for_delete 만 한다."""
    data = _snap_dict(_object_ref(bucket, key).get()) or {}
    refs = data.get("refs") or {}
    return sum(1 for e in refs.values() if _is_live_ref(e, now_ms))


def acquire_key_ownership(
    bucket: str,
    key: str,
    *,
    ref: str,
    kind: str,
    now_ms: int,
    expire_at_ms: int | None = None,
) -> bool:
    """producer 가 PUT/재사용 **전** 호출. 성공(True) 해야만 S3 에 손댄다.

    **state=='deleting' 이면 lease 만료 여부와 무관하게 항상 False** (11차 B11-01).
    만료된 deleting 을 producer 가 active 로 회수하면, 그 사이 살아 돌아온 이전 janitor 의
    늦은 DeleteObject 가 방금 올린 입력을 지운다 (T-31-93). 만료 deleting 회수는
    janitor 전용이고, janitor 는 commit_key_delete 로 한 번 더 fencing 된다.

    Args:
      ref: ref id — reservation id 또는 job id.
      kind: models.VISUAL_OBJECT_REF_KINDS ('reservation' | 'job').
      expire_at_ms: reservation ref 전용 만료. job ref 는 무시된다(항상 live).
    """
    if kind not in models.VISUAL_OBJECT_REF_KINDS:
        raise ValueError(f"kind must be one of {list(models.VISUAL_OBJECT_REF_KINDS)}")

    def _tx(transaction):
        obj = _object_ref(bucket, key)
        data = _snap_dict(obj.get(transaction=transaction))
        if data is None:
            transaction.set(
                obj,
                {
                    "bucket": bucket,
                    "key": key,
                    "state": "active",
                    "refs": {
                        ref: {
                            "kind": kind,
                            "generation": 0,
                            "expireAt": int(expire_at_ms or 0),
                        }
                    },
                    "deleteOwner": None,
                    "deleteLeaseExpiresAt": 0,
                    "generation": 0,
                    "updatedAtMs": now_ms,
                },
            )
            return True
        if data.get("state") == "deleting":
            return False  # B11-01 — 만료여도 회수 금지.
        refs = dict(data.get("refs") or {})
        refs[ref] = {
            "kind": kind,
            "generation": int(data.get("generation") or 0),
            "expireAt": int(expire_at_ms or 0),
        }
        transaction.update(obj, {"refs": refs, "updatedAtMs": now_ms})
        return True

    return _run_in_transaction(_tx)


def _promote_key_ownership_to_job_tx(
    transaction,
    bucket: str,
    key: str,
    *,
    reservation_ref: str,
    job_ref: str,
    snapshot: dict | None = None,
    now_ms: int | None = None,
) -> bool:
    """reserve transaction 안에서 reservation ref → job ref 원자 교체 (10차 H10-01).

    nested @transactional 금지 (9차 H9-04) — transaction 객체를 인자로 받는다. 여러 key
    를 승격할 때 전부 이전 또는 전부 승격만 허용되도록 **같은 transaction** 을 공유한다.

    **job ref 는 expireAt 을 설정하지 않는다 — 항상 live** (11차 B11-04). reservation 의
    만료를 job ref 로 복사하면 살아있는 job 의 입력이 만료로 삭제 가능해진다.

    Args:
      snapshot: read-all-before-write 를 위해 호출측이 미리 읽어둔 문서. 주면 read 를
        건너뛰고 write 만 버퍼링한다.
    """
    obj = _object_ref(bucket, key)
    data = snapshot if snapshot is not None else _snap_dict(obj.get(transaction=transaction))
    if data is None or data.get("state") == "deleting":
        return False
    refs = dict(data.get("refs") or {})
    refs.pop(reservation_ref, None)
    refs[job_ref] = {
        "kind": "job",
        "generation": int(data.get("generation") or 0),
        # expireAt 없음 — B11-04.
    }
    transaction.update(obj, {"refs": refs, "updatedAtMs": now_ms or _now_ms()})
    return True


def release_key_ownership(bucket: str, key: str, *, ref: str) -> None:
    """ref 제거. refs 가 비고 deleting 이 아니면 ownership 문서 자체를 지운다.

    종료 경로(worker cleanup / producer 보상 / reservation·orphan close)의 **필수 부분**
    이다 (10차 B10-03). 빠뜨리면 ownership 문서가 영구 잔존해 이후 그 key 의 cleanup 이
    영원히 skip 된다 (T-31-91).
    """

    def _tx(transaction):
        obj = _object_ref(bucket, key)
        data = _snap_dict(obj.get(transaction=transaction))
        if data is None:
            return
        refs = dict(data.get("refs") or {})
        refs.pop(ref, None)
        if not refs and data.get("state") != "deleting":
            transaction.delete(obj)
            return
        transaction.update(obj, {"refs": refs, "updatedAtMs": _now_ms()})

    _run_in_transaction(_tx)


def claim_key_for_delete(
    bucket: str,
    key: str,
    *,
    deleting_ref: str,
    owner: str,
    lease_ms: int,
    now_ms: int,
) -> dict | None:
    """외부 delete 권한 획득. 성공 시 fencing token, 실패(다른 live ref 존재) 시 None.

    순서가 중요하다 (10차 B10-01):
      (a) refs 에서 **자기 ref 를 먼저 소비**한다. 이걸 안 하면 자기 자신을 live ref 로
          세어 삭제가 영원히 멈춘다 (T-31-89 self-ref liveness 붕괴).
      (b) 남은 refs 중 live 판정 — job ref 는 항상 live, reservation ref 만 expireAt.
      (c) live 0 이면 state='deleting' + generation+1 CAS 후 token 반환.

    반환 token 은 **외부 DeleteObject 직전** commit_key_delete 로 재검증해야 한다.
    """

    def _tx(transaction):
        obj = _object_ref(bucket, key)
        data = _snap_dict(obj.get(transaction=transaction))
        if data is None:
            return None
        state = data.get("state") or "active"
        cur_owner = data.get("deleteOwner")
        lease_exp = int(data.get("deleteLeaseExpiresAt") or 0)
        if state == "deleting" and lease_exp > now_ms and cur_owner != owner:
            return None  # 다른 janitor 가 유효 lease 보유.

        refs = dict(data.get("refs") or {})
        refs.pop(deleting_ref, None)  # (a) 자기 ref 소비 — B10-01.
        if any(_is_live_ref(e, now_ms) for e in refs.values()):  # (b)
            # 다른 live ref 존재 → 삭제 불가. 자기 ref 소비는 확정한다.
            transaction.update(obj, {"refs": refs, "updatedAtMs": now_ms})
            return None
        generation = int(data.get("generation") or 0) + 1  # (c) fencing token.
        transaction.update(
            obj,
            {
                "refs": refs,
                "state": "deleting",
                "deleteOwner": owner,
                "deleteLeaseExpiresAt": now_ms + int(lease_ms),
                "generation": generation,
                "updatedAtMs": now_ms,
            },
        )
        return {
            "owner": owner,
            "generation": generation,
            "leaseExpiresAt": now_ms + int(lease_ms),
        }

    return _run_in_transaction(_tx)


def commit_key_delete(bucket: str, key: str, *, token: dict, now_ms: int) -> bool:
    """외부 DeleteObject **직전** fencing 재검증 (11차 B11-01).

    state=='deleting' AND deleteOwner==token.owner AND generation==token.generation AND
    미만료 lease 를 전부 통과해야 True. lease 만료 뒤 되살아난 이전 claimant 는
    generation 이 이미 올라가 있어 여기서 차단된다 — lease 길이가 아니라 이 generation
    비교가 실제 방어다.
    """

    def _tx(transaction):
        data = _snap_dict(_object_ref(bucket, key).get(transaction=transaction))
        if data is None:
            return False
        return bool(
            data.get("state") == "deleting"
            and data.get("deleteOwner") == token.get("owner")
            and int(data.get("generation") or 0) == int(token.get("generation"))
            and int(data.get("deleteLeaseExpiresAt") or 0) > now_ms
        )

    return _run_in_transaction(_tx)


# ═══════════════ (8) per-invocation upload reservation ═══════════════
#
# 임시 생체 프레임 privacy SLA = "즉시 삭제(하드 크래시에도 보장)" 는 belle 확정 축이다
# (31-CONTEXT SETTLED AXES) — 24h lifecycle 로 대체하지 않는다. producer 는 PUT 전에
# per-invocation **immutable** reservation 을 만들고, janitor 는 그 reservation 을
# claim 한 뒤에만 삭제한다. reserve_visual_job 과 janitor 의 claim 이 **배타 CAS** 라
# "janitor 가 확인 → producer 가 reserve → janitor 가 삭제" 순열이 성립하지 않는다.


def _reservation_ref(job_id: str, reservation_id: str):
    return _doc(models.visual_input_reservation_doc_path(job_id, reservation_id))


def create_input_reservation(
    job_id: str,
    reservation_id: str,
    *,
    owner: str,
    bucket: str,
    source_hash: str,
    expected_keys,
    now_ms: int,
    ttl_ms: int | None = None,
) -> dict:
    """create-only precondition (8차 B8-05). 이미 있으면 **덮어쓰지 않고** 기존 반환.

    per-invocation immutable 이라 동시 producer 가 서로의 reservation 을 덮어써
    expectedKeys 를 잃는 일이 없다 (T-31-88).
    """
    ttl = int(ttl_ms if ttl_ms is not None else models.VISUAL_INPUT_RESERVATION_TTL_MS)

    def _tx(transaction):
        ref = _reservation_ref(job_id, reservation_id)
        existing = _snap_dict(ref.get(transaction=transaction))
        if existing is not None:
            return existing
        payload = {
            "jobId": job_id,
            "reservationId": reservation_id,
            "owner": owner,
            "bucket": bucket,
            "sourceHash": source_hash,
            "expectedKeys": list(expected_keys or []),
            "createdKeys": [],
            "state": "open",
            "leaseExpiresAt": now_ms + ttl,
            "claimOwner": None,
            "claimLeaseExpiresAt": 0,
            "claimAttempt": 0,
            "createdAtMs": now_ms,
        }
        transaction.set(ref, payload)
        return payload

    return _run_in_transaction(_tx)


def record_reservation_keys(
    job_id: str, reservation_id: str, *, created_keys, owner: str
) -> bool:
    """실제 PUT 한 key 기록. owner CAS — 남의 reservation 을 오염시키지 못한다."""

    def _tx(transaction):
        ref = _reservation_ref(job_id, reservation_id)
        data = _snap_dict(ref.get(transaction=transaction))
        if data is None or data.get("owner") != owner:
            return False
        merged = list(dict.fromkeys(list(data.get("createdKeys") or []) + list(created_keys or [])))
        transaction.update(ref, {"createdKeys": merged})
        return True

    return _run_in_transaction(_tx)


def reservation_keys(data: dict) -> list:
    """expectedKeys ∪ createdKeys (순서 보존 dedupe). 다중 객체 정리의 단일 출처."""
    return list(
        dict.fromkeys(list(data.get("expectedKeys") or []) + list(data.get("createdKeys") or []))
    )


def _claim_reservation_for_job_tx(
    transaction,
    job_id: str,
    reservation_id: str,
    *,
    owner: str,
    now_ms: int,
    snapshot: dict | None = None,
) -> bool:
    """reservation 을 job 소유로 확정 (8차 B8-06). nested @transactional 금지 — 9차 H9-04.

    open + owner 일치 + 미만료여야 True. 'claimed_by_janitor' 이거나 만료면 False 이고,
    호출측(reserve)은 job 을 만들지 않고 'reservation_lost' 를 돌려 새 preflight 를
    요구한다 — janitor 가 이미 가져간 입력 위에 job 을 세우지 않기 위해서다.

    Args:
      snapshot: reserve 의 read-all-before-write 를 위해 미리 읽어둔 문서.
    """
    ref = _reservation_ref(job_id, reservation_id)
    data = snapshot if snapshot is not None else _snap_dict(ref.get(transaction=transaction))
    if data is None:
        return False
    if data.get("state") != "open":
        return False
    if data.get("owner") != owner:
        return False
    if int(data.get("leaseExpiresAt") or 0) <= now_ms:
        return False
    transaction.update(ref, {"state": "claimed_by_job", "claimedAtMs": now_ms})
    return True


def claim_reservation_for_job(
    job_id: str, reservation_id: str, *, owner: str, now_ms: int
) -> bool:
    """단독 transaction wrapper. 본체는 reserve_visual_job 과 **같은 함수**를 쓴다."""

    def _tx(transaction):
        return _claim_reservation_for_job_tx(
            transaction, job_id, reservation_id, owner=owner, now_ms=now_ms
        )

    return _run_in_transaction(_tx)


def _reservation_has_live_job(data: dict, now_ms: int) -> bool:
    """H9-02 predicate — 이 reservation 의 key 를 소유한 nonterminal unsealed job 존재?

    terminal job / inputSealed job / 이미 다른 payload 로 넘어간 job 은 삭제를 막지
    않는다(입력을 더 안 쓴다). matching nonterminal unsealed job 만 보존 대상이다.
    """
    bucket = data.get("bucket")
    for key in reservation_keys(data):
        obj = _snap_dict(_object_ref(bucket, key).get()) or {}
        for ref_id, entry in (obj.get("refs") or {}).items():
            if entry.get("kind") != "job":
                continue
            job = _snap_dict(_doc(models.visual_job_doc_path(ref_id)).get())
            if job is None:
                continue
            if job.get("state") in models.VISUAL_TERMINAL_STATES:
                continue
            if job.get("inputSealed") is True:
                continue
            return True
    return False


def claim_reservation_for_janitor(
    job_id: str,
    reservation_id: str,
    *,
    owner: str,
    now_ms: int,
    claim_lease_ms: int | None = None,
) -> bool:
    """janitor 회수 claim. **성공 후에만 S3 delete 를 시도한다.**

    claim 대상:
      - (state=='open' AND leaseExpiresAt<=now) — TTL 만료된 미사용 reservation
      - (state=='claimed_by_janitor' AND claimLeaseExpiresAt<=now) — 이전 janitor 가
        claim 직후 crash 한 경우의 재claim (9차 B9-01). 이게 없으면 claim 직후 crash 한
        reservation 이 영원히 회수되지 않아 PII 가 남는다.

    'claimed_by_job' 은 항상 False — 유효 job 의 입력을 지우지 않는다.
    live job ref 가 남아 있으면(H9-02) 역시 False.
    """
    lease = int(claim_lease_ms if claim_lease_ms is not None else models.VISUAL_JANITOR_CLAIM_LEASE_MS)
    pre = _snap_dict(_reservation_ref(job_id, reservation_id).get())
    if pre is None:
        return False
    if _reservation_has_live_job(pre, now_ms):
        return False

    def _tx(transaction):
        ref = _reservation_ref(job_id, reservation_id)
        data = _snap_dict(ref.get(transaction=transaction))
        if data is None:
            return False
        state = data.get("state")
        claimable = (
            state == "open" and int(data.get("leaseExpiresAt") or 0) <= now_ms
        ) or (
            state == "claimed_by_janitor"
            and int(data.get("claimLeaseExpiresAt") or 0) <= now_ms
        )
        if not claimable:
            return False
        transaction.update(
            ref,
            {
                "state": "claimed_by_janitor",
                "claimOwner": owner,
                "claimLeaseExpiresAt": now_ms + lease,
                "claimAttempt": int(data.get("claimAttempt") or 0) + 1,
            },
        )
        return True

    return _run_in_transaction(_tx)


def close_reservation(
    job_id: str, reservation_id: str, *, owner: str | None = None, now_ms: int | None = None
) -> bool:
    """종결 — 'closed' + TTL expireAt + **모든 key 의 ref release 를 같은 transaction**.

    release 를 별도 호출로 미루면 close 직후 crash 시 ownership 문서가 영구 잔존한다
    (10차 B10-03 / T-31-91). 상태 전이의 필수 부분이라 원자로 묶는다.
    """
    now = int(now_ms if now_ms is not None else _now_ms())

    def _tx(transaction):
        ref = _reservation_ref(job_id, reservation_id)
        data = _snap_dict(ref.get(transaction=transaction))
        if data is None:
            return False
        bucket = data.get("bucket")
        keys = reservation_keys(data)
        obj_reads = [
            (k, _object_ref(bucket, k), _snap_dict(_object_ref(bucket, k).get(transaction=transaction)))
            for k in keys
        ]
        transaction.update(
            ref,
            {
                "state": "closed",
                "closedAtMs": now,
                "expireAt": _as_ts(now + models.VISUAL_CLOSED_DOC_RETENTION_MS),
            },
        )
        for _key, obj, obj_data in obj_reads:
            if obj_data is None:
                continue
            refs = dict(obj_data.get("refs") or {})
            refs.pop(reservation_id, None)
            if not refs and obj_data.get("state") != "deleting":
                transaction.delete(obj)
            else:
                transaction.update(obj, {"refs": refs, "updatedAtMs": now})
        return True

    return _run_in_transaction(_tx)


# ═══════════════ (9) durable orphan registry ═══════════════
#
# 보상 delete 가 실패하면 **반드시** 여기 남긴다 — "지우려다 실패했는데 아무도 모르는
# PII" 를 만들지 않기 위해서다.


def upsert_visual_orphan(bucket: str, key: str, *, now_ms: int, reason: str) -> str:
    """보상 delete 실패 기록. closed 였던 같은 key 가 재발하면 재오픈한다 (9차 H9-07).

    문서 id 가 (bucket,key) 결정론 해시라 재발 시 같은 문서를 만난다. closed 로 두면
    두 번째 사고가 조용히 묻히므로 generation+1 로 새 incident 를 연다.
    """
    orphan_id = models.visual_input_object_doc_path(bucket, key).rsplit("/", 1)[-1]

    def _tx(transaction):
        ref = _doc(models.visual_orphan_doc_path(orphan_id))
        data = _snap_dict(ref.get(transaction=transaction))
        if data is None:
            transaction.set(
                ref,
                {
                    "bucket": bucket,
                    "key": key,
                    "state": "open",
                    "generation": 1,
                    "attempt": 0,
                    "nextRetryAtMs": now_ms,
                    "lastError": reason,
                    "createdAtMs": now_ms,
                    "claimOwner": None,
                    "claimLeaseExpiresAt": 0,
                },
            )
            return orphan_id
        if data.get("state") == "closed":
            transaction.update(
                ref,
                {
                    "state": "open",
                    "generation": int(data.get("generation") or 0) + 1,
                    "attempt": 0,
                    "nextRetryAtMs": now_ms,
                    "lastError": reason,
                    "claimOwner": None,
                    "claimLeaseExpiresAt": 0,
                    "expireAt": None,
                },
            )
            return orphan_id
        transaction.update(ref, {"lastError": reason})
        return orphan_id

    return _run_in_transaction(_tx)


def claim_visual_orphan(
    orphan_id: str, *, owner: str, now_ms: int, lease_ms: int | None = None
) -> dict | None:
    """(open AND due) 또는 (claimed AND lease 만료) 를 claim (9차 B9-01 crash 재claim)."""
    lease = int(lease_ms if lease_ms is not None else models.VISUAL_JANITOR_CLAIM_LEASE_MS)

    def _tx(transaction):
        ref = _doc(models.visual_orphan_doc_path(orphan_id))
        data = _snap_dict(ref.get(transaction=transaction))
        if data is None:
            return None
        state = data.get("state")
        claimable = (
            state == "open" and int(data.get("nextRetryAtMs") or 0) <= now_ms
        ) or (
            state == "claimed" and int(data.get("claimLeaseExpiresAt") or 0) <= now_ms
        )
        if not claimable:
            return None
        updated = dict(data)
        updated.update(
            {
                "state": "claimed",
                "claimOwner": owner,
                "claimLeaseExpiresAt": now_ms + lease,
                "attempt": int(data.get("attempt") or 0) + 1,
            }
        )
        transaction.update(
            ref,
            {
                "state": "claimed",
                "claimOwner": owner,
                "claimLeaseExpiresAt": now_ms + lease,
                "attempt": updated["attempt"],
            },
        )
        return updated

    return _run_in_transaction(_tx)


def close_visual_orphan(orphan_id: str, *, now_ms: int) -> bool:
    """delete + HEAD404 확인 후 종결 + ownership ref release (10차 B10-03)."""

    def _tx(transaction):
        ref = _doc(models.visual_orphan_doc_path(orphan_id))
        data = _snap_dict(ref.get(transaction=transaction))
        if data is None:
            return False
        obj = _object_ref(data.get("bucket"), data.get("key"))
        obj_data = _snap_dict(obj.get(transaction=transaction))
        transaction.update(
            ref,
            {
                "state": "closed",
                "closedAtMs": now_ms,
                "expireAt": _as_ts(now_ms + models.VISUAL_CLOSED_DOC_RETENTION_MS),
            },
        )
        if obj_data is not None:
            refs = dict(obj_data.get("refs") or {})
            refs.pop(orphan_id, None)
            if not refs:
                transaction.delete(obj)
            else:
                transaction.update(obj, {"refs": refs, "updatedAtMs": now_ms})
        return True

    return _run_in_transaction(_tx)


def bump_visual_orphan(orphan_id: str, *, next_retry_at_ms: int, last_error: str) -> bool:
    """실패 backoff — claim 반납 후 다음 시도 시각 기록."""

    def _tx(transaction):
        ref = _doc(models.visual_orphan_doc_path(orphan_id))
        if _snap_dict(ref.get(transaction=transaction)) is None:
            return False
        transaction.update(
            ref,
            {
                "state": "open",
                "nextRetryAtMs": int(next_retry_at_ms),
                "lastError": last_error,
                "claimOwner": None,
                "claimLeaseExpiresAt": 0,
            },
        )
        return True

    return _run_in_transaction(_tx)


# ═══════════════ (1) reserve — dispatch 가능 상태를 여는 transaction ═══════════════


def reserve_visual_job(
    uid: str,
    analysis_id: str,
    kind: str,
    *,
    date_key: str | None = None,
    user_limit: int | None = None,
    global_limit: int | None = None,
    payload: dict | None = None,
    allow_retry_failed: bool = False,
    reservation_id: str | None = None,
    reservation_owner: str | None = None,
    now_ms: int | None = None,
) -> dict:
    """job 예약 + analysis 'pending' + 초기 outbox/claim/privacy 를 한 transaction 에 (B3-03).

    correctedPose 호출측은 **immutable srcKey S3 conditional put/preflight 를 먼저 마친
    뒤에만** 호출한다 (upload-first). 입력이 이미 S3 에 있는 상태여야 job 이 만들어지고,
    job 이 만들어지면 그 입력은 janitor 로부터 보호된다.

    correctedPose + reservation_id 지정 시, **같은 transaction 안에서** reservation claim
    (B8-06) + 각 key 의 reservation→job ownership 승격(H10-01)이 함께 성공해야 job 이
    생성된다. 셋이 단일 commit/commit-loss 단위라 "job 은 생겼는데 입력은 janitor 소유"
    같은 중간 상태가 없다.

    Returns:
      {"created": True, "job": {...}}
      {"created": False, "job": {...}}        이미 존재 (호출측 분기 근거 — B2-03)
      {"created": False, "reason": ...}       models.VISUAL_RESERVE_REASONS
    """
    if kind not in models.VISUAL_JOB_KINDS:
        raise ValueError(f"kind must be one of {list(models.VISUAL_JOB_KINDS)}")
    if payload:
        _validate_dict_only_scalars(payload, path="payload")
    now = int(now_ms if now_ms is not None else _now_ms())
    job_id = models.visual_job_id(uid, analysis_id, kind)
    uses_quota = kind == models.VISUAL_KIND_ROTATION and date_key is not None

    def _tx(transaction):
        # ── read all ──────────────────────────────────────────────────────
        job_ref = _doc(models.visual_job_doc_path(job_id))
        job = _snap_dict(job_ref.get(transaction=transaction))
        analysis_ref = _doc(models.analysis_doc_path(uid, analysis_id))
        analysis = _snap_dict(analysis_ref.get(transaction=transaction))

        user_ref = global_ref = None
        user_count = global_count = 0
        if uses_quota:
            user_ref = _doc(models.visual_quota_doc_path(uid, date_key))
            user_count = int((_snap_dict(user_ref.get(transaction=transaction)) or {}).get("count") or 0)
            if global_limit is not None:
                global_ref = _doc(models.visual_quota_doc_path("_global", date_key))
                global_count = int(
                    (_snap_dict(global_ref.get(transaction=transaction)) or {}).get("count") or 0
                )

        reservation = None
        obj_snaps: list[tuple] = []
        if reservation_id is not None:
            reservation = _snap_dict(
                _reservation_ref(job_id, reservation_id).get(transaction=transaction)
            )
            if reservation is not None:
                bucket = reservation.get("bucket")
                for key in reservation_keys(reservation):
                    obj_ref = _object_ref(bucket, key)
                    obj_snaps.append(
                        (bucket, key, _snap_dict(obj_ref.get(transaction=transaction)))
                    )

        # ── decide ────────────────────────────────────────────────────────
        if analysis is None:
            return {"created": False, "reason": "analysis_missing"}

        is_retry = False
        if job is not None:
            if not (allow_retry_failed and job.get("state") == "failed"):
                return {"created": False, "job": job}
            is_retry = True

        if uses_quota:
            if user_limit is not None and user_count >= int(user_limit):
                return {"created": False, "reason": "daily_limit"}
            if global_limit is not None and global_count >= int(global_limit):
                return {"created": False, "reason": "daily_limit"}

        if reservation_id is not None:
            if reservation is None:
                return {"created": False, "reason": "reservation_lost"}
            # 승격 가능성을 **쓰기 전에 전부** 확인한다 (H10-01 all-or-nothing). 하나라도
            # 불가능하면 claim 조차 버퍼링하지 않아, 일부 key 만 승격된 채 job 이 없는
            # 중간 상태가 생기지 않는다.
            if any(
                obj_data is None or obj_data.get("state") == "deleting"
                for _b, _k, obj_data in obj_snaps
            ):
                return {"created": False, "reason": "reservation_lost"}
            if not _claim_reservation_for_job_tx(
                transaction,
                job_id,
                reservation_id,
                owner=reservation_owner,
                now_ms=now,
                snapshot=reservation,
            ):
                return {"created": False, "reason": "reservation_lost"}
            for bucket, key, obj_data in obj_snaps:
                if not _promote_key_ownership_to_job_tx(
                    transaction,
                    bucket,
                    key,
                    reservation_ref=reservation_id,
                    job_ref=job_id,
                    snapshot=obj_data,
                    now_ms=now,
                ):
                    return {"created": False, "reason": "reservation_lost"}

        # ── write all ─────────────────────────────────────────────────────
        generation = int(job.get("generation") or 1) + 1 if is_retry else 1
        doc = {
            "uid": uid,
            "analysisId": analysis_id,
            "kind": kind,
            "state": "reserved",
            # outbox 초기값 (B4-01) — 예약 즉시 dispatch 가능.
            "nextAction": "create",
            "dispatchState": "pending",
            "nextDispatchAtMs": now,
            "outboxSeq": 1,
            # claim 초기값은 clear 상태 (B6-01) — create 는 claim CAS 를 쓰지 않는다.
            "claimedOutboxSeq": 0,
            "claimState": None,
            "claimOwner": None,
            "claimLeaseExpiresAt": 0,
            "generation": generation,
            "attempt": 0,
            "retryCount": 0,
            "taskId": None,
            "requestKey": None,
            "leaseOwner": None,
            "leaseExpiresAt": 0,
            "failureReason": None,
            "pendingTerminalState": None,
            "pendingFailureReason": None,
            "pairAttempt": 0,
            "cleanupAttempt": 0,
            # privacy 초기값 (B6-03/B6-04).
            "inputSealed": False,
            "privacyBlocker": None,
            "cleanupVerifiedAtMs": 0,
            "requestedAtMs": now,
            "updatedAtMs": now,
            "quotaDateKey": date_key,
            "reservationId": reservation_id,
        }
        if payload:
            doc.update(payload)
        transaction.set(job_ref, doc)

        if uses_quota:
            transaction.set(user_ref, {"count": user_count + 1, "dateKey": date_key}, True)
            if global_ref is not None:
                transaction.set(global_ref, {"count": global_count + 1, "dateKey": date_key}, True)

        # 표시 상태 'pending' 은 job 예약과 **같은 transaction** 이어야 한다 (B3-03) —
        # 늦은 pending 이 terminal 을 덮어쓰는 창을 없앤다.
        transaction.update(
            analysis_ref,
            {
                f"result.{kind}Status": models.VISUAL_STATUS_PENDING,
                f"result.{kind}UpdatedAtMs": now,
            },
        )
        return {"created": True, "job": doc}

    return _run_in_transaction(_tx)


# ═══════════════ (2) transition — outbox instance CAS + claim owner/lease CAS ═══════════════


def transition_visual_job(
    job_id: str,
    *,
    expect_states,
    updates: dict,
    next_action: str | None,
    expect_outbox_seq: int,
    expect_generation: int | None = None,
    expect_claim_owner: str | None = None,
    now_ms: int | None = None,
    next_dispatch_at_ms: int | None = None,
) -> dict | None:
    """nonterminal 전이. 성공 시 **갱신된 job snapshot**, CAS 실패 시 None.

    snapshot 을 돌려주는 게 계약의 핵심이다 (5차 H5-04): 호출자는 전이 후 새 outboxSeq /
    generation / requestKey 를 **여기서만** 얻고, 인바운드 SQS 메시지 값을 재사용하지
    않는다. 재사용하면 이미 한 칸 진행한 job 을 옛 seq 로 다시 건드린다.

    CAS 4중:
      - state ∈ expect_states
      - generation == expect_generation (구세대 메시지 차단)
      - outboxSeq == expect_outbox_seq (구 action instance 차단 — B4-01)
      - expect_claim_owner 지정 시 claimOwner/claimedOutboxSeq 일치 + **lease 미만료**
        (lease 를 잃은 늦은 worker 의 write 차단 — B5-01 + H6-07)

    Raises:
      ValueError: terminal 전이 시도, 상태별 필수 필드 누락 등 계약 위반.
    """
    now = int(now_ms if now_ms is not None else _now_ms())

    def _tx(transaction):
        ref = _doc(models.visual_job_doc_path(job_id))
        job = _snap_dict(ref.get(transaction=transaction))
        if job is None:
            return None
        if job.get("state") not in tuple(expect_states):
            return None
        if expect_generation is not None and int(job.get("generation") or 0) != int(expect_generation):
            return None
        if int(job.get("outboxSeq") or 0) != int(expect_outbox_seq):
            return None
        if expect_claim_owner is not None:
            if job.get("claimOwner") != expect_claim_owner:
                return None
            if int(job.get("claimedOutboxSeq") or 0) != int(expect_outbox_seq):
                return None
            if now >= int(job.get("claimLeaseExpiresAt") or 0):
                return None  # lease 만료 — 이미 남이 재claim 했을 수 있다.

        candidate = dict(job)
        candidate.update(updates)
        from_state = job.get("state")
        new_state = candidate.get("state")

        if new_state in models.VISUAL_TERMINAL_STATES:
            raise ValueError("terminal 은 finalize_visual_job 전용 — transition 금지")
        if new_state not in models.VISUAL_JOB_STATES:
            raise ValueError(f"state must be one of {list(models.VISUAL_JOB_STATES)}")
        if next_action is not None and next_action not in models.VISUAL_NEXT_ACTIONS:
            raise ValueError(f"next_action must be one of {list(models.VISUAL_NEXT_ACTIONS)}")
        # next_action=None 은 'creating' 에서만 — create 는 outbox 가 아니라 durable
        # lease 로 보호되기 때문이다. 그 외 nonterminal 이 nextAction 없이 남으면
        # dispatcher 가 집을 수 없어 job 이 영구 정지한다.
        if next_action is None and new_state != "creating":
            raise ValueError(f"nonterminal state {new_state!r} 는 next_action 필수")
        if new_state == "postprocessing" and next_action != "postprocess":
            raise ValueError("postprocessing 전이는 next_action='postprocess' 필수")
        if new_state == "polling" and not candidate.get("taskId"):
            raise ValueError("polling 전이는 비어있지 않은 taskId 필수")

        generation = int(job.get("generation") or 1)
        if new_state == "creating":
            if from_state == "retry_ready":
                if candidate.get("taskId") is not None:
                    raise ValueError("retry_ready→creating 은 taskId=None 강제 (B4-03)")
                generation += 1
            if not candidate.get("leaseOwner") or not candidate.get("leaseExpiresAt"):
                raise ValueError("creating 전이는 leaseOwner/leaseExpiresAt 필수")
            # requestKey 는 **이 transaction 안에서** 새 generation 으로 만든다 (H5-03).
            # caller 가 준 값은 무시 — 옛 generation 의 멱등키가 새 세대에 새면
            # 벤더가 이전 결과를 그대로 돌려준다.
            candidate["requestKey"] = f"{job_id}:gen{generation}"

        outbox_seq = int(job.get("outboxSeq") or 0) + 1
        candidate.update(
            {
                "generation": generation,
                "outboxSeq": outbox_seq,
                "nextAction": next_action,
                "dispatchState": None if new_state == "creating" else "pending",
                "nextDispatchAtMs": 0
                if new_state == "creating"
                else int(next_dispatch_at_ms if next_dispatch_at_ms is not None else now),
                # 새 outboxSeq → 다음 action 용 claim 필드 원자 clear (B6-01).
                # claimedOutboxSeq 는 audit 로 남기되 새 seq 와 반드시 다르다(=이전 seq).
                "claimState": None,
                "claimOwner": None,
                "claimLeaseExpiresAt": 0,
                "updatedAtMs": now,
            }
        )
        if new_state == "creating":
            assert candidate["requestKey"].endswith(f":gen{candidate['generation']}")
        transaction.set(ref, candidate)
        return candidate

    return _run_in_transaction(_tx)


# ═══════════════ (3) claim — dict 4상태 ═══════════════


def claim_visual_job_action(
    job_id: str,
    *,
    generation: int,
    action: str,
    outbox_seq: int,
    owner: str,
    lease_ms: int,
    now_ms: int,
) -> dict:
    """외부 side-effect **전** claim. 반환 `{"status", "job"}`.

    status 4상태:
      claimed    미claim 또는 same-seq lease 만료 → owner/lease 원자 갱신 후 실행 가능
      busy       same-seq + 유효 lease → **정상 ACK 금지** (batchItemFailures 로 반납).
                 정상 ACK 하면 중복 전달이 유료 action 을 두 번 태운다 (T-31-62)
      stale      generation/action/outboxSeq 불일치 → 외부 0, 정상 ACK
      completed  이미 다음 instance/terminal → 외부 0, 정상 ACK

    **claimedOutboxSeq 단독 판정 금지** (B5-01): claimState/claimOwner/claimLeaseExpiresAt
    를 함께 봐야 same-seq active(busy) 와 same-seq expired(재claim 가능) 가 구분된다.

    반환 snapshot 은 owner handoff 의 **유일 출처**다 (B6-01) — 호출자는 claim 이전 job 을
    action 이나 후속 CAS 에 재사용하지 않는다.

    create action 은 claim 을 쓰지 않는다 — begin_visual_job_create 의 creating lease 특례.
    """
    def _tx(transaction):
        ref = _doc(models.visual_job_doc_path(job_id))
        job = _snap_dict(ref.get(transaction=transaction))
        if job is None:
            return {"status": "stale", "job": None}

        cur_seq = int(job.get("outboxSeq") or 0)
        cur_gen = int(job.get("generation") or 0)
        if (
            job.get("state") in models.VISUAL_TERMINAL_STATES
            or cur_gen > int(generation)
            or cur_seq > int(outbox_seq)
        ):
            return {"status": "completed", "job": job}
        if cur_gen != int(generation) or cur_seq != int(outbox_seq) or job.get("nextAction") != action:
            return {"status": "stale", "job": job}

        claimed_seq = int(job.get("claimedOutboxSeq") or 0)
        if (
            claimed_seq == int(outbox_seq)
            and job.get("claimOwner")
            and int(job.get("claimLeaseExpiresAt") or 0) > int(now_ms)
        ):
            return {"status": "busy", "job": job}

        updated = dict(job)
        updated.update(
            {
                "claimedOutboxSeq": int(outbox_seq),
                "claimState": "claimed",
                "claimOwner": owner,
                "claimLeaseExpiresAt": int(now_ms) + int(lease_ms),
            }
        )
        transaction.update(
            ref,
            {
                "claimedOutboxSeq": int(outbox_seq),
                "claimState": "claimed",
                "claimOwner": owner,
                "claimLeaseExpiresAt": int(now_ms) + int(lease_ms),
            },
        )
        return {"status": "claimed", "job": updated}

    return _run_in_transaction(_tx)


# ═══════════════ (4b) read ═══════════════


def read_visual_job(job_id: str) -> dict | None:
    """단순 get (side-effect 0). 31-10 producer preflight + janitor 가 사용 (7차 H7-03)."""
    return _snap_dict(_doc(models.visual_job_doc_path(job_id)).get())


# ═══════════════ (4c) begin_visual_job_create — create 전용 CAS ═══════════════


def begin_visual_job_create(
    job_id: str,
    *,
    expect_generation: int,
    expect_outbox_seq: int,
    now_ms: int,
    owner: str,
    lease_ms: int,
    expect_next_action: str = "create",
) -> dict:
    """vendor create 전용 CAS (8차 B8-01). 반환 `{"status", "job"}`.

    status 5상태:
      acquired    creating 전이 완료 — **반환 snapshot 하나로 즉시 vendor create 1회**.
                  future lease 를 다시 busy 로 판정해 no-op 하지 않는다(그러면 정상
                  create 가 영영 안 나간다 — T-31-85). 2차 _advance(creating) 호출 없음
      busy        다른 owner 가 유효 lease 보유
      unconfirmed lease 만료 + taskId 부재 → **수동 판정**. 자동 재생성 금지 (B2-02):
                  create 가 벤더에 도달했는지 알 수 없어 재시도가 이중 과금이 된다
      resume      taskId 존재 → polling 재개
      stale       generation/outboxSeq/nextAction 불일치 또는 terminal → 외부 0, 정상 ACK

    create 는 claim CAS 를 쓰지 않는다 (B6-01): reserve/retry_ready snapshot 의 claim
    필드가 clear 상태라 claim owner CAS 를 걸면 자기 자신에게 막힌다.
    """
    def _tx(transaction):
        ref = _doc(models.visual_job_doc_path(job_id))
        job = _snap_dict(ref.get(transaction=transaction))
        if job is None:
            return {"status": "stale", "job": None}
        state = job.get("state")
        if state in models.VISUAL_TERMINAL_STATES:
            return {"status": "stale", "job": job}

        if state == "creating":
            if job.get("taskId"):
                return {"status": "resume", "job": job}
            if int(job.get("leaseExpiresAt") or 0) > int(now_ms):
                # 유효 lease 보유 — 자기 owner 여도 busy 로 반납한다. stale(정상 ACK)로
                # 두면 job 이 dispatcher 복구까지 멈추고, 재진입을 허용하면 벤더 create 가
                # 두 번 나갈 여지가 생긴다. busy 는 visibility 뒤 재전달이라 둘 다 없다.
                return {"status": "busy", "job": job}
            return {"status": "unconfirmed", "job": job}

        if (
            state not in ("reserved", "retry_ready")
            or int(job.get("generation") or 0) != int(expect_generation)
            or int(job.get("outboxSeq") or 0) != int(expect_outbox_seq)
            or job.get("nextAction") != expect_next_action
            or int(job.get("nextDispatchAtMs") or 0) > int(now_ms)
        ):
            return {"status": "stale", "job": job}

        generation = int(job.get("generation") or 1)
        if state == "retry_ready":
            generation += 1

        # H9-03 고정 write set — 여기서 빠지는 필드가 있으면 옛 create 메시지가
        # stale 로 죽지 않고 두 번째 vendor create 를 태운다.
        updated = dict(job)
        updated.update(
            {
                "state": "creating",
                "generation": generation,
                "taskId": None,
                "leaseOwner": owner,
                "leaseExpiresAt": int(now_ms) + int(lease_ms),
                "requestKey": f"{job_id}:gen{generation}",
                "outboxSeq": int(job.get("outboxSeq") or 0) + 1,
                "nextAction": None,
                "dispatchState": None,
                "nextDispatchAtMs": 0,
                "claimState": None,
                "claimOwner": None,
                "claimLeaseExpiresAt": 0,
                "updatedAtMs": int(now_ms),
            }
        )
        transaction.set(ref, updated)
        return {"status": "acquired", "job": updated}

    return _run_in_transaction(_tx)


# ═══════════════ (5) mark dispatched ═══════════════


def mark_visual_job_dispatched(
    job_id: str,
    *,
    expect_action: str,
    expect_outbox_seq: int,
    expect_generation: int | None = None,
) -> bool:
    """SQS send 성공 후 'pending'→'sent' CAS (B4-01).

    3중 CAS(generation+action+outboxSeq)여야 하는 이유: 이전 action 의 send 가 늦게
    성공해 mark 를 던지면, 그 사이 job 이 다음 action 으로 전이했더라도 seq/action 이
    달라 no-op 된다. seq 없이 하면 늦은 mark 가 새 continuation 의 pending 을 'sent' 로
    덮어 dispatcher 가 영영 재발행하지 않는다 (T-31-56).
    """
    def _tx(transaction):
        ref = _doc(models.visual_job_doc_path(job_id))
        job = _snap_dict(ref.get(transaction=transaction))
        if job is None:
            return False
        if job.get("dispatchState") != "pending":
            return False
        if expect_generation is not None and int(job.get("generation") or 0) != int(expect_generation):
            return False
        if job.get("nextAction") != expect_action:
            return False
        if int(job.get("outboxSeq") or 0) != int(expect_outbox_seq):
            return False
        transaction.update(ref, {"dispatchState": "sent"})
        return True

    return _run_in_transaction(_tx)


# ═══════════════ (6) dispatcher — 이중 durable cursor ═══════════════


def _save_scan_cursor(cursor_path: str, last_id: str | None) -> None:
    _doc(cursor_path).set({"lastId": last_id, "updatedAtMs": _now_ms()}, merge=True)


def _scan_cycle(field_value: str, cursor_path: str, max_scan: int) -> tuple[list, bool, bool]:
    """등가 쿼리 1개 + __name__ 정렬 + durable cursor 순환 스캔.

    **복합 인덱스 금지 이유** (STATE.md phase-33 3f6681f 선례): 등가(dispatchState==)와
    range(nextDispatchAtMs<=) 를 한 쿼리에 섞으면 Firestore 가 composite index 를 요구하고
    운영에서 FAILED_PRECONDITION 으로 죽는다. 그래서 등가만 서버에 맡기고 due 판정은
    python 에서 한다.

    **cursor 순환이 필요한 이유** (H4-08): 매번 앞에서 N개만 보면 앞쪽 문서가 계속 잡혀
    뒤쪽이 영구 starvation 된다. durable cursor 로 이어 스캔하고 끝에서 wrap 하면
    max_scan 을 넘는 backlog 도 여러 호출에 걸쳐 전량 drain 된다.
    """
    cursor_ref = _doc(cursor_path)
    last_id = (_snap_dict(cursor_ref.get()) or {}).get("lastId")

    def _query(start_after_id):
        q = _collection(_VISUAL_JOBS_COLLECTION).where(
            filter=_field_filter("dispatchState", "==", field_value)
        )
        q = q.order_by("__name__")
        if start_after_id:
            q = _query_start_after_name(q, _VISUAL_JOBS_COLLECTION, start_after_id)
        return q

    scanned = list(_query(last_id).limit(max_scan).stream())
    wrapped = False
    if len(scanned) < max_scan and last_id:
        seen = {s.id for s in scanned}
        for snap in _query(None).limit(max_scan - len(scanned)).stream():
            if snap.id in seen:
                continue
            scanned.append(snap)
        wrapped = True

    truncated = len(scanned) >= max_scan
    return scanned, truncated, wrapped


def list_dispatch_pending(now_ms: int, *, limit: int = 20, max_scan: int = 1000) -> dict:
    """dispatcher 가 발행할 항목 목록. 두 종류를 한 번에 돌려준다.

    (a) pending — dispatchState=='pending' 이면서 due(nextDispatchAtMs<=now). CAS 는
        성공했는데 SQS send 가 유실된 경우가 여기로 복구된다.
    (b) sent-recovery — dispatchState=='sent' 인데
        `claimedOutboxSeq==outboxSeq AND claimState=='claimed' AND
         0 < claimLeaseExpiresAt <= now_ms AND state nonterminal`.
        **claim 직후 crash 의 durable 복구 주체다** (5차 B5-01 + 6차 H6-01). "재전달
        no-op 멱등" 만으로는 복구되지 않는다 — 아무도 재전달을 만들어주지 않기 때문.
        정확 필터라 미claim sent(lease 0)나 구 seq claim 은 재발행하지 않는다(정상 sent
        재발행 0). dispatchState 를 pending 으로 되돌리지 않는다.

    pending/sent 는 **독립 durable cursor** 로 순환한다 (H5-06/H6-01) — cursor 를 공유하면
    한쪽이 다른 쪽을 굶긴다. 두 종류가 서로를 굶기지 않도록 각각 limit 만큼 담는다.

    Returns:
      items: [{jobId, nextAction, generation, outboxSeq, state, recovery}]
      scanned_outbox_max_age_ms: **스캔 window 안** due 항목의 최고 경과 (M6-01 —
        전체 backlog 최고령이 아니다. 알람 해석 시 truncated 와 함께 봐야 한다)
      truncated: pending 스캔이 max_scan 에 도달 (backlog 초과 신호 — 31-10 alarm)
      cursor_wrapped: 순환 wrap 발생
    """
    pending, truncated, wrapped = _scan_cycle(
        "pending", models.visual_dispatch_cursor_doc_path(), max_scan
    )

    due = []
    max_age = 0
    for snap in pending:
        data = snap.to_dict()
        at = int(data.get("nextDispatchAtMs") or 0)
        if at > int(now_ms):
            continue
        max_age = max(max_age, int(now_ms) - at)
        due.append((at, snap.id, data))
    due.sort(key=lambda r: r[0])

    emitted = due[:limit]
    items = [
        {
            "jobId": job_id,
            "nextAction": data.get("nextAction"),
            "generation": int(data.get("generation") or 0),
            "outboxSeq": int(data.get("outboxSeq") or 0),
            "state": data.get("state"),
            "recovery": False,
        }
        for _at, job_id, data in emitted
    ]
    # cursor 는 **실제로 발행한** 마지막 문서까지만 전진시킨다 (H4-08). 스캔한 끝까지
    # 밀면 window 당 limit 개만 발행되고 나머지 (max_scan - limit) 개는 매 순환마다
    # 같은 자리에서 다시 건너뛰어져 영구 starvation 된다 — backlog 전량 drain 불가.
    _save_scan_cursor(
        models.visual_dispatch_cursor_doc_path(),
        max((job_id for _at, job_id, _d in emitted), default=(pending[-1].id if pending else None)),
    )

    sent, _sent_truncated, sent_wrapped = _scan_cycle(
        "sent", models.visual_dispatch_sent_cursor_doc_path(), max_scan
    )
    recovered_ids: list[str] = []
    for snap in sent:
        if len(recovered_ids) >= limit:
            break
        data = snap.to_dict()
        lease = int(data.get("claimLeaseExpiresAt") or 0)
        if data.get("state") in models.VISUAL_TERMINAL_STATES:
            continue
        if data.get("claimState") != "claimed":
            continue
        if int(data.get("claimedOutboxSeq") or 0) != int(data.get("outboxSeq") or 0):
            continue
        if not (0 < lease <= int(now_ms)):
            continue
        items.append(
            {
                "jobId": snap.id,
                "nextAction": data.get("nextAction"),
                "generation": int(data.get("generation") or 0),
                "outboxSeq": int(data.get("outboxSeq") or 0),
                "state": data.get("state"),
                "recovery": True,
            }
        )
        recovered_ids.append(snap.id)

    _save_scan_cursor(
        models.visual_dispatch_sent_cursor_doc_path(),
        max(recovered_ids, default=(sent[-1].id if sent else None)),
    )

    return {
        "items": items,
        "scanned_outbox_max_age_ms": max_age,
        "truncated": truncated,
        "cursor_wrapped": bool(wrapped or sent_wrapped),
    }


# ═══════════════ (4) finalize — 유일한 terminal 경로 ═══════════════


def _assert_visual_key_prefix(key: str, uid: str, analysis_id: str) -> None:
    prefix = f"results/{uid}/{analysis_id}/"
    if not key.startswith(prefix):
        raise ValueError(f"visual key 는 {prefix!r} prefix 필수 (H-02): got {key!r}")


def finalize_visual_job(
    job_id: str,
    *,
    terminal_state: str,
    failure_reason: str | None,
    job_meta: dict | None,
    display_status: str,
    expect_states,
    key: str | None = None,
    joint: str | None = None,
    cleanup_verified_at_ms: int | None = None,
    expect_generation: int | None = None,
    expect_outbox_seq: int | None = None,
    expect_claim_owner: str | None = None,
    now_ms: int | None = None,
) -> str:
    """job terminal + analysis 표시 상태를 **하나의 multi-document transaction** 으로.

    둘을 나누면 사이의 crash 가 "job 은 done 인데 앱은 영원히 pending" 을 만든다
    (T-31-57). uid/analysisId/kind 는 **caller 인자가 아니라 job 문서에서 파생**한다 —
    caller 가 틀린(또는 악의적인) analysisId 를 넣어도 남의 분석을 건드릴 수 없다 (H4-07).

    Returns: 'finalized' | 'stale'(CAS 실패 no-op) | 'orphaned_analysis'

    Raises:
      ValueError: 모순 조합, correctedPose privacy gate 위반, key prefix 위반.
    """
    if terminal_state not in models.VISUAL_TERMINAL_STATES:
        raise ValueError("terminal_state must be 'done' or 'failed'")
    if display_status not in models.VISUAL_STATUSES:
        raise ValueError(f"display_status must be one of {list(models.VISUAL_STATUSES)}")
    meta = dict(job_meta or {})
    # privacy 필드는 dedicated 파라미터로만 (8차 B8-03) — job_meta 우회로 지우면
    # 재확인 없이 blocker 가 사라진다.
    for banned in ("privacyBlocker", "cleanupVerifiedAtMs"):
        if banned in meta:
            raise ValueError(f"job_meta 로 {banned} 지정 금지 — dedicated parameter 사용")
    if meta:
        _validate_dict_only_scalars(meta, path="job_meta")

    # 모순 조합 거부 — 표시와 실제가 어긋난 terminal 을 애초에 못 쓰게 한다.
    if terminal_state == "done":
        if display_status != models.VISUAL_STATUS_DONE:
            raise ValueError("terminal 'done' 은 display_status='done' 필수")
        if not key:
            raise ValueError("terminal 'done' 은 canonical key 필수")
        if failure_reason is not None:
            raise ValueError("terminal 'done' 은 failure_reason=None 필수")
    else:
        if display_status != models.VISUAL_STATUS_FAILED:
            raise ValueError("terminal 'failed' 는 display_status='failed' 필수")
        if key is not None:
            raise ValueError("terminal 'failed' 는 canonical key 금지")
        if failure_reason not in models.VISUAL_FAILURE_REASONS:
            raise ValueError(
                f"failure_reason must be one of {list(models.VISUAL_FAILURE_REASONS)}"
            )

    now = int(now_ms if now_ms is not None else _now_ms())

    def _tx(transaction):
        job_ref = _doc(models.visual_job_doc_path(job_id))
        job = _snap_dict(job_ref.get(transaction=transaction))
        if job is None:
            return "stale"
        if job.get("state") not in tuple(expect_states):
            return "stale"
        if expect_generation is not None and int(job.get("generation") or 0) != int(expect_generation):
            return "stale"
        if expect_outbox_seq is not None and int(job.get("outboxSeq") or 0) != int(expect_outbox_seq):
            return "stale"
        if expect_claim_owner is not None:
            if job.get("claimOwner") != expect_claim_owner:
                return "stale"
            if expect_outbox_seq is not None and int(job.get("claimedOutboxSeq") or 0) != int(
                expect_outbox_seq
            ):
                return "stale"
            if now >= int(job.get("claimLeaseExpiresAt") or 0):
                return "stale"

        uid = job.get("uid")
        analysis_id = job.get("analysisId")
        kind = job.get("kind")
        analysis_ref = _doc(models.analysis_doc_path(uid, analysis_id))
        analysis = _snap_dict(analysis_ref.get(transaction=transaction))

        # cleanup 시각 기록과 terminal 전이는 **같은 transaction** 이어야 한다 (7차 B7-03).
        # job_meta 로만 넘기면 validator 가 기존 문서(0)를 읽어 항상 ValueError 났다.
        candidate = dict(job)
        candidate.update(meta)
        candidate["state"] = terminal_state
        candidate["failureReason"] = failure_reason
        if cleanup_verified_at_ms is not None and int(cleanup_verified_at_ms) > 0:
            candidate["cleanupVerifiedAtMs"] = int(cleanup_verified_at_ms)
            candidate["privacyBlocker"] = None  # B8-03 — clear+terminal 원자 완성.
        elif job.get("privacyBlocker") is not None:
            raise ValueError(
                "privacyBlocker 존재 — cleanup_verified_at_ms 재확인 없이 terminal 금지"
            )

        # ★ correctedPose privacy gate — **unconditional** (8차 B8-02).
        # 'inputSealed==True 이면' 같은 조건부로 쓰면 inputSealed=False 인 job(예: 예약
        # 직후 문서)이 게이트를 통째로 건너뛰어 cleanup 없이 terminal 이 된다 (T-31-86).
        # done/failed 공통이다 — 실패해도 임시 생체 프레임은 지워져야 한다.
        if kind == models.VISUAL_KIND_CORRECTED_POSE:
            if candidate.get("inputSealed") is not True:
                raise ValueError("correctedPose terminal 은 inputSealed=True 필수 (B8-02)")
            if int(candidate.get("cleanupVerifiedAtMs") or 0) <= 0:
                raise ValueError("correctedPose terminal 은 cleanupVerifiedAtMs>0 필수 (B8-02)")
            if candidate.get("privacyBlocker") is not None:
                raise ValueError("correctedPose terminal 은 privacyBlocker=None 필수 (B8-02)")

        if key is not None:
            _assert_visual_key_prefix(key, uid, analysis_id)

        job_write = dict(meta)
        job_write.update(
            {
                "state": terminal_state,
                "failureReason": failure_reason,
                "nextAction": None,
                "dispatchState": None,
                "updatedAtMs": now,
            }
        )
        if "cleanupVerifiedAtMs" in candidate:
            job_write["cleanupVerifiedAtMs"] = candidate["cleanupVerifiedAtMs"]
        job_write["privacyBlocker"] = candidate.get("privacyBlocker")

        if analysis is None:
            # 표시할 곳이 없다 — job 만 typed 실패로 닫고 reconciler 에 넘긴다.
            transaction.update(
                job_ref,
                {
                    "state": "failed",
                    "failureReason": "orphaned_analysis",
                    "nextAction": None,
                    "dispatchState": None,
                    "updatedAtMs": now,
                },
            )
            return "orphaned_analysis"

        transaction.update(job_ref, job_write)
        analysis_update = {
            f"result.{kind}Status": display_status,
            f"result.{kind}UpdatedAtMs": now,
        }
        if terminal_state == "done":
            analysis_update[f"result.{_visual_key_field(kind)}"] = key
            if kind == models.VISUAL_KIND_CORRECTED_POSE and joint is not None:
                analysis_update["result.correctedPoseJoint"] = joint
        # 분석 공용 top-level updatedAt 은 건드리지 않는다 — 시각물은 표현물이라
        # 분석 자체의 갱신 시각을 흔들면 안 된다 (D-03 경계).
        transaction.update(analysis_ref, analysis_update)
        return "finalized"

    return _run_in_transaction(_tx)


def _visual_key_field(kind: str) -> str:
    """canonical key 필드명. 31-04 TS 측과 lockstep."""
    return "correctedPoseKey" if kind == models.VISUAL_KIND_CORRECTED_POSE else "rotationVideoKey"


# ═══════════════ (7) 운영 reconciler 전용 ═══════════════


def update_analysis_visual(
    uid: str,
    analysis_id: str,
    kind: str,
    *,
    status: str,
    key: str | None = None,
    joint: str | None = None,
) -> None:
    """terminal reconciler(31-09 운영 스크립트) **전용**.

    production worker 경로에서 호출 금지 — job 문서를 건너뛰고 표시 상태만 바꾸면
    finalize 의 원자성이 깨진다. 31-09 acceptance 가 grep 으로 강제한다.

    URL 파라미터가 없다는 점이 계약이다 (H-02/H3-01): Firestore 에는 canonical key 만
    저장하고 presigned URL 은 인증 재서명 경로에서만 만든다.
    """
    if kind not in models.VISUAL_JOB_KINDS:
        raise ValueError(f"kind must be one of {list(models.VISUAL_JOB_KINDS)}")
    if status not in models.VISUAL_STATUSES:
        raise ValueError(f"status must be one of {list(models.VISUAL_STATUSES)}")
    if key is not None:
        _assert_visual_key_prefix(key, uid, analysis_id)
    update = {
        f"result.{kind}Status": status,
        f"result.{kind}UpdatedAtMs": _now_ms(),
    }
    if key is not None:
        update[f"result.{_visual_key_field(kind)}"] = key
    if joint is not None and kind == models.VISUAL_KIND_CORRECTED_POSE:
        update["result.correctedPoseJoint"] = joint
    # top-level updatedAt 미갱신 (D-03 경계).
    _doc(models.analysis_doc_path(uid, analysis_id)).update(update)
