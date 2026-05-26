"""pipeline lambda_handler — RunPod 위임 분기 / 폴백 / 실패 매핑.

이 테스트는 NLF·S3·Firestore 없이 동작 (전부 monkeypatch). lambda_handler 가
SQS 이벤트에서 키 → 위임 또는 폴백을 정확히 디스패치하고, 실패를 contract
오류 코드로 매핑하는지만 검증.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

# functions/pipeline/ 디렉토리를 path 에 추가 — app 모듈 임포트.
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))


def _sqs_event(bucket: str, key: str) -> dict:
    """S3 → SQS 메시지 모양 (sunity_shared.events.iter_s3_keys_from_sqs 형식)."""
    body = {
        "Records": [
            {"s3": {"bucket": {"name": bucket}, "object": {"key": key}}}
        ]
    }
    return {"Records": [{"body": json.dumps(body)}]}


@pytest.fixture
def pipeline(monkeypatch):
    """app 모듈을 환경변수 클리어 + monkeypatch 상태로 재로드."""
    for k in ("RUNPOD_ANALYZE_URL", "RUNPOD_AUTH_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    # 어댑터 import 비용 회피 — boto3 만 가짜로
    sys.modules.pop("app", None)
    import app  # noqa: WPS433

    importlib.reload(app)

    calls = {"process": [], "delegate": [], "queued": [], "failed": [], "noHuman": 0}

    def fake_process(bucket, key, uid, analysis_id):
        calls["process"].append((bucket, key, uid, analysis_id))

    def fake_delegate(bucket, key):
        calls["delegate"].append((bucket, key))

    def fake_update_status(uid, analysis_id, status):
        if status == app.models.STATUS_QUEUED:
            calls["queued"].append((uid, analysis_id))

    def fake_fail(uid, analysis_id, code, message):
        calls["failed"].append((uid, analysis_id, code))

    monkeypatch.setattr(app, "_process", fake_process)
    monkeypatch.setattr(app, "_delegate_to_runpod", fake_delegate)
    monkeypatch.setattr(app.firestore_admin, "update_analysis_status", fake_update_status)
    monkeypatch.setattr(app.firestore_admin, "fail_analysis", fake_fail)

    app._test_calls = calls
    return app


def test_fallback_when_runpod_unset(pipeline):
    # 환경변수 없음 — _process 호출돼야 함.
    out = pipeline.lambda_handler(_sqs_event("b", "uploads/u1/a1.mp4"), None)

    assert out == {"processed": 1}
    assert pipeline._test_calls["process"] == [("b", "uploads/u1/a1.mp4", "u1", "a1")]
    assert pipeline._test_calls["delegate"] == []
    assert pipeline._test_calls["failed"] == []


def test_delegate_when_runpod_set(monkeypatch, pipeline):
    # 위임 모드 — 환경변수 셋 + 모듈 재로드.
    monkeypatch.setenv("RUNPOD_ANALYZE_URL", "https://pod.example/analyze")
    monkeypatch.setenv("RUNPOD_AUTH_TOKEN", "tok")
    importlib.reload(pipeline)

    calls = {"process": [], "delegate": [], "queued": [], "failed": []}
    monkeypatch.setattr(pipeline, "_process", lambda *a: calls["process"].append(a))
    monkeypatch.setattr(pipeline, "_delegate_to_runpod", lambda b, k: calls["delegate"].append((b, k)))
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "update_analysis_status",
        lambda uid, aid, status: calls["queued"].append((uid, aid, status)),
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "fail_analysis",
        lambda uid, aid, c, m: calls["failed"].append((uid, aid, c)),
    )

    out = pipeline.lambda_handler(_sqs_event("b", "uploads/u2/a2.mov"), None)

    assert out == {"processed": 1}
    assert calls["delegate"] == [("b", "uploads/u2/a2.mov")]
    assert calls["process"] == []
    # status=queued 가 위임 전에 한 번 갱신돼야 — UX(앱이 진행 상태 본다).
    assert (
        "u2",
        "a2",
        pipeline.models.STATUS_QUEUED,
    ) in calls["queued"]
    assert calls["failed"] == []


def test_delegate_failure_maps_to_server_error(monkeypatch, pipeline):
    monkeypatch.setenv("RUNPOD_ANALYZE_URL", "https://pod.example/analyze")
    monkeypatch.setenv("RUNPOD_AUTH_TOKEN", "tok")
    importlib.reload(pipeline)

    def fake_delegate_raises(bucket, key):
        raise RuntimeError("runpod 500")

    calls = {"failed": []}
    monkeypatch.setattr(pipeline, "_delegate_to_runpod", fake_delegate_raises)
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "update_analysis_status",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        pipeline.firestore_admin,
        "fail_analysis",
        lambda uid, aid, c, m: calls["failed"].append((uid, aid, c)),
    )

    out = pipeline.lambda_handler(_sqs_event("b", "uploads/u3/a3.mp4"), None)

    # 위임 실패해도 lambda_handler 자체는 정상 종료(메시지 1개 처리 = processed:0).
    # 실패 매핑은 ERR_SERVER_ERROR 로.
    assert out == {"processed": 0}
    assert calls["failed"] == [("u3", "a3", pipeline.models.ERR_SERVER_ERROR)]


def test_invalid_key_is_skipped(pipeline):
    out = pipeline.lambda_handler(_sqs_event("b", "results/u/a.mp4"), None)
    assert out == {"processed": 0}
    # 잘못된 키는 fail 도 안 함 — uid 를 모르므로 그냥 스킵.
    assert pipeline._test_calls["failed"] == []
    assert pipeline._test_calls["process"] == []
    assert pipeline._test_calls["delegate"] == []
