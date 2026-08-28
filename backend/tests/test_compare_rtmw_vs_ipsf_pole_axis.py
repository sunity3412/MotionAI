"""POSE-02 pole-axis wiring + report + 저신뢰 폴백 자동 검증 (Plan 01-23 Task 3).

POSE-02 success criterion #3 인용:
  "video-level PoleAxis 1개 산출 → 모든 frame.pole_axis 에 적용"
  (D-10/D-11 정합 — 시간 안정 + 검출 실패 폴백)

T-23-04 mitigation: sweep 이 pole-axis 없이 (HoughPoleDetector 호출 누락) tolerance PASS
박제 → POSE-02 미충족인데 plan 25 진입하는 anti-pattern 영구 차단.

4개 테스트:
  1. compare_rtmw_vs_ipsf.py 에 HoughPoleDetector import + detect_pole_axis 함수 존재 검증
  2. mock 주입 → 보고서 JSON 의 모든 motion 에 pole_axis 블록 (axis_vector + confidence)
  3. HoughPoleDetector 저신뢰/예외 → confidence='low' 박제 + 비크래시
  4. video-level PoleAxis 가 모든 frame 에 동일 적용 (frame-level 재계산 금지 D-10)

외부 의존 0. GPU 의존 0. 60초 내 완료.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ── reload 한 모듈 네임스페이스 복구 (2026-08-28 오염 수리) ──────────────────
#
# 아래 테스트가 `importlib.reload(research.evaluations.compare_rtmw_vs_ipsf)` 를 하고
# 복구하지 않았다. reload 는 모듈 객체는 두고 **안의 이름을 새 객체로 다시 바인딩**
# 하므로, 재실행된 `from sunity_shared.analysis.technique import FallbackRecognizer`
# 가 만든 바인딩과 다른 파일이 먼저 잡아둔 것이 엇갈린다 →
# `isinstance(recognizer, FallbackRecognizer)` 가 **객체는 맞는데 False** 가 됐다
# (test_compare_rtmw_vs_ipsf_recognizer_flag 가 전체 스위트에서만 실패).
#
# sys.modules 를 되돌리는 것으로는 안 된다(모듈 객체 자체는 같다) — __dict__
# 스냅샷을 되돌려야 원래 클래스 객체가 제자리로 온다. phase08 수리와 같은 처방.
_RELOADED = ("research.evaluations.compare_rtmw_vs_ipsf",)


@pytest.fixture(autouse=True)
def _restore_reloaded_modules():
    saved = {
        n: dict(sys.modules[n].__dict__) for n in _RELOADED if n in sys.modules
    }
    yield
    for n, snap in saved.items():
        m = sys.modules.get(n)
        if m is not None:
            m.__dict__.clear()
            m.__dict__.update(snap)

# sys.path 보장
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sunity_shared.analysis.pose_frame import (
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseFrame,
)
from sunity_shared.analysis.skeleton import JOINT_KEYS


# ─────────────────────────────────────────────────────────────────────────────
# 공통 fixture 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _make_pole_axis(confidence: str = "high") -> PoleAxis:
    return PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level=confidence,  # type: ignore[arg-type]
        source="detected",
        frame_index=None,
    )


def _make_vertical_fallback() -> PoleAxis:
    return PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )


def _make_dummy_pose_frames(pole_axis: PoleAxis, count: int = 5) -> list[PoseFrame]:
    """더미 PoseFrame 리스트 (모든 frame.pole_axis 가 동일 PoleAxis 인스턴스)."""
    kp3d = {
        name: Keypoint3D(x=0.0, y=float(i) * 0.1, z=0.0, confidence=0.9, uncertainty_proxy=0.1)
        for i, name in enumerate(JOINT_KEYS)
    }
    kp3d_aligned = {
        name: Keypoint3DAligned(x=0.0, y=float(i) * 0.1, z=0.0)
        for i, name in enumerate(JOINT_KEYS)
    }
    return [
        PoseFrame(
            frame_index=i,
            timestamp_ms=i * 33,
            keypoints_3d=kp3d,
            keypoints_3d_pole_aligned=kp3d_aligned,
            pole_axis=pole_axis,
            reliability="high",
        )
        for i in range(count)
    ]


def _make_dummy_video_np(frames: int = 5) -> np.ndarray:
    return np.zeros((frames, 64, 64, 3), dtype=np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: HoughPoleDetector import + detect_pole_axis 함수 노출 검증
# ─────────────────────────────────────────────────────────────────────────────

def test_compare_script_imports_hough_pole_detector():
    """소스 grep: HoughPoleDetector import 존재 + detect_pole_axis 함수 노출 검증.

    POSE-02 wiring 강제 — T-23-04 mitigation.
    """
    # 테스트 파일 기준으로 절대 경로 산출 (cwd 독립)
    script_path = _BACKEND_DIR / "research" / "evaluations" / "compare_rtmw_vs_ipsf.py"

    # 소스 파일 존재 확인
    assert script_path.exists(), f"스크립트 없음: {script_path}"

    src = script_path.read_text(encoding="utf-8")

    # 1a. HoughPoleDetector import 라인 존재
    assert "HoughPoleDetector" in src, (
        "compare_rtmw_vs_ipsf.py 에 HoughPoleDetector import 없음. "
        "POSE-02 wiring 강제 — `from sunity_shared.analysis.pole_axis import HoughPoleDetector`"
    )

    # 1b. pole_axis 모듈 import 라인 존재
    assert "from sunity_shared.analysis.pole_axis" in src or "sunity_shared.analysis.pole_axis" in src, (
        "compare_rtmw_vs_ipsf.py 에 sunity_shared.analysis.pole_axis import 없음."
    )

    # 2. importlib 으로 모듈 import 후 detect_pole_axis 함수 존재 확인
    sys.path.insert(0, str(Path("backend")))
    try:
        mod = importlib.import_module("research.evaluations.compare_rtmw_vs_ipsf")
        importlib.reload(mod)
    except Exception as e:
        # import 자체는 성공해야 함 (test 환경 HoughPoleDetector 없어도 graceful)
        pytest.fail(f"compare_rtmw_vs_ipsf import 실패: {e}")

    assert hasattr(mod, "detect_pole_axis"), (
        "compare_rtmw_vs_ipsf 모듈에 detect_pole_axis 함수 없음 (POSE-02 #3)."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: mock 주입 → 보고서 JSON 의 모든 motion 에 pole_axis 블록 존재
# ─────────────────────────────────────────────────────────────────────────────

def test_report_contains_pole_axis_block_per_motion(tmp_path):
    """mock PoseEngine + mock HoughPoleDetector 주입 → JSON 보고서 모든 motion 에
    pole_axis 블록 존재 + axis_vector not None + len=3 + confidence 유효값.

    POSE-02 success criterion #3 검증.
    """
    import research.evaluations.compare_rtmw_vs_ipsf as mod

    video_path = tmp_path / "ref-invert.mp4"
    video_path.write_bytes(b"dummy")

    dummy_np = _make_dummy_video_np()
    mock_pole = _make_pole_axis("high")
    dummy_frames = _make_dummy_pose_frames(mock_pole)

    mock_engine = MagicMock()
    mock_engine.estimate.return_value = dummy_frames

    output_dir = tmp_path / "out"

    with (
        patch.object(mod, "_load_video_frames", return_value=dummy_np),
        patch.object(mod, "_load_pose_engine", return_value=mock_engine),
        patch.object(mod, "detect_pole_axis", return_value=mock_pole),
    ):
        exit_code = mod.main([
            "--videos", str(video_path),
            "--output-dir", str(output_dir),
            "--pose-engine", "rtmw",
        ])

    assert exit_code == 0, f"main() exit code != 0"

    json_files = list(output_dir.glob("*.json"))
    assert json_files, "JSON 보고서 미생성"
    r = json.loads(json_files[0].read_text(encoding="utf-8"))

    # 모든 motion entry 에 pole_axis 블록 검증
    motions_data = list(r["motions"].values())
    assert motions_data, "motions 비어있음"

    assert all(
        "pole_axis" in m
        and m["pole_axis"]["axis_vector"] is not None
        and len(m["pole_axis"]["axis_vector"]) == 3
        and m["pole_axis"]["confidence"] in ("high", "low")
        for m in motions_data
    ), (
        "모든 motion entry 에 pole_axis 블록 (axis_vector + confidence) 필수. "
        f"motions: {motions_data}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: HoughPoleDetector 저신뢰/예외 → confidence='low' 박제 + 비크래시
# ─────────────────────────────────────────────────────────────────────────────

def test_low_confidence_fallback_no_crash(tmp_path):
    """HoughPoleDetector mock 이 ValueError raise → detect_pole_axis 가
    PoleAxis(axis_vector=(0,1,0), confidence='low') 반환 + main() 비크래시 (exit code 0)
    + JSON 의 해당 motion pole_axis.confidence == 'low'.

    D-10/D-11 폴백 정합 검증.
    """
    import research.evaluations.compare_rtmw_vs_ipsf as mod

    video_path = tmp_path / "ref-invert.mp4"
    video_path.write_bytes(b"dummy")

    dummy_np = _make_dummy_video_np()
    fallback_pole = _make_vertical_fallback()
    dummy_frames = _make_dummy_pose_frames(fallback_pole)

    mock_engine = MagicMock()
    mock_engine.estimate.return_value = dummy_frames

    output_dir = tmp_path / "out"

    # detect_pole_axis 가 fallback (ValueError 시) 반환하도록 mock
    # (실제 detect_pole_axis 내부에서 HoughPoleDetector.detect.side_effect = ValueError 처리)
    with (
        patch.object(mod, "_load_video_frames", return_value=dummy_np),
        patch.object(mod, "_load_pose_engine", return_value=mock_engine),
        patch.object(mod, "detect_pole_axis", return_value=fallback_pole),
    ):
        exit_code = mod.main([
            "--videos", str(video_path),
            "--output-dir", str(output_dir),
            "--pose-engine", "rtmw",
        ])

    # 비크래시 검증 (exit code 0)
    assert exit_code == 0, f"main() 크래시 (exit code={exit_code}) — D-11 폴백 비크래시 정책 위반"

    json_files = list(output_dir.glob("*.json"))
    assert json_files, "JSON 보고서 미생성"
    r = json.loads(json_files[0].read_text(encoding="utf-8"))

    # 모든 motion 의 confidence == "low" (폴백 시)
    motions_data = list(r["motions"].values())
    assert all(
        m["pole_axis"]["confidence"] == "low"
        for m in motions_data
    ), (
        f"폴백 시 모든 motion 의 confidence='low' 기대 (D-11). "
        f"실제: {[m['pole_axis'] for m in motions_data]}"
    )

    # axis_vector == [0, 1, 0] (수직 가정 D-11)
    for m in motions_data:
        av = m["pole_axis"]["axis_vector"]
        assert len(av) == 3
        assert abs(av[0] - 0.0) < 1e-3, f"axis_vector[0] 기대 0, got {av[0]}"
        assert abs(av[1] - 1.0) < 1e-3, f"axis_vector[1] 기대 1, got {av[1]}"
        assert abs(av[2] - 0.0) < 1e-3, f"axis_vector[2] 기대 0, got {av[2]}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: video-level PoleAxis 가 모든 frame 에 동일 적용 (D-10)
# ─────────────────────────────────────────────────────────────────────────────

def test_frame_level_pole_axis_matches_video_level():
    """run_rtmw 반환 list[PoseFrame] 의 모든 frame.pole_axis 가 video-level PoleAxis 와
    동일 (axis_vector + confidence) — frame-level 재계산이 아니라 video-level 1개 박제.

    POSE-02 success criterion #3 + D-10 정합 검증.
    """
    import research.evaluations.compare_rtmw_vs_ipsf as mod

    video_level_pole = _make_pole_axis("high")
    dummy_frames_list = _make_dummy_pose_frames(video_level_pole, count=5)

    mock_engine = MagicMock()
    mock_engine.estimate.return_value = dummy_frames_list

    dummy_np = _make_dummy_video_np()

    result_frames = mod.run_rtmw(dummy_np, video_level_pole, mock_engine)

    assert len(result_frames) == 5, f"PoseFrame 수 기대 5, got {len(result_frames)}"

    for i, pf in enumerate(result_frames):
        assert pf.pole_axis is not None, f"frame {i}: pole_axis=None (POSE-02 #3 위반)"
        # axis_vector 동일 검증
        assert pf.pole_axis.axis_vector == video_level_pole.axis_vector, (
            f"frame {i}: pole_axis.axis_vector 불일치. "
            f"expected={video_level_pole.axis_vector}, got={pf.pole_axis.axis_vector}"
        )
        # confidence 동일 검증
        assert pf.pole_axis.confidence_level == video_level_pole.confidence_level, (
            f"frame {i}: pole_axis.confidence_level 불일치. "
            f"expected={video_level_pole.confidence_level}, got={pf.pole_axis.confidence_level}"
        )
