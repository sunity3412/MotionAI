"""WR-07 regression — recognizer.motion_query_hint 가 분석 간 leak 차단.

박제 정신 (WR-07 / 2026-06-08 review):
  - _RECOGNIZER 는 module-global singleton — SQS 메시지 간 / BackgroundTask 간 공유.
  - mode1 분석이 hint="ref-foxtop" 박은 뒤 mode3 분석 진입 시 if guard 가 false 라
    hint 가 그대로 유지 → Gemini 가 mode3 의 student 영상을 foxtop 으로 biased.
  - fix: 모든 _process 진입 시 hint 를 명시적 set/None (분기 X) — leak 차단.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest


_PIPELINE = Path(__file__).resolve().parents[2] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _import_pipeline():
    sys.modules.pop("app", None)
    import app  # noqa: WPS433
    return importlib.reload(app)


@pytest.fixture
def app_mod():
    return _import_pipeline()


def _fake_frame(i):
    from sunity_shared.analysis.pose_frame import (
        Keypoint3D,
        Keypoint3DAligned,
        PoleAxis,
        PoseFrame,
    )
    kp = {
        "left_shoulder": Keypoint3D(x=430.0, y=100.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_shoulder": Keypoint3D(x=570.0, y=100.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_elbow": Keypoint3D(x=430.0, y=220.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_elbow": Keypoint3D(x=570.0, y=220.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_wrist": Keypoint3D(x=430.0, y=330.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_wrist": Keypoint3D(x=570.0, y=330.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_hip": Keypoint3D(x=450.0, y=300.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_hip": Keypoint3D(x=550.0, y=300.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_knee": Keypoint3D(x=450.0, y=480.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_knee": Keypoint3D(x=550.0, y=480.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_ankle": Keypoint3D(x=450.0, y=640.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_ankle": Keypoint3D(x=550.0, y=640.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
    }
    aligned = {n: Keypoint3DAligned(x=v.x, y=v.y, z=v.z) for n, v in kp.items()}
    return PoseFrame(
        frame_index=i, timestamp_ms=i * 111, raw_landmarks_33={},
        keypoints_3d=kp, keypoints_3d_pole_aligned=aligned, keypoints_2d=None,
        pole_extension_landmarks=None,
        pole_axis=PoleAxis(axis_vector=(0.0, 1.0, 0.0), confidence_level="medium",
                           source="vertical_fallback", frame_index=None),
        reliability="high", body_shape=None,
    )


def _setup_minimal_mocks(app_mod, monkeypatch, recognizer):
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    pose_frames = [_fake_frame(i) for i in range(30)]
    fake_engine = MagicMock()
    fake_engine.estimate.return_value = pose_frames
    fake_frame_extractor = MagicMock()
    fake_frame_extractor.extract.return_value = np.zeros((30, 320, 240, 3), dtype=np.uint8)
    app_mod._FRAME_EXTRACTOR = fake_frame_extractor
    app_mod._RTMW_ENGINE = fake_engine
    app_mod._POSE_ESTIMATOR = MagicMock()
    app_mod._COACH_WRITER = MagicMock()
    monkeypatch.setattr(app_mod, "_s3", MagicMock())

    student = BodyNormalizationProfile(
        estimated_height_scale=0.875, arm_scale=0.9, leg_scale=0.85,
        torso_scale=1.0, shoulder_hip_ratio=1.1, confidence=0.8, warnings=[],
    )
    monkeypatch.setattr(
        "sunity_shared.analysis.body_normalization_measurer.measure_body_profile",
        lambda pfs: student,
    )
    monkeypatch.setattr(app_mod, "measure_body_profile", lambda pfs: student)

    monkeypatch.setattr(app_mod, "_RECOGNIZER", recognizer)
    monkeypatch.setattr(app_mod, "_ensure_recognizer", lambda: recognizer)


def test_motion_query_hint_reset_to_none_for_mode3(app_mod, monkeypatch):
    """WR-07 — mode1 분석이 hint 박은 뒤 mode3 분석 진입 시 hint=None.

    leak 방지 — Gemini 가 mode3 의 student 영상을 이전 mode1 의 motion 으로 biased X.
    """
    from sunity_shared import models
    from sunity_shared.analysis.technique import TechniqueProfile

    rec = MagicMock()
    # 이전 분석이 박은 hint 시뮬레이션
    rec.motion_query_hint = "ref-foxtop"
    rec.recognize.return_value = TechniqueProfile(
        name="fallback", category="unknown", joint_expectations={}, motion_id=None,
    )
    _setup_minimal_mocks(app_mod, monkeypatch, rec)

    fake_fs = MagicMock()
    fake_fs.get_analysis.return_value = {
        "mode": models.MODE_SELF, "referenceMotionId": None, "analysisId": "a1",
    }
    fake_fs.get_reference_motion.return_value = None
    fake_fs.get_previous_analysis.return_value = None
    fake_fs.update_analysis_status = MagicMock()
    fake_fs.complete_analysis = MagicMock()
    fake_fs.fail_analysis = MagicMock()
    fake_fs.record_unregistered_keyword = MagicMock()
    monkeypatch.setattr(app_mod, "firestore_admin", fake_fs)

    # mode3 _process 진입
    app_mod._process("bucket", "uploads/u/a1.mp4", "user-x", "a1")

    # WR-07 검증 — mode3 분석 진입 시 hint 가 reset.
    assert rec.motion_query_hint is None, (
        f"WR-07 위반 — mode3 분석에서 motion_query_hint={rec.motion_query_hint!r} leak. "
        "None 으로 reset 되어야 함."
    )


def test_motion_query_hint_set_to_motion_id_for_mode_expert(app_mod, monkeypatch):
    """WR-07 정합 — mode1 (expert) 분석 시 hint 는 referenceMotionId."""
    from sunity_shared import models
    from sunity_shared.analysis.technique import TechniqueProfile

    rec = MagicMock()
    rec.motion_query_hint = None  # 이전 분석 없음 가정
    rec.recognize.return_value = TechniqueProfile(
        name="inversion", category="recognized", joint_expectations={}, motion_id="inversion",
    )
    _setup_minimal_mocks(app_mod, monkeypatch, rec)

    from sunity_shared.analysis.skeleton import KEYPOINT_NAMES
    ref_doc = {
        "motionId": "inversion",
        "bodyNormalizationProfile": {
            "estimatedHeightScale": 1.0, "armScale": 1.0, "legScale": 1.0,
            "torsoScale": 1.0, "shoulderHipRatio": 1.0, "confidence": 0.9, "warnings": [],
        },
        "bodyComparisonSourcePose": {
            "jointKeys": list(KEYPOINT_NAMES),
            "values": [500.0, 200.0, 0.0, 0.9] * len(KEYPOINT_NAMES),
            "frameIndex": 0, "torsoPx": 200.0, "confidence": 0.9, "measuredAt": 0,
        },
        "athleteName": "정은지",
        "angles": [170.0] * (30 * 8),
        "anglesJointKeys": [
            "left_elbow", "right_elbow", "left_shoulder", "right_shoulder",
            "left_hip", "right_hip", "left_knee", "right_knee",
        ],
        "anglesFrames": 30,
        "videoS3Key": None,
    }

    fake_fs = MagicMock()
    fake_fs.get_analysis.return_value = {
        "mode": models.MODE_EXPERT, "referenceMotionId": "inversion", "analysisId": "a1",
    }
    fake_fs.get_reference_motion.return_value = ref_doc
    fake_fs.update_analysis_status = MagicMock()
    fake_fs.complete_analysis = MagicMock()
    fake_fs.fail_analysis = MagicMock()
    fake_fs.record_unregistered_keyword = MagicMock()
    monkeypatch.setattr(app_mod, "firestore_admin", fake_fs)

    app_mod._process("bucket", "uploads/u/a1.mp4", "user-x", "a1")
    assert rec.motion_query_hint == "inversion"
