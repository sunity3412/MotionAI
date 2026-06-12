"""Phase 17 Plan 06C — E1 objectivity reject regex assertion (Promptfoo).

박제 정신:
  · AI-SPEC §6 G1 박제 — output 텍스트에 점수/좌표/판단 어휘 1건이라도 매치 시 fail.
  · 영역 D (KeypointRefinement) 만 좌표 허용 — region 인자로 분리.
  · Promptfoo external assertion 박제 — `assert_no_reject_patterns(output, region)`
    반환 dict (`{"pass": bool, "score": float, "reason": str}`).

호출:
  >>> from objectivity_reject import assert_no_reject_patterns
  >>> r = assert_no_reject_patterns("이 자세는 8.5점입니다")
  >>> r["pass"]
  False
"""

from __future__ import annotations

import re
from typing import Any

# AI-SPEC §6 G1 reject regex 박제 — sunity_shared.gemini.guardrails 와 동일 패턴.
# 본 모듈은 Promptfoo eval (sunity_shared layer 미가용 — 별도 venv) 용 self-contained.

_SCORE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d+(\.\d+)?\s*점"),
    re.compile(r"\d+\s*/\s*\d+"),
)

_COORDINATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b좌표\b"),
    re.compile(r"x\s*=", re.IGNORECASE),
    re.compile(r"y\s*=", re.IGNORECASE),
)

_JUDGMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"잘했다"),
    re.compile(r"훌륭하다"),
    re.compile(r"훌륭"),
    re.compile(r"완벽"),
)


def assert_no_reject_patterns(
    output: str,
    region: str = "B",
) -> dict[str, Any]:
    """output 텍스트의 객관성 검증 — fail 1건이라도 발견 시 pass=False.

    Args:
      output: Gemini 응답 raw text 또는 coach JSON dump.
      region: "A" / "B" / "C" / "D". region == "D" 시 좌표 패턴 skip (영역 D 만 좌표
        허용 — KeypointRefinement). 점수 / 판단 어휘는 모든 region 영구 차단.

    Returns:
      `{"pass": bool, "score": float (0~1), "reason": str}`.
    """
    if not output:
        return {"pass": True, "score": 1.0, "reason": "empty output (skip)"}

    # 점수 패턴 — 영구 차단.
    for pat in _SCORE_PATTERNS:
        m = pat.search(output)
        if m:
            return {
                "pass": False,
                "score": 0.0,
                "reason": f"score pattern match: '{m.group(0)}' (pattern={pat.pattern})",
            }

    # 좌표 패턴 — region D 외 차단.
    if region != "D":
        for pat in _COORDINATE_PATTERNS:
            m = pat.search(output)
            if m:
                return {
                    "pass": False,
                    "score": 0.0,
                    "reason": (
                        f"coordinate pattern match: '{m.group(0)}' (region={region}, "
                        f"pattern={pat.pattern})"
                    ),
                }

    # 판단 어휘 — 영구 차단.
    for pat in _JUDGMENT_PATTERNS:
        m = pat.search(output)
        if m:
            return {
                "pass": False,
                "score": 0.0,
                "reason": (
                    f"judgment pattern match: '{m.group(0)}' (pattern={pat.pattern})"
                ),
            }

    return {"pass": True, "score": 1.0, "reason": "no reject patterns"}


__all__ = ["assert_no_reject_patterns"]
