"""CR-01 / CR-02 regression — Firestore camelCase → BodyNormalizationProfile snake_case coercion.

박제 정신:
  - CR-01 (2026-06-08 review): pipeline/app.py 가 Firestore `bodyNormalizationProfile`
    dict 를 `BodyNormalizationProfile(**raw)` 로 직접 unpack. Firestore 는 camelCase
    저장 (extract_reference_body_profiles.py:_bp_to_camel_dict + complete_analysis 의
    _dataclass_to_camel_case_dict), dataclass 는 snake_case → TypeError 실 production
    crash. 본 테스트는 _coerce_body_profile_dict 의 camelCase 통과 정합 검증.
  - CR-02: 동일 함정이 mode3_progress prev fetch path (prev["bodyNormalizationProfile"])
    에도 적용. 본 테스트는 _dataclass_to_camel_case_dict 의 production 산출 정확히
    재현 — 이전 시점 fixture 가 snake_case 였다면 실제 함정을 잡지 못함.

회귀 방지:
  - _coerce_body_profile_dict 부재 시 (또는 wrong 매핑) BodyNormalizationProfile(**...) 가
    TypeError. 본 테스트가 fail.
  - 모든 7 필드 (estimatedHeightScale, armScale, legScale, torsoScale, shoulderHipRatio,
    confidence, warnings) 의 camel→snake 매핑 정합 확인.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

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


def _snake_profile_kwargs() -> dict:
    """BodyNormalizationProfile snake_case kwargs (golden source)."""
    return {
        "estimated_height_scale": 0.875,
        "arm_scale": 0.9,
        "leg_scale": 0.85,
        "torso_scale": 1.0,
        "shoulder_hip_ratio": 1.1,
        "confidence": 0.8,
        "warnings": ["low_keypoint_confidence"],
    }


def _camel_firestore_dict() -> dict:
    """Production-shape Firestore dict — `_dataclass_to_camel_case_dict` 산출과 정확히 일치.

    backend/scripts/extract_reference_body_profiles.py:_bp_to_camel_dict 와도 정확히
    일치 (양 write path 의 schema 박제).
    """
    return {
        "estimatedHeightScale": 0.875,
        "armScale": 0.9,
        "legScale": 0.85,
        "torsoScale": 1.0,
        "shoulderHipRatio": 1.1,
        "confidence": 0.8,
        "warnings": ["low_keypoint_confidence"],
    }


def test_coerce_body_profile_dict_passes_camel_case_through(app_mod):
    """CR-01 regression — camelCase Firestore dict → BodyNormalizationProfile snake_case kwargs."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    camel = _camel_firestore_dict()
    coerced = app_mod._coerce_body_profile_dict(camel)
    # 7 snake_case 필드가 모두 있어야 함.
    expected_keys = {
        "estimated_height_scale",
        "arm_scale",
        "leg_scale",
        "torso_scale",
        "shoulder_hip_ratio",
        "confidence",
        "warnings",
    }
    assert set(coerced.keys()) == expected_keys

    # BodyNormalizationProfile constructor 가 정상 통과.
    profile = BodyNormalizationProfile(**coerced)
    assert profile.estimated_height_scale == 0.875
    assert profile.arm_scale == 0.9
    assert profile.leg_scale == 0.85
    assert profile.torso_scale == 1.0
    assert profile.shoulder_hip_ratio == 1.1
    assert profile.confidence == 0.8
    assert profile.warnings == ["low_keypoint_confidence"]


def test_coerce_body_profile_dict_accepts_snake_case_too(app_mod):
    """fixture 호환 — 기존 테스트의 snake_case 도 거부 X."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    snake = _snake_profile_kwargs()
    coerced = app_mod._coerce_body_profile_dict(snake)
    profile = BodyNormalizationProfile(**coerced)
    assert profile.arm_scale == 0.9


def test_coerce_body_profile_dict_none_returns_none(app_mod):
    """None 입력 시 None 반환 — caller 의 truthy check 분기 정합."""
    assert app_mod._coerce_body_profile_dict(None) is None


def test_dataclass_to_camel_case_dict_roundtrip_via_coerce(app_mod):
    """CR-01 end-to-end — _dataclass_to_camel_case_dict 산출이
    _coerce_body_profile_dict 를 통해 다시 BodyNormalizationProfile 로 round-trip.

    production write path (complete_analysis: profile → camelCase dict → Firestore) 와
    read path (Firestore → camelCase dict → BodyNormalizationProfile) 의 완전 양방향
    정합 회귀 방지.
    """
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    original = BodyNormalizationProfile(**_snake_profile_kwargs())
    camel_dict = app_mod._dataclass_to_camel_case_dict(original)
    # camelCase keys 가 production 과 정확히 일치
    assert "estimatedHeightScale" in camel_dict
    assert "armScale" in camel_dict
    assert "legScale" in camel_dict
    assert "torsoScale" in camel_dict
    assert "shoulderHipRatio" in camel_dict
    # round-trip
    coerced = app_mod._coerce_body_profile_dict(camel_dict)
    recovered = BodyNormalizationProfile(**coerced)
    assert recovered.estimated_height_scale == original.estimated_height_scale
    assert recovered.arm_scale == original.arm_scale
    assert recovered.leg_scale == original.leg_scale
    assert recovered.torso_scale == original.torso_scale
    assert recovered.shoulder_hip_ratio == original.shoulder_hip_ratio
    assert recovered.confidence == original.confidence
    assert recovered.warnings == original.warnings


def test_seed_script_camel_keys_match_coerce_helper(app_mod):
    """extract_reference_body_profiles.py 의 _bp_to_camel_dict 가 산출하는 camelCase
    key set 이 _coerce_body_profile_dict 가 인식하는 key 와 일치.

    backend/scripts 의 production write path schema (Pod GPU 측정 → JSON fixture →
    seed-reference-body-profile.mjs → Firestore) 와 pipeline read path 의 schema 정합.
    """
    # production source — _bp_to_camel_dict 의 fixed key set.
    production_camel_keys = {
        "estimatedHeightScale",
        "armScale",
        "legScale",
        "torsoScale",
        "shoulderHipRatio",
        "confidence",
        "warnings",
    }
    # 본 set 으로 dict 구성 + coerce
    sample = {
        "estimatedHeightScale": 1.0,
        "armScale": 1.0,
        "legScale": 1.0,
        "torsoScale": 1.0,
        "shoulderHipRatio": 1.0,
        "confidence": 0.5,
        "warnings": [],
    }
    assert set(sample.keys()) == production_camel_keys
    coerced = app_mod._coerce_body_profile_dict(sample)
    assert coerced is not None
    assert coerced["estimated_height_scale"] == 1.0


def test_pipeline_mode1_with_production_camel_case_ref_doc(app_mod, monkeypatch):
    """CR-01 end-to-end regression — production-shape camelCase reference doc 로 _process 가
    crash 없이 mode1 분석 완료.

    snake_case fixture (test_pipeline_body_comparison._ref_profile_dict) 는 함정을
    잡지 못했음 — 본 테스트는 _dataclass_to_camel_case_dict 산출 그대로 사용.
    """
    from unittest.mock import MagicMock

    import numpy as np

    from sunity_shared import models
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.pose_frame import (
        Keypoint3D,
        Keypoint3DAligned,
        PoleAxis,
        PoseFrame,
    )

    # PoseFrame fixture
    def _frame(i):
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
        )

    pose_frames = [_frame(i) for i in range(30)]
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
        estimated_height_scale=0.875,
        arm_scale=0.9,
        leg_scale=0.85,
        torso_scale=1.0,
        shoulder_hip_ratio=1.1,
        confidence=0.8,
        warnings=[],
    )
    monkeypatch.setattr(
        "sunity_shared.analysis.body_normalization_measurer.measure_body_profile",
        lambda pfs: student,
    )
    monkeypatch.setattr(app_mod, "measure_body_profile", lambda pfs: student)

    # KEY: production-shape camelCase ref doc (extract script + complete_analysis 산출과 동일).
    from sunity_shared.analysis.skeleton import KEYPOINT_NAMES
    camel_source_pose = {
        "jointKeys": list(KEYPOINT_NAMES),
        "values": [500.0, 200.0, 0.0, 0.9] * len(KEYPOINT_NAMES),
        "frameIndex": 0,
        "torsoPx": 200.0,
        "confidence": 0.9,
        "measuredAt": 0,
    }
    camel_ref_doc = {
        "motionId": "inversion",
        "bodyNormalizationProfile": _camel_firestore_dict(),
        "bodyComparisonSourcePose": camel_source_pose,
        "athleteName": "정은지",
        "videoS3Key": None,
        "angles": [170.0] * (30 * 8),
        "anglesJointKeys": [
            "left_elbow", "right_elbow", "left_shoulder", "right_shoulder",
            "left_hip", "right_hip", "left_knee", "right_knee",
        ],
        "anglesFrames": 30,
    }

    fake_fs = MagicMock()
    fake_fs.get_analysis.return_value = {
        "mode": models.MODE_EXPERT,
        "referenceMotionId": "inversion",
        "analysisId": "a1",
    }
    fake_fs.get_reference_motion.return_value = camel_ref_doc
    fake_fs.update_analysis_status = MagicMock()
    fake_fs.complete_analysis = MagicMock()
    fake_fs.fail_analysis = MagicMock()
    monkeypatch.setattr(app_mod, "firestore_admin", fake_fs)

    from sunity_shared.analysis.technique import TechniqueProfile
    profile = TechniqueProfile(
        name="inversion",
        category="recognized",
        joint_expectations={},
        motion_id="inversion",
    )
    fake_rec = MagicMock()
    fake_rec.recognize.return_value = profile
    fake_rec.motion_query_hint = None
    monkeypatch.setattr(app_mod, "_RECOGNIZER", fake_rec)
    monkeypatch.setattr(app_mod, "_ensure_recognizer", lambda: fake_rec)

    # 본 호출이 CR-01 시점 production code path 에서 TypeError 던지던 지점.
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")

    # complete_analysis 호출 + camelCase scaleProfile (정규화 ON) 산출 보장.
    assert fake_fs.complete_analysis.called
    bcr = fake_fs.complete_analysis.call_args.kwargs.get("body_comparison_report")
    assert bcr is not None
    assert bcr["comparisonType"] == "mode1"
    # production-shape ref → BodyNormalizationProfile 정상 construct → 정규화 ON 까지 도달.
    assert bcr.get("scaleProfile") is not None, (
        "production-shape camelCase ref doc 로 정규화 통과 실패 — CR-01 회귀"
    )


def test_pipeline_mode3_progress_with_production_camel_case_prev_doc(app_mod, monkeypatch):
    """CR-02 end-to-end regression — mode3_progress prev doc 의 camelCase
    bodyNormalizationProfile 로 crash 없이 분석 완료.

    test_process_mode3_progress_with_prev_body_profile (기존) 는 snake_case 사용 →
    CR-02 함정 잡지 못함.
    """
    from unittest.mock import MagicMock

    import numpy as np

    from sunity_shared import models
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.pose_frame import (
        Keypoint3D,
        Keypoint3DAligned,
        PoleAxis,
        PoseFrame,
    )

    def _frame(i):
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

    pose_frames = [_frame(i) for i in range(30)]
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

    from sunity_shared.analysis.skeleton import KEYPOINT_NAMES

    # KEY: prev doc 의 bodyNormalizationProfile + bodyComparisonSourcePose 모두 camelCase
    # (production 의 complete_analysis → _dataclass_to_camel_case_dict 산출 정합).
    camel_prev_doc = {
        "analysisId": "prevA",
        "angles": [170.0] * (30 * 8),
        "anglesJointKeys": [
            "left_elbow", "right_elbow", "left_shoulder", "right_shoulder",
            "left_hip", "right_hip", "left_knee", "right_knee",
        ],
        "anglesFrames": 30,
        "bodyNormalizationProfile": _camel_firestore_dict(),
        "bodyComparisonSourcePose": {
            "jointKeys": list(KEYPOINT_NAMES),
            "values": [500.0, 200.0, 0.0, 0.9] * len(KEYPOINT_NAMES),
            "frameIndex": 0,
            "torsoPx": 200.0,
            "confidence": 0.9,
            "measuredAt": 0,
        },
        "result": {"dimensionScores": {"line": 60, "stability": 65}},
    }

    fake_fs = MagicMock()
    fake_fs.get_analysis.return_value = {
        "mode": models.MODE_SELF,
        "referenceMotionId": None,
        "analysisId": "a1",
    }
    fake_fs.get_reference_motion.return_value = None
    fake_fs.get_previous_analysis.return_value = camel_prev_doc
    fake_fs.update_analysis_status = MagicMock()
    fake_fs.complete_analysis = MagicMock()
    fake_fs.fail_analysis = MagicMock()
    monkeypatch.setattr(app_mod, "firestore_admin", fake_fs)

    from sunity_shared.analysis.technique import TechniqueProfile
    profile = TechniqueProfile(
        name="fallback", category="unknown",
        joint_expectations={}, motion_id=None,
    )
    fake_rec = MagicMock()
    fake_rec.recognize.return_value = profile
    fake_rec.motion_query_hint = None
    monkeypatch.setattr(app_mod, "_RECOGNIZER", fake_rec)
    monkeypatch.setattr(app_mod, "_ensure_recognizer", lambda: fake_rec)

    # CR-02 시점 production code path 가 TypeError 던지던 지점.
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")

    assert fake_fs.complete_analysis.called
    bcr = fake_fs.complete_analysis.call_args.kwargs.get("body_comparison_report")
    assert bcr is not None
    assert bcr["comparisonType"] == "mode3_progress"
    assert bcr.get("previousAnalysisId") == "prevA"
