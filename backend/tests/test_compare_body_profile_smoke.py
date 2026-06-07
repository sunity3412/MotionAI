"""Phase 2 R&D harness smoke tests (post 2026-06-08 RTMW scope correction).

2026-06-08 scope correction (supersedes v5 §4 + Task 5b): RTMW pivot
([[rtmw-free-stack-pivot]]) 가 NLF/SMPL-X 의존 영구 제거. SMPL-X 관련
스크립트 (smplx_joints_to_body_profile / extract_smplx_joints_from_video /
run_body_profile_gap_report) 폐기. 본 모듈은 RTMW-native 두 path 만 smoke:

  argparse help (2) — compare_body_profile + extract_rtmw_body_profile_keypoints
  gap compute (2)   — compute_profile_gap zero/nonzero
  load empty (1)    — load_rtmw_profiles graceful on missing dir
  extract mock (1)  — extract_rtmw helper graceful in CI
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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


# ── argparse help (2) ─────────────────────────────────────────────────────


def test_argparse_help_compare() -> None:
    """compare_body_profile --help (RTMW vs RTMW, 2026-06-08 scope correction)."""
    rc, out = _run_help("backend.research.evaluations.compare_body_profile")
    assert rc == 0
    assert "rtmw-keypoints-dir" in out
    assert "rtmw-keypoints-dir-b" in out


def test_argparse_help_extract_rtmw() -> None:
    """HIGH-4 v3: extract_rtmw_body_profile_keypoints --help."""
    rc, out = _run_help(
        "backend.research.evaluations.extract_rtmw_body_profile_keypoints"
    )
    assert rc == 0
    assert "--videos" in out
    assert "--output-dir" in out


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
    profiles_a = {"video_a": p}
    profiles_b = {"video_a": p}
    gap = compute_profile_gap(profiles_a, profiles_b)
    assert gap["verdict"] == "within_5pct_tolerance"
    for diff in gap["per_video"]["video_a"].values():
        assert diff == 0.0


def test_compute_profile_gap_nonzero() -> None:
    """diff > 0.05 → gap_too_wide."""
    from backend.research.evaluations.compare_body_profile import compute_profile_gap

    profiles_a = {"video_a": _make_profile(arm_scale=1.0)}
    profiles_b = {"video_a": _make_profile(arm_scale=1.5)}  # 0.5 diff > 0.05
    gap = compute_profile_gap(profiles_a, profiles_b)
    assert gap["verdict"] == "gap_too_wide"
    assert gap["per_video"]["video_a"]["arm_scale"] == pytest.approx(0.5)


# ── load_rtmw_profiles 비존재 dir → {} ─────────────────────────────────────


def test_load_rtmw_profiles_empty_dir(tmp_path: Path) -> None:
    from backend.research.evaluations.compare_body_profile import load_rtmw_profiles

    result = load_rtmw_profiles(tmp_path / "nonexistent", ["ref-foxtop"])
    assert result == {}


# ── extract_rtmw helper callable with mock ───────────────────────────────


def test_extract_rtmw_helper_callable_with_mock(tmp_path: Path) -> None:
    """HIGH-4 v3: extract helper callable + Pod 환경 graceful."""
    from backend.research.evaluations import extract_rtmw_body_profile_keypoints as mod

    # CI 환경 — RTMW 모델 load 실패 시 main() 이 graceful exit
    rc = mod.main(["--videos", "test", "--output-dir", str(tmp_path)])
    assert rc == 0  # graceful
