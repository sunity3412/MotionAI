"""quick-261003-svg — 점수 뒤 사후 단계 병렬(코칭 문장 ∥ 오디오 → 확대 사진 → 스팟체크).

목적:
  complete_analysis(status='done') 뒤 사후 단계 다섯 개가 지금은 한 줄로 돈다 —
  coach_text → coach_audio → fault_zoom → spot_check → compare_render. 38-14 쌍 Pod 증거
  로그(quick-261003-qmg)에서 coach_dual 58~87초 · fault_zoom 66~112초 · spot_check 7.5~9.5초 ·
  compare_render 73~77초였다. 코칭 문장(메인)과 곁가지(coach_audio → fault_zoom → spot_check)
  는 서로의 결과를 읽지 않으므로 겹쳐 돌리고, 두 결과를 받고 RTMW(GPU)를 쓰는
  compare_render 만 둘이 끝난 뒤에 둔다. env `POST_STAGE_PARALLEL`(기본 ON, "0" 이면 직렬).

  1부 — 오케스트레이터 `_run_post_stages` 와 토글 `_post_stage_parallel_enabled` 단위.
        stage 는 전부 기록용 stub(스레드 이름 · 받은 인자 · 사건 순서).
  2부 — `_process` 통합. qmg 하네스(tests/test_ref_prefetch_scene_join.py `_install`)를
        그대로 쓰고, 사후 단계 다섯 개를 기록 wrapper 로 감싸 두 모드(0/1)를 대조한다.

전부 stub — 실 S3 / Firestore / Gemini / Polly / Cerebras 호출 0 (2부는 소켓 가드로 확인).
"""

from __future__ import annotations

import logging
import threading
import time

import pytest

from tests.test_ref_prefetch_scene_join import (  # noqa: F401 — 픽스처 재등록
    net_attempts,
    pipeline,
)

_MAIN = "MainThread"


class _Log:
    """스레드 공유 기록 — 모든 쓰기는 락 안에서."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.events: list[tuple] = []

    def add(self, *ev) -> None:
        with self._lock:
            self.events.append(ev)

    def snapshot(self) -> list[tuple]:
        with self._lock:
            return list(self.events)


def _names(events: list[tuple]) -> list[str]:
    return [ev[0] for ev in events]


# ═══════════════════════════ 1부 — 오케스트레이터 단위 ═══════════════════════════


# ── _post_stage_parallel_enabled ─────────────────────────────────────────────


def test_toggle_default_on_when_unset(pipeline, monkeypatch):
    monkeypatch.delenv("POST_STAGE_PARALLEL", raising=False)
    assert pipeline._post_stage_parallel_enabled() is True


@pytest.mark.parametrize(
    "raw,expected",
    [("1", True), ("0", False), ("false", False), ("FALSE", False), ("", False)],
)
def test_toggle_values(pipeline, monkeypatch, raw, expected):
    monkeypatch.setenv("POST_STAGE_PARALLEL", raw)
    assert pipeline._post_stage_parallel_enabled() is expected


def test_toggle_reads_env_every_call(pipeline, monkeypatch):
    """모듈 적재 시 고정 금지 — Pod env 재기동만으로 전후 교차 측정하는 레버."""
    monkeypatch.setenv("POST_STAGE_PARALLEL", "0")
    assert pipeline._post_stage_parallel_enabled() is False
    monkeypatch.setenv("POST_STAGE_PARALLEL", "1")
    assert pipeline._post_stage_parallel_enabled() is True


# ── _run_post_stages ─────────────────────────────────────────────────────────


def test_serial_runs_main_then_side_then_compare_on_main_thread(pipeline):
    rec = _Log()
    timings: dict[str, int] = {"firestore_complete": 5}
    audio_items = [{"recordId": "r1"}]
    zoom_items = [{"criterion": "c1"}]

    def coach(stage_timings):
        rec.add("coach", threading.current_thread().name, stage_timings)

    def side(stage_timings):
        rec.add("side", threading.current_thread().name, stage_timings)
        return audio_items, zoom_items

    def compare(a, z):
        rec.add("compare", threading.current_thread().name, a, z)

    pipeline._run_post_stages(
        coach_text_stage=coach,
        side_stage=side,
        compare_render_stage=compare,
        timings_ms=timings,
        analysis_id="a1",
        parallel=False,
    )

    events = rec.snapshot()
    assert _names(events) == ["coach", "side", "compare"]
    assert all(ev[1] == _MAIN for ev in events)
    assert events[0][2] is timings
    assert events[1][2] is timings
    assert events[2][2] is audio_items
    assert events[2][3] is zoom_items
    assert "post_parallel" not in timings


def test_parallel_overlaps_main_and_side_then_compare_after_both(pipeline):
    rec = _Log()
    timings: dict[str, int] = {"firestore_complete": 5}
    audio_items = [{"recordId": "r1"}]
    zoom_items = [{"criterion": "c1"}]
    coach_started = threading.Event()
    side_started = threading.Event()
    seen: dict[str, object] = {}

    def coach(stage_timings):
        rec.add("coach_start", threading.current_thread().name)
        seen["coach_dict"] = stage_timings
        coach_started.set()
        # 곁가지가 동시에 돌고 있어야만 풀린다 — 직렬이면 timeout 으로 False.
        seen["coach_saw_side"] = side_started.wait(timeout=5.0)
        stage_timings["coach_dual"] = 11
        rec.add("coach_end", threading.current_thread().name)

    def side(stage_timings):
        rec.add("side_start", threading.current_thread().name)
        seen["side_dict"] = stage_timings
        side_started.set()
        seen["side_saw_coach"] = coach_started.wait(timeout=5.0)
        stage_timings["coach_audio"] = 1
        stage_timings["fault_zoom"] = 22
        stage_timings["spot_check"] = 3
        rec.add("side_end", threading.current_thread().name)
        return audio_items, zoom_items

    def compare(a, z):
        rec.add("compare", threading.current_thread().name, a, z)

    pipeline._run_post_stages(
        coach_text_stage=coach,
        side_stage=side,
        compare_render_stage=compare,
        timings_ms=timings,
        analysis_id="a1",
        parallel=True,
    )

    assert seen["coach_saw_side"] is True
    assert seen["side_saw_coach"] is True

    events = rec.snapshot()
    by_name = {ev[0]: ev for ev in events}
    assert by_name["coach_start"][1] == _MAIN
    assert by_name["coach_end"][1] == _MAIN
    assert by_name["side_start"][1].startswith("post_side")
    assert by_name["side_end"][1].startswith("post_side")
    assert by_name["compare"][1] == _MAIN

    names = _names(events)
    assert names.count("compare") == 1
    assert names.index("compare") > names.index("side_end")
    assert names.index("compare") > names.index("coach_end")
    assert by_name["compare"][2] is audio_items
    assert by_name["compare"][3] is zoom_items

    # 메인은 timings_ms 그 객체, 곁가지는 전용 dict — join 뒤 합쳐진다.
    assert seen["coach_dict"] is timings
    assert seen["side_dict"] is not timings
    for key, val in (("coach_audio", 1), ("fault_zoom", 22), ("spot_check", 3), ("coach_dual", 11)):
        assert timings[key] == val
    assert isinstance(timings["post_parallel"], int)
    assert timings["firestore_complete"] == 5


def test_parallel_side_exception_does_not_escape_and_compare_gets_empty_lists(
    pipeline, caplog
):
    rec = _Log()
    timings: dict[str, int] = {}

    def coach(stage_timings):  # noqa: ARG001
        rec.add("coach")

    def side(stage_timings):  # noqa: ARG001
        raise RuntimeError("boom-secret")

    def compare(a, z):
        rec.add("compare", a, z)

    with caplog.at_level(logging.WARNING):
        pipeline._run_post_stages(
            coach_text_stage=coach,
            side_stage=side,
            compare_render_stage=compare,
            timings_ms=timings,
            analysis_id="a1",
            parallel=True,
        )

    events = rec.snapshot()
    assert _names(events) == ["coach", "compare"]
    assert events[1][1] == [] and events[1][2] == []
    warned = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("RuntimeError" in m for m in warned), warned
    # 예외 본문은 로그에 남기지 않는다(T-svg-07) — 메시지 · 예외 정보 둘 다.
    assert not any("boom-secret" in m for m in warned)
    assert not any(r.exc_info for r in caplog.records if r.levelno >= logging.WARNING)


def test_parallel_main_exception_propagates_only_after_side_finished(pipeline):
    """메인 가지 예외는 곁가지가 끝난 뒤에 전파된다 — outer finally 의 unlink 보다 곁가지가 먼저."""
    rec = _Log()
    coach_raised = threading.Event()

    def coach(stage_timings):  # noqa: ARG001
        rec.add("coach_raise")
        coach_raised.set()
        raise RuntimeError("main branch failed")

    def side(stage_timings):  # noqa: ARG001
        rec.add("side_start")
        coach_raised.wait(timeout=5.0)
        time.sleep(0.05)
        rec.add("side_end")
        return [], []

    def compare(a, z):  # noqa: ARG001
        rec.add("compare")

    with pytest.raises(RuntimeError, match="main branch failed"):
        pipeline._run_post_stages(
            coach_text_stage=coach,
            side_stage=side,
            compare_render_stage=compare,
            timings_ms={},
            analysis_id="a1",
            parallel=True,
        )
    names = _names(rec.snapshot())
    assert "side_end" in names
    assert "compare" not in names


# ═══════════════════════════ 2부 — _process 통합 ═══════════════════════════
#
# qmg 하네스(`_install`, mode1 · prefetch ON)를 그대로 깔고, 그 위에:
#   · `_run_deferred_coach_text` — 기록 stub (하네스가 no-op 로 둔 이유 = Gemini coach B 의
#     SSM 키 조회, qmg SUMMARY 편차 2). 병렬 런에서만 "coach_audio 시작" Event 를 기다린다.
#   · coach_audio · fault_zoom · spot_check · compare_render — 원본을 감싼 기록 wrapper.
#   · `_build_fault_zoom_comparisons` — 원본을 감싼 기록 wrapper(실패 격리 테스트는 raise).
#   · Firestore 사후 부분 갱신 4종 — (이름, status) 기록 stub.
# 두 모드는 한 하네스에서 차례로 돌리고, 런마다 기록 길이로 구간을 자른다.

from collections import Counter  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import NamedTuple  # noqa: E402

from tests.test_ref_prefetch_scene_join import (  # noqa: E402
    _STUDENT_KEY,
    _first_index,
    _install,
)

_POST_STAGES = ("coach_text", "coach_audio", "fault_zoom", "spot_check", "compare_render")
_SIDE_STAGES = ("coach_audio", "fault_zoom", "spot_check")
_WRAPPED = ("coach_audio", "fault_zoom", "spot_check", "compare_render")
_POST_FS = (
    "update_analysis_coach_audio",
    "update_analysis_fault_zoom",
    "update_analysis_spot_check",
    "update_analysis_rendered_compare",
)
_STR_KWARGS = ("uid", "analysis_id", "bucket", "mode", "local_video_path")


class _StageCall(NamedTuple):
    name: str
    thread: str
    kwargs: dict
    out: object


class _PostRec:
    """사후 단계 기록 — 모든 쓰기는 락 안에서."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls: list[_StageCall] = []
        self.fs: list[tuple[str, object, str]] = []  # (함수, status, 스레드)
        self.zoom_builds: list[tuple[str, dict]] = []  # (스레드, result)
        self.coach_saw_audio: list[bool] = []

    def add_call(self, call: _StageCall) -> None:
        with self._lock:
            self.calls.append(call)

    def add_fs(self, name: str, status, thread: str) -> None:
        with self._lock:
            self.fs.append((name, status, thread))

    def add_zoom_build(self, thread: str, result: dict) -> None:
        with self._lock:
            self.zoom_builds.append((thread, result))


class _PostHarness(NamedTuple):
    h: object  # qmg _Harness
    post: _PostRec
    state: dict
    audio_started: threading.Event


class _Run(NamedTuple):
    events: list[tuple]
    calls: dict[str, list[_StageCall]]
    fs: list[tuple[str, object, str]]
    zoom_builds: list[tuple[str, dict]]
    coach_saw_audio: list[bool]
    statuses: list[str]
    result: dict
    ref_dests: list[str]


def _install_post(pipeline, monkeypatch, tmp_path, *, mode, zoom_error=None) -> _PostHarness:
    h = _install(pipeline, monkeypatch, tmp_path, mode=mode, prefetch=True)
    post = _PostRec()
    state = {"parallel": False}
    audio_started = threading.Event()

    def _coach_text(**kwargs):
        h.rec.add("coach_text_start")
        if state["parallel"]:
            # 곁가지(coach_audio)가 동시에 시작해야만 풀린다 — 직렬이면 timeout 으로 False.
            saw = audio_started.wait(timeout=5.0)
            with post._lock:
                post.coach_saw_audio.append(saw)
        post.add_call(_StageCall("coach_text", threading.current_thread().name, kwargs, None))
        h.rec.add("coach_text_end")

    monkeypatch.setattr(pipeline, "_run_deferred_coach_text", _coach_text)

    def _wrap(name, orig):
        def wrapper(*args, **kwargs):
            h.rec.add(f"{name}_start")
            if name == "coach_audio":
                audio_started.set()
            out = orig(*args, **kwargs)
            post.add_call(_StageCall(name, threading.current_thread().name, kwargs, out))
            h.rec.add(f"{name}_end")
            return out

        return wrapper

    for name in _WRAPPED:
        attr = f"_run_deferred_{name}"
        monkeypatch.setattr(pipeline, attr, _wrap(name, getattr(pipeline, attr)))

    orig_build = pipeline._build_fault_zoom_comparisons

    def _zoom_build(result, *args, **kwargs):
        post.add_zoom_build(threading.current_thread().name, result)
        if zoom_error is not None:
            raise zoom_error
        return orig_build(result, *args, **kwargs)

    monkeypatch.setattr(pipeline, "_build_fault_zoom_comparisons", _zoom_build)

    def _fs_stub(name):
        def stub(uid, analysis_id, *args, **kwargs):  # noqa: ARG001
            status = kwargs.get("status")
            if status is None and name == "update_analysis_spot_check" and args:
                status = (args[0] or {}).get("status")
            elif status is None and len(args) >= 2:
                status = args[1]
            post.add_fs(name, status, threading.current_thread().name)

        return stub

    for name in _POST_FS:
        monkeypatch.setattr(pipeline.firestore_admin, name, _fs_stub(name))

    return _PostHarness(h, post, state, audio_started)


def _run(pipeline, monkeypatch, ph: _PostHarness, *, parallel: bool) -> _Run:
    monkeypatch.setenv("POST_STAGE_PARALLEL", "1" if parallel else "0")
    ph.state["parallel"] = parallel
    ph.audio_started.clear()
    h, post = ph.h, ph.post
    e0 = len(h.rec.snapshot())
    d0 = len(h.rec.downloads)
    s0 = len(h.rec.statuses)
    n0 = h.complete.call_count
    with post._lock:
        c0, f0, z0, w0 = len(post.calls), len(post.fs), len(post.zoom_builds), len(post.coach_saw_audio)

    pipeline._process("bkt", _STUDENT_KEY, "u1", "a1")

    assert h.complete.call_count == n0 + 1
    with post._lock:
        calls = post.calls[c0:]
        fs = post.fs[f0:]
        zoom_builds = post.zoom_builds[z0:]
        saw = post.coach_saw_audio[w0:]
    by_name: dict[str, list[_StageCall]] = {n: [] for n in _POST_STAGES}
    for c in calls:
        by_name[c.name].append(c)
    return _Run(
        events=h.rec.snapshot()[e0:],
        calls=by_name,
        fs=fs,
        zoom_builds=zoom_builds,
        coach_saw_audio=saw,
        statuses=list(h.rec.statuses[s0:]),
        result=h.complete.call_args_list[n0].args[2],
        ref_dests=[d for _, d, _ in h.rec.downloads[d0:]],
    )


def _assert_cleanup_after_all_post_stages(run: _Run, student: str, stages) -> None:
    i_close = _first_index(run.events, ("close",))
    i_unlink = _first_index(run.events, ("unlink", student))
    for name in stages:
        i_end = _first_index(run.events, (f"{name}_end",))
        assert i_end < i_close, (name, run.events)
        assert i_end < i_unlink, (name, run.events)


def test_process_serial_and_parallel_same_calls_args_and_results(
    pipeline, monkeypatch, tmp_path, net_attempts
):
    ph = _install_post(pipeline, monkeypatch, tmp_path, mode=pipeline.models.MODE_EXPERT)
    student = str(ph.h.student_path)

    off = _run(pipeline, monkeypatch, ph, parallel=False)
    assert not ph.h.student_path.exists()
    on = _run(pipeline, monkeypatch, ph, parallel=True)
    assert not ph.h.student_path.exists()

    for run in (off, on):
        # 다섯 단계 각 1회, 같은 result 객체.
        for name in _POST_STAGES:
            assert len(run.calls[name]) == 1, (name, run.calls[name])
        for name in ("coach_text", "coach_audio", "spot_check", "compare_render"):
            assert run.calls[name][0].kwargs["result"] is run.result, name
        assert len(run.zoom_builds) == 1
        assert run.zoom_builds[0][1] is run.result
        # 코칭 문장은 두 모드 모두 timings_ms(= result["timingsMs"]) 그 객체로 잰다.
        assert run.calls["coach_text"][0].kwargs["timings_ms"] is run.result["timingsMs"]
        # compare_render 는 곁가지가 돌려준 객체를 그대로 받는다.
        cr = run.calls["compare_render"][0].kwargs
        assert cr["coach_audio_items"] is run.calls["coach_audio"][0].out
        assert cr["fault_zoom_items"] is run.calls["fault_zoom"][0].out
        # 기준 temp 는 그 런의 prefetch 다운로드 경로(이름이 런마다 달라 값 대조 대신).
        assert len(run.ref_dests) == 1
        assert cr["reference_local_video_path"] == run.ref_dests[0]
        assert not Path(run.ref_dests[0]).exists()
        _assert_cleanup_after_all_post_stages(run, student, _POST_STAGES)

    # 인자 — 키 집합 · 문자열 값이 두 모드에서 같다.
    for name in _POST_STAGES:
        k_off = off.calls[name][0].kwargs
        k_on = on.calls[name][0].kwargs
        assert set(k_off) == set(k_on), name
        for key in _STR_KWARGS:
            if key in k_off:
                assert k_off[key] == k_on[key], (name, key)

    # 직렬 — 전부 메인, 지금 순서 그대로.
    assert all(off.calls[n][0].thread == _MAIN for n in _POST_STAGES)
    assert off.zoom_builds[0][0] == _MAIN
    serial_expected = [f"{n}_{edge}" for n in _POST_STAGES for edge in ("start", "end")]
    off_order = [ev[0] for ev in off.events if ev[0] in serial_expected]
    assert off_order == serial_expected
    assert off.coach_saw_audio == []

    # 병렬 — 곁가지 post_side · 코칭 문장 · compare_render 메인 · 겹침 증명.
    for name in _SIDE_STAGES:
        assert on.calls[name][0].thread.startswith("post_side"), name
    assert on.zoom_builds[0][0].startswith("post_side")
    assert on.calls["coach_text"][0].thread == _MAIN
    assert on.calls["compare_render"][0].thread == _MAIN
    assert on.coach_saw_audio == [True]
    ev = on.events
    side_seq = [_first_index(ev, (f"{n}_{e}",)) for n in _SIDE_STAGES for e in ("start", "end")]
    assert side_seq == sorted(side_seq)  # 곁가지 안 순서는 직렬과 같다
    i_cr = _first_index(ev, ("compare_render_start",))
    assert i_cr > _first_index(ev, ("coach_text_end",))
    assert i_cr > _first_index(ev, ("spot_check_end",))

    # 결과 · 타이밍 키 · Firestore 기록 · 상태 전이.
    assert set(off.result) == set(on.result)
    assert set(on.result["timingsMs"]) == set(off.result["timingsMs"]) | {"post_parallel"}
    assert "post_parallel" not in off.result["timingsMs"]
    assert isinstance(on.result["timingsMs"]["post_parallel"], int)
    for key in ("coach_audio", "fault_zoom", "spot_check", "compare_render"):
        assert key in on.result["timingsMs"], key
    assert Counter((n, s) for n, s, _ in off.fs) == Counter((n, s) for n, s, _ in on.fs)
    assert off.statuses == on.statuses
    assert net_attempts == []


def test_process_parallel_fault_zoom_failure_is_isolated(
    pipeline, monkeypatch, tmp_path, net_attempts
):
    ph = _install_post(
        pipeline, monkeypatch, tmp_path,
        mode=pipeline.models.MODE_EXPERT, zoom_error=RuntimeError("zoom render boom"),
    )

    run = _run(pipeline, monkeypatch, ph, parallel=True)

    assert len(run.zoom_builds) == 1
    zoom_fs = [(n, s) for n, s, _ in run.fs if n == "update_analysis_fault_zoom"]
    assert zoom_fs == [("update_analysis_fault_zoom", pipeline.models.FAULT_ZOOM_STATUS_FAILED)]
    for name in ("coach_text", "spot_check", "compare_render"):
        assert len(run.calls[name]) == 1, name
    assert run.calls["spot_check"][0].thread.startswith("post_side")
    assert run.calls["fault_zoom"][0].out == []
    assert run.calls["compare_render"][0].kwargs["fault_zoom_items"] == []
    assert run.calls["compare_render"][0].kwargs["fault_zoom_items"] is run.calls["fault_zoom"][0].out
    _assert_cleanup_after_all_post_stages(run, str(ph.h.student_path), _POST_STAGES)
    assert not ph.h.student_path.exists()
    assert net_attempts == []


def test_process_parallel_mode3_first_analysis_has_no_fault_zoom(
    pipeline, monkeypatch, tmp_path, net_attempts
):
    ph = _install_post(pipeline, monkeypatch, tmp_path, mode=pipeline.models.MODE_SELF)

    run = _run(pipeline, monkeypatch, ph, parallel=True)

    assert run.calls["fault_zoom"] == []
    assert run.zoom_builds == []
    assert not any(n == "update_analysis_fault_zoom" for n, _, _ in run.fs)
    for name in ("coach_audio", "spot_check"):
        assert len(run.calls[name]) == 1, name
        assert run.calls[name][0].thread.startswith("post_side"), name
    assert len(run.calls["coach_text"]) == 1
    assert run.calls["coach_text"][0].thread == _MAIN
    assert len(run.calls["compare_render"]) == 1
    assert run.calls["compare_render"][0].thread == _MAIN
    assert run.coach_saw_audio == [True]
    _assert_cleanup_after_all_post_stages(
        run, str(ph.h.student_path), ("coach_text", "coach_audio", "spot_check", "compare_render")
    )
    assert not ph.h.student_path.exists()
    assert net_attempts == []
