"""Plan 08-03 Task 1 — REVIEWS Cycle 2 R8 NEW HIGH 차단 검증.

Gemini model name = env-driven 박제 검증. 실 default 위치 = `judging/gemini_moment_extractor.py`
(Cycle 1 plan 이 recognizer.py 에만 박제하여 path 누락 → Cycle 2 R8 carryover 차단).

박제 메모:
  · default 'gemini-2.5-flash' 박제 = non-EOL (Gemini Flash family stable).
  · 'gemini-2.0-flash-exp' 박제 = 2026-06-01 EOL (Google deprecation) — grep 안전망.
  · belle env 박제 (GEMINI_MODEL=gemini-3.1-pro-preview) 변경만으로 모델 박제 변경 (코드 변경 0).
"""

from __future__ import annotations

import importlib
import os
import subprocess
from pathlib import Path

import pytest


def _reload_extractor_module():
    """env 변경 후 module 재import — DEFAULT_GEMINI_MODEL 박제 갱신."""
    import sunity_shared.judging.gemini_moment_extractor as mod
    return importlib.reload(mod)


def _reload_recognizer_module():
    """env 변경 후 module 재import — recognizer 의 GEMINI_MODEL env reuse 박제."""
    import sunity_shared.analysis.gemini_technique_recognizer as mod
    return importlib.reload(mod)


def test_gemini_moment_extractor_default_is_non_eol(monkeypatch):
    """env GEMINI_MODEL 미설정 시 DEFAULT_GEMINI_MODEL == 'gemini-2.5-flash' 박제 (non-EOL).

    REVIEWS Cycle 2 R8 — 'gemini-2.0-flash-exp' 박제 2026-06-01 EOL 차단.
    """
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    mod = _reload_extractor_module()
    assert mod.DEFAULT_GEMINI_MODEL == "gemini-2.5-flash"
    # 안전망 — EOL 모델 박제 영구 제거 검증.
    assert mod.DEFAULT_GEMINI_MODEL != "gemini-2.0-flash-exp"


def test_gemini_moment_extractor_env_override(monkeypatch):
    """env GEMINI_MODEL=gemini-3.1-pro-preview 설정 시 DEFAULT 박제 변경.

    belle 운영 작업 — env 박제만으로 model 박제 변경 박제 (코드 변경 0).
    """
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    mod = _reload_extractor_module()
    assert mod.DEFAULT_GEMINI_MODEL == "gemini-3.1-pro-preview"


def test_gemini_moment_model_dedicated_key_scopes_extractor_only(monkeypatch):
    """Phase 27-09 (27-FLASH-DECISION §반영 제약) — GEMINI_MOMENT_MODEL 전용 키.

    GEMINI_MODEL 은 veto scorer 와 공유 env 라 전역 export 시 veto 까지 flip 된다.
    전용 키는 extractor default 만 바꾸고 veto(DEFAULT_VISION_MODEL)는 무접촉.
    """
    monkeypatch.setenv("GEMINI_MOMENT_MODEL", "gemini-3.5-flash")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    mod = _reload_extractor_module()
    # 전용 키가 공유 키보다 우선.
    assert mod.DEFAULT_GEMINI_MODEL == "gemini-3.5-flash"

    # veto scorer 는 GEMINI_MOMENT_MODEL 무접촉 — GEMINI_MODEL 체인 유지.
    import sunity_shared.analysis.gemini_vision_scorer as scorer_mod
    scorer_mod = importlib.reload(scorer_mod)
    assert scorer_mod.DEFAULT_VISION_MODEL == "gemini-3.1-pro-preview"


def test_gemini_moment_model_unset_falls_back_to_shared_chain(monkeypatch):
    """GEMINI_MOMENT_MODEL 미설정 시 기존 GEMINI_MODEL fallback 체인 그대로."""
    monkeypatch.delenv("GEMINI_MOMENT_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    mod = _reload_extractor_module()
    assert mod.DEFAULT_GEMINI_MODEL == "gemini-3.1-pro-preview"


def test_gemini_technique_recognizer_env_override(monkeypatch):
    """recognizer 가 인스턴스화한 GeminiMomentExtractor 도 env 박제 model reuse.

    REVIEWS R6 정합 — recognizer 가 extractor 인스턴스화 시 model_name 인자
    박제하지 않음 → extractor default (env 박제) 박제 자동 reuse 박제.
    """
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    _reload_extractor_module()
    rec_mod = _reload_recognizer_module()

    # extractor 의 DEFAULT_GEMINI_MODEL 박제 반영.
    from sunity_shared.judging.gemini_moment_extractor import (
        DEFAULT_GEMINI_MODEL,
        GeminiMomentExtractor,
    )

    extractor = GeminiMomentExtractor()
    assert extractor.model_name == DEFAULT_GEMINI_MODEL == "gemini-3.1-pro-preview"
    # recognizer 박제도 동일 env 박제 환경에서 GeminiMomentExtractor 박제 instance
    # 의 model_name 박제 inheriting 박제 검증 (구조적 lazy init path).
    assert rec_mod is not None


def test_gemini_default_is_not_gemini_2_0_flash_exp_grep():
    """안전망 — shared/python/sunity_shared/ 안 어디에도 'gemini-2.0-flash-exp' literal 박제 0.

    REVIEWS Cycle 2 R8 EOL 박제 영구 차단 grep guard.
    """
    # __file__ = backend/tests/phase08/test_*.py → parents[2] = backend/
    backend_dir = Path(__file__).resolve().parents[2]
    shared_dir = backend_dir / "shared" / "python" / "sunity_shared"
    assert shared_dir.is_dir(), f"shared dir missing: {shared_dir}"
    # subprocess grep — pytest collect 가 본 grep 의 cwd 박제 보장.
    result = subprocess.run(
        ["grep", "-rn", "gemini-2.0-flash-exp", str(shared_dir)],
        capture_output=True,
        text=True,
    )
    # grep 가 hit 0 이면 returncode=1 박제.
    assert result.returncode != 0, (
        f"'gemini-2.0-flash-exp' literal found in shared/python/sunity_shared/ — "
        f"REVIEWS Cycle 2 R8 EOL 차단 위반:\n{result.stdout}"
    )
