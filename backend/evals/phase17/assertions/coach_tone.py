"""Phase 17 Plan 06C — E4 coach tone validation assertion (Promptfoo).

박제 정신:
  · AI-SPEC §5 E4 박제 — Plan 04 `coach_writer_v2._validate_tone` 의 로직 self-contained
    재구현. 부위별 용어 14개 + coach_note 3 어휘 + blocklist 박제.
  · Promptfoo external assertion — output dict (joint_key → detail/detail2) 전체를
    1 binary pass 로 산출.
"""

from __future__ import annotations

import json
import re
from typing import Any

# AI-SPEC §5 E4 + coach_writer_v2.py L49 정합 — 부위별 용어 14개.
_BODY_PART_TERMS: tuple[str, ...] = (
    "고관절",
    "후굴",
    "코어",
    "내전근",
    "외회전",
    "햄스트링",
    "견갑",
    "엉덩이 굴곡",
    "회전근개",
    "요추",
    "흉추",
    "슬괵",
    "장요근",
    "대퇴직근",
)

# coach_note 3 어휘 — "강사 보조 톤".
_COACH_NOTE_REQUIRED_WORDS: tuple[str, ...] = ("강사", "함께", "확인")

# blocklist — 단정/지시형 어휘.
_TONE_BLOCKLIST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"이렇게\s*하세요"),
    re.compile(r"잘못됐습니다"),
    re.compile(r"틀렸습니다"),
    re.compile(r"당신은"),
)


def _check_joint(joint_key: str, joint_data: dict[str, Any]) -> str | None:
    """단일 joint 의 detail2 검증 — 실패 시 reason str, 통과 시 None."""
    if not isinstance(joint_data, dict):
        return f"{joint_key}: not a dict"

    detail2 = joint_data.get("detail2", {})
    if not isinstance(detail2, dict):
        return f"{joint_key}: detail2 missing"

    causes = detail2.get("causes", [])
    if not isinstance(causes, list) or len(causes) == 0:
        return f"{joint_key}: causes 0건"

    # 각 cause.explanation 에 부위별 용어 1개 이상 박혀야 함.
    for idx, cause in enumerate(causes):
        if not isinstance(cause, dict):
            continue
        explanation = str(cause.get("explanation", ""))
        if not any(term in explanation for term in _BODY_PART_TERMS):
            return (
                f"{joint_key}: causes[{idx}] 부위별 용어 14개 중 0개 — "
                f"explanation={explanation[:60]!r}"
            )

    # coach_note 3 어휘 동시 포함.
    coach_note = str(detail2.get("coachNote", ""))
    missing = [w for w in _COACH_NOTE_REQUIRED_WORDS if w not in coach_note]
    if missing:
        return (
            f"{joint_key}: coachNote 필수 어휘 누락 ({missing!r}) — "
            f"coachNote={coach_note[:80]!r}"
        )

    # blocklist 매치 검증.
    for pat in _TONE_BLOCKLIST_PATTERNS:
        m = pat.search(coach_note)
        if m:
            return f"{joint_key}: blocklist match '{m.group(0)}'"
        for cause in causes:
            if not isinstance(cause, dict):
                continue
            m2 = pat.search(str(cause.get("explanation", "")))
            if m2:
                return (
                    f"{joint_key}: blocklist match in explanation '{m2.group(0)}'"
                )

    return None


def assert_coach_tone(output: dict[str, Any] | str) -> dict[str, Any]:
    """coach_payload 전체의 강사 보조 톤 검증.

    Args:
      output: GeminiCoachWriter 의 반환 dict (joint_key → detail / detail2).
        str (JSON 문자열) 입력 시 parse.

    Returns:
      `{"pass": bool, "score": float, "reason": str}`. 모든 joint 통과 시 pass=True.
    """
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return {"pass": False, "score": 0.0, "reason": "output JSON parse fail"}

    if not isinstance(output, dict):
        return {"pass": False, "score": 0.0, "reason": "output not a dict"}

    # `_` prefix 키 (reserved — _meta / _fallbackReason) skip.
    joint_entries = {k: v for k, v in output.items() if not k.startswith("_")}
    if not joint_entries:
        return {"pass": False, "score": 0.0, "reason": "no joint entries (empty coach)"}

    reasons: list[str] = []
    for joint_key, joint_data in joint_entries.items():
        reason = _check_joint(joint_key, joint_data)
        if reason is not None:
            reasons.append(reason)

    if reasons:
        return {
            "pass": False,
            "score": 0.0,
            "reason": "; ".join(reasons[:3]),  # 최대 3개만 박제.
        }
    return {"pass": True, "score": 1.0, "reason": "tone validation passed"}


__all__ = ["assert_coach_tone"]
