"""Plan 08-03 Task 2 — pipeline Phase 8 wiring integration test (mock E2E).

11 신설 test (Cycle 1 8 + Cycle 2 NEW HIGH #1 plumbing 3):
  1. test_pipeline_phase8_layer2_off_when_force_signals_flag_unset (REVIEWS R7)
  2. test_pipeline_phase8_layer2_on_when_both_flags_set
  3. test_pipeline_phase8_layer2_off_when_recognizer_backend_unset
  4. test_pipeline_phase8_default_off_safe — 분석 죽지 않음
  5. test_pipeline_phase8_mode1_force_signals_emitted
  6. test_pipeline_phase8_mode3_force_signals_emitted
  7. test_pipeline_phase8_complete_analysis_force_signals_kwarg
  8. test_pipeline_phase8_pole_axis_measurement_present (REVIEWS R10)
  9. test_pipeline_phase8_preflight_gate_env_truthy_passes_true (Cycle 2 NEW HIGH #1)
  10. test_pipeline_phase8_preflight_gate_env_falsy_passes_false
  11. test_pipeline_phase8_preflight_gate_env_unset_passes_none

mock-based — 실 S3 / 실 Firestore / 실 RTMW / 실 Gemini 호출 0.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

# functions/pipeline/ 디렉토리를 path 에 추가.
_PIPELINE = Path(__file__).resolve().parents[1].parent / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _import_pipeline():
    sys.modules.pop("app", None)
    import app  # noqa: WPS433
    return importlib.reload(app)


def _angles_8j(rows: int = 60) -> np.ndarray:
    from sunity_shared.analysis.skeleton import JOINT_KEYS
    rng = np.random.default_rng(0)
    base = 90.0 + 5.0 * np.sin(np.arange(rows) / 5.0)
    out = np.tile(base.reshape(-1, 1), (1, len(JOINT_KEYS)))
    out += rng.normal(0.0, 0.5, size=(rows, len(JOINT_KEYS)))
    return out


def _make_pose_frames(n: int = 60) -> list:
    """합성 PoseFrame 박제 — keypoints_2d 박제만 채움 (Phase 8 force_signals 박제 사용).

    phase08 fixture factory 박제 (Plan 08-00 _factory.py) 박제 reuse.
    """
    # phase08 fixture factory 박제 reuse (Plan 08-00 박제 정합).
    import sys
    from pathlib import Path

    phase08_tests = Path(__file__).resolve().parents[1] / "phase08"
    if str(phase08_tests) not in sys.path:
        sys.path.insert(0, str(phase08_tests))
    from fixtures._factory import make_keypoint2d, make_pose_frame  # noqa: WPS433

    frames = []
    for i in range(n):
        kp2d = {
            "left_shoulder": make_keypoint2d(0.45, 0.3),
            "right_shoulder": make_keypoint2d(0.55, 0.3),
            "left_hip": make_keypoint2d(0.46, 0.6),
            "right_hip": make_keypoint2d(0.54, 0.6),
            "left_wrist": make_keypoint2d(0.5, 0.2),
            "right_wrist": make_keypoint2d(0.5, 0.2),
        }
        frames.append(
            make_pose_frame(
                frame_index=i,
                timestamp_ms=int(i * 111.0),
                keypoints_2d=kp2d,
                reliability="high",
            )
        )
    return frames


def _stub_extract_inputs(pipeline_mod, tmp_video_path: str = "/tmp/__phase8.mp4"):
    """_extract_video_analysis_inputs mock factory — Plan 08-03 pole_axis_measurement 박제 포함."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.pole_geometry import build_pole_axis_measurement

    def _impl(bucket, key, default_pole, *, keep_local_video=False):
        local_path = Path(tmp_video_path) if keep_local_video else None
        fallback_profile = BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=0.0,
            warnings=["mock"],
        )
        pole_axis_measurement = build_pole_axis_measurement(
            axis_3d=default_pole, line=None, frame_index=None
        )
        return pipeline_mod._VideoAnalysisInputs(
            angles=_angles_8j(),
            student_profile=fallback_profile,
            pose_frames=_make_pose_frames(60),
            local_video_path=local_path,
            pole_axis_measurement=pole_axis_measurement,
            # Plan 17-03 — _VideoAnalysisInputs.keypoints_4ch 신설 (3차 R-B3 정합).
            keypoints_4ch=np.zeros((_angles_8j().shape[0], 17, 4), dtype=float),
        )

    return _impl


@pytest.fixture(autouse=True)
def _reset_pipeline_env(monkeypatch):
    """env clear — env 박제 leak 차단."""
    for k in (
        "GEMINI_RECOGNIZER_ENABLED",
        "RECOGNIZER_BACKEND",
        "FORCE_SIGNALS_LAYER2_ENABLED",
        "PREFLIGHT_LABEL_GATE_PASSED",
        "RUNPOD_ANALYZE_URL",
        "RUNPOD_AUTH_TOKEN",
    ):
        monkeypatch.delenv(k, raising=False)
    yield
    sys.modules.pop("app", None)


@pytest.fixture
def base_mocks(monkeypatch):
    """공통 mock — Mode 3 분기 (referenceMotionId 없음)."""
    pipeline = _import_pipeline()
    meta = {"mode": pipeline.models.MODE_SELF}
    monkeypatch.setattr(
        pipeline.firestore_admin, "get_analysis", lambda uid, aid: dict(meta)
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_previous_analysis",
        lambda uid, aid, mode=None: None,
    )
    # complete_analysis 박제 MagicMock — call_args 검사 박제.
    complete_mock = MagicMock()
    monkeypatch.setattr(
        pipeline.firestore_admin, "complete_analysis", complete_mock
    )
    monkeypatch.setattr(
        pipeline, "_signed_get", lambda bucket, key: f"https://signed/{key}"
    )

    coach_mock = MagicMock()
    coach_mock.write.return_value = {"summary": "mock coach"}
    pipeline._COACH_WRITER = coach_mock
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)

    return pipeline, complete_mock


# ── Layer 2 env separation matrix — REVIEWS R7 (4 combination) ─────────────


def test_pipeline_phase8_layer2_off_when_force_signals_flag_unset(
    base_mocks, monkeypatch
):
    """RECOGNIZER_BACKEND='gemini' + FORCE_SIGNALS_LAYER2_ENABLED unset → Layer 2 비활성."""
    pipeline, complete_mock = base_mocks
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    monkeypatch.delenv("FORCE_SIGNALS_LAYER2_ENABLED", raising=False)
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )
    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    # complete_analysis 박제 호출 박제 + force_signals_report 박제 검사.
    fs_report = complete_mock.call_args.kwargs.get("force_signals_report")
    assert fs_report is not None
    assert "layer2_unavailable" in fs_report.get("warnings", [])


def test_pipeline_phase8_layer2_on_when_both_flags_set(
    base_mocks, monkeypatch
):
    """RECOGNIZER_BACKEND='gemini' + FORCE_SIGNALS_LAYER2_ENABLED='1' → Layer 2 활성
    technique_profile.key_moments 박제 mock + force_signals_report 의 phaseBoundaries
    안에 source='gemini_assisted' 박제 entry 박제 (한 개 이상).
    """
    pipeline, complete_mock = base_mocks
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    # preflight=True 박제 — ceiling 박제 'medium' 박제 → Layer 2 agreement 'high'/'medium'
    # 박제 박제 effective != 'low' 박제 강제 (source='gemini_assisted' 박제 propagate).
    monkeypatch.setenv("PREFLIGHT_LABEL_GATE_PASSED", "1")
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )

    # mock recognizer — recognize() 가 TechniqueProfile(key_moments=...) 박제 반환.
    from sunity_shared.analysis.technique import TechniqueProfile
    from sunity_shared.judging.gemini_moment_extractor import KeyMoment

    moments = (
        KeyMoment(
            motion="ref-invert",
            moment_key="setup",
            timestamp_seconds=1.3,
            frame_index=12,
            confidence=0.9,
            source_response_excerpt="",
        ),
        KeyMoment(
            motion="ref-invert",
            moment_key="hold",
            timestamp_seconds=5.3,
            frame_index=48,
            confidence=0.9,
            source_response_excerpt="",
        ),
        KeyMoment(
            motion="ref-invert",
            moment_key="release",
            timestamp_seconds=6.5,
            frame_index=59,
            confidence=0.9,
            source_response_excerpt="",
        ),
    )
    tp = TechniqueProfile(
        name="invert",
        category="recognized",
        joint_expectations={},
        required_split_deg=None,
        requires_hold=True,
        is_symmetric=False,
        motion_id="ref-invert",
        key_moments=moments,
    )
    fake_recognizer = MagicMock()
    fake_recognizer.recognize.return_value = tp
    fake_recognizer.motion_query_hint = None
    fake_recognizer.unregistered_hook = None
    monkeypatch.setattr(pipeline, "_ensure_recognizer", lambda: fake_recognizer)
    # _get_force_signals_layer2_recognizer 박제 → fake recognizer 박제 반환 강제.
    monkeypatch.setattr(
        pipeline, "_get_force_signals_layer2_recognizer", lambda: fake_recognizer
    )
    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    fs_report = complete_mock.call_args.kwargs.get("force_signals_report")
    assert fs_report is not None
    sources = [b["source"] for b in fs_report["phaseBoundaries"]]
    assert any(s == "gemini_assisted" for s in sources), (
        f"Layer 2 활성 박제 강제 — sources={sources}"
    )


def test_pipeline_phase8_layer2_off_when_recognizer_backend_unset(
    base_mocks, monkeypatch
):
    """RECOGNIZER_BACKEND unset + FORCE_SIGNALS_LAYER2_ENABLED='1' → Layer 2 비활성
    (Phase 5 recognizer 비활성 시 Phase 8 Layer 2 박제 자동 OFF).
    """
    pipeline, complete_mock = base_mocks
    monkeypatch.delenv("RECOGNIZER_BACKEND", raising=False)
    monkeypatch.delenv("GEMINI_RECOGNIZER_ENABLED", raising=False)
    monkeypatch.setenv("FORCE_SIGNALS_LAYER2_ENABLED", "1")
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )
    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    fs_report = complete_mock.call_args.kwargs.get("force_signals_report")
    assert fs_report is not None
    assert "layer2_unavailable" in fs_report.get("warnings", []), (
        "RECOGNIZER_BACKEND unset 박제 Layer 2 비활성 강제 — "
        f"warnings={fs_report.get('warnings')}"
    )


def test_pipeline_phase8_default_off_safe(base_mocks, monkeypatch):
    """모든 env unset → Layer 1 단독 + force_signals_report 정상 산출 (분석 죽지 않음)."""
    pipeline, complete_mock = base_mocks
    # 모든 env unset (autouse fixture 박제).
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )
    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    fs_report = complete_mock.call_args.kwargs.get("force_signals_report")
    assert fs_report is not None
    assert fs_report["version"] == "1.0"
    assert "phaseBoundaries" in fs_report
    assert "axisMetrics" in fs_report


# ── Mode 분기 — mode1 / mode3 각각 force_signals_report emit ───────────────


def test_pipeline_phase8_mode1_force_signals_emitted(base_mocks, monkeypatch):
    """mode='mode1' + mock reference → force_signals_report kwarg 전달."""
    pipeline, complete_mock = base_mocks
    # meta mode 박제 변경.
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_analysis",
        lambda uid, aid: {
            "mode": pipeline.models.MODE_EXPERT,
            "referenceMotionId": "ref-invert",
        },
    )
    # reference motion mock — angles 박제. assemble.build_mode1 박제 motionId 박제 필요.
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_reference_motion",
        lambda mid: {
            "motionId": "ref-invert",
            "name": "invert",
            "athleteName": "정은지",
            "angles": np.full(60 * 8, 90.0).tolist(),
            "anglesJointKeys": list(["a"] * 8),
            "videoS3Key": None,
        },
    )
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )
    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    fs_report = complete_mock.call_args.kwargs.get("force_signals_report")
    assert fs_report is not None


def test_pipeline_phase8_mode3_force_signals_emitted(base_mocks, monkeypatch):
    """mode='mode3' + mock → force_signals_report kwarg 전달."""
    pipeline, complete_mock = base_mocks
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )
    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    fs_report = complete_mock.call_args.kwargs.get("force_signals_report")
    assert fs_report is not None


# ── complete_analysis 박제 force_signals_report kwarg 박제 ────────────────


def test_pipeline_phase8_complete_analysis_force_signals_kwarg(
    base_mocks, monkeypatch
):
    """complete_analysis 박제 call_args 박제 force_signals_report 박제 dict + 필수 키 박제."""
    pipeline, complete_mock = base_mocks
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )
    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    kwargs = complete_mock.call_args.kwargs
    fs = kwargs.get("force_signals_report")
    assert isinstance(fs, dict)
    for key in (
        "version",
        "overallConfidence",
        "warnings",
        "phaseBoundaries",
        "axisMetrics",
        "stabilityMetrics",
        "contactMetrics",
    ):
        assert key in fs, f"force_signals_report missing key {key}"


# ── pole_axis_measurement 박제 — REVIEWS R10 ───────────────────────────────


def test_pipeline_phase8_pole_axis_measurement_present(monkeypatch):
    """_extract_video_analysis_inputs 박제 _VideoAnalysisInputs 박제 pole_axis_measurement
    필드 존재 + coordinate_space='unavailable' (vertical fallback, REVIEWS R10).
    """
    pipeline = _import_pipeline()
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)

    # 직접 _stub_extract_inputs 박제 호출 박제 검증.
    stub = _stub_extract_inputs(pipeline)
    from sunity_shared.analysis.pose_frame import PoleAxis
    result = stub(
        "bucket",
        "key",
        PoleAxis(
            axis_vector=(0.0, 1.0, 0.0),
            confidence_level="low",
            source="vertical_fallback",
            frame_index=None,
        ),
        keep_local_video=False,
    )
    assert hasattr(result, "pole_axis_measurement")
    assert result.pole_axis_measurement.coordinate_space == "unavailable"
    assert result.pole_axis_measurement.line is None


# ── preflight gate env plumbing — REVIEWS Cycle 2 NEW HIGH #1 (3 state) ────


def test_pipeline_phase8_preflight_gate_env_truthy_passes_true(
    base_mocks, monkeypatch
):
    """PREFLIGHT_LABEL_GATE_PASSED='1' → preflight_label_gate_passed=True 박제 검증.

    REVIEWS Cycle 2 NEW HIGH #1 — phase_boundaries 박제 preflightLabelGatePassed=True
    확인 + 'preflight_gate_pending' / 'preflight_label_gate_failed' warning 박제 X.
    """
    pipeline, complete_mock = base_mocks
    monkeypatch.setenv("PREFLIGHT_LABEL_GATE_PASSED", "1")
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )
    # _preflight_label_gate_passed 박제 helper 박제 검증.
    assert pipeline._preflight_label_gate_passed() is True

    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    fs_report = complete_mock.call_args.kwargs.get("force_signals_report")
    assert fs_report is not None
    for b in fs_report["phaseBoundaries"]:
        assert b["preflightLabelGatePassed"] is True
    assert "preflight_label_gate_failed" not in fs_report["warnings"]
    assert "preflight_gate_pending" not in fs_report["warnings"]


def test_pipeline_phase8_preflight_gate_env_falsy_passes_false(
    base_mocks, monkeypatch
):
    """PREFLIGHT_LABEL_GATE_PASSED='0' → preflight_label_gate_passed=False 박제 + warning
    'preflight_label_gate_failed' 박제 검증.
    """
    pipeline, complete_mock = base_mocks
    monkeypatch.setenv("PREFLIGHT_LABEL_GATE_PASSED", "0")
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )
    assert pipeline._preflight_label_gate_passed() is False

    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    fs_report = complete_mock.call_args.kwargs.get("force_signals_report")
    assert fs_report is not None
    for b in fs_report["phaseBoundaries"]:
        assert b["preflightLabelGatePassed"] is False
    assert "preflight_label_gate_failed" in fs_report["warnings"]


def test_pipeline_phase8_preflight_gate_env_unset_passes_none(
    base_mocks, monkeypatch
):
    """PREFLIGHT_LABEL_GATE_PASSED unset → preflight_label_gate_passed=None 박제 + warning
    'preflight_gate_pending' 박제 검증.
    """
    pipeline, complete_mock = base_mocks
    monkeypatch.delenv("PREFLIGHT_LABEL_GATE_PASSED", raising=False)
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs", _stub_extract_inputs(pipeline)
    )
    assert pipeline._preflight_label_gate_passed() is None

    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    fs_report = complete_mock.call_args.kwargs.get("force_signals_report")
    assert fs_report is not None
    for b in fs_report["phaseBoundaries"]:
        assert b["preflightLabelGatePassed"] is None
    assert "preflight_gate_pending" in fs_report["warnings"]
