"""Plan 5-04 Task 2 — RunPod server.py `_warmup` Gemini fail-loud 단위 테스트.

박제 정신 (D-12 / D-15 / D-16 / Common Pitfall 4):
  · D-12 — server.py 변경 = `_warmup` 안 한 줄 추가 (외부 시그너처 무변경)
  · D-15 — GEMINI_API_KEY 누락 시 SSM Parameter Store fallback path 박제
  · D-16 — google-genai SDK lazy import (server.py 자체는 미import)
  · Common Pitfall 4 — Pod env 누락 시 startup 에서 fail-loud, 첫 분석 시점
    갑작스러운 RuntimeError 박제 회피

테스트 4 종:
  · test_warmup_fallback_default_succeeds — env 미설정 시 정상 (회귀 0)
  · test_warmup_fails_loud_when_gemini_enabled_without_key — env ON + 키 누락 시
    log.error + log.exception 박제 (outer except 가 RuntimeError 흡수, server 살아있음)
  · test_warmup_succeeds_with_gemini_and_key — env ON + key 정상 시 통과
  · test_warmup_calls_ensure_recognizer_when_gemini_enabled — _ensure_recognizer 호출 검증

mock-based — 실 Gemini / 실 pipeline 모듈 import 0.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


_RUNPOD_DIR = Path(__file__).resolve().parents[1] / "runpod_inference"
_BACKEND = Path(__file__).resolve().parents[1]


def _import_server() -> Any:
    """runpod_inference/server.py 를 동적 import + 강제 재로드.

    global state (`_pipeline_module`, `_AUTH_TOKEN`) 격리를 위해 매 테스트마다 reload.
    """
    sys.modules.pop("runpod_inference_server", None)
    spec = importlib.util.spec_from_file_location(
        "runpod_inference_server", _RUNPOD_DIR / "server.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["runpod_inference_server"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """매 테스트마다 Plan 5-03 박제 env 초기화 — 다른 테스트의 누수 차단."""
    monkeypatch.delenv("GEMINI_RECOGNIZER_ENABLED", raising=False)
    monkeypatch.delenv("RECOGNIZER_BACKEND", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def _make_pipeline_mock(
    gemini_enabled: bool, ensure_recognizer_return: Any = None
) -> MagicMock:
    """pipeline 모듈 mock 박제 — _ensure_adapters / _ensure_recognizer / _gemini_enabled."""
    mod = MagicMock()
    mod._ensure_adapters = MagicMock()
    mod._gemini_enabled = MagicMock(return_value=gemini_enabled)
    mod._ensure_recognizer = MagicMock(
        return_value=ensure_recognizer_return or MagicMock(name="FallbackRecognizer")
    )
    return mod


def test_warmup_fallback_default_succeeds(caplog: pytest.LogCaptureFixture) -> None:
    """env 미설정 (RECOGNIZER_BACKEND 미설정) → _warmup 정상. 회귀 0 박제.

    Plan 5-03 default = FallbackRecognizer 박제 정합.
    """
    server = _import_server()
    mock_pipeline = _make_pipeline_mock(gemini_enabled=False)

    with patch.object(server, "_load_pipeline_module", return_value=mock_pipeline):
        with caplog.at_level(logging.INFO, logger="runpod_inference"):
            # FastAPI startup hook 직접 호출 (TestClient 없이도 동작 박제 정합)
            server._warmup()

    # 회귀 0 검증:
    mock_pipeline._ensure_adapters.assert_called_once()
    mock_pipeline._ensure_recognizer.assert_called_once()
    # Gemini 미활성 — _load_api_key 호출 0
    assert "Gemini API 키 검증" not in caplog.text
    # RuntimeError fail-loud 박제 X (env OFF default)
    assert "Gemini API 키 검증 실패" not in caplog.text


def test_warmup_fails_loud_when_gemini_enabled_without_key(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """env RECOGNIZER_BACKEND=gemini + GEMINI_API_KEY 미설정 + SSM fail
    → _warmup 안 log.error + RuntimeError → outer except 흡수 (server 살아있음).

    Common Pitfall 4 박제 — startup 시점 명시 실패, 첫 /analyze 갑작스러운 에러 X.
    fail-loud 정신 = 로그 명시 + 첫 분석 시점 명시 실패.
    """
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    # GEMINI_API_KEY 미설정 + SSM 도 fail 박제

    server = _import_server()
    mock_pipeline = _make_pipeline_mock(gemini_enabled=True)

    # _load_api_key 가 RuntimeError 발생 박제 (SSM fetch 실패 path)
    fake_load_api_key = MagicMock(
        side_effect=RuntimeError(
            "Gemini API 키 fetch 실패 — env GEMINI_API_KEY 미설정 + "
            "AWS Parameter Store /sunity/motion/gemini-api-key 조회 실패"
        )
    )

    # 모듈 박제 path — gemini_moment_extractor._load_api_key 가 _warmup 안에서 import 됨.
    fake_module = MagicMock()
    fake_module._load_api_key = fake_load_api_key

    with patch.object(server, "_load_pipeline_module", return_value=mock_pipeline):
        with patch.dict(
            sys.modules,
            {"sunity_shared.judging.gemini_moment_extractor": fake_module},
        ):
            with caplog.at_level(logging.ERROR, logger="runpod_inference"):
                # _warmup 은 outer except Exception 으로 RuntimeError 흡수 박제 —
                # server FastAPI 자체는 살아있음, 첫 /analyze 시점 503/실패 path.
                server._warmup()

    # fail-loud 검증:
    #  1. _ensure_adapters + _ensure_recognizer 모두 호출
    mock_pipeline._ensure_adapters.assert_called_once()
    mock_pipeline._ensure_recognizer.assert_called_once()
    #  2. _load_api_key 가 호출됨 (gemini_enabled True → 검증 진입)
    fake_load_api_key.assert_called_once()
    #  3. log.error 박제 (사용자 가독 메시지)
    assert "Gemini API 키 검증 실패" in caplog.text
    assert "GEMINI_API_KEY" in caplog.text
    assert "/sunity/motion/gemini-api-key" in caplog.text
    #  4. log.exception 박제 (outer except — traceback 박제)
    assert "워밍업 실패" in caplog.text


def test_warmup_succeeds_with_gemini_and_key(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """env RECOGNIZER_BACKEND=gemini + GEMINI_API_KEY="test-key" → _warmup 정상.

    Gemini 어댑터 박제 — API 키 검증 PASS path.
    """
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    server = _import_server()
    mock_pipeline = _make_pipeline_mock(gemini_enabled=True)

    # _load_api_key 정상 반환 박제
    fake_load_api_key = MagicMock(return_value="test-key")
    fake_module = MagicMock()
    fake_module._load_api_key = fake_load_api_key

    with patch.object(server, "_load_pipeline_module", return_value=mock_pipeline):
        with patch.dict(
            sys.modules,
            {"sunity_shared.judging.gemini_moment_extractor": fake_module},
        ):
            with caplog.at_level(logging.INFO, logger="runpod_inference"):
                server._warmup()

    # 정상 검증:
    mock_pipeline._ensure_adapters.assert_called_once()
    mock_pipeline._ensure_recognizer.assert_called_once()
    fake_load_api_key.assert_called_once()
    # API 키 검증 완료 log.info 박제
    assert "Gemini API 키 검증 완료" in caplog.text
    # 실패 박제 X (RuntimeError 없음)
    assert "Gemini API 키 검증 실패" not in caplog.text
    assert "워밍업 실패" not in caplog.text


def test_warmup_calls_ensure_recognizer_when_gemini_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """env RECOGNIZER_BACKEND=gemini → _ensure_recognizer + _gemini_enabled 호출 검증.

    Plan 5-04 박제 정신 = `_warmup` 안 `_ensure_recognizer()` 명시 호출 (fail-loud 박제).
    """
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    server = _import_server()

    fake_recognizer = MagicMock(name="GeminiTechniqueRecognizer")
    mock_pipeline = _make_pipeline_mock(
        gemini_enabled=True, ensure_recognizer_return=fake_recognizer
    )

    fake_load_api_key = MagicMock(return_value="test-key")
    fake_module = MagicMock()
    fake_module._load_api_key = fake_load_api_key

    with patch.object(server, "_load_pipeline_module", return_value=mock_pipeline):
        with patch.dict(
            sys.modules,
            {"sunity_shared.judging.gemini_moment_extractor": fake_module},
        ):
            server._warmup()

    # _ensure_recognizer 1회 호출 박제
    mock_pipeline._ensure_recognizer.assert_called_once()
    # _gemini_enabled 도 호출됨 (분기 박제)
    mock_pipeline._gemini_enabled.assert_called_once()
    # _load_api_key 도 호출됨 (Gemini path 의 키 검증 박제)
    fake_load_api_key.assert_called_once()
