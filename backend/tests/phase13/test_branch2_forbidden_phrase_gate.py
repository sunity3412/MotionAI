"""Phase 13-B Task 2 — 분기2 카피 forbidden-phrase 게이트 (criteria 8).

분기2 모든 baseline 카피에 "세계 심사 기준"/"IPSF"/"180°"/"180도" 0 hit 강제.
precedent: force_pattern_copy.FORBIDDEN_PHRASES_PHASE9_REGEX.
"""

from __future__ import annotations

import re

from sunity_shared.analysis import assemble
from sunity_shared.analysis.assemble import MotionBranchInfo

_DIM_SCORES = {"angle": 70, "line": 70, "stability": 70}


def _all_branch2_baseline_text() -> str:
    # 직접 baseline 상수 + build_dimension_explanation 산출 양쪽 스캔.
    static = " ".join(assemble._DIMENSION_BASELINES_BRANCH2.values())
    branch2 = MotionBranchInfo(
        copyBranch="branch2_eunji_reference",
        ipsfCode=None,
        officialName="폭스탑",
        angleSource="eunji_measured_yaml",
        angleFixtureKey="ref-foxtop",
        criteriaYaml="ref-foxtop.yaml",
        sourceNote="test",
    )
    out = assemble.build_dimension_explanation(
        [], _DIM_SCORES, {"mode": "mode1"}, branch_info=branch2
    )
    dynamic = " ".join(v["baseline"] for v in out.values())
    return static + " " + dynamic


def test_branch2_baseline_has_no_forbidden_phrase():
    text = _all_branch2_baseline_text()
    for phrase in assemble.BRANCH2_FORBIDDEN_PHRASES:
        assert phrase not in text, f"분기2 카피에 금지 표현 '{phrase}' 발견: {text!r}"


def test_branch2_forbidden_regex_180_variants():
    text = _all_branch2_baseline_text()
    # "180" 숫자 자체가 분기2 카피에 등장하면 안 됨 (180°/180도 변형 catch).
    assert not re.search(r"180\s*(°|도)", text)
