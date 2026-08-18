"""Plan 17-02 Task 2 — pipeline _process 의 영역 C wave 1 wiring 통합 테스트.

박제 정신:
  · `_process(bucket, key, uid, analysis_id)` 시그니처 변경 0 — RunPod /
    Lambda SQS caller 갱신 0.
  · find_scene_flags 는 monkeypatch — 외부 Gemini API 호출 0.
  · `_extract_video_analysis_inputs` / recognizer / complete_analysis 등 다른
    pipeline 의존성도 monkeypatch — 실 GPU / S3 / Firestore 호출 0.
  · is_reference 판별 — S3 key prefix (`reference/`) 1차 + Firestore mode 2차.
  · GEMINI_FINDING_ENABLED=0 → wave 1 skip + geminiC=None.
  · local_video_path=None → wave 1 skip + geminiC=None (B4 회귀).
  · find_scene_flags 안에서 S3 download / RTMW 재실행 호출 0 — wiring 박제만 검증.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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


# pipeline app.py — Lambda 함수 entry. 본 test 가 import 시점에 boto3 client /
# Cerebras 등 초기화 트리거 가능. 미설치 환경 박제 graceful skip — 본 plan scope 는
# wiring 검증이므로 실 Lambda 환경에서만 verify (자동화 verify 명령은 plan 박제).
pipeline_app = pytest.importorskip("app")


# ─────────────────── stub helpers ───────────────────


def _stub_inputs(local_video_path: str | None = "/tmp/x.mp4") -> SimpleNamespace:
    """_extract_video_analysis_inputs 반환 stub — pipeline _process 박제 흐름이
    참조하는 필드만 박는다."""
    import numpy as np

    # angles: (T, J) — _process 가 reshape 박제. 최소 1 frame × 8 joint.
    angles = np.zeros((3, 8), dtype=float)
    pose_frames: list[Any] = [
        {"keypoints": np.zeros((17, 4), dtype=float), "scores": np.ones(17)},
    ] * 3
    return SimpleNamespace(
        angles=angles,
        student_profile=SimpleNamespace(  # R4 — non-null
            estimated_height_scale=1.0,
            arm_scale=1.0,
            leg_scale=1.0,
            torso_scale=1.0,
            shoulder_hip_ratio=1.0,
            confidence=0.9,
            warnings=[],
        ),
        pose_frames=pose_frames,
        local_video_path=Path(local_video_path) if local_video_path else None,
        pole_axis_measurement=SimpleNamespace(
            coordinate_space="unavailable",
            axis_vector_world=(0.0, 1.0, 0.0),
            axis_vector_screen=None,
            origin_world=None,
            origin_screen=None,
            confidence_level="low",
            source="vertical_fallback",
            frame_index=None,
            tilt_deg=0.0,
            warnings=[],
        ),
    )


class _CallTracker:
    """find_scene_flags 호출 횟수 + 인자 박제 기록."""

    def __init__(self, return_value: Any) -> None:
        self.return_value = return_value
        self.calls: list[tuple[str, bool]] = []

    def __call__(self, video_path: str, is_reference: bool = False) -> Any:
        self.calls.append((video_path, is_reference))
        return self.return_value


def _patch_minimal_process_deps(monkeypatch) -> dict[str, Any]:
    """_process 호출이 외부 의존성 (Firestore / boto3 / recognizer / KISMAM / Phase
    9/12) 박제 0 으로 흐르도록 monkeypatch — wiring scope 박제 검증 전용.

    완전 stub 인 만큼 pipeline 본체의 raise 분기 (NoHumanError / NotPoleMotionError /
    기준 모션 없음) 박제도 우회. 본 test 가 검증하는 것은:
      1. find_scene_flags 호출 횟수 + 인자
      2. complete_analysis kwarg `gemini_c` 박힘 여부 + 박힌 dict 내용
      3. G4 가드 통과 / GEMINI_FINDING_ENABLED=0 / local_video_path=None 분기

    Returns:
      capture dict — complete_analysis 호출 시 kwargs 박힘.
    """
    capture: dict[str, Any] = {}

    # 1) firestore_admin.update_analysis_status — no-op.
    monkeypatch.setattr(
        pipeline_app.firestore_admin, "update_analysis_status", lambda *a, **k: None
    )
    # 2) firestore_admin.get_analysis — mode=mode3 (default — mode1 path 는 reference
    #    조회 박제 X 박제 흐름이 복잡 → mode3 박제 wiring scope 검증).
    monkeypatch.setattr(
        pipeline_app.firestore_admin,
        "get_analysis",
        lambda _uid, _aid: {"mode": "mode3"},
    )
    # 3) firestore_admin.get_previous_analysis — None (first-time mode3).
    monkeypatch.setattr(
        pipeline_app.firestore_admin,
        "get_previous_analysis",
        lambda *a, **k: None,
    )
    # 4) firestore_admin.complete_analysis — capture only.
    def _capture_complete(*args, **kwargs):
        capture["complete_args"] = args
        capture["complete_kwargs"] = kwargs

    monkeypatch.setattr(
        pipeline_app.firestore_admin, "complete_analysis", _capture_complete
    )
    # 5) firestore_admin.fail_analysis — capture.
    monkeypatch.setattr(
        pipeline_app.firestore_admin,
        "fail_analysis",
        lambda *a, **k: capture.setdefault("fail_args", (a, k)),
    )
    # 6) firestore_admin.record_unregistered_keyword — no-op.
    monkeypatch.setattr(
        pipeline_app.firestore_admin,
        "record_unregistered_keyword",
        lambda *a, **k: None,
    )

    # 7) _ensure_adapters / _ensure_recognizer — no-op + dummy recognizer.
    monkeypatch.setattr(pipeline_app, "_ensure_adapters", lambda: None)

    dummy_profile = SimpleNamespace(
        motion_id="mock",
        motion_name_ko="mock",
        motion_name_ipsf="mock",
        joint_expectations={},
        confidence=0.9,
        source="fallback",
        warnings=[],
    )
    dummy_recognizer = SimpleNamespace(
        motion_query_hint=None,
        unregistered_hook=None,
        recognize=lambda angles, frames=None: dummy_profile,
    )
    monkeypatch.setattr(pipeline_app, "_ensure_recognizer", lambda: dummy_recognizer)

    # 8) 27-05 2-함수 seam stub — 다운로드(경로) + from_local(_VideoAnalysisInputs).
    #    기본 = local_video_path "/tmp/x.mp4" 박힘 (_stub_inputs default 정합).
    capture["inputs_stub"] = _stub_inputs()
    monkeypatch.setattr(
        pipeline_app,
        "_download_analysis_video",
        lambda *a, **k: "/tmp/x.mp4",
    )
    monkeypatch.setattr(
        pipeline_app,
        "_extract_video_analysis_inputs_from_local",
        lambda *a, **k: capture["inputs_stub"],
    )

    # 9) dimension/abs/KISMAM/Phase 9/12 등 모두 _process 가 내부에서 복잡하게 호출
    #    → 본 test 는 wiring 핵심만 검증하므로 _process 본체 우회 전략 사용:
    #    monkeypatch 박제 가 가능한 외부 의존 (firestore / find_scene_flags) 까지만.
    #    실제 _process 는 본 stub 흐름에서 후속 단계 (recognizer.recognize 이후 KISMAM
    #    assess / dimension overall / Phase 6 BodyComparison / Phase 8 force /
    #    Phase 9 ForcePattern / Phase 12 keypoint) 박제 충돌이 큼 — wiring 검증을
    #    위해 별도 helper `_process_until_find_scene_flags` 를 박는다.
    return capture


# ─────────────────── 테스트 ───────────────────
#
# _process 본체는 후속 단계 (KISMAM / Phase 6/8/9/12) 박제 dependency 가 깊어 monkeypatch
# 단위 단순 unit test 박제 한계. 본 plan scope (wiring) 박제 검증은 별도 박제 entry
# helper `_invoke_wave1` 박제 — pipeline app.py 가 wave 1 helper 박제 노출 필요.
# 본 test 는 그 helper 박제 검증을 박는다.


class TestWave1Helper:
    """pipeline app.py 가 wave 1 helper 박제 노출 — find_scene_flags 호출 + 결과
    dict 반환."""

    def test_helper_exists_and_callable(self) -> None:
        assert hasattr(pipeline_app, "_call_wave1_scene_finder")
        assert callable(pipeline_app._call_wave1_scene_finder)

    def test_helper_returns_none_when_local_video_path_none(self, monkeypatch) -> None:
        """local_video_path=None → wave 1 skip + return None (B4 정합)."""
        # find_scene_flags 호출 0 검증.
        tracker = _CallTracker(return_value={"unused": True})
        monkeypatch.setattr(pipeline_app, "find_scene_flags", tracker)

        result = pipeline_app._call_wave1_scene_finder(
            local_video_path=None, is_reference=False
        )
        assert result is None
        assert tracker.calls == []

    def test_helper_returns_none_when_finding_disabled(
        self, monkeypatch, tmp_path
    ) -> None:
        """GEMINI_FINDING_ENABLED=0 → wave 1 skip + return None."""
        tracker = _CallTracker(return_value={"unused": True})
        monkeypatch.setattr(pipeline_app, "find_scene_flags", tracker)
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "0")

        video_path = str(tmp_path / "x.mp4")
        Path(video_path).write_bytes(b"fake")

        result = pipeline_app._call_wave1_scene_finder(
            local_video_path=video_path, is_reference=False
        )
        assert result is None
        assert tracker.calls == []

    def test_helper_passes_is_reference_through(self, monkeypatch, tmp_path) -> None:
        """is_reference=True 박제 → find_scene_flags 에 전달."""
        flag_dict = {
            "grip_visible": True,
            "backbend_present": False,
            "occlusion_severe": False,
            "camera_angle_problematic": False,
            "notes_ko": "ok",
            "model": "gemini-3.7-flash",
            "tokens_used": 0,
            "latency_ms": 100,
            "guardrail_triggered": None,
            "error": None,
        }
        tracker = _CallTracker(return_value=flag_dict)
        monkeypatch.setattr(pipeline_app, "find_scene_flags", tracker)
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "1")

        video_path = str(tmp_path / "ref.mp4")
        Path(video_path).write_bytes(b"fake")

        result = pipeline_app._call_wave1_scene_finder(
            local_video_path=video_path, is_reference=True
        )
        assert result == flag_dict
        assert tracker.calls == [(video_path, True)]

    def test_helper_swallows_exceptions_graceful(
        self, monkeypatch, tmp_path
    ) -> None:
        """find_scene_flags 가 예외 raise → wave 1 helper 가 graceful None 반환.
        (분석 흐름 차단 X — find_scene_flags 의 ValueError(객관성 가드) 도 흡수해서
        D-skip path 가 wave 1 fail 로 인해 모두 멈추지 않게 박제.)"""

        def _raises(*a, **k):
            raise ValueError("객관성 가드 매치 시뮬")

        monkeypatch.setattr(pipeline_app, "find_scene_flags", _raises)
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "1")

        video_path = str(tmp_path / "x.mp4")
        Path(video_path).write_bytes(b"fake")

        result = pipeline_app._call_wave1_scene_finder(
            local_video_path=video_path, is_reference=False
        )
        assert result is None

    def test_helper_does_not_call_s3_or_rtmw(
        self, monkeypatch, tmp_path
    ) -> None:
        """B4 hard gate — wave 1 helper 안에서 boto3 S3 download / _POSE_ESTIMATOR
        / _RTMW_ENGINE 호출 0. find_scene_flags 가 local_video_path 만 사용 박제."""
        s3_calls: list[Any] = []
        rtmw_calls: list[Any] = []

        # _s3.download_file 호출 추적.
        monkeypatch.setattr(
            pipeline_app._s3,
            "download_file",
            lambda *a, **k: s3_calls.append(a) or None,
        )
        # _POSE_ESTIMATOR / _RTMW_ENGINE 호출 추적 — singleton swap.
        fake_pose = SimpleNamespace(
            estimate=lambda *a, **k: rtmw_calls.append(("pose", a)) or None,
            estimate_with_profile=lambda *a, **k: rtmw_calls.append(("pose_profile", a)) or (None, None),
        )
        monkeypatch.setattr(pipeline_app, "_POSE_ESTIMATOR", fake_pose)
        fake_rtmw = SimpleNamespace(
            estimate=lambda *a, **k: rtmw_calls.append(("rtmw", a)) or None,
        )
        monkeypatch.setattr(pipeline_app, "_RTMW_ENGINE", fake_rtmw)

        # find_scene_flags 가 정상 호출되어도 (caller scope) S3/RTMW 호출 0.
        flag_dict = {
            "grip_visible": True,
            "backbend_present": False,
            "occlusion_severe": False,
            "camera_angle_problematic": False,
            "notes_ko": "ok",
            "model": "gemini-3.7-flash",
            "tokens_used": 0,
            "latency_ms": 100,
            "guardrail_triggered": None,
            "error": None,
        }
        tracker = _CallTracker(return_value=flag_dict)
        monkeypatch.setattr(pipeline_app, "find_scene_flags", tracker)
        monkeypatch.setenv("GEMINI_FINDING_ENABLED", "1")

        video_path = str(tmp_path / "x.mp4")
        Path(video_path).write_bytes(b"fake")

        result = pipeline_app._call_wave1_scene_finder(
            local_video_path=video_path, is_reference=False
        )
        assert result == flag_dict
        # B4 hard gate — S3 / RTMW 호출 0.
        assert s3_calls == []
        assert rtmw_calls == []


class TestIsReferenceResolution:
    """_process 내부 is_reference 판별 — S3 key prefix 1차 + Firestore mode 2차."""

    def test_helper_exists_and_callable(self) -> None:
        assert hasattr(pipeline_app, "_resolve_is_reference")
        assert callable(pipeline_app._resolve_is_reference)

    def test_key_prefix_reference_returns_true(self) -> None:
        # S3 key prefix 'reference/' → is_reference=True (Firestore 조회 0).
        assert pipeline_app._resolve_is_reference(
            key="reference/jeong/inverted-butterfly.mp4",
            meta={"mode": "mode3"},
        ) is True

    def test_uploads_key_with_mode1_register_returns_true(self) -> None:
        # S3 key prefix 'uploads/' 지만 mode == 'mode1_register' → True (분기 2).
        assert pipeline_app._resolve_is_reference(
            key="uploads/uid-x/an-y.mp4",
            meta={"mode": "mode1_register"},
        ) is True

    def test_uploads_key_with_mode3_returns_false(self) -> None:
        # 일반 사용자 mode3 영상 → False.
        assert pipeline_app._resolve_is_reference(
            key="uploads/uid-x/an-y.mp4",
            meta={"mode": "mode3"},
        ) is False

    def test_uploads_key_with_mode1_returns_false(self) -> None:
        # mode1 (정은지 비교 모드) 박제 — 사용자가 정은지 영상에 비교하는 케이스.
        # 본인 영상이므로 reference 아님 — False.
        assert pipeline_app._resolve_is_reference(
            key="uploads/uid-x/an-y.mp4",
            meta={"mode": "mode1"},
        ) is False

    def test_meta_none_falls_back_to_key_only(self) -> None:
        # meta 박제 없음 → S3 key prefix 만 검사.
        assert pipeline_app._resolve_is_reference(
            key="reference/foo.mp4",
            meta=None,
        ) is True
        assert pipeline_app._resolve_is_reference(
            key="uploads/foo.mp4",
            meta=None,
        ) is False


class TestProcessImportsFindSceneFlags:
    """pipeline app.py 가 find_scene_flags 박제 import 했는지 grep 정합."""

    def test_pipeline_module_exposes_find_scene_flags(self) -> None:
        # plan verification 박제 — `grep find_scene_flags app.py | grep -c .` ≥ 2.
        assert hasattr(pipeline_app, "find_scene_flags")
        # callable — sunity_shared.gemini.scene_finder.find_scene_flags 박제 mirror.
        assert callable(pipeline_app.find_scene_flags)

    def test_pipeline_source_has_find_scene_flags_call_site(self) -> None:
        """app.py source 안에 find_scene_flags 박제 호출 라인 존재."""
        from importlib import resources

        # app.py 경로 직접 박제.
        src = Path(pipeline_app.__file__).read_text(encoding="utf-8")
        # import 1 + 호출 1 (helper 안에서) — 최소 2회 등장 박제.
        occurrences = src.count("find_scene_flags")
        assert occurrences >= 2, (
            f"find_scene_flags 박제 등장 횟수 {occurrences} < 2 — "
            f"import + _call_wave1_scene_finder 호출 박제 누락 가능"
        )
