"""moment_dimensions 단위 테스트 (Plan 01-13 T-2).

검증:
  · measure_moment_angles — 8 joints 만, derive joint 거부, frame 범위 가드, NaN 거부.
  · compute_criteria_gap — gap / beyond_tolerance / deduction / minimum_met / score 정확성.
  · score_moment — line/angle 차원 계산, minimum_failures 누적, 빈 criteria 대응.

모든 테스트는 numpy 만 의존 (mmpose / torch / google.generativeai / boto3 미import).
"""

from __future__ import annotations

import numpy as np
import pytest

from sunity_shared.analysis.skeleton import JOINT_KEYS
from sunity_shared.judging import (
    CriteriaGap,
    GeometricCriterion,
    compute_criteria_gap,
    measure_moment_angles,
    score_moment,
)


def _make_criterion(
    joint_key: str = "left_knee",
    angle_target: float = 180.0,
    tolerance_full: float = 20.0,
    deduction_per_step: float = 0.2,
    minimum_requirement: float = 130.0,
) -> GeometricCriterion:
    """IPSF invert hold default — 변경 시 source_ref 갱신 필요."""
    return GeometricCriterion(
        motion="ref-invert",
        moment_key="hold",
        joint_key=joint_key,
        angle_target=angle_target,
        tolerance_full=tolerance_full,
        deduction_per_step=deduction_per_step,
        minimum_requirement=minimum_requirement,
        source_ref="IPSF Code of Points 2024 §4.2.1",
    )


# ─────────────────── measure_moment_angles ───────────────────


class TestMeasureMomentAngles:
    def test_basic_8_joints(self) -> None:
        # T=10 프레임, J=8 관절. frame=5 의 모든 관절 = 180.0
        angles = np.full((10, len(JOINT_KEYS)), 180.0)
        out = measure_moment_angles(angles, frame_index=5)
        assert len(out) == 8
        assert set(out.keys()) == set(JOINT_KEYS)
        for v in out.values():
            assert v == 180.0

    def test_subset_joint_keys(self) -> None:
        angles = np.full((10, len(JOINT_KEYS)), 180.0)
        angles[5, JOINT_KEYS.index("left_knee")] = 175.0
        out = measure_moment_angles(
            angles, frame_index=5, joint_keys=("left_knee", "right_knee")
        )
        assert out == {"left_knee": 175.0, "right_knee": 180.0}

    def test_derive_joint_rejected(self) -> None:
        """hip/spine/thorax/neck_nose/head 등 derive joint 절대 금지 (Plan 12 (d) 회피)."""
        angles = np.full((10, len(JOINT_KEYS)), 180.0)
        with pytest.raises(ValueError, match="derive joint"):
            measure_moment_angles(angles, frame_index=5, joint_keys=("hip",))

    def test_frame_out_of_range_rejected(self) -> None:
        angles = np.full((10, len(JOINT_KEYS)), 180.0)
        with pytest.raises(ValueError, match="frame_index 범위 위반"):
            measure_moment_angles(angles, frame_index=10)
        with pytest.raises(ValueError, match="frame_index 범위 위반"):
            measure_moment_angles(angles, frame_index=-1)

    def test_nan_rejected(self) -> None:
        angles = np.full((10, len(JOINT_KEYS)), 180.0)
        angles[5, JOINT_KEYS.index("left_knee")] = float("nan")
        with pytest.raises(ValueError, match="NaN"):
            measure_moment_angles(angles, frame_index=5, joint_keys=("left_knee",))

    def test_inf_rejected(self) -> None:
        angles = np.full((10, len(JOINT_KEYS)), 180.0)
        angles[5, JOINT_KEYS.index("left_knee")] = float("inf")
        with pytest.raises(ValueError, match="NaN"):
            measure_moment_angles(angles, frame_index=5, joint_keys=("left_knee",))

    def test_wrong_shape_rejected(self) -> None:
        wrong = np.full((10, 17), 180.0)
        with pytest.raises(ValueError, match="형상"):
            measure_moment_angles(wrong, frame_index=5)


# ─────────────────── compute_criteria_gap ───────────────────


class TestComputeCriteriaGap:
    def test_perfect_match_zero_gap_max_score(self) -> None:
        c = _make_criterion(angle_target=180.0, tolerance_full=20.0)
        gap = compute_criteria_gap(180.0, c)
        assert gap.gap == 0.0
        assert gap.beyond_tolerance == 0.0
        assert gap.deduction == 0.0
        assert gap.minimum_met is True
        assert gap.score == 100

    def test_within_tolerance_no_beyond(self) -> None:
        c = _make_criterion(angle_target=180.0, tolerance_full=20.0)
        gap = compute_criteria_gap(170.0, c)  # 10 deg off, within 20
        assert gap.gap == 10.0
        assert gap.beyond_tolerance == 0.0
        assert gap.deduction == 0.0
        assert gap.minimum_met is True

    def test_beyond_tolerance_deduction_positive(self) -> None:
        c = _make_criterion(
            angle_target=180.0, tolerance_full=20.0, deduction_per_step=0.2
        )
        gap = compute_criteria_gap(150.0, c)  # 30 deg off, 10 beyond
        assert gap.gap == 30.0
        assert gap.beyond_tolerance == 10.0
        assert gap.deduction == pytest.approx(2.0)  # 10 * 0.2
        # minimum_requirement default 130.0 — 150 >= 130 → met
        assert gap.minimum_met is True

    def test_minimum_failure(self) -> None:
        c = _make_criterion(
            angle_target=180.0, tolerance_full=20.0, minimum_requirement=160.0
        )
        gap = compute_criteria_gap(150.0, c)
        assert gap.minimum_met is False

    def test_returns_criteria_gap_dataclass(self) -> None:
        c = _make_criterion()
        gap = compute_criteria_gap(170.0, c)
        assert isinstance(gap, CriteriaGap)
        assert gap.joint_key == "left_knee"
        assert gap.angle_target == 180.0

    def test_nan_measured_rejected(self) -> None:
        c = _make_criterion()
        with pytest.raises(ValueError, match="NaN"):
            compute_criteria_gap(float("nan"), c)


# ─────────────────── score_moment ───────────────────


class TestScoreMoment:
    def test_basic_all_extension(self) -> None:
        """3 entries all 180° target, measured 180 (perfect) → line/angle 모두 max."""
        criteria = [
            _make_criterion(joint_key="left_knee"),
            _make_criterion(joint_key="right_knee"),
            _make_criterion(joint_key="left_shoulder"),
        ]
        measured = {"left_knee": 180.0, "right_knee": 180.0, "left_shoulder": 180.0}
        result = score_moment(measured, criteria)
        assert result["line"] == 100
        assert result["angle"] == 100
        assert result["criteria_count"] == 3
        assert result["minimum_failures"] == []
        assert len(result["per_joint"]) == 3

    def test_minimum_failure_accumulates(self) -> None:
        criteria = [
            _make_criterion(joint_key="left_knee", minimum_requirement=160.0),
            _make_criterion(joint_key="right_knee", minimum_requirement=160.0),
        ]
        measured = {"left_knee": 180.0, "right_knee": 100.0}
        result = score_moment(measured, criteria)
        assert result["minimum_failures"] == ["right_knee"]

    def test_empty_criteria_returns_none(self) -> None:
        """빈 criteria → line/angle 모두 None, per_joint 빈 list (Plan 15 ref-climb 케이스)."""
        result = score_moment({}, [])
        assert result["line"] is None
        assert result["angle"] is None
        assert result["per_joint"] == []
        assert result["criteria_count"] == 0
        assert result["minimum_failures"] == []

    def test_missing_measured_joint_rejected(self) -> None:
        """criterion 의 joint_key 가 measured dict 에 없으면 ValueError (silent skip 금지)."""
        criteria = [_make_criterion(joint_key="left_knee")]
        with pytest.raises(ValueError, match="측정 각도가 측정 dict 에 없음"):
            score_moment({}, criteria)

    def test_non_180_target_not_in_line(self) -> None:
        """angle_target != 180° entry 는 line 차원에 기여하지 않음 (IPSF 신전 한정)."""
        # 90° target only — line 은 None, angle 은 산출
        criteria = [
            _make_criterion(joint_key="left_elbow", angle_target=90.0),
        ]
        measured = {"left_elbow": 90.0}
        result = score_moment(measured, criteria)
        assert result["line"] is None  # 180° entry 0건
        assert result["angle"] == 100

    def test_mixed_180_and_other_target(self) -> None:
        """180° entry 와 다른 target entry 가 혼합 시 line 은 180° 평균만, angle 은 전체 평균."""
        criteria = [
            _make_criterion(joint_key="left_knee", angle_target=180.0),
            _make_criterion(joint_key="left_elbow", angle_target=90.0),
        ]
        measured = {"left_knee": 180.0, "left_elbow": 90.0}
        result = score_moment(measured, criteria)
        # line: left_knee (180°) only, deficit 0 → 100
        assert result["line"] == 100
        # angle: 평균 갭 0 → 100
        assert result["angle"] == 100

    def test_deduction_propagates_to_per_joint(self) -> None:
        c = _make_criterion(
            joint_key="left_knee",
            angle_target=180.0,
            tolerance_full=20.0,
            deduction_per_step=0.2,
        )
        measured = {"left_knee": 150.0}  # 30 off, 10 beyond
        result = score_moment(measured, [c])
        assert result["per_joint"][0].deduction == pytest.approx(2.0)
