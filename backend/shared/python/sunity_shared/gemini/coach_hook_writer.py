"""Phase 11 — text-only GeminiCoachHookWriter (CoachCommentHook 생성, single call).

박제 정신 (D-03 [2026-06-16 review correction], BLOCKER-1):
  · 기존 Vision writer (coach_writer_v2.py — joint-card / 영상 입력 의존) 는 **무수정**.
    본 모듈은 **별도 text-only** writer 다.
  · 1회 분석당 hook 호출 1회로 두 리포트(ForcePatternInference / BodyComparisonReport)
    의 hook 을 함께 산출한다 (single call) — report 당 1회 아님.
  · 영상 업로드 / Files API / 영상 입력 경로 **미접촉** — `client.models.generate_content`
    text-only path 만 사용 (영상 입력 seam 없음).

iter-3 HIGH-1 — bundle|None only:
  · build_coach_hooks(...) 는 **parsed CoachHookBundle 또는 None 만** 반환한다.
    canned hook 을 만들지 않는다 (None on: api_key_loader 실패 / 4xx / guard reject /
    retry 소진). per-report 폴백은 coach_hook_builder.resolve_coach_hook_bundle 가 소유.

iter-2 HIGH-1 — schema-strip config 재사용:
  · client.py 의 `_strip_unsupported_schema_keys` / `_HTTP_TIMEOUT_MS` 를 import 해서
    재사용한다 — `CoachHookBundle` 은 nested 라 `$defs` 가 생겨 raw 주입 시 live 400.

iter-2 BLOCKER-2 + iter-3 HIGH-2 — number-free 가드:
  · raw text 에 `_enforce_no_reject_patterns(..., forbid_measurement_units=True)` 를
    적용 — 점수/판정 + 모든 Arabic digit(도/%/cm/초/회/bare) reject → ValueError →
    None 반환 (reject-and-fallback, 런타임 sanitize 금지 — D-05).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from pydantic import ValidationError

# schema-strip config 재사용 (iter-2 HIGH-1) — client.py 의 module-level helper/상수.
from .client import _HTTP_TIMEOUT_MS, _default_api_key_loader, _strip_unsupported_schema_keys
from .config import resolve_model
from .guardrails import _enforce_no_reject_patterns
from .schemas import CoachHookBundle

log = logging.getLogger(__name__)


# 분석 1회당 hook 1회 호출 (single call). force/body findings 를 구조화 텍스트로
# 묶어 두 report hook 을 한 번에 산출한다. 점수/좌표/도(degree)/% 출력 금지 (number-free).
_HOOK_SYSTEM_PROMPT = (
    "당신은 폴스포츠 코칭 보조 작가입니다. 주어진 finding 들의 한국어 해설을 "
    "강사와 수강생이 읽을 자연어 hook 으로 풀어 씁니다. 규칙: "
    "(1) finding 자연어 풀이만 — 수치·좌표·점수·판정·숫자·도(degree)·% 출력 금지. "
    "(2) '잘했다'/'훌륭'/'완벽'/'양호' 같은 사람 판단 어휘 금지 — '가능성' 언어 유지. "
    "(3) force/body 각 report 에 대해 autoFindingsSummary(한 문단), "
    "openQuestionsForCoach(강사 질문 1~3), suggestedCues(수강생 큐 2~4) 를 채웁니다. "
    "(4) 해당 report 의 finding 이 없으면 그 report 는 비워 둬도 됩니다."
)


def _finding_lines(findings: Any, *, label: str) -> str:
    """findings → 구조화 텍스트 (LLM 입력). interpretation/enum 필드만 — 수치 제외.

    kismam.top_issues / generic top-joint deviation 미주입 (tip.detail2 중복 회피).
    measured_value / deduction_score 등 수치 필드는 프롬프트에 넣지 않는다 (number-free).
    """
    lines: list[str] = [f"[{label}]"]
    for i, f in enumerate(findings or []):
        parts: list[str] = []
        for attr in ("interpretation", "body_type_interpretation", "recommendation"):
            val = getattr(f, attr, None)
            if isinstance(val, str) and val:
                parts.append(val)
        hint = getattr(f, "joint_hint", None) or getattr(f, "joint_key", None)
        if isinstance(hint, str) and hint:
            parts.append(f"(부위: {hint})")
        if parts:
            lines.append(f"- {' '.join(parts)}")
    if len(lines) == 1:
        lines.append("- (해당 없음)")
    return "\n".join(lines)


class GeminiCoachHookWriter:
    """text-only Gemini hook writer (single call, bundle|None only).

    seam:
      api_key_loader: 키 로더 (기본 client._default_api_key_loader). 실패 시 None 반환.
      model_override: resolve_model('B', override) — raw model string 금지.
      client: 테스트용 주입 seam — `.generate(model=, contents=, config=)` 를 노출하는
        오브젝트. None 이면 google-genai Client 를 lazy 생성해 text-only 호출. 주입
        client 가 던지는 예외는 .status / .status_code (4xx/5xx) 로 분기.
    """

    def __init__(
        self,
        *,
        api_key_loader: Callable[[], str] | None = None,
        model_override: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._api_key_loader = api_key_loader or _default_api_key_loader
        self._model_override = model_override
        self._injected_seam = client

    def build_coach_hooks(
        self,
        *,
        force_findings: Any,
        body_findings: Any,
    ) -> CoachHookBundle | None:
        """force/body findings → CoachHookBundle 또는 None (single call).

        canned 미생성 (iter-3 HIGH-1). None trigger: api_key_loader 실패 / 4xx /
        guard reject / retry 소진 / parse 실패 2회.
        """
        model = resolve_model("B", self._model_override)

        # ── api_key 로드 (graceful — D-08 seam). 실패/빈 키 → None.
        try:
            api_key = self._api_key_loader()
        except Exception as exc:  # noqa: BLE001 - api 키 실패는 graceful None
            log.warning("CoachHook api_key load 실패 — graceful None (model=%s): %s", model, exc)
            return None
        if not api_key:
            log.warning("CoachHook api_key 비어있음 — graceful None (model=%s).", model)
            return None

        prompt = "\n\n".join(
            [
                _HOOK_SYSTEM_PROMPT,
                _finding_lines(force_findings, label="forcePatternInference"),
                _finding_lines(body_findings, label="bodyComparisonReport"),
            ]
        )

        # ── config (iter-2 HIGH-1): CoachHookBundle nested → $defs strip 필수.
        config = self._build_config()

        call_seam = self._injected_seam
        if call_seam is None:
            call_seam = self._make_genai_adapter(api_key)

        return self._generate_with_retry(
            call_seam, model=model, prompt=prompt, config=config
        )

    # ─────────────────── 내부 helpers ───────────────────

    def _build_config(self) -> Any:
        """generate_content config — schema-strip 재사용 (iter-2 HIGH-1).

        raw CoachHookBundle 직접 주입 금지 ($defs/additionalProperties → live 400).
        client.py 의 _strip_unsupported_schema_keys 로 inline.
        """
        from google.genai import types as genai_types

        return genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_strip_unsupported_schema_keys(
                CoachHookBundle.model_json_schema()
            ),
            http_options=genai_types.HttpOptions(timeout=_HTTP_TIMEOUT_MS),
        )

    def _make_genai_adapter(self, api_key: str) -> Any:
        """google-genai Client lazy 생성 — text-only generate_content 어댑터.

        주입 client seam (테스트) 와 동일한 `.generate(model=, contents=, config=)`
        인터페이스를 노출하는 thin adapter 를 반환한다. 영상 입력 경로 미접촉.
        """
        from google import genai

        real = genai.Client(api_key=api_key)

        class _TextOnlyAdapter:
            def generate(self, *, model: str, contents: Any, config: Any) -> Any:
                # text-only — contents 는 [prompt] (영상 입력 없음).
                return real.models.generate_content(
                    model=model, contents=contents, config=config
                )

        return _TextOnlyAdapter()

    def _generate_with_retry(
        self, client: Any, *, model: str, prompt: str, config: Any
    ) -> CoachHookBundle | None:
        """generate + 객관성/number-free 가드 + parse + 1회 retry (Vision retry path mirror).

        retry trigger: ValidationError / JSONDecodeError 또는 5xx → attempt 1 만 retry.
        즉시 None: 4xx / guard reject (ValueError) / retry 소진.
        """
        for attempt in (1, 2):
            try:
                response = client.generate(
                    model=model, contents=[prompt], config=config
                )
            except Exception as exc:  # noqa: BLE001 - status 분기 후 graceful None
                code = self._status_of(exc)
                if isinstance(code, int) and 400 <= code < 500:
                    log.warning("CoachHook APIError 4xx code=%s — None (model=%s).", code, model)
                    return None
                if attempt == 1:
                    log.warning("CoachHook APIError code=%s — retry 1회 (model=%s).", code, model)
                    time.sleep(0.0)
                    continue
                log.warning("CoachHook APIError code=%s — retry 소진 None (model=%s).", code, model)
                return None

            # 주입 client (테스트) 가 이미 bundle duck object 를 반환한 경우 — 그대로 사용.
            if isinstance(response, CoachHookBundle):
                bundle: Any = response
            elif self._looks_like_bundle(response):
                bundle = response
            else:
                # 실 Gemini 응답 — raw text 가드 + parse.
                raw_text = getattr(response, "text", "") or ""
                # 객관성 + number-free 가드 (hook-scoped). reject → None (D-05).
                try:
                    _enforce_no_reject_patterns(
                        raw_text, context="coach_hook", forbid_measurement_units=True
                    )
                except ValueError as guard_exc:
                    log.warning(
                        "CoachHook 객관성/number-free 가드 reject — None (model=%s): %s",
                        model,
                        guard_exc,
                    )
                    return None

                parsed = getattr(response, "parsed", None)
                if parsed is not None and isinstance(parsed, CoachHookBundle):
                    return parsed
                try:
                    if not raw_text:
                        raise ValueError("CoachHook 응답 text 가 비어있음")
                    payload = json.loads(raw_text)
                    return CoachHookBundle.model_validate(payload)
                except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                    if attempt == 1:
                        log.warning("CoachHook parse 실패 — retry 1회 (model=%s): %s", model, exc)
                        continue
                    log.warning("CoachHook parse 2회 실패 — None (model=%s): %s", model, exc)
                    return None
                bundle = None  # pragma: no cover - 위 분기에서 모두 return

            return bundle

        return None

    @staticmethod
    def _status_of(exc: Exception) -> int | None:
        """예외에서 HTTP status code 추출 (status / status_code / code)."""
        for attr in ("status", "status_code", "code"):
            val = getattr(exc, attr, None)
            if isinstance(val, int):
                return val
        return None

    @staticmethod
    def _looks_like_bundle(obj: Any) -> bool:
        """duck object 가 CoachHookBundle shape 인지 (테스트 SimpleNamespace seam).

        실 Gemini 응답(GenerateContentResponse) 은 `text`/`parsed` 를 갖지만
        force_pattern_inference / body_comparison_report attribute 는 없다 — 그 둘이
        있으면 주입된 bundle duck object 로 간주.
        """
        return hasattr(obj, "force_pattern_inference") and hasattr(
            obj, "body_comparison_report"
        )


__all__ = ["GeminiCoachHookWriter"]
