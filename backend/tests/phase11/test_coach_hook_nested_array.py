"""Phase 11 Wave 0 — 전용 _validate_coach_comment_hook gate (iter-2 BLOCKER-1).

nested-array 차단 기준이 generic `_validate_dict_only_scalars` 가 아니라 **전용
`_validate_coach_comment_hook`** 임을 박제한다. generic validator 는 list[dict] 를
scalar-only 로 허용했던 root cause (iter-2 BLOCKER-1) — 전용 validator 가 그것을 차단.

force path (_validate_force_pattern_inference 안 coachCommentHook 키) AND body path
(complete_analysis body precheck) 둘 다 검증.

케이스:
  (1) valid flat hook dict (list[str] 필드) → force/body 통과.
  (2) coachCommentHook 안 openQuestionsForCoach 를 list[dict] → ValueError (force AND body).
  (3) coachCommentHook 안 nested list (list[list]) → ValueError.
  (4) coachCommentHook 안 unknown key → ValueError.

Wave 0: `_validate_coach_comment_hook` 미존재 → 존재 assert 가 RED. validator 브랜치
미구현이므로 force/body reject 케이스도 RED (Wave 1 GREEN). top-level import 는
현재 존재하는 firestore_admin 심볼만 (iter-4 HIGH-2).
"""

from __future__ import annotations

import pytest

from sunity_shared import firestore_admin


def _valid_hook_dict() -> dict:
    """list[str] 전용 valid hook dict (TS camelCase 키)."""
    return {
        "autoFindingsSummary": "홀드 구간에서 힘이 부족할 가능성이 있어요.",
        "openQuestionsForCoach": ["어깨 정렬은 의도한 건가요?"],
        "suggestedCues": ["광배를 먼저 당겨보세요."],
        "coachComment": None,
        "reviewedBy": None,
        "sourceReport": "forcePatternInference",
    }


def test_dedicated_validator_exists() -> None:
    """전용 _validate_coach_comment_hook 가 존재해야 함 (iter-2 BLOCKER-1).

    Wave 0: 부재 → RED. Wave 1 (Plan 11-01) 이 firestore_admin 에 신설.
    """
    validator = getattr(firestore_admin, "_validate_coach_comment_hook", None)
    assert validator is not None, (
        "_validate_coach_comment_hook 미구현 (Wave 1) — generic "
        "_validate_dict_only_scalars 가 list[dict] 를 허용하던 root cause 차단 필요"
    )


# ── (1) valid hook → force path AND body path 통과 ─────────────────────────


def test_valid_hook_passes_force_path() -> None:
    """valid flat hook 이 _validate_force_pattern_inference (coachCommentHook 키) 통과."""
    payload = {
        "version": "1.0",
        "warnings": [],
        "coachCommentHook": _valid_hook_dict(),
    }
    # Wave 1 이 _validate_force_pattern_inference 에 전용 hook 브랜치 추가 — 그 전까지
    # 현재 generic dict 브랜치가 raise 하므로 RED (Wave 1 GREEN).
    firestore_admin._validate_force_pattern_inference(payload)


def test_valid_hook_passes_body_precheck() -> None:
    """valid flat hook 이 body path (complete_analysis bodyComparisonReport precheck) 통과.

    Wave 1 이 body precheck 에 전용 hook validator 브랜치 추가. Wave 0 에서는 전용
    validator 부재 → 직접 호출이 RED (validator None).
    """
    validator = getattr(firestore_admin, "_validate_coach_comment_hook", None)
    assert validator is not None, "_validate_coach_comment_hook 미구현 (Wave 1, body path)"
    validator(_valid_hook_dict(), path="bodyComparisonReport.coachCommentHook")


# ── (2) list[dict] → ValueError (force AND body — BLOCKER-1 핵심) ──────────


def test_list_of_dict_rejected_force_path() -> None:
    """coachCommentHook.openQuestionsForCoach 가 list[dict] → force path ValueError."""
    hook = _valid_hook_dict()
    hook["openQuestionsForCoach"] = [{"q": "어깨?"}]  # list[dict] — generic 이 허용하던 case
    payload = {"version": "1.0", "warnings": [], "coachCommentHook": hook}
    with pytest.raises(ValueError):
        firestore_admin._validate_force_pattern_inference(payload)


def test_list_of_dict_rejected_body_path() -> None:
    """coachCommentHook.openQuestionsForCoach 가 list[dict] → body path ValueError."""
    validator = getattr(firestore_admin, "_validate_coach_comment_hook", None)
    assert validator is not None, "_validate_coach_comment_hook 미구현 (Wave 1, body path)"
    hook = _valid_hook_dict()
    hook["openQuestionsForCoach"] = [{"q": "어깨?"}]
    with pytest.raises(ValueError):
        validator(hook, path="bodyComparisonReport.coachCommentHook")


# ── (3) nested list (list[list]) → ValueError ──────────────────────────────


def test_nested_list_rejected_force_path() -> None:
    """coachCommentHook.suggestedCues 가 nested list → force path ValueError."""
    hook = _valid_hook_dict()
    hook["suggestedCues"] = [["광배", "코어"]]  # list[list]
    payload = {"version": "1.0", "warnings": [], "coachCommentHook": hook}
    with pytest.raises(ValueError):
        firestore_admin._validate_force_pattern_inference(payload)


# ── (4) unknown key → ValueError ───────────────────────────────────────────


def test_unknown_key_rejected_body_path() -> None:
    """coachCommentHook 안 화이트리스트 외 key → body path ValueError."""
    validator = getattr(firestore_admin, "_validate_coach_comment_hook", None)
    assert validator is not None, "_validate_coach_comment_hook 미구현 (Wave 1)"
    hook = _valid_hook_dict()
    hook["unexpectedField"] = "x"
    with pytest.raises(ValueError):
        validator(hook, path="bodyComparisonReport.coachCommentHook")
