"""Phase 27 SPD-02 / D-04 — GeminiFileSession: 분석당 File API 업로드 1회 + 종료 일괄 delete.

박제 정신:
  · D-04 허용 레버 "파일 핸들 재사용": 학생/기준 영상이 scene_finder + moment extractor +
    veto + coach B 로 최대 4~5회 중복 업로드되던 것을 분석당 1회로 축약하고, 핸들(`files/...`
    name = 서버측 리소스, 48h TTL)을 전 모듈이 공유한다. 소비처 배선은 27-04.
  · 20GB 적체 실증(2026-07-06): 업로드본을 안 지우면 프로젝트 file_storage_bytes(~20GB)에
    분석 영상이 쌓여, 한도 초과 시 이후 files.upload 가 RESOURCE_EXHAUSTED 로 실패한다(간헐
    분석 실패). 파일은 48h TTL 이지만 실증 부하는 그 전에 한도를 채운다. → close() 일괄 delete
    규율 불변. delete 가 "호출마다"에서 "분석마다"로 바뀔 뿐 누수 0 은 그대로다 (27-RESEARCH
    Pattern 1, T-27-06).
  · 락 스코프(외부 리뷰 MEDIUM-2 — 전체-메서드 락 금지): 락=맵/마커만 보호, 업로드+ACTIVE
    폴링(수십 초 I/O)은 락 밖 — 서로 다른 경로(학생 ∥ 기준)의 동시 업로드가 직렬화되지 않아야
    27-05 prefetch 수확이 보존된다. 정확성(경로당 1회)은 per-path in-flight Event 로 보장.

외부 의존: google-genai (기존 핀 재사용, 신규 패키지 0). lazy import (Lambda 250MB 규율).
테스트: tests/gemini/test_file_session.py — client_factory 주입으로 네트워크 0 검증.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Callable

log = logging.getLogger(__name__)


def _default_client_factory() -> Any:
    """기본 client factory — 첫 업로드 시에만 genai.Client 를 생성 (lazy).

    api_key 로더는 client.py 정본(_default_api_key_loader = env → SSM fallback) 재사용.
    """
    from google import genai  # lazy — top-level import 금지 (D-16, Lambda 250MB)

    from .client import _default_api_key_loader

    api_key = _default_api_key_loader()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 부재 — file session upload 불가")
    return genai.Client(api_key=api_key)


def _ascii_safe_path(path: str) -> tuple[str, str | None]:
    """genai SDK 가 파일명을 HTTP 헤더(ascii)에 넣어 한글 파일명은 UnicodeEncodeError.
    비-ASCII 경로면 ASCII 임시 파일로 복사 후 반환 (gemini_vision_scorer._ascii_safe_path 포팅).

    반환: (업로드에 쓸 경로, 정리할 임시 경로 or None).
    """
    name = os.path.basename(path)
    try:
        name.encode("ascii")
        return path, None
    except UnicodeEncodeError:
        import shutil
        import tempfile

        suffix = os.path.splitext(path)[1]
        tmp = tempfile.NamedTemporaryFile(prefix="fsession_", suffix=suffix, delete=False)
        tmp.close()
        shutil.copyfile(path, tmp.name)
        return tmp.name, tmp.name


class GeminiFileSession:
    """분석 1회 스코프의 Gemini File API 핸들 공유 세션.

    사용:
        with GeminiFileSession() as session:
            handle = session.get_or_upload(student_video_path)  # 첫 호출만 실제 업로드
            ...                                                  # 후속 호출은 핸들 재사용
        # __exit__ 에서 세션이 업로드한 모든 핸들 일괄 delete (예외 경로 포함, 누수 0)

    스레드 안전: get_or_upload 는 동시 호출 가능. 같은 경로는 in-flight 마커로 이중
    업로드가 차단되고, 서로 다른 경로는 락 밖에서 병렬 업로드된다.
    """

    def __init__(self, client_factory: Callable[[], Any] | None = None) -> None:
        self._client_factory = client_factory or _default_client_factory
        self._client: Any = None
        # path → 업로드된 file 객체 (ACTIVE 성공분만; None 은 캐시 금지 — 재시도 여지).
        self._handles: dict[str, Any] = {}
        # path → 업로드 진행 마커 (같은 경로 이중 업로드 방지, MEDIUM-2).
        self._inflight: dict[str, threading.Event] = {}
        # 락=맵/마커만 보호 (업로드/폴링은 락 밖). 근거: 27-PLAN-REVIEW MEDIUM-2.
        self._lock = threading.Lock()

    def _get_client(self) -> Any:
        """genai.Client lazy-init + 캐시 (첫 업로드 시 1회 생성)."""
        with self._lock:
            if self._client is None:
                self._client = self._client_factory()
            return self._client

    def get_or_upload(self, video_path: str, *, mime_type: str = "video/mp4") -> Any | None:
        """로컬 영상 → File API 핸들. 캐시 hit 시 즉시 반환, miss 시 업로드+ACTIVE 폴링.

        락=맵/마커만 (업로드=락 밖). 흐름:
          (1) 락 안: _handles hit → 즉시 반환. miss + _inflight 마커 있음 → 락 해제 후
              Event wait → 재조회(같은 경로 이중 업로드 방지). 없음 → 자기 Event 등록 후
              업로더가 되어 락 해제.
          (2) 락 밖: 업로드 + ACTIVE 폴링 (수십 초 I/O — 경로 간 병렬 보존).
          (3) 락 안: 성공 시 _handles 기록, _inflight 제거 (finally — 실패 포함, 대기
              스레드 기아 방지) + Event set.

        타임아웃/FAILED/APIError → log.warning + None (graceful — 분석 비차단).
        None 은 캐시하지 않는다 (재시도 여지). in-flight 마커는 반드시 해제.
        """
        my_event: threading.Event
        while True:
            with self._lock:
                handle = self._handles.get(video_path)
                if handle is not None:
                    return handle
                waiting = self._inflight.get(video_path)
                if waiting is None:
                    # 업로더 확정 — 마커 등록 후 락 해제하고 업로드 (락 밖).
                    my_event = threading.Event()
                    self._inflight[video_path] = my_event
                    break
            # 다른 스레드가 같은 경로 업로드 중 — 락 밖에서 대기 후 재조회.
            waiting.wait()

        result: Any | None = None
        try:
            result = self._upload_and_wait_active(video_path, mime_type)
        finally:
            with self._lock:
                if result is not None:
                    self._handles[video_path] = result
                self._inflight.pop(video_path, None)
            # Event set 은 락 밖 — 대기 스레드가 즉시 재조회 진입.
            my_event.set()
        return result

    def _upload_and_wait_active(self, video_path: str, mime_type: str) -> Any | None:
        """File API 업로드 + PROCESSING→ACTIVE 폴링 (client.py:210-279 정본 포팅).

        UploadFileConfig TypeError stub 폴백 + 한글 파일명 ascii-safe 복사 포함.
        폴링 상수는 client.py 의 정본(_FILES_PROCESSING_TIMEOUT_S/_FILES_POLL_INTERVAL_S)
        을 재사용 — 신규 상수 발명 금지.
        """
        from google.genai import errors as genai_errors  # lazy
        from google.genai import types as genai_types  # lazy

        # client 생성 실패(API 키 부재/SSM fetch 실패 등)는 graceful None — 소비처가 자체
        # 업로드 폴백으로 분석을 비차단(27-04 must_have). 여기서 raise 하면 _process 가 세션
        # 생성 시점(try 진입 전)에 깨져 keyless 환경(Lambda CPU 폴백·단위 테스트)이 전면 실패.
        try:
            client = self._get_client()
        except Exception as exc:  # noqa: BLE001 - client 생성 실패 → graceful skip
            log.warning("GeminiFileSession client 생성 실패 — graceful skip: %s", exc)
            return None
        upload_path, tmp_path = _ascii_safe_path(video_path)
        try:
            try:
                uploaded = client.files.upload(
                    file=upload_path,
                    config=genai_types.UploadFileConfig(mime_type=mime_type),
                )
            except TypeError:
                # 일부 stub 환경에서 UploadFileConfig 미지원 — kwargs file 단독 호출.
                uploaded = client.files.upload(file=upload_path)
            except genai_errors.APIError as exc:
                log.warning(
                    "GeminiFileSession upload APIError code=%s — graceful skip.",
                    getattr(exc, "code", None),
                )
                return None
            return self._wait_for_active(client, uploaded)
        finally:
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _wait_for_active(self, client: Any, uploaded: Any) -> Any | None:
        """Files API state machine — ACTIVE 면 객체, FAILED/timeout 면 None (graceful)."""
        import time

        from google.genai import errors as genai_errors  # lazy

        # 폴링 상수/state helper 는 client.py 정본 재사용 (신규 상수 발명 금지).
        from .client import (
            _FILES_POLL_INTERVAL_S,
            _FILES_PROCESSING_TIMEOUT_S,
            _state_name,
        )

        start = time.monotonic()
        state_name = _state_name(uploaded)
        while state_name == "PROCESSING":
            if time.monotonic() - start > _FILES_PROCESSING_TIMEOUT_S:
                log.warning(
                    "GeminiFileSession Files API processing > %ds — graceful skip.",
                    int(_FILES_PROCESSING_TIMEOUT_S),
                )
                return None
            time.sleep(_FILES_POLL_INTERVAL_S)
            try:
                uploaded = client.files.get(name=uploaded.name)
            except genai_errors.APIError as exc:
                log.warning(
                    "GeminiFileSession files.get APIError code=%s — graceful skip.",
                    getattr(exc, "code", None),
                )
                return None
            state_name = _state_name(uploaded)

        if state_name == "FAILED":
            log.warning(
                "GeminiFileSession Files API state=FAILED — graceful skip (name=%s).",
                getattr(uploaded, "name", "?"),
            )
            return None
        if state_name != "ACTIVE":
            log.warning(
                "GeminiFileSession Files API state=%s 미지원 — graceful skip.", state_name
            )
            return None
        return uploaded

    def close(self) -> None:
        """세션이 업로드한 모든 핸들 일괄 delete (누수 0, T-27-06).

        20GB 적체(2026-07-06 실증) → RESOURCE_EXHAUSTED 방어. 각 delete 실패는 best-effort
        (log.warning) — 정리 실패는 나머지 핸들 정리나 분석을 막지 않는다
        (gemini_vision_scorer.py:1283-1336 finally 일괄 delete 정본 복제).
        """
        with self._lock:
            handles = list(self._handles.values())
            self._handles.clear()
        if not handles or self._client is None:
            return
        client = self._client
        for handle in handles:
            name = getattr(handle, "name", None)
            if not name:
                continue
            try:
                client.files.delete(name=name)
            except Exception:  # noqa: BLE001 - 정리 실패는 분석을 막지 않는다
                log.warning("Gemini 업로드 파일 삭제 실패 (graceful): %s", name)

    def __enter__(self) -> "GeminiFileSession":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        # 예외 경로 포함 — 누수 0 불변 (T-27-06).
        self.close()


__all__ = ["GeminiFileSession"]
