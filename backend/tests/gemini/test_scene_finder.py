"""Plan 17-02 Task 1 — find_scene_flags 단위 테스트.

박제 정신:
  · Plan 17-02 박제 — 영역 C (Finding) 4 flag 정상 호출 + G4 정은지 영상 가드 +
    graceful 폴백 (call None → 빈 flag dict) + env override path.
  · AI-SPEC §6 G4 — `is_reference=True + occlusion_severe=True` 동시 시 flag 폐기 +
    `guardrail_triggered="G4_reference_occlusion_fp"` 박힘. PROJECT.md "정은지 영상
    위양성" 직격.
  · GeminiVisionCall.call 은 monkeypatch 로 stub — 외부 네트워크 호출 0.
  · resolve_model 경로 박제 — GEMINI_C_MODEL_OVERRIDE 가 override path. ALLOWED_MODELS
    화이트리스트 통과 (gemini-3.1-pro-preview).
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest

from sunity_shared.gemini import scene_finder
from sunity_shared.gemini.schemas import FindingFlags


# ─────────────────── 더미 GeminiVisionCall stub ───────────────────


class _StubCall:
    """GeminiVisionCall 대체 — schema/model/prompt/... 인자 기록 + call() 결과 박제."""

    def __init__(self, result: Any) -> None:
        self.result = result
        self.init_kwargs: dict[str, Any] = {}
        self.call_paths: list[str] = []

    def __call__(self, *args: Any, **kwargs: Any) -> "_StubCall":
        # dataclass(...) 호출 박제 — init kwargs 저장 후 self 반환 (call() 사용).
        self.init_kwargs = dict(kwargs)
        return self

    def call(self, video_path: str) -> Any:  # noqa: D401
        self.call_paths.append(video_path)
        return self.result


def _ok_flags(**overrides: Any) -> FindingFlags:
    base = dict(
        grip_visible=True,
        backbend_present=False,
        occlusion_severe=False,
        camera_angle_problematic=False,
        notes_ko="그립 명확, 후굴 없음.",
    )
    base.update(overrides)
    return FindingFlags.model_validate(base)


def _video(tmp_path) -> str:
    p = tmp_path / "ref.mp4"
    p.write_bytes(b"fake-mp4")
    return str(p)


def _patch_call(monkeypatch, stub: _StubCall) -> None:
    monkeypatch.setattr(scene_finder, "GeminiVisionCall", stub)


# ─────────────────── 테스트 ───────────────────


class TestHappyPath:
    """Flash 호출 성공 + 4 flag 정상 → dict 반환."""

    def test_returns_flags_dict_with_meta(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(_ok_flags())
        _patch_call(monkeypatch, stub)

        result = scene_finder.find_scene_flags(_video(tmp_path), is_reference=False)

        assert result is not None
        # 4 flag 박힘.
        assert result["grip_visible"] is True
        assert result["backbend_present"] is False
        assert result["occlusion_severe"] is False
        assert result["camera_angle_problematic"] is False
        # 박제 — notes_ko + meta.
        assert result["notes_ko"] == "그립 명확, 후굴 없음."
        assert result["model"] == "gemini-3.5-flash"
        assert "latency_ms" in result and isinstance(result["latency_ms"], int)
        # G4 박제 — 정상 path 는 guardrail_triggered=None.
        assert result["guardrail_triggered"] is None
        # error 키 박제 0 (정상 path).
        assert result.get("error") is None
        # call() 1회.
        assert stub.call_paths == [_video(tmp_path)]

    def test_init_uses_resolve_model_default_flash(self, tmp_path, monkeypatch) -> None:
        """GEMINI_C_MODEL_OVERRIDE 미설정 시 default = gemini-3.5-flash 박제."""
        stub = _StubCall(_ok_flags())
        _patch_call(monkeypatch, stub)
        monkeypatch.delenv("GEMINI_C_MODEL_OVERRIDE", raising=False)
        monkeypatch.delenv("GEMINI_C_MODEL", raising=False)

        scene_finder.find_scene_flags(_video(tmp_path), is_reference=False)

        # GeminiVisionCall 인스턴스화 kwargs 박제 — model=DEFAULT_C_MODEL.
        assert stub.init_kwargs.get("model") == "gemini-3.5-flash"
        # enforce_object_guard=True 박제 (G1 정합).
        assert stub.init_kwargs.get("enforce_object_guard") is True
        # FindingFlags schema 박제.
        assert stub.init_kwargs.get("schema") is FindingFlags
        # max_output_tokens / temperature / thinking_budget 박제 (AI-SPEC §4 영역 C).
        assert stub.init_kwargs.get("max_output_tokens") == 512
        assert stub.init_kwargs.get("temperature") == 0.0
        assert stub.init_kwargs.get("thinking_budget") == 0


class TestG4Guardrail:
    """is_reference=True + occlusion_severe=True 동시 시 4 flag 폐기."""

    def test_reference_with_occlusion_triggers_guardrail(
        self, tmp_path, monkeypatch
    ) -> None:
        # Gemini 가 잘못 occlusion_severe=True 박는 경우 — 정은지 영상이면 폐기.
        stub = _StubCall(
            _ok_flags(
                grip_visible=True,
                backbend_present=True,
                occlusion_severe=True,  # G4 trigger
                camera_angle_problematic=True,
            )
        )
        _patch_call(monkeypatch, stub)

        result = scene_finder.find_scene_flags(_video(tmp_path), is_reference=True)

        assert result is not None
        # G4 박제 — 4 flag 전부 False 로 폐기.
        assert result["grip_visible"] is False
        assert result["backbend_present"] is False
        assert result["occlusion_severe"] is False
        assert result["camera_angle_problematic"] is False
        # guardrail_triggered 박힘.
        assert result["guardrail_triggered"] == "G4_reference_occlusion_fp"
        # model/meta 는 박혀있어야 (audit).
        assert result["model"] == "gemini-3.5-flash"

    def test_reference_without_occlusion_passes_through(
        self, tmp_path, monkeypatch
    ) -> None:
        """is_reference=True 이지만 occlusion_severe=False → G4 미발동, flag 그대로."""
        stub = _StubCall(
            _ok_flags(
                grip_visible=True,
                backbend_present=True,
                occlusion_severe=False,
                camera_angle_problematic=False,
            )
        )
        _patch_call(monkeypatch, stub)

        result = scene_finder.find_scene_flags(_video(tmp_path), is_reference=True)

        assert result is not None
        # 그대로 박힘.
        assert result["grip_visible"] is True
        assert result["backbend_present"] is True
        assert result["occlusion_severe"] is False
        assert result["guardrail_triggered"] is None

    def test_nonreference_with_occlusion_passes_through(
        self, tmp_path, monkeypatch
    ) -> None:
        """is_reference=False + occlusion_severe=True → G4 미발동 (사용자 영상의
        실제 occlusion 신호 박힘)."""
        stub = _StubCall(
            _ok_flags(
                occlusion_severe=True,
                grip_visible=False,
            )
        )
        _patch_call(monkeypatch, stub)

        result = scene_finder.find_scene_flags(_video(tmp_path), is_reference=False)

        assert result is not None
        assert result["occlusion_severe"] is True
        assert result["guardrail_triggered"] is None


class TestGracefulFallback:
    """GeminiVisionCall.call → None 시 빈 flag dict 반환 (분석 흐름 차단 0)."""

    def test_call_none_returns_empty_flag_dict(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(result=None)
        _patch_call(monkeypatch, stub)

        result = scene_finder.find_scene_flags(_video(tmp_path), is_reference=False)

        assert result is not None
        # 4 flag 전부 False.
        assert result["grip_visible"] is False
        assert result["backbend_present"] is False
        assert result["occlusion_severe"] is False
        assert result["camera_angle_problematic"] is False
        assert result["notes_ko"] == ""
        # error 박제 — caller 가 추적 가능.
        assert result["error"] == "api_or_schema_fail"
        assert result["guardrail_triggered"] is None
        assert result["model"] == "gemini-3.5-flash"


class TestEnvOverride:
    """GEMINI_C_MODEL_OVERRIDE 박힘 → resolve_model 통과 후 Pro 승급 path."""

    def test_override_to_pro_preview(self, tmp_path, monkeypatch) -> None:
        stub = _StubCall(_ok_flags())
        _patch_call(monkeypatch, stub)
        monkeypatch.setenv("GEMINI_C_MODEL_OVERRIDE", "gemini-3.1-pro-preview")
        monkeypatch.delenv("GEMINI_C_MODEL", raising=False)

        result = scene_finder.find_scene_flags(_video(tmp_path), is_reference=False)

        assert result is not None
        assert stub.init_kwargs.get("model") == "gemini-3.1-pro-preview"
        assert result["model"] == "gemini-3.1-pro-preview"

    def test_gemini_c_model_alias_env(self, tmp_path, monkeypatch) -> None:
        """`GEMINI_C_MODEL` 도 박제 alias (override 미설정 시 fallback)."""
        stub = _StubCall(_ok_flags())
        _patch_call(monkeypatch, stub)
        monkeypatch.delenv("GEMINI_C_MODEL_OVERRIDE", raising=False)
        monkeypatch.setenv("GEMINI_C_MODEL", "gemini-3.1-pro-preview")

        scene_finder.find_scene_flags(_video(tmp_path), is_reference=False)

        assert stub.init_kwargs.get("model") == "gemini-3.1-pro-preview"

    def test_disallowed_model_raises_via_resolve(
        self, tmp_path, monkeypatch
    ) -> None:
        """ALLOWED_MODELS 박제 외 (예: gemini-2.5-flash) → resolve_model 가 ValueError.

        graceful X — caller 가 가짜 model 박힌 채 호출하면 안 되므로 hard fail.
        """
        stub = _StubCall(_ok_flags())
        _patch_call(monkeypatch, stub)
        monkeypatch.setenv("GEMINI_C_MODEL_OVERRIDE", "gemini-2.5-flash")

        with pytest.raises(ValueError, match="ALLOWED_MODELS"):
            scene_finder.find_scene_flags(_video(tmp_path), is_reference=False)


class TestFirestoreAdminGeminiCKwarg:
    """firestore_admin.complete_analysis 가 gemini_c kwarg 박제 정합."""

    def test_complete_analysis_accepts_gemini_c_kwarg(self, monkeypatch) -> None:
        """gemini_c=dict 전달 시 Firestore set 의 payload 에 `geminiC` 박힘."""
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _FakeDoc:
            def set(self, payload, merge=True):  # noqa: D401
                captured["payload"] = payload
                captured["merge"] = merge

        def _fake_doc(_path: str) -> _FakeDoc:
            return _FakeDoc()

        monkeypatch.setattr(firestore_admin, "_doc", _fake_doc)

        gemini_c_payload = {
            "grip_visible": True,
            "backbend_present": False,
            "occlusion_severe": False,
            "camera_angle_problematic": False,
            "notes_ko": "정상",
            "model": "gemini-3.5-flash",
            "tokens_used": 120,
            "latency_ms": 2400,
            "guardrail_triggered": None,
        }

        firestore_admin.complete_analysis(
            "uid-x",
            "an-x",
            result={"overall": 80},
            gemini_c=gemini_c_payload,
        )

        payload = captured["payload"]
        assert "geminiC" in payload
        # flat object 박제 — nested array 0.
        assert payload["geminiC"] == gemini_c_payload

    def test_complete_analysis_gemini_c_none_omits_field(self, monkeypatch) -> None:
        """gemini_c=None 시 Firestore payload 에 geminiC 박힘 X (불필요한 None 박제 차단)."""
        from sunity_shared import firestore_admin

        captured: dict[str, Any] = {}

        class _FakeDoc:
            def set(self, payload, merge=True):  # noqa: D401
                captured["payload"] = payload

        monkeypatch.setattr(firestore_admin, "_doc", lambda _p: _FakeDoc())

        firestore_admin.complete_analysis(
            "uid-x",
            "an-x",
            result={"overall": 80},
            gemini_c=None,
        )

        assert "geminiC" not in captured["payload"]
