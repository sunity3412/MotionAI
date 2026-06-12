"""Plan 17-01 Task 2 — GeminiVisionCall 베이스 클라이언트 단위 테스트.

박제 정신:
  · Files API state machine (PROCESSING → ACTIVE / FAILED / timeout) 박제.
  · retry: ValidationError/JSONDecodeError 1회 재시도, APIError 5xx 1회 backoff retry,
    APIError 4xx 즉시 graceful return None.
  · 객관성 가드 (G1) 매치 → ValueError (graceful X — hard fail).
  · api_key_loader 실패 → graceful return None.

외부 네트워크 호출 0 — monkeypatch 로 genai.Client / files / models 전부 stub.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, Field, ValidationError

from sunity_shared.gemini import client as client_mod
from sunity_shared.gemini.client import GeminiVisionCall


# ─────────────────── 더미 schema ───────────────────


class _StubSchema(BaseModel):
    label: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)


# ─────────────────── Fake genai SDK 박제 helpers ───────────────────


class _FakeFile:
    def __init__(self, state: str = "ACTIVE", name: str = "files/abc") -> None:
        self.state = SimpleNamespace(name=state)
        self.name = name


class _FakeFiles:
    """Files API stub — upload + get."""

    def __init__(
        self,
        *,
        upload_state: str = "ACTIVE",
        get_sequence: list[str] | None = None,
    ) -> None:
        self.upload_state = upload_state
        self.get_sequence = list(get_sequence) if get_sequence else []
        self.upload_calls = 0
        self.get_calls = 0

    def upload(self, *, file: Any) -> _FakeFile:
        self.upload_calls += 1
        return _FakeFile(state=self.upload_state)

    def get(self, *, name: str) -> _FakeFile:
        self.get_calls += 1
        if self.get_sequence:
            return _FakeFile(state=self.get_sequence.pop(0), name=name)
        return _FakeFile(state="ACTIVE", name=name)


class _FakeModels:
    """generate_content stub — sequence of responses or exceptions."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _FakeClient:
    def __init__(self, files: _FakeFiles, models: _FakeModels) -> None:
        self.files = files
        self.models = models


def _patch_genai(monkeypatch, files: _FakeFiles, models: _FakeModels) -> _FakeClient:
    """genai.Client / time.sleep / time.monotonic 박제."""
    fake_client = _FakeClient(files, models)

    def _fake_client_ctor(*, api_key: str) -> _FakeClient:  # noqa: ARG001 - signature 박제
        return fake_client

    monkeypatch.setattr(client_mod.genai, "Client", _fake_client_ctor)
    # 폴링 sleep 박제 — 테스트 속도 박제.
    monkeypatch.setattr(client_mod.time, "sleep", lambda _s: None)
    return fake_client


def _ok_response(payload: dict) -> Any:
    """parsed 가 채워진 정상 응답."""
    return SimpleNamespace(parsed=_StubSchema.model_validate(payload), text=json.dumps(payload))


def _text_only_response(payload: dict) -> Any:
    """parsed=None + text JSON 응답 (폴백 path 박제)."""
    return SimpleNamespace(parsed=None, text=json.dumps(payload))


def _invalid_text_response(text: str) -> Any:
    return SimpleNamespace(parsed=None, text=text)


# ─────────────────── 테스트 ───────────────────


def _video(tmp_path: Path, name: str = "x.mp4") -> str:
    p = tmp_path / name
    p.write_bytes(b"fake-mp4")
    return str(p)


def _make_call(**kw: Any) -> GeminiVisionCall:
    defaults = dict(
        schema=_StubSchema,
        model="gemini-3.1-pro-preview",
        prompt="동작 분류",
        api_key_loader=lambda: "AQ.test-key",
    )
    defaults.update(kw)
    return GeminiVisionCall(**defaults)


class TestActiveStateHappyPath:
    def test_active_with_parsed_returns_instance(self, tmp_path, monkeypatch) -> None:
        files = _FakeFiles(upload_state="ACTIVE")
        models = _FakeModels([_ok_response({"label": "invert", "score": 0.9})])
        _patch_genai(monkeypatch, files, models)

        call = _make_call()
        result = call.call(_video(tmp_path))
        assert isinstance(result, _StubSchema)
        assert result.label == "invert"
        assert files.upload_calls == 1


class TestProcessingToActive:
    def test_polls_until_active(self, tmp_path, monkeypatch) -> None:
        files = _FakeFiles(
            upload_state="PROCESSING",
            get_sequence=["PROCESSING"] * 5 + ["ACTIVE"],
        )
        models = _FakeModels([_ok_response({"label": "fox", "score": 0.7})])
        _patch_genai(monkeypatch, files, models)

        call = _make_call()
        result = call.call(_video(tmp_path))
        assert isinstance(result, _StubSchema)
        assert files.get_calls >= 5


class TestFailedState:
    def test_failed_returns_none(self, tmp_path, monkeypatch) -> None:
        files = _FakeFiles(
            upload_state="PROCESSING",
            get_sequence=["PROCESSING", "FAILED"],
        )
        models = _FakeModels([])  # generate_content 호출 0
        _patch_genai(monkeypatch, files, models)

        call = _make_call()
        result = call.call(_video(tmp_path))
        assert result is None


class TestTimeout:
    def test_timeout_returns_none(self, tmp_path, monkeypatch) -> None:
        files = _FakeFiles(
            upload_state="PROCESSING",
            get_sequence=["PROCESSING"] * 200,
        )
        models = _FakeModels([])
        _patch_genai(monkeypatch, files, models)

        # time.monotonic 가 큰 값으로 점프하도록 박제 — 120s 초과 시뮬.
        seq = iter([0.0, 200.0])
        monkeypatch.setattr(client_mod.time, "monotonic", lambda: next(seq))

        call = _make_call()
        result = call.call(_video(tmp_path))
        assert result is None


class TestParsedNoneTextFallback:
    def test_parsed_none_with_valid_json_text(self, tmp_path, monkeypatch) -> None:
        files = _FakeFiles(upload_state="ACTIVE")
        models = _FakeModels([_text_only_response({"label": "split", "score": 0.6})])
        _patch_genai(monkeypatch, files, models)

        call = _make_call()
        result = call.call(_video(tmp_path))
        assert isinstance(result, _StubSchema)
        assert result.label == "split"


class TestValidationErrorRetry:
    def test_two_validation_errors_return_none(self, tmp_path, monkeypatch) -> None:
        files = _FakeFiles(upload_state="ACTIVE")
        # 두 번 모두 schema 위반 (score=2.0 범위 초과).
        bad = _text_only_response({"label": "x", "score": 2.0})
        models = _FakeModels([bad, bad])
        _patch_genai(monkeypatch, files, models)

        call = _make_call()
        result = call.call(_video(tmp_path))
        assert result is None
        # retry 1회 박제 — generate_content 호출 2회.
        assert len(models.calls) == 2

    def test_first_validation_error_then_success(self, tmp_path, monkeypatch) -> None:
        files = _FakeFiles(upload_state="ACTIVE")
        bad = _text_only_response({"label": "x", "score": 2.0})
        good = _ok_response({"label": "ok", "score": 0.5})
        models = _FakeModels([bad, good])
        _patch_genai(monkeypatch, files, models)

        call = _make_call()
        result = call.call(_video(tmp_path))
        assert isinstance(result, _StubSchema)
        assert result.label == "ok"


class TestAPIErrorRetry:
    def test_5xx_retry_then_success(self, tmp_path, monkeypatch) -> None:
        from google.genai import errors as genai_errors

        files = _FakeFiles(upload_state="ACTIVE")
        err500 = genai_errors.APIError(500, {"error": {"message": "internal"}})
        good = _ok_response({"label": "ok", "score": 0.5})
        models = _FakeModels([err500, good])
        _patch_genai(monkeypatch, files, models)

        call = _make_call()
        result = call.call(_video(tmp_path))
        assert isinstance(result, _StubSchema)
        assert len(models.calls) == 2

    def test_4xx_immediate_none(self, tmp_path, monkeypatch) -> None:
        from google.genai import errors as genai_errors

        files = _FakeFiles(upload_state="ACTIVE")
        err401 = genai_errors.APIError(401, {"error": {"message": "unauthorized"}})
        models = _FakeModels([err401])
        _patch_genai(monkeypatch, files, models)

        call = _make_call()
        result = call.call(_video(tmp_path))
        assert result is None
        # 즉시 graceful — retry 0.
        assert len(models.calls) == 1


class TestRejectGuardHardFail:
    def test_reject_regex_match_raises_value_error(self, tmp_path, monkeypatch) -> None:
        files = _FakeFiles(upload_state="ACTIVE")
        # 응답 text 가 점수 박제 — guardrail 이 ValueError raise (graceful X).
        bad_text = SimpleNamespace(
            parsed=None,
            text='{"label": "x", "score": 0.5} 이 자세는 87점',
        )
        models = _FakeModels([bad_text])
        _patch_genai(monkeypatch, files, models)

        call = _make_call(enforce_object_guard=True)
        with pytest.raises(ValueError, match="점수"):
            call.call(_video(tmp_path))


class TestApiKeyLoaderFailure:
    def test_loader_runtime_error_returns_none(self, tmp_path, monkeypatch) -> None:
        files = _FakeFiles(upload_state="ACTIVE")
        models = _FakeModels([])
        _patch_genai(monkeypatch, files, models)

        def _raise() -> str:
            raise RuntimeError("API 키 미설정")

        call = _make_call(api_key_loader=_raise)
        result = call.call(_video(tmp_path))
        assert result is None
        # genai.Client 미호출 박제 — upload 도 0.
        assert files.upload_calls == 0
