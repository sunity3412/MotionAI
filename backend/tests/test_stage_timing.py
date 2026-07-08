"""Phase 27 SPD-01 — stage-timing 계측 단위 테스트 (27-RESEARCH Pattern 6).

박제 정신 (D-01 before/after 표의 데이터 소스):
  · `_stage` contextmanager 가 timings dict 에 int ms 를 누적하고
    `stage_timing analysis_id=%s stage=%s elapsed_ms=%d` 로그 라인을 방출한다
    (%-lazy 포맷 — [[never-log-secrets]] / 구조 로그 규율).
  · stage 블록 안에서 예외가 나도 elapsed 를 기록한 뒤 예외를 전파한다 (try/finally).
  · timings dict 는 `dict[str, int]` flat — `firestore_admin._validate_dict_only_scalars`
    통과 ([[firestore-nested-array-flat]] 정합, nested list/dict 없음).

전부 순수 함수 검증 — 실 S3 / 실 Firestore / 실 Gemini / 네트워크 호출 0.
PYTHONPATH=shared/python:. (pipeline/app.py 는 sys.path 주입으로 import).
"""

from __future__ import annotations

import importlib
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

# pipeline/app.py + shared layer path 주입 (test_pipeline_deduction_seam.py 관례).
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402
from sunity_shared import firestore_admin  # noqa: E402


def test_stage_records_int_ms_and_emits_log(caplog) -> None:
    """Test 1 — timings dict 에 int ms 누적 + stage_timing 로그 라인 방출."""
    timings: dict[str, int] = {}
    with caplog.at_level(logging.INFO):
        with app._stage(timings, "analysis-xyz", "s3_download"):
            pass

    # dict 에 int ms 가 기록됐다.
    assert "s3_download" in timings
    assert isinstance(timings["s3_download"], int)
    assert timings["s3_download"] >= 0

    # stage_timing 로그 라인이 방출됐다 (analysis_id + stage 포함).
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "stage_timing" in joined
    assert "analysis-xyz" in joined
    assert "s3_download" in joined


def test_stage_records_elapsed_then_reraises_on_exception() -> None:
    """Test 2 — stage 블록 안 예외가 elapsed 기록 후 전파된다 (try/finally)."""
    timings: dict[str, int] = {}

    class _Boom(RuntimeError):
        pass

    with pytest.raises(_Boom):
        with app._stage(timings, "analysis-err", "rtmw"):
            raise _Boom("stage 안 예외")

    # 예외가 나도 elapsed 가 finally 에서 기록됐다.
    assert "rtmw" in timings
    assert isinstance(timings["rtmw"], int)


def test_timings_dict_is_flat_scalar_only() -> None:
    """Test 3 — timings dict 는 flat dict[str, int] — _validate_dict_only_scalars 통과."""
    timings: dict[str, int] = {}
    for name in ("s3_download", "frame_extract", "rtmw", "dtw_scoring", "coach_dual"):
        with app._stage(timings, "analysis-flat", name):
            pass

    # nested list/dict 없음 — [[firestore-nested-array-flat]] 정합.
    firestore_admin._validate_dict_only_scalars(timings, path="result.timingsMs")
    # 모든 값이 int scalar.
    assert all(isinstance(v, int) for v in timings.values())
    assert len(timings) == 5


# ─────────────── 27-05 Task 2 — prefetch submit-before-rtmw 로그 순서 (HIGH-1) ───────────────
#
# 겹치기 수확의 필요조건: Gemini 업로드 prefetch submit 이 포즈(RTMW) 시작 **전**에
# 발생해야 한다. submit 이 RTMW 뒤면 겹칠 그늘이 없다(HIGH-1). 이 순서를 caplog 레코드
# 인덱스로 기계 검증한다 — `gemini_upload_prefetch_submit` 마커가 `stage=rtmw` 완료
# 로그보다 먼저 방출되는지. (프로덕션 실측 로그 순서 재검은 27-09 sweep.)


@dataclass
class _StubMoment:
    moment_key: str
    timestamp_seconds: float
    confidence: float
    frame_index: int = 0


class _StubExtractor:
    """GeminiMomentExtractor 호환 — extract_key_moments 만 (Gemini SDK 호출 0)."""

    def __init__(self) -> None:
        self._last_raw_response = '{"motion_name": "ref-foxtop"}'
        self._last_motion_name = "ref-foxtop"
        self.call_count = 0

    def extract_key_moments(self, video_uri, motion, *, preuploaded_handle=None):
        self.call_count += 1
        return [_StubMoment("hold", 5.0, 0.85)]


def _angles_8j(rows: int = 20):
    from sunity_shared.analysis.skeleton import JOINT_KEYS

    return np.full((rows, len(JOINT_KEYS)), 170.0)


def _reload_pipeline():
    sys.modules.pop("app", None)
    import app as _app  # noqa: WPS433

    return importlib.reload(_app)


def test_prefetch_submit_logged_before_rtmw(monkeypatch, caplog, tmp_path):
    """`gemini_upload_prefetch_submit` 마커가 `stage=rtmw` 로그보다 먼저 방출된다.

    _process 는 다운로드 직후 prefetch submit(마커) → 이후 frame_extract/RTMW 순으로
    실행하므로, from_local stub 이 방출하는 rtmw 로그보다 submit 마커가 앞서야 한다.
    submit 이 rtmw 뒤로 재배치되면 이 테스트가 FAIL 한다 (겹치기 수확 소멸 회귀 감지).
    """
    # RECOGNIZER_BACKEND=gemini → _gemini_enabled() True → keep_local_video=True →
    # prefetch_active (GEMINI_UPLOAD_PREFETCH default "1"). veto/scene 는 키 없어 graceful.
    monkeypatch.setenv("RECOGNIZER_BACKEND", "gemini")
    monkeypatch.setenv("GEMINI_UPLOAD_PREFETCH", "1")
    pipeline = _reload_pipeline()

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

    fake_video = tmp_path / "prefetch-order.mp4"

    def _fake_download(bucket, key, *, timings_ms=None, analysis_id=""):
        fake_video.write_bytes(b"fake video bytes")
        return str(fake_video)

    def _fake_from_local(
        local_video_path, default_pole, *, keep_local_video=False,
        timings_ms=None, analysis_id="",
    ):
        # 실제 from_local 처럼 rtmw stage 로그를 방출 (submit 마커보다 뒤여야 함).
        from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
        from sunity_shared.analysis.pole_geometry import build_pole_axis_measurement

        with pipeline._stage(
            timings_ms if timings_ms is not None else {}, analysis_id, "rtmw"
        ):
            pass
        profile = BodyNormalizationProfile(
            estimated_height_scale=1.0, arm_scale=1.0, leg_scale=1.0,
            torso_scale=1.0, shoulder_hip_ratio=1.0, confidence=0.0, warnings=["mock"],
        )
        return pipeline._VideoAnalysisInputs(
            angles=_angles_8j(),
            student_profile=profile,
            pose_frames=[],
            local_video_path=Path(local_video_path) if keep_local_video else None,
            pole_axis_measurement=build_pole_axis_measurement(
                axis_3d=default_pole, line=None, frame_index=None
            ),
            keypoints_4ch=np.zeros((_angles_8j().shape[0], 17, 4), dtype=float),
        )

    monkeypatch.setattr(pipeline, "_download_analysis_video", _fake_download)
    monkeypatch.setattr(
        pipeline, "_extract_video_analysis_inputs_from_local", _fake_from_local
    )

    recognizer = pipeline._ensure_recognizer()
    recognizer.extractor = _StubExtractor()
    recognizer.cache = None

    with caplog.at_level(logging.INFO):
        pipeline._process("test-bucket", "uploads/u1/order.mp4", "u1", "order")

    msgs = [r.getMessage() for r in caplog.records]
    submit_idx = next(
        (i for i, m in enumerate(msgs) if "gemini_upload_prefetch_submit" in m), None
    )
    rtmw_idx = next(
        (i for i, m in enumerate(msgs) if "stage=rtmw" in m), None
    )
    assert submit_idx is not None, "prefetch submit 마커 로그 미방출 (prefetch 비활성?)"
    assert rtmw_idx is not None, "rtmw stage 로그 미방출"
    assert submit_idx < rtmw_idx, (
        f"submit({submit_idx}) 가 rtmw({rtmw_idx}) 뒤 — HIGH-1 겹치기 수확 소멸 회귀"
    )
