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


# ── 공용 이미지 디코드 방어 (H4-06) ───────────────────────────────────────


def safe_decode_image(
    data: bytes,
    *,
    allowed_formats: tuple[str, ...],
    max_decoded_bytes: int,
    max_pixels: int,
    max_edge: int,
):
    """bytes → PIL.Image. decode 전/직후 3중 cap 으로 bomb 을 typed 로 거부한다.

    judge(prepare_judge_payload)와 pose gate(31-06)가 공용으로 쓴다 — 외부에서
    들어온 이미지 바이트가 Gemini/Pod 로 나가기 **전에** 여기서 걸러진다.

    3중 cap 이 다 필요한 이유:
      1. len(data) — 압축 상태 상한. 네트워크에서 받은 직후 즉시 판정.
      2. Image.MAX_IMAGE_PIXELS — PIL 이 decode 도중 스스로 터뜨리게 함.
         압축 20MB 이하인데 20000x20000 인 bomb 은 (1) 을 통과하므로 필요.
      3. open 직후 format/width/height 재검사 — PIL 은 lazy 라 open 시점에는
         헤더만 읽는다. 실제 픽셀 접근 전에 여기서 끊어야 메모리가 안 터진다.

    반환된 Image 는 아직 lazy 다. 호출측이 load/convert 하기 전에 이 함수를
    통과했다는 사실이 보장된다.
    """
    from PIL import Image, UnidentifiedImageError

    if len(data) > max_decoded_bytes:
        raise ImageDecodeError("too_large")

    previous_cap = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        img = Image.open(_bytes_io(data))
    except Image.DecompressionBombError:
        raise ImageDecodeError("bomb") from None
    except (UnidentifiedImageError, OSError, ValueError):
        raise ImageDecodeError("unreadable") from None
    finally:
        Image.MAX_IMAGE_PIXELS = previous_cap

    if (img.format or "").upper() not in allowed_formats:
        raise ImageDecodeError("bad_format")
    width, height = img.size
    if max(width, height) > max_edge or width * height > max_pixels:
        raise ImageDecodeError("bad_dimension")
    return img


def _bytes_io(data: bytes):
    from io import BytesIO

    return BytesIO(data)


# ── 벤더 산출물 다운로드 경계 (H-05 + H2-04/H2-05 + H3-05) ────────────────

_ALLOWED_HOST_SUFFIXES = ("aliyuncs.com",)
_DOWNLOAD_CHUNK = 64 * 1024


@dataclass(frozen=True)
class DownloadedAsset:
    """다운로드 결과 — 바이트가 아니라 **파일 경로**다 (H2-05).

    벤더 산출물은 수백 MB 일 수 있어 메모리로 받으면 Lambda 가 OOM 난다.
    /tmp 로 스트리밍하고 sha256 을 누적 계산해 무결성 참조를 남긴다.
    """

    path: str
    sha256: str
    size_bytes: int
    content_type: str


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """모든 리다이렉트를 즉시 거부 (H2-04 + H3-05).

    벤더 응답 URL 은 신뢰 경계 밖이다. 리다이렉트를 따라가면 호스트 allowlist와
    사설 IP 검사를 **첫 홉에만** 적용한 꼴이 돼 SSRF 가 열린다 (T-31-16).
    redirect_request 만 막으면 부족해서 http_error_30x 도 전부 덮는다.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VendorDownloadError("redirect")

    def http_error_301(self, req, fp, code, msg, headers):
        raise VendorDownloadError("redirect")

    http_error_302 = http_error_301
    http_error_303 = http_error_301
    http_error_307 = http_error_301
    http_error_308 = http_error_301


def _host_allowed(host: str, allowed_suffixes: tuple[str, ...]) -> bool:
    """정확 매칭 — 'evilaliyuncs.com' 이 'aliyuncs.com' 으로 통과하지 않게 한다."""
    host = host.lower()
    return any(host == s or host.endswith("." + s) for s in allowed_suffixes)


def _resolve_public(host: str) -> None:
    """호스트의 **모든** A/AAAA 가 공인 IP 인지 확인 (T-31-16 SSRF).

    하나라도 사설/루프백/링크로컬/예약이면 거부한다 — DNS rebinding 은 여러
    레코드 중 하나만 내부를 가리켜도 성립하기 때문이다.
    """
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise VendorDownloadError("bad_host") from None
    if not infos:
        raise VendorDownloadError("bad_host")
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        ):
            raise VendorDownloadError("private_ip")


def download_vendor_asset(
    url: str,
    dest_path: str,
    *,
    max_bytes: int,
    allowed_content_types: tuple[str, ...],
    timeout_s: int = _HTTP_TIMEOUT_S,
    _test_allowed_hosts: tuple[str, ...] | None = None,
    _test_allow_private: bool = False,
    _test_ssl_context=None,
) -> DownloadedAsset:
    """벤더 산출물을 dest_path 로 스트리밍 다운로드.

    경계 7종: https 고정 / 호스트 allowlist / 사설 IP 거부 / 리다이렉트 거부 /
    Content-Type allowlist / 타임아웃 / 누적 바이트 cap.

    평문 HTTP 폴백 스위치는 **인자로 존재하지 않는다** (H3-05). 그런 스위치가
    시그니처에 있으면 언젠가 켜진다 — 애초에 만들지 않는다.

    `_test_*` 인자는 테스트 전용이다 (self-signed TLS 로컬 서버로 실제 30x 를
    핸들러에 도달시키기 위함). production 호출부에는 나타나지 않으며 31-09
    acceptance 가 grep 으로 강제한다.

    URL 의 query(서명)는 어떤 경로로도 로깅하지 않는다 (T-31-01).
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https":
        raise VendorDownloadError("bad_scheme")
    host = parsed.hostname or ""
    allowed_hosts = _test_allowed_hosts or _ALLOWED_HOST_SUFFIXES
    if not _host_allowed(host, allowed_hosts):
        raise VendorDownloadError("bad_host")
    if not _test_allow_private:
        _resolve_public(host)

    handlers: list = [_NoRedirectHandler(), urllib.request.ProxyHandler({})]
    if _test_ssl_context is not None:
        handlers.append(urllib.request.HTTPSHandler(context=_test_ssl_context))
    opener = urllib.request.build_opener(*handlers)

    digest = hashlib.sha256()
    total = 0
    try:
        with opener.open(url, timeout=timeout_s) as resp:
            content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if not any(content_type.startswith(t) for t in allowed_content_types):
                raise VendorDownloadError("bad_content_type")
            with open(dest_path, "wb") as fh:
                while True:
                    chunk = resp.read(_DOWNLOAD_CHUNK)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise VendorDownloadError("too_large")
                    digest.update(chunk)
                    fh.write(chunk)
    except VendorDownloadError:
        _unlink_quiet(dest_path)
        raise
    except socket.timeout:
        _unlink_quiet(dest_path)
        raise VendorDownloadError("timeout") from None
    except urllib.error.URLError as e:
        _unlink_quiet(dest_path)
        if isinstance(e.reason, VendorDownloadError):
            raise e.reason from None
        if isinstance(e.reason, socket.timeout):
            raise VendorDownloadError("timeout") from None
        log.warning("vendor download failed host=%s", host)
        raise VendorDownloadError("bad_host") from None

    return DownloadedAsset(
        path=dest_path, sha256=digest.hexdigest(), size_bytes=total, content_type=content_type
    )


def _unlink_quiet(path: str) -> None:
    """경계 위반 시 부분 파일을 남기지 않는다 — /tmp 는 invocation 간 공유된다."""
    try:
        os.unlink(path)
    except OSError:
        pass


# ── before/after 보존 judge (H-03 + H3-02/H3-03 + M4-02) ──────────────────

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"
)

# 31-13 calibration meta 재현성 — 프롬프트가 바뀌면 여기도 올려야 임계값이
# 어느 프롬프트에서 잡힌 값인지 추적된다.
PROMPT_VERSION = "judge-v1"

# Gemini 공식 inline request 상한은 20MB
# (https://ai.google.dev/gemini-api/docs/vision — inline data 20MB).
# base64 팽창(4/3)과 JSON 오버헤드를 감안해 16MB 에서 미리 끊는다.
JUDGE_BODY_MAX_BYTES = 16 * 1024 * 1024

_JUDGE_ALLOWED_FORMATS = ("PNG", "JPEG")
_JUDGE_MAX_DECODED_BYTES = 20 * 1024 * 1024
_JUDGE_MAX_PIXELS = 16 * 1024 * 1024
_JUDGE_MAX_EDGE = 8192
_JUDGE_NORMALIZED_EDGE = 2048
_JUDGE_JPEG_QUALITY = 85

# 판정 축 7종. 벤더가 "지정 관절만 교정" 지시를 자주 어기고 자세를 전면
# 재생성한다는 31-01 실측(8건 중 보존 성공 2건)이 이 축 구성의 근거다 —
# correction_visible 하나만 보면 전면 재생성이 통과해 버린다.
JUDGE_AXES = (
    "identity_ok",
    "clothing_ok",
    "background_ok",
    "pole_ok",
    "single_person_ok",
    "no_extra_limbs",
    "correction_visible",
)

# confidence 와 무관하게 실패로 처리하는 축 — "사람이 아예 다르거나, 여럿이거나,
# 팔다리가 더 생긴" 산출물은 확신도가 낮다는 이유로 통과시킬 수 없다.
_HARD_REJECTION_AXES = ("single_person_ok", "no_extra_limbs")

_JUDGE_PROMPT = (
    "너는 폴스포츠 자세 교정 이미지의 검수자다. BEFORE 는 사용자의 원본 프레임이고 "
    "AFTER 는 특정 관절 하나를 교정하도록 생성된 이미지다. 두 이미지를 비교해 "
    "AFTER 가 BEFORE 의 인물 정체성/복장/배경/폴 위치를 보존했는지, 인물이 정확히 "
    "한 명인지, 팔다리가 늘거나 왜곡되지 않았는지, 그리고 의도한 교정이 실제로 "
    "보이는지를 판정하라. 자세가 전면적으로 다시 그려졌다면 correction_visible 이 "
    "참이더라도 보존 축들을 거짓으로 판정하라. 확신이 없으면 confidence 를 낮게 잡아라."
)

_JUDGE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        **{axis: {"type": "boolean"} for axis in JUDGE_AXES},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": [*JUDGE_AXES, "confidence", "reason"],
}


@dataclass(frozen=True)
class JudgeVerdict:
    """judge 판정 — 7축 bool + confidence + 근거 문장."""

    identity_ok: bool
    clothing_ok: bool
    background_ok: bool
    pole_ok: bool
    single_person_ok: bool
    no_extra_limbs: bool
    correction_visible: bool
    confidence: float
    reason: str


def _normalize_for_judge(data: bytes) -> bytes:
    """safe_decode → EXIF 제거 + 최대 변 축소 + JPEG 재인코딩.

    판정용 **파생본**이다 — canonical 산출물은 건드리지 않는다. EXIF 를 떨어뜨리는
    이유는 원본 촬영 메타(위치/기기)가 외부 판정 API 로 새 나가는 것을 막기 위함이다
    (T-31-01). 재인코딩은 픽셀만 다시 쓰므로 메타가 자연히 사라진다.
    """
    from PIL import Image

    img = safe_decode_image(
        data,
        allowed_formats=_JUDGE_ALLOWED_FORMATS,
        max_decoded_bytes=_JUDGE_MAX_DECODED_BYTES,
        max_pixels=_JUDGE_MAX_PIXELS,
        max_edge=_JUDGE_MAX_EDGE,
    )
    img = img.convert("RGB")
    longest = max(img.size)
    if longest > _JUDGE_NORMALIZED_EDGE:
        scale = _JUDGE_NORMALIZED_EDGE / longest
        new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
        img = img.resize(new_size, Image.LANCZOS)
    buf = _bytes_io(b"")
    img.save(buf, format="JPEG", quality=_JUDGE_JPEG_QUALITY)
    return buf.getvalue()


def prepare_judge_payload(before_png: bytes, after_png: bytes, prompt: str) -> bytes:
    """두 이미지를 정규화해 Gemini generateContent body 로 직렬화한다.

    상한 초과(또는 decode 경계 위반)는 typed JudgeInputTooLargeError — None 으로
    뭉개지 않는다. 호출측이 'judge_input_too_large' 로 종결해야 하는데, None 은
    "판정 실패(재시도 가능)" 와 구분되지 않기 때문이다.

    judge_corrected_pose 내부에서만 호출된다 (M4-02 — 워커가 선호출하면 같은
    이미지를 두 번 decode 하게 되고, 그 자체가 bomb 증폭 경로다).
    """
    try:
        before_jpeg = _normalize_for_judge(before_png)
        after_jpeg = _normalize_for_judge(after_png)
    except ImageDecodeError as e:
        raise JudgeInputTooLargeError(f"decode rejected: {e.reason}") from None

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "BEFORE (원본)"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64.b64encode(before_jpeg).decode(),
                        }
                    },
                    {"text": "AFTER (생성)"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64.b64encode(after_jpeg).decode(),
                        }
                    },
                    {"text": prompt},
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _JUDGE_RESPONSE_SCHEMA,
        },
    }
    serialized = json.dumps(body).encode()
    if len(serialized) > JUDGE_BODY_MAX_BYTES:
        raise JudgeInputTooLargeError(f"body {len(serialized)} > {JUDGE_BODY_MAX_BYTES}")
    return serialized


def _parse_verdict(payload: dict) -> JudgeVerdict | None:
    """Gemini 응답 → JudgeVerdict. 스키마 위반은 None (검증 SDK 미반입 — 수동 검사)."""
    try:
        candidates = payload["candidates"]
        text = candidates[0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    values = {}
    for axis in JUDGE_AXES:
        v = parsed.get(axis)
        if not isinstance(v, bool):
            return None
        values[axis] = v
    confidence = parsed.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return None
    reason = parsed.get("reason")
    if not isinstance(reason, str):
        return None
    return JudgeVerdict(**values, confidence=float(confidence), reason=reason)


def judge_corrected_pose(
    before_png: bytes,
    after_png: bytes,
    context: dict,
    *,
    api_key: str | None = None,
) -> JudgeVerdict | None:
    """before/after 를 함께 판정 → JudgeVerdict, 판정 불가 시 None (fail-closed).

    None 은 "통과" 가 아니다 — 호출측(31-09)이 judge_failed 로 종결한다. 판정
    불가한 산출물을 사용자에게 보여주지 않는 것이 D-08 의 조용한 폴백이다.

    JudgeInputTooLargeError 만은 전파한다 — 재시도해도 같은 결과인 결정론적
    입력 문제라 'judge_input_too_large' 로 구분 종결해야 한다.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        log.warning("judge skipped — GEMINI_API_KEY 미설정")
        return None

    prompt = _JUDGE_PROMPT
    hint = context.get("correction_hint") if isinstance(context, dict) else None
    if isinstance(hint, str) and hint:
        prompt = f"{prompt}\n\n교정 지시: {hint}"
    body = prepare_judge_payload(before_png, after_png, prompt)

    for attempt in range(2):
        req = urllib.request.Request(GEMINI_ENDPOINT, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-goog-api-key", key)
        try:
            with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            if e.code >= 500 and attempt == 0:
                continue
            log.warning("judge http error status=%s", e.code)
            return None
        except Exception:  # noqa: BLE001 - 네트워크 실패는 fail-closed (키 미로깅)
            if attempt == 0:
                continue
            log.warning("judge request failed")
            return None
        try:
            payload = json.loads(raw)
        except (ValueError, TypeError):
            return None
        return _parse_verdict(payload) if isinstance(payload, dict) else None
    return None


def _preserved(verdict: JudgeVerdict) -> bool:
    return all(getattr(verdict, axis) for axis in JUDGE_AXES)


def _hard_rejected(verdict: JudgeVerdict) -> bool:
    return any(not getattr(verdict, axis) for axis in _HARD_REJECTION_AXES)


def judge_display_pass(verdict: JudgeVerdict, *, min_confidence: float) -> bool:
    """앱 노출 허용 여부. 임계값은 인자 주입 (H3-02 — 모듈에 리터럴 금지).

    31-09 가 DISPLAY_JUDGE_CONFIDENCE env 로 주입하고, 값 자체는 31-13
    calibration harness 가 grid 로 고른다.
    """
    if _hard_rejected(verdict):
        return False
    return _preserved(verdict) and verdict.confidence >= min_confidence


def judge_training_pass(verdict: JudgeVerdict, *, min_confidence: float) -> bool:
    """학습 페어 적재 허용 여부 — display 와 같은 축, 더 높은 임계값을 주입받는다.

    별도 함수인 이유(B4-05): 노출 기준과 학습 적재 기준은 실패 비용이 다르다.
    잘못 노출된 이미지는 사용자가 한 번 보고 끝이지만, 잘못 적재된 페어는 이후
    모델을 영구히 오염시킨다. 31-09 가 TRAINING_JUDGE_CONFIDENCE 로 별개 주입.
    """
    if _hard_rejected(verdict):
        return False
    return _preserved(verdict) and verdict.confidence >= min_confidence
