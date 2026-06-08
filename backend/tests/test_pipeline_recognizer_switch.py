"""Plan 5-03 Task 1 — pipeline _RECOGNIZER lazy swap + env switch 박제 단위 테스트.

박제 정신:
  · D-12 (RunPod server.py 무수정 1pass) — pipeline 모듈 1점 swap 박제
  · D-16 (lazy import) — google.genai / boto3 / firebase_admin 모듈 로드 0 import
  · 박제 보존 — env 미설정 시 FallbackRecognizer 유지 (회귀 위험 최소)
  · B8 fix (2026-06-04 revision) — `_angles_from_video` 시그너처 무변경 + 별 helper
    `_angles_and_video_path_from_video` 신설 (RunPod server.py 호출처 무수정 박제)

테스트 클래스:
  · TestEnvSwitch (5) — default fallback / RECOGNIZER_BACKEND=gemini / 호환 alias / 멱등
  · TestLazyImport (2) — google.genai / firebase_admin 모듈 로드 시점 0 import
  · TestProtocolCompat (2) — FallbackRecognizer.recognize(frames=None/path) 호환
  · TestGeminiComposition (2) — cache + unregistered_hook 자동 박제 주입
  · TestB8FixSignature (2) — `_angles_from_video` 무변경 + helper 신설 박제 검증

mock 박제만 — google.genai / firebase_admin / boto3 실 호출 0.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path

import pytest


# functions/pipeline/ 디렉토리를 path 에 추가 — app 모듈 임포트.
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _import_pipeline():
    """pipeline/app.py 모듈을 강제 재로드 (global state 격리).

    sys.modules['app'] 제거 + importlib.reload 박제. 각 테스트마다 env switch
    분기를 깨끗하게 검증할 수 있도록 박제.
    """
    sys.modules.pop("app", None)
    import app  # noqa: WPS433 - dynamic local import 박제

    return importlib.reload(app)


@pytest.fixture(autouse=True)
def _reset_recognizer_module(monkeypatch):
    """각 테스트마다 module reload + env clear 박제."""
    for k in (
        "GEMINI_RECOGNIZER_ENABLED",
        "RECOGNIZER_BACKEND",
        "RUNPOD_ANALYZE_URL",
        "RUNPOD_AUTH_TOKEN",
    ):
        monkeypatch.delenv(k, raising=False)
    yield
    # 정리 — 다음 테스트 격리
    sys.modules.pop("app", None)


# ─────────────────── TestEnvSwitch (5 tests) ───────────────────


class TestEnvSwitch:
    """env switch 박제 — default fallback + Gemini opt-in + 호환 alias + 멱등."""

    def test_default_is_fallback(self):
        """env 미설정 → FallbackRecognizer instance 박제."""
        from sunity_shared.analysis.technique import FallbackRecognizer

        app = _import_pipeline()
        rec = app._ensure_recognizer()
        assert isinstance(rec, FallbackRecognizer), (
            f"default = FallbackRecognizer 박제 정합 위반: got {type(rec).__name__}"
        )

    def test_env_enables_gemini(self, monkeypatch):
        """RECOGNIZER_BACKEND=gemini → GeminiTechniqueRecognizer."""
        from sunity_shared.analysis.gemini_technique_recognizer import (
            GeminiTechniqueRecognizer,
        )

        monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
        app = _import_pipeline()
        rec = app._ensure_recognizer()
        assert isinstance(rec, GeminiTechniqueRecognizer)

    def test_env_alias_gemini_recognizer_enabled(self, monkeypatch):
        """GEMINI_RECOGNIZER_ENABLED=1 → GeminiTechniqueRecognizer (호환 alias)."""
        from sunity_shared.analysis.gemini_technique_recognizer import (
            GeminiTechniqueRecognizer,
        )

        monkeypatch.setenv("GEMINI_RECOGNIZER_ENABLED", "1")
        app = _import_pipeline()
        rec = app._ensure_recognizer()
        assert isinstance(rec, GeminiTechniqueRecognizer)

    def test_env_case_insensitive(self, monkeypatch):
        """GEMINI_RECOGNIZER_ENABLED=TRUE (case-insensitive) → GeminiTechniqueRecognizer."""
        from sunity_shared.analysis.gemini_technique_recognizer import (
            GeminiTechniqueRecognizer,
        )

        monkeypatch.setenv("GEMINI_RECOGNIZER_ENABLED", "TRUE")
        app = _import_pipeline()
        rec = app._ensure_recognizer()
        assert isinstance(rec, GeminiTechniqueRecognizer)

    def test_ensure_recognizer_idempotent(self, monkeypatch):
        """`_ensure_recognizer()` 2회 호출 = 같은 instance 박제 (lock + 더블체크)."""
        monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
        app = _import_pipeline()
        a = app._ensure_recognizer()
        b = app._ensure_recognizer()
        assert a is b, "lazy creation 멱등 박제 위반"


# ─────────────────── TestLazyImport (2 tests) ───────────────────


class TestLazyImport:
    """D-16 박제 — pipeline 모듈 import 시 무거운 의존성 0 import."""

    def test_no_gemini_module_at_pipeline_load(self):
        """pipeline 모듈 import 시 google.genai / google.generativeai 미존재 박제."""
        # 사전 정리 — 다른 테스트가 import 한 경우 정리
        for k in list(sys.modules.keys()):
            if k.startswith("google.genai") or k.startswith("google.generativeai"):
                sys.modules.pop(k, None)
        _import_pipeline()
        # pipeline 모듈 import 자체로는 Gemini SDK 가 로드되면 안 됨 (D-16)
        loaded = [
            k for k in sys.modules
            if k.startswith("google.genai") or k.startswith("google.generativeai")
        ]
        assert not loaded, (
            f"pipeline 모듈 import 시 Gemini SDK 가 로드됨 (D-16 박제 위반): {loaded}"
        )

    def test_no_firebase_admin_at_pipeline_load(self):
        """pipeline 모듈 import 시 firebase_admin 미존재 박제 (D-16)."""
        # firebase_admin 는 firestore_admin._db() 안에서 lazy — pipeline import
        # 시점엔 로드되지 않음.
        for k in list(sys.modules.keys()):
            if k.startswith("firebase_admin"):
                sys.modules.pop(k, None)
        _import_pipeline()
        loaded = [k for k in sys.modules if k.startswith("firebase_admin")]
        assert not loaded, (
            f"pipeline 모듈 import 시 firebase_admin 로드됨 (D-16 박제 위반): {loaded}"
        )


# ─────────────────── TestProtocolCompat (2 tests) ───────────────────


class TestProtocolCompat:
    """FallbackRecognizer.recognize(angles, frames=...) 호환 박제 (Protocol 정합)."""

    def test_fallback_recognize_accepts_frames_none(self):
        """FallbackRecognizer.recognize(angles, frames=None) 정상 동작 박제."""
        import numpy as np

        from sunity_shared.analysis.technique import FallbackRecognizer

        angles = np.full((10, 8), 170.0)
        rec = FallbackRecognizer()
        profile = rec.recognize(angles, frames=None)
        assert profile.name == "미상"
        assert profile.category == "unknown"

    def test_fallback_recognize_accepts_frames_path(self):
        """FallbackRecognizer.recognize(angles, frames='/tmp/x.mp4') frames ignore 박제."""
        import numpy as np

        from sunity_shared.analysis.technique import FallbackRecognizer

        angles = np.full((10, 8), 170.0)
        rec = FallbackRecognizer()
        profile = rec.recognize(angles, frames="/tmp/fake.mp4")
        # frames 인자는 ignore (FallbackRecognizer 는 angles 만 사용)
        assert profile.name == "미상"


# ─────────────────── TestGeminiComposition (2 tests) ───────────────────


class TestGeminiComposition:
    """GeminiTechniqueRecognizer 합성 시 cache + unregistered_hook 자동 박제 주입."""

    def test_gemini_recognizer_has_cache_injected(self, monkeypatch):
        """GeminiTechniqueRecognizer instance 의 cache 박제 None X."""
        from sunity_shared.analysis.technique_cache import TechniqueCache

        monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
        app = _import_pipeline()
        rec = app._ensure_recognizer()
        assert rec.cache is not None, "TechniqueCache 자동 주입 박제 위반"
        assert isinstance(rec.cache, TechniqueCache)

    def test_gemini_recognizer_has_unregistered_hook(self, monkeypatch):
        """unregistered_hook callable 박제 주입 확인 (D-09 case 3)."""
        monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
        app = _import_pipeline()
        rec = app._ensure_recognizer()
        assert callable(rec.unregistered_hook), (
            "unregistered_hook 박제 주입 위반 (callable 아님)"
        )


# ─────────────────── TestB8FixSignature (2 tests) ───────────────────


class TestB8FixSignature:
    """B8 fix (2026-06-04 revision) — `_angles_from_video` 시그너처 무변경 +
    별 helper `_angles_and_video_path_from_video` 신설 박제 검증.

    RunPod server.py D-12 무수정 박제 정합 (호출처 갱신 0).
    """

    def test_angles_from_video_signature_unchanged(self):
        """_angles_from_video(bucket, key) -> np.ndarray 시그너처 무변경 박제."""
        import numpy as np

        app = _import_pipeline()
        sig = inspect.signature(app._angles_from_video)
        params = list(sig.parameters.keys())
        assert params == ["bucket", "key"], (
            f"_angles_from_video 시그너처 변경 (B8 fix 박제 위반): params={params}"
        )
        # return type annotation = np.ndarray
        assert sig.return_annotation in (np.ndarray, "np.ndarray"), (
            f"return type = np.ndarray 박제 위반: {sig.return_annotation}"
        )

    def test_unified_extract_video_analysis_inputs_helper_exists(self):
        """Phase 6 R3 fix (Plan 06-02): `_angles_and_video_path_from_video` 폐기 →
        단일 `_extract_video_analysis_inputs(bucket, key, default_pole, *, keep_local_video=False)` 통합.
        """
        app = _import_pipeline()
        # 신설 박제
        assert hasattr(app, "_extract_video_analysis_inputs"), (
            "_extract_video_analysis_inputs (R3 fix) 미신설"
        )
        # 폐기 박제
        assert not hasattr(app, "_angles_and_video_path_from_video"), (
            "R3 fix 위반 — _angles_and_video_path_from_video 폐기 안 됨"
        )
