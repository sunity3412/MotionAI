"""GeometricCriterion.validate() 단위 테스트 (Plan 01-15 T-3-1).

목적: IPSF 객관성 가드 6항목 — 사람 점수 라벨링 우회나 IPSF 인용 누락이 절대
런타임을 통과하지 못함을 회귀 방지로 박제. 모든 테스트는 stdlib + pytest 만 사용
(mmpose / torch / NLF / numpy 미import).

memory: analysis-objectivity-no-human-scores, judging-baseline-ipsf-code-of-points
"""

from __future__ import annotations

import pytest

from sunity_shared.judging import GeometricCriterion
from sunity_shared.judging.geometric_criterion import VALID_MOMENT_KEYS


def _valid_invert_hold_left_knee() -> GeometricCriterion:
    """IPSF invert hold 정상 entry — 비교 baseline."""
    return GeometricCriterion(
        motion="ref-invert",
        moment_key="hold",
        joint_key="left_knee",
        angle_target=180.0,
        tolerance_full=20.0,
        deduction_per_step=0.2,
        minimum_requirement=130.0,
        source_ref="IPSF Code of Points 2024 §4.2.1 invert family knee extension",
    )


class TestValidate:
    def test_valid_invert_hold_passes(self) -> None:
        """IPSF invert hold target 180° / tolerance 20° → 예외 없음."""
        c = _valid_invert_hold_left_knee()
        c.validate()  # no raise

    def test_tolerance_zero_rejected(self) -> None:
        c = GeometricCriterion(
            motion="ref-invert",
            moment_key="hold",
            joint_key="left_knee",
            angle_target=180.0,
            tolerance_full=0.0,
            deduction_per_step=0.2,
            minimum_requirement=130.0,
            source_ref="IPSF Code of Points 2024 §4.2.1",
        )
        with pytest.raises(ValueError, match="tolerance"):
            c.validate()

    def test_tolerance_negative_rejected(self) -> None:
        c = GeometricCriterion(
            motion="ref-invert",
            moment_key="hold",
            joint_key="left_knee",
            angle_target=180.0,
            tolerance_full=-5.0,
            deduction_per_step=0.2,
            minimum_requirement=130.0,
            source_ref="IPSF Code of Points 2024 §4.2.1",
        )
        with pytest.raises(ValueError, match="tolerance"):
            c.validate()

    def test_deduction_zero_rejected(self) -> None:
        c = GeometricCriterion(
            motion="ref-invert",
            moment_key="hold",
            joint_key="left_knee",
            angle_target=180.0,
            tolerance_full=20.0,
            deduction_per_step=0.0,
            minimum_requirement=130.0,
            source_ref="IPSF Code of Points 2024 §4.2.1",
        )
        with pytest.raises(ValueError, match="deduction_per_step"):
            c.validate()

    def test_angle_target_negative_rejected(self) -> None:
        c = GeometricCriterion(
            motion="ref-invert",
            moment_key="hold",
            joint_key="left_knee",
            angle_target=-10.0,
            tolerance_full=20.0,
            deduction_per_step=0.2,
            minimum_requirement=0.0,
            source_ref="IPSF Code of Points 2024 §4.2.1",
        )
        with pytest.raises(ValueError, match="angle_target"):
            c.validate()

    def test_angle_target_over_360_rejected(self) -> None:
        c = GeometricCriterion(
            motion="ref-invert",
            moment_key="hold",
            joint_key="left_knee",
            angle_target=361.0,
            tolerance_full=20.0,
            deduction_per_step=0.2,
            minimum_requirement=130.0,
            source_ref="IPSF Code of Points 2024 §4.2.1",
        )
        with pytest.raises(ValueError, match="angle_target"):
            c.validate()

    def test_minimum_greater_than_target_rejected(self) -> None:
        c = GeometricCriterion(
            motion="ref-invert",
            moment_key="hold",
            joint_key="left_knee",
            angle_target=150.0,
            tolerance_full=20.0,
            deduction_per_step=0.2,
            minimum_requirement=180.0,  # minimum > target
            source_ref="IPSF Code of Points 2024 §4.2.1",
        )
        with pytest.raises(ValueError, match="minimum_requirement"):
            c.validate()

    @pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
    def test_source_ref_blank_rejected(self, blank: str) -> None:
        """source_ref 비어있음/공백만 → '객관 인용' 메시지로 ValueError."""
        c = GeometricCriterion(
            motion="ref-invert",
            moment_key="hold",
            joint_key="left_knee",
            angle_target=180.0,
            tolerance_full=20.0,
            deduction_per_step=0.2,
            minimum_requirement=130.0,
            source_ref=blank,
        )
        with pytest.raises(ValueError, match="객관 인용|source_ref"):
            c.validate()

    def test_invalid_moment_key_rejected(self) -> None:
        """moment_key ∉ {setup, hold, peak, release} → ValueError + 유효값 명시."""
        c = GeometricCriterion(
            motion="ref-invert",
            moment_key="invalid_moment",
            joint_key="left_knee",
            angle_target=180.0,
            tolerance_full=20.0,
            deduction_per_step=0.2,
            minimum_requirement=130.0,
            source_ref="IPSF Code of Points 2024 §4.2.1",
        )
        with pytest.raises(ValueError) as exc_info:
            c.validate()
        # 4개 valid 값이 모두 메시지에 포함
        msg = str(exc_info.value)
        for key in VALID_MOMENT_KEYS:
            assert key in msg, f"valid moment_key '{key}' missing from error: {msg}"
