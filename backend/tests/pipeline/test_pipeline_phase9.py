"""Plan 09-02 Task T4 — pipeline Phase 9 wiring integration test (mock E2E).

5 cases — all run against the real `_process` entrypoint (R8 정합 — mini-helper
extraction 금지, wrong-MODE_* / axis-warning / mode-context bug class 모두 real
_process 통과 시에만 catchable):

  1. test_mode1_path_emits_mode1_context — mode == MODE_EXPERT → modeContext='mode1'
  2. test_mode3_first_path_emits_mode3_first_context — MODE_SELF + isFirst=True →
     modeContext='mode3_first'
  3. test_mode3_progress_path_emits_mode3_progress_context — MODE_SELF + isFirst=False →
     modeContext='mode3_progress'
  4. test_complete_analysis_kwarg_camelcase — complete_analysis call captures
     force_pattern_inference kwarg with camelCase keys
  5. test_force_signals_none_path_passes_none — force_signals_report mocked to None
     → force_pattern_inference=None (no-op)

Mirrors backend/tests/pipeline/test_pipeline_phase8.py fixture style 1:1.
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
    """Phase 8 패턴 정합 — phase08 fixture factory 박제 reuse."""
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


def _stub_download_video(tmp_video_path: str = "/tmp/__phase9.mp4"):
    """27-05 seam — `_download_analysis_video` mock. 경로 문자열 반환 (실 S3 접근 0)."""
    def _dl(bucket, key, *, timings_ms=None, analysis_id=""):
        return tmp_video_path

    return _dl


def _stub_extract_inputs(pipeline_mod, tmp_video_path: str = "/tmp/__phase9.mp4"):
    """27-05 seam — `_extract_video_analysis_inputs_from_local` mock factory (Phase 8 pattern
    정합). from_local stub — local_video_path/default_pole 기반."""
    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.pole_geometry import build_pole_axis_measurement

    def _impl(
        local_video_path, default_pole, *, keep_local_video=False,
        timings_ms=None, analysis_id="",  # Phase 27 SPD-01 — stage-timing kwargs (stub 무시)
    ):
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


def _patch_extract_inputs(monkeypatch, pipeline_mod, tmp_video_path: str = "/tmp/__phase9.mp4"):
    """27-05 seam 마이그레이션 — wrapper 단일 patch → 2-함수 patch 재배선 (stub 재배선만)."""
    monkeypatch.setattr(
        pipeline_mod, "_download_analysis_video", _stub_download_video(tmp_video_path)
    )
    monkeypatch.setattr(
        pipeline_mod,
        "_extract_video_analysis_inputs_from_local",
        _stub_extract_inputs(pipeline_mod, tmp_video_path),
    )


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
def base_mocks_mode3_first(monkeypatch):
    """Mode 3 분기 + prev=None → isFirst=True path. complete_analysis MagicMock."""
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


# ── Test 1: mode1 (MODE_EXPERT) path ─────────────────────────────────────


def test_mode1_path_emits_mode1_context(monkeypatch):
    """mode == MODE_EXPERT → modeContext='mode1'."""
    pipeline = _import_pipeline()
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_analysis",
        lambda uid, aid: {
            "mode": pipeline.models.MODE_EXPERT,
            "referenceMotionId": "ref-invert",
        },
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
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
    _patch_extract_inputs(monkeypatch, pipeline)

    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")

    kwargs = complete_mock.call_args.kwargs
    fpi = kwargs.get("force_pattern_inference")
    assert fpi is not None, "force_pattern_inference kwarg 누락"
    assert isinstance(fpi, dict)
    assert fpi.get("modeContext") == "mode1", f"modeContext mismatch: {fpi}"


# ── Test 2: mode3_first path (isFirst=True via prev=None) ────────────────


def test_mode3_first_path_emits_mode3_first_context(base_mocks_mode3_first):
    """MODE_SELF + prev=None → comparison['isFirst']=True → modeContext='mode3_first'."""
    pipeline, complete_mock = base_mocks_mode3_first
    # monkeypatch fixture 내부 정합 — _extract_video_analysis_inputs stub.
    import pytest as _pytest
    monkeypatch = _pytest.MonkeyPatch()
    _patch_extract_inputs(monkeypatch, pipeline)
    try:
        pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    finally:
        monkeypatch.undo()

    kwargs = complete_mock.call_args.kwargs
    fpi = kwargs.get("force_pattern_inference")
    assert fpi is not None
    assert fpi.get("modeContext") == "mode3_first", f"modeContext mismatch: {fpi}"


# ── Test 3: mode3_progress path (isFirst=False via prev populated) ───────


def test_mode3_progress_path_emits_mode3_progress_context(monkeypatch):
    """MODE_SELF + prev=populated → comparison['isFirst']=False → modeContext='mode3_progress'.

    _mode3_comparison 가 prev 의 angles + bodyNormalizationProfile 둘 다 있어야
    mode3_progress path 진입. prev 가 'angles' 만 있으면 dimensions.absolute
    path → assemble.build_mode3(is_first=False, ...).
    """
    pipeline = _import_pipeline()
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_analysis",
        lambda uid, aid: {"mode": pipeline.models.MODE_SELF},
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
    # prev 분석 박제 — angles 있어서 isFirst=False path 진입.
    prev_angles = np.full(60 * 8, 90.0).tolist()
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_previous_analysis",
        lambda uid, aid, mode=None: {
            "analysisId": "prev-a",
            "angles": prev_angles,
            "anglesJointKeys": list("abcdefgh"),
            "result": {"dimensionScores": {}},
        },
    )
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
    _patch_extract_inputs(monkeypatch, pipeline)

    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")

    kwargs = complete_mock.call_args.kwargs
    fpi = kwargs.get("force_pattern_inference")
    assert fpi is not None, "force_pattern_inference kwarg 누락"
    assert fpi.get("modeContext") == "mode3_progress", (
        f"modeContext mismatch: {fpi}"
    )


# ── Test 4: complete_analysis kwarg camelCase ────────────────────────────


def test_complete_analysis_kwarg_camelcase(base_mocks_mode3_first):
    """complete_analysis 호출 시 force_pattern_inference kwarg 가 camelCase keys
    (sourceSignal / jointHint / overallConfidence / modeContext) 포함.
    """
    pipeline, complete_mock = base_mocks_mode3_first
    import pytest as _pytest
    monkeypatch = _pytest.MonkeyPatch()
    _patch_extract_inputs(monkeypatch, pipeline)
    try:
        pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")
    finally:
        monkeypatch.undo()

    kwargs = complete_mock.call_args.kwargs
    fpi = kwargs.get("force_pattern_inference")
    assert isinstance(fpi, dict)
    # ForcePatternInference camelCase keys.
    for key in ("version", "findings", "overallConfidence", "modeContext", "warnings"):
        assert key in fpi, f"force_pattern_inference missing camelCase key {key}"
    # findings 가 비어도 list 여야 함.
    assert isinstance(fpi["findings"], list)
    # 만약 findings 가 있다면 ForcePatternFinding camelCase keys.
    for f in fpi["findings"]:
        for k in (
            "pattern",
            "phase",
            "sourceSignal",
            "reason",
            "interpretation",
            "confidence",
            "jointHint",
            "warnings",
        ):
            assert k in f, f"finding missing camelCase key {k}: {f}"


# ── Test 5: force_signals_report=None no-op ──────────────────────────────


def test_force_signals_none_path_passes_none(base_mocks_mode3_first, monkeypatch):
    """compute_force_signals 가 None 반환 시 force_pattern_inference=None 전달 (no-op)."""
    pipeline, complete_mock = base_mocks_mode3_first
    _patch_extract_inputs(monkeypatch, pipeline)
    # compute_force_signals mock → None 반환.
    monkeypatch.setattr(pipeline.fs, "compute_force_signals", lambda *a, **k: None)

    pipeline._process("bucket", "uploads/u/a.mp4", "u", "a")

    kwargs = complete_mock.call_args.kwargs
    fpi = kwargs.get("force_pattern_inference")
    assert fpi is None, f"force_signals None path 가 None 전달해야 함, got {fpi!r}"
    # 동시에 force_signals_report 도 None 전달.
    fsr = kwargs.get("force_signals_report")
    assert fsr is None
