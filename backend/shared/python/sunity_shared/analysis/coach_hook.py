"""Phase 11 — CoachCommentHook 데이터 구조 + pure validator (D-02 per-report 부착 단위).

박제 정신:
  · COACH-01 SC#1 — CoachCommentHook 타입이 3-way lockstep 으로 추가 (analysis.ts ↔
    models.py re-export ↔ docs/contract.md §8/§9.11).
  · D-02 — hook 은 per-report 단위 (ForcePatternInference / BodyComparisonReport 각각
    `coachCommentHook?` 부착). `source_report` scalar = v2 콘솔 집계 provenance.
  · D-06 — coach_comment / reviewed_by 는 v1 항상 None (강사 입력/리뷰는 v2 console).

HIGH-3 모듈 분리 (순환 import 차단):
  · 본 모듈은 **frozen dataclass + pure validator helper 만** 보유한다.
  · `ForcePatternFinding` / `BodyComparisonFinding` 등 finding 클래스를 **import 하지
    않는다** (모듈 로드 시점 import 금지). 이유: `force_pattern.py` 와
    `body_normalizer.py` 가 `coach_hook.CoachCommentHook` 을 import 하므로, 본 모듈이
    그 모듈을 역참조하면 `force_pattern → coach_hook → force_pattern` 순환 발생.
  · canned/builder 로직 (finding → hook 변환) 은 별도 모듈 `coach_hook_builder.py` 에 둔다.

list 필드 = list[str] 전용 — nested array (list[dict] / list[list]) 금지
([[firestore-nested-array-flat]] 정합). `__post_init__` strict 검증으로 dataclass
경계에서 차단 + Wave 1 Firestore 전용 validator (_validate_coach_comment_hook) 가
write 경로에서 재차단.

TS 미러: app/src/types/analysis.ts CoachCommentHook interface.
변경 시 TS + models.py re-export + docs/contract.md §8/§9.11 동시 갱신 (CLAUDE.md Cross-cutting).
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _validate_str_list(value: object, *, field: str) -> None:
    """list[str] of non-empty str strict 검증 (nested array reject).

    list[dict] / list[list] / 빈 str / 비-list 입력 모두 ValueError. ForcePatternInference
    .__post_init__ 의 warnings 검증 패턴 mirror — dataclass 경계 backstop.

    Raises:
        ValueError: value 가 list[str] of non-empty str 가 아닐 때.
    """
    if not isinstance(value, list):
        raise ValueError(
            f"{field} must be list[str] (contract list[str] only), "
            f"got {type(value).__name__}"
        )
    for i, item in enumerate(value):
        # nested array / dict 명시 reject (list[dict] / list[list] 차단 — D-02).
        if isinstance(item, (list, dict)):
            raise ValueError(
                f"{field}[{i}] nested {type(item).__name__} reject "
                f"(list[str] only — [[firestore-nested-array-flat]])"
            )
        if not isinstance(item, str) or not item:
            raise ValueError(
                f"{field}[{i}] must be non-empty str, "
                f"got {type(item).__name__}={item!r}"
            )


@dataclass(frozen=True)
class CoachCommentHook:
    """리포트 1건에 부착되는 LLM 코칭 코멘트 hook (D-02 per-report 단위).

    Phase 11 Wave 1 (coach_hook_builder / GeminiCoachHookWriter) 이 findings 의 canned
    interpretation 을 자연어로 번역해 `auto_findings_summary` / `open_questions_for_coach`
    / `suggested_cues` 를 채운다. coach_comment / reviewed_by 는 v2 강사 콘솔 입력용으로
    v1 에서는 항상 None (D-06).

    필드 순서: 3 non-default (str + 2 list) → 3 default (None) — Python dataclass rule
    상 default 이후 non-default 금지 (force_pattern.py trailing default precedent).

    필드:
      auto_findings_summary: LLM 자연어 요약 (findings interpretation 번역). non-empty str.
      open_questions_for_coach: 강사에게 던지는 질문 (list[str], 빈 list 허용).
      suggested_cues: 수강생용 큐 (list[str], 빈 list 허용).
      coach_comment: v2 강사 입력 — v1 항상 None (D-06).
      reviewed_by: v2 리뷰어 — v1 항상 None (D-06).
      source_report: provenance scalar ('forcePatternInference' / 'bodyComparisonReport')
        — v2 콘솔 집계용 (D-02). v1 builder 가 set, None 허용.
    """

    auto_findings_summary: str
    open_questions_for_coach: list[str]
    suggested_cues: list[str]
    coach_comment: str | None = None
    reviewed_by: str | None = None
    source_report: str | None = None

    def __post_init__(self) -> None:
        # auto_findings_summary non-empty str.
        if not isinstance(self.auto_findings_summary, str) or not self.auto_findings_summary:
            raise ValueError(
                "auto_findings_summary must be non-empty str (LLM 자연어 요약)"
            )
        # list 필드 = list[str] 전용 strict (nested array reject — D-02).
        _validate_str_list(
            self.open_questions_for_coach, field="open_questions_for_coach"
        )
        _validate_str_list(self.suggested_cues, field="suggested_cues")
        # coach_comment / reviewed_by = str | None (v1 항상 None — D-06).
        if self.coach_comment is not None and not isinstance(self.coach_comment, str):
            raise ValueError(
                f"coach_comment must be str | None, "
                f"got {type(self.coach_comment).__name__}"
            )
        if self.reviewed_by is not None and not isinstance(self.reviewed_by, str):
            raise ValueError(
                f"reviewed_by must be str | None, "
                f"got {type(self.reviewed_by).__name__}"
            )
        # source_report = str | None (provenance scalar).
        if self.source_report is not None and not isinstance(self.source_report, str):
            raise ValueError(
                f"source_report must be str | None, "
                f"got {type(self.source_report).__name__}"
            )


__all__ = ["CoachCommentHook", "_validate_str_list"]
