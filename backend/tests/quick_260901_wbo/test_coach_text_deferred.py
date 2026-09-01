"""coach_dual + hook 사후 스테이지 테스트 (quick-260901-wbo Task 2).

박제 정신 (260901-wbo PLAN verification_requirements):
  (a) complete 시점 — coachStatus='pending' 마커가 complete 이전에 실리고, tips 는
      수치 폴백 형상(detail2 부재), gemini_b kwarg None (소스 게이트 + build_result).
  (b) 사후 성공 — update_analysis_coach_text 를 전수 표 5필드 전부로 호출 +
      in-memory result 동기 갱신 ([[partial-field-writes-invisible-to-inmemory-doc]]).
  (b') bodyComparisonReport 부재 doc — body_hook field-path 미전송 (stub map 금지).
  (c) 일반 팁 단독(angle>=95) + veto applied — rebuild_tips_for_vision_fault 경유.
  (d) 양쪽 writer 실패 — FAILED + tips 미전송 (수치 폴백 잔존).
  (e) 스테이지 예외 — FAILED 마킹 + 재raise 0.

모든 테스트는 stdlib + pytest 만 — 실제 Firestore/LLM 호출 0 (mock).
"""

from __future__ import annotations

import inspect
import sys
import types

import pytest

from sunity_shared.analysis.kismam import JointAssessment


@pytest.fixture
def pipeline_app():
    import app  # noqa: E402 — conftest path 주입 후 지연 import

    return app


# ─────────────────── 공용 fixture 재료 ───────────────────


def _assessments() -> list[JointAssessment]:
    return [
        JointAssessment(
            key="left_knee", label_ko="왼쪽 무릎", score=60,
            deviation_deg=20.0, part="하체",
        ),
        JointAssessment(
            key="right_knee", label_ko="오른쪽 무릎", score=70,
            deviation_deg=15.0, part="하체",
        ),
        JointAssessment(
            key="left_elbow", label_ko="왼쪽 팔꿈치", score=80,
            deviation_deg=10.0, part="상체",
        ),
    ]


def _writer_details(prefix: str) -> dict:
    """coach writer 산출 형상 ({joint: {detail, detail2}} + _meta)."""
    out: dict = {}
    for joint in ("left_knee", "right_knee", "left_elbow"):
        out[joint] = {
            "detail": f"{prefix} {joint} 코칭 문장",
            "detail2": {
                "causes": [
                    {
                        "title": f"{prefix} 원인",
                        "explanation": f"{prefix} 설명",
                        "fix": f"{prefix} 처방",
                    }
                ],
                "coachNote": "강사와 함께 확인해 보세요.",
            },
        }
    out["_meta"] = {"model": f"{prefix}-model", "latency_ms": 42, "tokens_used": 7}
    return out


def _numeric_fallback_tips() -> list[dict]:
    """complete 시점 result.tips 형상 (coach_details={} — detail2 부재)."""
    return [
        {"joint": "left_knee", "title": "왼쪽 무릎 신전",
         "detail": "왼쪽 무릎 각도가 기준과 평균 20° 차이가 납니다."},
        {"joint": "right_knee", "title": "오른쪽 무릎 신전",
         "detail": "오른쪽 무릎 각도가 기준과 평균 15° 차이가 납니다."},
        {"joint": "left_elbow", "title": "왼쪽 팔꿈치 정렬",
         "detail": "왼쪽 팔꿈치 각도가 기준과 평균 10° 차이가 납니다."},
    ]


class _CoachTextSpy:
    """firestore_admin.update_analysis_coach_text mock — kwargs 캡처."""

    def __init__(self, fail_on_status: str | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_on_status = fail_on_status

    def __call__(self, uid, analysis_id, **kwargs) -> None:
        self.calls.append({"uid": uid, "analysis_id": analysis_id, **kwargs})
        if (
            self.fail_on_status is not None
            and kwargs.get("status") == self.fail_on_status
        ):
            raise RuntimeError("firestore update failed (mock)")


class _FakeWriter:
    def __init__(self, details: dict) -> None:
        self._details = details

    def write(self, context: dict) -> dict:
        return dict(self._details)


def _install_hook_writer(monkeypatch, *, force_payload, body_payload) -> None:
    """sunity_shared.gemini.coach_hook_writer fake 모듈 주입 (lazy import 대상).

    fault_zoom 테스트의 sys.modules 주입 선례 — 실 Gemini SDK import 회피.
    """
    bundle = types.SimpleNamespace(
        force_pattern_inference=force_payload,
        body_comparison_report=body_payload,
    )

    class _FakeHookWriter:
        def build_coach_hooks(self, *, force_findings, body_findings):
            return bundle

    fake_mod = types.ModuleType("sunity_shared.gemini.coach_hook_writer")
    fake_mod.GeminiCoachHookWriter = _FakeHookWriter
    monkeypatch.setitem(
        sys.modules, "sunity_shared.gemini.coach_hook_writer", fake_mod
    )


def _hook_payload(summary: str) -> dict:
    return {
        "auto_findings_summary": summary,
        "open_questions_for_coach": ["강사와 확인해 보세요."],
        "suggested_cues": ["큐 하나", "큐 둘"],
    }


def _run(
    pipeline_app,
    *,
    result: dict,
    spy: _CoachTextSpy,
    monkeypatch,
    force_findings: list | None = None,
    body_findings: list | None = None,
    force_dict: dict | None = None,
    body_dict: dict | None = None,
    gemini_details: dict | None = None,
    cerebras_details: dict | None = None,
) -> dict:
    monkeypatch.setattr(
        pipeline_app.firestore_admin, "update_analysis_coach_text", spy
    )
    monkeypatch.setattr(pipeline_app, "_coach_enabled", lambda: True)
    monkeypatch.setattr(
        pipeline_app,
        "_ensure_gemini_coach_writer",
        lambda: _FakeWriter(gemini_details if gemini_details is not None else {}),
    )
    monkeypatch.setattr(
        pipeline_app,
        "_COACH_WRITER",
        _FakeWriter(cerebras_details if cerebras_details is not None else {}),
    )
    timings: dict = {}
    pipeline_app._run_deferred_coach_text(
        result=result,
        assessments=_assessments(),
        coach_context={"mode": "mode1"},
        force_findings=force_findings or [],
        body_findings=body_findings or [],
        force_pattern_inference_dict=force_dict,
        body_comparison_report_dict=body_dict,
        uid="u1",
        analysis_id="a1",
        timings_ms=timings,
    )
    return timings


# ─────────────────── (a) complete 시점 — pending 마커 + coach 동기 소멸 ──────


def test_process_source_gate_pending_before_complete(pipeline_app) -> None:
    """_process 소스 게이트 — pending 마커가 complete 이전, coach 동기 산출 소멸.

    (a) 전체 _process 실행은 영상/GPU 없이 불가 — 소스 순서 게이트로 증명한다
    (test_force_pattern_no_severity_use.py AST 게이트 선례).
    """
    src = inspect.getsource(pipeline_app._process)
    marker = 'result["coachStatus"] = models.COACH_STATUS_PENDING'
    complete = "firestore_admin.complete_analysis("
    deferred = "_run_deferred_coach_text("
    assert marker in src, "pending 마커 부재"
    assert src.index(marker) < src.index(complete), "pending 마커가 complete 이후"
    # 영역 B audit 은 사후로 이동 — complete kwarg 는 None 고정.
    assert "gemini_b=None" in src
    # coach_dual 동기 산출 소멸 (섹션 조립/audit/hook Gemini 콜 전부 사후로).
    assert "assemble_dual_coach_sections" not in src
    assert "_gemini_b_audit_payload" not in src
    assert "GeminiCoachHookWriter" not in src
    # 사후 스테이지 호출은 complete 이후.
    assert deferred in src
    assert src.index(deferred) > src.index(complete)


def test_complete_tips_are_numeric_fallback_shape() -> None:
    """(a) coach_details={} 의 build_result tips = 수치 폴백 (detail2 부재)."""
    from sunity_shared.analysis import assemble

    result = assemble.build_result(
        _assessments(),
        {"angle": 70, "line": 80, "stability": 75},
        70,
        {"mode": "mode1"},
        "https://x/video.mp4",
        coach_details={},
    )
    assert len(result["tips"]) == 3
    for tip in result["tips"]:
        assert "detail2" not in tip
        assert "차이가 납니다" in tip["detail"]  # 수치 폴백 문구


# ─────────────────── (b) 사후 성공 — 5필드 전부 + in-memory 동기 ───────────


def test_deferred_success_sends_all_five_fields(pipeline_app, monkeypatch) -> None:
    spy = _CoachTextSpy()
    _install_hook_writer(
        monkeypatch,
        force_payload=_hook_payload("force 요약"),
        body_payload=_hook_payload("body 요약"),
    )
    result = {"tips": _numeric_fallback_tips()}
    force_dict = {"findings": []}
    body_dict = {"findings": []}
    _run(
        pipeline_app,
        result=result,
        spy=spy,
        monkeypatch=monkeypatch,
        force_findings=[{"f": 1}],
        body_findings=[{"b": 1}],
        force_dict=force_dict,
        body_dict=body_dict,
        gemini_details=_writer_details("gemini"),
        cerebras_details=_writer_details("cerebras"),
    )
    assert len(spy.calls) == 1
    call = spy.calls[0]
    assert (call["uid"], call["analysis_id"]) == ("u1", "a1")
    assert call["status"] == "done"
    # 전수 표 5필드 — tips 통째 + hook 2 + geminiB + status.
    assert isinstance(call["tips"], list) and len(call["tips"]) == 3
    for tip in call["tips"]:
        assert "detail2" in tip  # 코칭 텍스트 승격
    assert call["force_hook"]["autoFindingsSummary"] == "force 요약"
    assert call["body_hook"]["autoFindingsSummary"] == "body 요약"
    assert call["gemini_b"]["dualTrack"] is True
    # in-memory 동기 갱신 (partial-field-writes-invisible-to-inmemory-doc 갑주).
    assert result["tips"] == call["tips"]
    assert result["coachStatus"] == "done"
    assert force_dict["coachCommentHook"] == call["force_hook"]
    assert body_dict["coachCommentHook"] == call["body_hook"]


def test_deferred_stage_timings_logged_locally(pipeline_app, monkeypatch) -> None:
    """coach_dual/coach_hook 스테이지 계측 — timings dict 에만 (doc 저장은 이미 끝)."""
    spy = _CoachTextSpy()
    _install_hook_writer(
        monkeypatch,
        force_payload=_hook_payload("f"),
        body_payload=None,
    )
    timings = _run(
        pipeline_app,
        result={"tips": _numeric_fallback_tips()},
        spy=spy,
        monkeypatch=monkeypatch,
        force_findings=[{"f": 1}],
        force_dict={"findings": []},
        gemini_details=_writer_details("gemini"),
        cerebras_details=_writer_details("cerebras"),
    )
    assert "coach_dual" in timings
    assert "coach_hook" in timings


# ─────────────────── (b') body 리포트 부재 — stub map 생성 금지 ─────────────


def test_body_hook_omitted_when_report_absent(pipeline_app, monkeypatch) -> None:
    """bodyComparisonReport 부재 doc — body_hook 미전송 (체커 warning 1)."""
    spy = _CoachTextSpy()
    # hook bundle 은 body payload 를 반환하지만 — doc 에 리포트가 없으면 차단.
    _install_hook_writer(
        monkeypatch,
        force_payload=_hook_payload("force 요약"),
        body_payload=_hook_payload("body 요약"),
    )
    _run(
        pipeline_app,
        result={"tips": _numeric_fallback_tips()},
        spy=spy,
        monkeypatch=monkeypatch,
        force_findings=[{"f": 1}],
        body_findings=[{"b": 1}],
        force_dict={"findings": []},
        body_dict=None,  # complete 시점 bodyComparisonReport 미방출 doc
        gemini_details=_writer_details("gemini"),
        cerebras_details=_writer_details("cerebras"),
    )
    call = spy.calls[0]
    assert call["body_hook"] is None
    assert call["force_hook"] is not None


def test_hook_gemini_payload_absent_keeps_canned(pipeline_app, monkeypatch) -> None:
    """hook bundle payload 부재(canned 폴백) — hook field-path 미전송."""
    spy = _CoachTextSpy()
    _install_hook_writer(monkeypatch, force_payload=None, body_payload=None)
    _run(
        pipeline_app,
        result={"tips": _numeric_fallback_tips()},
        spy=spy,
        monkeypatch=monkeypatch,
        force_findings=[{"f": 1}],
        force_dict={"findings": []},
        body_dict={"findings": []},
        gemini_details=_writer_details("gemini"),
        cerebras_details=_writer_details("cerebras"),
    )
    call = spy.calls[0]
    assert call["force_hook"] is None
    assert call["body_hook"] is None
    assert call["status"] == "done"


# ─────────────────── (c) 일반 팁 + veto applied — rebuild 경유 ──────────────


def test_generic_tip_with_veto_applied_rebuilds(pipeline_app, monkeypatch) -> None:
    spy = _CoachTextSpy()
    result = {
        "tips": [
            {
                "joint": None,
                "title": "정은지 선수와 거의 동일한 자세입니다",
                "detail": "관절각 일치도 97점 — 자세 차이가 거의 없어요.",
            }
        ],
        "visionVeto": {"status": "applied", "faultJoints": ["left_knee"]},
    }
    _run(
        pipeline_app,
        result=result,
        spy=spy,
        monkeypatch=monkeypatch,
        gemini_details=_writer_details("gemini"),
        cerebras_details=_writer_details("cerebras"),
    )
    call = spy.calls[0]
    assert call["status"] == "done"
    # per-joint 재조립 — veto fault 관절 선두 (rebuild_tips_for_vision_fault 규율).
    assert call["tips"][0]["joint"] == "left_knee"
    assert all(t["joint"] is not None for t in call["tips"])
    assert result["tips"] == call["tips"]  # in-memory 동기


def test_generic_tip_without_veto_keeps_generic(pipeline_app, monkeypatch) -> None:
    """veto 미적용 + 일반 팁 — rebuild 게이트 불통과 = tips 불변 (종전과 동일)."""
    spy = _CoachTextSpy()
    generic = [
        {
            "joint": None,
            "title": "정은지 선수와 거의 동일한 자세입니다",
            "detail": "관절각 일치도 97점 — 자세 차이가 거의 없어요.",
        }
    ]
    result = {"tips": list(generic)}
    _run(
        pipeline_app,
        result=result,
        spy=spy,
        monkeypatch=monkeypatch,
        gemini_details=_writer_details("gemini"),
        cerebras_details=_writer_details("cerebras"),
    )
    call = spy.calls[0]
    assert call["status"] == "done"
    assert call["tips"] == generic  # 코칭이 tips 에 안 실리는 케이스 유지


# ─────────────────── (d) 양쪽 writer 실패 — FAILED + tips 미전송 ────────────


def test_both_writers_failed_marks_failed_without_tips(
    pipeline_app, monkeypatch
) -> None:
    spy = _CoachTextSpy()
    result = {"tips": _numeric_fallback_tips()}
    _run(
        pipeline_app,
        result=result,
        spy=spy,
        monkeypatch=monkeypatch,
        gemini_details={},  # user-visible 키 0 = 실패
        cerebras_details={},
    )
    call = spy.calls[0]
    assert call["status"] == "failed"
    assert call.get("tips") is None  # tips 미전송 — 수치 폴백 잔존
    assert call["gemini_b"]["fallbackReason"] == "both_failed"
    assert result["coachStatus"] == "failed"
    # in-memory tips 는 수치 폴백 그대로 (최후 바닥 불변).
    assert result["tips"] == _numeric_fallback_tips()


# ─────────────────── (e) 스테이지 예외 — FAILED 마킹 + 재raise 0 ────────────


def test_stage_exception_marks_failed_no_reraise(pipeline_app, monkeypatch) -> None:
    spy = _CoachTextSpy()
    monkeypatch.setattr(
        pipeline_app.firestore_admin, "update_analysis_coach_text", spy
    )

    def _boom():
        raise RuntimeError("stage boom")

    monkeypatch.setattr(pipeline_app, "_coach_enabled", _boom)
    # 재raise 되지 않아야 한다 (분석은 이미 complete).
    pipeline_app._run_deferred_coach_text(
        result={"tips": _numeric_fallback_tips()},
        assessments=_assessments(),
        coach_context={},
        force_findings=[],
        body_findings=[],
        force_pattern_inference_dict=None,
        body_comparison_report_dict=None,
        uid="u1",
        analysis_id="a1",
        timings_ms={},
    )
    assert [c["status"] for c in spy.calls] == ["failed"]
    assert spy.calls[0].get("tips") is None


def test_failed_marking_write_exception_swallowed(pipeline_app, monkeypatch) -> None:
    """스테이지 예외 + failed 마킹 write 실패 → 예외 삼킴 (앱 시간 상한 방어)."""
    spy = _CoachTextSpy(fail_on_status="failed")
    monkeypatch.setattr(
        pipeline_app.firestore_admin, "update_analysis_coach_text", spy
    )

    def _boom():
        raise RuntimeError("stage boom")

    monkeypatch.setattr(pipeline_app, "_coach_enabled", _boom)
    pipeline_app._run_deferred_coach_text(
        result={"tips": _numeric_fallback_tips()},
        assessments=_assessments(),
        coach_context={},
        force_findings=[],
        body_findings=[],
        force_pattern_inference_dict=None,
        body_comparison_report_dict=None,
        uid="u1",
        analysis_id="a1",
        timings_ms={},
    )
    assert [c["status"] for c in spy.calls] == ["failed"]
