"""Plan 07-01 Task 2 — WR-04 fix.

Phase 6 의 6 BodyComparisonFinding emit pattern (body_normalizer.py line
945/977/1027/1056/1076/1102 박제 정합) × 3 category = 18 + 15 global keys = 33
조합 모두 _COPY_TEMPLATES 키 coverage 검증.

generic fallback path (Phase 11 LLM 풍부화 전) 진입 빈도 0 보장.

per Plan 07-01 Task 2 + .planning/phases/07-difference-classification/07-PATTERNS.md
§"test_copy_templates_resolver_coverage.py" + 07-REVIEW.md §WR-04.

Plan 02 의 `_resolve_joint_group` 와 동일 룰 (forward-compat). joint_key=None 인
4 deficit (clean_lines / extension / posture / body_placement) 은 `global` 그룹
사용 가능 — CR-02 fix 의 12 global keys 박제.
"""

from __future__ import annotations

import pytest

from sunity_shared.analysis.copy_templates import _COPY_TEMPLATES


# Phase 6 의 6 BodyComparisonFinding emit pattern — body_normalizer.py 박제 정합.
# 5 종 deficit 이 joint_key=None, knee_toe_alignment 만 joint_key="left_knee".
PHASE6_EMIT_PATTERNS = [
    ("knee_toe_alignment", "left_knee"),
    ("clean_lines", None),
    ("extension", None),
    ("posture", None),
    ("body_placement", None),
    ("pose_reliability_low", None),
]


# Plan 02 의 _resolve_joint_group 와 동일 룰 (forward-compat).
_DEFICIT_TO_GROUP_LOCAL: dict[str, str] = {
    "knee_toe_alignment": "leg",
    "extension": "torso",
    "posture": "arm",
    "body_placement": "pole_axis",
    "pose_reliability_low": "global",
}

_JOINT_TO_GROUP_LOCAL: dict[str, str] = {
    "left_elbow": "arm",
    "right_elbow": "arm",
    "left_shoulder": "arm",
    "right_shoulder": "arm",
    "left_wrist": "arm",
    "right_wrist": "arm",
    "left_hip": "leg",
    "right_hip": "leg",
    "left_knee": "leg",
    "right_knee": "leg",
    "left_ankle": "leg",
    "right_ankle": "leg",
}


def _resolve_for_test(deficit_code: str, joint_key: str | None) -> str:
    """Plan 02 의 _resolve_joint_group 동일 룰 시뮬레이션.

    - clean_lines + joint_key 있음 → _JOINT_TO_GROUP_LOCAL 매핑 (arm 또는 leg)
    - clean_lines + joint_key=None → "global" (CR-02 fix path)
    - 그 외 deficit → _DEFICIT_TO_GROUP_LOCAL.get(deficit_code, "global")
    """
    if deficit_code == "clean_lines" and joint_key:
        return _JOINT_TO_GROUP_LOCAL.get(joint_key, "arm")
    if deficit_code == "clean_lines":
        return "global"
    return _DEFICIT_TO_GROUP_LOCAL.get(deficit_code, "global")


# ── Test 1: 6 emit pattern × 3 category = 18 조합 coverage ──────────


@pytest.mark.parametrize("deficit_code,joint_key", PHASE6_EMIT_PATTERNS)
@pytest.mark.parametrize(
    "category", ["body_type_allowed", "needs_adjustment", "uncertain"]
)
def test_resolver_coverage_for_phase6_emit_shapes(
    deficit_code: str, joint_key: str | None, category: str
) -> None:
    """WR-04 fix — Phase 6 emit pattern 6 종 × 3 category = 18 조합이 모두
    _COPY_TEMPLATES 에 존재. generic fallback path 진입 0 보장."""
    group = _resolve_for_test(deficit_code, joint_key)
    key = (deficit_code, category, group)
    assert key in _COPY_TEMPLATES, (
        f"resolver group={group!r} 가 _COPY_TEMPLATES 에 없음: key={key!r}"
    )


# ── Test 2: 5 deficit (joint_key=None emit) × 3 category × "global" = 15 keys ──


@pytest.mark.parametrize(
    "deficit_code",
    [
        "clean_lines",
        "extension",
        "posture",
        "body_placement",
        "pose_reliability_low",
    ],
)
@pytest.mark.parametrize(
    "category", ["body_type_allowed", "needs_adjustment", "uncertain"]
)
def test_all_joint_key_none_deficits_have_global_keys(
    deficit_code: str, category: str
) -> None:
    """CR-02 fix — 5 deficit (joint_key=None emit 케이스) × 3 category = 15 조합
    모두 ("global") 키 존재. Plan 02 의 _resolve_joint_group 가 joint_key=None
    인 deficit 을 "global" 로 fallback 시 _COPY_TEMPLATES 키 미발견 path 진입 0."""
    assert (deficit_code, category, "global") in _COPY_TEMPLATES, (
        f"global 키 누락: ({deficit_code!r}, {category!r}, 'global')"
    )
