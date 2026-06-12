"""Phase 17 Plan 06B Task 2 — LLM judge (영역 B 코칭 톤 binary pass).

박제 정신:
  · AI-SPEC §5 E4 + §7 정합 — Gemini Flash text-only 호출로 코칭 톤 binary judge 산출.
  · belle binary 라벨 calibration mode — `belle_label` 박제 시 judge vs belle 일치
    여부를 confidence 박제 (correlation 측정 입력, ≥ 0.7 게이트).
  · text-only — coach JSON 평문 + judge prompt. Files API 우회 (영상 없음).
  · 외부 호출은 `_call_judge_llm` indirection 박제 — 테스트가 monkeypatch.

graceful 폴백:
  · `_call_judge_llm` 반환 None 시 `pass=None` (judge 자체 미작동 — Cerebras 폴백 X,
    eval/audit 만 None 박제).
"""

from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)


# AI-SPEC §5 E4 — Gemini Flash judge model. Memory [[gemini-latest-model-versions]]
# 2.5 영구 금지 정합 — 3.5 Flash 박제.
_JUDGE_MODEL: str = "gemini-3.5-flash"

# judge prompt 박제 (한국어). 3 조건 (강사 보조 톤 / 원인→해결 / 부위별 용어) 동시 충족
# 시 pass=true, 1개라도 미달 시 pass=false binary.
_JUDGE_PROMPT_TEMPLATE: str = (
    "당신은 폴스포츠 강사 보조 코칭 멘트 검수자입니다.\n"
    "다음 코칭 출력 JSON 을 읽고 (1) 강사 보조 톤 (단정/지시형 아님), "
    "(2) 원인 → 해결 순서, (3) 부위별 용어 사용 — 3 조건 모두 충족하면 "
    "pass=true, 1개라도 미달이면 pass=false binary 판정 후 한국어 reasoning "
    "1~2 문장.\n"
    "절대 금지: 점수/등급 어휘.\n"
    "\n"
    "코칭 출력 JSON:\n"
    "{coach_json}\n"
    "\n"
    "응답 schema (JSON only):\n"
    '{{"pass": true|false, "reasoning_ko": "1~2 문장"}}'
)


def _call_judge_llm(prompt: str, model: str) -> dict[str, Any] | None:
    """judge LLM 호출 indirection — 테스트가 monkeypatch.

    실 호출은 `from google import genai` text-only API (Files API 우회).
    graceful 폴백 — API 키 미설정 / 4xx / parse 실패 시 None.

    Args:
      prompt: judge prompt 텍스트 (한국어).
      model: Gemini Flash 모델 string.

    Returns:
      `{"pass": bool, "reasoning_ko": str}` 또는 None (graceful).
    """
    try:
        from google import genai
        from google.genai import errors as genai_errors
        from google.genai import types as genai_types

        from sunity_shared.judging.gemini_moment_extractor import _load_api_key
    except ImportError as exc:  # pragma: no cover
        log.warning("judge LLM dependency 미설치 — graceful skip: %s", exc)
        return None

    try:
        api_key = _load_api_key()
    except Exception as exc:  # noqa: BLE001
        log.warning("judge API key load 실패 — graceful skip: %s", exc)
        return None
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=[prompt],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
                max_output_tokens=256,
                # Flash 3.5 — thinking 비활성 (latency 우선).
                thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except genai_errors.APIError as exc:
        log.warning("judge APIError code=%s — graceful skip.", getattr(exc, "code", None))
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("judge generate_content raise — graceful skip: %s", exc)
        return None

    raw_text = getattr(response, "text", "") or ""
    if not raw_text:
        return None
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        log.warning("judge response JSON parse 실패 — graceful skip.")
        return None
    if not isinstance(payload, dict) or "pass" not in payload:
        return None
    return payload


def judge_coach_tone(
    coach_payload: dict[str, Any],
    belle_label: bool | None = None,
) -> dict[str, Any]:
    """영역 B 코칭 톤 binary judge + (옵션) belle 라벨 calibration.

    Args:
      coach_payload: GeminiCoachWriter 의 반환 dict (joint_key → detail / detail2).
      belle_label: belle 가 박은 binary 라벨 (True=좋은 코칭 / False=폴백). None
        이면 calibration mode 미진입 — confidence None 박제.

    Returns:
      `{"pass": bool | None, "confidence": float | None, "reasoning_ko": str,
        "judge_model": "gemini-3.5-flash"}`.

      · pass: judge 가 산출한 binary (LLM None 시 None).
      · confidence: belle_label 박혀있고 judge pass 박혀있으면 1.0 (일치) or 0.0
        (불일치). belle_label None 또는 judge None 시 None.
      · reasoning_ko: judge 의 한국어 1~2 문장.
      · judge_model: 박제 model string (audit).
    """
    coach_json = json.dumps(coach_payload, ensure_ascii=False)
    prompt = _JUDGE_PROMPT_TEMPLATE.format(coach_json=coach_json)

    raw = _call_judge_llm(prompt, _JUDGE_MODEL)

    if raw is None:
        return {
            "pass": None,
            "confidence": None,
            "reasoning_ko": "",
            "judge_model": _JUDGE_MODEL,
        }

    judge_pass = bool(raw.get("pass"))
    reasoning = str(raw.get("reasoning_ko", "")).strip()

    confidence: float | None = None
    if belle_label is not None:
        confidence = 1.0 if judge_pass == bool(belle_label) else 0.0

    return {
        "pass": judge_pass,
        "confidence": confidence,
        "reasoning_ko": reasoning,
        "judge_model": _JUDGE_MODEL,
    }


__all__ = ["judge_coach_tone"]
