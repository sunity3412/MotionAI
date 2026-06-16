"""Phase 11 Wave 0 — translation-only forbidden-phrase + hook-scoped number guard.

3 게이트 (collection-green, intentional RED — Wave 1 GREEN):
  (a) D-05 forbidden-pattern: golden finding → build_canned_hook 출력 텍스트에 점수/판정/
      좌표 표현 0 (호출이 NotImplementedError 이므로 현재 RED).
  (b) hook-scoped all-digit reject (iter-2 BLOCKER-2 + iter-3 HIGH-2): hook 전용 가드가
      도/% 뿐 아니라 모든 Arabic digit 에 ValueError. bare/measurement 수치 포함
      (number-free lock, D-04). hook 가드 미구현 → RED.
  (c) 글로벌 가드 비회귀 (iter-2 BLOCKER-2 핵심): 기본 _enforce_no_reject_patterns 가
      "30도"/"50%" 를 절대 reject 안 함 — scene_finder 등 정당 사용처 회귀 0.
      현재 PASS (regression guard — Wave 1 이 글로벌 오염 시 RED).
  (d) score reject: 기본 가드가 "87점"/"훌륭" → ValueError (canned fallback 트리거).

Wave 1 심볼 (_enforce_no_hook_number_patterns / forbid_measurement_units / build_canned_hook)
은 top-level import 금지 — test body 안 getattr / signature 검사로만 참조 (iter-4 HIGH-2).
"""

from __future__ import annotations

import inspect

import pytest

from sunity_shared.analysis import coach_hook_builder
from sunity_shared.gemini import guardrails


# ── (a) D-05 forbidden-pattern (canned hook 출력) ──────────────────────────

_FORBIDDEN = ("점", "/10", "좌표", "x=", "y=", "잘했다", "훌륭", "완벽", "양호")


@pytest.mark.parametrize("phrase", _FORBIDDEN)
def test_canned_hook_has_no_forbidden_phrase(
    phrase: str, golden_force_finding
) -> None:
    """canned hook 의 모든 텍스트 필드 blob 에 금지 표현 0 (D-05).

    Wave 0: build_canned_hook 가 NotImplementedError → RED. Wave 1 구현 후 GREEN.
    """
    hook = coach_hook_builder.build_canned_hook(
        [golden_force_finding], source_report="forcePatternInference"
    )
    blob = " ".join(
        [
            hook.auto_findings_summary,
            *hook.open_questions_for_coach,
            *hook.suggested_cues,
        ]
    )
    assert phrase not in blob, f"canned hook 에 금지 표현 {phrase!r} 발견: {blob!r}"


# ── (b) hook-scoped all-digit reject (number-free lock, D-04) ──────────────

_HOOK_NUMBER_CASES = (
    "무릎이 23도 차이",
    "23°",
    "23 deg",
    "15%",
    # bare/measurement 수치도 차단 (iter-3 HIGH-2 number-free lock).
    "3초",
    "2회",
    "15cm",
    "180",
)


@pytest.mark.parametrize("text", _HOOK_NUMBER_CASES)
def test_hook_guard_rejects_numbers(text: str) -> None:
    """hook 전용 가드가 모든 Arabic digit (도/% + bare/measurement) reject.

    Wave 1 심볼 — `_enforce_no_hook_number_patterns` 가 있으면 사용, 없으면
    `_enforce_no_reject_patterns` 가 `forbid_measurement_units` 파라미터를 얻었는지
    런타임 확인. 둘 다 없으면 assertion failure (RED).
    """
    hook_guard = getattr(guardrails, "_enforce_no_hook_number_patterns", None)
    if hook_guard is not None:
        with pytest.raises(ValueError):
            hook_guard(text)
        return
    # fallback: forbid_measurement_units 파라미터가 생겼는지 signature 확인.
    params = inspect.signature(guardrails._enforce_no_reject_patterns).parameters
    assert "forbid_measurement_units" in params, (
        "hook-scoped number guard 미구현 (Wave 1): "
        "_enforce_no_hook_number_patterns 부재 AND "
        "_enforce_no_reject_patterns 에 forbid_measurement_units 없음"
    )
    with pytest.raises(ValueError):
        guardrails._enforce_no_reject_patterns(
            text, context="coach_hook", forbid_measurement_units=True
        )


# ── (c) 글로벌 가드 비회귀 (regression guard — 현재 PASS) ──────────────────


def test_global_guard_allows_degree_percent() -> None:
    """기본 _enforce_no_reject_patterns 가 "30도"/"50%" 를 절대 reject 안 함.

    scene_finder / reference_extractor 가 "30도"/"50%" 를 정당하게 쓰므로 글로벌
    가드 오염 0 (iter-2 BLOCKER-2). 현재 PASS — Wave 1 이 글로벌 _SCORE_PATTERNS
    등에 도/% 를 추가하면 이 테스트가 RED 가 되어 회귀를 잡는다.
    """
    guardrails._enforce_no_reject_patterns("등이 30도 이상 후굴", context="scene_finder")
    guardrails._enforce_no_reject_patterns(
        "신체의 50% 이상 가려짐", context="scene_finder"
    )


# ── (d) score reject (canned fallback 트리거) ──────────────────────────────


@pytest.mark.parametrize("text", ("87점", "이건 정말 훌륭"))
def test_guard_rejects_score(text: str) -> None:
    """기본 가드가 점수/판정 어휘 → ValueError (Wave 1 canned fallback 경로).

    현재 guardrails 가 점수("87점")/판정("훌륭")를 잡으므로 PASS — Wave 1 이
    이 가드를 hook writer 출력에 적용해 fallback 으로 전환.
    """
    with pytest.raises(ValueError):
        guardrails._enforce_no_reject_patterns(text, context="coach_hook")
