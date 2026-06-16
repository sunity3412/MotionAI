"""Phase 11 — CoachCommentHook builder + per-report fallback resolver (Wave 1 fills).

본 모듈은 finding → CoachCommentHook 변환 / per-report fallback 정책의 단일 소유처다.
`coach_hook.py` (dataclass + pure validator) 와 분리한 이유는 HIGH-3 순환 import 차단:
  · `force_pattern.py` / `body_normalizer.py` 가 `coach_hook.CoachCommentHook` 을 import.
  · builder 는 `ForcePatternFinding` / `BodyComparisonFinding` 를 알아야 하지만,
    coach_hook.py 가 그것을 import 하면 순환 (`force_pattern → coach_hook → force_pattern`).
  · 따라서 builder 는 별도 모듈이고, finding 클래스는 `TYPE_CHECKING` 가드 / local import
    로만 참조한다 (모듈 로드 시점 top-level import 금지).

Wave 0 (Plan 11-00) = stub (NotImplementedError) — Wave 0 test scaffold 가 top-level
import 해도 collection 에러가 아니라 호출 시 RED 가 되도록 보장 (WARNING-1 collection-green).
Wave 1 (Plan 11-01 Task 1) = canned 변환 + per-report fallback 본체 박제.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .coach_hook import CoachCommentHook

if TYPE_CHECKING:  # 모듈 로드 시점 import 금지 (HIGH-3 순환 차단) — 타입 힌트 전용.
    from .body_normalizer import BodyComparisonFinding
    from .force_pattern import ForcePatternFinding


def build_canned_hook(
    findings: list,
    *,
    source_report: str,
) -> CoachCommentHook:
    """findings → canned CoachCommentHook (Gemini 실패/미사용 시 fallback 경로).

    Wave 1 (Plan 11-01 Task 1) 이 findings 의 canned interpretation 을 자연어 hook 으로
    변환한다 (점수/좌표/판정/도(degree)/% mint 0 — D-04/D-05). source_report 는
    provenance scalar 로 hook 에 박제 (D-02).

    Raises:
        NotImplementedError: Wave 0 stub. Wave 1 (11-01 Task 1) 이 채운다.
    """
    raise NotImplementedError("Wave 1: 11-01 Task 1")


def resolve_coach_hook_bundle(
    bundle,
    *,
    force_findings: list,
    body_findings: list,
) -> tuple[CoachCommentHook, CoachCommentHook]:
    """per-report fallback 정책의 단일 소유처 (iter-3 HIGH-1 pure helper).

    `bundle` = `CoachHookBundle | None` (Gemini writer 산출) + 양 findings 를 받아
    `(force_hook, body_hook)` 두 CoachCommentHook 를 반환하는 **pure** helper
    (pipeline / Firestore I/O 무관, gemini.schemas import 안 함 — MEDIUM-2).

    정책 (Wave 1 본체):
      · bundle is None → 양쪽 canned (build_canned_hook).
      · bundle.force_pattern_inference 만 present → force 변환 + body canned.
      · full → 양쪽 변환.
    항상 tuple 양 원소 모두 CoachCommentHook (None 아님 — COACH-01 SC#2).

    Raises:
        NotImplementedError: Wave 0 stub. Wave 1 (11-01 Task 1) 이 채운다.
    """
    raise NotImplementedError("Wave 1: 11-01 Task 1")


__all__ = ["build_canned_hook", "resolve_coach_hook_bundle"]
