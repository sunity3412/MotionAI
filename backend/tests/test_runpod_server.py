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


# ── Phase 38 (38-08 Task 1) — POST /register-reference + 자기 재현성 실패 훅 배선 ──────────
#
# 리뷰 R3: 어느 입구(Lambda 위임 · requeue · 손 curl)든 같은 `claim_registration` 을 지난다 —
# `jobId` 가 오면 전달자가 이미 claim 한 것, 없으면 Pod 가 직접 claim(False → 409, 실행 0).
# `/analyze` 는 byte-무접촉(위 테스트 그대로 통과). Firestore · GPU 0 — FakeAdmin · FakeMod.

REG_UID = "u1"
REG_REF = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
REG_UPLOAD_KEY = f"reference/{REG_UID}/{REG_REF}/upload.mp4"


@pytest.fixture
def reg_mod(monkeypatch):
    monkeypatch.setenv("RUNPOD_AUTH_TOKEN", "test-token")
    if "runpod_inference.server" in sys.modules:
        del sys.modules["runpod_inference.server"]
    import runpod_inference.server as server  # noqa: WPS433

    importlib.reload(server)

    rec: dict = {"register": [], "process": [], "mark": [], "claim": [], "reg_failed": [], "fail": []}
    ctl: dict = {"claim_ok": True, "register_raises": None, "process_raises": None, "load_raises": None}

    class FakeMod:
        @staticmethod
        def _process(bucket, key, uid, analysis_id):
            rec["process"].append((bucket, key, uid, analysis_id))
            if ctl["process_raises"] is not None:
                raise ctl["process_raises"]

        @staticmethod
        def _register_reference(bucket, key, uid, ref_id, job_id):
            rec["register"].append((bucket, key, uid, ref_id, job_id))
            if ctl["register_raises"] is not None:
                raise ctl["register_raises"]

        @staticmethod
        def _mark_self_check_failed_if_needed(uid, analysis_id):
            rec["mark"].append((uid, analysis_id))

    class FakeAdmin:
        @staticmethod
        def claim_registration(ref_id, job_id):
            rec["claim"].append((ref_id, job_id))
            return ctl["claim_ok"]

        @staticmethod
        def set_registration_failed(ref_id, job_id, *, error):
            rec["reg_failed"].append((ref_id, job_id, error))
            return True

        @staticmethod
        def fail_analysis(uid, analysis_id, code, message):
            rec["fail"].append((uid, analysis_id, code))

    def fake_load():
        if ctl["load_raises"] is not None:
            raise ctl["load_raises"]
        return FakeMod

    monkeypatch.setattr(server, "_load_pipeline_module", fake_load)
    monkeypatch.setattr(server, "firestore_admin", FakeAdmin)
    server._rec = rec
    server._ctl = ctl
    return server


def _client(server):
    from fastapi.testclient import TestClient

    return TestClient(server.app)


def test_register_requires_token(reg_mod):
    resp = _client(reg_mod).post("/register-reference", json={"bucket": "b", "key": REG_UPLOAD_KEY})

    assert resp.status_code == 401
    assert reg_mod._rec["register"] == [] and reg_mod._rec["claim"] == []


@pytest.mark.parametrize(
    "key",
    [
        "uploads/u/a.mp4",  # 학생 키
        "reference/ref-kip-up.mp4",  # legacy 평면
        f"reference/{REG_UID}/{REG_REF}/v1.mp4",  # 확정 키 — upload 만 받는다
    ],
)
def test_register_rejects_non_upload_keys(reg_mod, key):
    resp = _client(reg_mod).post(
        "/register-reference",
        json={"bucket": "b", "key": key, "jobId": "A"},
        headers={"X-RunPod-Token": "test-token"},
    )

    assert resp.status_code == 400
    assert "invalid reference key" in resp.json()["detail"]
    assert reg_mod._rec["register"] == [] and reg_mod._rec["claim"] == []


def test_register_with_job_id_runs_without_claim(reg_mod):
    """전달자(Lambda · requeue)가 이미 claim 했다 — Pod 는 claim 을 다시 부르지 않는다."""
    resp = _client(reg_mod).post(
        "/register-reference",
        json={"bucket": "bk", "key": REG_UPLOAD_KEY, "jobId": "A"},
        headers={"X-RunPod-Token": "test-token"},
    )

    assert resp.status_code == 202
    assert resp.json() == {"status": "accepted", "uid": REG_UID, "refId": REG_REF, "jobId": "A"}
    assert reg_mod._rec["register"] == [("bk", REG_UPLOAD_KEY, REG_UID, REG_REF, "A")]
    assert reg_mod._rec["claim"] == []


def test_register_without_job_id_claims_itself(reg_mod):
    """손 curl 도 같은 claim 을 지난다(R3) — 새 32-hex job id 로 claim 성공 → 그 id 로 실행."""
    resp = _client(reg_mod).post(
        "/register-reference",
        json={"bucket": "bk", "key": REG_UPLOAD_KEY},
        headers={"X-RunPod-Token": "test-token"},
    )

    assert resp.status_code == 202
    (ref_id, job_id), = reg_mod._rec["claim"]
    assert ref_id == REG_REF
    assert len(job_id) == 32 and all(c in "0123456789abcdef" for c in job_id)
    assert resp.json()["jobId"] == job_id
    assert reg_mod._rec["register"] == [("bk", REG_UPLOAD_KEY, REG_UID, REG_REF, job_id)]


def test_register_without_job_id_claim_false_is_409(reg_mod):
    reg_mod._ctl["claim_ok"] = False

    resp = _client(reg_mod).post(
        "/register-reference",
        json={"bucket": "bk", "key": REG_UPLOAD_KEY},
        headers={"X-RunPod-Token": "test-token"},
    )

    assert resp.status_code == 409
    assert "registration not claimable" in resp.json()["detail"]
    assert len(reg_mod._rec["claim"]) == 1
    assert reg_mod._rec["register"] == []


def test_register_background_exception_records_server_error(reg_mod):
    reg_mod._ctl["register_raises"] = RuntimeError("등록 문서 없음")

    resp = _client(reg_mod).post(
        "/register-reference",
        json={"bucket": "bk", "key": REG_UPLOAD_KEY, "jobId": "A"},
        headers={"X-RunPod-Token": "test-token"},
    )

    assert resp.status_code == 202
    (ref_id, job_id, error), = reg_mod._rec["reg_failed"]
    assert (ref_id, job_id) == (REG_REF, "A")
    assert error["code"] == reg_mod.models.REG_ERR_SERVER_ERROR
    assert error["message"] == reg_mod.models.REGISTRATION_ERROR_MESSAGE[reg_mod.models.REG_ERR_SERVER_ERROR]


def test_register_background_success_writes_nothing_extra(reg_mod):
    _client(reg_mod).post(
        "/register-reference",
        json={"bucket": "bk", "key": REG_UPLOAD_KEY, "jobId": "A"},
        headers={"X-RunPod-Token": "test-token"},
    )
    assert reg_mod._rec["reg_failed"] == []


@pytest.mark.parametrize("exc_kind", ["no_human", "not_pole", "other"])
def test_process_in_background_failure_marks_self_check(reg_mod, exc_kind):
    exc = {
        "no_human": reg_mod.NoHumanError("x"),
        "not_pole": reg_mod.NotPoleMotionError("x"),
        "other": RuntimeError("x"),
    }[exc_kind]
    reg_mod._ctl["process_raises"] = exc

    reg_mod._process_in_background("b", "uploads/u1/a1.mp4", "u1", "a1")

    assert [f[:2] for f in reg_mod._rec["fail"]] == [("u1", "a1")]
    assert reg_mod._rec["mark"] == [("u1", "a1")]


def test_process_in_background_success_does_not_mark(reg_mod):
    reg_mod._process_in_background("b", "uploads/u1/a1.mp4", "u1", "a1")

    assert reg_mod._rec["fail"] == [] and reg_mod._rec["mark"] == []


def test_process_in_background_mark_survives_module_load_failure(reg_mod):
    """pipeline 모듈 로드 자체가 실패해도 fail_analysis 는 남고 예외는 새지 않는다."""
    reg_mod._ctl["load_raises"] = RuntimeError("import failed")

    reg_mod._process_in_background("b", "uploads/u1/a1.mp4", "u1", "a1")

    assert [f[:2] for f in reg_mod._rec["fail"]] == [("u1", "a1")]
    assert reg_mod._rec["mark"] == []
