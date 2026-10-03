"""quick-261003-qmg — 기준 영상 Gemini 업로드 prefetch + scene_finder join 이동 테스트.

목적:
  mode1 분석은 veto 직전에 기준 영상(v1 ≈100MB)을 S3 에서 받고 Gemini File API 에
  새로 올린다. 38-14 Pod 로그(.planning/phases/38-supplier-link/evidence/
  runpod_server_38_14_1002.log)에서 이 업로드+ACTIVE 폴링이 ≈42초였고, 어느
  stage_timing 에도 잡히지 않았다(메모리 analysis-time-reference-gemini-reupload-42s).
  이 테스트는 그 업로드를 학생 영상 다운로드 직후 백그라운드로 옮긴 장치와,
  scene_finder join 을 recognizer 앞에서 첫 소비처(_build_coach_context) 직전으로
  옮긴 배선을 잠근다.

  1부 — 모듈 수준 헬퍼 5개의 계약(어떤 입력에도 raise 하지 않는다).
  2부 — `_process` 통합(prefetch on/off · mode1/mode3 · key 불일치 · prefetch 실패 ·
        조기 실패 정리 순서 · scene join 위치).

전부 stub — 실 S3 / 실 Firestore / 실 Gemini / 네트워크 호출 0. future 는 스레드 없이
`concurrent.futures.Future()` 에 set_result / set_exception 으로 만든다(1부).
"""

from __future__ import annotations

import importlib
import os
import sys
from concurrent.futures import Future
from pathlib import Path

import pytest

# pipeline/app.py + shared layer path 주입 (test_stage_timing.py 관례).
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
for _p in (_PIPELINE, _SHARED):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import app  # noqa: E402,F401 - 경로 주입 뒤 import (아래 fixture 가 매 테스트 재적재)


_ENV_KEYS = (
    "GEMINI_VISION_VETO_ENABLED",
    "GEMINI_UPLOAD_PREFETCH",
    "GEMINI_RECOGNIZER_ENABLED",
    "RECOGNIZER_BACKEND",
    "RUNPOD_ANALYZE_URL",
    "RUNPOD_AUTH_TOKEN",
    "FORCE_SIGNALS_LAYER2_ENABLED",
    "PREFLIGHT_LABEL_GATE_PASSED",
)


@pytest.fixture
def pipeline(monkeypatch):
    """env 리셋 뒤 app 모듈을 새로 적재 (모듈 싱글턴 · 토글 잔재 차단)."""
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    sys.modules.pop("app", None)
    import app as _app  # noqa: WPS433

    mod = importlib.reload(_app)
    yield mod
    sys.modules.pop("app", None)


def _done_future(value) -> Future:
    fut: Future = Future()
    fut.set_result(value)
    return fut


def _failed_future(exc: BaseException) -> Future:
    fut: Future = Future()
    fut.set_exception(exc)
    return fut


# ═══════════════════════════ 1부 — 헬퍼 단위 테스트 ═══════════════════════════


# ── _reference_prefetch_wanted ───────────────────────────────────────────────


def test_wanted_mode1_veto_on_with_id(pipeline, monkeypatch):
    monkeypatch.setenv("GEMINI_VISION_VETO_ENABLED", "1")
    assert pipeline._reference_prefetch_wanted(pipeline.models.MODE_EXPERT, "ref-x") is True


def test_wanted_false_when_veto_off(pipeline, monkeypatch):
    monkeypatch.delenv("GEMINI_VISION_VETO_ENABLED", raising=False)
    assert pipeline._reference_prefetch_wanted(pipeline.models.MODE_EXPERT, "ref-x") is False


def test_wanted_false_for_mode3(pipeline, monkeypatch):
    monkeypatch.setenv("GEMINI_VISION_VETO_ENABLED", "1")
    assert pipeline._reference_prefetch_wanted(pipeline.models.MODE_SELF, "ref-x") is False


@pytest.mark.parametrize("missing_id", [None, ""])
def test_wanted_false_without_reference_id(pipeline, monkeypatch, missing_id):
    monkeypatch.setenv("GEMINI_VISION_VETO_ENABLED", "1")
    assert (
        pipeline._reference_prefetch_wanted(pipeline.models.MODE_EXPERT, missing_id)
        is False
    )


# ── _prefetch_reference_video ────────────────────────────────────────────────


def test_prefetch_downloads_reference_key_to_suffixed_temp(pipeline, monkeypatch):
    key = "reference/ref-x/v1.mov"
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_reference_motion",
        lambda mid: {"motionId": mid, "videoS3Key": key},
    )
    calls: list[tuple[str, str, str]] = []

    def _dl(bucket, k, dest):
        calls.append((bucket, k, dest))
        Path(dest).write_bytes(b"ref bytes")

    monkeypatch.setattr(pipeline, "_s3_download", _dl)

    out = pipeline._prefetch_reference_video("bkt", "ref-x")
    try:
        assert out is not None
        got_key, dest = out
        assert got_key == key
        assert calls == [("bkt", key, dest)]
        assert dest.endswith(".mov")
        assert Path(dest).exists()
    finally:
        if out is not None:
            Path(out[1]).unlink(missing_ok=True)


@pytest.mark.parametrize(
    "doc",
    [None, {"motionId": "ref-x"}, {"motionId": "ref-x", "videoS3Key": None}],
    ids=["doc-none", "key-absent", "key-none"],
)
def test_prefetch_none_without_video_key(pipeline, monkeypatch, doc):
    monkeypatch.setattr(pipeline.firestore_admin, "get_reference_motion", lambda mid: doc)
    calls: list = []
    monkeypatch.setattr(pipeline, "_s3_download", lambda *a: calls.append(a))

    assert pipeline._prefetch_reference_video("bkt", "ref-x") is None
    assert calls == []


def test_prefetch_none_when_reference_read_raises(pipeline, monkeypatch):
    def _boom(mid):
        raise RuntimeError("firestore down")

    monkeypatch.setattr(pipeline.firestore_admin, "get_reference_motion", _boom)
    calls: list = []
    monkeypatch.setattr(pipeline, "_s3_download", lambda *a: calls.append(a))

    assert pipeline._prefetch_reference_video("bkt", "ref-x") is None
    assert calls == []


def test_prefetch_none_and_temp_removed_when_download_raises(pipeline, monkeypatch):
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_reference_motion",
        lambda mid: {"motionId": mid, "videoS3Key": "reference/ref-x/v1.mp4"},
    )
    dests: list[str] = []

    def _dl(bucket, k, dest):
        dests.append(dest)
        Path(dest).write_bytes(b"partial")
        raise OSError("s3 link collapsed")

    monkeypatch.setattr(pipeline, "_s3_download", _dl)

    assert pipeline._prefetch_reference_video("bkt", "ref-x") is None
    assert len(dests) == 1
    assert not Path(dests[0]).exists()


# ── _upload_prefetched_reference ─────────────────────────────────────────────


class _RecordingSession:
    def __init__(self, handle="files/ref-handle") -> None:
        self.calls: list[str] = []
        self.handle = handle

    def get_or_upload(self, path):
        self.calls.append(path)
        return self.handle


def test_upload_uses_downloaded_path(pipeline):
    session = _RecordingSession()
    fut = _done_future(("reference/ref-x/v1.mp4", "/tmp/ref-x.mp4"))

    assert pipeline._upload_prefetched_reference(session, fut) == "files/ref-handle"
    assert session.calls == ["/tmp/ref-x.mp4"]


def test_upload_none_when_download_result_none(pipeline):
    session = _RecordingSession()
    assert pipeline._upload_prefetched_reference(session, _done_future(None)) is None
    assert session.calls == []


def test_upload_none_when_download_future_raised(pipeline):
    session = _RecordingSession()
    fut = _failed_future(RuntimeError("download thread died"))
    assert pipeline._upload_prefetched_reference(session, fut) is None
    assert session.calls == []


def test_upload_none_when_future_missing(pipeline):
    session = _RecordingSession()
    assert pipeline._upload_prefetched_reference(session, None) is None
    assert session.calls == []


# ── _take_prefetched_reference_path ──────────────────────────────────────────


def test_take_returns_path_on_key_match(pipeline, tmp_path):
    p = tmp_path / "ref.mp4"
    p.write_bytes(b"x")
    fut = _done_future(("reference/a.mp4", str(p)))
    assert pipeline._take_prefetched_reference_path(fut, "reference/a.mp4") == str(p)


def test_take_none_on_key_mismatch_keeps_file(pipeline, tmp_path):
    p = tmp_path / "ref.mp4"
    p.write_bytes(b"x")
    fut = _done_future(("reference/a.mp4", str(p)))
    assert pipeline._take_prefetched_reference_path(fut, "reference/b.mp4") is None
    # 업로드 future 가 아직 이 파일을 읽고 있을 수 있다 — 여기서 지우지 않는다(WR-02).
    assert p.exists()


def test_take_none_without_future(pipeline):
    assert pipeline._take_prefetched_reference_path(None, "reference/a.mp4") is None


def test_take_none_when_result_none(pipeline):
    assert pipeline._take_prefetched_reference_path(_done_future(None), "reference/a.mp4") is None


def test_take_none_when_future_raised(pipeline):
    fut = _failed_future(RuntimeError("boom"))
    assert pipeline._take_prefetched_reference_path(fut, "reference/a.mp4") is None


# ── _prefetched_reference_temp_path ──────────────────────────────────────────


def test_temp_path_from_successful_future(pipeline):
    fut = _done_future(("reference/a.mp4", "/tmp/ref-a.mp4"))
    assert pipeline._prefetched_reference_temp_path(fut) == "/tmp/ref-a.mp4"


def test_temp_path_none_without_future(pipeline):
    assert pipeline._prefetched_reference_temp_path(None) is None


def test_temp_path_none_for_pending_future_without_waiting(pipeline):
    fut: Future = Future()  # 미완료 — 기다리면 테스트가 멈춘다
    assert pipeline._prefetched_reference_temp_path(fut) is None


def test_temp_path_none_for_failed_future(pipeline):
    assert pipeline._prefetched_reference_temp_path(_failed_future(OSError("x"))) is None


def test_temp_path_none_for_none_result(pipeline):
    assert pipeline._prefetched_reference_temp_path(_done_future(None)) is None
