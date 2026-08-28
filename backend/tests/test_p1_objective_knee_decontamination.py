"""P1 step 4 (quick-260627-afq) — 객관 무릎 신전 채점 de-contamination (pod-free).

이 작업의 핵심 증거(pod 불필요, 순수 결정적):
  · 곧은 무릎(정은지 측정값과 달라도) → 무릎 감점 ~0 (de-contamination).
  · 굽은 무릎 → leg_extension(ipsf_absolute) 감점 + 그 무릎의 reference_relative
    (angle_vs_reference__{knee}) cross-exclusion(double-count 0).

엔진 코드 변경 0 — yaml(EXTEND 무릎) + 등록만으로 기존 배선(24-07 cross-exclusion +
profile-gated extension_deviation)이 객관 채점을 켠다는 걸 구조적으로 단언한다.
특정 점수 밴드는 단언하지 않는다(구조적 단언만, 의미있는 테스트만).

검증 레이어:
  (A) dimensions.extension_deviation — EXTEND 무릎 profile 에서 곧음/굽음이 deficit 을 가른다.
  (B) deduction_engine.tally — 엔진-stage cross-exclusion(leg_extension 활성 →
      angle_vs_reference__{knee} discard).
  (C) pipeline._build_deduction_measured_deviations — seed-stage cross-exclusion(builder 가
      expects_extension 무릎의 reference_relative md 자체를 차단; 비-EXTEND 관절은 유지).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from sunity_shared.analysis import deduction_engine, dimensions
from sunity_shared.analysis.skeleton import JOINT_KEYS
from sunity_shared.analysis.technique import (
    JOINT_BENT_OK,
    JOINT_EXTEND,
    TechniqueProfile,
)
from sunity_shared.judging.loader import load_grouped_criteria

_LEFT_KNEE = JOINT_KEYS.index("left_knee")
_RIGHT_KNEE = JOINT_KEYS.index("right_knee")
_LEFT_HIP = JOINT_KEYS.index("left_hip")


# ★무릎 EXTEND 를 실제로 등재한 동작 (2026-08-28 수리).
#
# 이 파일은 원래 "ref-kip-up" 으로 EXTEND 무릎 채점을 검증했는데, 2026-06-27 Pod
# 진단에서 **kip-up 의 무릎각 신호가 역전**(정타 min 149° vs fault min 161° — 정타가
# 더 굽음)이라 어떤 window 로도 변별 불가로 판명됐다. belle 원칙("굽힘 form 엔
# 신전기준 강요 금지")에 따라 ref-kip-up.yaml 에서 knee EXTEND 가 **의도적으로
# 제거**됐고(yaml 주석에 근거 박제), 테스트만 옛 상태를 요구한 채 남아 실패해 왔다.
#
# 검증 대상은 "특정 동작이 무릎 EXTEND 를 갖는다"가 아니라 **"EXTEND 로 등재된
# 무릎이 곧음/굽음으로 객관 채점되고, reference-relative 오염이 차단된다"** 는
# 메커니즘이다. 그래서 그 메커니즘이 실제로 걸려 있는 동작으로 옮긴다.
# (yaml 전수 실측: EXTEND 무릎을 가진 동작은 ref-power-spin 뿐 — 나머지는 BENT_OK)
_EXTEND_KNEE_MOTION = "ref-power-spin"


def _profile_from_yaml(motion: str) -> TechniqueProfile:
    """recognizer._build_profile 와 동일 규칙으로 yaml → EXTEND 무릎 profile 구성.

    hold_moment 의 extension_class==EXTEND 관절만 JOINT_EXTEND, 나머지 BENT_OK.
    hold_window 는 전체 범위로 박제(곧음/굽음만 보도록 — windowing drift 제거).
    """
    hold = load_grouped_criteria(motion)["hold"]
    extend_joints = {c.joint_key for c in hold if c.extension_class == "EXTEND"}
    expectations = {
        jk: (JOINT_EXTEND if jk in extend_joints else JOINT_BENT_OK) for jk in JOINT_KEYS
    }
    return TechniqueProfile(
        name=motion,
        category="recognized",
        joint_expectations=expectations,
        motion_id=motion,
    )


def _angles(knee_deg: float, other_deg: float = 150.0, frames: int = 8) -> np.ndarray:
    """(T, 8) 각도 행렬 — 양 무릎=knee_deg, 그 외=other_deg, 전 프레임 동일(window-무관)."""
    row = np.full(len(JOINT_KEYS), float(other_deg), dtype=float)
    row[_LEFT_KNEE] = knee_deg
    row[_RIGHT_KNEE] = knee_deg
    return np.tile(row, (frames, 1))


# ── (A) profile 활성: EXTEND 무릎이 곧음/굽음으로 채점된다 ─────────────────────


class TestExtendKneeProfileActivation:
    def test_yaml_marks_both_knees_extend(self) -> None:
        profile = _profile_from_yaml(_EXTEND_KNEE_MOTION)
        assert profile.expects_extension("left_knee")
        assert profile.expects_extension("right_knee")
        # 비-무릎 사지(팔꿈치)는 EXTEND 아님 — 무릎만 객관 채점 대상.
        assert not profile.expects_extension("left_elbow")

    def test_bent_knee_produces_positive_deficit(self) -> None:
        profile = _profile_from_yaml(_EXTEND_KNEE_MOTION)
        dev = dimensions.extension_deviation(_angles(knee_deg=140.0), profile)
        # 굽은 무릎 → 180-140=40° 부족분(>0). 구조적: 무릎 인덱스만 양수.
        assert dev[_LEFT_KNEE] > 0.0
        assert dev[_RIGHT_KNEE] > 0.0
        # 비-EXTEND 관절은 신전 채점 제외 → 0.
        assert dev[_LEFT_HIP] == 0.0

    def test_straight_knee_near_zero_deficit_regardless_of_reference(self) -> None:
        # 178° = 곧음. 정은지 measured 무릎(예: 137° in ref-invert)과 달라도 deficit ~0.
        profile = _profile_from_yaml(_EXTEND_KNEE_MOTION)
        dev = dimensions.extension_deviation(_angles(knee_deg=178.0), profile)
        assert dev[_LEFT_KNEE] < 5.0
        assert dev[_RIGHT_KNEE] < 5.0


# ── (B) 엔진-stage cross-exclusion: leg_extension 활성 → 무릎 reference 제외 ─────


class TestEngineCrossExclusion:
    def _tally(self, md: dict):
        return deduction_engine.tally(
            None,  # quantification (unavailable — reach substrate 없음)
            None,  # fault_context (Gemini 무지목)
            dimension_overall=100.0,
            measured_deviations=md,
            dimension_scores=None,
            baseline_kind="hip_line",
        )

    def test_bent_knee_leg_extension_excludes_reference_knee(self) -> None:
        # leg_extension(굽은 무릎 측정편차 >tol) 와 무릎 reference 편차가 동시 존재해도,
        # 엔진이 무릎 reference(angle_vs_reference__{knee})를 discard(double-count 금지).
        md = {
            "leg_extension": 40.0,
            "angle_vs_reference__left_knee": 50.0,
            "angle_vs_reference__right_knee": 50.0,
        }
        breakdown = self._tally(md)
        crits = {r.criterion for r in breakdown.records}
        assert "leg_extension" in crits  # 굽은 무릎 검출(ipsf_absolute)
        assert "angle_vs_reference__left_knee" not in crits  # cross-excluded
        assert "angle_vs_reference__right_knee" not in crits
        # leg_extension record 는 ipsf_absolute(객관 180°) 출처.
        leg = next(r for r in breakdown.records if r.criterion == "leg_extension")
        assert leg.deviation_source == "ipsf_absolute"
        assert leg.points < 0.0  # signed-negative 감점

    def test_straight_knee_no_leg_deduction(self) -> None:
        # 곧은 무릎 → leg_extension 측정편차가 tolerance(20°) 이하 → seed 안 됨 → record 0.
        md = {"leg_extension": 2.0}
        breakdown = self._tally(md)
        crits = {r.criterion for r in breakdown.records}
        assert "leg_extension" not in crits


# ── (C) seed-stage(builder) cross-exclusion + de-contamination ────────────────

_LAYER = Path(__file__).resolve().parents[1] / "shared" / "python"
_PIPELINE_DIR = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
for _p in (str(_LAYER), str(_PIPELINE_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pipeline_app = pytest.importorskip("app")


def _identity_match(frames: int):
    return SimpleNamespace(
        path=[(i, i) for i in range(frames)], start=0, end=frames
    )


class TestBuilderSeamDecontamination:
    def test_straight_knee_blocks_reference_keeps_non_extend(self) -> None:
        """곧은 학생 무릎이 정은지(reference)와 크게 달라도 무릎 reference seed 차단.

        비-EXTEND 관절(hip)의 reference 편차는 유지 — 차단이 EXTEND 무릎에 한정됨을 증명.
        """
        profile = _profile_from_yaml(_EXTEND_KNEE_MOTION)
        frames = 8
        student = _angles(knee_deg=178.0, other_deg=120.0, frames=frames)
        # 정은지: 무릎 158°(학생 178°와 20° 차이=오염원), left_hip 도 50° 차이(control).
        reference = _angles(knee_deg=158.0, other_deg=120.0, frames=frames)
        reference[:, _LEFT_HIP] = 170.0  # student hip 120 vs ref 170 → 50° 편차
        student[:, _LEFT_HIP] = 120.0

        md = pipeline_app._build_deduction_measured_deviations(
            angles=student,
            profile=profile,
            assessments=None,
            dimension_scores=None,
            quantification=None,
            reference_dtw_match=_identity_match(frames),
            reference_angles=reference,
        )
        # EXTEND 무릎: reference seed 차단(seed-stage cross-exclusion).
        assert "angle_vs_reference__left_knee" not in md
        assert "angle_vs_reference__right_knee" not in md
        # 비-EXTEND hip: reference 편차 유지(control — 차단이 blanket 아님).
        assert "angle_vs_reference__left_hip" in md
        # 곧은 무릎 → leg_extension 측정편차가 있더라도 작음(tolerance 이하).
        assert md.get("leg_extension", 0.0) < dimensions._LINE_TOL_DEG

    def test_straight_knee_yields_no_knee_deduction_in_tally(self) -> None:
        """builder→tally 전 경로: 곧은 무릎=무릎 감점 0(정은지와 달라도). de-contamination."""
        profile = _profile_from_yaml(_EXTEND_KNEE_MOTION)
        frames = 8
        student = _angles(knee_deg=178.0, other_deg=120.0, frames=frames)
        reference = _angles(knee_deg=158.0, other_deg=120.0, frames=frames)

        md = pipeline_app._build_deduction_measured_deviations(
            angles=student,
            profile=profile,
            assessments=None,
            dimension_scores=None,
            quantification=None,
            reference_dtw_match=_identity_match(frames),
            reference_angles=reference,
        )
        breakdown = deduction_engine.tally(
            None,
            None,
            dimension_overall=100.0,
            measured_deviations=md,
            dimension_scores=None,
            baseline_kind="hip_line",
        )
        crits = {r.criterion for r in breakdown.records}
        # 무릎 관련 감점 record 0 (leg_extension 도, 무릎 reference 도 없음).
        assert "leg_extension" not in crits
        assert "angle_vs_reference__left_knee" not in crits
        assert "angle_vs_reference__right_knee" not in crits

    def test_bent_knee_detected_via_builder(self) -> None:
        """굽은 학생 무릎 → builder 가 leg_extension 측정편차 방출 + tally 가 감점."""
        profile = _profile_from_yaml(_EXTEND_KNEE_MOTION)
        frames = 8
        student = _angles(knee_deg=140.0, other_deg=120.0, frames=frames)
        reference = _angles(knee_deg=178.0, other_deg=120.0, frames=frames)

        md = pipeline_app._build_deduction_measured_deviations(
            angles=student,
            profile=profile,
            assessments=None,
            dimension_scores=None,
            quantification=None,
            reference_dtw_match=_identity_match(frames),
            reference_angles=reference,
        )
        # 굽은 무릎 → leg_extension 측정편차 방출(>tolerance).
        assert md.get("leg_extension", 0.0) > dimensions._LINE_TOL_DEG
        # 무릎 reference 는 여전히 차단(EXTEND).
        assert "angle_vs_reference__left_knee" not in md
        assert "angle_vs_reference__right_knee" not in md

        breakdown = deduction_engine.tally(
            None,
            None,
            dimension_overall=100.0,
            measured_deviations=md,
            dimension_scores=None,
            baseline_kind="hip_line",
        )
        crits = {r.criterion for r in breakdown.records}
        assert "leg_extension" in crits  # 굽은 무릎 검출
