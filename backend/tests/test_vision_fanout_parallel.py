"""Phase 27 Task 3 (SPD-03/05) — veto fan-out 병렬화 결정론·fail-closed 단위 테스트.

박제 정신 (27-05 must_haves / 27-RESEARCH Pattern 4·Pitfall 4·7):
  · 병렬 실행이라도 집계 입력 순서는 call_plan 인덱스 순 (as_completed 금지) — 지연
    주입(느린 콜)에도 parsed_verdicts[0] = call_plan[0] (T-27-12 결정론).
  · 부분 완료(completed < planned)는 fail-closed resource_limited — 부분 verdict 금지
    (T-27-13, D-13 HIGH-2 Option A).
  · GEMINI_FANOUT_WORKERS 폴백(1 이면 순차 등가, 429 시 축소 레버, T-27-15).

전부 mock — google.genai / 실 Gemini API 호출 0 (`_call_gemini_comparison` monkeypatch).
"""

from __future__ import annotations

import json
import threading
import time

import pytest

from sunity_shared.analysis import gemini_vision_scorer as gvs


def _verdict_json(part_scope: str) -> str:
    """scope 를 primary_fault 에 인코딩한 유효 verdict JSON (differences 없음)."""
    return json.dumps(
        {
            "primary_fault": f"fault_{part_scope}",
            "dominant_severity": "moderate",
            "differences": [],
        }
    )


@pytest.fixture(autouse=True)
def _clear_fanout_env(monkeypatch):
    monkeypatch.delenv("GEMINI_FANOUT_WORKERS", raising=False)
    yield


def test_fanout_preserves_call_plan_order_under_delay(monkeypatch):
    """지연 주입 — call_plan[0](upper_body) 이 가장 늦게 끝나도 parsed_verdicts[0] 유지.

    as_completed 였다면 먼저 끝난 lower_body/line 이 [0] 에 들어가 verdict.primary_fault
    가 달라진다 → 이 assert 가 as_completed 회귀를 잡는다 (Pitfall 4).
    """
    def _fake_compare(client, ref, student, at_seconds, part_scope=None, media_kind="video"):
        # call_plan[0] = upper_body 에 큰 지연 → 완료 순서 최후.
        time.sleep(0.25 if part_scope == "upper_body" else 0.01)
        return _verdict_json(part_scope)

    monkeypatch.setattr(gvs, "_call_gemini_comparison", _fake_compare)

    result = gvs._run_part_frame_fanout(
        client=None,
        ref_uploaded="ref",
        student_uploaded="stu",
        part_scopes=["upper_body", "lower_body", "line"],
        at_seconds=None,
    )

    assert result["status"] == "candidate_verdict"
    assert result["telemetry"]["completedCalls"] == 3
    assert result["telemetry"]["plannedCalls"] == 3
    # 지연된 upper_body(call_plan[0]) 가 primary — 인덱스 순 join 증명.
    assert result["verdict"].primary_fault == "fault_upper_body"


def test_fanout_executes_calls_in_parallel(monkeypatch):
    """4콜이 동시에 in-flight — 관측 최대 동시성 ≥ 2 (순차면 1, RED)."""
    lock = threading.Lock()
    state = {"cur": 0, "max": 0}

    def _fake_compare(client, ref, student, at_seconds, part_scope=None, media_kind="video"):
        with lock:
            state["cur"] += 1
            state["max"] = max(state["max"], state["cur"])
        time.sleep(0.05)
        with lock:
            state["cur"] -= 1
        return _verdict_json(part_scope)

    monkeypatch.setattr(gvs, "_call_gemini_comparison", _fake_compare)

    result = gvs._run_part_frame_fanout(
        client=None,
        ref_uploaded="ref",
        student_uploaded="stu",
        part_scopes=["upper_body", "lower_body", "line"],
        at_seconds=None,
        upper_still_handles=("ref_img", "stu_img"),  # upper×2 → planned=4
    )

    assert result["telemetry"]["plannedCalls"] == 4
    assert result["telemetry"]["completedCalls"] == 4
    assert state["max"] >= 2, (
        f"동시 실행 관측 실패 (max={state['max']}) — 병렬화 미적용(순차)"
    )


def test_fanout_fail_closed_on_budget_exhaustion(monkeypatch):
    """예산 소진(clock) 으로 일부만 완료 → resource_limited (부분 verdict 금지)."""
    def _fake_compare(client, ref, student, at_seconds, part_scope=None, media_kind="video"):
        return _verdict_json(part_scope)

    monkeypatch.setattr(gvs, "_call_gemini_comparison", _fake_compare)

    # clock 시퀀스: start=0 → iter0=1 → iter1=2 → iter2=999(예산 초과) → break.
    seq = [0.0, 1.0, 2.0, 999.0, 999.0, 999.0, 999.0]
    idx = {"i": 0}

    def _clock():
        v = seq[idx["i"]] if idx["i"] < len(seq) else seq[-1]
        idx["i"] += 1
        return v

    result = gvs._run_part_frame_fanout(
        client=None,
        ref_uploaded="ref",
        student_uploaded="stu",
        part_scopes=["upper_body", "lower_body", "line"],
        at_seconds=None,
        clock=_clock,
        wall_budget_s=100.0,
    )

    assert result["status"] == "resource_limited"
    assert result["verdict"] is None
    assert result["supported_differences"] == []
    tel = result["telemetry"]
    assert tel["completedCalls"] < tel["plannedCalls"]
    assert tel["samplingComplete"] is False


def test_fanout_budget_exhaustion_returns_without_waiting_inflight(monkeypatch):
    """WR-01 (27-REVIEW): 예산 소진 break 시 blocked in-flight/미시작 콜 완료를
    기다리지 않고 즉시 resource_limited 반환 — wall budget hard bound.

    구 with-block(shutdown wait=True)이면 release 가 set 될 때까지(최대 10s) 반환이
    지연돼 elapsed 가드가 RED. 집계 의미론(fail-closed)은 기존 테스트가 방어."""
    release = threading.Event()

    def _fake_compare(client, ref, student, at_seconds, part_scope=None, media_kind="video"):
        if part_scope != "upper_body":
            release.wait(timeout=10)  # in-flight 블록 — 반환이 이걸 기다리면 회귀
        return _verdict_json(part_scope)

    monkeypatch.setattr(gvs, "_call_gemini_comparison", _fake_compare)

    # clock: start=0 → iter0 remaining=99(join OK) → iter1=999(예산 초과) → break.
    seq = [0.0, 1.0, 999.0]
    idx = {"i": 0}

    def _clock():
        v = seq[idx["i"]] if idx["i"] < len(seq) else seq[-1]
        idx["i"] += 1
        return v

    t0 = time.monotonic()
    try:
        result = gvs._run_part_frame_fanout(
            client=None,
            ref_uploaded="ref",
            student_uploaded="stu",
            part_scopes=["upper_body", "lower_body", "line"],
            at_seconds=None,
            clock=_clock,
            wall_budget_s=100.0,
        )
        elapsed = time.monotonic() - t0
    finally:
        release.set()  # 블록된 스레드 해제 (teardown)

    assert result["status"] == "resource_limited"  # fail-closed 의미론 불변
    assert result["telemetry"]["completedCalls"] < result["telemetry"]["plannedCalls"]
    # hard bound: blocked 콜(10s) 완료를 기다리지 않았다.
    assert elapsed < 5.0, f"budget break 후 in-flight 대기 감지 (elapsed={elapsed:.1f}s)"


def test_fanout_workers_one_is_sequential_equivalent(monkeypatch):
    """GEMINI_FANOUT_WORKERS=1 → 동시성 1(순차 등가) + 결과 동일."""
    monkeypatch.setenv("GEMINI_FANOUT_WORKERS", "1")
    lock = threading.Lock()
    state = {"cur": 0, "max": 0}

    def _fake_compare(client, ref, student, at_seconds, part_scope=None, media_kind="video"):
        with lock:
            state["cur"] += 1
            state["max"] = max(state["max"], state["cur"])
        time.sleep(0.02)
        with lock:
            state["cur"] -= 1
        return _verdict_json(part_scope)

    monkeypatch.setattr(gvs, "_call_gemini_comparison", _fake_compare)

    result = gvs._run_part_frame_fanout(
        client=None,
        ref_uploaded="ref",
        student_uploaded="stu",
        part_scopes=["upper_body", "lower_body", "line"],
        at_seconds=None,
    )

    assert state["max"] == 1, f"workers=1 인데 동시 실행 관측 (max={state['max']})"
    assert result["status"] == "candidate_verdict"
    assert result["verdict"].primary_fault == "fault_upper_body"
