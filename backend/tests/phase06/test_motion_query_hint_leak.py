"""WR-07 regression — motion hint 가 분석 간 leak/오염되지 않는다.

박제 정신 (WR-07 / 2026-06-08 review):
  - _RECOGNIZER 는 module-global singleton — SQS 메시지 간 / BackgroundTask 간 공유.
  - mode1 분석이 hint="ref-foxtop" 를 박은 뒤 mode3 분석이 그 값을 상속하면
    Gemini 가 mode3 의 student 영상을 foxtop 으로 biased 하게 본다.

계약 변경 (2026-09-20, 동시 분석 오염 수리):
  - WR-07 의 원래 fix 는 "모든 _process 진입 시 싱글턴 속성 `motion_query_hint` 를
    명시적으로 set/None" 이었다. 이 fix 는 **직렬** leak 만 막는다.
  - rebind(진입 직후)와 소비(recognize) 사이에 프레임 추출 + RTMW 추론이 통째로
    끼어 있다(실측 warm 51.3초 / cold 176.6초). 동시 분석이면 그 창에서 다른 분석이
    속성을 덮어쓴다 — 예외도 로그도 없이 **남의 동작 이름으로 채점**된다.
    Pod 은 `--workers 1` + BackgroundTasks(스레드풀), Lambda 는
    ReservedConcurrentExecutions 가 없으므로 학원 동시 업로드에서 실제로 열리는 창이다.
  - 그래서 속성 자체를 폐기했다. `GeminiTechniqueRecognizer.motion_query_hint` 는
    삭제됐고(대입 시 AttributeError), 값은 `recognize(..., motion_hint=...)` 키워드
    인자로만 흐른다 — 호출 스택을 벗어나지 않으므로 직렬 leak 도 동시 오염도
    구조적으로 불가능하다.
  - 따라서 이 회귀의 검증 지점은 "_process 뒤 속성값" 이 아니라
    "**recognize 호출이 받은 motion_hint**" 다. 의도는 그대로, 표현만 바뀐다.
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


def _make_recognizer():
    """spec_set 싱글턴 대역 — Protocol 밖 속성 대입을 즉시 터뜨린다.

    운영 recognizer(`GeminiTechniqueRecognizer`)는 2026-09-20 수리로 생성 후
    속성 대입이 AttributeError 다(`__post_init__` 의 `_frozen=True`). 대역도 같은
    성질을 갖게 해서, 파이프라인이 다시 `recognizer.motion_query_hint = ...` 같은
    싱글턴 속성 rebind 로 회귀하면 이 테스트가 통과할 수 없게 만든다.
    """
    from sunity_shared.analysis.technique import TechniqueRecognizer

    return MagicMock(spec_set=TechniqueRecognizer)


def _ref_doc(motion_id: str) -> dict:
    from sunity_shared.analysis.skeleton import KEYPOINT_NAMES

    return {
        "motionId": motion_id,
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


def _profile(name: str, motion_id: str | None):
    from sunity_shared.analysis.technique import TechniqueProfile

    return TechniqueProfile(
        name=name,
        category="recognized" if motion_id else "unknown",
        joint_expectations={},
        motion_id=motion_id,
    )


def _hint_of(call) -> str | None:
    """recognize 호출이 받은 motion_hint — 키워드 인자로만 받는 계약(kw-only)."""
    assert "motion_hint" in call.kwargs, (
        f"recognize 가 motion_hint 를 키워드로 받지 않았다 — kwargs={sorted(call.kwargs)}"
    )
    return call.kwargs["motion_hint"]


def test_motion_query_hint_reset_to_none_for_mode3(app_mod, monkeypatch):
    """WR-07 — mode1 분석 직후 같은 싱글턴으로 mode3 분석을 돌려도 hint=None.

    leak 방지 — Gemini 가 mode3 의 student 영상을 이전 mode1 의 motion 으로 biased X.
    2026-09-20 계약: 검증 지점은 싱글턴 속성이 아니라 recognize 가 받은 인자다.
    """
    from sunity_shared import models

    rec = _make_recognizer()
    _setup_minimal_mocks(app_mod, monkeypatch, rec)

    fake_fs = MagicMock()
    # mode1(ref-foxtop) → mode3 순서. 같은 recognizer 인스턴스를 연달아 쓴다.
    fake_fs.get_analysis.side_effect = [
        {"mode": models.MODE_EXPERT, "referenceMotionId": "ref-foxtop", "analysisId": "a1"},
        {"mode": models.MODE_SELF, "referenceMotionId": None, "analysisId": "a2"},
    ]
    fake_fs.get_reference_motion.side_effect = (
        lambda motion_id: _ref_doc(motion_id) if motion_id else None
    )
    fake_fs.get_previous_analysis.return_value = None
    fake_fs.update_analysis_status = MagicMock()
    fake_fs.complete_analysis = MagicMock()
    fake_fs.fail_analysis = MagicMock()
    fake_fs.record_unregistered_keyword = MagicMock()
    monkeypatch.setattr(app_mod, "firestore_admin", fake_fs)

    # 1) 앞선 mode1 분석 — hint 오염원을 실제로 만든다.
    rec.recognize.return_value = _profile("ref-foxtop", "ref-foxtop")
    app_mod._process("bucket", "uploads/u/a1.mp4", "user-x", "a1")
    assert _hint_of(rec.recognize.call_args) == "ref-foxtop", "선행 mode1 오염원 준비 실패"

    # 2) 뒤따르는 mode3 분석 — 앞 분석이 무엇이었든 hint 는 None 이어야 한다.
    rec.recognize.return_value = _profile("fallback", None)
    app_mod._process("bucket", "uploads/u/a2.mp4", "user-x", "a2")

    leaked = _hint_of(rec.recognize.call_args)
    assert leaked is None, (
        f"WR-07 위반 — mode3 분석의 recognize 가 motion_hint={leaked!r} 를 받았다. "
        "None 이어야 함 (앞 mode1 분석의 hint 상속 금지)."
    )
    assert rec.recognize.call_count == 2


def test_motion_query_hint_set_to_motion_id_for_mode_expert(app_mod, monkeypatch):
    """WR-07 정합 — mode1 (expert) 분석의 recognize 는 hint=referenceMotionId."""
    from sunity_shared import models

    rec = _make_recognizer()
    rec.recognize.return_value = _profile("inversion", "inversion")
    _setup_minimal_mocks(app_mod, monkeypatch, rec)

    fake_fs = MagicMock()
    fake_fs.get_analysis.return_value = {
        "mode": models.MODE_EXPERT, "referenceMotionId": "inversion", "analysisId": "a1",
    }
    fake_fs.get_reference_motion.side_effect = (
        lambda motion_id: _ref_doc(motion_id) if motion_id else None
    )
    fake_fs.update_analysis_status = MagicMock()
    fake_fs.complete_analysis = MagicMock()
    fake_fs.fail_analysis = MagicMock()
    fake_fs.record_unregistered_keyword = MagicMock()
    monkeypatch.setattr(app_mod, "firestore_admin", fake_fs)

    app_mod._process("bucket", "uploads/u/a1.mp4", "user-x", "a1")

    assert _hint_of(rec.recognize.call_args) == "inversion"
