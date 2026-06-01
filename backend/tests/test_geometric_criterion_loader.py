"""GeometricCriterion YAML 로더 단위 테스트 (Plan 01-15 T-3-2).

검증 대상:
  · 5영상 빈 템플릿 정합 (`backend/judging_data/criteria/ref-*.yaml`)
  · 누락 motion → FileNotFoundError + belle 라벨링 안내 메시지
  · 잘못된 YAML → ValueError + 어느 entry / phase 인지 명시
  · belle 가 채운 가상 fixture → load + validate PASS
  · load_grouped_criteria 의 moment_key 별 그룹화 정확
  · validate 실패 entry 에 motion/moment_key/joint_key 메시지 박제

모든 테스트는 stdlib + pytest + PyYAML 만. mmpose / torch / NLF / numpy 미import.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sunity_shared.judging import GeometricCriterion, load_criteria, load_grouped_criteria
from sunity_shared.judging.geometric_criterion import VALID_MOMENT_KEYS
from sunity_shared.judging.loader import DEFAULT_CRITERIA_DIR

# Plan 08/10/11 일관성 — sweep 5영상 그대로.
SWEEP_MOTIONS = (
    "ref-climb",
    "ref-foxtop-split",
    "ref-foxtop",
    "ref-invert",
    "ref-sideway-spin",
)


# ─────────────────── 5영상 빈 템플릿 ───────────────────


class TestLoadEmptyTemplates:
    @pytest.mark.parametrize("motion", SWEEP_MOTIONS)
    def test_empty_template_loads_to_empty_list(self, motion: str) -> None:
        """T-2 빈 템플릿 5개 다 load_criteria 성공 + criteria list 비어있음."""
        criteria = load_criteria(motion)
        assert criteria == [], (
            f"빈 템플릿이 비어있지 않음: {motion} → {criteria} "
            f"(belle 라벨링 진행 중이면 grouped 테스트로 확인)"
        )

    def test_default_dir_resolves_under_backend(self) -> None:
        """기본 DEFAULT_CRITERIA_DIR 가 backend/judging_data/criteria 로 풀림."""
        assert DEFAULT_CRITERIA_DIR.name == "criteria"
        assert DEFAULT_CRITERIA_DIR.parent.name == "judging_data"
        assert DEFAULT_CRITERIA_DIR.parent.parent.name == "backend"


# ─────────────────── 오류 경로 ───────────────────


class TestLoadErrors:
    def test_missing_motion_raises_with_guidance(self, tmp_path: Path) -> None:
        """누락 motion → FileNotFoundError 메시지에 motion 이름 + belle 라벨링 안내."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_criteria("ref-nonexistent", base_dir=tmp_path)
        msg = str(exc_info.value)
        assert "ref-nonexistent" in msg
        assert "belle 라벨링" in msg or "라벨링" in msg

    def test_malformed_yaml_top_level_not_dict(self, tmp_path: Path) -> None:
        """최상위가 dict 가 아닌 YAML → ValueError + 어느 파일인지 명시."""
        bad = tmp_path / "ref-broken.yaml"
        bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(ValueError) as exc_info:
            load_criteria("ref-broken", base_dir=tmp_path)
        assert "ref-broken.yaml" in str(exc_info.value)

    def test_missing_required_field_identifies_entry(self, tmp_path: Path) -> None:
        """entry 에 필수 키 누락 → ValueError + motion/moment 식별."""
        bad = tmp_path / "ref-missing.yaml"
        bad.write_text(
            "motion: ref-missing\n"
            "source: \"IPSF stub\"\n"
            "criteria:\n"
            "  hold_moment:\n"
            "    - joint: left_knee\n"
            "      angle_target: 180.0\n"
            "      # tolerance_full / deduction_per_step / minimum_requirement / source_ref 누락\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError) as exc_info:
            load_criteria("ref-missing", base_dir=tmp_path)
        msg = str(exc_info.value)
        assert "ref-missing" in msg
        assert "hold" in msg

    def test_validate_failure_identifies_motion_moment_joint(
        self, tmp_path: Path
    ) -> None:
        """validate() 실패 entry → 메시지에 motion / moment_key / joint_key 모두 박제."""
        bad = tmp_path / "ref-bad-source.yaml"
        bad.write_text(
            "motion: ref-bad-source\n"
            "source: \"IPSF stub\"\n"
            "criteria:\n"
            "  hold_moment:\n"
            "    - joint: right_elbow\n"
            "      angle_target: 90.0\n"
            "      tolerance_full: 20.0\n"
            "      deduction_per_step: 0.2\n"
            "      minimum_requirement: 60.0\n"
            "      source_ref: \"\"\n",  # 빈 source_ref → validate 실패
            encoding="utf-8",
        )
        with pytest.raises(ValueError) as exc_info:
            load_criteria("ref-bad-source", base_dir=tmp_path)
        msg = str(exc_info.value)
        assert "ref-bad-source" in msg
        assert "hold" in msg
        assert "right_elbow" in msg


# ─────────────────── belle 라벨링 시뮬레이션 ───────────────────


_BELLE_LABELED_INVERT_YAML = """\
motion: ref-invert
source: "IPSF Code of Points 2024 — invert family"
criteria:
  setup_moment:
    - joint: left_shoulder
      angle_target: 170.0
      tolerance_full: 20.0
      deduction_per_step: 0.2
      minimum_requirement: 120.0
      source_ref: "IPSF Code of Points 2024 §4.2.0 invert setup shoulder line"
  hold_moment:
    - joint: left_knee
      angle_target: 180.0
      tolerance_full: 20.0
      deduction_per_step: 0.2
      minimum_requirement: 130.0
      source_ref: "IPSF Code of Points 2024 §4.2.1 invert family knee extension"
    - joint: right_knee
      angle_target: 180.0
      tolerance_full: 20.0
      deduction_per_step: 0.2
      minimum_requirement: 130.0
      source_ref: "IPSF Code of Points 2024 §4.2.1 invert family knee extension"
  peak_moment: []
  release_moment: []
"""


class TestLoadBelleSimulatedFixture:
    def test_simulated_belle_data_loads_and_validates(self, tmp_path: Path) -> None:
        """belle 가 IPSF 기준으로 채운 가상 fixture → load + validate PASS."""
        (tmp_path / "ref-invert.yaml").write_text(
            _BELLE_LABELED_INVERT_YAML, encoding="utf-8"
        )
        flat = load_criteria("ref-invert", base_dir=tmp_path)
        assert len(flat) == 3
        for c in flat:
            assert isinstance(c, GeometricCriterion)
            assert c.motion == "ref-invert"
            assert c.source_ref.startswith("IPSF Code of Points")

    def test_load_grouped_criteria_returns_all_phase_keys(
        self, tmp_path: Path
    ) -> None:
        """load_grouped_criteria → 4 phase 키 모두 존재 + 정확한 분류."""
        (tmp_path / "ref-invert.yaml").write_text(
            _BELLE_LABELED_INVERT_YAML, encoding="utf-8"
        )
        grouped = load_grouped_criteria("ref-invert", base_dir=tmp_path)

        # 4 phase 키 모두 존재 (빈 list 라도)
        assert set(grouped.keys()) == set(VALID_MOMENT_KEYS)
        assert len(grouped["setup"]) == 1
        assert len(grouped["hold"]) == 2
        assert grouped["peak"] == []
        assert grouped["release"] == []
        # joint_key 정확
        hold_joints = sorted(c.joint_key for c in grouped["hold"])
        assert hold_joints == ["left_knee", "right_knee"]
        assert grouped["setup"][0].joint_key == "left_shoulder"
