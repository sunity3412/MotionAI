"""MediaPipeWithLifterEngine 단위 테스트.

Plan 01-08 T-2: DI factory (create_with_engines) 를 사용해
mediapipe 와 torch 없이 검증.

검증 항목:
  - estimate() 결과 길이 = 입력 PoseFrame 수
  - 출력 PoseFrame 의 pole_axis 가 입력과 동일하게 보존 (H-3)
  - 출력 PoseFrame 에 reliability 필드 존재 + 유효 값
  - _extract_mp_2d_from_pose_frames 가 (T, 33, 2) 형상 반환
  - _replace_keypoints 가 limb joints 에 Keypoint3D 생성
  - estimate() 가 mediapipe_to_h36m17, h36m17_to_coco17_subset 경로 통과
  - lazy __getattr__ 로 pose_engines 패키지에서 접근 가능
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from unittest.mock import MagicMock

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# mediapipe stub — 모듈 load 시 실제 mediapipe 불필요
# ---------------------------------------------------------------------------

def _install_mediapipe_stub() -> None:
    """mediapipe 가 없어도 테스트 가능하도록 최소 stub 주입."""
    if "mediapipe" in sys.modules:
        return
    mp_mod = types.ModuleType("mediapipe")
    mp_tasks = types.ModuleType("mediapipe.tasks")
    mp_tasks_python = types.ModuleType("mediapipe.tasks.python")
    mp_tasks_vision = types.ModuleType("mediapipe.tasks.python.vision")

    class _FakeLandmarkerOptions:
        pass

    mp_tasks_vision.PoseLandmarker = MagicMock()
    mp_tasks_vision.PoseLandmarkerOptions = _FakeLandmarkerOptions
    mp_tasks_vision.RunningMode = MagicMock()
    mp_mod.tasks = mp_tasks
    mp_tasks.python = mp_tasks_python
    mp_tasks_python.vision = mp_tasks_vision
    sys.modules["mediapipe"] = mp_mod
    sys.modules["mediapipe.tasks"] = mp_tasks
    sys.modules["mediapipe.tasks.python"] = mp_tasks_python
    sys.modules["mediapipe.tasks.python.vision"] = mp_tasks_vision


_install_mediapipe_stub()

# ---------------------------------------------------------------------------
# 로컬 import (mediapipe stub 주입 후)
# ---------------------------------------------------------------------------

from sunity_shared.analysis.pose_frame import (  # noqa: E402
    Keypoint2D,
    Keypoint3D,
    Keypoint3DAligned,
    PoleAxis,
    PoseFrame,
)
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES  # noqa: E402


# ---------------------------------------------------------------------------
# 헬퍼: PoleAxis, PoseFrame 픽스처
# ---------------------------------------------------------------------------

def _make_pole_axis() -> PoleAxis:
    return PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="high",
        source="detected",
        frame_index=None,
    )


def _make_pose_frame(
    frame_index: int,
    with_keypoints: bool = True,
) -> PoseFrame:
    """COCO-17 limb joints 가 포함된 간단한 PoseFrame."""
    kp3d: dict[str, Keypoint3D] = {}
    kp2d: dict[str, Keypoint2D] | None = None
    pole_axis = _make_pole_axis()

    if with_keypoints:
        limb_names = [
            "left_shoulder", "right_shoulder",
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
            "left_hip", "right_hip",
            "left_knee", "right_knee",
            "left_ankle", "right_ankle",
        ]
        for name in limb_names:
            kp3d[name] = Keypoint3D(x=0.1, y=0.2, z=0.3, confidence=0.9, uncertainty_proxy=0.1)

        kp2d = {}
        for name in limb_names:
            kp2d[name] = Keypoint2D(x=0.4, y=0.5, visibility=0.9)
        kp2d["nose"] = Keypoint2D(x=0.5, y=0.1, visibility=0.8)

    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=frame_index * 111,
        raw_landmarks_33={},
        keypoints_3d=kp3d,
        keypoints_3d_pole_aligned={},
        keypoints_2d=kp2d,
        pole_extension_landmarks=None,
        pole_axis=pole_axis,
        reliability="high" if with_keypoints else "low",
    )


# ---------------------------------------------------------------------------
# Mock lifter: lift(x) → (T, 17, 3) zeros
# ---------------------------------------------------------------------------

class _MockLifter:
    def lift(self, landmarks_2d: np.ndarray) -> np.ndarray:
        T = landmarks_2d.shape[0]
        return np.zeros((T, 17, 3), dtype=np.float32)


# ---------------------------------------------------------------------------
# Mock mp_engine: returns preset pose_frames
# ---------------------------------------------------------------------------

class _MockMpEngine:
    def __init__(self, pose_frames: list[PoseFrame]) -> None:
        self._frames = pose_frames

    def estimate(self, frames: np.ndarray, pole_axis: PoleAxis) -> list[PoseFrame]:
        return self._frames


# ---------------------------------------------------------------------------
# 지연 import — create_with_engines 가 mediapipe/torch skip 하므로 safe
# ---------------------------------------------------------------------------

def _make_engine(pose_frames: list[PoseFrame]):
    from sunity_shared.analysis.pose_engines.mediapipe_lifter_engine import (
        MediaPipeWithLifterEngine,
    )
    return MediaPipeWithLifterEngine.create_with_engines(
        mp_engine=_MockMpEngine(pose_frames),
        lifter=_MockLifter(),
    )


# ---------------------------------------------------------------------------
# Tests: estimate() 기본 계약
# ---------------------------------------------------------------------------

class TestEstimateOutputLength:
    """estimate() 결과 길이는 입력 PoseFrame 수와 동일해야 한다."""

    def test_single_frame(self) -> None:
        frames_in = [_make_pose_frame(0)]
        engine = _make_engine(frames_in)
        dummy_frames = np.zeros((1, 4, 4, 3), dtype=np.uint8)
        result = engine.estimate(dummy_frames, _make_pole_axis())
        assert len(result) == 1

    def test_multiple_frames(self) -> None:
        frames_in = [_make_pose_frame(i) for i in range(5)]
        engine = _make_engine(frames_in)
        dummy_frames = np.zeros((5, 4, 4, 3), dtype=np.uint8)
        result = engine.estimate(dummy_frames, _make_pole_axis())
        assert len(result) == 5

    def test_empty_input(self) -> None:
        engine = _make_engine([])
        dummy_frames = np.zeros((0, 4, 4, 3), dtype=np.uint8)
        result = engine.estimate(dummy_frames, _make_pole_axis())
        assert result == []


# ---------------------------------------------------------------------------
# Tests: pole_axis 보존 (H-3)
# ---------------------------------------------------------------------------

class TestPoleAxisPreservation:
    """출력 PoseFrame 의 pole_axis 는 estimate() 인자와 동일해야 한다 (H-3)."""

    def test_pole_axis_preserved(self) -> None:
        frames_in = [_make_pose_frame(0), _make_pose_frame(1)]
        engine = _make_engine(frames_in)
        dummy_frames = np.zeros((2, 4, 4, 3), dtype=np.uint8)
        pole = _make_pole_axis()
        result = engine.estimate(dummy_frames, pole)
        for frame in result:
            assert frame.pole_axis == pole

    def test_different_pole_axis_preserved(self) -> None:
        """대각선 폴 축도 그대로 보존한다."""
        ax = (1.0 / 2.0**0.5, 1.0 / 2.0**0.5, 0.0)  # 45도
        pole = PoleAxis(axis_vector=ax, confidence_level="medium", source="detected")
        frames_in = [_make_pose_frame(0)]
        engine = _make_engine(frames_in)
        dummy_frames = np.zeros((1, 4, 4, 3), dtype=np.uint8)
        result = engine.estimate(dummy_frames, pole)
        assert result[0].pole_axis == pole


# ---------------------------------------------------------------------------
# Tests: reliability 필드 존재 및 유효 값
# ---------------------------------------------------------------------------

class TestReliabilityField:
    """출력 PoseFrame 의 reliability 는 'high'|'medium'|'low' 이어야 한다 (H-4)."""

    _valid_levels = {"high", "medium", "low"}

    def test_reliability_valid_value(self) -> None:
        frames_in = [_make_pose_frame(0)]
        engine = _make_engine(frames_in)
        dummy_frames = np.zeros((1, 4, 4, 3), dtype=np.uint8)
        result = engine.estimate(dummy_frames, _make_pole_axis())
        assert result[0].reliability in self._valid_levels

    def test_reliability_present_for_all_frames(self) -> None:
        frames_in = [_make_pose_frame(i) for i in range(3)]
        engine = _make_engine(frames_in)
        dummy_frames = np.zeros((3, 4, 4, 3), dtype=np.uint8)
        result = engine.estimate(dummy_frames, _make_pole_axis())
        for frame in result:
            assert frame.reliability in self._valid_levels


# ---------------------------------------------------------------------------
# Tests: _extract_mp_2d_from_pose_frames
# ---------------------------------------------------------------------------

class TestExtractMp2d:
    """_extract_mp_2d_from_pose_frames 가 (T, 33, 2) 배열을 반환해야 한다."""

    def _get_engine(self) -> object:
        from sunity_shared.analysis.pose_engines.mediapipe_lifter_engine import (
            MediaPipeWithLifterEngine,
        )
        return MediaPipeWithLifterEngine.create_with_engines(
            mp_engine=_MockMpEngine([]),
            lifter=_MockLifter(),
        )

    def test_output_shape(self) -> None:
        engine = self._get_engine()
        frames = [_make_pose_frame(i) for i in range(4)]
        result = engine._extract_mp_2d_from_pose_frames(frames)
        assert result.shape == (4, 33, 2)

    def test_empty_frames(self) -> None:
        engine = self._get_engine()
        result = engine._extract_mp_2d_from_pose_frames([])
        assert result.shape == (0, 33, 2)

    def test_known_joint_filled(self) -> None:
        """left_shoulder (COCO 5→MP 11) 의 x/y 가 keypoints_2d 값과 일치해야 한다."""
        frame = _make_pose_frame(0)
        engine = self._get_engine()
        result = engine._extract_mp_2d_from_pose_frames([frame])
        # COCO left_shoulder→MP index 11
        assert result[0, 11, 0] == pytest.approx(0.4, abs=1e-5)
        assert result[0, 11, 1] == pytest.approx(0.5, abs=1e-5)

    def test_unmapped_joints_padded(self) -> None:
        """매핑 안 된 MP 관절(예: 1=left_eye) 은 0.5 패딩이어야 한다."""
        frame = _make_pose_frame(0)
        engine = self._get_engine()
        result = engine._extract_mp_2d_from_pose_frames([frame])
        # MP 1 (left_eye) 은 COCO-17 에 없음
        assert result[0, 1, 0] == pytest.approx(0.5, abs=1e-5)
        assert result[0, 1, 1] == pytest.approx(0.5, abs=1e-5)

    def test_none_keypoints_2d_stays_padded(self) -> None:
        """keypoints_2d=None 인 프레임은 전체 0.5 패딩 유지."""
        frame = _make_pose_frame(0, with_keypoints=False)
        engine = self._get_engine()
        result = engine._extract_mp_2d_from_pose_frames([frame])
        assert result[0, 11, 0] == pytest.approx(0.5, abs=1e-5)


# ---------------------------------------------------------------------------
# Tests: _replace_keypoints
# ---------------------------------------------------------------------------

class TestReplaceKeypoints:
    """_replace_keypoints 가 limb joints 에 Keypoint3D 를 생성해야 한다."""

    def _get_engine(self) -> object:
        from sunity_shared.analysis.pose_engines.mediapipe_lifter_engine import (
            MediaPipeWithLifterEngine,
        )
        return MediaPipeWithLifterEngine.create_with_engines(
            mp_engine=_MockMpEngine([]),
            lifter=_MockLifter(),
        )

    def _make_coco17_row(self, nan_face: bool = True) -> np.ndarray:
        """(17, 4) 배열. face joints(0-4)는 NaN, limb joints(5-16)는 유효 값."""
        row = np.zeros((17, 4), dtype=np.float32)
        row[:, 3] = 0.1  # uncertainty_proxy = 0.1 → confidence = 0.9
        if nan_face:
            row[:5, :] = np.nan  # nose, eyes, ears → NaN
        return row

    def test_limb_joints_created(self) -> None:
        engine = self._get_engine()
        frame = _make_pose_frame(0)
        coco17_row = self._make_coco17_row()
        new_frame = engine._replace_keypoints(frame, coco17_row, _make_pole_axis())
        # limb joints (5~16 in COCO) 가 keypoints_3d 에 있어야 함
        limb_names = [KEYPOINT_NAMES[i] for i in range(5, 17)]
        for name in limb_names:
            assert name in new_frame.keypoints_3d, f"{name} missing from keypoints_3d"

    def test_face_nans_excluded(self) -> None:
        """face joints NaN 이면 keypoints_3d 에 포함 안 됨."""
        engine = self._get_engine()
        frame = _make_pose_frame(0)
        coco17_row = self._make_coco17_row(nan_face=True)
        new_frame = engine._replace_keypoints(frame, coco17_row, _make_pole_axis())
        face_names = [KEYPOINT_NAMES[i] for i in range(5)]  # nose,eyes,ears
        for name in face_names:
            assert name not in new_frame.keypoints_3d

    def test_pole_axis_set(self) -> None:
        engine = self._get_engine()
        frame = _make_pose_frame(0)
        pole = _make_pole_axis()
        coco17_row = self._make_coco17_row()
        new_frame = engine._replace_keypoints(frame, coco17_row, pole)
        assert new_frame.pole_axis == pole

    def test_reliability_field_exists(self) -> None:
        engine = self._get_engine()
        frame = _make_pose_frame(0)
        coco17_row = self._make_coco17_row()
        new_frame = engine._replace_keypoints(frame, coco17_row, _make_pole_axis())
        assert new_frame.reliability in {"high", "medium", "low"}

    def test_empty_frame_low_reliability(self) -> None:
        """모든 관절 NaN 이면 reliability='low'."""
        engine = self._get_engine()
        frame = _make_pose_frame(0, with_keypoints=False)
        coco17_row = np.full((17, 4), np.nan, dtype=np.float32)
        new_frame = engine._replace_keypoints(frame, coco17_row, _make_pole_axis())
        assert new_frame.reliability == "low"


# ---------------------------------------------------------------------------
# Tests: lazy import via pose_engines package __getattr__
# ---------------------------------------------------------------------------

class TestLazyImport:
    """pose_engines 패키지 __getattr__ 로 MediaPipeWithLifterEngine 접근 가능."""

    def test_lazy_getattr(self) -> None:
        import sunity_shared.analysis.pose_engines as pe
        cls = pe.MediaPipeWithLifterEngine
        from sunity_shared.analysis.pose_engines.mediapipe_lifter_engine import (
            MediaPipeWithLifterEngine,
        )
        assert cls is MediaPipeWithLifterEngine

    def test_unknown_attr_raises(self) -> None:
        import sunity_shared.analysis.pose_engines as pe
        with pytest.raises(AttributeError):
            _ = pe.DoesNotExist  # type: ignore[attr-defined]
