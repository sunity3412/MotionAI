"""compare_rtmw_vs_ipsf.py smoke 테스트 (Plan 01-23 Task 1).

fixture 데이터로 게이트 로직 검증. GPU/rtmlib/mmpose 의존 0.
60초 내 완료.

검증 항목:
  1. compare_to_ipsf: within_tolerance=True (갭 ≤ toleranceFull)
  2. compare_to_ipsf: within_tolerance=False (갭 > toleranceFull)
  3. phase1_ready_to_swap: 5영상 모두 within_tolerance + line/angle PASS → True
  4. phase1_ready_to_swap: 1영상 within_tolerance=False → False
  5. phase1_ready_to_swap: line_pass=False (둘 다 게이트) → False
  6. write_report: .json + .md 파일 생성
  7. smoke main with fixtures: argparse + mock PoseEngine → 보고서 생성 + exit code 0

T-23-03 정합: None / N/A 를 PASS 로 카운트하지 않는 게이트 검증.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# sys.path 보장
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from research.evaluations.compare_rtmw_vs_ipsf import (
    IpsfGapEntry,
    MotionResult,
    SweepReport,
    compare_to_ipsf,
    compute_phase1_ready_to_swap,
    write_report,
)
from sunity_shared.judging.geometric_criterion import GeometricCriterion


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_criterion(
    motion: str = "ref-invert",
    moment_key: str = "hold",
    joint_key: str = "left_knee",
    angle_target: float = 180.0,
    tolerance_full: float = 20.0,
) -> GeometricCriterion:
    return GeometricCriterion(
        motion=motion,
        moment_key=moment_key,
        joint_key=joint_key,
        angle_target=angle_target,
        tolerance_full=tolerance_full,
        deduction_per_step=0.2,
        minimum_requirement=120.0,
        source_ref="IPSF Code of Points 2024 §4.2.1 test fixture",
    )


def _make_motion_result(
    name: str = "ref-invert",
    within_tolerance: bool = True,
    line_pass: bool = True,
    angle_pass: bool = True,
) -> MotionResult:
    """테스트용 MotionResult fixture."""
    gap_val = 5.0 if within_tolerance else 30.0
    gap_entry = IpsfGapEntry(
        joint="left_knee",
        moment="hold",
        target=180.0,
        measured=175.0 if within_tolerance else 150.0,
        gap=gap_val,
        within_tolerance=within_tolerance,
    )
    return MotionResult(
        motion_name=name,
        pole_axis_vector=(0.0, 1.0, 0.0),
        pole_axis_confidence="low",
        ipsf_gaps=[gap_entry],
        line_pass=line_pass,
        angle_pass=angle_pass,
        ms_per_frame=20.0,
        rtmw_mean_score=75.0,
        lift_swap_ratio=0.0,
        within_tolerance_all=within_tolerance,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: compare_to_ipsf — within_tolerance=True
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_to_ipsf_within_tolerance(tmp_path):
    """GeometricCriterion (target=180, tolerance=20) + measured≈175 → within_tolerance=True, gap≈5."""
    # belle fixture YAML 작성 (hold_moment 에 left_knee)
    yaml_content = """
motion: ref-invert
source: "Test fixture"
criteria:
  setup_moment: []
  hold_moment:
    - joint: left_knee
      angle_target: 180.0
      tolerance_full: 20.0
      deduction_per_step: 0.2
      minimum_requirement: 120.0
      source_ref: "IPSF Code of Points 2024 §4.2.1 test"
  peak_moment: []
  release_moment: []
"""
    criteria_dir = tmp_path / "criteria"
    criteria_dir.mkdir()
    (criteria_dir / "ref-invert.yaml").write_text(yaml_content, encoding="utf-8")

    # 관절각 배열: (T=5, NUM_JOINTS) — left_knee 인덱스만 의미 있게
    from sunity_shared.analysis.skeleton import JOINT_KEYS
    T = 5
    angles = np.full((T, len(JOINT_KEYS)), 170.0)  # 모든 관절 170°로 채움
    # left_knee 를 175° 로 설정
    lk_idx = JOINT_KEYS.index("left_knee")
    angles[:, lk_idx] = 175.0

    gaps = compare_to_ipsf("ref-invert", angles, criteria_dir=criteria_dir)

    assert len(gaps) == 1, "1개 criteria entry → 1개 gap"
    g = gaps[0]
    assert g.joint == "left_knee"
    assert g.moment == "hold"
    assert g.target == 180.0
    assert abs(g.measured - 175.0) < 1.0, f"measured ≈ 175, got {g.measured}"
    assert abs(g.gap - 5.0) < 1.0, f"gap ≈ 5, got {g.gap}"
    assert g.within_tolerance is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: compare_to_ipsf — within_tolerance=False
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_to_ipsf_exceeds_tolerance(tmp_path):
    """GeometricCriterion (target=180, tolerance=20) + measured≈150 → within_tolerance=False, gap≈30."""
    yaml_content = """
motion: ref-invert
source: "Test fixture"
criteria:
  setup_moment: []
  hold_moment:
    - joint: left_knee
      angle_target: 180.0
      tolerance_full: 20.0
      deduction_per_step: 0.2
      minimum_requirement: 100.0
      source_ref: "IPSF Code of Points 2024 §4.2.1 test"
  peak_moment: []
  release_moment: []
"""
    criteria_dir = tmp_path / "criteria"
    criteria_dir.mkdir()
    (criteria_dir / "ref-invert.yaml").write_text(yaml_content, encoding="utf-8")

    from sunity_shared.analysis.skeleton import JOINT_KEYS
    T = 5
    angles = np.full((T, len(JOINT_KEYS)), 150.0)
    lk_idx = JOINT_KEYS.index("left_knee")
    angles[:, lk_idx] = 150.0

    gaps = compare_to_ipsf("ref-invert", angles, criteria_dir=criteria_dir)

    assert len(gaps) == 1
    g = gaps[0]
    assert abs(g.measured - 150.0) < 1.0
    assert abs(g.gap - 30.0) < 1.0
    assert g.within_tolerance is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: phase1_ready_to_swap — 5영상 모두 PASS → True
# ─────────────────────────────────────────────────────────────────────────────

def test_phase1_ready_to_swap_all_pass():
    """5영상 모두 within_tolerance + line/angle PASS → phase1_ready_to_swap=True."""
    motions = [
        _make_motion_result(name=f"ref-motion-{i}", within_tolerance=True, line_pass=True, angle_pass=True)
        for i in range(5)
    ]
    assert compute_phase1_ready_to_swap(motions) is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: phase1_ready_to_swap — 1영상 within_tolerance=False → False
# ─────────────────────────────────────────────────────────────────────────────

def test_phase1_ready_to_swap_partial_fail():
    """1영상 within_tolerance=False → phase1_ready_to_swap=False."""
    motions = [
        _make_motion_result(name="ref-motion-0", within_tolerance=True, line_pass=True, angle_pass=True),
        _make_motion_result(name="ref-motion-1", within_tolerance=True, line_pass=True, angle_pass=True),
        _make_motion_result(name="ref-motion-2", within_tolerance=False, line_pass=True, angle_pass=True),
        _make_motion_result(name="ref-motion-3", within_tolerance=True, line_pass=True, angle_pass=True),
        _make_motion_result(name="ref-motion-4", within_tolerance=True, line_pass=True, angle_pass=True),
    ]
    assert compute_phase1_ready_to_swap(motions) is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: phase1_ready_to_swap — 모든 ipsf PASS + 1영상 line_pass=False → False
# ─────────────────────────────────────────────────────────────────────────────

def test_phase1_ready_to_swap_line_fail():
    """모든 ipsf within_tolerance + 1영상 line_pass=False → phase1_ready_to_swap=False (둘 다 게이트)."""
    motions = [
        _make_motion_result(name="ref-motion-0", within_tolerance=True, line_pass=False, angle_pass=True),
        _make_motion_result(name="ref-motion-1", within_tolerance=True, line_pass=True, angle_pass=True),
        _make_motion_result(name="ref-motion-2", within_tolerance=True, line_pass=True, angle_pass=True),
        _make_motion_result(name="ref-motion-3", within_tolerance=True, line_pass=True, angle_pass=True),
        _make_motion_result(name="ref-motion-4", within_tolerance=True, line_pass=True, angle_pass=True),
    ]
    assert compute_phase1_ready_to_swap(motions) is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: write_report — .json + .md 파일 생성
# ─────────────────────────────────────────────────────────────────────────────

def test_report_writes_json_and_markdown(tmp_path):
    """write_report → output_dir 에 .json + .md 파일 생성."""
    motions = [_make_motion_result("ref-invert", True, True, True)]
    report = SweepReport(
        timestamp="2026-06-03T00:00:00+00:00",
        motions=motions,
        phase1_ready_to_swap=True,
    )

    output_dir = tmp_path / "reports"
    json_path, md_path = write_report(report, output_dir)

    assert json_path.exists(), f"JSON 파일 미생성: {json_path}"
    assert md_path.exists(), f"Markdown 파일 미생성: {md_path}"

    # JSON 내용 검증
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "motions" in data
    assert "summary" in data
    assert "phase1_ready_to_swap" in data["summary"]
    assert data["summary"]["phase1_ready_to_swap"] is True

    # pole_axis 블록 검증 (T-23-04)
    for motion_data in data["motions"].values():
        assert "pole_axis" in motion_data, "pole_axis 블록 필수"
        assert motion_data["pole_axis"]["axis_vector"] is not None, "axis_vector null 금지"
        assert len(motion_data["pole_axis"]["axis_vector"]) == 3
        assert motion_data["pole_axis"]["confidence"] in ("high", "low")

    # Markdown 내용 검증
    md_content = md_path.read_text(encoding="utf-8")
    assert "phase1_ready_to_swap" in md_content
    assert "RTMW vs IPSF" in md_content


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: smoke main with fixtures — mock PoseEngine 주입 → exit code 0
# ─────────────────────────────────────────────────────────────────────────────

def test_smoke_main_with_fixtures(tmp_path):
    """argparse 로 fixture 영상 (mock PoseEngine) 주입 → main() 실행 → 보고서 생성 + exit code 0."""
    from sunity_shared.analysis.skeleton import JOINT_KEYS
    from sunity_shared.analysis.pose_frame import (
        PoleAxis, PoseFrame, Keypoint3D, Keypoint3DAligned,
    )

    # 더미 영상 파일 생성 (numpy .npy — _load_video_frames 를 mock 으로 대체)
    video_path = tmp_path / "ref-invert.mp4"
    video_path.write_bytes(b"dummy")

    # 더미 PoseFrame 5개
    def _make_dummy_pose_frame(frame_index: int, pole_axis: PoleAxis) -> PoseFrame:
        kp3d = {
            name: Keypoint3D(x=0.0, y=float(i) * 0.1, z=0.0, confidence=0.9, uncertainty_proxy=0.1)
            for i, name in enumerate(JOINT_KEYS)
        }
        kp3d_aligned = {
            name: Keypoint3DAligned(x=0.0, y=float(i) * 0.1, z=0.0)
            for i, name in enumerate(JOINT_KEYS)
        }
        return PoseFrame(
            frame_index=frame_index,
            timestamp_ms=frame_index * 33,
            keypoints_3d=kp3d,
            keypoints_3d_pole_aligned=kp3d_aligned,
            pole_axis=pole_axis,
            reliability="high",
        )

    dummy_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )
    dummy_frames_list = [_make_dummy_pose_frame(i, dummy_pole) for i in range(5)]

    # 더미 frames numpy (5, 64, 64, 3)
    dummy_np_frames = np.zeros((5, 64, 64, 3), dtype=np.uint8)

    # mock: _load_video_frames, _load_pose_engine, detect_pole_axis
    from research.evaluations import compare_rtmw_vs_ipsf as mod

    mock_engine = MagicMock()
    mock_engine.estimate.return_value = dummy_frames_list

    output_dir = tmp_path / "out"

    with (
        patch.object(mod, "_load_video_frames", return_value=dummy_np_frames),
        patch.object(mod, "_load_pose_engine", return_value=mock_engine),
        patch.object(mod, "detect_pole_axis", return_value=dummy_pole),
    ):
        exit_code = mod.main([
            "--videos", str(video_path),
            "--output-dir", str(output_dir),
            "--pose-engine", "rtmw",
        ])

    assert exit_code == 0, f"main() exit code != 0: {exit_code}"

    # 보고서 파일 생성 확인
    json_files = list(output_dir.glob("*.json"))
    md_files = list(output_dir.glob("*.md"))
    assert json_files, "JSON 보고서 미생성"
    assert md_files, "Markdown 보고서 미생성"

    # JSON 내용 기본 검증
    data = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert "motions" in data
    assert "summary" in data
    assert "phase1_ready_to_swap" in data["summary"]
