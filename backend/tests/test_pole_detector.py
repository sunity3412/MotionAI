"""HoughPoleDetector 단위 테스트.

REVIEWS H-2 박제: cv2 module-level import 금지 검증.
REVIEWS M-2 박제: confidence_level enum ('high'/'medium'/'low') 검증.
D-09: Hough Line Transform + 수직 prior.
D-10: video-level PoleAxis 1개 산출.
D-11: 검출 실패 시 vertical_fallback + confidence_level='low'.

Test 1 과 Test 8 은 cv2 부재 환경에서도 통과 (module load + 함수 매핑만).
Test 2~7 은 cv2 의존 — 미설치 시 pytest.importorskip 으로 skip.
"""

from __future__ import annotations

import importlib
import sys

import numpy as np
import pytest

from fixtures.synthetic_frames import (
    synthetic_no_pole_frames,
    synthetic_tilted_pole_frames,
    synthetic_vertical_pole_frames,
)


# ── Test 1: H-2 박제 — cv2 없이 모듈 import 성공 ──────────────────────────

def test_module_import_without_cv2():
    """cv2가 sys.modules에 없어도 detector 모듈 load 성공 (H-2 박제).

    클래스 인스턴스화는 cv2 필요 — 여기서는 import 만 검증.
    cv2 미설치 환경에서도 통과해야 함.
    """
    saved_cv2 = sys.modules.pop("cv2", None)
    try:
        # 이전에 import 된 모듈 캐시 제거 후 재import
        sys.modules.pop("sunity_shared.analysis.pole.detector", None)
        sys.modules.pop("sunity_shared.analysis.pole", None)

        # cv2 부재 상태에서 module import — ImportError 발생하면 안 됨
        module = importlib.import_module("sunity_shared.analysis.pole.detector")
        assert hasattr(module, "HoughPoleDetector"), "HoughPoleDetector 클래스가 없음"
        # cv2는 아직 import 되지 않았어야 함
        assert "cv2" not in sys.modules, "cv2가 module-level 에서 import 됐음 (H-2 위반)"
    finally:
        # 원래 cv2 복원
        if saved_cv2 is not None:
            sys.modules["cv2"] = saved_cv2


# ── Test 8: confidence_level 임계값 매핑 (M-2 enum) — cv2 불필요 ──────────

def test_confidence_level_threshold_mapping():
    """_map_numeric_to_confidence_level 함수 임계값 매핑 검증 (M-2 enum + H-4 재사용).

    >=0.7 → 'high', >=0.4 → 'medium', <0.4 → 'low'.
    cv2 없이 통과해야 함 (순수 함수 테스트).
    """
    from sunity_shared.analysis.pole.detector import _map_numeric_to_confidence_level

    # high 경계
    assert _map_numeric_to_confidence_level(0.7) == "high"
    assert _map_numeric_to_confidence_level(1.0) == "high"
    assert _map_numeric_to_confidence_level(0.9) == "high"

    # medium 경계
    assert _map_numeric_to_confidence_level(0.4) == "medium"
    assert _map_numeric_to_confidence_level(0.5) == "medium"
    assert _map_numeric_to_confidence_level(0.69) == "medium"

    # low 경계
    assert _map_numeric_to_confidence_level(0.0) == "low"
    assert _map_numeric_to_confidence_level(0.39) == "low"
    assert _map_numeric_to_confidence_level(0.3) == "low"


# ── cv2 의존 테스트 (cv2 설치 환경에서만 실행) ────────────────────────────

@pytest.fixture(scope="module")
def cv2_module():
    """cv2 importorskip — 미설치 시 이 fixture 사용하는 모든 테스트 skip."""
    return pytest.importorskip("cv2", reason="opencv-python(-headless) 미설치 — cv2 테스트 skip")


@pytest.fixture(scope="module")
def detector(cv2_module):
    """HoughPoleDetector 인스턴스 (cv2 필요)."""
    from sunity_shared.analysis.pole.detector import HoughPoleDetector
    return HoughPoleDetector()


# ── Test 2: 수직 폴 프레임 → source='detected', confidence 'high'/'medium' ─

def test_detect_vertical_pole_returns_detected(detector):
    """수직 폴이 있는 합성 프레임에서 검출 성공 + 수직성 확인 (D-09).

    axis_vector[1] (y 성분) > 0.9 이어야 수직 판정.
    """
    frames = synthetic_vertical_pole_frames(num_frames=3, height=256, width=128)
    result = detector.detect(frames)

    assert result.source == "detected", f"source={result.source!r}, 'detected' 기대"
    assert result.confidence_level in {"high", "medium"}, (
        f"confidence_level={result.confidence_level!r}, 'high'/'medium' 기대 (M-2)"
    )
    ax, ay, az = result.axis_vector
    assert ay > 0.9, f"axis_vector y 성분={ay:.3f}, 0.9 초과 기대 (수직성)"


# ── Test 3: 빈 프레임 (균일 흰색) → vertical_fallback + confidence_level='low' ─

def test_detect_no_pole_fallback_low_confidence(detector):
    """수직 선이 없는 프레임 → vertical_fallback + confidence_level='low' (D-11 + M-2).

    axis_vector = (0, 1, 0) 수직 가정 폴백.
    """
    frames = synthetic_no_pole_frames(num_frames=3, height=128, width=64)
    result = detector.detect(frames)

    assert result.source == "vertical_fallback", (
        f"source={result.source!r}, 'vertical_fallback' 기대"
    )
    assert result.confidence_level == "low", (
        f"confidence_level={result.confidence_level!r}, 'low' 기대 (M-2)"
    )
    ax, ay, az = result.axis_vector
    assert abs(ay - 1.0) < 0.01, f"수직 폴백 axis_vector y={ay:.3f}, 1.0 기대"


# ── Test 4: 기울어진 폴 (30°) → vertical_tolerance ±5° 밖 → vertical_fallback ──

def test_detect_tilted_pole_fallback(detector):
    """30° 기울어진 폴은 vertical_tolerance(±5°) 초과 → vertical_fallback (D-11)."""
    frames = synthetic_tilted_pole_frames(num_frames=3, height=256, width=128, tilt_deg=30.0)
    result = detector.detect(frames)

    assert result.source == "vertical_fallback", (
        f"source={result.source!r}, tilted 30° 폴은 vertical_fallback 기대"
    )
    assert result.confidence_level == "low"


# ── Test 5: video-level 단일 PoleAxis (D-10) ────────────────────────────

def test_video_level_single_axis(detector):
    """5 frame 입력 → 결과 PoleAxis는 단일 instance (D-10).

    frame_index=None 이면 video-level.
    """
    frames = synthetic_vertical_pole_frames(num_frames=5, height=256, width=128)
    result = detector.detect(frames)

    from sunity_shared.analysis.pose_frame import PoleAxis
    assert isinstance(result, PoleAxis), "반환값이 PoleAxis 인스턴스여야 함"
    # D-10 — frame_index=None (video-level)
    assert result.frame_index is None, (
        f"frame_index={result.frame_index}, None(video-level) 기대 (D-10)"
    )


# ── Test 6: axis_vector 단위 벡터 (norm = 1.0 ± 1e-3) ─────────────────

def test_pole_axis_returns_unit_vector(detector):
    """검출 성공 시 axis_vector norm = 1.0 ± 1e-3."""
    frames = synthetic_vertical_pole_frames(num_frames=3, height=256, width=128)
    result = detector.detect(frames)

    ax, ay, az = result.axis_vector
    norm = (ax * ax + ay * ay + az * az) ** 0.5
    assert abs(norm - 1.0) < 1e-3, f"norm={norm:.6f}, 1.0 ± 1e-3 기대"


# ── Test 7: 빈 배열 (T=0) → graceful fallback (raise 안 함) ──────────────

def test_detector_empty_frames_handles_gracefully(detector):
    """빈 (0, H, W, 3) 배열 → vertical_fallback + 'low', raise 안 함 (D-11)."""
    frames = np.zeros((0, 128, 64, 3), dtype=np.uint8)

    result = detector.detect(frames)
    assert result.source == "vertical_fallback"
    assert result.confidence_level == "low"
    assert result.frame_index is None
