"""pipeline lambda_handler — `reference/` 접두사 분기 (Phase 38-07 Task 1, REQ-38-1 · D-20 · 리뷰 R3/R4/R5).

이 테스트는 S3 · Firestore · Pod 없이 동작한다(전부 monkeypatch). 잠그는 것:
  · `reference/{uid}/{refId}/upload.{ext}` 이벤트가 스킵되지 않고 Pod 유무에 따라 queued / delegated 로 갈린다.
  · 위임은 `claim_registration` 이 True 를 준 뒤 **정확히 한 번**(R3 — 같은 이벤트 2건이면 1회).
  · 상태 쓰기(queued / claim) 실패는 **전파**된다 — 메시지를 소비하지 않아 SQS 가 재전달한다(R4). 위임 뒤 실패는
    `set_registration_failed(server_error)` 로 남기고 정상 종료한다.
  · `v1.{ext}` 확정 복사 이벤트 · doc 없음 · `registering` 아님 · uid 불일치는 writer 호출 0 으로 스킵(R5).
  · `uploads/` 학생 경로는 byte-무접촉 — 같은 이벤트에 두 종류가 섞여도 각자 처리.
  · `_pod_available` 판정 순서: env 미설정 → SSM `runpod-pod-expected == down` → `/health`(12초, UA 헤더).

`test_pipeline_dispatch.py` 의 fixture 어법(모듈 캐시 리셋 + env monkeypatch)을 복제한다.
"""

from __future__ import annotations

import importlib
import json
import logging
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

# functions/pipeline/ 디렉토리를 path 에 추가 — app 모듈 임포트.
_PIPELINE = Path(__file__).resolve().parents[1] / "functions" / "pipeline"
if str(_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_PIPELINE))

UID = "u1"
REF_ID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"  # uuid4 hex 모양(영숫자 — legacy `ref-*` 가 아니다)
UPLOAD_KEY = f"reference/{UID}/{REF_ID}/upload.mp4"
V1_KEY = f"reference/{UID}/{REF_ID}/v1.mp4"
BUCKET = "b"
ANALYZE_URL = "https://pod.example/analyze"
_HEX32 = re.compile(r"^[0-9a-f]{32}$")


def _sqs_event(bucket: str, *keys: str) -> dict:
    """S3 → SQS 메시지 모양 — 레코드 여러 개면 한 메시지에 같이 싣는다(중복 이벤트 재현)."""
    body = {
        "Records": [
            {"s3": {"bucket": {"name": bucket}, "object": {"key": key}}} for key in keys
        ]
    }
    return {"Records": [{"body": json.dumps(body)}]}


@pytest.fixture
def app(monkeypatch):
    """RunPod 위임 모드(env 셋)로 app 모듈을 재로드한다."""
    monkeypatch.setenv("RUNPOD_ANALYZE_URL", ANALYZE_URL)
    monkeypatch.setenv("RUNPOD_AUTH_TOKEN", "tok")
    sys.modules.pop("app", None)
    import app as mod  # noqa: WPS433

    importlib.reload(mod)
    return mod


class _Harness:
    """writer · claim · pod · delegate 를 기록하고 예외를 주입할 수 있는 가짜 묶음."""

    def __init__(self) -> None:
        self.calls: dict[str, list] = {
            "get": [],
            "queued": [],
            "claim": [],
            "failed": [],
            "delegate": [],
            "pod": [],
            "status": [],
            "fail_analysis": [],
        }
        self.doc: dict | None = {
            "motionId": REF_ID,
            "registrationStatus": "registering",
            "supplierUid": UID,
            "uploadKey": UPLOAD_KEY,
        }
        self.pod: tuple[bool, str] = (True, "healthy")
        self.claim_results: list[bool] = [True]
        self.queued_exc: Exception | None = None
        self.claim_exc: Exception | None = None
        self.delegate_exc: Exception | None = None
        self.failed_exc: Exception | None = None


@pytest.fixture
def h(app, monkeypatch) -> _Harness:
    h = _Harness()

    def get_reg(ref_id):
        h.calls["get"].append(ref_id)
        return h.doc

    def queued(ref_id, *, queued_reason):
        h.calls["queued"].append((ref_id, queued_reason))
        if h.queued_exc is not None:
            raise h.queued_exc
        return True

    def claim(ref_id, job_id, **_kw):
        h.calls["claim"].append((ref_id, job_id))
        if h.claim_exc is not None:
            raise h.claim_exc
        # 첫 호출만 True 같은 시나리오 — 목록을 앞에서부터 소비, 마지막 값은 반복.
        return h.claim_results.pop(0) if len(h.claim_results) > 1 else h.claim_results[0]

    def failed(ref_id, job_id, *, error):
        h.calls["failed"].append((ref_id, job_id, error))
        if h.failed_exc is not None:
            raise h.failed_exc
        return True

    def delegate(bucket, key, *, url=None, extra=None):
        h.calls["delegate"].append((bucket, key, url, extra))
        if h.delegate_exc is not None:
            raise h.delegate_exc

    def pod():
        h.calls["pod"].append(1)
        return h.pod

    monkeypatch.setattr(app.firestore_admin, "get_reference_registration", get_reg)
    monkeypatch.setattr(app.firestore_admin, "set_registration_queued", queued)
    monkeypatch.setattr(app.firestore_admin, "claim_registration", claim)
    monkeypatch.setattr(app.firestore_admin, "set_registration_failed", failed)
    monkeypatch.setattr(app, "_pod_available", pod)
    monkeypatch.setattr(app, "_delegate_to_runpod", delegate)
    # uploads/ 학생 경로가 섞인 이벤트용 — Firestore 없이.
    monkeypatch.setattr(
        app.firestore_admin,
        "update_analysis_status",
        lambda uid, aid, status: h.calls["status"].append((uid, aid, status)),
    )
    monkeypatch.setattr(
        app.firestore_admin,
        "fail_analysis",
        lambda uid, aid, c, m: h.calls["fail_analysis"].append((uid, aid, c)),
    )
    return h


# ── D-20 / R4 — Pod 부재 = queued, 그 쓰기가 실패하면 재전달 ─────────────────────────────────


def test_pod_down_writes_queued_and_returns_normally(app, h):
    h.pod = (False, "pod_expected_down")
    out = app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY), None)
    assert out == {"processed": 0}
    assert h.calls["queued"] == [(REF_ID, "pod_down")]
    assert h.calls["claim"] == []
    assert h.calls["delegate"] == []
    assert h.calls["failed"] == []


def test_queued_write_failure_reraises(app, h):
    """R4 — 영속 queued 에 실패하면 메시지를 소비하지 않는다(SQS BatchSize 1 · maxReceiveCount 3 → DLQ)."""
    h.pod = (False, "health_failed")
    h.queued_exc = RuntimeError("firestore unavailable")
    with pytest.raises(RuntimeError, match="firestore unavailable"):
        app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY), None)
    assert h.calls["queued"] == [(REF_ID, "pod_down")]
    assert h.calls["delegate"] == []


# ── R3 — claim 뒤 위임 1회 ───────────────────────────────────────────────────────────────


def test_pod_healthy_claims_then_delegates_with_job_id(app, h):
    out = app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY), None)
    assert out == {"processed": 1}
    assert len(h.calls["claim"]) == 1
    ref_id, job_id = h.calls["claim"][0]
    assert ref_id == REF_ID
    assert _HEX32.match(job_id), job_id
    assert h.calls["delegate"] == [
        (BUCKET, UPLOAD_KEY, "https://pod.example/register-reference", {"jobId": job_id})
    ]
    assert h.calls["queued"] == []
    assert h.calls["failed"] == []


def test_duplicate_events_delegate_once(app, h, caplog):
    """같은 이벤트 2건 — claim 이 첫 호출만 True 라 위임은 정확히 1회(R3)."""
    caplog.set_level(logging.WARNING)
    h.claim_results = [True, False]
    out = app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY, UPLOAD_KEY), None)
    assert out == {"processed": 1}
    assert len(h.calls["claim"]) == 2
    assert len(h.calls["delegate"]) == 1
    assert h.calls["failed"] == []
    assert any("중복 이벤트 스킵" in r.getMessage() for r in caplog.records)


def test_claim_failure_reraises(app, h):
    """R4 — claim(상태 쓰기) 자체가 예외면 전파 — 재전달 대상."""
    h.claim_exc = RuntimeError("tx aborted")
    with pytest.raises(RuntimeError, match="tx aborted"):
        app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY), None)
    assert h.calls["delegate"] == []


def test_delegate_failure_marks_failed_server_error_and_returns(app, h):
    h.delegate_exc = RuntimeError("runpod 500")
    out = app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY), None)
    assert out == {"processed": 0}
    assert len(h.calls["failed"]) == 1
    ref_id, job_id, error = h.calls["failed"][0]
    assert ref_id == REF_ID
    assert job_id == h.calls["claim"][0][1]
    assert error == {
        "code": app.models.REG_ERR_SERVER_ERROR,
        "message": app.models.REGISTRATION_ERROR_MESSAGE[app.models.REG_ERR_SERVER_ERROR],
    }


def test_delegate_failure_then_writer_failure_is_logged_only(app, h, caplog):
    """위임 실패 뒤 failed writer 마저 죽으면 로그만 — lease 만료 뒤 requeue `--reclaim-stale` 가 줍는다."""
    caplog.set_level(logging.ERROR)
    h.delegate_exc = RuntimeError("runpod 500")
    h.failed_exc = RuntimeError("firestore down")
    out = app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY), None)
    assert out == {"processed": 0}
    assert len(h.calls["failed"]) == 1
    assert any(r.levelno >= logging.ERROR for r in caplog.records)


# ── R5 — 확정 키 이벤트 · 활성화 뒤 재PUT · 손 업로드 방어 ────────────────────────────────


def test_v1_event_skipped(app, h, caplog):
    caplog.set_level(logging.INFO)
    out = app.lambda_handler(_sqs_event(BUCKET, V1_KEY), None)
    assert out == {"processed": 0}
    assert h.calls["get"] == []
    assert h.calls["pod"] == []
    assert h.calls["queued"] == [] and h.calls["claim"] == [] and h.calls["delegate"] == []
    assert any("확정 키 이벤트 무시" in r.getMessage() for r in caplog.records)


def test_missing_doc_skipped(app, h):
    h.doc = None
    out = app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY), None)
    assert out == {"processed": 0}
    assert h.calls["get"] == [REF_ID]
    assert h.calls["pod"] == []
    assert h.calls["queued"] == [] and h.calls["claim"] == [] and h.calls["delegate"] == []


@pytest.mark.parametrize("status", ["active", "queued", "processing", "failed", "expired"])
def test_non_registering_status_skipped(app, h, status, caplog):
    """활성화 뒤 같은 URL 로 두 번째 PUT 이 와도 여기서 끝난다(R5)."""
    caplog.set_level(logging.WARNING)
    h.doc = dict(h.doc, registrationStatus=status)
    out = app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY), None)
    assert out == {"processed": 0}
    assert h.calls["pod"] == []
    assert h.calls["queued"] == [] and h.calls["claim"] == [] and h.calls["delegate"] == []
    assert any("등록 대기 doc 아님" in r.getMessage() for r in caplog.records)


def test_supplier_uid_mismatch_skipped(app, h):
    h.doc = dict(h.doc, supplierUid="u9")
    out = app.lambda_handler(_sqs_event(BUCKET, UPLOAD_KEY), None)
    assert out == {"processed": 0}
    assert h.calls["pod"] == []
    assert h.calls["queued"] == [] and h.calls["claim"] == [] and h.calls["delegate"] == []


def test_handle_reference_upload_return_values(app, h):
    """반환 계약 'skipped' | 'queued' | 'delegated' | 'failed' — 라우트/테스트가 이 문자열을 본다."""
    from sunity_shared.s3keys import parse_reference_key

    ref = parse_reference_key(UPLOAD_KEY)
    assert app._handle_reference_upload(BUCKET, V1_KEY, parse_reference_key(V1_KEY)) == "skipped"
    h.doc = None
    assert app._handle_reference_upload(BUCKET, UPLOAD_KEY, ref) == "skipped"
    h.doc = {"registrationStatus": "registering", "supplierUid": UID}
    h.pod = (False, "pod_expected_down")
    assert app._handle_reference_upload(BUCKET, UPLOAD_KEY, ref) == "queued"
    h.pod = (True, "healthy")
    assert app._handle_reference_upload(BUCKET, UPLOAD_KEY, ref) == "delegated"
    h.delegate_exc = RuntimeError("boom")
    assert app._handle_reference_upload(BUCKET, UPLOAD_KEY, ref) == "failed"
    h.delegate_exc = None
    h.claim_results = [False]
    assert app._handle_reference_upload(BUCKET, UPLOAD_KEY, ref) == "skipped"


# ── Success ④ — uploads/ 학생 경로 무접촉 ─────────────────────────────────────────────────


def test_uploads_and_reference_records_in_one_event_are_each_handled(app, h):
    out = app.lambda_handler(_sqs_event(BUCKET, "uploads/u3/a3.mp4", UPLOAD_KEY), None)
    assert out == {"processed": 2}
    # 학생 경로: queued 갱신 + 종전 시그니처 그대로 위임(url/extra 없음).
    assert ("u3", "a3", app.models.STATUS_QUEUED) in h.calls["status"]
    assert (BUCKET, "uploads/u3/a3.mp4", None, None) in h.calls["delegate"]
    # 등록 경로: claim 뒤 register-reference 로.
    reg = [c for c in h.calls["delegate"] if c[1] == UPLOAD_KEY]
    assert len(reg) == 1 and reg[0][2] == "https://pod.example/register-reference"
    assert h.calls["fail_analysis"] == []


def test_legacy_flat_reference_key_is_still_unrecognised(app, h):
    """기존 11개 평면 `reference/ref-*.mp4` 는 등록 경로에 들어오지 않는다(D-19)."""
    out = app.lambda_handler(_sqs_event(BUCKET, "reference/ref-kip-up.mp4"), None)
    assert out == {"processed": 0}
    assert h.calls["get"] == [] and h.calls["delegate"] == []


# ── _pod_available · URL 파생 · _delegate_to_runpod(url=, extra=) ──────────────────────────


class _Resp:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self, _n: int = -1) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _capture_urlopen(monkeypatch, responder):
    seen: list[tuple] = []

    def fake_urlopen(req, timeout=None):
        seen.append((req, timeout))
        return responder(req)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return seen


def test_pod_available_runpod_env_unset(app, monkeypatch):
    monkeypatch.setattr(app, "_RUNPOD_URL", "")
    monkeypatch.setattr(app, "_ssm_get_parameter", lambda name: pytest.fail("SSM 조회하면 안 된다"))
    assert app._pod_available() == (False, "runpod_env_unset")


def test_pod_available_ssm_down_short_circuits(app, monkeypatch):
    names: list[str] = []

    def ssm(name):
        names.append(name)
        return "down"

    monkeypatch.setattr(app, "_ssm_get_parameter", ssm)
    seen = _capture_urlopen(monkeypatch, lambda req: pytest.fail("health 를 부르면 안 된다"))
    assert app._pod_available() == (False, "pod_expected_down")
    assert names == ["/sunity/motion/runpod-pod-expected"]
    assert seen == []


def test_pod_available_ssm_error_falls_through_to_health(app, monkeypatch):
    monkeypatch.setattr(app, "_ssm_get_parameter", lambda name: None)
    seen = _capture_urlopen(
        monkeypatch, lambda req: _Resp(200, json.dumps({"status": "ok", "pipeline_loaded": True}).encode())
    )
    assert app._pod_available() == (True, "healthy")
    assert len(seen) == 1
    req, timeout = seen[0]
    assert req.full_url == "https://pod.example/health"
    assert timeout == 12
    headers = {k.lower(): v for k, v in req.header_items()}
    assert headers.get("user-agent") == "sunity-motion-pilot/1.0 (+aws-lambda)"


@pytest.mark.parametrize(
    "body",
    [
        json.dumps({"status": "ok", "pipeline_loaded": False}).encode(),
        json.dumps({"status": "starting", "pipeline_loaded": True}).encode(),
        b"<html>not json</html>",
    ],
)
def test_pod_available_health_not_loaded_is_failed(app, monkeypatch, body):
    monkeypatch.setattr(app, "_ssm_get_parameter", lambda name: "up")
    _capture_urlopen(monkeypatch, lambda req: _Resp(200, body))
    assert app._pod_available() == (False, "health_failed")


@pytest.mark.parametrize(
    "exc",
    [urllib.error.URLError("connection refused"), TimeoutError("timed out")],
)
def test_pod_available_health_error_is_failed(app, monkeypatch, exc):
    monkeypatch.setattr(app, "_ssm_get_parameter", lambda name: None)

    def raiser(_req):
        raise exc

    _capture_urlopen(monkeypatch, raiser)
    assert app._pod_available() == (False, "health_failed")


def test_pod_available_health_http_error_is_failed(app, monkeypatch):
    monkeypatch.setattr(app, "_ssm_get_parameter", lambda name: None)

    def raiser(req):
        raise urllib.error.HTTPError(req.full_url, 502, "bad gateway", {}, None)

    _capture_urlopen(monkeypatch, raiser)
    assert app._pod_available() == (False, "health_failed")


def test_ssm_get_parameter_returns_none_on_error_without_logging_value(app, monkeypatch, caplog):
    caplog.set_level(logging.WARNING)

    class _Ssm:
        def get_parameter(self, **kw):
            raise RuntimeError("ParameterNotFound secret-value-xyz")

    monkeypatch.setattr(app.boto3, "client", lambda name, **kw: _Ssm())
    assert app._ssm_get_parameter("/sunity/motion/runpod-pod-expected") is None
    assert any("/sunity/motion/runpod-pod-expected" in r.getMessage() for r in caplog.records)
    assert not any("secret-value-xyz" in r.getMessage() for r in caplog.records)


def test_ssm_get_parameter_returns_value(app, monkeypatch):
    class _Ssm:
        def get_parameter(self, **kw):
            assert kw["Name"] == "/sunity/motion/runpod-pod-expected"
            return {"Parameter": {"Value": " up \n"}}

    monkeypatch.setattr(app.boto3, "client", lambda name, **kw: _Ssm())
    assert app._ssm_get_parameter("/sunity/motion/runpod-pod-expected") == "up"


@pytest.mark.parametrize(
    "base, register, health",
    [
        ("https://x/analyze", "https://x/register-reference", "https://x/health"),
        ("https://x", "https://x/register-reference", "https://x/health"),
        ("https://x/", "https://x/register-reference", "https://x/health"),
        ("https://p-8000.proxy.runpod.net/analyze", "https://p-8000.proxy.runpod.net/register-reference",
         "https://p-8000.proxy.runpod.net/health"),
    ],
)
def test_register_and_health_url_derivation(app, monkeypatch, base, register, health):
    monkeypatch.setattr(app, "_RUNPOD_URL", base)
    assert app._register_url() == register
    assert app._health_url() == health


def test_delegate_to_runpod_url_and_extra(app, monkeypatch):
    """실제 `_delegate_to_runpod` — url 인자와 extra 가 payload 에 실리고 기본 호출은 종전 그대로."""
    seen = _capture_urlopen(monkeypatch, lambda req: _Resp(202, b""))
    app._delegate_to_runpod(BUCKET, UPLOAD_KEY, url="https://pod.example/register-reference", extra={"jobId": "j" * 32})
    app._delegate_to_runpod(BUCKET, "uploads/u1/a1.mp4")
    assert len(seen) == 2
    reg_req, reg_timeout = seen[0]
    assert reg_req.full_url == "https://pod.example/register-reference"
    assert reg_req.get_method() == "POST"
    assert json.loads(reg_req.data.decode()) == {"bucket": BUCKET, "key": UPLOAD_KEY, "jobId": "j" * 32}
    assert reg_timeout == app._RUNPOD_TIMEOUT_S
    headers = {k.lower(): v for k, v in reg_req.header_items()}
    assert headers.get("x-runpod-token") == "tok"
    std_req, _ = seen[1]
    assert std_req.full_url == ANALYZE_URL
    assert json.loads(std_req.data.decode()) == {"bucket": BUCKET, "key": "uploads/u1/a1.mp4"}


def test_delegate_to_runpod_non_2xx_raises(app, monkeypatch):
    _capture_urlopen(monkeypatch, lambda req: _Resp(500, b"boom"))
    with pytest.raises(RuntimeError, match="runpod 500"):
        app._delegate_to_runpod(BUCKET, UPLOAD_KEY, url="https://pod.example/register-reference", extra={"jobId": "x"})
