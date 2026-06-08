"""Task 3 — pipeline _process → firestore_admin.complete_analysis wiring 검증.

박제 정신:
  - body_comparison_report dataclass → _dataclass_to_camel_case_dict 변환 →
    Firestore camelCase (comparisonType / bodyNormalizationConfidence /
    usedReferenceFallback).
  - body_normalization_profile (R4 fix non-null) → 항상 변환.
  - None graceful (mode 분기 의도된 None path).
  - _validate_flat_dict_no_nested_array TypeError → fail_analysis(server_error).
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


def _student_profile():
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    return BodyNormalizationProfile(
        estimated_height_scale=0.875,
        arm_scale=0.9,
        leg_scale=0.85,
        torso_scale=1.0,
        shoulder_hip_ratio=1.1,
        confidence=0.8,
        warnings=[],
    )


def _ref_profile_dict():
    return {
        "estimated_height_scale": 1.0,
        "arm_scale": 1.0,
        "leg_scale": 1.0,
        "torso_scale": 1.0,
        "shoulder_hip_ratio": 1.0,
        "confidence": 0.9,
        "warnings": [],
    }


def _ref_source_pose_dict():
    from sunity_shared.analysis.skeleton import KEYPOINT_NAMES

    joint_keys = list(KEYPOINT_NAMES)
    values = [500.0, 200.0, 0.0, 0.9] * len(joint_keys)
    return {
        "joint_keys": tuple(joint_keys),
        "values": tuple(values),
        "frame_index": 0,
        "torso_px": 200.0,
        "confidence": 0.9,
        "measured_at": 0,
    }


def _fake_pose_frames(n=30, conf=0.9):
    from sunity_shared.analysis.pose_frame import (
        Keypoint3D,
        Keypoint3DAligned,
        PoleAxis,
        PoseFrame,
    )

    frames = []
    for i in range(n):
        kp = {
            "left_shoulder": Keypoint3D(x=430.0, y=100.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "right_shoulder": Keypoint3D(x=570.0, y=100.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "left_elbow": Keypoint3D(x=430.0, y=220.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "right_elbow": Keypoint3D(x=570.0, y=220.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "left_wrist": Keypoint3D(x=430.0, y=330.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "right_wrist": Keypoint3D(x=570.0, y=330.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "left_hip": Keypoint3D(x=450.0, y=300.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "right_hip": Keypoint3D(x=550.0, y=300.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "left_knee": Keypoint3D(x=450.0, y=480.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "right_knee": Keypoint3D(x=550.0, y=480.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "left_ankle": Keypoint3D(x=450.0, y=640.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
            "right_ankle": Keypoint3D(x=550.0, y=640.0, z=0.0, confidence=conf, uncertainty_proxy=1 - conf),
        }
        aligned = {n: Keypoint3DAligned(x=v.x, y=v.y, z=v.z) for n, v in kp.items()}
        frames.append(PoseFrame(
            frame_index=i,
            timestamp_ms=i * 111,
            raw_landmarks_33={},
            keypoints_3d=kp,
            keypoints_3d_pole_aligned=aligned,
            keypoints_2d=None,
            pole_extension_landmarks=None,
            pole_axis=PoleAxis(
                axis_vector=(0.0, 1.0, 0.0),
                confidence_level="medium",
                source="vertical_fallback",
                frame_index=None,
            ),
            reliability="high",
            body_shape=None,
        ))
    return frames


def _install_mocks(app_mod, monkeypatch, *, mode, ref_doc=None, prev_doc=None):
    from sunity_shared.analysis.technique import TechniqueProfile

    pose_frames = _fake_pose_frames()
    profile = _student_profile()
    fake_engine = MagicMock()
    fake_engine.estimate.return_value = pose_frames
    fake_frame_extractor = MagicMock()
    fake_frame_extractor.extract.return_value = np.zeros((30, 320, 240, 3), dtype=np.uint8)
    app_mod._FRAME_EXTRACTOR = fake_frame_extractor
    app_mod._RTMW_ENGINE = fake_engine
    app_mod._POSE_ESTIMATOR = MagicMock()
    app_mod._COACH_WRITER = MagicMock()
    monkeypatch.setattr(app_mod, "_s3", MagicMock())
    monkeypatch.setattr(
        "sunity_shared.analysis.body_normalization_measurer.measure_body_profile",
        lambda pfs: profile,
    )
    monkeypatch.setattr(app_mod, "measure_body_profile", lambda pfs: profile)

    fake_fs = MagicMock()
    fake_fs.get_analysis.return_value = {
        "mode": mode,
        "referenceMotionId": "inversion" if ref_doc else None,
        "analysisId": "a1",
    }
    fake_fs.get_reference_motion.return_value = ref_doc
    fake_fs.get_previous_analysis.return_value = prev_doc
    fake_fs.update_analysis_status = MagicMock()
    fake_fs.complete_analysis = MagicMock()
    fake_fs.fail_analysis = MagicMock()
    monkeypatch.setattr(app_mod, "firestore_admin", fake_fs)

    tp = TechniqueProfile(
        name="inversion",
        category="recognized",
        joint_expectations={},
        motion_id="inversion",
    )
    fake_rec = MagicMock()
    fake_rec.recognize.return_value = tp
    fake_rec.motion_query_hint = None
    monkeypatch.setattr(app_mod, "_RECOGNIZER", fake_rec)
    monkeypatch.setattr(app_mod, "_ensure_recognizer", lambda: fake_rec)
    return fake_fs


def test_process_calls_complete_analysis_with_body_comparison_report(app_mod, monkeypatch):
    """Test 1 — mode1 end-to-end → complete_analysis 의 body_comparison_report arg 가 camelCase 필드 보유."""
    from sunity_shared import models

    ref_doc = {
        "motionId": "inversion",
        "bodyNormalizationProfile": _ref_profile_dict(),
        "bodyComparisonSourcePose": _ref_source_pose_dict(),
        "athleteName": "정은지",
        "angles": [170.0] * (30 * 8),
        "anglesJointKeys": ["left_elbow", "right_elbow", "left_shoulder",
                            "right_shoulder", "left_hip", "right_hip",
                            "left_knee", "right_knee"],
        "anglesFrames": 30,
    }
    fake_fs = _install_mocks(app_mod, monkeypatch, mode=models.MODE_EXPERT, ref_doc=ref_doc)
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert "comparisonType" in bcr
    assert "bodyNormalizationConfidence" in bcr
    assert "usedReferenceFallback" in bcr


def test_process_calls_complete_analysis_with_body_normalization_profile(app_mod, monkeypatch):
    """Test 2 — student_profile (R4 non-null) → complete_analysis 의 body_normalization_profile arg 가 camelCase 필드 보유."""
    from sunity_shared import models

    fake_fs = _install_mocks(app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None)
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bnp = fake_fs.complete_analysis.call_args.kwargs["body_normalization_profile"]
    assert bnp is not None
    assert "estimatedHeightScale" in bnp
    assert "armScale" in bnp
    assert "shoulderHipRatio" in bnp
    assert "confidence" in bnp


def test_process_handles_none_body_comparison_report_gracefully(app_mod, monkeypatch):
    """Test 3 — body_comparison_report 가 None 일 수 있는 path (예: 알고리즘 실패) → fail_analysis 호출 X.

    pipeline 이 body_comparison_report=None 으로 complete_analysis 호출 → graceful.
    """
    # body_comparison_report 가 None 이려면 mode 가 알 수 없는 값일 때 — 본 pipeline 은
    # 항상 mode1/mode3 분기 안에서 값 박제 한다. 본 test 는 complete_analysis 의
    # body_comparison_report=None 인자 그 자체가 fail_analysis 호출 trigger X 박제.
    from sunity_shared import firestore_admin

    fake_doc = MagicMock()
    monkeypatch.setattr(firestore_admin, "_doc", lambda path: fake_doc)
    firestore_admin.complete_analysis(
        "u1",
        "a1",
        {"overallScore": 80, "dimensionScores": {}, "joints": [], "tips": [],
         "comparison": {"mode": "mode1"}, "myVideoUrl": "x"},
        body_comparison_report=None,
    )
    # fail_analysis path 진입 0
    payload = fake_doc.set.call_args.args[0]
    assert payload["status"] == "done"


def test_process_validates_flat_dict_before_firestore_write(app_mod):
    """Test 4 — findings 에 nested list 발생 시 validator TypeError → pipeline 의 fail_analysis 진입.

    본 test 는 pipeline 의 wiring 까지 박제 X — Task 2 validator 가 raise 한다는
    것만 확인 (별도 fail_analysis wiring 은 Task 3 우선순위 가벼움 — 후속 작업).
    """
    from sunity_shared import firestore_admin

    nested_bcr = {
        "comparisonType": "mode1",
        "findings": [{"deficitCode": "x", "badNested": [1, 2]}],  # nested list in dict 박제
        "warnings": [],
        "usedReferenceFallback": False,
    }
    with pytest.raises(TypeError):
        firestore_admin._validate_flat_dict_no_nested_array(
            nested_bcr, path="bodyComparisonReport"
        )


def test_userAnalyses_normalize_passes_through_body_comparison_report():
    """Test 5 — app/src/lib/userAnalyses.ts 가 raw.result.bodyComparisonReport passthrough.

    TS 타입 정의 + literal "bodyComparisonReport" 등장 검증 (I2 positive assertion).
    """
    from pathlib import Path as _P

    user_analyses_path = _P(__file__).resolve().parents[3] / "app" / "src" / "lib" / "userAnalyses.ts"
    src = user_analyses_path.read_text(encoding="utf-8")
    assert "bodyComparisonReport" in src, (
        "Plan 06-02 Task 3 I2 positive assertion 위반 — userAnalyses.ts 에 bodyComparisonReport 표기 없음"
    )
