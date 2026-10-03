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
import logging
import os
import socket
import sys
import threading
import time
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from typing import NamedTuple
from unittest.mock import MagicMock

import numpy as np
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


# ═══════════════════════════ 2부 — _process 통합 테스트 ═══════════════════════════
#
# 하네스는 tests/pipeline/test_pipeline_phase9.py 의 모양(_import_pipeline · env 리셋 ·
# _stub_extract_inputs)을 따른다. 차이:
#   · 포즈 stub 은 tmp_path 에 실제 학생 파일을 쓰고 그 경로를 돌려준다(unlink 검증용).
#   · GeminiFileSession 을 기록용 하위 클래스로 바꾼다 — 진짜 락 · inflight · close 로직은
#     그대로 쓰고 `_upload_and_wait_active` 만 가짜(네트워크 0). close 가 실제로 delete
#     경로를 타도록 `_client` 를 delete 기록용 가짜로 채운다.
#   · 소켓 connect / getaddrinfo 를 막고 시도를 기록한다 — 테스트마다 0 을 확인한다.

_REF_KEY = "reference/ref-x/v1.mp4"
_REF_KEY_OTHER = "reference/ref-x/v2.mp4"
_STUDENT_KEY = "uploads/u1/a1.mp4"


class _Rec:
    """스레드 공유 기록 — 모든 쓰기는 락 안에서."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.events: list[tuple] = []
        self.downloads: list[tuple[str, str, str]] = []  # (key, dest, thread name)
        self.handles: dict[str, object] = {}  # path → 세션이 만든 핸들
        self.veto_kwargs: list[dict] = []
        self.coach_scene_flags: list[object] = []
        self.scene_sentinels: list[dict] = []
        self.statuses: list[str] = []

    def add(self, *ev) -> None:
        with self._lock:
            self.events.append(ev)

    def add_download(self, key: str, dest: str, thread: str) -> None:
        with self._lock:
            self.downloads.append((key, dest, thread))

    def ref_dests(self) -> set[str]:
        with self._lock:
            return {d for _, d, _ in self.downloads}

    def set_handle(self, path: str, handle: object) -> None:
        with self._lock:
            self.handles[path] = handle

    def snapshot(self) -> list[tuple]:
        with self._lock:
            return list(self.events)


def _first_index(events: list[tuple], ev: tuple) -> int:
    assert ev in events, f"사건 {ev} 미기록 — events={events}"
    return events.index(ev)


@pytest.fixture
def net_attempts(monkeypatch):
    """소켓 connect / DNS 조회를 막고 시도를 기록한다 (네트워크 0 확인용)."""
    attempts: list[tuple] = []

    def _blocked_connect(self, address, *a, **k):  # noqa: ARG001
        attempts.append(("connect", address))
        raise OSError("network blocked in test (quick-261003-qmg)")

    def _blocked_getaddrinfo(host, *a, **k):  # noqa: ARG001
        attempts.append(("getaddrinfo", host))
        raise socket.gaierror("network blocked in test (quick-261003-qmg)")

    monkeypatch.setattr(socket.socket, "connect", _blocked_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked_connect)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked_getaddrinfo)
    return attempts


def _angles_8j(rows: int = 60) -> np.ndarray:
    from sunity_shared.analysis.skeleton import JOINT_KEYS

    rng = np.random.default_rng(0)
    base = 90.0 + 5.0 * np.sin(np.arange(rows) / 5.0)
    out = np.tile(base.reshape(-1, 1), (1, len(JOINT_KEYS)))
    out += rng.normal(0.0, 0.5, size=(rows, len(JOINT_KEYS)))
    return out


def _make_pose_frames(n: int = 60) -> list:
    from tests.phase08.fixtures._factory import (  # noqa: WPS433
        make_keypoint2d,
        make_pose_frame,
    )

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


def _ref_doc(key: str) -> dict:
    return {
        "motionId": "ref-x",
        "name": "invert",
        "athleteName": "정은지",
        "angles": np.full(60 * 8, 90.0).tolist(),
        "anglesJointKeys": list(["a"] * 8),
        "videoS3Key": key,
    }


class _Harness(NamedTuple):
    rec: _Rec
    complete: MagicMock
    student_path: Path
    prefetch_spy: list
    veto_started: threading.Event


def _install(
    pipeline,
    monkeypatch,
    tmp_path,
    *,
    mode: str,
    prefetch: bool,
    scene_waits_for_veto: bool = False,
    ref_upload_delay: float = 0.0,
    gemini_ref_key: str = _REF_KEY,
    main_ref_key: str = _REF_KEY,
    fail_gemini_download: bool = False,
    pose_error: BaseException | None = None,
    fail_on_comparison_status: bool = False,
) -> _Harness:
    """`_process` 를 네트워크 없이 돌리는 stub 일체를 깐다."""
    monkeypatch.setenv("GEMINI_VISION_VETO_ENABLED", "1")
    monkeypatch.setenv("GEMINI_UPLOAD_PREFETCH", "1" if prefetch else "0")

    rec = _Rec()
    veto_started = threading.Event()

    # ── GeminiFileSession → 기록용 하위 클래스 (진짜 락 · inflight · close 로직 사용) ──
    from sunity_shared.gemini import file_session as fs_mod

    base_cls = fs_mod.GeminiFileSession

    class _FakeFiles:
        def delete(self, *, name):
            rec.add("delete", name)

    class _FakeClient:
        def __init__(self) -> None:
            self.files = _FakeFiles()

    class _RecordingFileSession(base_cls):
        def __init__(self, client_factory=None) -> None:
            super().__init__(client_factory=client_factory)
            self._client = _FakeClient()

        def _upload_and_wait_active(self, video_path, mime_type):  # noqa: ARG002
            rec.add("upload_start", video_path)
            if video_path in rec.ref_dests():
                time.sleep(ref_upload_delay)
            handle = SimpleNamespace(name="files/" + os.path.basename(video_path))
            rec.set_handle(video_path, handle)
            rec.add("upload_done", video_path)
            return handle

        def close(self) -> None:
            rec.add("close")
            super().close()

    monkeypatch.setattr(fs_mod, "GeminiFileSession", _RecordingFileSession)

    # ── 학생 영상 다운로드 + 포즈 stub (27-05 seam 두 함수) ──
    student_path = tmp_path / "student.mp4"

    def _fake_download(bucket, key, *, timings_ms=None, analysis_id=""):  # noqa: ARG001
        student_path.write_bytes(b"student video bytes")
        return str(student_path)

    from sunity_shared.analysis.body_normalization import BodyNormalizationProfile
    from sunity_shared.analysis.pole_geometry import build_pole_axis_measurement

    def _fake_from_local(
        local_video_path, default_pole, *, keep_local_video=False,
        timings_ms=None, analysis_id="", unlink_on_error=True,  # noqa: ARG001
    ):
        if pose_error is not None:
            raise pose_error
        profile = BodyNormalizationProfile(
            estimated_height_scale=1.0, arm_scale=1.0, leg_scale=1.0,
            torso_scale=1.0, shoulder_hip_ratio=1.0, confidence=0.0, warnings=["mock"],
        )
        return pipeline._VideoAnalysisInputs(
            angles=_angles_8j(),
            student_profile=profile,
            pose_frames=_make_pose_frames(60),
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

    # ── 기준 영상 S3 다운로드 stub — (key, dest, 스레드 이름) 기록 ──
    def _fake_s3_download(bucket, key, dest):  # noqa: ARG001
        thread = threading.current_thread().name
        rec.add_download(key, dest, thread)
        if fail_gemini_download and thread.startswith("gemini"):
            Path(dest).write_bytes(b"partial")
            raise OSError("prefetch link collapsed")
        Path(dest).write_bytes(b"reference video bytes")

    monkeypatch.setattr(pipeline, "_s3_download", _fake_s3_download)

    # ── Firestore stub ──
    meta = {"mode": mode, "referenceMotionId": "ref-x"}
    monkeypatch.setattr(
        pipeline.firestore_admin, "get_analysis", lambda uid, aid: dict(meta)
    )

    def _fake_status(uid, aid, status, *a, **k):  # noqa: ARG001
        rec.statuses.append(status)
        if fail_on_comparison_status and status == pipeline.models.STATUS_COMPARISON:
            raise RuntimeError("firestore comparison write failed")

    monkeypatch.setattr(pipeline.firestore_admin, "update_analysis_status", _fake_status)

    def _fake_get_ref(mid):  # noqa: ARG001
        # prefetch 스레드("gemini" 접두)와 채점 경로(메인)를 스레드 이름으로 가른다 —
        # 순서 경쟁 없이 키 불일치를 재현한다.
        if threading.current_thread().name.startswith("gemini"):
            return _ref_doc(gemini_ref_key)
        return _ref_doc(main_ref_key)

    monkeypatch.setattr(pipeline.firestore_admin, "get_reference_motion", _fake_get_ref)
    monkeypatch.setattr(
        pipeline.firestore_admin, "get_active_reference_release", lambda mid: None
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "get_previous_analysis",
        lambda uid, aid, mode=None: None,
    )
    complete = MagicMock()
    monkeypatch.setattr(pipeline.firestore_admin, "complete_analysis", complete)

    # ── 나머지 경계 stub ──
    monkeypatch.setattr(pipeline, "_signed_get", lambda bucket, key: f"https://signed/{key}")
    monkeypatch.setattr(pipeline, "_ensure_adapters", lambda: None)
    coach_mock = MagicMock()
    coach_mock.write.return_value = {"summary": "mock coach"}
    pipeline._COACH_WRITER = coach_mock

    def _fake_scene(local_video_path=None, is_reference=False, preuploaded_handle=None):  # noqa: ARG001
        if scene_waits_for_veto:
            released = veto_started.wait(timeout=5.0)
        else:
            released = veto_started.is_set()
        sentinel = {"released_by_veto": released, "qmg_sentinel": True}
        rec.scene_sentinels.append(sentinel)
        return sentinel

    monkeypatch.setattr(pipeline, "_call_wave1_scene_finder", _fake_scene)

    def _fake_collect(*args, **kwargs):  # noqa: ARG001
        rec.veto_kwargs.append(kwargs)
        veto_started.set()
        return None

    monkeypatch.setattr(pipeline, "_collect_vision_fault_context", _fake_collect)
    monkeypatch.setattr(pipeline, "_apply_vision_veto", lambda result, *a, **k: result)
    # 사후 코칭 작성(Gemini coach B)은 API 키를 SSM 에서 찾으러 나간다 — 소켓 가드로 확인한
    # 유일한 네트워크 시도라 이 스테이지만 no-op 으로 둔다(이 테스트의 관심사 밖).
    monkeypatch.setattr(pipeline, "_run_deferred_coach_text", lambda **k: None)

    orig_build_coach_context = pipeline._build_coach_context

    def _spy_build_coach_context(*args, **kwargs):
        rec.coach_scene_flags.append(kwargs.get("scene_flags"))
        return orig_build_coach_context(*args, **kwargs)

    monkeypatch.setattr(pipeline, "_build_coach_context", _spy_build_coach_context)

    orig_unlink = pipeline._safe_unlink_local_video

    def _rec_unlink(path):
        rec.add("unlink", path)
        orig_unlink(path)

    monkeypatch.setattr(pipeline, "_safe_unlink_local_video", _rec_unlink)

    prefetch_spy: list = []
    orig_prefetch = pipeline._prefetch_reference_video

    def _spy_prefetch(*args, **kwargs):
        prefetch_spy.append(args)
        return orig_prefetch(*args, **kwargs)

    monkeypatch.setattr(pipeline, "_prefetch_reference_video", _spy_prefetch)

    return _Harness(rec, complete, student_path, prefetch_spy, veto_started)


def _stage_logged(caplog, name: str) -> bool:
    return any(f"stage={name} " in r.getMessage() for r in caplog.records)


def _uploads_of(events: list[tuple], path: str) -> int:
    return sum(1 for ev in events if ev == ("upload_start", path))


# ── [A] prefetch ON · mode1 · veto ON ────────────────────────────────────────


def test_a_mode1_prefetch_downloads_and_uploads_reference_once_off_main(
    pipeline, monkeypatch, tmp_path, caplog, net_attempts
):
    h = _install(pipeline, monkeypatch, tmp_path, mode=pipeline.models.MODE_EXPERT, prefetch=True)

    with caplog.at_level(logging.INFO):
        pipeline._process("bkt", _STUDENT_KEY, "u1", "a1")

    rec = h.rec
    assert len(rec.downloads) == 1, rec.downloads
    key, dest, thread = rec.downloads[0]
    assert key == _REF_KEY
    assert thread.startswith("gemini"), f"기준 다운로드가 메인에서 돌았다: {thread}"

    assert len(rec.veto_kwargs) == 1
    veto = rec.veto_kwargs[0]
    assert veto["reference_video_path"] == dest
    assert veto["preuploaded_reference_handle"] is rec.handles[dest]

    events = rec.snapshot()
    assert _uploads_of(events, dest) == 1  # veto 직전 호출은 캐시 hit/inflight
    assert _uploads_of(events, str(h.student_path)) == 1

    for stage in ("ref_upload", "ref_video_download", "student_upload_wait"):
        assert _stage_logged(caplog, stage), f"stage={stage} 로그 없음"

    assert not Path(dest).exists()
    assert not h.student_path.exists()
    deleted = {ev[1] for ev in events if ev[0] == "delete"}
    assert deleted == {getattr(hd, "name") for hd in rec.handles.values()}
    assert _first_index(events, ("close",)) < min(
        i for i, ev in enumerate(events) if ev[0] == "delete"
    )
    h.complete.assert_called_once()
    assert net_attempts == []


# ── [B] scene join 위치 — veto 뒤 · coach context 직전 ──────────────────────


def test_b_scene_join_happens_after_veto_collect(
    pipeline, monkeypatch, tmp_path, net_attempts
):
    h = _install(
        pipeline, monkeypatch, tmp_path,
        mode=pipeline.models.MODE_EXPERT, prefetch=True, scene_waits_for_veto=True,
    )

    pipeline._process("bkt", _STUDENT_KEY, "u1", "a1")

    rec = h.rec
    assert len(rec.scene_sentinels) == 1
    assert len(rec.coach_scene_flags) == 1
    assert rec.coach_scene_flags[0] is rec.scene_sentinels[0]
    # 옛 배선(recognizer 앞 join)이면 veto 전에 기다리다 5초 timeout → False.
    assert rec.scene_sentinels[0]["released_by_veto"] is True
    h.complete.assert_called_once()
    assert net_attempts == []


# ── [C] prefetch OFF — 지금 동기 경로 그대로 ─────────────────────────────────


def test_c_prefetch_off_keeps_synchronous_reference_path(
    pipeline, monkeypatch, tmp_path, caplog, net_attempts
):
    h = _install(pipeline, monkeypatch, tmp_path, mode=pipeline.models.MODE_EXPERT, prefetch=False)

    with caplog.at_level(logging.INFO):
        pipeline._process("bkt", _STUDENT_KEY, "u1", "a1")

    rec = h.rec
    assert h.prefetch_spy == []
    assert len(rec.downloads) == 1, rec.downloads
    key, dest, thread = rec.downloads[0]
    assert key == _REF_KEY
    assert thread == "MainThread"
    assert len(rec.scene_sentinels) == 1
    assert rec.coach_scene_flags == [rec.scene_sentinels[0]]
    assert rec.coach_scene_flags[0] is rec.scene_sentinels[0]
    assert _stage_logged(caplog, "ref_upload")
    events = rec.snapshot()
    assert _uploads_of(events, dest) == 1
    assert rec.veto_kwargs[0]["reference_video_path"] == dest
    assert not Path(dest).exists()
    assert not h.student_path.exists()
    h.complete.assert_called_once()
    assert net_attempts == []


# ── [D] mode3 — 기준 영상 prefetch 없음 ──────────────────────────────────────


def test_d_mode3_has_no_reference_prefetch(
    pipeline, monkeypatch, tmp_path, caplog, net_attempts
):
    h = _install(pipeline, monkeypatch, tmp_path, mode=pipeline.models.MODE_SELF, prefetch=True)

    with caplog.at_level(logging.INFO):
        pipeline._process("bkt", _STUDENT_KEY, "u1", "a1")

    rec = h.rec
    assert h.prefetch_spy == []
    assert rec.downloads == []
    assert not _stage_logged(caplog, "ref_upload")
    assert len(rec.scene_sentinels) == 1
    assert rec.coach_scene_flags[0] is rec.scene_sentinels[0]
    assert not h.student_path.exists()
    h.complete.assert_called_once()
    assert net_attempts == []


# ── [E] key 불일치 — 채점 경로의 키로 동기 폴백 ──────────────────────────────


def test_e_key_mismatch_falls_back_to_scoring_key(
    pipeline, monkeypatch, tmp_path, net_attempts
):
    # gemini 스레드(prefetch)는 v1, 메인(채점 경로)은 v2 를 본다 — 그 사이 base doc 이
    # 바뀐 경우의 재현(videoS3Key 는 version overlay 대상이 아니다).
    h = _install(
        pipeline, monkeypatch, tmp_path,
        mode=pipeline.models.MODE_EXPERT, prefetch=True,
        gemini_ref_key=_REF_KEY, main_ref_key=_REF_KEY_OTHER,
    )

    pipeline._process("bkt", _STUDENT_KEY, "u1", "a1")

    rec = h.rec
    by_key = {k: (d, t) for k, d, t in rec.downloads}
    assert set(by_key) == {_REF_KEY, _REF_KEY_OTHER}, rec.downloads
    dest_a, thread_a = by_key[_REF_KEY]
    dest_b, thread_b = by_key[_REF_KEY_OTHER]
    assert thread_a.startswith("gemini")
    assert thread_b == "MainThread"

    assert rec.veto_kwargs[0]["reference_video_path"] == dest_b
    assert not Path(dest_a).exists()
    assert not Path(dest_b).exists()

    events = rec.snapshot()
    deleted = {ev[1] for ev in events if ev[0] == "delete"}
    assert rec.handles[dest_a].name in deleted
    assert rec.handles[dest_b].name in deleted
    h.complete.assert_called_once()
    assert net_attempts == []


# ── [F] prefetch 다운로드 실패 — 동기 폴백으로 완주 ──────────────────────────


def test_f_prefetch_download_failure_falls_back(
    pipeline, monkeypatch, tmp_path, net_attempts
):
    h = _install(
        pipeline, monkeypatch, tmp_path,
        mode=pipeline.models.MODE_EXPERT, prefetch=True, fail_gemini_download=True,
    )

    pipeline._process("bkt", _STUDENT_KEY, "u1", "a1")

    rec = h.rec
    gemini_dl = [d for k, d, t in rec.downloads if t.startswith("gemini")]
    main_dl = [d for k, d, t in rec.downloads if t == "MainThread"]
    assert len(gemini_dl) == 1, "prefetch 다운로드 시도 자체가 없었다"
    assert len(main_dl) == 1
    assert rec.veto_kwargs[0]["reference_video_path"] == main_dl[0]
    h.complete.assert_called_once()
    assert not Path(gemini_dl[0]).exists()
    assert not Path(main_dl[0]).exists()
    assert not h.student_path.exists()
    assert net_attempts == []


# ── [G] 포즈 블록 조기 실패 — join → close → unlink ──────────────────────────


def test_g_pose_failure_joins_then_closes_then_unlinks(
    pipeline, monkeypatch, tmp_path, net_attempts
):
    h = _install(
        pipeline, monkeypatch, tmp_path,
        mode=pipeline.models.MODE_EXPERT, prefetch=True,
        ref_upload_delay=0.3, pose_error=RuntimeError("pose boom"),
    )

    with pytest.raises(RuntimeError, match="pose boom"):
        pipeline._process("bkt", _STUDENT_KEY, "u1", "a1")

    rec = h.rec
    assert len(rec.downloads) == 1, "기준 prefetch 가 시작되지 않았다"
    ref_dest = rec.downloads[0][1]
    events = rec.snapshot()
    i_done = _first_index(events, ("upload_done", ref_dest))
    i_close = _first_index(events, ("close",))
    i_unlink = _first_index(events, ("unlink", ref_dest))
    assert i_done < i_close < i_unlink, events
    assert ("delete", rec.handles[ref_dest].name) in events
    assert not Path(ref_dest).exists()
    assert not h.student_path.exists()
    h.complete.assert_not_called()
    assert net_attempts == []


# ── [H] 포즈 블록과 outer try 사이 실패 — 같은 정리 순서 ─────────────────────


def test_h_between_blocks_failure_still_closes_and_unlinks(
    pipeline, monkeypatch, tmp_path, net_attempts
):
    h = _install(
        pipeline, monkeypatch, tmp_path,
        mode=pipeline.models.MODE_EXPERT, prefetch=True,
        ref_upload_delay=0.3, fail_on_comparison_status=True,
    )

    with pytest.raises(RuntimeError, match="comparison write failed"):
        pipeline._process("bkt", _STUDENT_KEY, "u1", "a1")

    rec = h.rec
    assert len(rec.downloads) == 1, "기준 prefetch 가 시작되지 않았다"
    ref_dest = rec.downloads[0][1]
    events = rec.snapshot()
    i_done = _first_index(events, ("upload_done", ref_dest))
    i_close = _first_index(events, ("close",))
    i_unlink = _first_index(events, ("unlink", ref_dest))
    assert i_done < i_close < i_unlink, events
    assert ("delete", rec.handles[ref_dest].name) in events
    assert not Path(ref_dest).exists()
    assert not h.student_path.exists()
    h.complete.assert_not_called()
    assert net_attempts == []
