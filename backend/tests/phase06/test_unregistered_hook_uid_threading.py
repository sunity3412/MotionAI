"""WR-03 regression — pipeline 의 unregistered_hook 이 실제 caller uid 를 물고 recognize 에 도달.

박제 정신 (WR-03 / 2026-06-08 review):
  - _ensure_recognizer 의 default hook 은 cache 생성 시점에 uid 미상이라
    "anonymous-pipeline" 박힘. 그대로 두면 term_collection.unique_users 가 single-
    element set 으로 수렴 → Phase 16 TERM-DATA-01 promotion 임계 무력화.
  - _process 진입 시점에는 caller uid 가 함수 파라미터로 알려져 있음. 본 fix 는
    uid 를 문 closure 를 만들어 실제 uid 가 record_unregistered_keyword 에 전달.

전달 경로 변경 (2026-09-20 동시 분석 오염 수리):
  종전에는 그 closure 를 전역 싱글턴 recognizer 의 `unregistered_hook` **속성에 대입**
  했다. 대입과 소비(recognize) 사이에 프레임 추출 + RTMW 추론(51~177초)이 끼어 있어
  동시 분석이면 그 창에서 B 의 closure 가 A 의 것을 덮어썼다 — 미등록 용어 원장에
  **다른 학생의 uid** 가 찍히고 예외도 로그도 안 남는다. 지금은 속성 대입 없이
  `recognize(unregistered_hook=...)` 키워드 인자로 넘긴다(값이 호출 스택을 벗어나지
  않음). WR-03 의 의도는 그대로 — 검증 지점만 "속성이 바뀌었나"에서
  "recognize 에 넘어간 hook 이 실제 uid 를 물고 있나"로 옮긴다.
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


def test_process_rebinds_unregistered_hook_with_real_uid(app_mod, monkeypatch):
    """WR-03 — _process 가 caller uid 를 문 hook 을 recognize() 에 넘긴다.

    2026-09-20 이전에는 `recognizer.unregistered_hook` 속성 대입을 봤다. 지금은
    인자 전달이므로 recognize 의 call kwargs 를 본다 — 같은 의도, 더 강한 검증
    (넘어간 hook 을 실제로 호출해서 uid 가 firestore 까지 닿는지까지 본다).
    """
    from sunity_shared import models
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.technique import TechniqueProfile

    # adapter 박제
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

    # recognizer 박제 (Gemini path). unregistered_hook 은 **합성 시점 기본값** 자리에
    # 그대로 남아 있다 (_ensure_recognizer 의 uid="anonymous-pipeline" default 대역).
    # motion_query_hint 는 2026-09-20 에 필드 자체가 폐기 — 여기서도 세우지 않는다.
    initial_hook_called_with = {}
    def _initial_hook(keyword, video_hash):
        initial_hook_called_with["uid"] = "anonymous-pipeline"
    rec = MagicMock()
    rec.unregistered_hook = _initial_hook
    rec.recognize.return_value = TechniqueProfile(
        name="fallback", category="unknown", joint_expectations={}, motion_id=None,
    )
    monkeypatch.setattr(app_mod, "_RECOGNIZER", rec)
    monkeypatch.setattr(app_mod, "_ensure_recognizer", lambda: rec)

    # firestore 박제
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

    # 실 caller uid = "user-42"
    app_mod._process("bucket", "uploads/u/a1.mp4", "user-42", "a1")

    # 전달 검증 — recognize() 가 unregistered_hook 을 **키워드 인자로** 받았고,
    # 그 hook 이 합성 시점 기본값(anonymous-pipeline)이 아니다.
    assert rec.recognize.call_count == 1, "recognize 호출 1회 박제"
    passed_hook = rec.recognize.call_args.kwargs.get("unregistered_hook")
    assert passed_hook is not None, (
        "_process 가 recognize 에 unregistered_hook 을 안 넘김 — WR-03 회귀"
    )
    assert passed_hook is not _initial_hook, (
        "_process 가 합성 시점 기본 hook(anonymous-pipeline)을 그대로 넘김 — WR-03 회귀"
    )

    # 넘어간 hook 호출 시 실 caller uid 로 record_unregistered_keyword.
    passed_hook("test-keyword", "vidhash-123")
    fake_fs.record_unregistered_keyword.assert_called_once_with(
        "test-keyword", uid="user-42", video_hash="vidhash-123"
    )

    # 속성 오염 부재 — 2026-09-20 수리의 핵심. 전역 싱글턴 recognizer 의 속성은
    # 분석 전후로 그대로여야 한다 (동시 분석이 서로의 uid 를 덮어쓸 창 0).
    assert rec.unregistered_hook is _initial_hook, (
        "_process 가 전역 recognizer 속성을 다시 오염시킴 — 동시 분석 오염 재발"
    )


def test_pipeline_source_does_not_call_record_with_anonymous_pipeline_in_process(app_mod):
    """WR-03 grep gate — _process 함수 본문이 'anonymous-pipeline' uid 로
    record_unregistered_keyword 직접 호출하지 않음. (코멘트 안에서 default 라고
    설명은 가능 — 실 호출은 closure rebind 뒤로.)"""
    import inspect
    import re

    src = inspect.getsource(app_mod._process)
    # `uid="anonymous-pipeline"` 같은 kwarg 패턴 부재.
    pattern = re.compile(r'uid\s*=\s*["\']anonymous-pipeline["\']')
    assert not pattern.search(src), (
        "WR-03 위반 — _process 가 'anonymous-pipeline' uid 로 호출 — closure rebind 안 함"
    )
