"""Plan 17-03 Task 2 — pipeline _process 의 영역 D wave 2 wiring 통합 테스트.

박제 정신:
  · `_process(bucket, key, uid, analysis_id)` 시그너처 변경 0 — RunPod /
    Lambda SQS caller 갱신 0.
  · augment_low_confidence 는 monkeypatch — 외부 Gemini API 호출 0.
  · GEMINI_D_ENABLED=0 → wave 2 skip + geminiD=None.
  · occlusion_severe=True → wave 2 skip + geminiD=None.
  · local_video_path=None → wave 2 skip + geminiD=None (B4 회귀).
  · **B2 hard gate** — 3D coco_array (inputs.keypoints_4ch) mutate 0 회귀.
  · `_VideoAnalysisInputs.keypoints_4ch` 박제 회귀 (3차 R-B3 정합 — RTMW 1회 보장).
  · uncertainty_proxy frame 식별 = `max(axis=1) > 0.5` 회귀 (`min < 0.5` 박제 0).
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest


# pipeline app.py 의 Lambda Layer path 박제 (/opt/python) 가 import 시 필요.
_LAYER = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_LAYER) not in sys.path:
    sys.path.insert(0, str(_LAYER))

_PIPELINE_DIR = (
    Path(__file__).resolve().parents[1] / "functions" / "pipeline"
)
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))


pipeline_app = pytest.importorskip("app")
from sunity_shared.analysis.keypoint_frame import KeypointReport  # noqa: E402


# ─────────────────── KeypointReport fixture 박제 ───────────────────


def _make_report(T: int = 3) -> KeypointReport:
    joints = [
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_hand",
        "right_hand",
    ]
    J = len(joints)
    data: list[float] = []
    confidence: list[float] = []
    for t in range(T):
        for j_name in joints:
            if "left_" in j_name:
                data.extend((0.3, 0.5))
            elif "right_" in j_name:
                data.extend((0.7, 0.5))
            else:
                data.extend((0.5, 0.5))
            confidence.append(0.9)
    reliability = ["high" for _ in range(T)]
    return KeypointReport(
        version="1.0",
        joints=joints,
        frames=T,
        fps=9.0,
        data=data,
        confidence=confidence,
        reliability=reliability,
        axis_data=[0.0] * (T * 3 * 2),
        axis_mask=[True] * (T * 3),
        warnings=[],
    )


# ─────────────────── 테스트 ───────────────────


class TestWave2Helpers:
    """pipeline app.py 가 wave 2 helper 박제 노출."""

    def test_d_enabled_helper_exists(self) -> None:
        assert hasattr(pipeline_app, "_d_enabled")
        assert callable(pipeline_app._d_enabled)

    def test_call_wave2_helper_exists(self) -> None:
        assert hasattr(pipeline_app, "_call_wave2_keypoint_augmenter")
        assert callable(pipeline_app._call_wave2_keypoint_augmenter)

    def test_low_uncertainty_helper_exists(self) -> None:
        assert hasattr(pipeline_app, "_low_uncertainty_frame_indices")
        assert callable(pipeline_app._low_uncertainty_frame_indices)

    def test_apply_refinement_helper_exists(self) -> None:
        assert hasattr(pipeline_app, "_apply_keypoint_refinement_to_report")
        assert callable(pipeline_app._apply_keypoint_refinement_to_report)


class TestDEnabledFlag:
    """GEMINI_D_ENABLED env 토글 박제."""

    def test_default_off(self, monkeypatch) -> None:
        """env 미설정 시 default OFF (Plan 17-01 _VISION_ENV_DEFAULTS 박제 정합)."""
        monkeypatch.delenv("GEMINI_D_ENABLED", raising=False)
        assert pipeline_app._d_enabled() is False

    def test_truthy_on(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_D_ENABLED", "1")
        assert pipeline_app._d_enabled() is True

    def test_zero_off(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_D_ENABLED", "0")
        assert pipeline_app._d_enabled() is False


class TestVideoAnalysisInputsKeypoints4ch:
    """_VideoAnalysisInputs 에 keypoints_4ch 필드 박제 (3차 R-B3 정합)."""

    def test_namedtuple_has_keypoints_4ch_field(self) -> None:
        fields = pipeline_app._VideoAnalysisInputs._fields
        assert "keypoints_4ch" in fields, (
            f"_VideoAnalysisInputs.keypoints_4ch 박제 누락 — fields={fields}"
        )


class TestLowUncertaintyFrameIndices:
    """`coco_array[:, :, 3].max(axis=1) > 0.5` 인 frame 식별 (3차 R-B3 정합)."""

    def test_max_gt_threshold_returns_indices(self) -> None:
        """frame 1 의 joint 3 이 uncertainty=0.6 → frame 1 반환."""
        T, J = 5, 17
        arr = np.zeros((T, J, 4), dtype=float)
        arr[:, :, 3] = 0.2  # baseline.
        arr[1, 3, 3] = 0.6  # frame 1, joint 3 — 위.
        arr[3, 5, 3] = 0.55  # frame 3, joint 5 — 위.
        result = pipeline_app._low_uncertainty_frame_indices(arr)
        assert result == [1, 3]

    def test_no_frames_above_threshold(self) -> None:
        T, J = 5, 17
        arr = np.zeros((T, J, 4), dtype=float)
        arr[:, :, 3] = 0.4  # baseline below 0.5.
        result = pipeline_app._low_uncertainty_frame_indices(arr)
        assert result == []

    def test_max_axis_logic_not_min(self) -> None:
        """uncertainty_proxy 의 max(axis=1) 가 정답 — min < 0.5 박제 금지 (회귀).

        frame 1 의 모든 joint 가 0.6 → max = 0.6 (위), min = 0.6 (위).
        frame 2 는 joint 0 만 0.6, 나머지 0.0 → max = 0.6 (위), min = 0.0 (아래).
        max 박제 정답: 둘 다 식별. min 박제 오답: frame 1만 식별 (frame 2 누락).
        """
        T, J = 3, 17
        arr = np.zeros((T, J, 4), dtype=float)
        arr[1, :, 3] = 0.6  # 전체 frame 1 = 0.6.
        arr[2, 0, 3] = 0.6  # frame 2 joint 0 만 = 0.6.
        result = pipeline_app._low_uncertainty_frame_indices(arr)
        # max 박제 — 둘 다 식별.
        assert 1 in result
        assert 2 in result

    def test_none_returns_empty(self) -> None:
        assert pipeline_app._low_uncertainty_frame_indices(None) == []


class TestCallWave2HelperGates:
    """wave 2 진입 게이트 박제 — occlusion_severe / GEMINI_D_ENABLED / local_video_path."""

    def test_skip_when_local_video_path_none(self, monkeypatch) -> None:
        """local_video_path=None → wave 2 skip + None (B4 hard gate)."""
        call_count = {"n": 0}

        def _tracker(**kwargs: Any) -> Any:
            call_count["n"] += 1
            return {}

        monkeypatch.setattr("sunity_shared.gemini.keypoint_augmenter.augment_low_confidence", _tracker)
        monkeypatch.setenv("GEMINI_D_ENABLED", "1")

        result = pipeline_app._call_wave2_keypoint_augmenter(
            local_video_path=None,
            low_uncertainty_frame_indices=[1, 2],
            keypoint_report_2d=_make_report(),
            scene_result={"occlusion_severe": False},
        )

        assert result is None
        assert call_count["n"] == 0

    def test_skip_when_d_disabled(self, monkeypatch) -> None:
        """GEMINI_D_ENABLED=0 → wave 2 skip + None."""
        call_count = {"n": 0}

        def _tracker(**kwargs: Any) -> Any:
            call_count["n"] += 1
            return {}

        monkeypatch.setattr("sunity_shared.gemini.keypoint_augmenter.augment_low_confidence", _tracker)
        monkeypatch.setenv("GEMINI_D_ENABLED", "0")

        result = pipeline_app._call_wave2_keypoint_augmenter(
            local_video_path="/tmp/v.mp4",
            low_uncertainty_frame_indices=[1, 2],
            keypoint_report_2d=_make_report(),
            scene_result={"occlusion_severe": False},
        )

        assert result is None
        assert call_count["n"] == 0

    def test_skip_when_occlusion_severe(self, monkeypatch) -> None:
        """occlusion_severe=True → wave 2 skip + None (게이트 1)."""
        call_count = {"n": 0}

        def _tracker(**kwargs: Any) -> Any:
            call_count["n"] += 1
            return {}

        monkeypatch.setattr("sunity_shared.gemini.keypoint_augmenter.augment_low_confidence", _tracker)
        monkeypatch.setenv("GEMINI_D_ENABLED", "1")

        result = pipeline_app._call_wave2_keypoint_augmenter(
            local_video_path="/tmp/v.mp4",
            low_uncertainty_frame_indices=[1, 2],
            keypoint_report_2d=_make_report(),
            scene_result={"occlusion_severe": True},
        )

        assert result is None
        assert call_count["n"] == 0

    def test_invokes_augment_when_all_gates_pass(self, monkeypatch) -> None:
        """모든 게이트 통과 → augment_low_confidence 1회 호출 + 결과 그대로 반환."""
        captured = {}

        def _tracker(**kwargs: Any) -> dict:
            captured.update(kwargs)
            return {"refined": [], "model": "gemini-3.1-pro-preview"}

        monkeypatch.setattr("sunity_shared.gemini.keypoint_augmenter.augment_low_confidence", _tracker)
        monkeypatch.setenv("GEMINI_D_ENABLED", "1")
        report = _make_report()

        result = pipeline_app._call_wave2_keypoint_augmenter(
            local_video_path="/tmp/v.mp4",
            low_uncertainty_frame_indices=[1, 2],
            keypoint_report_2d=report,
            scene_result={"occlusion_severe": False},
        )

        assert result == {"refined": [], "model": "gemini-3.1-pro-preview"}
        assert captured["video_path"] == "/tmp/v.mp4"
        assert captured["low_uncertainty_frame_indices"] == [1, 2]
        assert captured["keypoint_report_2d"] is report

    def test_graceful_swallow_exception(self, monkeypatch) -> None:
        """augment_low_confidence raise → graceful None."""
        def _raiser(**kwargs: Any) -> Any:
            raise ValueError("객관성 가드 시뮬")

        monkeypatch.setattr("sunity_shared.gemini.keypoint_augmenter.augment_low_confidence", _raiser)
        monkeypatch.setenv("GEMINI_D_ENABLED", "1")

        result = pipeline_app._call_wave2_keypoint_augmenter(
            local_video_path="/tmp/v.mp4",
            low_uncertainty_frame_indices=[1, 2],
            keypoint_report_2d=_make_report(),
            scene_result={"occlusion_severe": False},
        )
        assert result is None


class TestApplyRefinementToReport:
    """augment_low_confidence 결과의 refined 좌표를 KeypointReport 에 박제 (B2 정합)."""

    def test_data_and_confidence_updated_only_for_mapped_joints(self) -> None:
        """shoulder/hip/knee 는 KeypointReport 박제, elbow 는 skip (KeypointReport 에 없음)."""
        report = _make_report(T=3)
        augment_result = {
            "refined": [
                {
                    "frame_index": 1,
                    "joint_key": "left_shoulder",
                    "x_normalized": 0.4,
                    "y_normalized": 0.55,
                    "confidence": 0.88,
                },
                {
                    "frame_index": 1,
                    "joint_key": "left_elbow",  # KeypointReport 에 없음 — skip.
                    "x_normalized": 0.9,
                    "y_normalized": 0.1,
                    "confidence": 0.95,
                },
            ],
        }

        new_report = pipeline_app._apply_keypoint_refinement_to_report(
            report, augment_result
        )

        # left_shoulder = joints[0] (T=3 박제), frame 1, joint 0 → data[(1*8 + 0)*2] = 16.
        J = len(new_report.joints)
        data_idx = (1 * J + 0) * 2
        assert new_report.data[data_idx] == pytest.approx(0.4)
        assert new_report.data[data_idx + 1] == pytest.approx(0.55)
        conf_idx = 1 * J + 0
        assert new_report.confidence[conf_idx] == pytest.approx(0.88)
        # 원본 보존 — frame 0 의 left_shoulder data 는 변경 X.
        orig_idx = (0 * J + 0) * 2
        assert new_report.data[orig_idx] == pytest.approx(0.3)  # 원본 박제.
        # warnings 박제.
        assert "gemini_d_augmented" in new_report.warnings

    def test_reliability_promoted_on_augmented_frames(self) -> None:
        """보강 frame 의 reliability 가 'medium' 박제 ('high' 은 유지)."""
        report = _make_report(T=3)
        # reliability 전부 'high' 박제 — 새 frame index 1 박제 high 유지.
        augment_result = {
            "refined": [
                {
                    "frame_index": 1,
                    "joint_key": "left_shoulder",
                    "x_normalized": 0.4,
                    "y_normalized": 0.55,
                    "confidence": 0.88,
                },
            ],
        }
        new_report = pipeline_app._apply_keypoint_refinement_to_report(
            report, augment_result
        )
        # 본 fixture 는 high → high 유지.
        assert new_report.reliability[1] == "high"

    def test_empty_refined_returns_original(self) -> None:
        """refined 빈 → 원본 그대로 (frozen dataclass)."""
        report = _make_report(T=3)
        result = pipeline_app._apply_keypoint_refinement_to_report(
            report, {"refined": []}
        )
        assert result is report


class TestB2HardGate3DCocoArrayInvariant:
    """B2 hard gate — augment_low_confidence 시그너처 + apply helper 가 3D 입력 0건."""

    def test_augment_low_confidence_signature_no_coco_array(self) -> None:
        """augment_low_confidence 시그너처에 coco_array / rtmw_array 박제 0건 (B2 회귀)."""
        # 원본 함수를 본다 — app.py 는 D-16 지연 import 라 최상위 속성이 아니다
        # (2026-08-28: pipeline_app 겨냥이 AttributeError 였다. 불변식 자체는 유효).
        from sunity_shared.gemini.keypoint_augmenter import augment_low_confidence

        params = inspect.signature(augment_low_confidence).parameters
        assert "coco_array" not in params
        assert "rtmw_array" not in params

    def test_apply_helper_does_not_take_coco_array(self) -> None:
        """_apply_keypoint_refinement_to_report 도 3D 행렬 미수용 — KeypointReport 만."""
        params = inspect.signature(
            pipeline_app._apply_keypoint_refinement_to_report
        ).parameters
        assert "coco_array" not in params
        assert "rtmw_array" not in params
        # 박힌 인자 박제 — keypoint_report + augment_result.
        assert "keypoint_report" in params
        assert "augment_result" in params

    def test_coco_array_unchanged_by_wave2_path(self, monkeypatch) -> None:
        """wave 2 호출 전후 keypoints_4ch np.array_equal True (B2 핵심 회귀)."""
        T, J = 5, 17
        before = np.zeros((T, J, 4), dtype=float)
        before[:, :, 3] = 0.6  # 전 frame 0.5 초과 → wave 2 진입 가능.
        before[0, 0, 0] = 100.0  # marker.
        # 깊은 복사 박제 — wave 2 가 변경하면 before vs after 비교 가능.
        snapshot = before.copy()

        # augment_low_confidence 박제 — refined 박제 dict 반환.
        def _tracker(**kwargs: Any) -> dict:
            return {
                "refined": [
                    {
                        "frame_index": 0,
                        "joint_key": "left_shoulder",
                        "x_normalized": 0.5,
                        "y_normalized": 0.5,
                        "confidence": 0.9,
                    }
                ],
                "model": "gemini-3.1-pro-preview",
            }

        monkeypatch.setattr("sunity_shared.gemini.keypoint_augmenter.augment_low_confidence", _tracker)
        monkeypatch.setenv("GEMINI_D_ENABLED", "1")

        # wave 2 helper 호출 — coco_array 인자 박제 0건. KeypointReport 만 박제.
        report = _make_report(T=T)
        result = pipeline_app._call_wave2_keypoint_augmenter(
            local_video_path="/tmp/v.mp4",
            low_uncertainty_frame_indices=pipeline_app._low_uncertainty_frame_indices(
                before
            ),
            keypoint_report_2d=report,
            scene_result={"occlusion_severe": False},
        )

        # apply 박제 — KeypointReport 만 보강.
        if result is not None and result.get("refined"):
            pipeline_app._apply_keypoint_refinement_to_report(report, result)

        # 3D 행렬 mutate 0 회귀.
        assert np.array_equal(before, snapshot), (
            "B2 hard gate 위반 — coco_array (keypoints_4ch) 가 wave 2 path 에서 mutate됨"
        )


class TestExtractVideoAnalysisInputsKeypoints4ch:
    """_extract_video_analysis_inputs 가 keypoints_4ch 박제 — RTMW 1회 보장 회귀 (3차 R-B3)."""

    def test_field_populated_from_to_coco17_array(self, monkeypatch) -> None:
        """_extract_video_analysis_inputs 가 to_coco17_array 결과를 keypoints_4ch 에 박제.

        to_coco17_array 호출 횟수 = 1 (재계산 0건 — Phase 6 RTMW estimate 1회 보장).
        """
        # 박제용 stub fixture.
        T = 3
        fake_coco = np.zeros((T, 17, 4), dtype=np.float32)
        fake_coco[:, :, 3] = 0.3

        call_count = {"to_coco17": 0}

        def _stub_to_coco17(pose_frames):
            call_count["to_coco17"] += 1
            return fake_coco

        # 박제 — to_coco17_array, _ensure_adapters, _s3, _FRAME_EXTRACTOR/_RTMW_ENGINE 등.
        monkeypatch.setattr(pipeline_app, "to_coco17_array", _stub_to_coco17)
        monkeypatch.setattr(pipeline_app, "_ensure_adapters", lambda: None)

        # _s3.download_file no-op.
        class _StubS3:
            def download_file(self, *a, **k):
                return None

        monkeypatch.setattr(pipeline_app, "_s3", _StubS3())

        # _FRAME_EXTRACTOR / _RTMW_ENGINE 박제.
        class _StubFrames:
            frames = np.zeros((T, 320, 320, 3), dtype=np.uint8)

        class _StubExtractor:
            def extract(self, path):
                return _StubFrames()

        class _StubRTMW:
            def estimate(self, frames, default_pole):
                return [object() for _ in range(T)]  # 박제 — pose_frames T 개.

        monkeypatch.setattr(pipeline_app, "_FRAME_EXTRACTOR", _StubExtractor())
        monkeypatch.setattr(pipeline_app, "_RTMW_ENGINE", _StubRTMW())

        # measure_body_profile / compute_joint_angles / temporal_fill /
        # joint_uncertainty / build_pole_axis_measurement 박제.
        from sunity_shared.analysis.body_normalization import BodyNormalizationProfile

        def _stub_measure(pose_frames):
            return BodyNormalizationProfile(
                estimated_height_scale=1.0,
                arm_scale=1.0,
                leg_scale=1.0,
                torso_scale=1.0,
                shoulder_hip_ratio=1.0,
                confidence=0.9,
                warnings=[],
            )

        monkeypatch.setattr(pipeline_app, "measure_body_profile", _stub_measure)
        monkeypatch.setattr(
            pipeline_app, "compute_joint_angles", lambda arr: np.zeros((T, 8))
        )
        monkeypatch.setattr(
            pipeline_app, "joint_uncertainty", lambda arr: np.zeros((T, 8))
        )
        monkeypatch.setattr(
            pipeline_app, "temporal_fill", lambda angles, unc: angles
        )

        class _StubPoleMeasurement:
            coordinate_space = "unavailable"
            axis_vector_world = (0.0, 1.0, 0.0)
            axis_vector_screen = None
            origin_world = None
            origin_screen = None
            confidence_level = "low"
            source = "vertical_fallback"
            frame_index = None
            tilt_deg = 0.0
            warnings = []

        monkeypatch.setattr(
            pipeline_app,
            "build_pole_axis_measurement",
            lambda axis_3d, line, frame_index: _StubPoleMeasurement(),
        )
        # _POLE_DETECTOR = None → vertical_fallback path.
        monkeypatch.setattr(pipeline_app, "_POLE_DETECTOR", None)

        from sunity_shared.analysis.pose_frame import PoleAxis

        default_pole = PoleAxis(
            axis_vector=(0.0, 1.0, 0.0),
            confidence_level="low",
            source="vertical_fallback",
            frame_index=None,
        )

        result = pipeline_app._extract_video_analysis_inputs(
            "bucket", "key", default_pole, keep_local_video=False
        )

        # keypoints_4ch 박제.
        assert hasattr(result, "keypoints_4ch")
        assert result.keypoints_4ch is fake_coco
        # to_coco17_array 1회만 호출 (RTMW estimate 1회 보장 유지).
        assert call_count["to_coco17"] == 1


class TestImportSymbol:
    """augment_low_confidence import 박제 — pipeline app.py 가 정상 import 가능."""

    def test_augment_low_confidence_imported(self) -> None:
        """지연 import 대상이 실재하고 호출 가능한지 (D-16 정합).

        ~~`hasattr(pipeline_app, ...)`~~ 는 2026-08-28 제거 — app.py 가 Lambda
        250MB 때문에 함수 안에서 import 하므로 최상위 속성일 수 없다.
        """
        from sunity_shared.gemini.keypoint_augmenter import augment_low_confidence

        assert callable(augment_low_confidence)
