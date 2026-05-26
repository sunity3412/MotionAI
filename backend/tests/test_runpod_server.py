"""RunPod 분석 서버 — 인증/디스패치 분기 단위 테스트.

GPU·NLF·S3·Firestore 없이 동작해야 하므로 background task 로 넘기는 _process 는
가짜로 모킹한다. 실제 분석은 통합 테스트 영역.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

# runpod_inference 패키지 임포트를 위해 backend 디렉토리를 path 에 추가.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@pytest.fixture
def server_mod(monkeypatch):
    """RUNPOD_AUTH_TOKEN 을 셋하고 모듈을 재로드. _load_pipeline_module 은 모킹.

    server 임포트 시점에 sunity_shared.firestore_admin 이 import 되는데
    firebase_admin 도 함께 들어옴. 진짜 SDK 호출은 일어나지 않으므로 OK.
    """
    monkeypatch.setenv("RUNPOD_AUTH_TOKEN", "test-token")
    if "runpod_inference.server" in sys.modules:
        del sys.modules["runpod_inference.server"]
    import runpod_inference.server as server  # noqa: WPS433

    importlib.reload(server)

    calls: list[tuple[str, str, str, str]] = []

    def fake_load_pipeline():
        class FakeMod:
            @staticmethod
            def _process(bucket, key, uid, analysis_id):
                calls.append((bucket, key, uid, analysis_id))

        return FakeMod()

    monkeypatch.setattr(server, "_load_pipeline_module", fake_load_pipeline)
    server._calls = calls  # 테스트에서 접근하기 위해 부착
    return server


def test_health_ok(server_mod):
    from fastapi.testclient import TestClient

    client = TestClient(server_mod.app)
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["auth_configured"] is True


def test_analyze_requires_token(server_mod):
    from fastapi.testclient import TestClient

    client = TestClient(server_mod.app)
    resp = client.post(
        "/analyze",
        json={"bucket": "b", "key": "uploads/u1/a1.mp4"},
    )

    assert resp.status_code == 401


def test_analyze_invalid_key(server_mod):
    from fastapi.testclient import TestClient

    client = TestClient(server_mod.app)
    resp = client.post(
        "/analyze",
        json={"bucket": "b", "key": "results/u1/a1.mp4"},   # uploads/ 가 아님
        headers={"X-RunPod-Token": "test-token"},
    )

    assert resp.status_code == 400
    assert "invalid key" in resp.json()["detail"]


def test_analyze_accepted_runs_process(server_mod):
    from fastapi.testclient import TestClient

    client = TestClient(server_mod.app)
    resp = client.post(
        "/analyze",
        json={
            "bucket": "sunity-motion-pilot-videos",
            "key": "uploads/uid42/analysis99.mp4",
        },
        headers={"X-RunPod-Token": "test-token"},
    )

    assert resp.status_code == 202
    body = resp.json()
    assert body == {
        "status": "accepted",
        "uid": "uid42",
        "analysisId": "analysis99",
    }
    # TestClient 는 background task 도 동기 실행해줘서 _process 가 1회 호출됨.
    assert server_mod._calls == [
        ("sunity-motion-pilot-videos", "uploads/uid42/analysis99.mp4", "uid42", "analysis99")
    ]


def test_auth_token_unset_returns_503(monkeypatch):
    """토큰 미설정 시 외부 공개 위험 — 503 으로 잠근다."""
    monkeypatch.delenv("RUNPOD_AUTH_TOKEN", raising=False)
    if "runpod_inference.server" in sys.modules:
        del sys.modules["runpod_inference.server"]
    import runpod_inference.server as server  # noqa: WPS433

    from fastapi.testclient import TestClient

    client = TestClient(server.app)
    resp = client.post(
        "/analyze",
        json={"bucket": "b", "key": "uploads/u/a.mp4"},
        headers={"X-RunPod-Token": "anything"},
    )

    assert resp.status_code == 503
