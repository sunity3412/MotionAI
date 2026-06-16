"""Phase 11 — CoachCommentHook builder + per-report fallback resolver (Wave 1 본체).

본 모듈은 finding → CoachCommentHook 변환 / per-report fallback 정책의 단일 소유처다.
`coach_hook.py` (dataclass + pure validator) 와 분리한 이유는 HIGH-3 순환 import 차단:
  · `force_pattern.py` / `body_normalizer.py` 가 `coach_hook.CoachCommentHook` 을 import.
  · builder 는 `ForcePatternFinding` / `BodyComparisonFinding` 를 알아야 하지만,
    coach_hook.py 가 그것을 import 하면 순환 (`force_pattern → coach_hook → force_pattern`).
  · 따라서 builder 는 별도 모듈이고, finding 클래스는 `TYPE_CHECKING` 가드 / local import
    로만 참조한다 (모듈 로드 시점 top-level import 금지).

iter-4 MEDIUM-2 — analysis layer 결합 격리:
  · 본 모듈은 `sunity_shared.gemini.schemas` 를 **import 하지 않는다** (analysis →
    gemini adapter schema 의존 금지). resolve_coach_hook_bundle 의 bundle 입력은
    `object | dict | None` duck object — attribute access / dict access 둘 다 지원.

번역만 (D-04/D-05 number-free):
  · build_canned_hook 은 finding 의 기존 canned interpretation 텍스트 (이미 객관·
    number-free KO) 만 조합한다. 점수/좌표/판정/도(degree)/%/임의 숫자 mint 0.
  · LLM 미사용 (Gemini 실패/미사용 시 fallback 경로). 구성상 digit-free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .coach_hook import CoachCommentHook

if TYPE_CHECKING:  # 모듈 로드 시점 import 금지 (HIGH-3 순환 차단) — 타입 힌트 전용.
    from .body_normalizer import BodyComparisonFinding  # noqa: F401
    from .force_pattern import ForcePatternFinding  # noqa: F401


# canned 카피는 number-free + forbidden-phrase free (구성상 digit 0). 점수/판정 어휘
# (점/훌륭/완벽/양호/잘했다) 미사용 — '가능성' 언어 (D-09-D3 정합).
_FORCE_NO_FINDINGS_SUMMARY = (
    "이번 구간에서 두드러진 힘 사용 패턴은 발견되지 않았어요."
)
_BODY_NO_FINDINGS_SUMMARY = (
    "이번 구간에서 자세 라인의 뚜렷한 보정 포인트는 발견되지 않았어요."
)
_FORCE_CUE_DEFAULTS = (
    "지목된 부위의 힘 전달 감각에 집중해 보세요.",
    "동작 중 호흡과 코어 안정에 신경 써 보세요.",
)
_BODY_CUE_DEFAULTS = (
    "지목된 부위의 정렬을 거울이나 영상으로 확인해 보세요.",
    "동작을 천천히 반복하며 라인을 맞춰 보세요.",
)
_FORCE_QUESTION_TEMPLATE = "{part} 부위의 힘 사용이 의도한 동작인지 강사와 확인해 보세요."
_BODY_QUESTION_TEMPLATE = "{part} 정렬이 의도한 동작인지 강사와 확인해 보세요."
_GENERIC_QUESTION = (
    "이번 분석에서 강사와 함께 확인하고 싶은 부분이 있는지 살펴보세요."
)
_GENERIC_PART = "지목된"

# joint_key → 한국어 부위 라벨 (number-free, 객관). skeleton.JOINT_KEYS 8개 정합.
_JOINT_KEY_LABELS = {
    "left_elbow": "왼쪽 팔꿈치",
    "right_elbow": "오른쪽 팔꿈치",
    "left_shoulder": "왼쪽 어깨",
    "right_shoulder": "오른쪽 어깨",
    "left_hip": "왼쪽 고관절",
    "right_hip": "오른쪽 고관절",
    "left_knee": "왼쪽 무릎",
    "right_knee": "오른쪽 무릎",
}


def _force_part_label(finding: Any) -> str:
    """ForcePatternFinding 의 부위 라벨 — joint_hint 우선, 없으면 generic."""
    hint = getattr(finding, "joint_hint", None)
    if isinstance(hint, str) and hint:
        return hint
    return _GENERIC_PART


def _body_part_label(finding: Any) -> str:
    """BodyComparisonFinding 의 부위 라벨 — joint_key 매핑, 없으면 generic."""
    joint_key = getattr(finding, "joint_key", None)
    if isinstance(joint_key, str) and joint_key in _JOINT_KEY_LABELS:
        return _JOINT_KEY_LABELS[joint_key]
    return _GENERIC_PART


def build_canned_hook(
    findings: list,
    *,
    source_report: str,
) -> CoachCommentHook:
    """findings → canned CoachCommentHook (Gemini 실패/미사용 시 fallback 경로).

    finding 의 기존 canned interpretation 텍스트 (이미 객관·number-free KO) 만 조합한다.
    점수/좌표/판정/도(degree)/% mint 0 (D-04/D-05). LLM 미사용. source_report 는
    provenance scalar 로 hook 에 박제 (D-02).

    Args:
        findings: ForcePatternFinding[] 또는 BodyComparisonFinding[] (단일 report).
        source_report: 'forcePatternInference' / 'bodyComparisonReport'.

    Returns:
        CoachCommentHook — coach_comment / reviewed_by = None (v1, D-06).
    """
    is_force = source_report == "forcePatternInference"

    summaries: list[str] = []
    questions: list[str] = []
    cues: list[str] = []

    for finding in findings or []:
        if is_force:
            interpretation = getattr(finding, "interpretation", None)
            part = _force_part_label(finding)
            question = _FORCE_QUESTION_TEMPLATE.format(part=part)
            recommendation = None
        else:
            interpretation = getattr(finding, "body_type_interpretation", None)
            part = _body_part_label(finding)
            question = _BODY_QUESTION_TEMPLATE.format(part=part)
            recommendation = getattr(finding, "recommendation", None)

        if isinstance(interpretation, str) and interpretation:
            summaries.append(interpretation)
        if question not in questions:
            questions.append(question)
        if (
            isinstance(recommendation, str)
            and recommendation
            and recommendation not in cues
        ):
            cues.append(recommendation)

    if summaries:
        auto_findings_summary = " ".join(summaries)
    else:
        auto_findings_summary = (
            _FORCE_NO_FINDINGS_SUMMARY if is_force else _BODY_NO_FINDINGS_SUMMARY
        )

    if not questions:
        # 강사 질문이 없으면 일반 점검 질문 1개 (number-free).
        questions = [_GENERIC_QUESTION]

    # openQuestionsForCoach 1~3 캡.
    questions = questions[:3]

    # suggestedCues 2~4 (default 로 보강해 최소 2개 보장 — number-free).
    if not cues:
        cues = list(_FORCE_CUE_DEFAULTS if is_force else _BODY_CUE_DEFAULTS)
    cues = cues[:4]
    if len(cues) < 2:
        for extra in _FORCE_CUE_DEFAULTS if is_force else _BODY_CUE_DEFAULTS:
            if extra not in cues:
                cues.append(extra)
            if len(cues) >= 2:
                break

    return CoachCommentHook(
        auto_findings_summary=auto_findings_summary,
        open_questions_for_coach=questions,
        suggested_cues=cues,
        coach_comment=None,
        reviewed_by=None,
        source_report=source_report,
    )


def _get_payload(bundle: Any, *, attr: str) -> Any:
    """bundle 의 report payload 를 attribute access / dict access 둘 다로 읽는다.

    duck-type (iter-4 MEDIUM-2) — Wave 0 테스트는 SimpleNamespace, Wave 1 pipeline 은
    실 CoachHookBundle 로 동일 경로. Pydantic class 참조 없음.
    """
    if bundle is None:
        return None
    if isinstance(bundle, dict):
        return bundle.get(attr)
    return getattr(bundle, attr, None)


def _clean_str_list(value: Any) -> list[str]:
    """LLM list payload → trim 된 non-empty str 만 (순서보존 dedupe).

    빈/공백 str · 비-str(중첩 list/dict 포함) 를 제거해 `CoachCommentHook` 의 list[str]
    of non-empty str 검증을 항상 통과시킨다.
      · CR-01 (review): 빈 str (흔한 LLM 산출 artifact — 후행 빈 원소/공백 큐) 가
        dataclass 경계 `_validate_str_list` 에서 ValueError → resolve_coach_hook_bundle
        밖으로 전파 → pipeline broad except → fail_analysis(server_error) 하던
        크래시 경로를 차단한다 (D-08: hook 은 best-effort, 분석 절대 실패 안 함).
      · WR-01 (review): dedupe — cap 은 호출부에서 canned 와 동일하게 slice.
    """
    if not isinstance(value, (list, tuple)):
        return []
    cleaned: list[str] = []
    for item in value:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped and stripped not in cleaned:
                cleaned.append(stripped)
    return cleaned


def _payload_to_hook(payload: Any, *, source_report: str) -> CoachCommentHook:
    """LLM payload (CoachCommentHookPayload duck object) → CoachCommentHook.

    auto_findings_summary / open_questions_for_coach / suggested_cues 를 getattr-or-key
    로 읽어 변환 (Pydantic class 참조 없음 — duck-type). coach_comment / reviewed_by =
    None (v1, D-06).

    필드가 누락/빈 값/빈-str-원소인 degenerate payload (Wave 0 duck object · LLM 산출
    artifact 등) 는 정제 + canned default 로 보강해 dataclass 경계가 raise 하지 않게
    한다 (COACH-01 SC#2 — 항상 hook, CR-01 — 분석 절대 실패 안 함).
    """

    def _read(name: str) -> Any:
        if isinstance(payload, dict):
            return payload.get(name)
        return getattr(payload, name, None)

    is_force = source_report == "forcePatternInference"

    summary = _read("auto_findings_summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = _FORCE_NO_FINDINGS_SUMMARY if is_force else _BODY_NO_FINDINGS_SUMMARY
    else:
        summary = summary.strip()

    # CR-01/WR-01: 빈/공백 str 제거 + dedupe + canned 와 동일 cap (질문 3 / 큐 4, 최소 2).
    questions = _clean_str_list(_read("open_questions_for_coach"))[:3]
    if not questions:
        questions = [_GENERIC_QUESTION]

    cues = _clean_str_list(_read("suggested_cues"))[:4]
    if not cues:
        cues = list(_FORCE_CUE_DEFAULTS if is_force else _BODY_CUE_DEFAULTS)
    elif len(cues) < 2:
        for extra in _FORCE_CUE_DEFAULTS if is_force else _BODY_CUE_DEFAULTS:
            if extra not in cues:
                cues.append(extra)
            if len(cues) >= 2:
                break

    return CoachCommentHook(
        auto_findings_summary=summary,
        open_questions_for_coach=questions,
        suggested_cues=cues,
        coach_comment=None,
        reviewed_by=None,
        source_report=source_report,
    )


def resolve_coach_hook_bundle(
    bundle,
    *,
    force_findings: list,
    body_findings: list,
) -> tuple[CoachCommentHook, CoachCommentHook]:
    """per-report fallback 정책의 단일 소유처 (iter-3 HIGH-1 pure helper).

    `bundle` = `CoachHookBundle | None` (Gemini writer 산출, duck object) + 양 findings
    를 받아 `(force_hook, body_hook)` 두 CoachCommentHook 를 반환하는 **pure** helper
    (pipeline / Firestore I/O 무관, gemini.schemas import 안 함 — MEDIUM-2).

    정책:
      · bundle is None → 양쪽 canned (build_canned_hook).
      · bundle.force_pattern_inference 만 present → force 변환 + body canned.
      · full → 양쪽 변환.
    항상 tuple 양 원소 모두 CoachCommentHook (None 아님 — COACH-01 SC#2).
    """
    force_payload = _get_payload(bundle, attr="force_pattern_inference")
    body_payload = _get_payload(bundle, attr="body_comparison_report")

    if force_payload is not None:
        force_hook = _payload_to_hook(
            force_payload, source_report="forcePatternInference"
        )
    else:
        force_hook = build_canned_hook(
            force_findings, source_report="forcePatternInference"
        )

    if body_payload is not None:
        body_hook = _payload_to_hook(
            body_payload, source_report="bodyComparisonReport"
        )
    else:
        body_hook = build_canned_hook(
            body_findings, source_report="bodyComparisonReport"
        )

    return force_hook, body_hook


__all__ = ["build_canned_hook", "resolve_coach_hook_bundle"]
