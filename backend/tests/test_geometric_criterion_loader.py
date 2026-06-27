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


# ref-climb 은 IPSF "Transitions & Climbs" 카테고리 — 해부학적 각도 임계 X.
# 의도된 빈 list (NotebookLM 2026-06-01 lookup 후 정정 박제).
# 후속 plan 에서 Criteria 다중 타입 (Repetition / Flow / DeductionEvent) 신설 시 박제 대상.
ANGLE_LABELED_MOTIONS = (
    "ref-foxtop-split",
    "ref-foxtop",
    "ref-invert",
    "ref-sideway-spin",
)


class TestLoadLabeledTemplates:
    @pytest.mark.parametrize("motion", ANGLE_LABELED_MOTIONS)
    def test_labeled_template_loads_and_validates(self, motion: str) -> None:
        """1차 박제 (Plan 01-15 path (a), reference-motions.md §5 + IPSF Code of Points
        2024-2025 NotebookLM lookup 기반) 4영상 모두 load 성공 + criteria ≥ 1 + 모든
        entry validate PASS.

        - ref-invert: 5 entry (4 어깨/골반 + right_knee)
        - ref-foxtop: 6 entry (+ 양 무릎)
        - ref-foxtop-split: 6 entry (+ 양 무릎, ⚠ 좌우 추정)
        - ref-sideway-spin: 3 entry (자유 다리 측, ⚠ 좌우 추정)
        """
        criteria = load_criteria(motion)
        assert len(criteria) >= 1, (
            f"{motion} criteria 가 비어있음 — 1차 박제 후 fail. "
            f"파일 확인: backend/judging_data/criteria/{motion}.yaml"
        )
        for c in criteria:
            c.validate()  # validate 실패 시 ValueError 자동 propagate

    def test_ref_climb_intentionally_empty(self) -> None:
        """ref-climb 은 IPSF 'Transitions & Climbs' 카테고리 — 각도 임계 X (의도된 빈 list).
        해당 카테고리 평가 (반복 횟수 / 흐름 / re-grip 감점) 는 MVP scope 외.
        후속 plan 에서 Criteria 다중 타입 확장 시 박제 대상.
        """
        criteria = load_criteria("ref-climb")
        assert criteria == [], (
            "ref-climb 은 IPSF Climbs 카테고리 = 각도 임계 X 의도. "
            "비어있지 않으면 GeometricCriterion 으로 박제하면 안 됨 — Criteria 다중 타입 확장 후 박제."
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


# ─────────────────── P1 step 4: 객관 무릎 신전 5동작 ───────────────────


# P1 step4 (2026-06-27, quick-260627-afq) — IPSF element 미등재 동작에 객관 180° 무릎 신전
# (ipsf_absolute) criteria 등록. 곧아야 할 양 무릎을 EXTEND 로 박제(15-IPSF-SOURCING).
# P1 step5 (2026-06-27, pod 재-sweep 검증) — peter-pan/elbow-twist-sister/pdshape 는 correct(정타)
# form 이 무릎을 굽힘(실측, clean-residual 게이트 발화) → 무릎 신전이 결함 축 아님 → belle 결정으로
# knee EXTEND 제거(객관 angle criteria 없음, reference_relative 가 처리). power-spin/kip-up 만 유지.
# 상세 = 15-STEP5-POD-VERIFICATION-2026-06-27.md.
# P1 step5 진단(2026-06-27): kip-up도 knee EXTEND 제거 — 무릎각 신호 inverted(correct가 fault보다
# 더 굽음) + non-angle-shaped. power-spin만 유효한 straight-knee 동작으로 남음.
P1_EXTEND_KNEE_MOTIONS = (
    "ref-power-spin",
)
P1_NO_OBJECTIVE_MOTIONS = (
    "ref-kip-up",
    "ref-peter-pan",
    "ref-elbow-twist-sister",
    "ref-pdshape",
)
P1_OBJECTIVE_KNEE_MOTIONS = P1_EXTEND_KNEE_MOTIONS + P1_NO_OBJECTIVE_MOTIONS


class TestP1ObjectiveKneeExtension:
    @pytest.mark.parametrize("motion", P1_OBJECTIVE_KNEE_MOTIONS)
    def test_loads_and_validates(self, motion: str) -> None:
        """5 신규 yaml 모두 load + 모든 entry validate PASS (객관성 가드 통과).

        step5 후 peter-pan/elbow-twist/pdshape 는 criteria 비어있음(굽힘 form) — load 가
        graceful 하게 [] 반환하는 것이 정상. EXTEND 동작만 entry 존재.
        """
        criteria = load_criteria(motion)
        for c in criteria:
            c.validate()
        if motion in P1_EXTEND_KNEE_MOTIONS:
            assert len(criteria) >= 1, f"{motion} EXTEND criteria 비어있음"
        else:
            assert len(criteria) == 0, (
                f"{motion} 는 step5 에서 객관 criteria 제거됨 — 비어있어야 함: {criteria}"
            )

    @pytest.mark.parametrize("motion", P1_EXTEND_KNEE_MOTIONS)
    def test_hold_moment_has_extend_knees(self, motion: str) -> None:
        """EXTEND 동작(power-spin/kip-up) hold_moment 에 양 무릎 EXTEND + angle_target 180°."""
        grouped = load_grouped_criteria(motion)
        hold = grouped["hold"]
        extend_knees = {
            c.joint_key
            for c in hold
            if c.extension_class == "EXTEND" and c.joint_key.endswith("_knee")
        }
        assert extend_knees == {"left_knee", "right_knee"}, (
            f"{motion} EXTEND 무릎 누락: {extend_knees}"
        )
        for c in hold:
            if c.joint_key.endswith("_knee"):
                # 객관 IPSF 보편 신전기준 = 180° (정은지 측정값 아님).
                assert c.angle_target == 180.0
                # source_ref 가 IPSF 보편 신전기준 인용(element code 날조 아님).
                assert "Fully extended leg" in c.source_ref

    @pytest.mark.parametrize("motion", P1_NO_OBJECTIVE_MOTIONS)
    def test_no_objective_criteria_after_step5(self, motion: str) -> None:
        """step5 결정: 굽힘-form 동작은 객관 angle criteria 없음(EXTEND 0, 전 moment 빈 list)."""
        grouped = load_grouped_criteria(motion)
        assert all(len(grouped[k]) == 0 for k in grouped), (
            f"{motion} 는 객관 criteria 가 없어야 함(굽힘 form): {grouped}"
        )

    @pytest.mark.parametrize("motion", P1_EXTEND_KNEE_MOTIONS)
    def test_source_ref_non_empty_ipsf_cited(self, motion: str) -> None:
        """EXTEND 동작 entry source_ref 비어있지 않고 IPSF 인용(사람 점수 라벨링 금지)."""
        for c in load_criteria(motion):
            assert c.source_ref.strip()
            assert "IPSF" in c.source_ref


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
