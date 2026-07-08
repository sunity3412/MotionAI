"""Phase 27 SPD-02 / D-04 — GeminiFileSession 단위 테스트.

박제 정신:
  · D-04 핵심: 같은 로컬 경로는 분석당 File API 업로드 1회 + 핸들 재사용 (동시 호출 포함).
  · 누수 0 불변: close() / __exit__(예외 경로) 이 세션 업로드분을 일괄 delete (T-27-06).
  · 락 협소화(MEDIUM-2): 락은 맵/마커만 보호 — 업로드/폴링은 락 밖 (27-05 prefetch 전제).
  · delete best-effort: delete 예외는 나머지 핸들 정리를 막지 않는다 (T-27-06).

외부 네트워크 호출 0 — tests/gemini/fake_genai.py 의 Fake* stub 재사용 (27-01 산출).
"""

from __future__ import annotations

import json
import threading
import time
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, Field

from sunity_shared.gemini import client as client_mod
from sunity_shared.gemini.client import GeminiVisionCall
from sunity_shared.gemini.file_session import GeminiFileSession
from tests.gemini.fake_genai import FakeClient, FakeFile, FakeFiles, FakeModels, patch_genai


def _factory(files: FakeFiles, models: FakeModels | None = None):
    """client_factory 주입용 — 단일 FakeClient 를 재사용해 세션 내내 공유."""
    client = FakeClient(files, models or FakeModels())
    return lambda: client


# ─────────────────── Test 1: 같은 경로 업로드 1회 (D-04 핵심) ───────────────────


class TestUploadOncePerPath:
    def test_same_path_uploads_once(self) -> None:
        files = FakeFiles()
        session = GeminiFileSession(client_factory=_factory(files))

        h1 = session.get_or_upload("/tmp/student.mp4")
        h2 = session.get_or_upload("/tmp/student.mp4")
        h3 = session.get_or_upload("/tmp/student.mp4")

        assert files.upload_calls == 1
        assert h1.name == h2.name == h3.name


# ─────────────────── Test 2: 다중 경로 close() 일괄 delete (누수 0) ───────────────────


class TestBatchDeleteOnClose:
    def test_close_deletes_all_uploaded(self) -> None:
        files = FakeFiles()
        session = GeminiFileSession(client_factory=_factory(files))

        session.get_or_upload("/tmp/student.mp4")
        session.get_or_upload("/tmp/reference.mp4")
        session.close()

        assert files.delete_calls == 2
        assert sorted(files.deleted_names) == sorted(files.uploaded_names)


# ─────────────────── Test 3: context manager 예외 경로 누수 0 ───────────────────


class TestContextManagerExceptionPath:
    def test_exit_deletes_and_propagates(self) -> None:
        files = FakeFiles()

        with pytest.raises(RuntimeError, match="분석 중단"):
            with GeminiFileSession(client_factory=_factory(files)) as session:
                session.get_or_upload("/tmp/student.mp4")
                session.get_or_upload("/tmp/reference.mp4")
                raise RuntimeError("분석 중단")

        # 예외가 전파되더라도 __exit__ 이 일괄 delete (누수 0 불변).
        assert files.delete_calls == 2
        assert sorted(files.deleted_names) == sorted(files.uploaded_names)


# ─────────────────── Test 4: 업로드 FAILED → None, 성공분만 delete ───────────────────


class TestUploadFailedGraceful:
    def test_failed_upload_returns_none_and_not_cached(self) -> None:
        bad_files = FakeFiles(upload_state="FAILED")
        session = GeminiFileSession(client_factory=_factory(bad_files))

        bad_handle = session.get_or_upload("/tmp/broken.mp4")
        assert bad_handle is None

        # 실패 핸들은 캐시에 없음 → close() 는 delete 0 (성공분만 정리).
        session.close()
        assert bad_files.delete_calls == 0

        # 재조회 시 다시 업로드 시도 여지(None 은 캐시 금지).
        session.get_or_upload("/tmp/broken.mp4")
        assert bad_files.upload_calls == 2

    def test_close_deletes_only_successful(self) -> None:
        files = FakeFiles(upload_state="ACTIVE")
        session = GeminiFileSession(client_factory=_factory(files))
        session.get_or_upload("/tmp/a.mp4")
        session.get_or_upload("/tmp/b.mp4")
        session.close()
        assert files.delete_calls == 2


# ─────────────────── Test 5: delete 예외 best-effort (raise 안 함) ───────────────────


class _RaisingDeleteFiles(FakeFiles):
    """delete() 가 예외를 던지는 FakeFiles — best-effort 정리 검증."""

    def delete(self, *, name: str) -> None:
        self.delete_calls += 1
        self.deleted_names.append(name)
        raise RuntimeError(f"delete boom: {name}")


class TestDeleteBestEffort:
    def test_delete_exception_continues_and_no_raise(self) -> None:
        files = _RaisingDeleteFiles()
        session = GeminiFileSession(client_factory=_factory(files))
        session.get_or_upload("/tmp/a.mp4")
        session.get_or_upload("/tmp/b.mp4")

        # delete 가 매번 raise 해도 close() 는 나머지 핸들 정리를 계속하고 raise 하지 않는다.
        session.close()
        assert files.delete_calls == 2


# ─────────────────── Test 6: 동시 dedupe (MEDIUM-2 in-flight 마커) ───────────────────


class _BlockingUploadFiles(FakeFiles):
    """첫 업로드를 release Event 까지 블록해, 두 번째 동시 호출이 in-flight 마커에
    걸리는 상황을 재현 (같은 경로 이중 업로드 방지 검증)."""

    def __init__(self, entered: threading.Event, release: threading.Event) -> None:
        super().__init__()
        self._entered = entered
        self._release = release

    def upload(self, *, file, config=None):
        self._entered.set()
        self._release.wait(timeout=5)
        return super().upload(file=file, config=config)


class TestConcurrentSamePathDedupe:
    def test_two_threads_same_path_upload_once(self) -> None:
        entered = threading.Event()
        release = threading.Event()
        files = _BlockingUploadFiles(entered, release)
        session = GeminiFileSession(client_factory=_factory(files))

        results: dict[str, object] = {}

        def worker(key: str) -> None:
            results[key] = session.get_or_upload("/tmp/student.mp4")

        t_a = threading.Thread(target=worker, args=("a",))
        t_a.start()
        # A 스레드가 upload() 안에 진입할 때까지 대기 (업로더 확정).
        assert entered.wait(2)

        t_b = threading.Thread(target=worker, args=("b",))
        t_b.start()
        # B 가 in-flight 마커 wait 에 도달하도록 짧게 양보.
        time.sleep(0.1)

        # 첫 업로드 완료 → 핸들/이벤트 set → B 가 재조회로 동일 핸들 수신.
        release.set()
        t_a.join(5)
        t_b.join(5)

        assert files.upload_calls == 1
        assert results["a"] is not None
        assert results["a"].name == results["b"].name


# ─────────────────── Task 2: GeminiVisionCall.call() 핸들 주입 ───────────────────


class _StubSchema(BaseModel):
    label: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)


def _make_call(**kw) -> GeminiVisionCall:
    defaults = dict(
        schema=_StubSchema,
        model="gemini-3.1-pro-preview",
        prompt="동작 분류",
        api_key_loader=lambda: "AQ.test-key",
    )
    defaults.update(kw)
    return GeminiVisionCall(**defaults)


def _ok_response(payload: dict):
    return SimpleNamespace(parsed=_StubSchema.model_validate(payload), text=json.dumps(payload))


class TestPreuploadedHandleInjection:
    def test_injected_handle_skips_upload_and_delete(self, tmp_path, monkeypatch) -> None:
        # Test 7: preuploaded_handle 주입 → upload/폴링/delete skip, generate 는 주입 핸들로.
        files = FakeFiles()
        models = FakeModels([_ok_response({"label": "invert", "score": 0.9})])
        patch_genai(monkeypatch, client_mod, files=files, models=models)

        handle = FakeFile(name="files/session-shared", state="ACTIVE")
        video = tmp_path / "student.mp4"
        video.write_bytes(b"fake")

        call = _make_call()
        result = call.call(str(video), preuploaded_handle=handle)

        assert isinstance(result, _StubSchema)
        assert result.label == "invert"
        # 세션 소유 핸들 — 업로드/삭제는 세션 책임, call() 은 건드리지 않는다.
        assert files.upload_calls == 0
        assert files.delete_calls == 0
        # generate 는 주입 핸들을 그대로 contents 로 사용.
        assert models.calls[0]["contents"][0] is handle

    def test_no_handle_preserves_upload_and_delete(self, tmp_path, monkeypatch) -> None:
        # Test 8: 핸들 미주입 → 기존과 동일하게 upload 1회 + finally delete 1회 (회귀 가드).
        files = FakeFiles(upload_state="ACTIVE")
        models = FakeModels([_ok_response({"label": "fox", "score": 0.7})])
        patch_genai(monkeypatch, client_mod, files=files, models=models)

        video = tmp_path / "student.mp4"
        video.write_bytes(b"fake")

        call = _make_call()
        result = call.call(str(video))

        assert isinstance(result, _StubSchema)
        assert files.upload_calls == 1
        assert files.delete_calls == 1
