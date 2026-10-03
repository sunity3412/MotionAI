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
