"""외부 시각 생성 API 계층 — Wan2.7 어댑터 + 다운로드 경계 + before/after judge.

Phase 31 (D-02 생성 벤더 / D-03 다운로드 경계 / D-04 회전 수단 / D-08 모더레이션
조용한 폴백). 31-09 워커와 31-13 calibration harness 가 **이 모듈만** import 한다 —
외부 생성 API 로 나가는 코드 경로는 여기 1벌뿐이다.

신규 패키지 0 — stdlib urllib 만. google-genai SDK 는 transitive 로 ~100MB 를
끌어와 Lambda 250MB unzipped 한도를 넘긴다 (backend/functions/pipeline/
requirements.txt 2026-06-12 박제). 그래서 judge 도 Gemini REST 를 직접 친다.
PIL 은 이미지 정규화에서만 lazy import — 모듈 로드는 Pillow 없이도 성공한다.

핵심 계약 박제:

  B2-02 (create_task/poll 분리, 이미지도 동일):
    어댑터는 내부에서 폴링하지 않는다. create 는 taskId 만 받고 즉시 반환하고,
    폴링은 워커가 재호출로 한다. 어댑터가 장시간 폴링하면 Lambda 타임아웃 안에서
    taskId 를 journal 하지 못한 채 죽어 벤더 작업이 고아가 된다(과금·회수 불가).

  B4-02 (v1 async-only):
    sync succeeded 즉시반환 = production 미허용 — create action 은 async
    VendorTaskCreated(taskId) 만 정상 경로로 취급 (sync 지원은 future phase:
    same-invocation staging 완료 후 judging outbox — v1 미포함). sync 모델은
    taskId 가 없어 fetch 가 재-poll 로 fresh URL 을 얻을 수 없기 때문이다.
    어댑터는 IMAGE_ENGINE_SYNC / IMAGE_ENGINE_BLOCKED 를 방출하고, 릴리스
    게이트(31-01/31-13)가 sync-only 후보를 blocked 처리한다.

  H3-01 (출력 URL 비영속):
    poll 결과 output URL 은 **반환값으로만 흐른다** — 호출측이 Firestore/메시지/
    로그에 기록하는 것을 금지한다. 벤더 URL 은 단명 서명 URL 이라 기록해두면
    만료된 죽은 링크가 남고, 그 자체가 사용자 생체 프레임에 대한 무인증 접근
    경로가 된다 (T-31-01/T-31-02).

  T-31-15 (키 비노출):
    API 키는 인자/env 로만 받고 헤더에만 싣는다. URL query 금지, 로그·예외
    문자열에 포함 금지.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import logging
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .. import models

log = logging.getLogger(__name__)

BASE = "https://dashscope-intl.aliyuncs.com"
IMAGE_CREATE_PATH = "/api/v1/services/aigc/image-generation/generation"
VIDEO_CREATE_PATH = "/api/v1/services/aigc/video-generation/video-synthesis"
TASK_PATH = "/api/v1/tasks/{task_id}"

IMAGE_MODEL = "wan2.7-image-pro"
VIDEO_MODEL = "wan2.7-videoedit"

# 모더레이션 재시도 상한 (T-31-19 과금 DoS 방어). 차단은 대개 결정론이라
# 무한 재시도는 비용만 태운다. D-08 = 조용한 폴백이므로 1회로 충분.
MODERATION_RETRY_MAX = 1

_HTTP_TIMEOUT_S = 60

# ── 31-01 smoke 실측 전사 (smoke/RESULTS.json) ────────────────────────────
#
# 런타임에 .planning/ 을 읽지 않는다 (Lambda 배포 산물에 없음). 대신 값을 여기
# 전사하고, 테스트가 RESULTS.json 과 대조해 드리프트를 잡는다.
IMAGE_ENGINE_SYNC = False  # RESULTS.json.candidates[wan2.7-image-pro].sync
_RESULTS_BLOCKED = False  # RESULTS.json.blocked


def derive_engine_blocked(sync: bool, results_blocked: bool) -> bool:
    """async-only 릴리스 게이트 판정 (B4-02).

    sync-only 후보는 품질과 무관하게 v1 production 불가 — taskId 가 없어
    워커가 작업을 journal/재-poll 할 수 없기 때문이다. RESULTS.json 이 이미
    blocked 를 찍었다면 그것도 그대로 승계한다.
    """
    return bool(sync) or bool(results_blocked)


IMAGE_ENGINE_BLOCKED = derive_engine_blocked(IMAGE_ENGINE_SYNC, _RESULTS_BLOCKED)

# ── typed 결과 모델 (M-08 — dict|None 금지) ───────────────────────────────

VENDOR_STATE_PENDING = "pending"
VENDOR_STATE_SUCCEEDED = "succeeded"
VENDOR_STATE_FAILED = "failed"
VENDOR_STATE_BLOCKED = "blocked"
VENDOR_STATES = (
    VENDOR_STATE_PENDING,
    VENDOR_STATE_SUCCEEDED,
    VENDOR_STATE_FAILED,
    VENDOR_STATE_BLOCKED,
)

# 벤더가 폴링 응답에 싣는 종료 상태 문자열 (wan_gate_batch.py 실측 형상).
_VENDOR_RUNNING = ("PENDING", "RUNNING")
_VENDOR_SUCCEEDED = "SUCCEEDED"
_VENDOR_TERMINAL_FAIL = ("FAILED", "CANCELED", "UNKNOWN")

# 모더레이션 차단 식별자. code 우선, 없으면 message 문구로 판정.
_MODERATION_CODES = ("DataInspectionFailed", "InputDataInspectionFailed")
_MODERATION_HINTS = ("inappropriate content", "data inspection")


@dataclass(frozen=True)
class VendorTaskCreated:
    """create 성공 — async taskId 확보. 워커가 journal 후 poll 한다."""

    task_id: str
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id 는 필수 — 빈 값이면 고아 작업이 된다")


@dataclass(frozen=True)
class VendorPollResult:
    """폴링/실패 결과. output_url 은 반환값으로만 흐른다 (H3-01 — 영속 금지)."""

    state: str
    output_url: str | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if self.state not in VENDOR_STATES:
            raise ValueError(f"unknown vendor state: {self.state!r}")
        if self.failure_reason is not None and self.failure_reason not in models.VISUAL_FAILURE_REASONS:
            raise ValueError(
                f"failure_reason 은 models.VISUAL_FAILURE_REASONS 값만 허용: {self.failure_reason!r}"
            )
        if self.state == VENDOR_STATE_SUCCEEDED and not self.output_url:
            raise ValueError("succeeded 인데 output_url 부재 — invalid_output 으로 표현할 것")


class VendorDownloadError(Exception):
    """벤더 산출물 다운로드 경계 위반. reason 은 아래 고정 집합."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


DOWNLOAD_ERROR_REASONS = (
    "bad_scheme",
    "bad_host",
    "redirect",
    "private_ip",
    "bad_content_type",
    "too_large",
    "timeout",
)


class ImageDecodeError(Exception):
    """이미지 디코드 경계 위반 (bomb / 위장 포맷 / 과대 크기)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


IMAGE_DECODE_ERROR_REASONS = ("too_large", "bomb", "unreadable", "bad_format", "bad_dimension")


class JudgeInputTooLargeError(Exception):
    """judge 요청 payload 가 상한 초과 — 호출측이 'judge_input_too_large' 로 종결.

    bomb·위장 포맷(ImageDecodeError)도 여기로 승격한다. 어느 쪽이든 "판정 불가한
    입력" 이라는 동일 처분이고, 호출측이 두 예외를 따로 다룰 실익이 없다.
    """


# ── HTTP (stdlib urllib) ─────────────────────────────────────────────────


def _http_json(
    url: str,
    key: str,
    body: dict | None = None,
    *,
    async_header: bool = False,
    timeout_s: int = _HTTP_TIMEOUT_S,
) -> dict:
    """DashScope JSON 호출 (wan_gate_batch.py http_json 형상).

    body 가 있으면 POST + X-DashScope-Async, 없으면 GET.

    비-JSON 응답(게이트웨이 HTML 오류 페이지 등)은 ValueError 로 올린다 — 빈 dict 로
    뭉개면 "상태 미상" 이 pending 으로 오독돼 워커가 죽은 작업을 영원히 폴링한다.
    호출측 어댑터가 잡아서 vendor_error 로 수렴시킨다. 예외 문자열에 키를 넣지
    않는다 (T-31-15).
    """
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    if async_header:
        req.add_header("X-DashScope-Async", "enable")
    with urllib.request.urlopen(req, timeout=timeout_s) as r:
        raw = r.read()
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        raise ValueError("vendor response is not JSON") from None
    if not isinstance(parsed, dict):
        raise ValueError("vendor response is not a JSON object")
    return parsed


def _output(payload: dict) -> dict:
    out = payload.get("output")
    return out if isinstance(out, dict) else {}


def _is_moderation(out: dict) -> bool:
    code = str(out.get("code") or "")
    if code in _MODERATION_CODES:
        return True
    message = str(out.get("message") or "").lower()
    return any(hint in message for hint in _MODERATION_HINTS)


def _extract_url(out: dict, keys: tuple[str, ...]) -> str | None:
    """종료 응답에서 산출물 URL 추출 — 벤더 응답 형상 변주에 방어적.

    직접 키(video_url/image_url/url) 우선, 없으면 results[0] 안을 본다.
    """
    for k in keys:
        v = out.get(k)
        if isinstance(v, str) and v:
            return v
    results = out.get("results")
    if isinstance(results, list) and results:
        first = results[0]
        if isinstance(first, dict):
            for k in keys:
                v = first.get(k)
                if isinstance(v, str) and v:
                    return v
    return None


def _poll_result(payload: dict, url_keys: tuple[str, ...]) -> VendorPollResult:
    """폴링 응답 dict → typed VendorPollResult."""
    out = _output(payload)
    status = str(out.get("task_status") or "")
    if status in _VENDOR_RUNNING or not status:
        return VendorPollResult(state=VENDOR_STATE_PENDING)
    if status == _VENDOR_SUCCEEDED:
        url = _extract_url(out, url_keys)
        if not url:
            return VendorPollResult(state=VENDOR_STATE_FAILED, failure_reason="invalid_output")
        return VendorPollResult(state=VENDOR_STATE_SUCCEEDED, output_url=url)
    if status in _VENDOR_TERMINAL_FAIL:
        if _is_moderation(out):
            return VendorPollResult(state=VENDOR_STATE_BLOCKED, failure_reason="moderation")
        return VendorPollResult(state=VENDOR_STATE_FAILED, failure_reason="vendor_error")
    return VendorPollResult(state=VENDOR_STATE_FAILED, failure_reason="vendor_error")


def _create_failure(payload: dict) -> VendorPollResult:
    """create 응답에 taskId 가 없을 때의 typed 처분."""
    out = _output(payload)
    if _is_moderation(out):
        return VendorPollResult(state=VENDOR_STATE_BLOCKED, failure_reason="moderation")
    return VendorPollResult(state=VENDOR_STATE_FAILED, failure_reason="vendor_error")


class _WanAdapterBase:
    """create_task/poll 2단계 공통부. 내부 폴링 루프 없음 (B2-02)."""

    _URL_KEYS: tuple[str, ...] = ()

    def __init__(self, api_key: str, *, timeout_s: int = _HTTP_TIMEOUT_S) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    def _create(self, url: str, body: dict) -> VendorTaskCreated | VendorPollResult:
        try:
            payload = _http_json(
                url, self._api_key, body, async_header=True, timeout_s=self._timeout_s
            )
        except Exception:  # noqa: BLE001 - 벤더 실패는 typed 로 수렴 (키 미로깅)
            log.exception("vendor create failed url=%s", url)
            return VendorPollResult(state=VENDOR_STATE_FAILED, failure_reason="vendor_error")
        task_id = _output(payload).get("task_id")
        if not isinstance(task_id, str) or not task_id:
            return _create_failure(payload)
        request_id = payload.get("request_id")
        return VendorTaskCreated(
            task_id=task_id,
            request_id=request_id if isinstance(request_id, str) else None,
        )

    def poll(self, task_id: str) -> VendorPollResult:
        url = BASE + TASK_PATH.format(task_id=urllib.parse.quote(task_id, safe=""))
        try:
            payload = _http_json(url, self._api_key, timeout_s=self._timeout_s)
        except Exception:  # noqa: BLE001 - 폴링 실패도 typed 로 (키 미로깅)
            log.exception("vendor poll failed task_id=%s", task_id)
            return VendorPollResult(state=VENDOR_STATE_FAILED, failure_reason="vendor_error")
        return _poll_result(payload, self._URL_KEYS)


class WanImageAdapter(_WanAdapterBase):
    """correctedPose 정지 이미지 생성 — wan2.7-image-pro (31-01 chosen_model).

    request_params 는 smoke/RESULTS.json 실측 그대로다: input.messages 에
    [{"image": <presigned url>}, {"text": <prompt>}], parameters 는
    n=1 / watermark False / prompt_extend False.

    watermark False: 생성물은 앱 화면에 교정 시각물로 그대로 노출되므로 벤더
    워터마크가 얹히면 제품 화면이 오염된다. prompt_extend False: 벤더가 프롬프트를
    임의 확장하면 "지정 관절만 교정" 지시가 희석된다 — 31-01 실측에서 8건 중 6건이
    이미 자세를 전면 재생성했다(pose_tolerance 실패). 확장을 끄는 것이 그 실패
    유형에 대한 최소 방어이고, 나머지는 31-06 pose gate 와 judge 가 잡는다.
    """

    _URL_KEYS = ("image_url", "url")

    def create_task(self, image_url: str, prompt: str) -> VendorTaskCreated | VendorPollResult:
        body = {
            "model": IMAGE_MODEL,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"image": image_url}, {"text": prompt}],
                    }
                ]
            },
            "parameters": {"n": 1, "watermark": False, "prompt_extend": False},
        }
        return self._create(BASE + IMAGE_CREATE_PATH, body)


class WanVideoEditAdapter(_WanAdapterBase):
    """회전 합성 영상 생성 — wan2.7-videoedit (amended D-04: 회전의 유일 수단).

    GEN3C 는 spike 007b 에서 부적격(중앙 41.1° vs Wan2.7 9.9°) 판정돼 탈락했다.
    parameters 는 spike 008 실측 고정: 720P / watermark False / prompt_extend
    False / seed 42 (재현성 — 31-13 calibration 이 같은 seed 로 재현한다).
    """

    _URL_KEYS = ("video_url", "url")

    def create_task(self, video_url: str, prompt: str) -> VendorTaskCreated | VendorPollResult:
        body = {
            "model": VIDEO_MODEL,
            "input": {"prompt": prompt, "media": [{"type": "video", "url": video_url}]},
            "parameters": {
                "resolution": "720P",
                "watermark": False,
                "prompt_extend": False,
                "seed": 42,
            },
        }
        return self._create(BASE + VIDEO_CREATE_PATH, body)
