"""Phase 13-B Task 2 — build_dimension_explanation copyBranch 분기 (BLOCKER-1 / HIGH-3).

- branch1_ipsf_registered → angle 차원 = "IPSF 동작별 정의 각도"(universal 180° X),
  line 차원 = "180°".
- branch2_eunji_reference → "정은지 선수 기준" + "세계 심사 기준"/"180°" 미포함.
- unknown/None → 기존 mode-aware baseline 회귀.
"""

from __future__ import annotations

from sunity_shared.analysis import assemble
from sunity_shared.analysis.assemble import MotionBranchInfo

_DIM_SCORES = {"angle": 70, "line": 70, "stability": 70}
_CMP_MODE1 = {"mode": "mode1"}
_CMP_MODE3 = {"mode": "mode3"}


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


def test_branch1_angle_baseline_is_move_specific_not_180():
    out = assemble.build_dimension_explanation(
        [], _DIM_SCORES, _CMP_MODE1, branch_info=_branch("branch1_ipsf_registered")
    )
    angle_baseline = out["angle"]["baseline"]
    assert "IPSF 동작별 정의 각도" in angle_baseline
    # angle 차원 카피에는 universal 180° 가 들어가지 않는다 (HIGH-3).
    assert "180°" not in angle_baseline


def test_branch1_line_baseline_uses_180():
    out = assemble.build_dimension_explanation(
        [], _DIM_SCORES, _CMP_MODE1, branch_info=_branch("branch1_ipsf_registered")
    )
    assert "180°" in out["line"]["baseline"]


def test_branch2_baseline_uses_eunji_no_world_standard():
    out = assemble.build_dimension_explanation(
        [], _DIM_SCORES, _CMP_MODE1, branch_info=_branch("branch2_eunji_reference")
    )
    joined = " ".join(v["baseline"] for v in out.values())
    assert "정은지 선수 기준" in joined
    assert "세계 심사 기준" not in joined
    assert "180°" not in joined
    assert "IPSF" not in joined


def test_unknown_branch_falls_back_to_mode_aware_baseline():
    # branch_info=None → 기존 mode-aware baseline 회귀.
    out_none = assemble.build_dimension_explanation(
        [], _DIM_SCORES, _CMP_MODE3, branch_info=None
    )
    assert out_none["angle"]["baseline"] == assemble._DIMENSION_BASELINES_MODE3["angle"]
    # copyBranch="unknown" 도 동일 폴백.
    out_unknown = assemble.build_dimension_explanation(
        [], _DIM_SCORES, _CMP_MODE3, branch_info=_branch("unknown")
    )
    assert (
        out_unknown["angle"]["baseline"]
        == assemble._DIMENSION_BASELINES_MODE3["angle"]
    )


def test_backward_compatible_without_branch_info_kwarg():
    # 기존 호출자(branch_info 미전달) 는 mode-aware baseline 그대로.
    out = assemble.build_dimension_explanation([], _DIM_SCORES, _CMP_MODE1)
    assert out["angle"]["baseline"] == assemble._DIMENSION_BASELINES_MODE1["angle"]
