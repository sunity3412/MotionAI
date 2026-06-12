"""Plan 17-01 Task 3 — gemini/config.py 단일 source + ALLOWED_MODELS 화이트리스트 단위 테스트.

박제 정신:
  · AI-SPEC §4 Model Configuration 표 1:1 정합 — DEFAULT_*_MODEL 5개 상수.
  · 3차 review R-B1 정합 — ALLOWED_MODELS 화이트리스트 가드 (404 silent fallback 차단).
  · [[gemini-latest-model-versions]] — `gemini-3.1-pro-preview` (suffix 박제), `gemini-3.5-flash`.
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
        assert DEFAULT_C_MODEL == "gemini-3.5-flash"
        assert DEFAULT_C_MODEL_OVERRIDE == "gemini-3.1-pro-preview"


# ─────────────────── ALLOWED_MODELS 화이트리스트 ───────────────────


class TestAllowedModels:
    def test_allowed_models_exact_two_members(self) -> None:
        # B1 정합 — preview suffix Pro + flash 정확히 2개.
        assert ALLOWED_MODELS == frozenset({"gemini-3.1-pro-preview", "gemini-3.5-flash"})

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
        assert resolve_model("C", env_override="gemini-3.5-flash") == "gemini-3.5-flash"

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
