"""Task 4 — Phase 6 전체 통합 smoke test.

박제 정신:
  - End-to-end _process → mock Firestore → bodyComparisonReport 검증.
  - must_haves.truths 박제 정합.
  - C9 + R2 신규 canary 통합 smoke.
  - C14 (pose_reliability_low) deficit code grep gate.
  - R3 (RTMW estimate 1회) + R4 (student_profile non-null) 통합 smoke.

mock-based — RTMW / S3 / Firestore 실 호출 0.
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


def _student_profile(conf=0.8):
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


def _fallback_profile():
    """measure_body_profile fallback path 정합 — R4 fix non-null 검증용."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    return BodyNormalizationProfile(
        estimated_height_scale=1.0,
        arm_scale=1.0,
        leg_scale=1.0,
        torso_scale=1.0,
        shoulder_hip_ratio=1.0,
        confidence=0.0,
        warnings=["insufficient_frames"],
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


def _fake_pose_frames(n=30, conf=0.9, low_conf_ratio=0.0):
    """합성 PoseFrame list — low_conf_ratio > 0 시 일부 frame 의 keypoint confidence 낮춤."""
    from sunity_shared.analysis.pose_frame import (
        Keypoint3D,
        Keypoint3DAligned,
        PoleAxis,
        PoseFrame,
    )

    frames = []
    low_conf_count = int(n * low_conf_ratio)
    for i in range(n):
        c = 0.3 if i < low_conf_count else conf
        kp = {
            "left_shoulder": Keypoint3D(x=430.0, y=100.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "right_shoulder": Keypoint3D(x=570.0, y=100.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "left_elbow": Keypoint3D(x=430.0, y=220.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "right_elbow": Keypoint3D(x=570.0, y=220.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "left_wrist": Keypoint3D(x=430.0, y=330.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "right_wrist": Keypoint3D(x=570.0, y=330.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "left_hip": Keypoint3D(x=450.0, y=300.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "right_hip": Keypoint3D(x=550.0, y=300.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "left_knee": Keypoint3D(x=450.0, y=480.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "right_knee": Keypoint3D(x=550.0, y=480.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "left_ankle": Keypoint3D(x=450.0, y=640.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
            "right_ankle": Keypoint3D(x=550.0, y=640.0, z=0.0, confidence=c, uncertainty_proxy=1 - c),
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


def _install_e2e_mocks(
    app_mod,
    monkeypatch,
    *,
    mode,
    ref_doc=None,
    prev_doc=None,
    motion_id=None,
    student_profile=None,
    pose_frames=None,
):
    from sunity_shared.analysis.technique import TechniqueProfile

    if student_profile is None:
        student_profile = _student_profile()
    if pose_frames is None:
        pose_frames = _fake_pose_frames()

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
        lambda pfs: student_profile,
    )
    monkeypatch.setattr(app_mod, "measure_body_profile", lambda pfs: student_profile)

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
        name=motion_id or "fallback",
        category="recognized" if motion_id else "unknown",
        joint_expectations={},
        motion_id=motion_id,
    )
    fake_rec = MagicMock()
    fake_rec.recognize.return_value = tp
    fake_rec.motion_query_hint = None
    monkeypatch.setattr(app_mod, "_RECOGNIZER", fake_rec)
    monkeypatch.setattr(app_mod, "_ensure_recognizer", lambda: fake_rec)
    return fake_fs, fake_engine


def test_full_pipeline_mode1_smoke(app_mod, monkeypatch):
    """End-to-end mode1 — bodyComparisonReport.comparisonType == 'mode1' + scaleProfile != None +
    findings + bodyNormalizationConfidence > 0 + usedReferenceFallback == False.
    """
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
    fake_fs, _ = _install_e2e_mocks(
        app_mod, monkeypatch, mode=models.MODE_EXPERT, ref_doc=ref_doc, motion_id="inversion"
    )
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] == "mode1"
    assert bcr.get("scaleProfile") is not None
    assert bcr["bodyNormalizationConfidence"] > 0
    assert bcr["usedReferenceFallback"] is False


def test_full_pipeline_mode3_first_no_fallback_smoke(app_mod, monkeypatch):
    """Gemini OFF → comparisonType == 'mode3_first' + scaleProfile is None + usedReferenceFallback == False
    + warnings ⊃ 'low_confidence_normalization_off' (reference 없음).
    """
    from sunity_shared import models

    fake_fs, _ = _install_e2e_mocks(
        app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None, motion_id=None
    )
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] == "mode3_first"
    assert bcr.get("scaleProfile") is None
    assert bcr["usedReferenceFallback"] is False
    assert "low_confidence_normalization_off" in bcr["warnings"]


def test_full_pipeline_mode3_first_with_gemini_fallback_smoke(app_mod, monkeypatch):
    """C2 + W1 + R2 — Gemini matched + matched ref 박제 (둘 다) →
    comparisonType == 'mode3_first' + scaleProfile != None + usedReferenceFallback == True.
    """
    from sunity_shared import models

    matched_ref = {
        "motionId": "inversion",
        "bodyNormalizationProfile": _ref_profile_dict(),
        "bodyComparisonSourcePose": _ref_source_pose_dict(),
    }
    fake_fs, _ = _install_e2e_mocks(
        app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None, motion_id="inversion"
    )
    # mode3 path 가 get_reference_motion 호출 시 matched_ref 반환.
    fake_fs.get_reference_motion.return_value = matched_ref
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] == "mode3_first"
    assert bcr.get("scaleProfile") is not None
    assert bcr["usedReferenceFallback"] is True


def test_full_pipeline_mode3_first_with_gemini_motion_id_no_ref_match_smoke(app_mod, monkeypatch):
    """C2 + R8 — Gemini matched + get_reference_motion 반환 None →
    comparisonType == 'mode3_first' + usedReferenceFallback == False + warnings ⊃ "fallback_reference_not_found".
    """
    from sunity_shared import models

    fake_fs, _ = _install_e2e_mocks(
        app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None, motion_id="obscure"
    )
    fake_fs.get_reference_motion.return_value = None  # exact-match fail
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] == "mode3_first"
    assert bcr["usedReferenceFallback"] is False
    assert "fallback_reference_not_found" in bcr["warnings"]


def test_full_pipeline_mode1_ref_source_pose_missing_smoke(app_mod, monkeypatch):
    """R2 canary — mode1 + ref.bodyNormalizationProfile 박제 + ref.bodyComparisonSourcePose is None →
    warnings ⊃ "reference_source_pose_missing" + scaleProfile is None.
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
    fake_fs, _ = _install_e2e_mocks(
        app_mod, monkeypatch, mode=models.MODE_EXPERT, ref_doc=ref_doc, motion_id="inversion"
    )
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert "reference_source_pose_missing" in bcr["warnings"]
    assert bcr.get("scaleProfile") is None


def test_full_pipeline_rtmw_estimate_call_count_is_one_smoke(app_mod, monkeypatch):
    """R3 — Gemini ON path 전체 실행에서 RTMW estimate 호출 카운트 == 1.

    회귀 차단 — double RTMW 호출이 발생하면 GPU 자원 낭비 + 결과 비일관성.
    """
    from sunity_shared import models

    # Gemini ON env
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    app_mod = _import_pipeline()  # env 반영 위해 reload
    fake_fs, fake_engine = _install_e2e_mocks(
        app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None, motion_id="inversion"
    )
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    assert fake_engine.estimate.call_count == 1, (
        f"R3 회귀 — RTMW estimate 호출 카운트 {fake_engine.estimate.call_count} (1 박제 위반)"
    )


def test_full_pipeline_student_profile_non_null_smoke(app_mod, monkeypatch):
    """R4 — measure_body_profile fallback path 트리거 → student_profile 이 BodyNormalizationProfile
    인스턴스로 흘러감 (None 분기 발생 안 함).
    """
    from sunity_shared import models

    # fallback profile (confidence=0.0 + warnings 박제) 가 흐름 전체에 흘러야 함.
    fb_profile = _fallback_profile()
    fake_fs, _ = _install_e2e_mocks(
        app_mod,
        monkeypatch,
        mode=models.MODE_SELF,
        prev_doc=None,
        motion_id=None,
        student_profile=fb_profile,
    )
    # crash 0 박제 — None 분기 발생 시 .confidence 접근 AttributeError 발생.
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bnp = fake_fs.complete_analysis.call_args.kwargs["body_normalization_profile"]
    assert bnp is not None  # R4 fix 정합
    assert bnp["confidence"] == 0.0


def test_full_pipeline_all_must_haves_emitted(app_mod, monkeypatch):
    """must_haves.truths 박제 통합 검증.

    1. comparisonType 3 cases 만 emit.
    2. usedReferenceFallback default False.
    3. warnings 모두 BODY_COMPARISON_WARNING_CODES 내.
    """
    from sunity_shared import models
    from sunity_shared.analysis.body_normalizer import BODY_COMPARISON_WARNING_CODES

    fake_fs, _ = _install_e2e_mocks(
        app_mod, monkeypatch, mode=models.MODE_SELF, prev_doc=None, motion_id=None
    )
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    assert bcr["comparisonType"] in ("mode1", "mode3_first", "mode3_progress")
    assert isinstance(bcr["usedReferenceFallback"], bool)
    for w in bcr["warnings"]:
        assert w in BODY_COMPARISON_WARNING_CODES, (
            f"warnings element '{w}' 가 frozenset 외 — R8 검증 위반"
        )


def test_pose_reliability_low_deficit_code_in_findings(app_mod, monkeypatch):
    """C14 — 불안정 pose_frames (low confidence frames > 50%) → findings 중 pose_reliability_low 발견.

    `bad_angle` literal 부재 박제 (C14 grep gate).
    """
    from sunity_shared import models

    low_conf_frames = _fake_pose_frames(n=30, conf=0.9, low_conf_ratio=0.7)  # 70% low conf
    fake_fs, _ = _install_e2e_mocks(
        app_mod,
        monkeypatch,
        mode=models.MODE_SELF,
        prev_doc=None,
        motion_id=None,
        pose_frames=low_conf_frames,
    )
    app_mod._process("bucket", "uploads/u/a1.mp4", "u", "a1")
    bcr = fake_fs.complete_analysis.call_args.kwargs["body_comparison_report"]
    deficit_codes = [f["deficitCode"] for f in bcr.get("findings", [])]
    assert "pose_reliability_low" in deficit_codes, (
        f"C14 위반 — pose_reliability_low deficit 미발견. findings={deficit_codes}"
    )
    assert "bad_angle" not in deficit_codes, (
        "C14 위반 — bad_angle deficit_code 발견 (이미 pose_reliability_low 로 rename 박제)"
    )


# ─────────────── C14 final grep gate ───────────────


def test_c14_no_bad_angle_literal_in_phase06_files():
    """C14 final grep gate — Phase 6 production path 의 `bad_angle` literal 부재."""
    import re

    repo_root = Path(__file__).resolve().parents[3]
    targets = [
        repo_root / "backend" / "functions" / "pipeline" / "app.py",
        repo_root / "backend" / "shared" / "python" / "sunity_shared" / "analysis" / "body_normalizer.py",
        repo_root / "backend" / "shared" / "python" / "sunity_shared" / "firestore_admin.py",
        repo_root / "app" / "src" / "types" / "analysis.ts",
        repo_root / "app" / "src" / "lib" / "userAnalyses.ts",
    ]
    pattern = re.compile(r'"bad_angle"')
    for p in targets:
        src = p.read_text(encoding="utf-8")
        # comment 라인 제외
        for line in src.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            assert not pattern.search(line), (
                f"C14 위반 — {p.name} 에서 `bad_angle` literal 발견: {line!r}"
            )


# ─────────────── C15 SAM artifact 검증 (optional smoke) ───────────────


def test_c15_sam_build_artifacts_documented():
    """C15 — SAM Lambda Layer artifact 5종 박제 (build smoke 는 sam build --use-container 박제).

    본 test 는 src 파일 존재 박제만. 실 SAM build 는 별도 CLI 단계.
    """
    repo_root = Path(__file__).resolve().parents[3]
    layer_src = repo_root / "backend" / "shared" / "python" / "sunity_shared"
    targets = [
        layer_src / "analysis" / "body_normalizer.py",
        layer_src / "analysis" / "body_normalization.py",
        layer_src / "analysis" / "body_normalization_measurer.py",
        layer_src / "analysis" / "technique.py",
        layer_src / "firestore_admin.py",
    ]
    for p in targets:
        assert p.is_file(), f"C15 박제 위반 — Layer src 미존재: {p}"
