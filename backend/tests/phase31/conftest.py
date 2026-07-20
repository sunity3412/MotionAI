"""Phase 31 시각 교정물 테스트 공용 스캐폴드 — 실 Firestore/네트워크/Pod 미접촉 (LOCAL ONLY).

backend/tests/conftest.py 가 이미 shared/python 을 주입하지만, phase31 은 backend
루트(functions/*)와 scripts 를 직접 import 하는 후속 플랜(31-09/31-10)이 있어 여기서
함께 보장한다 (phase22/conftest.py 선례).

제공물 3종:
  1. `fake_firestore` — firestore_admin 의 4개 seam(_doc/_collection/_run_in_transaction/
     _field_filter/_query_start_after_name)을 patch 하는 in-memory Firestore 모사.
     optimistic concurrency(문서 version) 를 실제로 검사하므로 CAS/경쟁 계약을
     "테스트가 통과하도록 짠 mock" 이 아니라 진짜 재현으로 검증한다.
       - `run_contended(fn_a, fn_b)`: 둘 다 commit 전 상태를 read → A 먼저 commit →
         B 는 read version 불일치로 conflict → 자동 재시도(=A commit 결과 재read).
       - `commit_lost=True`: transaction 은 성공 commit 하되 호출측에 예외 — "commit
         응답 유실" 모사 (재호출이 stale no-op 인지 검증용).
       - read-after-write 순서 기록: Firestore transaction 의 read-all-before-write
         규율 위반을 테스트가 잡을 수 있다.
  2. `fake_clock` — 주입 가능한 UTC epoch ms 시계. claim lease 만료 전/후를 결정론으로
     재현 (5차 B5-01). 모든 만료 비교는 caller 가 넘긴 now_ms 하나만 쓴다는 계약
     (10차 H10-03) 이라 테스트도 이 시계 하나만 움직인다.
  3. `dashscope_urlopen_mock` — urllib.request.urlopen monkeypatch 팩토리.
     create/폴링/모더레이션 차단/redirect/oversized body 를 주입 가능
     (.planning/spikes/004-gemini-omni-view-editing/wan_gate_batch.py 의 http_json 형상).
"""

from __future__ import annotations

import copy
import io
import json
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2]
_LAYER = _BACKEND / "shared" / "python"
_SCRIPTS = _BACKEND / "scripts"
for _p in (_BACKEND, _LAYER, _SCRIPTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


# ─────────────────────── 주입 시계 ───────────────────────


class FakeClock:
    """단일 trusted clock (UTC epoch ms). 10차 H10-03 — 만료 비교의 유일 출처."""

    def __init__(self, now_ms: int = 1_700_000_000_000) -> None:
        self.now_ms = int(now_ms)

    def advance(self, ms: int) -> int:
        self.now_ms += int(ms)
        return self.now_ms

    def __call__(self) -> int:
        return self.now_ms


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


# ─────────────────────── in-memory Firestore ───────────────────────


class TransactionConflict(Exception):
    """read 한 문서가 commit 전에 변경됨 — Firestore optimistic concurrency 모사."""


class CommitLost(Exception):
    """commit 은 성사됐으나 응답이 유실됨 (호출측은 실패로 관측)."""


class NotFound(Exception):
    """update() 대상 문서 부재 — 실 Firestore 의 NotFound 모사."""


def _apply_update(doc: dict, payload: dict) -> None:
    """`.update()` 의미 — 각 field path 의 값을 **교체**한다 (deep merge 아님).

    실 Firestore 에서 `update({"refs": {...}})` 는 refs 맵 전체를 갈아끼운다. 여기서
    deep merge 하면 "ref 를 제거하는 write" 가 조용히 no-op 이 되어, ownership fence 의
    핵심(자기 ref 소비 / release)이 테스트를 통과해 버린다. dotted key 는 해당 경로만
    교체하고 형제 필드는 보존한다.
    """
    for key, value in payload.items():
        parts = key.split(".")
        cur = doc
        for part in parts[:-1]:
            if not isinstance(cur.get(part), dict):
                cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value


def _deep_merge(base: dict, patch: dict) -> dict:
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


class _FakeSnapshot:
    def __init__(self, doc_id: str, data: dict | None) -> None:
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> dict:
        # deepcopy — datetime(expireAt, TTL policy 대상) 은 JSON 직렬화 불가.
        return copy.deepcopy(self._data) if self._data is not None else {}


class _FakeDocRef:
    def __init__(self, db: "FakeFirestore", path: str) -> None:
        self._db = db
        self.path = path
        self.id = path.rsplit("/", 1)[-1]

    def get(self, transaction=None):
        if transaction is not None:
            return transaction._record_read(self)
        return self._db._snapshot(self.path)

    def set(self, payload: dict, merge: bool = False) -> None:
        self._db._apply("set", self.path, payload, merge)

    def update(self, payload: dict) -> None:
        self._db._apply("update", self.path, payload, None)

    def delete(self) -> None:
        self._db._apply("delete", self.path, None, None)


class _FakeQuery:
    """`where(filter=...).order_by('__name__').start_after(...).limit(n).stream()`.

    단일 등가 필터만 지원한다 — 등가+range 복합(=Firestore composite index 필수)을
    코드가 쓰면 여기서 바로 실패하므로, 인덱스 회피 계약이 테스트로 강제된다
    (STATE.md phase-33 3f6681f 선례).
    """

    def __init__(self, db, collection, filters=(), ordered=False, start_after_id=None, lim=None):
        self._db = db
        self._collection = collection
        self._filters = tuple(filters)
        self._ordered = ordered
        self._start_after_id = start_after_id
        self._limit = lim

    def _clone(self, **kw):
        base = {
            "filters": self._filters,
            "ordered": self._ordered,
            "start_after_id": self._start_after_id,
            "lim": self._limit,
        }
        base.update(kw)
        return _FakeQuery(self._db, self._collection, **base)

    def where(self, filter=None, **_ignored):  # noqa: A002 - 실 API 시그니처 미러
        if filter is None:
            raise TypeError("positional where 는 deprecated — filter= 만 허용")
        field, op, value = filter
        if op != "==":
            raise AssertionError(
                f"등가 아닌 연산자({op!r}) 사용 — composite index 필요 쿼리 금지 "
                "(H4-08/H5-06: durable cursor pagination 으로 회피할 것)"
            )
        self._db.query_log.append((self._collection, field, op, value))
        return self._clone(filters=self._filters + ((field, op, value),))

    def order_by(self, field: str):
        if field != "__name__":
            raise AssertionError("order_by 는 __name__ 만 허용 (index-free 계약)")
        return self._clone(ordered=True)

    def start_after(self, cursor):
        ref = cursor.get("__name__") if isinstance(cursor, dict) else cursor
        return self._clone(start_after_id=getattr(ref, "id", ref))

    def limit(self, n: int):
        return self._clone(lim=int(n))

    def stream(self):
        prefix = f"{self._collection}/"
        rows = [
            (path.rsplit("/", 1)[-1], data)
            for path, data in self._db.store.items()
            if path.startswith(prefix) and "/" not in path[len(prefix):]
        ]
        rows.sort(key=lambda r: r[0])
        out = []
        for doc_id, data in rows:
            if self._start_after_id is not None and doc_id <= self._start_after_id:
                continue
            if any(data.get(f) != v for f, _op, v in self._filters):
                continue
            out.append(_FakeSnapshot(doc_id, data))
            if self._limit is not None and len(out) >= self._limit:
                break
        return iter(out)


class _FakeCollection:
    def __init__(self, db, name: str) -> None:
        self._db = db
        self._name = name

    def where(self, filter=None, **kw):  # noqa: A002 - 실 API 시그니처 미러
        return _FakeQuery(self._db, self._name).where(filter=filter, **kw)

    def order_by(self, field: str):
        return _FakeQuery(self._db, self._name).order_by(field)


class _FakeTransaction:
    def __init__(self, db: "FakeFirestore") -> None:
        self._db = db
        self._reads: dict[str, int] = {}
        self._writes: list[tuple] = []
        self.read_after_write = False

    def _record_read(self, ref: _FakeDocRef):
        if self._writes:
            self.read_after_write = True
        self._reads[ref.path] = self._db.version.get(ref.path, 0)
        return self._db._snapshot(ref.path)

    def get(self, ref: _FakeDocRef):
        return self._record_read(ref)

    def set(self, ref: _FakeDocRef, payload: dict, merge: bool = False) -> None:
        self._writes.append(("set", ref.path, payload, merge))

    def update(self, ref: _FakeDocRef, payload: dict) -> None:
        self._writes.append(("update", ref.path, payload, None))

    def delete(self, ref: _FakeDocRef) -> None:
        self._writes.append(("delete", ref.path, None, None))

    def _commit(self) -> None:
        for path, version in self._reads.items():
            if self._db.version.get(path, 0) != version:
                raise TransactionConflict(path)
        for op, path, payload, merge in self._writes:
            self._db._apply(op, path, payload, merge)


class FakeFirestore:
    """firestore_admin 의 seam 을 대체하는 in-memory 저장소."""

    def __init__(self) -> None:
        self.store: dict[str, dict] = {}
        self.version: dict[str, int] = {}
        self.query_log: list[tuple] = []
        self.commit_count = 0
        self.conflict_count = 0
        self.read_after_write_seen = False
        self.missing_seams: tuple[str, ...] = ()

    # ── 내부 ──

    def _snapshot(self, path: str) -> _FakeSnapshot:
        return _FakeSnapshot(path.rsplit("/", 1)[-1], self.store.get(path))

    def _apply(self, op: str, path: str, payload, merge) -> None:
        if op == "delete":
            self.store.pop(path, None)
        elif op == "set":
            if merge and path in self.store:
                _deep_merge(self.store[path], copy.deepcopy(payload))
            else:
                self.store[path] = copy.deepcopy(payload)
        elif op == "update":
            if path not in self.store:
                raise NotFound(path)
            _apply_update(self.store[path], copy.deepcopy(payload))
        else:  # pragma: no cover - 방어
            raise AssertionError(f"unknown op {op}")
        self.version[path] = self.version.get(path, 0) + 1

    # ── firestore_admin seam ──

    def doc(self, path: str) -> _FakeDocRef:
        return _FakeDocRef(self, path)

    def collection(self, name: str) -> _FakeCollection:
        return _FakeCollection(self, name)

    def field_filter(self, field: str, op: str, value):
        return (field, op, value)

    def start_after_name(self, query, collection_name: str, doc_id: str):
        return query.start_after({"__name__": self.doc(f"{collection_name}/{doc_id}")})

    def run_in_transaction(self, fn, *, max_attempts: int = 5):
        for _ in range(max_attempts):
            tx = _FakeTransaction(self)
            result = fn(tx)
            try:
                tx._commit()
            except TransactionConflict:
                self.conflict_count += 1
                continue
            self.commit_count += 1
            self.read_after_write_seen |= tx.read_after_write
            if self._commit_lost:
                raise CommitLost("commit 응답 유실 (fake)")
            return result
        raise TransactionConflict("max attempts exceeded")

    # ── 테스트 제어 ──

    _commit_lost = False

    def commit_lost(self, enabled: bool = True) -> None:
        """다음 run_in_transaction 들이 commit 후 CommitLost 를 던지게 한다."""
        self._commit_lost = enabled

    def run_contended(self, fn_a, fn_b):
        """A/B 가 같은 pre-state 를 read → A commit → B conflict → B 자동 재시도.

        반환 (result_a, result_b). B 는 A 의 commit 결과 위에서 재실행된 결과다.
        """
        tx_a = _FakeTransaction(self)
        result_a = fn_a(tx_a)
        tx_b = _FakeTransaction(self)
        result_b = fn_b(tx_b)
        tx_a._commit()
        self.commit_count += 1
        try:
            tx_b._commit()
            self.commit_count += 1
        except TransactionConflict:
            self.conflict_count += 1
            result_b = self.run_in_transaction(fn_b)
        return result_a, result_b


@pytest.fixture
def fake_firestore(monkeypatch) -> FakeFirestore:
    """firestore_admin 의 Firestore seam 전체를 in-memory 로 교체.

    `_doc` 을 제외한 seam(_collection/_field_filter/_query_start_after_name/
    _run_in_transaction)은 31-02 Task 3 산출물이다. Task 1 시점에는 아직 없으므로
    raising=False 로 붙이되, **어떤 seam 이 없었는지를 `missing_seams` 로 노출**한다 —
    Task 3 테스트가 `missing_seams == ()` 를 단언해 오타 seam 이 영구히 조용히
    통과하는 것을 막는다.
    """
    from sunity_shared import firestore_admin

    db = FakeFirestore()
    seams = {
        "_doc": db.doc,
        "_collection": db.collection,
        "_field_filter": db.field_filter,
        "_query_start_after_name": db.start_after_name,
        "_run_in_transaction": db.run_in_transaction,
    }
    missing = tuple(n for n in seams if not hasattr(firestore_admin, n))
    for name, impl in seams.items():
        monkeypatch.setattr(firestore_admin, name, impl, raising=False)
    db.missing_seams = missing
    return db


# ─────────────────────── DashScope(Wan2.7) urllib mock ───────────────────────


class _FakeHTTPResponse(io.BytesIO):
    def __init__(self, body: bytes, status: int = 200, headers: dict | None = None):
        super().__init__(body)
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def getheader(self, name, default=None):
        return self.headers.get(name, default)


class DashScopeMock:
    """urlopen 대체. create → task_id, 폴링 → 상태 전이를 스크립트로 주입한다.

    실제 계약(wan_gate_batch.py http_json): POST create 는 X-DashScope-Async 헤더와
    함께 {"output": {"task_id": ...}} 를, GET /tasks/{id} 는
    {"output": {"task_status": ..., "video_url": ...}} 를 돌려준다.
    """

    def __init__(self) -> None:
        self.create_response: dict = {"output": {"task_id": "task-1"}}
        self.poll_responses: list[dict] = []
        self.requests: list[dict] = []
        self.status = 200
        self.body_override: bytes | None = None
        self.redirect_to: str | None = None
        self.oversized_bytes: int | None = None

    # ── 시나리오 헬퍼 ──

    def succeed(self, video_url: str = "https://vendor.example/out.mp4") -> "DashScopeMock":
        self.poll_responses = [
            {"output": {"task_status": "RUNNING"}},
            {"output": {"task_status": "SUCCEEDED", "video_url": video_url}},
        ]
        return self

    def moderation_blocked(self) -> "DashScopeMock":
        self.poll_responses = [
            {
                "output": {
                    "task_status": "FAILED",
                    "code": "DataInspectionFailed",
                    "message": "Input data may contain inappropriate content.",
                }
            }
        ]
        return self

    def vendor_failed(self, code: str = "InternalError") -> "DashScopeMock":
        self.poll_responses = [{"output": {"task_status": "FAILED", "code": code}}]
        return self

    def redirect(self, location: str) -> "DashScopeMock":
        self.redirect_to = location
        return self

    def oversized(self, n_bytes: int) -> "DashScopeMock":
        self.oversized_bytes = n_bytes
        return self

    # ── urlopen 대체 ──

    def __call__(self, req, timeout=None, **_kw):
        url = getattr(req, "full_url", req)
        method = getattr(req, "get_method", lambda: "GET")()
        self.requests.append({"url": url, "method": method, "timeout": timeout})
        if self.redirect_to is not None:
            return _FakeHTTPResponse(b"", status=302, headers={"Location": self.redirect_to})
        if self.oversized_bytes is not None:
            return _FakeHTTPResponse(b"x" * self.oversized_bytes, status=self.status)
        if self.body_override is not None:
            return _FakeHTTPResponse(self.body_override, status=self.status)
        if method == "POST":
            payload = self.create_response
        elif self.poll_responses:
            payload = self.poll_responses.pop(0) if len(self.poll_responses) > 1 else self.poll_responses[0]
        else:
            payload = {"output": {"task_status": "PENDING"}}
        return _FakeHTTPResponse(json.dumps(payload).encode(), status=self.status)


@pytest.fixture
def dashscope_urlopen_mock(monkeypatch) -> DashScopeMock:
    """urllib.request.urlopen 을 DashScopeMock 으로 교체 (실 네트워크 0)."""
    import urllib.request

    mock = DashScopeMock()
    monkeypatch.setattr(urllib.request, "urlopen", mock)
    return mock
