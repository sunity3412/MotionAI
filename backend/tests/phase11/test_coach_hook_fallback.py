"""Phase 11 Wave 0 — writer seam (None-only) + pure resolver fallback gate.

iter-4 HIGH-1 책임 경계 분리 (writer 가 canned 를 반환한다고 읽히지 않게 2 묶음):

(i) writer seam tests — GeminiCoachHookWriter.build_coach_hooks(...) 는 **None 만**
    반환 (writer 는 canned 를 만들지 않음): api_key_loader 실패 / 4xx / guard reject /
    retry exhausted → None. 5xx retry seam (iter-2 HIGH-1): 1차 5xx → retry → 2차 성공
    (bundle 반환) / 1차 4xx → 즉시 None. seam = api_key_loader/None-return — writer 의
    private client 속성 shape 직접 검사 금지 (WARNING-2).

(ii) pure resolver tests — resolve_coach_hook_bundle(bundle, *, force_findings,
     body_findings) 3 케이스 (None / partial / full) → 항상 tuple 양 원소 모두
     CoachCommentHook (None 아님 — COACH-01 SC#2). resolver 는 pure (gemini.schemas
     import 안 함, MEDIUM-2) — bundle 입력은 SimpleNamespace duck object.

"분석 status done(절대 fail 안 함)" 보장은 Wave 1 pipeline wiring / 통합 레벨 (D-08,
ROADMAP SC#5) — Wave 0 pure helper 테스트는 Firestore/pipeline 완료 상태 미주장.

Wave 1 심볼 (GeminiCoachHookWriter / build_coach_hooks / resolve_coach_hook_bundle 실
본체) 은 top-level import 금지 — test body 안 getattr 으로 찾아 부재 시 RED (iter-4 HIGH-2).
"""

from __future__ import annotations

import importlib
import types

import pytest

from sunity_shared.analysis import coach_hook_builder
from sunity_shared.analysis.coach_hook import CoachCommentHook


# ── (i) writer seam — None-only ────────────────────────────────────────────


def _load_writer_class():
    """gemini.coach_hook_writer.GeminiCoachHookWriter 를 getattr 로 찾는다.

    Wave 0 에서는 모듈/클래스 미존재 — top-level import 금지라 importlib 로 시도하고
    부재 시 None 반환 (caller 가 assert ... is not None → RED).
    """
    try:
        mod = importlib.import_module("sunity_shared.gemini.coach_hook_writer")
    except ModuleNotFoundError:
        return None
    return getattr(mod, "GeminiCoachHookWriter", None)


def test_writer_returns_none_on_api_key_failure() -> None:
    """api_key_loader 실패 → build_coach_hooks(...) is None (writer 는 canned X)."""
    writer_cls = _load_writer_class()
    assert writer_cls is not None, "GeminiCoachHookWriter 미구현 (Wave 1)"

    def failing_loader() -> str:
        raise RuntimeError("no api key")

    writer = writer_cls(api_key_loader=failing_loader)
    result = writer.build_coach_hooks(force_findings=[], body_findings=[])
    assert result is None


def test_writer_returns_none_on_4xx() -> None:
    """1차 4xx → 즉시 None (retry 안 함)."""
    writer_cls = _load_writer_class()
    assert writer_cls is not None, "GeminiCoachHookWriter 미구현 (Wave 1)"

    class _FourXXClient:
        def generate(self, *_a, **_k):
            raise _ApiError(status=400)

    writer = writer_cls(api_key_loader=lambda: "k", client=_FourXXClient())
    assert writer.build_coach_hooks(force_findings=[], body_findings=[]) is None


def test_writer_retries_on_5xx_then_succeeds() -> None:
    """1차 5xx → retry → 2차 성공 (bundle 반환, None 아님). iter-2 HIGH-1 seam."""
    writer_cls = _load_writer_class()
    assert writer_cls is not None, "GeminiCoachHookWriter 미구현 (Wave 1)"

    calls = {"n": 0}

    class _FlakyClient:
        def generate(self, *_a, **_k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise _ApiError(status=503)
            # 2차 성공 — bundle duck object 반환 (실 schema 는 Wave 1).
            return types.SimpleNamespace(
                force_pattern_inference=object(), body_comparison_report=object()
            )

    writer = writer_cls(api_key_loader=lambda: "k", client=_FlakyClient())
    result = writer.build_coach_hooks(force_findings=[], body_findings=[])
    assert result is not None
    assert calls["n"] == 2, "5xx 후 정확히 1회 retry"


def test_writer_returns_none_on_retry_exhausted() -> None:
    """5xx 가 retry 후에도 지속 → None (canned 변환은 resolver 책임)."""
    writer_cls = _load_writer_class()
    assert writer_cls is not None, "GeminiCoachHookWriter 미구현 (Wave 1)"

    class _Always5xx:
        def generate(self, *_a, **_k):
            raise _ApiError(status=500)

    writer = writer_cls(api_key_loader=lambda: "k", client=_Always5xx())
    assert writer.build_coach_hooks(force_findings=[], body_findings=[]) is None


class _ApiError(Exception):
    """테스트용 status 부착 예외 (Wave 1 실 APIError seam mirror)."""

    def __init__(self, *, status: int) -> None:
        super().__init__(f"api error {status}")
        self.status = status
        self.status_code = status


# ── (ii) pure resolver — 항상 양쪽 non-None CoachCommentHook ────────────────


def test_resolve_coach_hook_bundle(golden_force_finding, golden_body_finding) -> None:
    """resolve_coach_hook_bundle 3 케이스 → 항상 (CoachCommentHook, CoachCommentHook).

    bundle 입력 = SimpleNamespace duck object (gemini.schemas 미존재로도 작성 가능,
    Wave 1 실 Pydantic payload 도 동일 duck 경로). resolver 가 NotImplementedError
    이므로 현재 RED — Wave 1 GREEN.
    """
    resolver = getattr(coach_hook_builder, "resolve_coach_hook_bundle", None)
    assert resolver is not None, "resolve_coach_hook_bundle 미구현"

    force = [golden_force_finding]
    body = [golden_body_finding]

    # case 1: bundle None → 양쪽 canned.
    fh, bh = resolver(None, force_findings=force, body_findings=body)
    assert isinstance(fh, CoachCommentHook) and isinstance(bh, CoachCommentHook)

    # case 2: partial — force payload 만 present.
    partial = types.SimpleNamespace(
        force_pattern_inference=object(), body_comparison_report=None
    )
    fh, bh = resolver(partial, force_findings=force, body_findings=body)
    assert isinstance(fh, CoachCommentHook) and isinstance(bh, CoachCommentHook)

    # case 3: full — 양쪽 payload present.
    full = types.SimpleNamespace(
        force_pattern_inference=object(), body_comparison_report=object()
    )
    fh, bh = resolver(full, force_findings=force, body_findings=body)
    assert isinstance(fh, CoachCommentHook) and isinstance(bh, CoachCommentHook)


# ── (iii) schema extra=forbid (Wave 1 Pydantic — getattr only) ─────────────


def test_bundle_extra_forbid() -> None:
    """CoachHookBundle / CoachCommentHookPayload 가 extra=forbid (unknown 필드 reject).

    Wave 1 심볼 — top-level import 금지라 importlib + getattr 으로 찾고 부재 시 RED.
    LLM 이 mint 한 unexpected 필드가 schema 를 통과하지 못하게 박제 (T-11-01/02 정합).
    """
    try:
        schemas = importlib.import_module("sunity_shared.gemini.schemas")
    except ModuleNotFoundError:
        schemas = None
    payload_cls = getattr(schemas, "CoachCommentHookPayload", None) if schemas else None
    assert payload_cls is not None, (
        "CoachCommentHookPayload 미구현 (Wave 1) — extra=forbid schema 필요"
    )
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        payload_cls.model_validate(
            {
                "autoFindingsSummary": "요약",
                "openQuestionsForCoach": ["q"],
                "suggestedCues": ["c"],
                "unexpected": 1,
            }
        )
