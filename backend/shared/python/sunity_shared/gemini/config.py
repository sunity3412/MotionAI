"""Phase 17 Wave 0 — 영역별 default model string 단일 source + ALLOWED_MODELS 화이트리스트.

박제 정신:
  · AI-SPEC §4 Model Configuration 표 1:1 정합 — DEFAULT_A/B/C/D + C_OVERRIDE.
  · 3차 review R-B1 — ALLOWED_MODELS 화이트리스트 가드 (404 silent fallback 차단).
  · [[gemini-latest-model-versions]] — `gemini-3.1-pro-preview` (suffix 박제), `gemini-3.7-flash`(2026-08-18 갱신).
    2.5 호출 / plain Pro (suffix 누락) 호출 영구 금지 — resolve_model 가 ValueError raise.
  · Plan 02/03/04/05 는 본 모듈만 import — raw model string 박제 0 (회귀 grep 가드).

영역별 model 박제 근거 (AI-SPEC §4):
  · A (reference 등록): Pro preview — 동작 분류 + 8관절 expectation 추론 깊이 박제 필요.
  · B (코칭): Pro preview — 원인 3~5개 박제 + 한국어 자연어 박제 깊이 박제 필요.
  · C (finding): Flash default (빠른 분류 충분) + Pro override (어려운 케이스 박제).
  · D (keypoint refinement): Pro preview — 영상 좌표 보정 깊이 박제 필요.

라이브러리 의존 0 — pure Python.
"""

from __future__ import annotations

from typing import Literal


# ─────────────────── 영역별 default model 박제 ───────────────────

DEFAULT_A_MODEL: str = "gemini-3.1-pro-preview"
DEFAULT_B_MODEL: str = "gemini-3.1-pro-preview"
DEFAULT_C_MODEL: str = "gemini-3.7-flash"
DEFAULT_C_MODEL_OVERRIDE: str = "gemini-3.1-pro-preview"
DEFAULT_D_MODEL: str = "gemini-3.1-pro-preview"


# ─────────────────── ALLOWED_MODELS 화이트리스트 (B1 정합) ───────────────────

ALLOWED_MODELS: frozenset[str] = frozenset(
    {
        "gemini-3.1-pro-preview",
        "gemini-3.7-flash",
    }
)
# ★2026-08-18 (quick-260818-lik): Flash 를 3.5 → 3.7 로 올리면서 **3.5 를 화이트리스트에서
# 뺐다.** 남겨두면 어딘가 놓친 하드코딩이 가드를 통과해 **조용히 옛 모델로** 돈다 — 저번
# 갱신 지시가 반영 안 된 것이 정확히 그 모양이었다. 지금은 3.5 가 resolve_model 를 타면
# ValueError 로 터진다. 되돌릴 일이 생기면 여기 한 줄을 되돌리는 것이 유일한 경로다.


# region literal — Plan 02 (A) / 03 (B) / 04 (C) / 05 (D) 정합.
_RegionLiteral = Literal["A", "B", "C", "D"]


# region → default model 매핑 박제.
_REGION_DEFAULTS: dict[str, str] = {
    "A": DEFAULT_A_MODEL,
    "B": DEFAULT_B_MODEL,
    "C": DEFAULT_C_MODEL,
    "D": DEFAULT_D_MODEL,
}


def resolve_model(region: _RegionLiteral, env_override: str | None = None) -> str:
    """region 별 model string 박제 — env 우선, 없으면 default. ALLOWED_MODELS 검증.

    Args:
        region: 'A' / 'B' / 'C' / 'D' 중 하나 (Phase 17 4 영역 박제).
        env_override: caller 가 os.environ.get('GEMINI_X_MODEL') 박제 결과. None 또는
            빈 string 박제 시 default 박제.

    Returns:
        ALLOWED_MODELS 박제 안에서 검증된 model string.

    Raises:
        ValueError: region 박제 외 / env_override 가 ALLOWED_MODELS 박제 미박제 시.
            (2.5 호출 / plain Pro (suffix 누락) / typo 박제 차단.)
    """
    if region not in _REGION_DEFAULTS:
        raise ValueError(
            f"region '{region}' 박제 외 — 유효 값 = {sorted(_REGION_DEFAULTS.keys())}. "
            f"Plan 17 4 영역 (A/B/C/D) 박제 정합."
        )

    candidate = env_override if env_override else _REGION_DEFAULTS[region]

    if candidate not in ALLOWED_MODELS:
        raise ValueError(
            f"model '{candidate}' 박제는 ALLOWED_MODELS 박제 미박제 — "
            f"허용 = {sorted(ALLOWED_MODELS)}. "
            f"[[gemini-latest-model-versions]] 박제 정합 — 2.5 호출 / plain Pro "
            f"(suffix 누락) 영구 금지."
        )

    return candidate


__all__ = [
    "ALLOWED_MODELS",
    "DEFAULT_A_MODEL",
    "DEFAULT_B_MODEL",
    "DEFAULT_C_MODEL",
    "DEFAULT_C_MODEL_OVERRIDE",
    "DEFAULT_D_MODEL",
    "resolve_model",
]
