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
import sys
from pathlib import Path

import pytest


# 이 파일이 reload 하는 모듈들 — 끝나면 원상복구해야 한다(아래 fixture).
_RELOADED_MODULES = (
    "sunity_shared.judging.gemini_moment_extractor",
    "sunity_shared.analysis.gemini_technique_recognizer",
    "sunity_shared.analysis.gemini_vision_scorer",
)


@pytest.fixture(autouse=True)
def _restore_reloaded_modules():
    """★reload 한 모듈 네임스페이스를 테스트마다 원상복구 (2026-08-28 오염 수리).

    `importlib.reload(m)` 은 모듈 객체는 그대로 두고 **그 안의 이름을 새 객체로
    다시 바인딩**한다. 즉 reload 후 `m.VisionVetoCache` 는 **다른 클래스 객체**다.
    이 파일은 `gemini_vision_scorer` 까지 reload 하는데 복구하지 않아서,
    `tests/test_gemini_vision_scorer.py` 가 자기 모듈 로드 시점에 import 해둔
    **옛 클래스**에 monkeypatch 를 걸고 프로덕션 코드는 **새 클래스**를 쓰는
    엇갈림이 생겼다 → `_backend_get/_backend_put` 패치가 무효 → 캐시 miss.
    전체 스위트에서 캐시/결정론 테스트 6건이 이것 때문에 실패했다(단독 실행은 통과).

    복구는 sys.modules 를 되돌리는 것으로는 안 된다 — 모듈 객체 자체는 같기
    때문이다. **`__dict__` 스냅샷을 되돌려야** 원래 클래스 객체가 제자리로 온다.
    """
    saved = {
        name: dict(sys.modules[name].__dict__)
        for name in _RELOADED_MODULES
        if name in sys.modules
    }
    yield
    for name, snapshot in saved.items():
        mod = sys.modules.get(name)
        if mod is None:
            continue
        mod.__dict__.clear()
        mod.__dict__.update(snapshot)


def _reload_extractor_module():
    """env 변경 후 module 재import — DEFAULT_GEMINI_MODEL 박제 갱신."""
    import sunity_shared.judging.gemini_moment_extractor as mod
    return importlib.reload(mod)


def _reload_recognizer_module():
    """env 변경 후 module 재import — recognizer 의 GEMINI_MODEL env reuse 박제."""
    import sunity_shared.analysis.gemini_technique_recognizer as mod
    return importlib.reload(mod)


def test_gemini_moment_extractor_default_is_non_eol(monkeypatch):
    """env 미설정 시 기본 모델이 **EOL 이 아니어야** 한다 (R8 원래 의도).

    ~~`== "gemini-2.5-flash"` 문자열 박제~~ 는 2026-08-28 제거했다. 이 테스트의 의도는
    "EOL 모델로 굳지 않게 한다" 인데, 정작 **자기가 EOL 모델을 요구하고 있었다** —
    08-18 갱신으로 2.5 계열 전체가 ALLOWED_MODELS 에서 빠졌기 때문이다. 문자열을 박은
    테스트는 이렇게 의도와 반대로 뒤집힌다.

    그래서 값 대신 **불변식**을 검사한다: 화이트리스트 통과 = 살아있는 모델.
    화이트리스트에서 구 모델을 빼는 것이 EOL 차단의 단일 장치다(config.py 08-18 설계).
    """
    from sunity_shared.gemini.config import ALLOWED_MODELS

    monkeypatch.delenv("GEMINI_MOMENT_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    mod = _reload_extractor_module()
    assert mod.DEFAULT_GEMINI_MODEL in ALLOWED_MODELS, (
        f"기본 모델 {mod.DEFAULT_GEMINI_MODEL} 이 ALLOWED_MODELS 밖 — EOL/금지 모델 의심"
    )
    # 안전망 — 과거 EOL 사례가 되살아나지 않는지 (R8 원문 + 08-18 2.5 금지).
    assert not mod.DEFAULT_GEMINI_MODEL.startswith("gemini-2.")


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
    monkeypatch.setenv("GEMINI_MOMENT_MODEL", "gemini-3.7-flash")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-pro-preview")
    mod = _reload_extractor_module()
    # 전용 키가 공유 키보다 우선.
    assert mod.DEFAULT_GEMINI_MODEL == "gemini-3.7-flash"

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
