"""RTMW onnxruntime 결정론 모드 유닛 테스트 (Phase 25 근본원인 #2).

실 GPU/onnxruntime 불필요 — 순수 함수 + fake ort module 주입으로 검증:
  1. env 게이트 off = no-op (fake ort 무접촉, onnxruntime import 0 — 프로덕션 byte-동일)
  2. env 게이트 on = InferenceSession patch → CUDA EP 결정론 옵션 + 세션 옵션 주입
  3. 구간 종료/예외 시 원복 (구간 밖 onnxruntime 사용자 무영향)
  4. provider 옵션 병합 순수 함수 (문자열/tuple/CPU 케이스)
  5. rtmw_engine 이 Wholebody 생성 구간을 CM 으로 감싸는 배선 (mock rtmlib)
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock

import pytest

from sunity_shared.analysis.pose_engines.rtmw.ort_determinism import (
    DETERMINISTIC_CUDA_PROVIDER_OPTIONS,
    RTMW_DETERMINISTIC_ENV,
    apply_deterministic_provider_options,
    configure_session_options,
    deterministic_enabled,
    deterministic_inference_session,
)


# ── fakes ─────────────────────────────────────────────────────────────────

class _FakeSessionOptions:
    """onnxruntime.SessionOptions duck-type stub."""

    def __init__(self) -> None:
        self.intra_op_num_threads = 0
        self.inter_op_num_threads = 0
        self.config_entries: dict[str, str] = {}

    def add_session_config_entry(self, key: str, value: str) -> None:
        self.config_entries[key] = value


class _FakeSessionOptionsNoConfigEntry:
    """add_session_config_entry 미보유 구현체 — graceful skip 검증."""

    def __init__(self) -> None:
        self.intra_op_num_threads = 0
        self.inter_op_num_threads = 0


def _make_fake_ort() -> types.SimpleNamespace:
    """fake onnxruntime module — InferenceSession 은 받은 kwargs 를 기록."""
    calls: list[dict] = []

    def _inference_session(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return "fake-session"

    fake = types.SimpleNamespace(
        InferenceSession=_inference_session,
        SessionOptions=_FakeSessionOptions,
    )
    fake._calls = calls
    fake._original_inference_session = _inference_session
    return fake


# ── 1. env 게이트 ─────────────────────────────────────────────────────────

def test_deterministic_enabled_env_gate(monkeypatch):
    monkeypatch.delenv(RTMW_DETERMINISTIC_ENV, raising=False)
    assert deterministic_enabled() is False

    monkeypatch.setenv(RTMW_DETERMINISTIC_ENV, "1")
    assert deterministic_enabled() is True

    monkeypatch.setenv(RTMW_DETERMINISTIC_ENV, "0")
    assert deterministic_enabled() is False


def test_env_off_is_noop(monkeypatch):
    """게이트 off: fake ort 무접촉 — InferenceSession identity 불변 (요구 2)."""
    monkeypatch.delenv(RTMW_DETERMINISTIC_ENV, raising=False)
    fake_ort = _make_fake_ort()

    with deterministic_inference_session(fake_ort) as active:
        assert active is False
        assert fake_ort.InferenceSession is fake_ort._original_inference_session
        # 옵션 주입 없이 그대로 통과
        fake_ort.InferenceSession(path_or_bytes="m.onnx", providers=["CUDAExecutionProvider"])

    call = fake_ort._calls[0]
    assert call["kwargs"]["providers"] == ["CUDAExecutionProvider"]
    assert "sess_options" not in call["kwargs"]


# ── 2. env 게이트 on — patch 주입 ─────────────────────────────────────────

def test_env_on_injects_deterministic_options(monkeypatch):
    monkeypatch.setenv(RTMW_DETERMINISTIC_ENV, "1")
    fake_ort = _make_fake_ort()

    with deterministic_inference_session(fake_ort) as active:
        assert active is True
        assert fake_ort.InferenceSession is not fake_ort._original_inference_session
        # rtmlib BaseTool 호출 형태 재현 (base.py L80-81)
        result = fake_ort.InferenceSession(
            path_or_bytes="rtmw-x-384.onnx", providers=["CUDAExecutionProvider"]
        )
        assert result == "fake-session"

    call = fake_ort._calls[0]
    # CUDA provider 에 결정론 옵션 tuple 주입
    assert call["kwargs"]["providers"] == [
        ("CUDAExecutionProvider", DETERMINISTIC_CUDA_PROVIDER_OPTIONS)
    ]
    assert call["kwargs"]["providers"][0][1]["cudnn_conv_algo_search"] == "DEFAULT"
    # 세션 옵션: 스레드 1 + deterministic compute config
    so = call["kwargs"]["sess_options"]
    assert so.intra_op_num_threads == 1
    assert so.inter_op_num_threads == 1
    assert so.config_entries == {"session.use_deterministic_compute": "1"}
    # 원본 path_or_bytes kwargs 보존
    assert call["kwargs"]["path_or_bytes"] == "rtmw-x-384.onnx"


def test_env_on_sets_cublas_workspace_config(monkeypatch):
    monkeypatch.setenv(RTMW_DETERMINISTIC_ENV, "1")
    monkeypatch.delenv("CUBLAS_WORKSPACE_CONFIG", raising=False)
    fake_ort = _make_fake_ort()

    import os

    with deterministic_inference_session(fake_ort):
        assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"


def test_env_on_respects_operator_cublas_override(monkeypatch):
    """운영자가 명시한 CUBLAS_WORKSPACE_CONFIG 는 존중 (setdefault)."""
    monkeypatch.setenv(RTMW_DETERMINISTIC_ENV, "1")
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":16:8")
    fake_ort = _make_fake_ort()

    import os

    with deterministic_inference_session(fake_ort):
        assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":16:8"


# ── 3. 원복 ───────────────────────────────────────────────────────────────

def test_patch_restored_after_exit(monkeypatch):
    monkeypatch.setenv(RTMW_DETERMINISTIC_ENV, "1")
    fake_ort = _make_fake_ort()

    with deterministic_inference_session(fake_ort):
        pass
    assert fake_ort.InferenceSession is fake_ort._original_inference_session


def test_patch_restored_on_exception(monkeypatch):
    monkeypatch.setenv(RTMW_DETERMINISTIC_ENV, "1")
    fake_ort = _make_fake_ort()

    with pytest.raises(RuntimeError, match="boom"):
        with deterministic_inference_session(fake_ort):
            raise RuntimeError("boom")
    assert fake_ort.InferenceSession is fake_ort._original_inference_session


# ── 4. 순수 함수 ──────────────────────────────────────────────────────────

def test_provider_options_string_entry():
    out = apply_deterministic_provider_options(["CUDAExecutionProvider"])
    assert out == [("CUDAExecutionProvider", DETERMINISTIC_CUDA_PROVIDER_OPTIONS)]


def test_provider_options_tuple_entry_preserves_device_id():
    """rtmlib 'cuda:N' 경로 — ('CUDAExecutionProvider', {'device_id': 1}) 병합."""
    out = apply_deterministic_provider_options(
        [("CUDAExecutionProvider", {"device_id": 1})]
    )
    assert len(out) == 1
    name, opts = out[0]
    assert name == "CUDAExecutionProvider"
    assert opts["device_id"] == 1  # 기존 옵션 보존
    assert opts["cudnn_conv_algo_search"] == "DEFAULT"  # 결정론 키 주입


def test_provider_options_cpu_untouched():
    out = apply_deterministic_provider_options(["CPUExecutionProvider"])
    assert out == ["CPUExecutionProvider"]


def test_configure_session_options_graceful_without_config_entry():
    """add_session_config_entry 미보유 stub — 스레드 설정만 적용, 예외 0."""
    so = _FakeSessionOptionsNoConfigEntry()
    configure_session_options(so)
    assert so.intra_op_num_threads == 1
    assert so.inter_op_num_threads == 1


# ── 5. rtmw_engine 배선 ───────────────────────────────────────────────────

def test_rtmw_engine_wraps_wholebody_in_deterministic_cm(monkeypatch, tmp_path):
    """RTMWPoseEngine.__init__ 이 Wholebody 생성을 deterministic CM 구간 안에서 수행.

    mock rtmlib 주입 — Wholebody 생성 시점에 CM 활성 여부를 기록해 검증.
    """
    import json
    import sys

    from sunity_shared.analysis.pose_engines.rtmw import rtmw_engine as eng_mod

    manifest = tmp_path / "weights_manifest.json"
    manifest.write_text(
        json.dumps({"weights": [{"name": "w", "production_eligible": True}]}),
        encoding="utf-8",
    )

    active_during_init: list[bool] = []

    import contextlib

    @contextlib.contextmanager
    def _fake_cm():
        active_during_init.append(True)
        yield True
        active_during_init.append(False)

    monkeypatch.setattr(eng_mod, "deterministic_inference_session", _fake_cm)

    fake_rtmlib = types.ModuleType("rtmlib")

    constructed_inside_cm: list[bool] = []

    class _FakeWholebody:
        def __init__(self, **kwargs):
            # CM 진입(True 기록) 후 / 종료(False 기록) 전에 생성돼야 함
            constructed_inside_cm.append(
                active_during_init == [True]  # entered, not yet exited
            )

    fake_rtmlib.Wholebody = _FakeWholebody
    monkeypatch.setitem(sys.modules, "rtmlib", fake_rtmlib)
    monkeypatch.setenv("RTMW_ONNX_PATH", "/fake/rtmw.onnx")

    eng_mod.RTMWPoseEngine(manifest_path=manifest)

    assert constructed_inside_cm == [True]
    assert active_during_init == [True, False]  # CM 진입/종료 모두 발생
