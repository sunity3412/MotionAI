"""Plan 17-01 Task 3 — gemini/config.py 단일 source + ALLOWED_MODELS 화이트리스트 단위 테스트.

박제 정신:
  · AI-SPEC §4 Model Configuration 표 1:1 정합 — DEFAULT_*_MODEL 5개 상수.
  · 3차 review R-B1 정합 — ALLOWED_MODELS 화이트리스트 가드 (404 silent fallback 차단).
  · [[gemini-latest-model-versions]] — `gemini-3.1-pro-preview` (suffix 박제), `gemini-3.7-flash`.
    2.5 호출 / plain Pro 호출 영구 금지 — resolve_model 가 ValueError raise.

mock 불필요 — pure Python 함수.
"""

from __future__ import annotations

import pytest

from sunity_shared.gemini import (
    ALLOWED_MODELS,
    DEFAULT_A_MODEL,
    DEFAULT_B_MODEL,
    DEFAULT_C_MODEL,
    DEFAULT_C_MODEL_OVERRIDE,
    DEFAULT_D_MODEL,
    resolve_model,
)


# ─────────────────── DEFAULT_* 상수 박제 회귀 ───────────────────


class TestDefaultModelConstants:
    def test_default_a_b_d_are_pro_preview(self) -> None:
        # 영역 A / B / D — 객관 분류 + 깊은 추론 박제 = Pro preview.
        assert DEFAULT_A_MODEL == "gemini-3.1-pro-preview"
        assert DEFAULT_B_MODEL == "gemini-3.1-pro-preview"
        assert DEFAULT_D_MODEL == "gemini-3.1-pro-preview"

    def test_default_c_is_flash_with_pro_override(self) -> None:
        # 영역 C — finding 인식은 빠른 분류 = Flash default,
        # 어려운 케이스 override 시 Pro 박제.
        assert DEFAULT_C_MODEL == "gemini-3.7-flash"
        assert DEFAULT_C_MODEL_OVERRIDE == "gemini-3.1-pro-preview"


# ─────────────────── ALLOWED_MODELS 화이트리스트 ───────────────────


class TestAllowedModels:
    def test_allowed_models_exact_two_members(self) -> None:
        # B1 정합 — preview suffix Pro + flash 정확히 2개.
        assert ALLOWED_MODELS == frozenset({"gemini-3.1-pro-preview", "gemini-3.7-flash"})

    def test_allowed_models_is_frozenset(self) -> None:
        # 박제 정신 — 런타임 mutation 차단.
        assert isinstance(ALLOWED_MODELS, frozenset)


# ─────────────────── resolve_model ───────────────────


class TestResolveModel:
    def test_region_a_returns_default(self) -> None:
        assert resolve_model("A") == DEFAULT_A_MODEL

    def test_region_b_returns_default(self) -> None:
        assert resolve_model("B") == DEFAULT_B_MODEL

    def test_region_c_default_is_flash(self) -> None:
        assert resolve_model("C") == DEFAULT_C_MODEL

    def test_region_d_returns_default(self) -> None:
        assert resolve_model("D") == DEFAULT_D_MODEL

    def test_env_override_flash_allowed(self) -> None:
        # C override 박제 패턴 — env 박제 시 Flash → Flash (whitelist 통과).
        assert resolve_model("C", env_override="gemini-3.1-pro-preview") == "gemini-3.1-pro-preview"

    def test_c_override_rejects_retired_flash(self):
        """★quick-260818-lik — 은퇴한 gemini-3.5-flash 는 이제 조용히 통과하면 안 된다.

        화이트리스트에 남겨두면 어딘가 놓친 하드코딩이 가드를 통과해 옛 모델로 계속
        돌고, 모델 갱신 지시가 무효가 된다(실제로 그랬다). 여기서 터져야 한다.
        """
        import pytest

        with pytest.raises(ValueError):
            resolve_model("C", env_override="gemini-3.5-flash")

    def test_env_override_pro_preview_allowed(self) -> None:
        assert (
            resolve_model("C", env_override="gemini-3.1-pro-preview")
            == "gemini-3.1-pro-preview"
        )

    def test_deprecated_25_blocked(self) -> None:
        # [[gemini-latest-model-versions]] — 2.5 영구 금지.
        with pytest.raises(ValueError, match="ALLOWED_MODELS"):
            resolve_model("A", env_override="gemini-2.5-pro")

    def test_plain_pro_without_preview_blocked(self) -> None:
        # B1 회귀 — plain `gemini-3.1-pro` 는 404 silent fallback 박제 차단.
        with pytest.raises(ValueError, match="ALLOWED_MODELS"):
            resolve_model("A", env_override="gemini-3.1-pro")

    def test_invalid_region_blocked(self) -> None:
        with pytest.raises(ValueError, match="region"):
            resolve_model("X")  # type: ignore[arg-type]

    def test_empty_env_override_falls_back_to_default(self) -> None:
        # 빈 string env 박제 → default 박제 정합 (Plan 02~05 의 env 미설정 path).
        assert resolve_model("A", env_override="") == DEFAULT_A_MODEL

    def test_none_env_override_returns_default(self) -> None:
        assert resolve_model("B", env_override=None) == DEFAULT_B_MODEL


# ─────────────────── lazy __init__ 회귀 (quick-260821-umc) ───────────────────


class TestPackageInitIsLazy:
    def test_config_import_does_not_pull_client(self) -> None:
        """pure 소비자(.config 만)는 google-genai 없는 venv 에서도 살아야 한다.

        08-18 중앙 config 도입(359b9de5) 후 패키지 __init__ 의 eager `.client` import 가
        `from google import genai` 를 무조건 끌고 와, --skip-judge 게이트 하네스가
        ab_venv_cu129(genai 미설치)에서 ImportError 로 죽었다. 이 테스트는 fresh
        인터프리터에서 .config import 가 .client 를 안 끌고 오는지 박제한다.
        """
        import os
        import subprocess
        import sys
        from pathlib import Path

        import sunity_shared

        pkg_root = str(Path(sunity_shared.__file__).resolve().parent.parent)
        env = dict(os.environ)
        env["PYTHONPATH"] = pkg_root + os.pathsep + env.get("PYTHONPATH", "")
        code = (
            "import sys\n"
            "import sunity_shared.gemini.config\n"
            "assert 'sunity_shared.gemini.client' not in sys.modules, 'client eager import'\n"
            "assert 'google.genai' not in sys.modules, 'genai eager import'\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        assert result.returncode == 0, result.stderr
