"""Firestore Admin 클라이언트 (백엔드 전용 — 보안 규칙 우회).

용도:
  - pipeline: users/{uid}/analyses/{id} 의 status/result/error 갱신
  - reference-api: reference 컬렉션 목록 조회

앱은 절대 Admin 권한을 갖지 않는다. 서비스 계정은 auth.py 와 동일하게
Parameter Store(FIREBASE_SA_PARAM)에서 로드 — 코드/.env 하드코딩 금지.
"""

from __future__ import annotations

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
    for list_key in ("records", "coverageGaps"):
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


# ─────────────────── Plan 06-03 (2026-06-08, R2 fix round-2) ─────────────
#
# Phase 6 (2026-06-08, Plan 06-03) — D-06-B2 + R2 fix (round-2). mode1 silently
# OFF 차단 (두 canary: reference_profile_missing + reference_source_pose_missing) +
# Phase 14 정은지 reference 등록 helper. 두 필드 atomic merge.

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


def get_reference_motion(motion_id: str) -> dict | None:
    """기준 모션 1건. keyframe 각도 데이터(angles) + 메타 포함(ml_CLAUDE.md 등록)."""
    snap = _doc(models.reference_motion_path(motion_id)).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    data.setdefault("motionId", motion_id)
    return data


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
