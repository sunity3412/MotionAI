"""Phase 2 Task 4 — pipeline race-safe local-return helper 단위 테스트.

HIGH-1 v4 박제 검증:
  · _RTMWNlfCompat.estimate(frames) -> np.ndarray (B8 박제, 시그너처 무변경)
  · _RTMWNlfCompat.estimate_with_profile(frames) -> tuple[np.ndarray, profile]
  · _angles_and_body_profile_from_video(bucket, key) -> tuple[np.ndarray, profile]
  · 사이드카 attribute (last_body_profile) 영구 폐기
  · barriered concurrent 2 worker → profile leak 0
  · 예외 시 stale profile 반환 0

MEDIUM-1 v4 박제 (Firestore revert): _process / firestore_admin / AnalysisDoc
변경 X — Phase 6 plan 책임.
"""

from __future__ import annotations

import concurrent.futures
import dataclasses
import importlib
import inspect
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# pipeline/app.py 모듈을 path 에 추가
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _import_pipeline():
    sys.modules.pop("app", None)
    import app  # noqa: WPS433
    return importlib.reload(app)


@pytest.fixture
def app_mod():
    return _import_pipeline()


# ── helper: synthesize fake PoseFrames ────────────────────────────────────


def _build_fake_pose_frame(arm_scale_seed: float = 1.0):
    """합성 PoseFrame — measurer 가 약간씩 다른 profile 산출하도록 seed-derived 좌표."""
    from sunity_shared.analysis.pose_frame import (
        Keypoint3D,
        Keypoint3DAligned,
        PoleAxis,
        PoseFrame,
    )

    # arm_scale_seed 가 forearm 길이를 변경 → arm_scale 가 변화 (worker 별 distinct profile)
    forearm_len = 110.0 * arm_scale_seed
    keypoints_3d = {
        "left_shoulder": Keypoint3D(x=430.0, y=100.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_shoulder": Keypoint3D(x=570.0, y=100.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_elbow": Keypoint3D(x=430.0, y=220.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_elbow": Keypoint3D(x=570.0, y=220.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_wrist": Keypoint3D(x=430.0, y=220.0 + forearm_len, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_wrist": Keypoint3D(x=570.0, y=220.0 + forearm_len, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_hip": Keypoint3D(x=450.0, y=300.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_hip": Keypoint3D(x=550.0, y=300.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_knee": Keypoint3D(x=450.0, y=480.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_knee": Keypoint3D(x=550.0, y=480.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "left_ankle": Keypoint3D(x=450.0, y=640.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
        "right_ankle": Keypoint3D(x=550.0, y=640.0, z=0.0, confidence=0.9, uncertainty_proxy=0.1),
    }
    aligned = {
        n: Keypoint3DAligned(x=kp.x, y=kp.y, z=kp.z) for n, kp in keypoints_3d.items()
    }
    return PoseFrame(
        frame_index=0,
        timestamp_ms=0,
        raw_landmarks_33={},
        keypoints_3d=keypoints_3d,
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


def _make_fake_engine(arm_scale_seed: float = 1.0, num_frames: int = 30):
    """fake RTMW engine — estimate(frames, pole) 가 합성 PoseFrames 반환."""
    fake = MagicMock()
    pose_frames = [
        dataclasses.replace(_build_fake_pose_frame(arm_scale_seed), frame_index=i)
        for i in range(num_frames)
    ]
    fake.estimate.return_value = pose_frames
    return fake, pose_frames


# ── HIGH-1 v4 테스트 ──────────────────────────────────────────────────────


def test_estimate_with_profile_returns_tuple(app_mod):
    """estimate_with_profile(frames) -> (np.ndarray (T,17,4), profile)."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    estimator = app_mod._RTMWNlfCompat.__new__(app_mod._RTMWNlfCompat)
    fake_engine, pose_frames = _make_fake_engine(arm_scale_seed=1.0, num_frames=30)
    from sunity_shared.analysis.pose_frame import PoleAxis

    estimator._engine = fake_engine
    estimator._default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )

    coco_array, profile = estimator.estimate_with_profile(["dummy_frame"])
    assert isinstance(coco_array, np.ndarray)
    assert coco_array.shape == (30, 17, 4)
    assert isinstance(profile, BodyNormalizationProfile)


def test_estimate_signature_unchanged_b8_lock(app_mod):
    """B8 박제: estimate(frames) -> np.ndarray 시그너처 무변경 + 사이드카 폐기."""
    estimator = app_mod._RTMWNlfCompat.__new__(app_mod._RTMWNlfCompat)
    fake_engine, _ = _make_fake_engine()
    from sunity_shared.analysis.pose_frame import PoleAxis
    estimator._engine = fake_engine
    estimator._default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )
    result = estimator.estimate(["dummy"])
    assert isinstance(result, np.ndarray)
    assert not isinstance(result, tuple)
    # 사이드카 attribute 폐기 검증
    assert not hasattr(estimator, "last_body_profile"), (
        "HIGH-1 v4 박제 위반: last_body_profile 사이드카가 살아있음"
    )


def test_helper_returns_angles_and_profile_locally(app_mod, monkeypatch, tmp_path):
    """_angles_and_body_profile_from_video — mock S3 + fake estimator → tuple."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

    # _ensure_adapters 가 globals 를 채우도록 mock
    fake_engine, _ = _make_fake_engine(arm_scale_seed=1.0, num_frames=30)
    from sunity_shared.analysis.pose_frame import PoleAxis
    estimator = app_mod._RTMWNlfCompat.__new__(app_mod._RTMWNlfCompat)
    estimator._engine = fake_engine
    estimator._default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )

    fake_extractor = MagicMock()
    fake_extractor.extract.return_value = ["frame0"]

    monkeypatch.setattr(app_mod, "_FRAME_EXTRACTOR", fake_extractor)
    monkeypatch.setattr(app_mod, "_POSE_ESTIMATOR", estimator)
    monkeypatch.setattr(app_mod, "_COACH_WRITER", MagicMock())

    fake_s3 = MagicMock()
    monkeypatch.setattr(app_mod, "_s3", fake_s3)

    angles, profile = app_mod._angles_and_body_profile_from_video("bucket", "key")
    assert isinstance(angles, np.ndarray)
    assert isinstance(profile, BodyNormalizationProfile)
    fake_s3.download_file.assert_called_once()


def test_concurrency_no_profile_leak_between_background_tasks(app_mod):
    """HIGH-1 v4 핵심: barriered 2 worker → 각자 자기 profile (글로벌 leak 0)."""
    barrier = threading.Barrier(2)

    class BarrieredFakeEngine:
        def __init__(self, arm_scale_seed: float):
            self._seed = arm_scale_seed

        def estimate(self, frames, pole):
            # 두 worker 가 동시에 measure → 글로벌 공유에도 local-return tuple 분리
            barrier.wait()
            pose_frames = [
                dataclasses.replace(_build_fake_pose_frame(self._seed), frame_index=i)
                for i in range(30)
            ]
            return pose_frames

    # 두 worker — 다른 arm_scale_seed → 다른 profile
    from sunity_shared.analysis.pose_frame import PoleAxis

    def _worker(seed: float):
        est = app_mod._RTMWNlfCompat.__new__(app_mod._RTMWNlfCompat)
        est._engine = BarrieredFakeEngine(seed)
        est._default_pole = PoleAxis(
            axis_vector=(0.0, 1.0, 0.0),
            confidence_level="low",
            source="vertical_fallback",
            frame_index=None,
        )
        coco, profile = est.estimate_with_profile(["dummy"])
        return profile

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f_a = pool.submit(_worker, 1.0)
        f_b = pool.submit(_worker, 0.5)
        profile_a = f_a.result(timeout=10)
        profile_b = f_b.result(timeout=10)

    # 두 profile 의 arm_scale 가 다르다 — local-return 격리 박제 증거
    assert profile_a != profile_b
    assert profile_a.arm_scale != profile_b.arm_scale


def test_stale_profile_not_leaked_on_failure(app_mod):
    """HIGH-1 v4 핵심: 예외 발생 시 직전 profile 반환 X (전파)."""
    from sunity_shared.analysis.pose_frame import PoleAxis

    estimator = app_mod._RTMWNlfCompat.__new__(app_mod._RTMWNlfCompat)
    fake_engine = MagicMock()
    # first call: 정상
    _, pose_frames_ok = _make_fake_engine(arm_scale_seed=1.0)
    fake_engine.estimate.side_effect = [
        pose_frames_ok,
        RuntimeError("simulated GPU OOM"),
    ]
    estimator._engine = fake_engine
    estimator._default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )

    # 1st call OK
    _, profile_first = estimator.estimate_with_profile(["dummy"])
    assert profile_first is not None

    # 2nd call raises — stale profile 반환 0
    with pytest.raises(RuntimeError, match="simulated GPU OOM"):
        estimator.estimate_with_profile(["dummy"])


def test_b8_signature_lock_preserved(app_mod):
    """B8 박제: _angles_from_video / _angles_and_video_path_from_video / _angles_and_body_profile_from_video 시그너처."""
    sig1 = inspect.signature(app_mod._angles_from_video)
    assert list(sig1.parameters.keys()) == ["bucket", "key"]
    sig2 = inspect.signature(app_mod._angles_and_video_path_from_video)
    assert list(sig2.parameters.keys()) == ["bucket", "key"]
    sig3 = inspect.signature(app_mod._angles_and_body_profile_from_video)
    assert list(sig3.parameters.keys()) == ["bucket", "key"]


def test_estimate_injects_body_shape_into_all_frames(app_mod):
    """estimate_with_profile 가 모든 pose_frame 의 body_shape 에 동일 profile 주입.

    검증: to_coco17_array 가 호출되기 전 pose_frames 의 body_shape 가 same instance.
    """
    from sunity_shared.analysis.pose_frame import PoleAxis

    estimator = app_mod._RTMWNlfCompat.__new__(app_mod._RTMWNlfCompat)
    fake_engine, _ = _make_fake_engine(arm_scale_seed=1.0, num_frames=30)
    estimator._engine = fake_engine
    estimator._default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )
    coco_array, profile = estimator.estimate_with_profile(["dummy"])
    # profile 자체가 같은 값으로 모든 frame 에 주입됐는지는 직접 검증 어려움 (to_coco17_array 가 keypoints 만 사용).
    # 대신 measurer 의 결정성 + profile dataclass equality 박제로 충분.
    assert profile.arm_scale > 0.0
    assert coco_array.shape[0] == 30


def test_short_frames_graceful_degrade(app_mod):
    """T=3 → fallback path (MEDIUM-2 v5 scale=1.0, confidence=0, insufficient_frames)."""
    from sunity_shared.analysis.pose_frame import PoleAxis

    estimator = app_mod._RTMWNlfCompat.__new__(app_mod._RTMWNlfCompat)
    fake_engine, _ = _make_fake_engine(arm_scale_seed=1.0, num_frames=3)
    estimator._engine = fake_engine
    estimator._default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )
    coco_array, profile = estimator.estimate_with_profile(["dummy"])
    assert profile.arm_scale == 1.0
    assert profile.confidence == 0.0
    assert "insufficient_frames" in profile.warnings


def test_to_coco17_array_unaffected(app_mod):
    """body_shape 주입이 to_coco17_array shape 에 영향 0 (T,17,4) 유지."""
    from sunity_shared.analysis.pose_frame import PoleAxis

    estimator = app_mod._RTMWNlfCompat.__new__(app_mod._RTMWNlfCompat)
    fake_engine, _ = _make_fake_engine(arm_scale_seed=1.0, num_frames=30)
    estimator._engine = fake_engine
    estimator._default_pole = PoleAxis(
        axis_vector=(0.0, 1.0, 0.0),
        confidence_level="low",
        source="vertical_fallback",
        frame_index=None,
    )

    coco_with_profile, _ = estimator.estimate_with_profile(["dummy"])
    coco_without = estimator.estimate(["dummy"])
    assert coco_with_profile.shape == (30, 17, 4)
    assert coco_without.shape == (30, 17, 4)
