"""pipeline selfScore 훅 — `_record_self_score_if_needed` · `_mark_self_check_failed_if_needed` (Phase 38-08 Task 1).

D-10 · 리뷰 R2 · R8. 잠그는 것:
  · 기준 doc 이 권위다 — 분석 doc 의 표식(`selfCheckForReference` · `selfCheckJobId`)은 힌트일 뿐이고,
    `firestore_admin.self_check_authorized(ref_doc, uid, analysis_id, job_id)` 를 지난 경우에만 writer 를 부른다.
    위조 표식 · 다른 공급자 refId · stale analysis id · pending 전 완료(R8) · 기준 doc 없음 → writer 0회.
  · 기록 값은 `result["overallScore"]`(= deductionBreakdown.final, 화면 점수) — dimensionScores 가 아니다.
  · 기록 실패·읽기 실패는 삼킨다(분석은 이미 complete — 훅이 분석을 막지 않는다).
  · 호출 위치: `_process` 의 `log.info("분석 완료 …")` 바로 뒤 1곳, `lambda_handler` except 3곳 `fail_analysis` 뒤.

`test_pipeline_dispatch.py` 의 fixture 어법(모듈 캐시 리셋 + monkeypatch)을 따른다. Firestore · S3 · Pod 0.
"""

from __future__ import annotations

import ast
import importlib
import json
import logging
import sys
from pathlib import Path

import pytest

_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))
_APP_PY = _PIPELINE / "app.py"

REF = "r1"
JOB = "A"


def _ref_doc(**over) -> dict:
    doc = {
        "supplierUid": "u1",
        "selfCheckAnalysisId": "a1",
        "selfCheckJobId": JOB,
        "registrationStatus": "active",
    }
    doc.update(over)
    return doc


def _meta(ref=REF, job=JOB) -> dict:
    m = {"mode": "mode1", "referenceMotionId": ref}
    if ref is not None:
        m["selfCheckForReference"] = ref
    if job is not None:
        m["selfCheckJobId"] = job
    return m


@pytest.fixture
def app(monkeypatch):
    for k in ("RUNPOD_ANALYZE_URL", "RUNPOD_AUTH_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    sys.modules.pop("app", None)
    import app as mod  # noqa: WPS433

    importlib.reload(mod)

    calls: dict = {"writer": [], "get_ref": [], "get_analysis": [], "authorized": []}
    state: dict = {"refs": {REF: _ref_doc()}, "analyses": {}, "writer_raises": None}

    def fake_get_ref(ref_id):
        calls["get_ref"].append(ref_id)
        doc = state["refs"].get(ref_id)
        return dict(doc) if doc is not None else None

    def fake_writer(ref_id, **kw):
        calls["writer"].append((ref_id, kw))
        if state["writer_raises"] is not None:
            raise state["writer_raises"]
        return True

    def fake_get_analysis(uid, analysis_id):
        calls["get_analysis"].append((uid, analysis_id))
        v = state["analyses"].get((uid, analysis_id))
        if isinstance(v, Exception):
            raise v
        return v

    real_authorized = mod.firestore_admin.self_check_authorized

    def spy_authorized(ref_doc, **kw):
        calls["authorized"].append(kw)
        return real_authorized(ref_doc, **kw)

    monkeypatch.setattr(mod.firestore_admin, "get_reference_registration", fake_get_ref)
    monkeypatch.setattr(mod.firestore_admin, "set_reference_self_check", fake_writer)
    monkeypatch.setattr(mod.firestore_admin, "get_analysis", fake_get_analysis)
    monkeypatch.setattr(mod.firestore_admin, "self_check_authorized", spy_authorized)
    mod._t_calls = calls
    mod._t_state = state
    return mod


# ── _record_self_score_if_needed ──────────────────────────────────────────


def test_record_writes_screen_score_once(app):
    app._record_self_score_if_needed(_meta(), {"overallScore": 97.3}, "u1", "a1")

    assert app._t_calls["writer"] == [
        (
            REF,
            {
                "status": app.models.SELF_CHECK_STATUS_DONE,
                "uid": "u1",
                "analysis_id": "a1",
                "job_id": JOB,
                "score": 97.3,
            },
        )
    ]
    assert app._t_calls["authorized"] == [{"uid": "u1", "analysis_id": "a1", "job_id": JOB}]


def test_record_int_score_is_float(app):
    app._record_self_score_if_needed(_meta(), {"overallScore": 100}, "u1", "a1")

    (_, kw), = app._t_calls["writer"]
    assert kw["score"] == 100.0 and isinstance(kw["score"], float)


def test_record_ignores_dimension_scores(app):
    """화면 점수(overallScore)만 — dimensionScores 가 있어도 overallScore 없으면 쓰지 않는다."""
    app._record_self_score_if_needed(
        _meta(), {"dimensionScores": {"line": 91.0}}, "u1", "a1"
    )
    assert app._t_calls["writer"] == []


def test_record_no_marker_reads_nothing(app):
    app._record_self_score_if_needed(_meta(ref=None, job=None), {"overallScore": 90.0}, "u1", "a1")

    assert app._t_calls["writer"] == []
    assert app._t_calls["get_ref"] == []


def test_record_marker_without_job_is_skipped(app):
    app._record_self_score_if_needed(_meta(job=None), {"overallScore": 90.0}, "u1", "a1")

    assert app._t_calls["writer"] == []
    assert app._t_calls["get_ref"] == []


def test_record_none_meta_is_skipped(app):
    app._record_self_score_if_needed(None, {"overallScore": 90.0}, "u1", "a1")
    assert app._t_calls["writer"] == []


@pytest.mark.parametrize("bad", [None, "97.3", True, float("nan"), float("inf")])
def test_record_non_numeric_score_warns_and_skips(app, caplog, bad):
    caplog.set_level(logging.WARNING)
    result = {} if bad is None else {"overallScore": bad}

    app._record_self_score_if_needed(_meta(), result, "u1", "a1")

    assert app._t_calls["writer"] == []
    assert any("selfScore" in r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)


def test_record_writer_exception_is_swallowed(app, caplog):
    caplog.set_level(logging.ERROR)
    app._t_state["writer_raises"] = RuntimeError("firestore down")

    app._record_self_score_if_needed(_meta(), {"overallScore": 97.3}, "u1", "a1")  # 예외 없이 반환

    assert len(app._t_calls["writer"]) == 1
    assert any("selfScore 기록 실패" in r.getMessage() for r in caplog.records)


def test_record_ref_read_exception_is_swallowed(app, monkeypatch):
    def boom(ref_id):
        raise RuntimeError("read failed")

    monkeypatch.setattr(app.firestore_admin, "get_reference_registration", boom)
    app._record_self_score_if_needed(_meta(), {"overallScore": 97.3}, "u1", "a1")
    assert app._t_calls["writer"] == []


# ── R2 · R8 권위 가드 — 위조 표식 4케이스 + 기준 doc 없음 + job 불일치 ──────────


def test_guard_forged_marker_by_other_user(app, caplog):
    """(a) 정상 사용자 u9 가 자기 분석 doc 에 r1 표식을 넣었다 — r1.supplierUid == u1 이라 거부."""
    caplog.set_level(logging.WARNING)

    app._record_self_score_if_needed(_meta(), {"overallScore": 12.0}, "u9", "a1")

    assert app._t_calls["writer"] == []
    assert any("자기 재현성 표식 불일치" in r.getMessage() for r in caplog.records)


def test_guard_other_supplier_ref_id(app):
    """(b) 공급자 u1 의 분석이 다른 공급자(u2)의 refId r2 를 가리킨다."""
    app._t_state["refs"]["r2"] = _ref_doc(supplierUid="u2", selfCheckAnalysisId="a1")

    app._record_self_score_if_needed(_meta(ref="r2"), {"overallScore": 97.3}, "u1", "a1")

    assert app._t_calls["writer"] == []


def test_guard_stale_analysis_id(app):
    """(c) 기준 doc 의 예정 자기 분석은 a0 — 옛 분석 a1 의 완료는 쓰지 않는다."""
    app._t_state["refs"][REF] = _ref_doc(selfCheckAnalysisId="a0")

    app._record_self_score_if_needed(_meta(), {"overallScore": 97.3}, "u1", "a1")

    assert app._t_calls["writer"] == []


def test_guard_completion_before_pending(app):
    """(d) R8 — 완료 훅이 pending 선기록보다 먼저 왔다(selfCheckAnalysisId 없음) → 쓰지 않는다."""
    doc = _ref_doc()
    del doc["selfCheckAnalysisId"]
    del doc["selfCheckJobId"]
    app._t_state["refs"][REF] = doc

    app._record_self_score_if_needed(_meta(), {"overallScore": 97.3}, "u1", "a1")

    assert app._t_calls["writer"] == []


def test_guard_ref_doc_missing(app):
    app._t_state["refs"].clear()

    app._record_self_score_if_needed(_meta(), {"overallScore": 97.3}, "u1", "a1")

    assert app._t_calls["writer"] == []


def test_guard_job_mismatch(app):
    app._t_state["refs"][REF] = _ref_doc(selfCheckJobId="B")

    app._record_self_score_if_needed(_meta(), {"overallScore": 97.3}, "u1", "a1")

    assert app._t_calls["writer"] == []


# ── _mark_self_check_failed_if_needed ─────────────────────────────────────


def test_mark_failed_writes_failed_once(app):
    app._t_state["analyses"][("u1", "a1")] = _meta()

    app._mark_self_check_failed_if_needed("u1", "a1")

    assert app._t_calls["writer"] == [
        (
            REF,
            {
                "status": app.models.SELF_CHECK_STATUS_FAILED,
                "uid": "u1",
                "analysis_id": "a1",
                "job_id": JOB,
            },
        )
    ]


def test_mark_failed_no_marker(app):
    app._t_state["analyses"][("u1", "a1")] = _meta(ref=None, job=None)

    app._mark_self_check_failed_if_needed("u1", "a1")

    assert app._t_calls["writer"] == []
    assert app._t_calls["get_ref"] == []


def test_mark_failed_missing_analysis_doc(app):
    app._mark_self_check_failed_if_needed("u1", "a1")
    assert app._t_calls["writer"] == []


def test_mark_failed_read_exception_swallowed(app):
    app._t_state["analyses"][("u1", "a1")] = RuntimeError("read failed")

    app._mark_self_check_failed_if_needed("u1", "a1")  # 예외 없이 반환

    assert app._t_calls["writer"] == []


def test_mark_failed_forged_marker(app):
    app._t_state["analyses"][("u9", "a1")] = _meta()

    app._mark_self_check_failed_if_needed("u9", "a1")

    assert app._t_calls["writer"] == []


def test_mark_failed_writer_exception_swallowed(app):
    app._t_state["analyses"][("u1", "a1")] = _meta()
    app._t_state["writer_raises"] = RuntimeError("firestore down")

    app._mark_self_check_failed_if_needed("u1", "a1")

    assert len(app._t_calls["writer"]) == 1


# ── lambda_handler except 3곳 배선 ─────────────────────────────────────────


def _sqs_event(bucket: str, key: str) -> dict:
    body = {"Records": [{"s3": {"bucket": {"name": bucket}, "object": {"key": key}}}]}
    return {"Records": [{"body": json.dumps(body)}]}


@pytest.mark.parametrize("exc_name", ["NoHumanError", "NotPoleMotionError", "RuntimeError"])
def test_lambda_handler_failure_marks_self_check(app, monkeypatch, exc_name):
    order: list = []
    exc_cls = getattr(app, exc_name) if exc_name != "RuntimeError" else RuntimeError

    def fake_process(bucket, key, uid, analysis_id):
        raise exc_cls("x")

    monkeypatch.setattr(app, "_process", fake_process)
    monkeypatch.setattr(
        app.firestore_admin, "fail_analysis", lambda uid, aid, code, msg: order.append(("fail", uid, aid))
    )
    monkeypatch.setattr(
        app, "_mark_self_check_failed_if_needed", lambda uid, aid: order.append(("mark", uid, aid))
    )

    app.lambda_handler(_sqs_event("b", "uploads/u1/a1.mp4"), None)

    assert order == [("fail", "u1", "a1"), ("mark", "u1", "a1")]


def test_lambda_handler_success_does_not_mark(app, monkeypatch):
    marks: list = []
    monkeypatch.setattr(app, "_process", lambda *a: None)
    monkeypatch.setattr(app, "_mark_self_check_failed_if_needed", lambda uid, aid: marks.append(1))

    app.lambda_handler(_sqs_event("b", "uploads/u1/a1.mp4"), None)

    assert marks == []


# ── 호출 위치 / 비교식 단일 출처 (AST) ─────────────────────────────────────


def _func_node(name: str) -> ast.FunctionDef:
    tree = ast.parse(_APP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} 없음")


def test_process_calls_record_hook_right_after_completion_log():
    lines = _APP_PY.read_text(encoding="utf-8").splitlines()
    done = [i for i, s in enumerate(lines) if 'log.info("분석 완료 uid=%s analysis_id=%s mode=%s"' in s]
    hook = [i for i, s in enumerate(lines) if "_record_self_score_if_needed(meta, result, uid, analysis_id)" in s]
    assert len(done) == 1 and len(hook) == 1
    assert 0 < hook[0] - done[0] <= 3

    proc = _func_node("_process")
    assert proc.lineno <= hook[0] + 1 <= proc.end_lineno


@pytest.mark.parametrize("name", ["_record_self_score_if_needed", "_mark_self_check_failed_if_needed", "_self_check_target"])
def test_hooks_do_not_restate_the_guard(name):
    """비교식은 firestore_admin.self_check_authorized 하나 — 훅 안에 supplierUid 등 비교를 다시 쓰지 않는다."""
    src = ast.get_source_segment(_APP_PY.read_text(encoding="utf-8"), _func_node(name))
    assert "supplierUid" not in src
    assert "selfCheckAnalysisId" not in src
