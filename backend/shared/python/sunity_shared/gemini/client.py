"""Phase 17 Wave 0 — GeminiVisionCall 베이스 클라이언트.

박제 정신:
  · AI-SPEC §4 Core Pattern + §4b "Structured Outputs with Pydantic" 박제.
  · 후속 plan 02~05 가 본 클래스만 instantiate (`schema=...`, `prompt=...`) — Files API
    upload / ACTIVE 폴링 / response_schema 검증 / retry / 객관성 가드 재구현 0.
  · api_key 미설정 / Files API FAILED / Files API 120s 초과 / APIError 4xx / ValidationError
    2회 / APIError 5xx 2회 = graceful return None. 객관성 reject regex 매치만 ValueError
    raise (graceful X — caller hard fail 인지).
  · 외부 의존: google-genai >=1.0,<2.0 (이미 backend/runpod_inference/requirements.txt 박제).

테스트 가능성:
  · `genai.Client` / `files.upload` / `files.get` / `models.generate_content` 는
    monkeypatch 가능. test_client.py 가 외부 네트워크 호출 0 박제.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import BaseModel, ValidationError

from .guardrails import _enforce_no_reject_patterns

# Phase 17 Plan 06B — Phoenix span event 박제 (TELEMETRY_OK gate).
# extras 미설치 환경에서도 import 자체는 깨지지 않게 박제.
try:
    from sunity_shared.eval import TELEMETRY_OK
except ImportError:  # pragma: no cover - import 시그너처 회귀 안전망
    TELEMETRY_OK = False

if TELEMETRY_OK:
    try:
        from opentelemetry import trace as _otel_trace

        _tracer = _otel_trace.get_tracer(__name__)
    except ImportError:  # pragma: no cover
        _tracer = None
else:
    _tracer = None

log = logging.getLogger(__name__)


T = TypeVar("T", bound=BaseModel)


# Files API 폴링 박제 — ref-invert 7s 영상 기준 통상 5~15s, 상한 박제.
_FILES_PROCESSING_TIMEOUT_S: float = 120.0
_FILES_POLL_INTERVAL_S: float = 2.0

# generate_content http timeout 박제 (ms).
_HTTP_TIMEOUT_MS: int = 60_000


def _default_api_key_loader() -> str:
    """기본 API 키 로더 — sunity_shared.judging.gemini_moment_extractor 박제 재사용.

    lazy import — Plan 02~05 의 host runtime 에서 boto3 / SSM 의존성 박제 정합.
    """
    from sunity_shared.judging.gemini_moment_extractor import _load_api_key

    return _load_api_key()


def _mime_type_for(video_path: str) -> str:
    """확장자 → mime type 박제. 미지 확장자는 'video/mp4' 박제 fallback."""
    ext = Path(video_path).suffix.lower()
    if ext in (".mov", ".qt"):
        return "video/quicktime"
    if ext == ".webm":
        return "video/webm"
    return "video/mp4"


# Gemini proto schema 가 인식 못 하는 JSON Schema key 박힘 — 2026-06-12 deploy fix.
# google-genai SDK 가 이 key 들을 proto field 박혀 변환하면 Gemini API 400
# INVALID_ARGUMENT 박힘 ("Unknown name '...'").
_GEMINI_UNSUPPORTED_SCHEMA_KEYS = frozenset({
    "additionalProperties",  # Pydantic strict mode default → Gemini 400
    "$defs",                  # Pydantic ref 정의 — inline 박은 후 제거
    "discriminator",          # union 박힘 박힘 박힘 박힘 박힘
})


def _strip_unsupported_schema_keys(schema: Any) -> Any:
    """JSON Schema 에서 Gemini 가 인식 못 하는 key 제거 + `$defs` ref 재귀 resolve.

    Pydantic 2 의 nested model 은 `$defs/{Name}` 으로 분리되고 사용처는 `$ref`
    로 가리킨다. Gemini 는 ref 미지원이므로 inline 박제 필요. 단순 1-level
    inline 으로는 `CoachPayload.joints.items.$ref → JointCoaching → detail2.$ref
    → CoachDetail2 → causes.items.$ref → CoachCause` 같은 다단계 ref 가
    빈 `{}` 로 박힘 → Gemini 가 schema 의도 못 읽고 자유 형식 응답 → Pydantic
    validation fail. 재귀 resolver 로 모든 ref 를 inline 박는다.
    """
    if not isinstance(schema, dict):
        return schema
    # 최상위 $defs 보관 (재귀 호출 박혀 resolve)
    defs = schema.get("$defs") or schema.get("definitions") or {}
    return _resolve_and_strip(schema, defs)


def _resolve_and_strip(node: Any, defs: dict) -> Any:
    """node 재귀 순회 — $ref 인라인 + unsupported key 제거."""
    if isinstance(node, dict):
        # $ref 박혀 박힘 → defs 박혀 resolve + 재귀
        if "$ref" in node and isinstance(node["$ref"], str):
            ref_path = node["$ref"]
            if ref_path.startswith("#/$defs/") or ref_path.startswith("#/definitions/"):
                ref_name = ref_path.split("/")[-1]
                if ref_name in defs:
                    return _resolve_and_strip(defs[ref_name], defs)
            # ref 못 풀면 빈 dict (Gemini 가 type 만 보고 추측)
            return {}
        out: dict[str, Any] = {}
        for k, v in node.items():
            if k in _GEMINI_UNSUPPORTED_SCHEMA_KEYS:
                continue
            if k in ("$defs", "definitions"):
                continue
            out[k] = _resolve_and_strip(v, defs)
        return out
    if isinstance(node, list):
        return [_resolve_and_strip(v, defs) for v in node]
    return node


@dataclass
class GeminiVisionCall(Generic[T]):
    """4 영역 공통 Gemini Vision 호출 베이스.

    Fields:
      schema: Pydantic BaseModel subclass — response_schema 주입 + model_validate 폴백.
      model: Gemini 모델 string (예: 'gemini-3.1-pro-preview'). gemini/config.py 의
        DEFAULT_*_MODEL 상수 박제 (raw string 박제 0).
      prompt: 영역별 prompt (자연어). caller 가 박제.
      temperature: 기본 0.1 박제 — 객관 분류 task 우선.
      max_output_tokens: 기본 2048 박제 — 4 영역 모두 schema 박제 응답 사이즈 박제.
      thinking_budget: None = ThinkingConfig 박제 X. int 박제 시 types.ThinkingConfig
        (thinking_budget=...) 박제 (3.x 박제 default-on thinking 비용 박제).
      enforce_object_guard: True = raw text 에 _enforce_no_reject_patterns 박제. False
        = 영역 D (KeypointRefinement) 전용 — guardrail 우회는 caller 가 allow_coords=True
        로 직접 호출.
      allow_coords: enforce_object_guard 박제 시 좌표 패턴 우회 (영역 D 박제). 점수/판단
        어휘는 영구 차단.
      api_key_loader: None = 기본 (env GEMINI_API_KEY → SSM fallback). caller 박제 가능.
    """

    schema: type[T]
    model: str
    prompt: str
    temperature: float = 0.1
    max_output_tokens: int = 2048
    thinking_budget: int | None = None
    enforce_object_guard: bool = True
    allow_coords: bool = False
    api_key_loader: Callable[[], str] | None = None

    def call(self, video_path: str) -> T | None:
        """video_path → schema 인스턴스 또는 None (graceful 폴백).

        graceful 폴백 trigger (return None):
          1. api_key_loader 실패 (RuntimeError / Exception).
          2. Files API state == FAILED.
          3. Files API 폴링 > 120s.
          4. APIError 4xx (즉시 — retry X).
          5. APIError 5xx 2회.
          6. ValidationError / JSONDecodeError 2회.

        hard fail trigger (ValueError raise):
          1. enforce_object_guard=True 시 raw text 에 점수/좌표/판단 매치.

        Args:
          video_path: 로컬 영상 path (Lambda /tmp 또는 Pod tmpfs).

        Returns:
          schema 인스턴스 또는 None.

        Raises:
          ValueError: 객관성 reject regex 매치 (graceful X — caller hard fail 인지).
        """
        # ── Step 1: api_key 로드 (graceful — Plan 02~05 의 'API 키 미설정' fallback path).
        loader = self.api_key_loader or _default_api_key_loader
        try:
            api_key = loader()
        except Exception as exc:  # noqa: BLE001 - api 키 실패는 graceful return None
            log.warning(
                "Gemini API key load 실패 — graceful skip (model=%s): %s",
                self.model,
                exc,
            )
            return None
        if not api_key:
            log.warning(
                "Gemini API key 비어있음 — graceful skip (model=%s).", self.model
            )
            return None

        # ── Step 2: Client 생성 + Files API upload.
        client = genai.Client(api_key=api_key)
        mime_type = _mime_type_for(video_path)
        try:
            uploaded = client.files.upload(
                file=video_path,
                config=genai_types.UploadFileConfig(mime_type=mime_type),
            )
        except TypeError:
            # 일부 stub 환경에서 UploadFileConfig 미지원 — kwargs file 단독 호출 박제.
            uploaded = client.files.upload(file=video_path)
        except genai_errors.APIError as exc:
            return self._handle_api_error_first(exc, label="files.upload")

        # ── Step 3~4: ACTIVE 폴링 → generate_content. 완료(성공/실패/예외) 후
        #    Gemini File API 업로드본을 반드시 삭제한다 — 안 지우면 프로젝트 저장소
        #    (file_storage_bytes ~20GB)에 분석 영상이 쌓여, 한도 초과 시 이후
        #    files.upload 가 RESOURCE_EXHAUSTED 로 실패한다(실증 2026-07-06 20GB 적체
        #    → 분석 간헐 실패). 파일은 48h TTL 이지만 실증 부하는 그 전에 한도를 채운다.
        #    gemini_vision_scorer 의 finally DELETE 규율과 동일. 삭제 실패는 best-effort.
        try:
            # ── Step 3: ACTIVE 폴링 (PROCESSING → ACTIVE / FAILED / timeout).
            active_file = self._wait_for_active(client, uploaded)
            if active_file is None:
                return None

            # ── Step 4: generate_content + retry.
            config = self._build_config()
            return self._generate_with_retry(client, active_file, config)
        finally:
            _name = getattr(uploaded, "name", None)
            if _name:
                try:
                    client.files.delete(name=_name)
                except Exception:  # noqa: BLE001 - 정리 실패는 분석을 막지 않는다
                    log.warning("Gemini 업로드 파일 삭제 실패 (graceful): %s", _name)

    # ─────────────────── 내부 helpers ───────────────────

    def _wait_for_active(self, client: Any, uploaded: Any) -> Any | None:
        """Files API state machine 박제 — ACTIVE 면 객체, FAILED/timeout 면 None."""
        start = time.monotonic()
        state_name = _state_name(uploaded)
        while state_name == "PROCESSING":
            if time.monotonic() - start > _FILES_PROCESSING_TIMEOUT_S:
                log.warning(
                    "Gemini Files API processing > %ds — graceful skip (model=%s).",
                    int(_FILES_PROCESSING_TIMEOUT_S),
                    self.model,
                )
                return None
            time.sleep(_FILES_POLL_INTERVAL_S)
            try:
                uploaded = client.files.get(name=uploaded.name)
            except genai_errors.APIError as exc:
                return self._handle_api_error_first(exc, label="files.get")
            state_name = _state_name(uploaded)

        if state_name == "FAILED":
            log.warning(
                "Gemini Files API state=FAILED — graceful skip (model=%s name=%s).",
                self.model,
                getattr(uploaded, "name", "?"),
            )
            return None
        if state_name != "ACTIVE":
            log.warning(
                "Gemini Files API state=%s 미지원 — graceful skip (model=%s).",
                state_name,
                self.model,
            )
            return None
        return uploaded

    def _build_config(self) -> Any:
        """generate_content config 박제 — response_mime_type / response_schema /
        temperature / max_output_tokens / http timeout + 선택 ThinkingConfig.

        2026-06-12 deploy fix: Pydantic 2 의 json_schema 가 nested model 박혀
        `additionalProperties: false` 박힘 → google-genai SDK 가 이걸 proto field
        `additional_properties` 박혀 변환 → Gemini API 400 INVALID_ARGUMENT
        ("Unknown name 'additional_properties'"). Pydantic 모델 직접 박혀
        response_schema 박는 대신 dict 박혀 변환 후 unsupported key 박힘 strip.
        """
        kwargs: dict[str, Any] = dict(
            response_mime_type="application/json",
            response_schema=_strip_unsupported_schema_keys(
                self.schema.model_json_schema()
            ),
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            http_options=genai_types.HttpOptions(timeout=_HTTP_TIMEOUT_MS),
        )
        if self.thinking_budget is not None:
            kwargs["thinking_config"] = genai_types.ThinkingConfig(
                thinking_budget=self.thinking_budget
            )
        return genai_types.GenerateContentConfig(**kwargs)

    def _generate_with_retry(
        self, client: Any, active_file: Any, config: Any
    ) -> T | None:
        """generate_content + parsed/text 폴백 + 1회 retry 박제.

        retry trigger:
          · ValidationError / JSONDecodeError → 즉시 재시도 (attempt 1만).
          · APIError 5xx → 1초 backoff 후 재시도 (attempt 1만).
          · APIError 4xx → 즉시 None (retry X).
        """
        last_text: str = ""
        for attempt in (1, 2):
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=[active_file, self.prompt],
                    config=config,
                )
            except genai_errors.APIError as exc:
                code = getattr(exc, "code", None)
                if isinstance(code, int) and 400 <= code < 500:
                    log.warning(
                        "Gemini APIError 4xx code=%s — graceful skip (model=%s, attempt=%s).",
                        code,
                        self.model,
                        attempt,
                    )
                    return None
                # 5xx — attempt 1 만 retry, 그 외 None.
                if attempt == 1:
                    log.warning(
                        "Gemini APIError code=%s — retry 1회 (model=%s).",
                        code,
                        self.model,
                    )
                    time.sleep(1.0)
                    continue
                log.warning(
                    "Gemini APIError code=%s — retry 2회 모두 실패 (model=%s).",
                    code,
                    self.model,
                )
                return None

            raw_text = getattr(response, "text", "") or ""
            last_text = raw_text

            # 객관성 가드 (G1 hard fail — graceful X).
            # Phase 17 Plan 06B — TELEMETRY_OK gate 박제 + G1/G5 span event 박제.
            # G1 = 점수/판단 어휘 매치 (hard fail), G5 = 좌표 매치 차단 (영역 D 외).
            if self.enforce_object_guard:
                try:
                    _enforce_no_reject_patterns(
                        raw_text,
                        context=self.model,
                        allow_coords=self.allow_coords,
                    )
                except ValueError as guard_exc:
                    if TELEMETRY_OK and _tracer is not None:
                        current_span = _otel_trace.get_current_span()
                        # G1 (점수/판단) vs G5 (좌표) 분기 — guard exc 메시지로 식별.
                        guard_text = str(guard_exc)
                        if "좌표" in guard_text:
                            current_span.add_event("guardrail.G5.coord_blocked", attributes={"gemini.model": self.model, "gemini.allow_coords": self.allow_coords})
                        else:
                            current_span.add_event("guardrail.G1.triggered", attributes={"gemini.model": self.model, "gemini.enforce_object_guard": True})
                    # hard fail — caller (4 영역 wrapper) 가 ValueError 인지.
                    raise

            # response.parsed 우선 — 없으면 text JSON → model_validate 폴백.
            # Phase 17 Plan 06B — parse_success attribute 박제.
            parsed = getattr(response, "parsed", None)
            if parsed is not None and isinstance(parsed, self.schema):
                if TELEMETRY_OK and _tracer is not None:
                    current_span = _otel_trace.get_current_span()
                    current_span.set_attribute("gemini.parse_success", True)
                    current_span.set_attribute("gemini.retry_count", attempt - 1)
                    current_span.set_attribute("gemini.model", self.model)
                return parsed

            try:
                if parsed is None:
                    if not raw_text:
                        raise ValueError("Gemini 응답 text 가 비어있음")
                    payload = json.loads(raw_text)
                    result = self.schema.model_validate(payload)
                else:
                    # parsed 가 schema 인스턴스가 아니면 model_validate 재시도.
                    result = self.schema.model_validate(parsed)
                if TELEMETRY_OK and _tracer is not None:
                    current_span = _otel_trace.get_current_span()
                    current_span.set_attribute("gemini.parse_success", True)
                    current_span.set_attribute("gemini.retry_count", attempt - 1)
                    current_span.set_attribute("gemini.model", self.model)
                return result
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                if attempt == 1:
                    log.warning(
                        "Gemini schema 검증 실패 — retry 1회 (model=%s): %s",
                        self.model,
                        exc,
                    )
                    continue
                log.warning(
                    "Gemini schema 검증 2회 실패 — graceful skip (model=%s): %s",
                    self.model,
                    exc,
                )
                return None

        # for loop 미도달 (이중 안전망).
        return None

    def _handle_api_error_first(
        self, exc: genai_errors.APIError, *, label: str
    ) -> None:
        """upload / files.get 단계의 APIError — graceful return None.

        Files API 단계 4xx/5xx 는 retry path 가 다름 (generate_content 와 분리). 본 단계는
        둘 다 graceful return None — caller 가 후속 plan 박제 path 로 위임.
        """
        code = getattr(exc, "code", None)
        log.warning(
            "Gemini %s APIError code=%s — graceful skip (model=%s).",
            label,
            code,
            self.model,
        )
        return None


def _state_name(uploaded: Any) -> str:
    """Files API state → string (enum vs str 박제 흡수)."""
    state = getattr(uploaded, "state", None)
    if state is None:
        return ""
    name = getattr(state, "name", None)
    if isinstance(name, str):
        return name
    return str(state)


__all__ = ["GeminiVisionCall"]
