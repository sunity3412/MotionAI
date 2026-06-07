"""Phase 2 R&D harness smoke tests (HIGH-1 v5 + HIGH-2 v5 박제).

12 case — argparse help (5) + gap compute (2) + load empty (2) + extract mock (1) +
joints→profile (3 — HIGH-1 v5).
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_help(module: str) -> tuple[int, str]:
    """`python -m <module> --help` → (exitcode, stdout)."""
    result = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout


# ── argparse help (5) ─────────────────────────────────────────────────────


def test_argparse_help_compare() -> None:
    """LOW-1 v3: compare_body_profile --help."""
    rc, out = _run_help("backend.research.evaluations.compare_body_profile")
    assert rc == 0
    assert "rtmw-keypoints-dir" in out
    assert "smplx-joints-dir" in out  # HIGH-1 v5


def test_argparse_help_extract_rtmw() -> None:
    """HIGH-4 v3: extract_rtmw_body_profile_keypoints --help."""
    rc, out = _run_help(
        "backend.research.evaluations.extract_rtmw_body_profile_keypoints"
    )
    assert rc == 0
    assert "--videos" in out
    assert "--output-dir" in out


def test_argparse_help_extract_smplx_joints() -> None:
    """HIGH-1 v5: extract_smplx_joints_from_video --help."""
    rc, out = _run_help(
        "backend.research.evaluations.extract_smplx_joints_from_video"
    )
    assert rc == 0
    assert "--videos" in out
    assert "--output-dir" in out
    assert "--smplx-model-path" in out


def test_argparse_help_joints_to_profile() -> None:
    """HIGH-1 v5: smplx_joints_to_body_profile --help."""
    rc, out = _run_help("backend.research.evaluations.smplx_joints_to_body_profile")
    assert rc == 0
    assert "--joints-dir" in out


def test_argparse_help_orchestrator() -> None:
    """HIGH-2 v5: run_body_profile_gap_report --help."""
    rc, out = _run_help("backend.research.evaluations.run_body_profile_gap_report")
    assert rc == 0
    assert "--videos" in out
    assert "--date" in out


# ── gap 계산 (2) ──────────────────────────────────────────────────────────


def _make_profile(arm_scale: float = 1.1, leg_scale: float = 1.0):
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    return BodyNormalizationProfile(
        estimated_height_scale=(arm_scale + leg_scale + 1.0) / 3,
        arm_scale=arm_scale,
        leg_scale=leg_scale,
        torso_scale=1.0,
        shoulder_hip_ratio=1.2,
        confidence=1.0,
        warnings=[],
    )


def test_compute_profile_gap_zero() -> None:
    """동일 profile → diff 0 → within_5pct_tolerance."""
    from backend.research.evaluations.compare_body_profile import compute_profile_gap

    p = _make_profile()
    rtmw = {"video_a": p}
    smplx = {"video_a": p}
    gap = compute_profile_gap(rtmw, smplx)
    assert gap["verdict"] == "within_5pct_tolerance"
    for diff in gap["per_video"]["video_a"].values():
        assert diff == 0.0


def test_compute_profile_gap_nonzero() -> None:
    """diff > 0.05 → gap_too_wide."""
    from backend.research.evaluations.compare_body_profile import compute_profile_gap

    rtmw = {"video_a": _make_profile(arm_scale=1.0)}
    smplx = {"video_a": _make_profile(arm_scale=1.5)}  # 0.5 diff > 0.05
    gap = compute_profile_gap(rtmw, smplx)
    assert gap["verdict"] == "gap_too_wide"
    assert gap["per_video"]["video_a"]["arm_scale"] == pytest.approx(0.5)


# ── load_rtmw_profiles 비존재 dir → {} ─────────────────────────────────────


def test_load_rtmw_profiles_empty_dir(tmp_path: Path) -> None:
    from backend.research.evaluations.compare_body_profile import load_rtmw_profiles

    result = load_rtmw_profiles(tmp_path / "nonexistent", ["ref-foxtop"])
    assert result == {}


def test_load_smplx_joints_returns_empty_for_missing_dir(tmp_path: Path) -> None:
    """HIGH-3 v3 graceful: 비존재 dir → {} (raise X)."""
    from backend.research.evaluations.smplx_joints_to_body_profile import load_smplx_joints

    result = load_smplx_joints(tmp_path / "nonexistent")
    assert result == {}


# ── extract_rtmw helper callable with mock ───────────────────────────────


def test_extract_rtmw_helper_callable_with_mock(tmp_path: Path, monkeypatch) -> None:
    """HIGH-4 v3: extract helper callable + Pod 환경 graceful."""
    from backend.research.evaluations import extract_rtmw_body_profile_keypoints as mod

    # CI 환경 — RTMW 모델 load 실패 시 main() 이 graceful exit
    rc = mod.main(["--videos", "test", "--output-dir", str(tmp_path)])
    assert rc == 0  # graceful


# ── HIGH-1 v5 joints→profile 핵심 테스트 (3) ───────────────────────────────


def _make_synthetic_smplx_joints() -> np.ndarray:
    """확정된 segment 거리로 합성 SMPL-X joints.

    pelvis(0) 기준 좌표 — Task 3 measurer 박제 거리 정합:
    shoulder=140, hip=100, upper_arm=120, forearm=110, thigh=180, shank=160, torso=200.
    """
    # NJ=22 정도 — SMPLX_JOINT_INDICES 최대 인덱스 + 1
    joints = np.zeros((22, 3), dtype=float)
    # pelvis at origin
    joints[0] = [0.0, 0.0, 0.0]
    # hips
    joints[1] = [-50.0, 0.0, 0.0]  # left_hip
    joints[2] = [50.0, 0.0, 0.0]   # right_hip
    # spine chain
    joints[3] = [0.0, 50.0, 0.0]   # spine1
    joints[6] = [0.0, 100.0, 0.0]  # spine2
    joints[9] = [0.0, 150.0, 0.0]  # spine3
    joints[12] = [0.0, 180.0, 0.0]  # neck
    joints[15] = [0.0, 220.0, 0.0]  # head
    # collars
    joints[13] = [-30.0, 200.0, 0.0]
    joints[14] = [30.0, 200.0, 0.0]
    # shoulders (mid at y=200)
    joints[16] = [-70.0, 200.0, 0.0]  # left_shoulder
    joints[17] = [70.0, 200.0, 0.0]   # right_shoulder
    # elbows — upper_arm 120 (from shoulder, downward)
    joints[18] = [-70.0, 80.0, 0.0]   # left_elbow (200-120=80)
    joints[19] = [70.0, 80.0, 0.0]    # right_elbow
    # wrists — forearm 110 (from elbow)
    joints[20] = [-70.0, -30.0, 0.0]  # left_wrist (80-110=-30)
    joints[21] = [70.0, -30.0, 0.0]   # right_wrist
    # knees — thigh 180 (from hip, downward)
    joints[4] = [-50.0, -180.0, 0.0]  # left_knee
    joints[5] = [50.0, -180.0, 0.0]   # right_knee
    # ankles — shank 160 (from knee)
    joints[7] = [-50.0, -340.0, 0.0]  # left_ankle
    joints[8] = [50.0, -340.0, 0.0]   # right_ankle
    return joints


def test_smplx_joints_to_body_profile_synthetic_upright() -> None:
    """HIGH-1 v5 핵심: 합성 직립 joints → 알려진 ratio assert."""
    from backend.research.evaluations.smplx_joints_to_body_profile import (
        smplx_joints_to_body_profile,
    )

    joints = _make_synthetic_smplx_joints()
    profile = smplx_joints_to_body_profile(joints)
    # torso = shoulder_mid(0, 200) ↔ hip_mid(0, 0) = 200
    # arm_scale = (120 + 110) / 200 = 1.15
    # leg_scale = (180 + 160) / 200 = 1.7
    # shoulder_hip_ratio = 140 / 100 = 1.4
    assert math.isclose(profile.arm_scale, (120 + 110) / 200, abs_tol=0.05)
    assert math.isclose(profile.leg_scale, (180 + 160) / 200, abs_tol=0.05)
    assert math.isclose(profile.shoulder_hip_ratio, 140 / 100, abs_tol=0.05)


def test_smplx_joints_to_body_profile_two_inputs_yield_different_profiles() -> None:
    """HIGH-1 v5: 다른 joints 입력 → 다른 profile (결정적 변화)."""
    from backend.research.evaluations.smplx_joints_to_body_profile import (
        smplx_joints_to_body_profile,
    )

    j_short = _make_synthetic_smplx_joints()
    j_tall = _make_synthetic_smplx_joints().copy()
    # 전체 팔 길이를 늘림 — wrist y 를 더 아래로 (절댓값 큼 → -130).
    # 기존: 80 → -30 (forearm 110), 200 → 80 (upper_arm 120). total=230.
    # 갱신: wrist y=-130 → forearm 210. total=330 (length 증가).
    j_tall[20] = [-70.0, -130.0, 0.0]
    j_tall[21] = [70.0, -130.0, 0.0]

    profile_short = smplx_joints_to_body_profile(j_short)
    profile_tall = smplx_joints_to_body_profile(j_tall)
    assert profile_short.arm_scale != profile_tall.arm_scale


def test_smplx_joints_to_body_profile_passes_validator() -> None:
    """MEDIUM-2 v5: 합성 joints → 모든 scale 필드 finite + strictly positive."""
    from backend.research.evaluations.smplx_joints_to_body_profile import (
        smplx_joints_to_body_profile,
    )

    joints = _make_synthetic_smplx_joints()
    profile = smplx_joints_to_body_profile(joints)
    for fname in (
        "estimated_height_scale",
        "arm_scale",
        "leg_scale",
        "torso_scale",
        "shoulder_hip_ratio",
    ):
        v = getattr(profile, fname)
        assert math.isfinite(v) and v > 0.0


def test_extract_smplx_joints_graceful_exit_without_weights(
    tmp_path: Path, monkeypatch
) -> None:
    """HIGH-1 v5: SMPLX_MODEL_PATH 미설정 → exit 0 + stderr 한국어 메시지."""
    monkeypatch.delenv("SMPLX_MODEL_PATH", raising=False)
    monkeypatch.delenv("NLF_MODEL_PATH", raising=False)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.research.evaluations.extract_smplx_joints_from_video",
            "--videos",
            "x",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**__import__("os").environ, "SMPLX_MODEL_PATH": "", "NLF_MODEL_PATH": ""},
    )
    assert result.returncode == 0
    assert "SMPL-X weights 미설정" in result.stderr or "미설정" in result.stderr
