"""requeue_reference_registrations — Pod 기동 뒤 대기 등록 재개 스크립트 (Phase 38-08 Task 2, D-20 · 리뷰 R3 · R4).

잠그는 것:
  · `--dry-run` 은 표만 — claim 0 · POST 0 · writer 0.
  · 재개는 건마다 `claim_registration` 을 지난 뒤에만 Pod `/register-reference {bucket,key,jobId}` POST(R3) —
    같은 대기 목록으로 두 번 돌려도 POST 는 1회(`test_requeue_twice_posts_once`).
  · 200/202 외 응답은 그 건만 실패로 세고 다음 건 진행, 실패가 있으면 종료 코드 1.
  · legacy 평면 · 확정 v1 · 빈 uploadKey 는 스킵(경고) — 등록 서비스를 못 부른다.
  · `--reclaim-stale` 은 lease 만료 processing 만, `--sweep-expired` 는 presign 만료 registering 만(R4) —
    객체 있으면 claim+POST, 없으면 `set_registration_expired`, 미만료는 무접촉.

Firestore · S3 · Pod 0 — firestore_admin 함수 3개 · boto3.client · urllib.request.urlopen 을 monkeypatch.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest
from botocore.exceptions import ClientError

import requeue_reference_registrations as rq

NOW = 1_800_000_000_000
URL = "https://x/register-reference"
ARGS = ["--register-url", URL, "--token", "t-secret", "--bucket", "b"]


def _ref(i: int) -> str:
    return f"{i:032x}"


def _doc(i: int, status: str, **over) -> dict:
    ref = _ref(i)
    d = {
        "motionId": ref,
        "supplierUid": "u1",
        "registrationStatus": status,
        "uploadKey": f"reference/u1/{ref}/upload.mp4",
        "registrationUpdatedAt": NOW - 60_000,
        "uploadExpiresAt": NOW - 1,
        "leaseUntil": None,
    }
    d.update(over)
    return d


class _Resp:
    def __init__(self, status: int):
        self.status = status

    def read(self, *_a):
        return b"{}"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def h(monkeypatch):
    """가짜 Firestore(상태 기계 = claim_registration 규칙) + 가짜 S3 head + 가짜 Pod."""
    state: dict = {
        "docs": {},  # ref_id -> doc (claim 이 status 를 바꾼다)
        "snapshot": None,  # 목록 조회가 돌려줄 고정 목록(동시 실행 재현) — None 이면 현재 상태로
        "objects": set(),  # head_object 200 인 키
        "head_error": None,  # head_object 가 낼 비-404 ClientError 코드
        "http_status": {},  # ref_id -> 응답 코드(기본 202)
    }
    calls: dict = {"list": [], "claim": [], "expired": [], "head": [], "post": []}

    def fake_list(status):
        calls["list"].append(status)
        src = state["snapshot"] if state["snapshot"] is not None else list(state["docs"].values())
        return [dict(d) for d in src if d["registrationStatus"] == status]

    def fake_claim(ref_id, job_id, *, now_ms=None, **_kw):
        calls["claim"].append((ref_id, job_id, now_ms))
        d = state["docs"].get(ref_id)
        if d is None:
            return False
        st = d["registrationStatus"]
        if st == "processing":
            if now_ms < int(d.get("leaseUntil") or 0):
                return False
        elif st not in ("registering", "queued"):
            return False
        d.update(registrationStatus="processing", jobId=job_id, leaseUntil=now_ms + 900_000)
        return True

    def fake_expired(ref_id):
        calls["expired"].append(ref_id)
        d = state["docs"].get(ref_id)
        if d is None or d["registrationStatus"] != "registering":
            return False
        d["registrationStatus"] = "expired"
        return True

    class _S3:
        def head_object(self, *, Bucket, Key):
            calls["head"].append((Bucket, Key))
            if state["head_error"]:
                raise ClientError({"Error": {"Code": state["head_error"]}}, "HeadObject")
            if Key not in state["objects"]:
                raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
            return {"ContentLength": 1}

    def fake_client(name, *a, **kw):
        assert name == "s3", name
        return _S3()

    def fake_urlopen(req, timeout=None):
        body = json.loads(req.data.decode("utf-8"))
        headers = {k.lower(): v for k, v in req.header_items()}
        calls["post"].append({"url": req.full_url, "method": req.get_method(), "body": body, "headers": headers})
        ref_id = body["key"].split("/")[2]
        code = state["http_status"].get(ref_id, 202)
        if code >= 400:
            raise urllib.error.HTTPError(req.full_url, code, "err", {}, None)
        return _Resp(code)

    monkeypatch.setattr(rq.firestore_admin, "list_reference_registrations_by_status", fake_list)
    monkeypatch.setattr(rq.firestore_admin, "claim_registration", fake_claim)
    monkeypatch.setattr(rq.firestore_admin, "set_registration_expired", fake_expired)
    monkeypatch.setattr(rq.boto3, "client", fake_client)
    monkeypatch.setattr(rq.urllib.request, "urlopen", fake_urlopen)

    class H:
        pass

    x = H()
    x.state, x.calls = state, calls

    def add(*docs):
        for d in docs:
            state["docs"][d["motionId"]] = d

    x.add = add
    return x


def test_dry_run_touches_nothing(h, capsys):
    h.add(_doc(1, "queued"), _doc(2, "queued"))

    rc = rq.main(ARGS + ["--dry-run"], now_ms=NOW)

    assert rc == 0
    assert h.calls["claim"] == [] and h.calls["post"] == [] and h.calls["expired"] == []
    out = capsys.readouterr().out
    assert _ref(1) in out and _ref(2) in out
    assert "t-secret" not in out


def test_claim_then_post_with_four_headers_and_job_id(h, capsys):
    h.add(_doc(1, "queued"))

    rc = rq.main(ARGS, now_ms=NOW)

    assert rc == 0
    (ref_id, job_id, now_ms), = h.calls["claim"]
    assert ref_id == _ref(1) and now_ms == NOW
    assert len(job_id) == 32 and all(c in "0123456789abcdef" for c in job_id)
    (post,) = h.calls["post"]
    assert post["url"] == URL and post["method"] == "POST"
    assert post["body"] == {"bucket": "b", "key": f"reference/u1/{_ref(1)}/upload.mp4", "jobId": job_id}
    assert post["headers"] == {
        "content-type": "application/json",
        "accept": "application/json",
        "user-agent": "sunity-motion-pilot/1.0 (+requeue)",
        "x-runpod-token": "t-secret",
    }
    out = capsys.readouterr().out
    assert "t-secret" not in out
    assert f"job={job_id}" in out


def test_requeue_twice_posts_once(h):
    """R3 — 같은 대기 목록(동시 실행 두 개가 같은 목록을 읽은 상황)으로 두 번 돌려도 실행은 1회."""
    h.add(_doc(1, "queued"))
    h.state["snapshot"] = [dict(d) for d in h.state["docs"].values()]

    assert rq.main(ARGS, now_ms=NOW) == 0
    assert rq.main(ARGS, now_ms=NOW + 1000) == 0

    assert len(h.calls["claim"]) == 2
    assert len(h.calls["post"]) == 1


def test_non_202_counts_failure_and_continues(h):
    h.add(_doc(1, "queued"), _doc(2, "queued"))
    h.state["http_status"][_ref(1)] = 500

    rc = rq.main(ARGS, now_ms=NOW)

    assert rc == 1
    assert [p["body"]["key"].split("/")[2] for p in h.calls["post"]] == [_ref(1), _ref(2)]


def test_http_200_is_success(h):
    h.add(_doc(1, "queued"))
    h.state["http_status"][_ref(1)] = 200

    assert rq.main(ARGS, now_ms=NOW) == 0


def test_network_error_counts_failure(h, monkeypatch):
    h.add(_doc(1, "queued"))

    def boom(req, timeout=None):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(rq.urllib.request, "urlopen", boom)

    assert rq.main(ARGS, now_ms=NOW) == 1


@pytest.mark.parametrize(
    "key",
    [
        "reference/ref-kip-up.mp4",  # legacy 평면
        f"reference/u1/{_ref(1)}/v1.mp4",  # 확정 키
        "",
        None,
        f"reference/u1/{_ref(9)}/upload.mp4",  # 다른 refId 의 키 — doc 과 어긋남
    ],
)
def test_bad_upload_key_is_skipped(h, key):
    h.add(_doc(1, "queued", uploadKey=key))

    rc = rq.main(ARGS, now_ms=NOW)

    assert rc == 0
    assert h.calls["claim"] == [] and h.calls["post"] == []


def test_queued_only_by_default(h):
    """플래그 없으면 queued 쿼리 하나 — processing · registering 은 읽지도 않는다(Spark 읽기 캡)."""
    h.add(_doc(1, "processing", leaseUntil=NOW - 1), _doc(2, "registering"))

    assert rq.main(ARGS, now_ms=NOW) == 0

    assert h.calls["list"] == ["queued"]
    assert h.calls["claim"] == [] and h.calls["post"] == [] and h.calls["head"] == []


def test_reclaim_stale_only_expired_lease(h):
    h.add(
        _doc(1, "processing", leaseUntil=NOW + 60_000, jobId="old1"),  # 살아 있음
        _doc(2, "processing", leaseUntil=NOW - 1, jobId="old2"),  # 만료
    )

    rc = rq.main(ARGS + ["--reclaim-stale"], now_ms=NOW)

    assert rc == 0
    assert [c[0] for c in h.calls["claim"]] == [_ref(2)]
    assert len(h.calls["post"]) == 1
    assert h.calls["post"][0]["body"]["key"] == f"reference/u1/{_ref(2)}/upload.mp4"


def test_sweep_expired_without_object_marks_expired(h):
    h.add(_doc(1, "registering", uploadExpiresAt=NOW - 1))

    rc = rq.main(ARGS + ["--sweep-expired"], now_ms=NOW)

    assert rc == 0
    assert h.calls["head"] == [("b", f"reference/u1/{_ref(1)}/upload.mp4")]
    assert h.calls["expired"] == [_ref(1)]
    assert h.calls["claim"] == [] and h.calls["post"] == []


def test_sweep_expired_with_object_claims_and_posts(h):
    """이벤트 유실 뒤 객체는 있다 — claim 을 지나 등록을 재개한다(R4)."""
    d = _doc(1, "registering", uploadExpiresAt=NOW - 1)
    h.add(d)
    h.state["objects"].add(d["uploadKey"])

    rc = rq.main(ARGS + ["--sweep-expired"], now_ms=NOW)

    assert rc == 0
    assert [c[0] for c in h.calls["claim"]] == [_ref(1)]
    assert len(h.calls["post"]) == 1
    assert h.calls["expired"] == []


def test_sweep_leaves_unexpired_registering_alone(h):
    h.add(_doc(1, "registering", uploadExpiresAt=NOW + 1))

    rc = rq.main(ARGS + ["--sweep-expired"], now_ms=NOW)

    assert rc == 0
    assert h.calls["head"] == [] and h.calls["claim"] == [] and h.calls["expired"] == []


def test_sweep_head_other_error_is_failure(h):
    h.add(_doc(1, "registering", uploadExpiresAt=NOW - 1))
    h.state["head_error"] = "AccessDenied"

    rc = rq.main(ARGS + ["--sweep-expired"], now_ms=NOW)

    assert rc == 1
    assert h.calls["expired"] == [] and h.calls["claim"] == []


def test_dry_run_with_all_flags_touches_nothing(h):
    h.add(
        _doc(1, "queued"),
        _doc(2, "processing", leaseUntil=NOW - 1),
        _doc(3, "registering", uploadExpiresAt=NOW - 1),
    )

    assert rq.main(ARGS + ["--dry-run", "--reclaim-stale", "--sweep-expired"], now_ms=NOW) == 0

    assert sorted(h.calls["list"]) == ["processing", "queued", "registering"]
    for k in ("claim", "post", "expired", "head"):
        assert h.calls[k] == [], k


def test_register_url_from_analyze_url():
    assert rq.register_url_from_analyze("https://p-8000.proxy.runpod.net/analyze") == (
        "https://p-8000.proxy.runpod.net/register-reference"
    )
    assert rq.register_url_from_analyze("https://p/") == "https://p/register-reference"


def test_help_mentions_flags(capsys):
    with pytest.raises(SystemExit) as e:
        rq.main(["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    for flag in ("--dry-run", "--register-url", "--reclaim-stale", "--sweep-expired"):
        assert flag in out
