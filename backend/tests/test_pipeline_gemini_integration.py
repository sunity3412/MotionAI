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

2026-09-20 계약 갱신 (동시 분석 오염 수리):
  recognizer / moment extractor 는 모듈 전역 싱글턴인데, 분석별 값(질의할 motion,
  미등록 수집 hook, Gemini 원문)을 **인스턴스 속성**에 써 두고 Gemini 왕복 + RTMW
  추론(실측 warm 51.3초 / cold 176.6초) **뒤에** 되읽었다. 학원처럼 동시 업로드가
  들어오면 그 창에서 뒤 분석이 앞 분석의 값을 덮어쓴다 — 예외도 로그도 없이 남의
  동작 이름으로 채점된다. 지금은 값이 호출 스택을 벗어나지 않도록 전부 인자/반환값이다.

  이 파일에서의 번역:
    · _StubExtractor 의 사이드카 속성(_last_raw_response / _last_motion_name) 폐기.
      주 메서드 extract_key_moments_with_response 가 (moments, raw_response) 를 반환.
    · raw motion name 은 이제 **질의 문자열** 이다. 프로덕션에서 그 필드의 유일한 쓰기가
      "호출자가 넘긴 motion" 이었으므로 Gemini 자체 분류명이 들어간 적이 없다. 따라서
      mode3(MODE_SELF) 분석의 raw motion name = 질의 "auto" → 미등록 경로가 정상이다.
    · 통합 관점 검증점 추가 — _process 가 recognize 에 motion_hint / unregistered_hook 을
      **인자로** 넘기는가. 속성 대입이 사라졌으니 여기가 전달을 볼 수 있는 유일한 지점이다.
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
    """GeminiMomentExtractor 호환 mock.

    2026-09-20 — 주 메서드가 extract_key_moments_with_response 이고 raw_response 를
    **반환값**으로 돌려준다 (사이드카 속성 _last_raw_response 는 동시 분석에서 서로를
    덮어써서 폐기). raw_motion_name 파라미터도 없앴다 — 그 이름은 이제 호출자가 넘긴
    질의 문자열이라 stub 이 따로 정할 수 있는 값이 아니다.

    받은 질의를 motion_queries 에 적어 둔다. 속성 대입 경로가 사라진 지금, _process 가
    recognize(motion_hint=...) 로 제대로 넘겼는지 볼 수 있는 곳이 여기뿐이다.
    """

    def __init__(
        self,
        *,
        moments: list,
        raw_response: str = "",
        raise_on_call: Exception | None = None,
    ) -> None:
        self._moments = list(moments)
        self._raw_response = raw_response
        self._raise = raise_on_call
        self.call_count = 0
        self.motion_queries: list[str] = []

    def extract_key_moments_with_response(
        self, video_uri: str, motion: str, *, preuploaded_handle=None
    ) -> tuple[list, str]:
        # 27-04: recognizer 가 preuploaded_handle 전달 → stub 수용 (무시).
        self.call_count += 1
        self.motion_queries.append(motion)
        if self._raise is not None:
            raise self._raise
        return list(self._moments), self._raw_response

    def extract_key_moments(
        self, video_uri: str, motion: str, *, preuploaded_handle=None
    ) -> list:
        """moments 만 쓰는 호출자용 호환 래퍼 — 실물(GeminiMomentExtractor)과 같은 모양."""
        moments, _raw = self.extract_key_moments_with_response(
            video_uri, motion, preuploaded_handle=preuploaded_handle
        )
        return moments


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


def _stub_download_video(tmp_video_path: str):
    """27-05 seam — `_download_analysis_video` mock. 실 S3 다운로드 대체: fake bytes 를
    tmp_video_path 에 write 하고 경로 문자열을 반환한다 (다운로드는 keep 여부와 무관하게
    항상 발생 — from_local stub 이 keep 여부로 unlink/None 결정)."""
    from pathlib import Path as _P

    def _dl(bucket, key, *, timings_ms=None, analysis_id=""):
        _P(tmp_video_path).write_bytes(b"fake video bytes")
        return tmp_video_path

    return _dl


def _stub_extract_inputs(pipeline_mod, tmp_video_path: str):
    """27-05 seam — `_extract_video_analysis_inputs_from_local` mock factory (RTMW 1회).

    2-함수 seam(27-05 Task 1) 마이그레이션: 기존 wrapper `_extract_video_analysis_inputs`
    단일 patch 를 다운로드 stub(`_stub_download_video`) + from_local stub 2개로 분리했다.
    이 factory 는 from_local 반환 stub — local_video_path/default_pole 기반. keep_local_video
    =True 시 local_video_path 유지, False 시 unlink + None (기존 delete=True 의미론).
    """
    from pathlib import Path as _P

    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.pole_geometry import build_pole_axis_measurement

    def _impl(
        local_video_path,
        default_pole,
        *,
        keep_local_video=False,
        timings_ms=None,  # Phase 27 SPD-01 — stage-timing 계측 kwargs (stub 은 무시)
        analysis_id="",
        unlink_on_error=True,  # WR-02 fix (27-REVIEW) — 시그니처 정합 (stub 무시)
    ):
        if keep_local_video:
            local_path = _P(local_video_path)
        else:
            _P(local_video_path).unlink(missing_ok=True)
            local_path = None
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


def _patch_unregistered_sink(monkeypatch, pipeline_mod) -> dict:
    """D-09 case 3 미등록 수집 sink 를 가로챈다 (실 Firestore 호출 0).

    2026-09-20 — mode3(MODE_SELF) 의 질의는 "auto" 이고, raw motion name = 질의 문자열이
    됐으므로 classify_motion_name 이 unregistered 로 판정한다. 즉 이 경로에서 hook 이
    실제로 발화한다. hook 이 **이 분석의** uid 를 물고 있는지가 곧 _process 의
    unregistered_hook 인자 전달 검증이다 — "anonymous-pipeline" 이 찍히면 전역 싱글턴의
    인스턴스 기본값이 샜다는 뜻이고, 다른 uid 가 찍히면 남의 분석 값이 넘어온 것이다.
    """
    recorded: dict = {"calls": []}

    def _record(keyword: str, *, uid: str, video_hash: str) -> None:
        recorded["calls"].append(
            {"keyword": keyword, "uid": uid, "video_hash": video_hash}
        )

    monkeypatch.setattr(
        pipeline_mod.firestore_admin, "record_unregistered_keyword", _record
    )
    return recorded


def _patch_extract_inputs(monkeypatch, pipeline_mod, tmp_video_path: str):
    """27-05 seam 마이그레이션 — wrapper 단일 patch → 2-함수 patch 재배선 (stub 재배선만,
    assert·검증 로직 무변경). _process 가 2단 호출로 전환된 뒤에도 실 S3 접근 0."""
    monkeypatch.setattr(
        pipeline_mod, "_download_analysis_video", _stub_download_video(tmp_video_path)
    )
    monkeypatch.setattr(
        pipeline_mod,
        "_extract_video_analysis_inputs_from_local",
        _stub_extract_inputs(pipeline_mod, tmp_video_path),
    )


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

    # Mock 27-05 2-함수 seam (다운로드 + from_local) — 실 S3 접근 0.
    fake_video = tmp_path / "fake.mp4"
    _patch_extract_inputs(monkeypatch, pipeline, str(fake_video))

    # Inject mock extractor into recognizer (recognizer is lazy — force creation)
    stub_ext = _StubExtractor(
        moments=[_StubMoment("hold", 5.0, 0.85)],
        raw_response='{"moments": [{"moment": "hold"}]}',
    )
    recognizer = pipeline._ensure_recognizer()
    recognizer.extractor = stub_ext  # 박제 mock 주입

    # Bypass cache (lookup 결과 None 박제)
    recognizer.cache = None  # in-memory only — Firestore 호출 회피

    # 2026-09-20 — mode3 질의 "auto" 는 미등록이라 D-09 case 3 hook 이 발화한다.
    # 실 Firestore 대신 sink 를 가로채 hook 이 들고 온 uid 를 본다.
    recorded = _patch_unregistered_sink(monkeypatch, pipeline)

    # 실행
    pipeline._process("test-bucket", "uploads/u1/a1.mp4", "u1", "a1")

    # 검증 — Gemini 추출 1회 호출
    assert stub_ext.call_count == 1, (
        f"Gemini 추출 호출 회수 박제 위반: {stub_ext.call_count}"
    )
    # 2026-09-20 — 질의 문자열은 _process 가 recognize(motion_hint=...) 로 넘긴 값에서
    # 온다. mode3(MODE_SELF) = motion 미상 → hint None → "auto". 전역 속성 경유가 아니라
    # 인자 경유임을 여기서 확인한다 (사이드카 속성이 사라져 다른 관측점이 없다).
    assert stub_ext.motion_queries == ["auto"], (
        f"motion_hint 전달 박제 위반 — 질의={stub_ext.motion_queries}"
    )
    # unregistered_hook 도 인자로 넘어왔는지 — hook 은 이 분석의 uid 를 물고 있어야 한다.
    # "anonymous-pipeline" = 전역 싱글턴의 인스턴스 기본값이 샌 것.
    assert [c["uid"] for c in recorded["calls"]] == ["u1"], (
        f"unregistered_hook 전달 박제 위반 — {recorded['calls']}"
    )


# ─────────────────── Test 2: env OFF → Fallback path (회귀 0) ───────────────────


def test_process_without_env_uses_fallback(base_mocks, monkeypatch):
    """env 미설정 → FallbackRecognizer + Gemini SDK 호출 0 박제 (회귀 0)."""
    pipeline = base_mocks

    # Fallback path 도 같은 2-함수 seam patch (keep_local_video=False → local_video_path None).
    _patch_extract_inputs(monkeypatch, pipeline, "/tmp/__unused_phase06.mp4")

    # Gemini SDK 호출이 들어오면 fail (회귀 검증 박제)
    sentinel_called = {"gemini_sdk_imported": False}

    def _import_should_not_happen(*args, **kwargs):
        sentinel_called["gemini_sdk_imported"] = True
        raise RuntimeError("회귀 박제 위반 — Gemini SDK 호출 발생")

    # google.genai patch — env OFF path 에선 import 자체가 들어가면 안 됨.
    # 2026-09-20 — Protocol 에 motion_hint / unregistered_hook 키워드 인자가 생겼다.
    # 스텁이 그 인자를 받아 적어 두면, Fallback 경로에서도 _process 가 (속성 대입이
    # 아니라) 인자로 넘기는지 확인할 수 있다.
    seen_kwargs: dict = {}

    def _fake_recognize(
        self,
        angles,
        frames=None,
        *,
        preuploaded_handle=None,
        motion_hint=None,
        unregistered_hook=None,
    ):
        seen_kwargs["called"] = True
        seen_kwargs["motion_hint"] = motion_hint
        seen_kwargs["unregistered_hook"] = unregistered_hook
        return pipeline.technique.TechniqueProfile(
            name="미상",
            category="unknown",
            joint_expectations={k: "bent_ok" for k in pipeline.skeleton.JOINT_KEYS},
            required_split_deg=None,
            requires_hold=True,
            is_symmetric=False,
        )

    monkeypatch.setattr(
        pipeline.technique.FallbackRecognizer, "recognize", _fake_recognize
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
    # 2026-09-20 — 분석-로컬 값이 인자로 도착했는지 (mode3 = motion 미상 → hint None,
    # 미등록 수집 hook 은 caller uid 를 문 클로저라 항상 전달된다).
    assert seen_kwargs.get("called") is True, "recognize 미호출 — 검증 전제 붕괴"
    assert seen_kwargs["motion_hint"] is None, (
        f"mode3 hint 박제 위반 — motion_hint={seen_kwargs['motion_hint']!r}"
    )
    assert callable(seen_kwargs["unregistered_hook"]), (
        "unregistered_hook 이 인자로 전달되지 않음 (전역 속성 경유 잔재 의심)"
    )


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
    _patch_extract_inputs(monkeypatch, pipeline, str(fake_video))

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

    # 임시 파일 박제 — 다운로드 stub 이 실제로 파일 생성 (keep_local_video=True 유지)
    fake_video = tmp_path / "cleanup-test.mp4"
    _patch_extract_inputs(monkeypatch, pipeline, str(fake_video))

    # 정상 Gemini 박제 (api_failure path 회피)
    stub_ext = _StubExtractor(
        moments=[_StubMoment("hold", 5.0, 0.85)],
        raw_response='{"moments": [{"moment": "hold"}]}',
    )
    recognizer = pipeline._ensure_recognizer()
    recognizer.extractor = stub_ext
    recognizer.cache = None
    # 2026-09-20 — mode3 질의 "auto" 는 미등록 경로라 수집 hook 이 발화한다.
    # 실 Firestore 대신 sink 가로채기 (이 테스트의 관심사는 임시 파일 cleanup).
    _patch_unregistered_sink(monkeypatch, pipeline)

    # 실행
    pipeline._process("test-bucket", "uploads/u4/a4.mp4", "u4", "a4")

    # 검증 — _process 종료 후 임시 파일 unlink 박제
    assert not fake_video.exists(), (
        f"tempfile cleanup 박제 위반 — {fake_video} 가 여전히 존재 "
        "(T-05-03-02 디스크 누수)"
    )
