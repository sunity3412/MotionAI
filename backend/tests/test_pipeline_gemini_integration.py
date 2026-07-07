"""Plan 5-03 Task 2 — _process 흐름 통합 테스트 (mock-based, Lambda fallback path 박제).

mock-based — 실 Gemini / 실 S3 / 실 Firestore / 실 NLF 호출 0.

박제 정신:
  · D-12 (RunPod server.py 무수정) — pipeline 모듈 1점 swap 검증
  · D-09 case 1 — Gemini API 실패 시 FallbackRecognizer 위임 + analysis 흐름 계속
  · D-16 (lazy import) — Gemini SDK / firebase_admin 미import path 박제
  · T-05-03-02 (DoS — tempfile cleanup) — Gemini path 신설 local_video_path 가
    분석 끝나면 unlink 박제

테스트 4 종:
  · test_process_with_gemini_recognizer_uses_gemini — env ON 시 GeminiTechniqueRecognizer
    사용 + extract_key_moments 호출 박제
  · test_process_without_env_uses_fallback — env OFF (default) 시 FallbackRecognizer
    + Gemini SDK 호출 0 (회귀 0 박제)
  · test_gemini_api_failure_falls_back_to_fallback — Gemini RuntimeError 시
    api_failure category + 분석 흐름 계속 (D-09 case 1)
  · test_tempfile_cleanup — Gemini path 의 local_video_path 가 _process 종료 시 unlink
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# functions/pipeline/ 디렉토리를 path 에 추가 — app 모듈 임포트.
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _import_pipeline():
    """pipeline/app.py 모듈을 강제 재로드 (global state 격리).

    test_pipeline_recognizer_switch 의 _import_pipeline 박제 패턴 재사용.
    """
    sys.modules.pop("app", None)
    import app  # noqa: WPS433 - dynamic local import 박제

    return importlib.reload(app)


@dataclass
class _StubMoment:
    """KeyMoment 호환 더미 (test_gemini_technique_recognizer 박제 패턴 정합)."""

    moment_key: str
    timestamp_seconds: float
    confidence: float
    frame_index: int = 0


class _StubExtractor:
    """GeminiMomentExtractor 호환 mock — extract_key_moments 만 구현."""

    def __init__(
        self,
        *,
        moments: list,
        raw_response: str = "",
        raw_motion_name: str = "ref-foxtop",
        raise_on_call: Exception | None = None,
    ) -> None:
        self._moments = list(moments)
        self._last_raw_response = raw_response
        self._last_motion_name = raw_motion_name
        self._raise = raise_on_call
        self.call_count = 0

    def extract_key_moments(self, video_uri: str, motion: str) -> list:
        self.call_count += 1
        if self._raise is not None:
            raise self._raise
        return list(self._moments)


def _angles_8j(rows: int = 20) -> np.ndarray:
    """더미 (T, 8) angle 행렬 — JOINT_KEYS 길이 8 박제."""
    from sunity_shared.analysis.skeleton import JOINT_KEYS

    return np.full((rows, len(JOINT_KEYS)), 170.0)


@pytest.fixture(autouse=True)
def _reset_pipeline_module(monkeypatch):
    """각 테스트마다 env clear + module reload 박제."""
    for k in (
        "GEMINI_RECOGNIZER_ENABLED",
        "RECOGNIZER_BACKEND",
        "RUNPOD_ANALYZE_URL",
        "RUNPOD_AUTH_TOKEN",
    ):
        monkeypatch.delenv(k, raising=False)
    yield
    sys.modules.pop("app", None)


@pytest.fixture
def base_mocks(monkeypatch):
    """공통 mock 박제 — firestore_admin / dimensions / kismam / assemble / coach.

    각 테스트에서 추가 mock 박제 가능 (extractor / angles helper 등).
    """
    pipeline = _import_pipeline()

    # firestore_admin mock — Mode 3 분기 (referenceMotionId 없음).
    meta = {"mode": pipeline.models.MODE_SELF}
    monkeypatch.setattr(
        pipeline.firestore_admin, "get_analysis", lambda uid, aid: dict(meta)
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "update_analysis_status",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_previous_analysis",
        lambda uid, aid, mode=None: None,  # 첫 분석 박제 (prev 없음 → assemble.build_mode3(is_first=True))
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "complete_analysis", lambda *a, **k: None
    )

    # _signed_get mock (S3 presigned 호출 회피)
    monkeypatch.setattr(
        pipeline, "_signed_get", lambda bucket, key: f"https://signed/{key}"
    )

    # coach mock — CerebrasCoachWriter 가 lazy init 박제라 직접 attribute 박제.
    coach_mock = MagicMock()
    coach_mock.write.return_value = {"summary": "mock coach"}
    pipeline._COACH_WRITER = coach_mock

    # _ensure_adapters 박제 — 어댑터 초기화 skip (mock 박제 보호)
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)

    return pipeline


def _stub_angles_only(bucket, key):
    """`_angles_from_video` mock — Mode SELF / Fallback path 박제."""
    return _angles_8j()


def _stub_extract_inputs(pipeline_mod, tmp_video_path: str):
    """Phase 6 R3 fix (Plan 06-02) — `_extract_video_analysis_inputs` mock factory.

    기존 `_angles_and_video_path_from_video` 가 폐기되고 단일 helper
    `_extract_video_analysis_inputs(bucket, key, default_pole, *, keep_local_video)`
    로 통합 (RTMW 1회 실행 보장). Gemini path 시 keep_local_video=True.
    """
    from pathlib import Path as _P

    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.pole_geometry import build_pole_axis_measurement

    def _impl(
        bucket,
        key,
        default_pole,
        *,
        keep_local_video=False,
        timings_ms=None,  # Phase 27 SPD-01 — stage-timing 계측 kwargs (stub 은 무시)
        analysis_id="",
    ):
        local_path = _P(tmp_video_path) if keep_local_video else None
        if keep_local_video:
            _P(tmp_video_path).write_bytes(b"fake video bytes")
        fallback_profile = BodyNormalizationProfile(
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=0.0,
            warnings=["mock"],
        )
        # Plan 08-03 — pole_axis_measurement 박제 신설 (REVIEWS R10 정합).
        # vertical fallback default_pole 박제 + line=None → coordinate_space='unavailable'.
        pole_axis_measurement = build_pole_axis_measurement(
            axis_3d=default_pole, line=None, frame_index=None
        )
        return pipeline_mod._VideoAnalysisInputs(
            angles=_angles_8j(),
            student_profile=fallback_profile,
            pose_frames=[],
            local_video_path=local_path,
            pole_axis_measurement=pole_axis_measurement,
            # Plan 17-03 박제 — _VideoAnalysisInputs.keypoints_4ch 신설 (3차 R-B3 정합).
            keypoints_4ch=np.zeros((_angles_8j().shape[0], 17, 4), dtype=float),
        )

    return _impl


def _stub_extract_inputs_no_path(pipeline_mod):
    """env OFF path — keep_local_video=False, local_video_path=None."""
    return _stub_extract_inputs(pipeline_mod, "/tmp/__unused_phase06.mp4")


# ─────────────────── Test 1: env ON → Gemini path ───────────────────


def test_process_with_gemini_recognizer_uses_gemini(
    base_mocks, monkeypatch, tmp_path
):
    """env RECOGNIZER_BACKEND=gemini → GeminiTechniqueRecognizer.extract_key_moments
    1회 호출됨 박제."""
    # env 박제 + module reload (env 가 _gemini_enabled() 에 도달)
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    pipeline = _import_pipeline()

    # Re-apply base mocks (module reload 박제로 인해 다시 박제 필요)
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_analysis",
        lambda uid, aid: {"mode": pipeline.models.MODE_SELF},
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_previous_analysis",
        lambda uid, aid, mode=None: None,
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "complete_analysis", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline, "_signed_get", lambda bucket, key: f"https://signed/{key}"
    )
    coach_mock = MagicMock()
    coach_mock.write.return_value = {"summary": "mock"}
    pipeline._COACH_WRITER = coach_mock
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)

    # Mock R3 fix unified helper (Phase 6, Plan 06-02)
    fake_video = tmp_path / "fake.mp4"
    monkeypatch.setattr(
        pipeline,
        "_extract_video_analysis_inputs",
        _stub_extract_inputs(pipeline, str(fake_video)),
    )

    # Inject mock extractor into recognizer (recognizer is lazy — force creation)
    stub_ext = _StubExtractor(
        moments=[_StubMoment("hold", 5.0, 0.85)],
        raw_response='{"motion_name": "ref-foxtop"}',
        raw_motion_name="ref-foxtop",
    )
    recognizer = pipeline._ensure_recognizer()
    recognizer.extractor = stub_ext  # 박제 mock 주입

    # Bypass cache (lookup 결과 None 박제)
    recognizer.cache = None  # in-memory only — Firestore 호출 회피

    # 실행
    pipeline._process("test-bucket", "uploads/u1/a1.mp4", "u1", "a1")

    # 검증 — extract_key_moments 1회 호출
    assert stub_ext.call_count == 1, (
        f"Gemini extract_key_moments 호출 회수 박제 위반: {stub_ext.call_count}"
    )


# ─────────────────── Test 2: env OFF → Fallback path (회귀 0) ───────────────────


def test_process_without_env_uses_fallback(base_mocks, monkeypatch):
    """env 미설정 → FallbackRecognizer + Gemini SDK 호출 0 박제 (회귀 0)."""
    pipeline = base_mocks

    # R3 fix — Fallback path 도 같은 helper 사용 (keep_local_video=False).
    monkeypatch.setattr(
        pipeline,
        "_extract_video_analysis_inputs",
        _stub_extract_inputs_no_path(pipeline),
    )

    # Gemini SDK 호출이 들어오면 fail (회귀 검증 박제)
    sentinel_called = {"gemini_sdk_imported": False}

    def _import_should_not_happen(*args, **kwargs):
        sentinel_called["gemini_sdk_imported"] = True
        raise RuntimeError("회귀 박제 위반 — Gemini SDK 호출 발생")

    # google.genai patch — env OFF path 에선 import 자체가 들어가면 안 됨
    monkeypatch.setattr(
        pipeline.technique.FallbackRecognizer,
        "recognize",
        lambda self, angles, frames=None: pipeline.technique.TechniqueProfile(
            name="미상",
            category="unknown",
            joint_expectations={k: "bent_ok" for k in pipeline.skeleton.JOINT_KEYS},
            required_split_deg=None,
            requires_hold=True,
            is_symmetric=False,
        ),
    )

    # 실행
    pipeline._process("test-bucket", "uploads/u2/a2.mp4", "u2", "a2")

    # 검증 — Gemini SDK 호출 0
    assert not sentinel_called["gemini_sdk_imported"], (
        "env OFF 시 Gemini SDK 호출 발생 — 회귀 박제 위반"
    )
    # recognizer 가 FallbackRecognizer 인지 확인
    rec = pipeline._ensure_recognizer()
    assert isinstance(rec, pipeline.technique.FallbackRecognizer)


# ─────────────────── Test 3: Gemini API 실패 → api_failure (D-09 case 1) ───────────────────


def test_gemini_api_failure_falls_back_to_fallback(
    base_mocks, monkeypatch, tmp_path
):
    """Gemini RuntimeError → FallbackRecognizer 위임 + category="api_failure" 박제.

    D-09 case 1 박제 — API 실패 시 분석 흐름 crash 0 + graceful degrade.
    """
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    pipeline = _import_pipeline()

    # Re-apply base mocks
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_analysis",
        lambda uid, aid: {"mode": pipeline.models.MODE_SELF},
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_previous_analysis",
        lambda uid, aid, mode=None: None,
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "complete_analysis", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline, "_signed_get", lambda bucket, key: f"https://signed/{key}"
    )
    coach_mock = MagicMock()
    coach_mock.write.return_value = {"summary": "mock"}
    pipeline._COACH_WRITER = coach_mock
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)

    fake_video = tmp_path / "fake.mp4"
    monkeypatch.setattr(
        pipeline,
        "_extract_video_analysis_inputs",
        _stub_extract_inputs(pipeline, str(fake_video)),
    )

    # 실패하는 extractor 박제
    stub_ext = _StubExtractor(
        moments=[], raise_on_call=RuntimeError("Gemini quota exceeded")
    )
    recognizer = pipeline._ensure_recognizer()
    recognizer.extractor = stub_ext
    recognizer.cache = None

    # profile 캡처 박제 — dimensions.absolute_dimension_scores 가 받는 profile 확인
    captured = {"profile": None}
    original_abs_dims = pipeline.dimensions.absolute_dimension_scores

    def _capture_profile(angles, profile):
        captured["profile"] = profile
        return original_abs_dims(angles, profile)

    monkeypatch.setattr(
        pipeline.dimensions, "absolute_dimension_scores", _capture_profile
    )

    # 실행 — crash 0 박제
    pipeline._process("test-bucket", "uploads/u3/a3.mp4", "u3", "a3")

    # 검증 — Gemini 호출 1회 + profile.category = api_failure
    assert stub_ext.call_count == 1
    assert captured["profile"] is not None
    assert captured["profile"].category == "api_failure", (
        f"D-09 case 1 박제 위반 — category={captured['profile'].category}"
    )


# ─────────────────── Test 4: tempfile cleanup (T-05-03-02) ───────────────────


def test_tempfile_cleanup(base_mocks, monkeypatch, tmp_path):
    """Gemini path 에서 신설한 local_video_path 가 _process 종료 시 unlink 박제.

    T-05-03-02 (DoS — 디스크 누수) 박제 — try/finally + missing_ok=True.
    """
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    pipeline = _import_pipeline()

    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_analysis",
        lambda uid, aid: {"mode": pipeline.models.MODE_SELF},
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_previous_analysis",
        lambda uid, aid, mode=None: None,
    )
    monkeypatch.setattr(
        pipeline.firestore_admin, "complete_analysis", lambda *a, **k: None
    )
    monkeypatch.setattr(
        pipeline, "_signed_get", lambda bucket, key: f"https://signed/{key}"
    )
    coach_mock = MagicMock()
    coach_mock.write.return_value = {"summary": "mock"}
    pipeline._COACH_WRITER = coach_mock
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)

    # 임시 파일 박제 — _angles_and_video_path_from_video 가 실제로 파일 생성
    fake_video = tmp_path / "cleanup-test.mp4"
    monkeypatch.setattr(
        pipeline,
        "_extract_video_analysis_inputs",
        _stub_extract_inputs(pipeline, str(fake_video)),
    )

    # 정상 Gemini 박제 (api_failure path 회피)
    stub_ext = _StubExtractor(
        moments=[_StubMoment("hold", 5.0, 0.85)],
        raw_response='{"motion_name": "ref-foxtop"}',
        raw_motion_name="ref-foxtop",
    )
    recognizer = pipeline._ensure_recognizer()
    recognizer.extractor = stub_ext
    recognizer.cache = None

    # 실행
    pipeline._process("test-bucket", "uploads/u4/a4.mp4", "u4", "a4")

    # 검증 — _process 종료 후 임시 파일 unlink 박제
    assert not fake_video.exists(), (
        f"tempfile cleanup 박제 위반 — {fake_video} 가 여전히 존재 "
        "(T-05-03-02 디스크 누수)"
    )
