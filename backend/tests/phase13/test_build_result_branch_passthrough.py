"""Phase 13-B Task 2 — build_result 가 branch_info 를 build_dimension_explanation 으로
forward (HIGH-2). pipeline 이 build_result 경유이므로 pass-through 가 끊기면 분기 무효.
"""

from __future__ import annotations

from sunity_shared.analysis import assemble
from sunity_shared.analysis.assemble import MotionBranchInfo

_DIM_SCORES = {"angle": 70, "line": 70, "stability": 70}
_CMP = {"mode": "mode1"}


def _branch(copy_branch: str) -> MotionBranchInfo:
    return MotionBranchInfo(
        copyBranch=copy_branch,
        ipsfCode=None,
        officialName="X",
        angleSource="unavailable",
        angleFixtureKey=None,
        criteriaYaml=None,
        sourceNote="test",
    )


def test_build_result_forwards_branch2():
    result = assemble.build_result(
        [],
        _DIM_SCORES,
        70,
        _CMP,
        "https://example/my.mp4",
        branch_info=_branch("branch2_eunji_reference"),
    )
    explanation = result["dimensionExplanation"]
    joined = " ".join(v["baseline"] for v in explanation.values())
    assert "정은지 선수 기준" in joined
    assert "세계 심사 기준" not in joined


def test_build_result_forwards_branch1():
    result = assemble.build_result(
        [],
        _DIM_SCORES,
        70,
        _CMP,
        "https://example/my.mp4",
        branch_info=_branch("branch1_ipsf_registered"),
    )
    explanation = result["dimensionExplanation"]
    assert "IPSF 동작별 정의 각도" in explanation["angle"]["baseline"]
    assert "180°" in explanation["line"]["baseline"]


def test_build_result_backward_compatible_without_branch_info():
    # 기존 호출자(branch_info 미전달) → mode-aware baseline.
    result = assemble.build_result(
        [], _DIM_SCORES, 70, _CMP, "https://example/my.mp4"
    )
    explanation = result["dimensionExplanation"]
    assert (
        explanation["angle"]["baseline"]
        == assemble._DIMENSION_BASELINES_MODE1["angle"]
    )


def test_lookup_motion_branch_returns_dataclass():
    # 4차 MEDIUM-1 — dict 아님.
    info = assemble.lookup_motion_branch("ref-foxtop")
    assert isinstance(info, MotionBranchInfo)
    assert info.copyBranch == "branch2_eunji_reference"
