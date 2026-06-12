"""Phase 17 Wave 1 — 영역 C Finding 장면 인식 (Gemini Flash).

박제 정신:
  · 17-RESEARCH §9 Wave 1 + AI-SPEC §5 E5 + §6 G4 정합. 단일 영상 → 4 boolean flag
    (grip_visible / backbend_present / occlusion_severe / camera_angle_problematic)
    + 한국어 짧은 노트 (notes_ko ≤ 200자) + meta (model / tokens_used / latency_ms).
  · G4 정은지 영상 가드: `is_reference=True + occlusion_severe=True` 동시 시 4 flag
    전체 폐기 (False) + `guardrail_triggered="G4_reference_occlusion_fp"` 박힘.
    PROJECT.md "정은지 영상 41점 같은 위양성" 직격 — finding flag 가 잘못 폐기 분기
    트리거하기 전 차단.
  · Graceful 폴백: `GeminiVisionCall.call()` 가 None 반환 시 (API 키 미설정 / 4xx /
    schema 검증 실패 etc.) 빈 flag dict (`grip_visible=False ... notes_ko="" +
    error="api_or_schema_fail"`) 반환 — 분석 흐름 차단 0.
  · Model 결정 (3차 R-W2): `resolve_model("C", env_override=...)` 단일 source. raw
    string 박제 0. env 우선순위:
      1. `GEMINI_C_MODEL_OVERRIDE` (emergency manual override — 운영 대응)
      2. `GEMINI_C_MODEL` (alias)
      3. `DEFAULT_C_MODEL` = `gemini-3.5-flash`
    자동 escalation (E5 PASS rate < 95%) 은 runtime config (Firestore
    `visionConfig.regionC.model` 또는 SSM) 책임 — 본 모듈은 env 자동 set X.

후속 plan 정합:
  · 본 모듈은 후속 plan 04 (영역 C eval) 가 prompt 박제 회귀 검증할 수 있도록 prompt
    string 을 `_FINDING_PROMPT` 모듈 상수로 박는다 (test 에서 import 가능).
  · pipeline `_process` 가 본 모듈만 import — 외부 GeminiVisionCall / FindingFlags
    import 박제 0 (단일 진입점).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from .client import GeminiVisionCall
from .config import resolve_model
from .schemas import FindingFlags


log = logging.getLogger(__name__)


# ─────────────────── Finding prompt (한국어) ───────────────────
#
# AI-SPEC §1b "What Domain Experts Evaluate Against" 의 4번째 항목 정의를 그대로 박는다.
# 객관성 헌장 ([[analysis-objectivity-no-human-scores]]) 정합 — 좌표 / 점수 / 사람
# 판단 어휘 영구 금지. GeminiVisionCall 의 enforce_object_guard=True (G1 가드) 가
# raw text 차원에서 이를 한번 더 강제.

_FINDING_PROMPT: str = (
    "당신은 폴스포츠 동작 영상의 객관적 장면 인식기입니다.\n"
    "주어진 영상의 시각 단서를 관찰해 다음 4개 boolean flag 와 짧은 한국어 노트만 반환하세요.\n"
    "절대 금지: 점수/등급/시간 좌표/x=/y=/잘했다/훌륭/완벽 등 사람 판단 어휘.\n"
    "\n"
    "정의:\n"
    "1) grip_visible: 폴을 잡은 손과 그립 종류(오버그립/언더그립/스플릿그립/컵그립)가\n"
    "   영상에서 명확히 식별 가능한 시점이 1회 이상 존재하면 true.\n"
    "2) backbend_present: 등이 30도 이상 후굴된 백벤드 자세가 1초 이상 유지되면 true.\n"
    "   일반 인버트(수직 거꾸로 매달리기)는 backbend 아님 — false.\n"
    "3) occlusion_severe: 신체의 50% 이상이 폴 또는 다른 신체 부위에 의해 가려진\n"
    "   상태가 1초 이상 지속되면 true.\n"
    "4) camera_angle_problematic: 측면 촬영, 완전 뒤집힘 시점이 길어 좌/우 구분이\n"
    "   불가능한 각도면 true.\n"
    "\n"
    "notes_ko: 위 판단 근거를 한국어 1~2문장 (최대 200자) 으로 박으세요.\n"
    "점수/판단 어휘 금지. 시각 단서 묘사만.\n"
)


# ─────────────────── G4 guardrail token ───────────────────

_G4_GUARDRAIL_TAG: str = "G4_reference_occlusion_fp"


# ─────────────────── 영역 C 호출 설정 (AI-SPEC §4) ───────────────────
#
# Flash default — temperature 0.0 (객관 분류), max_output_tokens 512 (4 flag + 짧은
# 노트 충분), thinking_budget 0 (Flash 의 thinking 비활성, latency 우선).

_TEMPERATURE: float = 0.0
_MAX_OUTPUT_TOKENS: int = 512
_THINKING_BUDGET: int = 0


def _resolve_c_model() -> str:
    """env 박제 → resolve_model('C', env_override=...) 단일 source.

    우선순위:
      1. GEMINI_C_MODEL_OVERRIDE (emergency manual override — 운영 대응)
      2. GEMINI_C_MODEL (alias)
      3. DEFAULT_C_MODEL ('gemini-3.5-flash')

    Raises:
      ValueError: override 가 ALLOWED_MODELS 박제 외 (예: 'gemini-2.5-*' / plain Pro).
        graceful X — caller hard fail 인지.
    """
    env_override = (
        os.environ.get("GEMINI_C_MODEL_OVERRIDE")
        or os.environ.get("GEMINI_C_MODEL")
    )
    return resolve_model("C", env_override=env_override)


def _empty_flag_dict(model: str, error: str | None = None) -> dict[str, Any]:
    """4 flag 전부 False + 빈 notes + meta 박제 dict (graceful 폴백 + G4 폐기 공용)."""
    return {
        "grip_visible": False,
        "backbend_present": False,
        "occlusion_severe": False,
        "camera_angle_problematic": False,
        "notes_ko": "",
        "model": model,
        "tokens_used": 0,
        "latency_ms": 0,
        "guardrail_triggered": None,
        "error": error,
    }


def find_scene_flags(
    video_path: str,
    is_reference: bool = False,
) -> dict[str, Any] | None:
    """영상 path → Finding 4 flag + 메타 dict 박제 (graceful 폴백).

    Args:
      video_path: 로컬 영상 path (Pod tmpfs / Lambda /tmp). caller (pipeline) 가
        이미 박은 local_video_path 만 사용 — S3 재다운로드 X.
      is_reference: 정은지 영상 여부 (G4 가드 trigger). caller (pipeline `_process`)
        가 S3 key prefix (`reference/`) 또는 Firestore analysis mode 박제로 산출.

    Returns:
      dict 박제 (None 반환 안 함 — 빈 flag dict 라도 항상 dict). 키:
        grip_visible / backbend_present / occlusion_severe / camera_angle_problematic
        (bool), notes_ko (str ≤ 200자), model / tokens_used / latency_ms (meta),
        guardrail_triggered (None 또는 'G4_reference_occlusion_fp'),
        error (None 또는 'api_or_schema_fail').

    Raises:
      ValueError: resolve_model 가 ALLOWED_MODELS 박제 외 model 거부 (graceful X).
        또는 GeminiVisionCall 의 G1 guardrail (점수/판단 어휘) 매치.
    """
    model = _resolve_c_model()
    call = GeminiVisionCall(
        schema=FindingFlags,
        model=model,
        prompt=_FINDING_PROMPT,
        temperature=_TEMPERATURE,
        max_output_tokens=_MAX_OUTPUT_TOKENS,
        thinking_budget=_THINKING_BUDGET,
        enforce_object_guard=True,
    )

    start = time.monotonic()
    try:
        parsed: FindingFlags | None = call.call(video_path)
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)

    if parsed is None:
        # graceful 폴백 — 빈 flag dict.
        log.info(
            "find_scene_flags graceful skip model=%s latency_ms=%d "
            "(api_key 미설정 / 4xx / schema 검증 실패)",
            model,
            latency_ms,
        )
        out = _empty_flag_dict(model, error="api_or_schema_fail")
        out["latency_ms"] = latency_ms
        return out

    payload: dict[str, Any] = parsed.model_dump()

    # G4 정은지 영상 가드 — is_reference=True + occlusion_severe=True 동시 시 폐기.
    # PROJECT.md "정은지 영상 41점 같은 위양성" 직격. flag 전체 False + guardrail_triggered
    # 박힘 — caller (pipeline) 가 후속 path (D skip / fallback 경로) 박힐 때 가짜 신호
    # 전파 0.
    guardrail_triggered: str | None = None
    if is_reference and bool(payload.get("occlusion_severe")):
        log.warning(
            "G4 guardrail 발동 — is_reference=True + occlusion_severe=True model=%s",
            model,
        )
        payload = {
            "grip_visible": False,
            "backbend_present": False,
            "occlusion_severe": False,
            "camera_angle_problematic": False,
            "notes_ko": payload.get("notes_ko", ""),  # audit 용 보존
        }
        guardrail_triggered = _G4_GUARDRAIL_TAG

    payload["model"] = model
    # tokens_used 는 Gemini SDK response.usage_metadata 박제 — GeminiVisionCall.call()
    # 는 parsed 결과만 반환 (response 객체 미전달). usage_metadata 박제는 후속 plan
    # (Phase 17 eval/F8) 에서 client.call() 시그너처 확장 시 박힘. 본 plan 박제는
    # tokens_used=0 (audit 가능 시점에 채워질 자리). latency_ms 는 본 모듈이 산출.
    payload.setdefault("tokens_used", 0)
    payload["latency_ms"] = latency_ms
    payload["guardrail_triggered"] = guardrail_triggered
    payload["error"] = None
    return payload


__all__ = ["find_scene_flags"]
