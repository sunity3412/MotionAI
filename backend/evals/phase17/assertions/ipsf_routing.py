"""Phase 17 Plan 06C — E2/E3 IPSF routing accuracy assertion (Promptfoo).

박제 정신:
  · AI-SPEC §5 E2 (영역 A motion_name_ipsf 화이트리스트 매치) + E3 (routing_branch
    라벨과 label 일치 confusion matrix) 박제.
  · Promptfoo external assertion 박제 — output dict 의 motion_name_ipsf /
    routing_branch 가 label dict 의 expected_motion_name / expected_branch 와 일치.

호출:
  >>> assert_ipsf_routing(
  ...   output={"motion_name_ipsf": "Butterfly", "routing_branch": "branch_1_ipsf"},
  ...   expected={"expected_motion_name": "Butterfly", "expected_branch": "branch_1_ipsf"},
  ... )
  {"pass": True, "score": 1.0, "reason": "exact match"}
"""

from __future__ import annotations

import json
from typing import Any


def _normalize_name(name: str | None) -> str:
    """대소문자/공백 무시 정규화 박제."""
    if not name:
        return ""
    return name.strip().lower().replace(" ", "")


def assert_ipsf_routing(
    output: dict[str, Any] | str,
    expected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """영역 A 출력의 IPSF 명칭 + routing_branch 가 label 과 일치하는지 박제.

    Args:
      output: 영역 A 응답 dict — `{"motion_name_ipsf", "routing_branch"}`.
        str (JSON 문자열) 입력 시 parse.
      expected: label dict — `{"expected_motion_name", "expected_branch"}`.

    Returns:
      `{"pass": bool, "score": float, "reason": str}`. partial match 시 score 0.5
      (motion_name 만 또는 branch 만).
    """
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return {"pass": False, "score": 0.0, "reason": "output JSON parse fail"}

    if not isinstance(output, dict):
        return {"pass": False, "score": 0.0, "reason": "output not a dict"}

    if expected is None or not isinstance(expected, dict):
        return {"pass": False, "score": 0.0, "reason": "expected label missing"}

    actual_name = _normalize_name(output.get("motion_name_ipsf"))
    expected_name = _normalize_name(expected.get("expected_motion_name"))
    actual_branch = (output.get("routing_branch") or "").strip().lower()
    expected_branch = (expected.get("expected_branch") or "").strip().lower()

    name_match = actual_name == expected_name and expected_name != ""
    branch_match = actual_branch == expected_branch and expected_branch != ""

    if name_match and branch_match:
        return {"pass": True, "score": 1.0, "reason": "exact match"}
    if name_match or branch_match:
        return {
            "pass": False,
            "score": 0.5,
            "reason": (
                f"partial match — name_match={name_match} branch_match={branch_match} "
                f"(actual_name={actual_name!r}, expected={expected_name!r}; "
                f"actual_branch={actual_branch!r}, expected={expected_branch!r})"
            ),
        }
    return {
        "pass": False,
        "score": 0.0,
        "reason": (
            f"no match (actual_name={actual_name!r}, expected={expected_name!r}; "
            f"actual_branch={actual_branch!r}, expected={expected_branch!r})"
        ),
    }


__all__ = ["assert_ipsf_routing"]
