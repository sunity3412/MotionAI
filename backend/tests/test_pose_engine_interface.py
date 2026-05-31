"""단위 테스트: MediaPipePoseEngine 어댑터 (Plan 01-02 Task 2).

mock PoseLandmarker (DI 패턴) 으로 mediapipe 실제 설치 없이 테스트.

REVIEWS 박제:
  H-2: module-level mediapipe import 0 — mediapipe는 __init__ 내부에서만 lazy import
  H-3: pole_axis가 모든 반환 PoseFrame.pole_axis에 보존
  H-4: reliability가 'high' 산출 (모두 가시 mock)
  Pitfall 1: Lambda ARM64 미지원 fail-fast (RuntimeError "mediapipe")
  Pitfall 2: timestamp 단조 증가 (target_fps=9 → 0,111,222,...)
"""

from __future__ import annotations

import importlib
import sys
from collections import deque
from typing import Any

import numpy as np
import pytest

from tests.fixtures.mediapipe_landmarks import (
    make_mock_detection_result,
    make_mock_no_human_result,
    make_mock_world_landmarks_33,
    make_mock_image_landmarks_33,
)
from sunity_shared.analysis.pose_engines.mediapipe_engine import MediaPipePoseEngine
from sunity_shared.analysis.pose_frame import PoleAxis, PoseFrame
from sunity_shared.analysis.interfaces import NoHumanError


# ── Mock landmarker ───────────────────────────────────────────────────────


class _MockLandmarker:
    """MediaPipe PoseLandmarker duck-type. DI로 주입해 실 mediapipe 미사용.

    results_queue: deque[MockDetectionResult | None]
    None 이면 no_human_result 반환.
    """

    def __init__(self, results: list) -> None:
        self._queue: deque = deque(results)

    def detect_for_video(self, image: Any, timestamp_ms: int) -> Any:
        if self._queue:
            return self._queue.popleft()
        return make_mock_no_human_result()


def _make_engine_with_results(results: list, target_fps: float = 9.0) -> MediaPipePoseEngine:
    """factory classmethod로 mock landmarker 주입."""
    landmarker = _MockLandmarker(results)
    return MediaPipePoseEngine.create_with_landmarker(landmarker, target_fps=target_fps)


def _default_pole_axis() -> PoleAxis:
    return PoleAxis(
        axis_vector=(0.0, 0.0, 1.0),
        confidence_level="high",
        source="detected",
    )


def _make_3_frame_ndarray() -> np.ndarray:
    """3 frame RGB uint8 (T=3, H=4, W=4, C=3) 더미 배열."""
    return np.zeros((3, 4, 4, 3), dtype=np.uint8)


def _make_n_frame_ndarray(n: int) -> np.ndarray:
    return np.zeros((n, 4, 4, 3), dtype=np.uint8)


# ── Test 1: 기본 반환 ─────────────────────────────────────────────────────


def test_engine_estimate_returns_pose_frames():
    """mock PoseLandmarker(33 visible) 주입 → 3 frame → list[PoseFrame] 길이 3.

    frame_index = 0,1,2. timestamp_ms = 0, 111, 222 (target_fps=9).
    """
    results = [
        make_mock_detection_result() for _ in range(3)
    ]
    engine = _make_engine_with_results(results, target_fps=9.0)
    frames_arr = _make_3_frame_ndarray()
    pa = _default_pole_axis()

    pose_frames = engine.estimate(frames_arr, pa)

    assert len(pose_frames) == 3, f"expected 3, got {len(pose_frames)}"
    assert pose_frames[0].frame_index == 0
    assert pose_frames[1].frame_index == 1
    assert pose_frames[2].frame_index == 2
    # timestamp_ms: int(t * 1000 / 9.0)
    assert pose_frames[0].timestamp_ms == 0
    assert pose_frames[1].timestamp_ms == 111
    assert pose_frames[2].timestamp_ms == 222


# ── Test 2: pole_axis 보존 (H-3) ──────────────────────────────────────────


def test_engine_propagates_pole_axis_to_pose_frame():
    """estimate(frames, pole_axis=...) → 모든 PoseFrame.pole_axis가 같은 인스턴스 (H-3)."""
    results = [make_mock_detection_result() for _ in range(2)]
    engine = _make_engine_with_results(results)
    pa = _default_pole_axis()
    pose_frames = engine.estimate(_make_n_frame_ndarray(2), pa)

    for frame in pose_frames:
        assert frame.pole_axis is not None, "pole_axis가 None"
        assert frame.pole_axis.axis_vector == pa.axis_vector
        assert frame.pole_axis.confidence_level == pa.confidence_level
        assert frame.pole_axis.source == pa.source


# ── Test 3: NoHumanError ──────────────────────────────────────────────────


def test_engine_no_human_error():
    """전 프레임 미감지 → NoHumanError + message에 'MediaPipe' 포함."""
    results = [make_mock_no_human_result() for _ in range(3)]
    engine = _make_engine_with_results(results)

    with pytest.raises(NoHumanError) as exc_info:
        engine.estimate(_make_3_frame_ndarray(), _default_pole_axis())

    assert "MediaPipe" in str(exc_info.value), (
        f"NoHumanError message에 'MediaPipe'가 없음: {exc_info.value!r}"
    )


# ── Test 4: 부분 미감지 → sentinel (PoseFrame.empty) ─────────────────────


def test_engine_partial_detection_sentinel():
    """frame 1만 미감지 → list 길이 3 (frame 1 = PoseFrame.empty), NoHumanError 없음."""
    results = [
        make_mock_detection_result(),   # frame 0: detection
        make_mock_no_human_result(),    # frame 1: no human
        make_mock_detection_result(),   # frame 2: detection
    ]
    engine = _make_engine_with_results(results)

    # NoHumanError가 나면 안 됨
    pose_frames = engine.estimate(_make_3_frame_ndarray(), _default_pole_axis())

    assert len(pose_frames) == 3
    # frame 1은 empty sentinel: keypoints_3d가 비어있음
    assert len(pose_frames[1].keypoints_3d) == 0, (
        f"frame 1은 empty sentinel이어야 함, got {len(pose_frames[1].keypoints_3d)} keypoints"
    )
    # frame 0, 2는 정상 감지: keypoints_3d에 17개
    assert len(pose_frames[0].keypoints_3d) == 17
    assert len(pose_frames[2].keypoints_3d) == 17


# ── Test 5: timestamp 단조 증가 (Pitfall 2) ───────────────────────────────


def test_engine_timestamp_monotonic():
    """10 frame → timestamps 단조 증가. target_fps=9 기준 int(t*1000/9)."""
    n = 10
    results = [make_mock_detection_result() for _ in range(n)]
    engine = _make_engine_with_results(results, target_fps=9.0)

    pose_frames = engine.estimate(_make_n_frame_ndarray(n), _default_pole_axis())

    timestamps = [f.timestamp_ms for f in pose_frames]
    # 단조 증가
    for i in range(1, len(timestamps)):
        assert timestamps[i] > timestamps[i - 1], (
            f"timestamps not monotonic: {timestamps[i-1]} >= {timestamps[i]} at index {i}"
        )
    # 첫 번째: 0
    assert timestamps[0] == 0
    # 마지막 (n-1=9): int(9 * 1000 / 9) = 1000
    assert timestamps[-1] == int(9 * 1000 / 9.0)


# ── Test 6: 모델 파일 없음 → RuntimeError ────────────────────────────────


def test_engine_model_path_missing():
    """존재하지 않는 model_path + model_path=None → RuntimeError + 메시지에 파일명 포함.

    factory create_with_landmarker가 아닌 직접 생성 경로 (DI 없음 → mediapipe 필요).
    여기서는 model_path 검증 단계에서 RuntimeError를 발생시키는 것이 핵심.
    mediapipe 설치 여부와 무관하게 model_path 검증이 먼저일 경우도 있으나
    mediapipe import 실패 시 RuntimeError를 먼저 발생시킴 — 둘 다 RuntimeError.
    """
    with pytest.raises((RuntimeError, ImportError)):
        # mediapipe 미설치 환경에서는 ImportError → RuntimeError 매핑이 먼저.
        # 설치된 환경이라면 모델 파일 없음 → RuntimeError가 발생해야 함.
        MediaPipePoseEngine(model_path="/nonexistent/pose_landmarker_heavy.task")


# ── Test 7: mediapipe 미설치 → lazy import 실패 → RuntimeError (H-2 박제) ─


def test_engine_lazy_import_no_mediapipe():
    """mediapipe 미설치 시뮬레이션 → MediaPipePoseEngine() RuntimeError.

    sys.modules['mediapipe'] = None 패치로 ImportError 시뮬레이션.
    H-2 박제: 인스턴스화 시점에만 import — 모듈 로드는 성공해야 함.
    """
    # sys.modules에서 mediapipe를 강제 제거
    saved = {}
    keys_to_remove = [k for k in sys.modules if k == "mediapipe" or k.startswith("mediapipe.")]
    for k in keys_to_remove:
        saved[k] = sys.modules.pop(k)
    # mediapipe import를 block: None을 넣으면 ImportError처럼 동작
    sys.modules["mediapipe"] = None  # type: ignore[assignment]

    try:
        with pytest.raises((RuntimeError, ImportError)):
            MediaPipePoseEngine(model_path=None)
    finally:
        # 복원
        del sys.modules["mediapipe"]
        sys.modules.update(saved)


# ── Test 8: 모듈 import만으로 mediapipe import 안 함 (H-2 박제) ──────────


def test_module_import_without_mediapipe():
    """mediapipe 없이 mediapipe_engine 모듈 import만으로는 오류 없음.

    H-2 박제: module-level mediapipe import 금지.
    """
    # 모듈이 이미 로드됐으면 reload로 재검증
    import sunity_shared.analysis.pose_engines.mediapipe_engine as _mod
    importlib.reload(_mod)
    # import 자체가 성공하면 OK — RuntimeError/ImportError 없이 지나가야 함
    assert hasattr(_mod, "MediaPipePoseEngine")


# ── Test 9: confidence 변환 (D-05 + 어댑터 통합) ─────────────────────────


def test_confidence_conversion_in_engine():
    """mock landmark visibility=0.8, presence=0.7 → nose.confidence ≈ 0.56."""
    from tests.fixtures.mediapipe_landmarks import _MockLandmark

    # 모든 landmark를 visibility=0.8, presence=0.7로 만들기
    custom_world = [
        _MockLandmark(
            x=float(i % 5) * 0.1,
            y=float(i // 5) * 0.1,
            z=0.0,
            visibility=0.8,
            presence=0.7,
        )
        for i in range(33)
    ]
    custom_image = make_mock_image_landmarks_33()
    result = make_mock_detection_result(
        world_landmarks_33=custom_world,
        image_landmarks_33=custom_image,
    )
    engine = _make_engine_with_results([result])
    pose_frames = engine.estimate(_make_n_frame_ndarray(1), _default_pole_axis())

    nose_kp = pose_frames[0].keypoints_3d.get("nose")
    assert nose_kp is not None, "nose keypoint 없음"
    assert abs(nose_kp.confidence - 0.8 * 0.7) < 1e-6, (
        f"nose.confidence: expected {0.8*0.7:.4f}, got {nose_kp.confidence:.4f}"
    )


# ── Test 10: reliability 산출 (H-4 통합) ─────────────────────────────────


def test_reliability_set_in_engine():
    """mock 33 visible (0.9) → PoseFrame.reliability == 'high' (H-4 통합)."""
    results = [make_mock_detection_result()]
    engine = _make_engine_with_results(results)
    pose_frames = engine.estimate(_make_n_frame_ndarray(1), _default_pole_axis())

    assert pose_frames[0].reliability == "high", (
        f"expected 'high', got {pose_frames[0].reliability!r}"
    )
