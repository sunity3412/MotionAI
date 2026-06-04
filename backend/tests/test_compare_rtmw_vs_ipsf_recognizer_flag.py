"""compare_rtmw_vs_ipsf.py --recognizer flag 단위 테스트 (Plan 5-05 Task 1).

박제 정신:
  · D-01 박제 정신: Phase 5 게이트 = "정은지 reference 측정값 기준 채점 영역 모션 N/N PASS
    + ref-climb out-of-scope counted as PASS" (B1 fix 2026-06-04 revision).
  · D-12: Pod 안 1pass — sweep 도 Pod 안에서 실행.
  · D-14: cache 박제 효과 — recognizer instance 재사용 시 cache hit 보존.
  · D-16: lazy import — `_build_recognizer("gemini")` 가 호출 시점에만 google.genai/firebase_admin import.
  · [[gap-and-line-angle-mandatory-gates]] "강등/우회 금지" — 게이트 정의 정확화 (강등 X).

테스트 항목:
  Test 1: argparse `--recognizer` flag 기본값 = "fallback" (회귀 보존)
  Test 2: argparse `--recognizer fallback` 명시 인식 (choices)
  Test 3: argparse `--recognizer gemini` 명시 인식 (choices)
  Test 4: argparse `--recognizer foo` → SystemExit (choices 강제)
  Test 5: `_build_recognizer("fallback")` → FallbackRecognizer instance
  Test 6: `_build_recognizer("gemini")` → GeminiTechniqueRecognizer instance + cache + hook
  Test 7: `compute_line_angle_gates(recognizer=None)` → FallbackRecognizer default (회귀 보존)
  Test 8: `compute_line_angle_gates(recognizer=mock)` → 주입 recognizer.recognize 호출
  Test 9 (B1 fix): joint_expectations 빈 dict → ("out_of_scope_PASS", "out_of_scope_PASS")
  Test 10 (B1 fix): `gate_passed` helper — PASS / out_of_scope_PASS 둘 다 True, FAIL = False
  Test 11 (B1 fix): `is_in_scope` helper — out_of_scope_PASS 만 False
  Test 12: compute_line_angle_gates 가 video_path 인자를 recognizer.recognize(frames=) 로 전달
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

# sys.path 보장
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from research.evaluations.compare_rtmw_vs_ipsf import (
    _build_recognizer,
    compute_line_angle_gates,
    gate_passed,
    is_in_scope,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS
from sunity_shared.analysis.technique import (
    FallbackRecognizer,
    JOINT_BENT_OK,
    JOINT_EXTEND,
    TechniqueProfile,
)
from sunity_shared.analysis.pose_frame import PoleAxis


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_argv_parser():
    """compare_rtmw_vs_ipsf.main() 내부 argparse 와 동일한 parser 구성."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--pose-engine", default="rtmw")
    parser.add_argument("--criteria-dir", default=None)
    parser.add_argument(
        "--recognizer",
        choices=["fallback", "gemini"],
        default="fallback",
    )
    return parser


def _dummy_pole_axis() -> PoleAxis:
    return PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )


def _dummy_angles(T: int = 5) -> np.ndarray:
    """T×NUM_JOINTS 관절각 배열 (모든 관절 170°)."""
    return np.full((T, len(JOINT_KEYS)), 170.0, dtype=float)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: argparse default = fallback (회귀 보존)
# ─────────────────────────────────────────────────────────────────────────────

def test_recognizer_flag_default_is_fallback():
    """`--recognizer` 미지정 시 default = 'fallback' (Plan 11/23 박제 보존)."""
    # main() 의 parser 가 같은 형태인지 source 검증
    from research.evaluations import compare_rtmw_vs_ipsf as mod
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert '"--recognizer"' in src, "--recognizer flag 박제 X"
    assert '"fallback"' in src and '"gemini"' in src, "choices 박제 X"
    assert 'default="fallback"' in src, "default fallback 박제 X (회귀 보존)"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: argparse --recognizer fallback 인식
# ─────────────────────────────────────────────────────────────────────────────

def test_recognizer_flag_accepts_fallback():
    parser = _make_argv_parser()
    args = parser.parse_args(
        ["--videos", "x.mp4", "--output-dir", "/tmp/out", "--recognizer", "fallback"]
    )
    assert args.recognizer == "fallback"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: argparse --recognizer gemini 인식
# ─────────────────────────────────────────────────────────────────────────────

def test_recognizer_flag_accepts_gemini():
    parser = _make_argv_parser()
    args = parser.parse_args(
        ["--videos", "x.mp4", "--output-dir", "/tmp/out", "--recognizer", "gemini"]
    )
    assert args.recognizer == "gemini"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: argparse --recognizer foo → SystemExit
# ─────────────────────────────────────────────────────────────────────────────

def test_recognizer_flag_rejects_invalid():
    parser = _make_argv_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["--videos", "x.mp4", "--output-dir", "/tmp/out", "--recognizer", "foo"]
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: _build_recognizer("fallback") → FallbackRecognizer
# ─────────────────────────────────────────────────────────────────────────────

def test_build_recognizer_fallback():
    recognizer = _build_recognizer("fallback")
    assert isinstance(recognizer, FallbackRecognizer)


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: _build_recognizer("gemini") → GeminiTechniqueRecognizer + cache + hook
# ─────────────────────────────────────────────────────────────────────────────

def test_build_recognizer_gemini():
    from sunity_shared.analysis.gemini_technique_recognizer import (
        GeminiTechniqueRecognizer,
    )
    from sunity_shared.analysis.technique_cache import TechniqueCache

    recognizer = _build_recognizer("gemini")
    assert isinstance(recognizer, GeminiTechniqueRecognizer)
    # cache 박제 — TechniqueCache instance
    assert isinstance(recognizer.cache, TechniqueCache), (
        "GeminiTechniqueRecognizer.cache = TechniqueCache instance 박제 X"
    )
    # unregistered_hook 박제 — callable
    assert callable(recognizer.unregistered_hook), (
        "GeminiTechniqueRecognizer.unregistered_hook = callable 박제 X (D-09 case 3)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: compute_line_angle_gates(recognizer=None) → FallbackRecognizer default
# ─────────────────────────────────────────────────────────────────────────────

def test_compute_line_angle_gates_default_recognizer_none():
    """recognizer=None → 내부에서 FallbackRecognizer 합성 (회귀 보존)."""
    angles = _dummy_angles()
    pole = _dummy_pole_axis()
    # 회귀: 기존 호출 시그너처와 호환 — recognizer 미주입 가능
    line_v, angle_v = compute_line_angle_gates(angles, pole)
    # verdict 박제 — 3-state literal
    assert line_v in ("PASS", "FAIL", "out_of_scope_PASS")
    assert angle_v in ("PASS", "FAIL", "out_of_scope_PASS")


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: compute_line_angle_gates(recognizer=mock) → mock.recognize 호출
# ─────────────────────────────────────────────────────────────────────────────

def test_compute_line_angle_gates_uses_injected_recognizer():
    """주입된 recognizer.recognize 가 호출되는지 검증."""
    mock_recognizer = MagicMock()
    # 정상 채점 영역 profile (joint_expectations 비어있지 않음)
    mock_recognizer.recognize.return_value = TechniqueProfile(
        name="ref-foxtop",
        category="recognized",
        joint_expectations={k: JOINT_BENT_OK for k in JOINT_KEYS},
        required_split_deg=None,
        requires_hold=True,
        is_symmetric=False,
    )

    angles = _dummy_angles()
    pole = _dummy_pole_axis()
    compute_line_angle_gates(angles, pole, recognizer=mock_recognizer)

    mock_recognizer.recognize.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Test 9 (B1 fix): joint_expectations 빈 dict → ("out_of_scope_PASS", "out_of_scope_PASS")
# ─────────────────────────────────────────────────────────────────────────────

def test_compute_line_angle_gates_out_of_scope_when_no_joint_expectations():
    """B1 fix 박제 — ref-climb 같이 yaml hold_moment 빈 list →
    profile.joint_expectations = {} → out_of_scope_PASS 분기 (D-20 정합).
    """
    mock_recognizer = MagicMock()
    mock_recognizer.recognize.return_value = TechniqueProfile(
        name="ref-climb",
        category="recognized",
        joint_expectations={},  # ref-climb yaml hold_moment 빈 list 정합
        required_split_deg=None,
        requires_hold=True,
        is_symmetric=False,
    )

    angles = _dummy_angles()
    pole = _dummy_pole_axis()
    line_v, angle_v = compute_line_angle_gates(angles, pole, recognizer=mock_recognizer)

    assert line_v == "out_of_scope_PASS", (
        f"빈 joint_expectations → out_of_scope_PASS 박제, got {line_v}"
    )
    assert angle_v == "out_of_scope_PASS", (
        f"빈 joint_expectations → out_of_scope_PASS 박제, got {angle_v}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10 (B1 fix): gate_passed helper
# ─────────────────────────────────────────────────────────────────────────────

def test_gate_passed_counts_pass_and_out_of_scope():
    """B1 fix 박제 — PASS 와 out_of_scope_PASS 둘 다 True, FAIL = False."""
    assert gate_passed("PASS") is True
    assert gate_passed("out_of_scope_PASS") is True
    assert gate_passed("FAIL") is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 11 (B1 fix): is_in_scope helper
# ─────────────────────────────────────────────────────────────────────────────

def test_is_in_scope_excludes_out_of_scope():
    """B1 fix 박제 — verdict 표 분모 N = 채점 영역 모션 수 산정용."""
    assert is_in_scope("PASS") is True
    assert is_in_scope("FAIL") is True
    assert is_in_scope("out_of_scope_PASS") is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: compute_line_angle_gates 가 video_path 를 recognizer.recognize(frames=) 전달
# ─────────────────────────────────────────────────────────────────────────────

def test_compute_line_angle_gates_passes_video_path_to_recognizer():
    """video_path 인자 → recognizer.recognize(frames=video_path) 박제 정합 검증."""
    mock_recognizer = MagicMock()
    mock_recognizer.recognize.return_value = TechniqueProfile(
        name="ref-foxtop",
        category="recognized",
        joint_expectations={k: JOINT_BENT_OK for k in JOINT_KEYS},
        required_split_deg=None,
        requires_hold=True,
        is_symmetric=False,
    )

    angles = _dummy_angles()
    pole = _dummy_pole_axis()
    fake_video_path = "/workspace/videos/ref-foxtop.mp4"
    compute_line_angle_gates(
        angles, pole, recognizer=mock_recognizer, video_path=fake_video_path
    )

    # recognize 가 frames=video_path 로 호출됨
    call_kwargs = mock_recognizer.recognize.call_args.kwargs
    call_args = mock_recognizer.recognize.call_args.args
    # frames 는 positional 또는 kwarg — 둘 다 허용
    if "frames" in call_kwargs:
        assert call_kwargs["frames"] == fake_video_path
    else:
        # positional: (angles, frames)
        assert len(call_args) >= 2 and call_args[1] == fake_video_path
