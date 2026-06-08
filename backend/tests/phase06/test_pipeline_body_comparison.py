"""Task 1 — pipeline _process 의 body_normalizer.compare_body_profiles wiring 검증.

박제 정신:
  - R3 fix: 단일 _extract_video_analysis_inputs helper. RTMW estimate 1회 실행 보장.
  - R4 fix: student_profile non-null (BodyNormalizationProfile fallback 정합).
  - R2 wiring: mode1 + mode3 fallback path 가 reference 의 bodyComparisonSourcePose
    도 fetch. source_keypoints=ref_source_pose.to_keypoints_array() 전달.
  - R8 fix: extra_warnings injection (caller 가 fallback_reference_not_found /
    reference_source_pose_missing 주입). dataclasses.replace 우회 금지.
  - C2 fix: _match_reference_by_motion_id exact-match.
  - C9 fix: Pitfall 6 canary (mode1 missing ref_profile → warning + low confidence).
  - W1: comparisonType 3 cases (mode1 / mode3_first / mode3_progress) + usedReferenceFallback.

mock 전용 — RTMW / S3 / Firestore 실 호출 0.
"""

from __future__ import annotations

import dataclasses
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
    """pipeline/app.py 강제 재로드 (테스트 격리)."""
    sys.modules.pop("app", None)
    import app  # noqa: WPS433
    return importlib.reload(app)


@pytest.fixture
def app_mod():
    return _import_pipeline()


# ── helper: synthesize fake PoseFrames (Phase 2 test 패턴 재사용) ─────────


def _build_fake_pose_frame(frame_index: int = 0, conf: float = 0.9):
    from sunity_shared.analysis.pose_frame import (
        Keypoint3D,
        Keypoint3DAligned,
        PoleAxis,
        PoseFrame,
    )

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
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=frame_index * 111,
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


def _fake_pose_frames(n: int = 30, conf: float = 0.9):
    return [_build_fake_pose_frame(frame_index=i, conf=conf) for i in range(n)]


def _student_profile(conf: float = 0.8):
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    return BodyNormalizationProfile(
        estimated_height_scale=0.875,
        arm_scale=0.9,
        leg_scale=0.85,
        torso_scale=1.0,
        shoulder_hip_ratio=1.1,
        confidence=conf,
        warnings=[],
    )


def _ref_profile_dict():
    """reference 측 bodyNormalizationProfile (Firestore stored dict 형태)."""
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
    """reference 측 bodyComparisonSourcePose (Firestore stored dict 형태).

    flat values (4 × 17 = 68) — 직립 자세 박제.
    """
    from sunity_shared.analysis.skeleton import KEYPOINT_NAMES

    joint_keys = list(KEYPOINT_NAMES)
    values: list[float] = []
    for name in joint_keys:
        # 단순 직립 좌표 (x, y, z, conf)
        x = 500.0
        y = 200.0
        z = 0.0
        c = 0.9
        values.extend([x, y, z, c])
    return {
        "joint_keys": tuple(joint_keys),
        "values": tuple(values),
        "frame_index": 0,
        "torso_px": 200.0,
        "confidence": 0.9,
        "measured_at": 0,
    }


# ── helper: patch _extract_video_analysis_inputs (or its inputs) ──────────


def _install_video_extract_mocks(app_mod, monkeypatch, *, pose_frames=None, profile=None):
    """RTMW + measure_body_profile + S3 + frame_extractor 박제.

    helper 호출 시 estimate / measure_body_profile call count 추적 가능.
    """
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    if pose_frames is None:
        pose_frames = _fake_pose_frames(30, conf=0.9)
    if profile is None:
        profile = _student_profile(conf=0.8)

    fake_engine = MagicMock()
    fake_engine.estimate.return_value = pose_frames

    fake_frame_extractor = MagicMock()
    fake_frame_extractor.extract.return_value = np.zeros((30, 320, 240, 3), dtype=np.uint8)

    fake_s3 = MagicMock()

    # 어댑터 강제 set (lazy 우회) — _ensure_adapters 가 None check 시 skip 하도록 모든 singleton set.
    app_mod._FRAME_EXTRACTOR = fake_frame_extractor
    app_mod._RTMW_ENGINE = fake_engine
    app_mod._POSE_ESTIMATOR = MagicMock()
    app_mod._COACH_WRITER = MagicMock()
    monkeypatch.setattr(app_mod, "_s3", fake_s3)

    def fake_measure(pfs):
        return profile

    monkeypatch.setattr(
        "sunity_shared.analysis.body_normalization_measurer.measure_body_profile",
        fake_measure,
    )
    # pipeline 이 module-level import 한 경우 박제 동기화
    if hasattr(app_mod, "measure_body_profile"):
        monkeypatch.setattr(app_mod, "measure_body_profile", fake_measure)

    return fake_engine, fake_frame_extractor, fake_s3


# ── Test 9 (R3 fix — single RTMW call) ────────────────────────────────────


def test_extract_video_analysis_inputs_runs_rtmw_exactly_once(app_mod, monkeypatch):
    """R3 fix — _extract_video_analysis_inputs 1회 호출 → RTMW estimate call count == 1.

    Gemini ON 분기에서도 keep_local_video=True 로 동일하게 1회만 호출.
    """
    fake_engine, _, _ = _install_video_extract_mocks(app_mod, monkeypatch)

    from sunity_shared.analysis.pose_frame import PoleAxis

    default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )
    inputs = app_mod._extract_video_analysis_inputs(
        "bucket", "uploads/u/a.mp4", default_pole, keep_local_video=False
    )
    assert fake_engine.estimate.call_count == 1
    assert inputs.pose_frames is not None
    assert inputs.student_profile is not None
    assert inputs.angles is not None
    assert inputs.local_video_path is None

    # Gemini ON path — keep_local_video=True 로 1회 호출 (또 1회 = 누적 2)
    fake_engine.estimate.reset_mock()
    inputs2 = app_mod._extract_video_analysis_inputs(
        "bucket", "uploads/u/a.mp4", default_pole, keep_local_video=True
    )
    assert fake_engine.estimate.call_count == 1
    assert inputs2.local_video_path is not None
    # cleanup
    Path(str(inputs2.local_video_path)).unlink(missing_ok=True)


# ── Test 10 (R3 fix — legacy helpers deleted) ─────────────────────────────


def test_legacy_helpers_not_in_pipeline_anymore(app_mod):
    """R3 fix — _angles_and_video_path_from_video + 신설 X 모두 폐기.

    grep gate 의 보완 — 실제 module attribute 부재 확인.
    """
    import inspect

    src = inspect.getsource(app_mod)
    assert "def _angles_and_video_path_from_video" not in src, (
        "R3 fix 위반 — _angles_and_video_path_from_video 폐기 안 됨"
    )
    assert "def _angles_profile_and_frames_from_video" not in src, (
        "R3 fix 위반 — _angles_profile_and_frames_from_video 신설 금지 (단일 helper 통합)"
    )
    # Phase 2 보존
    assert hasattr(app_mod, "_angles_and_body_profile_from_video"), (
        "Phase 2 helper _angles_and_body_profile_from_video 무수정 보존 위반"
    )


# ── Test 11 (R4 fix — non-null student_profile) ───────────────────────────


def test_extract_video_analysis_inputs_student_profile_never_null(app_mod, monkeypatch):
    """R4 fix — measure_body_profile 의 _fallback_profile 정합. student_profile 항상 non-null."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.pose_frame import PoleAxis

    # measure_body_profile 가 fallback path 진입 (low confidence 등) — 여전히 instance 반환
    fallback_profile = BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.0,
        warnings=["profile_measurement_failed"],
    )
    _install_video_extract_mocks(app_mod, monkeypatch, profile=fallback_profile)

    default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )
    inputs = app_mod._extract_video_analysis_inputs(
        "bucket", "uploads/u/a.mp4", default_pole, keep_local_video=False
    )
    assert inputs.student_profile is not None
    assert isinstance(inputs.student_profile, BodyNormalizationProfile)
    assert inputs.student_profile.confidence == 0.0


# ── Test 13 (R2 wiring — _extract_target_torso_px) ────────────────────────


def test_extract_target_torso_px_helper(app_mod):
    """R2 wiring — _extract_target_torso_px(pose_frames) 반환 = 평균 mid_shoulder↔mid_hip 거리.

    pose_frames 빈 / endpoint 미감지 시 None.
    """
    pose_frames = _fake_pose_frames(10, conf=0.9)
    # mid_shoulder y=100, mid_hip y=300 → distance ≈ 200
    torso_px = app_mod._extract_target_torso_px(pose_frames)
    assert torso_px is not None
    assert abs(torso_px - 200.0) < 5.0

    # 빈 list
    assert app_mod._extract_target_torso_px([]) is None


# ── 직접 _process 호출 path 박제 helpers ────────────────────────────────


def _install_firestore_mock(app_mod, monkeypatch, *, mode, ref_doc=None, prev_doc=None):
    """firestore_admin path 박제 — get_analysis / get_reference_motion / get_previous_analysis."""
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
    return fake_fs


def _install_recognizer_mock(app_mod, monkeypatch, *, motion_id=None):
    """recognizer.recognize 결과 박제."""
    from sunity_shared.analysis.technique import TechniqueProfile

    profile = TechniqueProfile(
        name=motion_id or "fallback",
        category="recognized" if motion_id else "unknown",
        joint_expectations={},
        motion_id=motion_id,
    )
    fake_rec = MagicMock()
    fake_rec.recognize.return_value = profile
    fake_rec.motion_query_hint = None
    monkeypatch.setattr(app_mod, "_RECOGNIZER", fake_rec)
    monkeypatch.setattr(app_mod, "_ensure_recognizer", lambda: fake_rec)
    return fake_rec


# ── Test 1 (mode1 full ref) ───────────────────────────────────────────────


def test_process_mode1_with_full_ref_returns_mode1_report(app_mod, monkeypatch):
    """mode1 + ref.bodyNormalizationProfile + ref.bodyComparisonSourcePose 둘 다 박제 →
    comparison_type == 'mode1' + scale_profile != None + used_reference_fallback == False.
    """
    from sunity_shared import models

    ref_doc = {
        "motionId": "inversion",
        "bodyNormalizationProfile": _ref_profile_dict(),
        "bodyComparisonSourcePose": _ref_source_pose_dict(),
        "athleteName": "정은지",
        "videoS3Key": None,
        # 기존 angles 필요 (mode1 path 가 reference DTW 사용)
        "angles": [170.0] * (30 * 8),
        "anglesJointKeys": ["left_elbow", "right_elbow", "left_shoulder",
                            "right_shoulder", "left_hip", "right_hip",
                            "left_knee", "right_knee"],
        "anglesFrames": 30,
    }
    _install_video_extract_mocks(app_mod, monkeypatch)
    fake_fs = _install_firestore_mock(app_mod, monkeypatch, mode=models.MODE_EXPERT, ref_doc=ref_doc)
    _install_recognizer_mock(app_mod, monkeypatch, motion_id="inversion")
    # complete_analysis 가 호출되도록 모든 path 통과 필요
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    # complete_analysis 가 호출되었는지 확인
    assert fake_fs.complete_analysis.called, "complete_analysis 호출 안 됨"
    call_kwargs = fake_fs.complete_analysis.call_args.kwargs
    bcr = call_kwargs.get("body_comparison_report")
    assert bcr is not None
    assert bcr["comparisonType"] == "mode1"
    assert bcr.get("scaleProfile") is not None
    assert bcr["usedReferenceFallback"] is False


# ── Test 2 (C9 canary — missing ref.bodyNormalizationProfile) ─────────────


def test_process_mode1_missing_ref_body_profile_emits_canary_warning(app_mod, monkeypatch):
    """C9 fix canary — mode1 + ref.bodyNormalizationProfile is None + ref.bodyComparisonSourcePose 박제 →
    comparisonType == 'mode1' + warnings ⊃ ['reference_profile_missing'] +
    bodyNormalizationConfidence < CONFIDENCE_GATE (0.5).
    """
    from sunity_shared import models

    ref_doc = {
        "motionId": "inversion",
        "bodyNormalizationProfile": None,  # missing!
        "bodyComparisonSourcePose": _ref_source_pose_dict(),
        "athleteName": "정은지",
        "angles": [170.0] * (30 * 8),
        "anglesJointKeys": ["left_elbow", "right_elbow", "left_shoulder",
                            "right_shoulder", "left_hip", "right_hip",
                            "left_knee", "right_knee"],
        "anglesFrames": 30,
    }
    # student confidence 낮음 + reference None → confidence 산식이 가속화
    student = _student_profile(conf=0.3)
    _install_video_extract_mocks(app_mod, monkeypatch, profile=student)
    fake_fs = _install_firestore_mock(app_mod, monkeypatch, mode=models.MODE_EXPERT, ref_doc=ref_doc)
    _install_recognizer_mock(app_mod, monkeypatch, motion_id="inversion")
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] == "mode1"
    assert "reference_profile_missing" in bcr["warnings"], bcr["warnings"]
    assert bcr["bodyNormalizationConfidence"] < 0.5


# ── Test 3 (R2 canary — missing ref.bodyComparisonSourcePose) ─────────────


def test_process_mode1_missing_ref_source_pose_emits_canary_warning(app_mod, monkeypatch):
    """R2 wiring 신규 canary — mode1 + ref.bodyNormalizationProfile 박제 + ref.bodyComparisonSourcePose is None →
    comparisonType == 'mode1' + warnings ⊃ ['reference_source_pose_missing'] + scale_profile is None.
    """
    from sunity_shared import models

    ref_doc = {
        "motionId": "inversion",
        "bodyNormalizationProfile": _ref_profile_dict(),
        "bodyComparisonSourcePose": None,  # missing!
        "athleteName": "정은지",
        "angles": [170.0] * (30 * 8),
        "anglesJointKeys": ["left_elbow", "right_elbow", "left_shoulder",
                            "right_shoulder", "left_hip", "right_hip",
                            "left_knee", "right_knee"],
        "anglesFrames": 30,
    }
    _install_video_extract_mocks(app_mod, monkeypatch)
    fake_fs = _install_firestore_mock(app_mod, monkeypatch, mode=models.MODE_EXPERT, ref_doc=ref_doc)
    _install_recognizer_mock(app_mod, monkeypatch, motion_id="inversion")
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] == "mode1"
    assert "reference_source_pose_missing" in bcr["warnings"], bcr["warnings"]
    assert bcr.get("scaleProfile") is None


# ── Test 4 (R2 wiring — fetch both profile + source_pose) ─────────────────


def test_process_mode1_fetches_both_profile_and_source_pose(app_mod, monkeypatch):
    """R2 + R8 wiring — mode1 path 가 reference doc 의 bodyNormalizationProfile + bodyComparisonSourcePose 둘 다 read.

    compare_body_profiles 의 source_keypoints arg 가 ndarray (to_keypoints_array 결과).
    """
    from sunity_shared import models
    from sunity_shared.analysis import body_normalizer as bn_mod

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
    _install_video_extract_mocks(app_mod, monkeypatch)
    fake_fs = _install_firestore_mock(app_mod, monkeypatch, mode=models.MODE_EXPERT, ref_doc=ref_doc)
    _install_recognizer_mock(app_mod, monkeypatch, motion_id="inversion")
    # compare_body_profiles spy
    real_compare = bn_mod.compare_body_profiles
    call_args_capture = {}

    def spy(*args, **kwargs):
        call_args_capture["kwargs"] = kwargs
        return real_compare(*args, **kwargs)

    monkeypatch.setattr(bn_mod, "compare_body_profiles", spy)
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    captured = call_args_capture.get("kwargs", {})
    sk = captured.get("source_keypoints")
    assert sk is not None, "source_keypoints 인자 미전달 — R2 wiring 위반"
    # ndarray (J, 4) 모양
    assert isinstance(sk, np.ndarray)
    assert sk.shape == (17, 4)


# ── Test 5 (mode3 first, no Gemini, no fallback) ──────────────────────────


def test_process_mode3_first_no_prev_no_gemini_match_returns_mode3_first(app_mod, monkeypatch):
    """mode3 + prev=None + profile.motion_id is None →
    comparison_type == 'mode3_first' + scale_profile is None + used_reference_fallback == False.
    """
    from sunity_shared import models

    _install_video_extract_mocks(app_mod, monkeypatch)
    fake_fs = _install_firestore_mock(app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None)
    _install_recognizer_mock(app_mod, monkeypatch, motion_id=None)
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] == "mode3_first"
    assert bcr.get("scaleProfile") is None
    assert bcr["usedReferenceFallback"] is False


# ── Test 6 (C2 + W1 + R2 — mode3_first with Gemini fallback match) ────────


def test_process_mode3_first_with_gemini_fallback_exact_match_and_source_pose(app_mod, monkeypatch):
    """C2 + W1 + R2 — mode3 + prev=None + Gemini matched (motion_id="inversion") +
    matched ref (둘 다 박제) + confidence >= 0.5 →
    comparison_type == 'mode3_first' + scale_profile != None + used_reference_fallback == True.
    """
    from sunity_shared import models

    matched_ref = {
        "motionId": "inversion",
        "bodyNormalizationProfile": _ref_profile_dict(),
        "bodyComparisonSourcePose": _ref_source_pose_dict(),
    }
    _install_video_extract_mocks(app_mod, monkeypatch)
    fake_fs = _install_firestore_mock(app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None)
    fake_fs.get_reference_motion.return_value = matched_ref  # exact-match
    _install_recognizer_mock(app_mod, monkeypatch, motion_id="inversion")
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] == "mode3_first"
    assert bcr.get("scaleProfile") is not None
    assert bcr["usedReferenceFallback"] is True


# ── Test 7 (C2 + R8 — extra_warnings, no dataclasses.replace) ─────────────


def test_process_mode3_first_gemini_motion_id_missing_uses_extra_warnings(app_mod, monkeypatch):
    """C2 + R8 — mode3 + prev=None + Gemini matched (motion_id="obscure") +
    get_reference_motion(motion_id) returns None →
    extra_warnings=['fallback_reference_not_found'] injection 으로 wiring.
    """
    from sunity_shared import models

    _install_video_extract_mocks(app_mod, monkeypatch)
    fake_fs = _install_firestore_mock(app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None)
    fake_fs.get_reference_motion.return_value = None  # exact-match 실패
    _install_recognizer_mock(app_mod, monkeypatch, motion_id="obscure")
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert "fallback_reference_not_found" in bcr["warnings"], bcr["warnings"]

    # R8 grep gate — pipeline 모듈 src 에 dataclasses.replace + BodyComparisonReport 패턴 부재
    import inspect

    src = inspect.getsource(app_mod)
    assert "dataclasses.replace" not in src or "body_comparison_report" not in src.split("dataclasses.replace")[1].split("\n")[0], (
        "R8 위반 — dataclasses.replace(body_comparison_report=...) 우회 패턴 발견"
    )


# ── Test 8 (mode3 progress) ────────────────────────────────────────────────


def test_process_mode3_progress_with_prev_body_profile(app_mod, monkeypatch):
    """mode3 + prev.bodyNormalizationProfile 박제 →
    comparison_type == 'mode3_progress' + previous_analysis_id != None + used_reference_fallback == False.
    """
    from sunity_shared import models

    prev_doc = {
        "analysisId": "prevA",
        "angles": [170.0] * (30 * 8),
        "anglesJointKeys": ["left_elbow", "right_elbow", "left_shoulder",
                            "right_shoulder", "left_hip", "right_hip",
                            "left_knee", "right_knee"],
        "anglesFrames": 30,
        "bodyNormalizationProfile": _ref_profile_dict(),
        "bodyComparisonSourcePose": _ref_source_pose_dict(),
        "result": {"dimensionScores": {"line": 60, "stability": 65}},
    }
    _install_video_extract_mocks(app_mod, monkeypatch)
    fake_fs = _install_firestore_mock(app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=prev_doc)
    _install_recognizer_mock(app_mod, monkeypatch, motion_id=None)
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] == "mode3_progress"
    assert bcr.get("previousAnalysisId") == "prevA"
    assert bcr["usedReferenceFallback"] is False


# ── Test 12 (B2 — unstable arm swing lowers confidence) ───────────────────


def test_unstable_arm_swing_lowers_production_confidence(app_mod, monkeypatch):
    """B2 production path — unstable arm swing pose_frames 시 bodyNormalizationConfidence < 0.5.

    fixture_unstable_arm_swing 합성 데이터의 동등한 high-variance pose_frames 박제.
    """
    from sunity_shared import models
    from sunity_shared.analysis.pose_frame import Keypoint3D, Keypoint3DAligned, PoleAxis, PoseFrame

    # high-variance pose_frames — 매 frame 마다 wrist 좌표 변동.
    unstable_frames = []
    for i in range(30):
        wobble = (i % 2 - 0.5) * 200  # +- 100 px wobble in forearm
        kp = {
            "left_shoulder": Keypoint3D(x=430.0, y=100.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "right_shoulder": Keypoint3D(x=570.0, y=100.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "left_elbow": Keypoint3D(x=430.0 + wobble, y=220.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "right_elbow": Keypoint3D(x=570.0 + wobble, y=220.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "left_wrist": Keypoint3D(x=430.0 + wobble * 2, y=330.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "right_wrist": Keypoint3D(x=570.0 + wobble * 2, y=330.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "left_hip": Keypoint3D(x=450.0, y=300.0 + wobble, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "right_hip": Keypoint3D(x=550.0, y=300.0 + wobble, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "left_knee": Keypoint3D(x=450.0, y=480.0 + wobble * 2, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "right_knee": Keypoint3D(x=550.0, y=480.0 + wobble * 2, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "left_ankle": Keypoint3D(x=450.0, y=640.0 + wobble * 3, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
            "right_ankle": Keypoint3D(x=550.0, y=640.0 + wobble * 3, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        }
        aligned = {n: Keypoint3DAligned(x=v.x, y=v.y, z=v.z) for n, v in kp.items()}
        unstable_frames.append(PoseFrame(
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

    student = _student_profile(conf=0.6)
    _install_video_extract_mocks(app_mod, monkeypatch, pose_frames=unstable_frames, profile=student)
    fake_fs = _install_firestore_mock(app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None)
    _install_recognizer_mock(app_mod, monkeypatch, motion_id=None)
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["bodyNormalizationConfidence"] < 0.5, (
        f"unstable swing 시 confidence 하향 검증 실패: {bcr['bodyNormalizationConfidence']}"
    )
