"""Phase 17 Wave 0 — Gemini Vision 응답 객관성 가드 (G1 hard fail).

박제 정신:
  · [[analysis-objectivity-no-human-scores]] 헌장 — Gemini 응답이 사람 점수/좌표/판단을
    출력하면 graceful 폴백 X, 반드시 ValueError raise. 시스템 의미 자체 (객관 분석) 를 지킴.
  · AI-SPEC §6 G1 "객관성 reject regex (hard fail)" 박제 패턴 그대로.
  · sunity_shared.judging.gemini_moment_extractor._enforce_no_coordinate_or_score 와
    별도 가드 — 4 영역 plan 의 단일 진입점. 기존 모듈은 Phase 5 recognizer path 박제 유지.

영역 D 좌표 우회 박제:
  · `allow_coords=True` 호출 시 좌표 패턴 (r"\\b좌표\\b|x\\s*=|y\\s*=") 만 skip.
  · 점수/사람 판단 어휘는 영역 D 도 영구 차단 — 객관성 헌장 정합.
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)


# ─────────────────── reject regex 박제 (AI-SPEC §6 G1) ───────────────────
#
# 점수 패턴 — Korean 단일 점수 ("87점", "8.5점") + 분수 ("9/10").
_SCORE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d+(\.\d+)?\s*점"),
    re.compile(r"\d+\s*/\s*\d+"),
)

# 좌표 패턴 — 영역 D 는 allow_coords=True 박제로 우회.
_COORDINATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b좌표\b"),
    re.compile(r"x\s*=", re.IGNORECASE),
    re.compile(r"y\s*=", re.IGNORECASE),
)

# 사람 판단 어휘 — 영구 차단 (allow_coords 와 무관).
_JUDGMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"잘했다"),
    re.compile(r"훌륭하다"),
    re.compile(r"훌륭"),
    re.compile(r"완벽"),
)


def _enforce_no_reject_patterns(
    text: str,
    *,
    context: str,
    allow_coords: bool = False,
) -> None:
    """Gemini 응답이 점수/좌표/판단 어휘를 포함하는지 정규식 가드.

    매치 시 graceful return X — 반드시 ValueError raise. caller 가 hard fail 로 인지.

    Args:
        text: Gemini raw response text. 빈 문자열은 noop (별도 path 에서 처리).
        context: 호출 context (모델명 / 영역명 등). 예외 메시지에 박제.
        allow_coords: True 시 좌표 패턴 skip (영역 D 전용 — KeypointRefinement 박제).
            점수/판단 어휘는 영역 D 도 영구 차단.

    Raises:
        ValueError: 점수 / (allow_coords=False 시) 좌표 / 사람 판단 어휘 매치 시.
    """
    if not text:
        # 빈 응답은 별도 path 에서 처리 (필수 필드 누락 ValueError 등).
        return

    # 점수 패턴 — 영구 차단 (allow_coords 와 무관).
    for pat in _SCORE_PATTERNS:
        m = pat.search(text)
        if m:
            raise ValueError(
                f"Gemini 응답에 점수 라벨링이 포함됨 (context={context}): "
                f"패턴='{pat.pattern}' 매치='{m.group(0)}'. "
                f"사람 점수 ground truth 영구 금지 "
                f"([[analysis-objectivity-no-human-scores]] 헌장)."
            )

    # 좌표 패턴 — 영역 D 는 우회.
    if not allow_coords:
        for pat in _COORDINATE_PATTERNS:
            m = pat.search(text)
            if m:
                raise ValueError(
                    f"Gemini 응답에 좌표 출력이 포함됨 (context={context}): "
                    f"패턴='{pat.pattern}' 매치='{m.group(0)}'. "
                    f"좌표 출력은 영역 D (KeypointRefinement) 만 허용 — "
                    f"allow_coords=True 박제 후 재호출."
                )

    # 사람 판단 어휘 — 영구 차단.
    for pat in _JUDGMENT_PATTERNS:
        m = pat.search(text)
        if m:
            raise ValueError(
                f"Gemini 응답에 사람 판단 어휘가 포함됨 (context={context}): "
                f"패턴='{pat.pattern}' 매치='{m.group(0)}'. "
                f"사람 점수/판단 ground truth 영구 금지 "
                f"([[analysis-objectivity-no-human-scores]] 헌장)."
            )


__all__ = ["_enforce_no_reject_patterns"]
