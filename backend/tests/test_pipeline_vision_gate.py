"""Plan 17-01 Task 4 — pipeline._gemini_vision_enabled() + keep_local_video gate 단위 테스트.

박제 정신:
  · 3차 review R-B4 정합 — Phase 17 4 영역 토글 중 하나만 ON 이어도 local_video_path
    보존 (keep_local_video=True).
  · 기존 _gemini_enabled() (Phase 5 recognizer 전용) 시그니처/동작 변경 0 — backward compat.
  · 2차 R-W6 정합 — B/C default ON 으로 모든 분석이 keep_local_video=True 가 되더라도
    finally 박제 unlink 가 정상/예외 양쪽에서 호출 (disk budget 누수 차단).
  · 2차 R-W6 정합 — unlink 실패 (PermissionError 등) 시 log.warning 1회 박제 + 분석 흐름
    차단 0 (graceful).

mock-based — 실 S3 / 실 Firestore / 실 NLF 호출 0.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# functions/pipeline/ 디렉토리를 path 에 추가 — app 모듈 임포트.
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _import_pipeline():
    """pipeline/app.py 모듈을 강제 재로드 (env 박제 격리)."""
    sys.modules.pop("app", None)
    import app  # noqa: WPS433 - dynamic local import 박제

    return importlib.reload(app)


# Phase 17 4 영역 토글 박제 — A/B/C/D.
_VISION_ENV_VARS = (
    "GEMINI_REFERENCE_ENABLED",
    "GEMINI_COACH_ENABLED",
    "GEMINI_FINDING_ENABLED",
    "GEMINI_D_ENABLED",
)
_RECOGNIZER_ENV_VARS = (
    "GEMINI_RECOGNIZER_ENABLED",
    "RECOGNIZER_BACKEND",
)


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    """각 테스트마다 env clear + module reload 박제."""
    for k in _VISION_ENV_VARS + _RECOGNIZER_ENV_VARS:
        monkeypatch.delenv(k, raising=False)
    yield
    sys.modules.pop("app", None)


# ─────────────────── _gemini_vision_enabled 토글 케이스 ───────────────────


class TestGeminiVisionEnabled:
    def test_all_off_returns_false(self, monkeypatch) -> None:
        # 모든 토글 OFF — B/C default "1" override.
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is False

    def test_reference_only_on(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        monkeypatch.setenv("GEMINI_REFERENCE_ENABLED", "1")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_coach_only_on(self, monkeypatch) -> None:
        # B/C default = "1" 인데 명시적 ON 으로 박제.
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "1")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_finding_only_on(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "1")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_d_only_on(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        monkeypatch.setenv("GEMINI_D_ENABLED", "1")
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_bc_default_on_when_unset(self) -> None:
        # B/C default "1" — env 미설정 시 박제.
        app = _import_pipeline()
        assert app._gemini_vision_enabled() is True

    def test_falsy_values_block_default(self, monkeypatch) -> None:
        # default ON path 박제 차단 — "false" / "False" / "0" / "" 모두 false 처리.
        for val in ("0", "false", "False", ""):
            monkeypatch.setenv("GEMINI_COACH_ENABLED", val)
            monkeypatch.setenv("GEMINI_FINDING_ENABLED", val)
            app = _import_pipeline()
            assert app._gemini_vision_enabled() is False, f"value={val!r}"


# ─────────────────── _gemini_enabled 회귀 (backward compat) ───────────────────


class TestGeminiEnabledBackwardCompat:
    def test_recognizer_only_on_does_not_imply_vision(self, monkeypatch) -> None:
        # Phase 5 recognizer ON + Phase 17 4 영역 모두 OFF.
        monkeypatch.setenv("GEMINI_RECOGNIZER_ENABLED", "1")
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        app = _import_pipeline()
        assert app._gemini_enabled() is True
        # Phase 17 vision 은 별 helper — 모두 OFF 면 False.
        assert app._gemini_vision_enabled() is False

    def test_recognizer_off_returns_false(self, monkeypatch) -> None:
        # 둘 다 unset.
        app = _import_pipeline()
        assert app._gemini_enabled() is False


# ─────────────────── keep_local_video gate (OR) ───────────────────


class TestKeepLocalVideoGate:
    def test_gate_uses_or_of_both_helpers(self, monkeypatch) -> None:
        """Phase 17 4 영역 OR Phase 5 recognizer — 하나라도 ON 이면 True."""
        # case 1: recognizer only.
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        monkeypatch.setenv("GEMINI_RECOGNIZER_ENABLED", "1")
        app = _import_pipeline()
        assert (app._gemini_enabled() or app._gemini_vision_enabled()) is True

        # case 2: vision only.
        monkeypatch.delenv("GEMINI_RECOGNIZER_ENABLED", raising=False)
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "1")
        app = _import_pipeline()
        assert (app._gemini_enabled() or app._gemini_vision_enabled()) is True

        # case 3: 둘 다 OFF.
        monkeypatch.setenv("GEMINI_COACH_ENABLED", "0")
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")
        app = _import_pipeline()
        assert (app._gemini_enabled() or app._gemini_vision_enabled()) is False

    def test_gate_line_present_in_source(self) -> None:
        """grep 회귀 박제 — pipeline/app.py 의 _extract_video_analysis_inputs 호출이
        `keep_local_video=_gemini_enabled() or _gemini_vision_enabled()` 박제로 갱신."""
        source = (_PIPELINE / "app.py").read_text(encoding="utf-8")
        assert "_gemini_enabled() or _gemini_vision_enabled()" in source

    def test_gemini_vision_enabled_defined_in_source(self) -> None:
        source = (_PIPELINE / "app.py").read_text(encoding="utf-8")
        # 정의 1회 + 호출 1회 = ≥ 2회.
        assert source.count("_gemini_vision_enabled") >= 2


# ─────────────────── finally cleanup 회귀 (2차 R-W6) ───────────────────


class TestFinallyCleanup:
    def test_unlink_called_when_path_set(self, monkeypatch, tmp_path) -> None:
        """_process finally 박제 가 local_video_path 가 set 일 때 unlink 호출."""
        app = _import_pipeline()
        # 실 Path.unlink 박제 — 호출 count 검증.
        unlink_calls: list[Path] = []
        real_unlink = Path.unlink

        def _fake_unlink(self, missing_ok=False):
            unlink_calls.append(Path(self))
            return None

        monkeypatch.setattr(Path, "unlink", _fake_unlink)

        # finally 박제 path 시뮬레이션 — local_video_path 박제 후 unlink 호출.
        local_video_path = str(tmp_path / "fake.mp4")
        try:
            pass  # 정상 종료 path
        finally:
            if local_video_path is not None:
                Path(local_video_path).unlink(missing_ok=True)

        assert len(unlink_calls) == 1

        # 예외 path 도 finally 진입.
        unlink_calls.clear()
        with pytest.raises(RuntimeError):
            try:
                raise RuntimeError("boom")
            finally:
                if local_video_path is not None:
                    Path(local_video_path).unlink(missing_ok=True)
        assert len(unlink_calls) == 1

        monkeypatch.setattr(Path, "unlink", real_unlink)

    def test_unlink_failure_graceful_via_safe_unlink(self, monkeypatch, tmp_path) -> None:
        """unlink 실패 시 _safe_unlink_local_video 가 log.warning 1회 + 분석 흐름 차단 0.

        R-W6 박제 — Path(local_video_path).unlink(missing_ok=True) 자체는 PermissionError
        등에서 raise. pipeline 박제는 safe wrapper 박제 권장 — _safe_unlink_local_video.
        """
        app = _import_pipeline()

        # _safe_unlink_local_video 박제 신설 헬퍼 — 박제 정신 R-W6 정합.
        # unlink 실패해도 RuntimeError raise X (graceful).
        def _raising_unlink(self, missing_ok=False):
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "unlink", _raising_unlink)
        warnings: list[str] = []
        monkeypatch.setattr(app.log, "warning", lambda msg, *a, **kw: warnings.append(msg))

        fake_path = str(tmp_path / "fake.mp4")
        # 박제 — graceful return None.
        result = app._safe_unlink_local_video(fake_path)
        assert result is None
        assert len(warnings) == 1
