#!/usr/bin/env python3
"""quick-260930-o0u Task 5 — 라이브 Firestore 규칙 probe (instructorLinks · supplierCodes · suppliers).

38-09 rulesprobe38 방식: Admin SA custom token → signInWithCustomToken(ID 토큰은 출력하지 않는다)
→ Firestore REST v1 로 클라이언트 요청. 임시 doc 은 Admin 으로 만들고 finally 에서 지운다.
판정: ALLOW = HTTP 200, DENY = HTTP 403(PERMISSION_DENIED). 기대와 다른 행이 있으면 exit 1.

실행: backend/.venv/bin/python .planning/quick/260930-o0u-student-instructor-code-input/rulesprobe_o0u.py
행 1~20 = PLAN Task 5, 21~22 = 오케스트레이터 추가(여분 필드 credits · 클라이언트 supplierCodes 쓰기).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "backend" / "scripts"))

from e2e_app_path import firestore_client, signin_custom  # noqa: E402

PROJECT = "sunity-ai-coach"
DOC_ROOT = f"projects/{PROJECT}/databases/(default)/documents"
BASE = f"https://firestore.googleapis.com/v1/{DOC_ROOT}"

S, A, B = "o0uprobeS", "o0uprobeA", "o0uprobeB"
NAME = "시험강사"
CODE_OK, CODE_OFF, CODE_NONE = "QZPRBA", "QZPRBX", "QZNONE"

PROBE_PATHS = [
    f"instructorLinks/{A}",
    f"instructorLinks/{B}",
    f"instructorLinks/{S}",
    f"supplierCodes/{CODE_OK}",
    f"supplierCodes/{CODE_OFF}",
    f"supplierCodes/{CODE_NONE}",
    f"suppliers/{S}",
    f"users/{A}/analyses/probeo0u",
    f"users/{A}/analyses/probeo0uok",
    f"users/{A}",
]


def req(method: str, url: str, token: str | None, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:200]}


def sval(v):
    if v is None:
        return {"nullValue": None}
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    return {"stringValue": v}


def create_write(path: str, fields: dict, *, server_time: bool = True, create_only: bool = True,
                 client_ts: str | None = None) -> dict:
    f = {k: sval(v) for k, v in fields.items()}
    if client_ts is not None:
        f["linkedAt"] = {"timestampValue": client_ts}
    w: dict = {"update": {"name": f"{DOC_ROOT}/{path}", "fields": f}}
    if server_time:
        w["updateTransforms"] = [{"fieldPath": "linkedAt", "setToServerValue": "REQUEST_TIME"}]
    if create_only:
        w["currentDocument"] = {"exists": False}
    return {"writes": [w]}


def commit(token: str | None, body: dict) -> tuple[int, dict]:
    return req("POST", f"{BASE}:commit", token, body)


def link_fields(code=CODE_OK, supplier=S, name=NAME, **extra) -> dict:
    d = {"code": code, "supplierUid": supplier, "displayName": name}
    d.update(extra)
    return d


def main() -> int:
    db = firestore_client()

    def exists_all() -> list[bool]:
        return [db.document(p).get().exists for p in PROBE_PATHS]

    pre = exists_all()
    print("pre-exists", dict(zip(PROBE_PATHS, pre)))
    if any(pre):
        print("ABORT: probe path already exists — 남의 데이터를 건드리지 않으려고 멈춘다", file=sys.stderr)
        return 2

    rows: list[tuple[int, str, str, int, str]] = []
    try:
        now_ms = int(time.time() * 1000)
        db.document(f"supplierCodes/{CODE_OK}").set({"supplierUid": S, "displayName": NAME, "active": True})
        db.document(f"supplierCodes/{CODE_OFF}").set({"supplierUid": S, "displayName": NAME, "active": False})
        db.document(f"suppliers/{S}").set(
            {"email": None, "code": CODE_OK, "displayName": NAME, "active": True, "since": now_ms})

        tok = {u: signin_custom(u)[1] for u in (S, A, B)}

        def run(n: int, desc: str, expect: str, result: tuple[int, dict], check=None) -> None:
            code, body = result
            status = (body.get("error") or {}).get("status", "") if isinstance(body, dict) else ""
            got = "ALLOW" if code == 200 else ("DENY" if code == 403 else f"OTHER{code}")
            note = status
            if check is not None and code == 200:
                ok, msg = check(body)
                note = msg
                if not ok:
                    got = "ALLOW-BADBODY"
            rows.append((n, desc, expect, code, note))
            mark = "OK " if got == expect else "XX "
            print(f"{mark}{n:>2} | {desc} | expect {expect} | HTTP {code} {note}")

        run(1, "A get supplierCodes/QZPRBA", "ALLOW", req("GET", f"{BASE}/supplierCodes/{CODE_OK}", tok[A]))
        run(2, "no-token get supplierCodes/QZPRBA", "DENY", req("GET", f"{BASE}/supplierCodes/{CODE_OK}", None))
        run(3, "A list supplierCodes", "DENY", req("GET", f"{BASE}/supplierCodes?pageSize=1", tok[A]))
        run(4, "S create instructorLinks/S (own code)", "DENY",
            commit(tok[S], create_write(f"instructorLinks/{S}", link_fields())))
        run(5, "A create QZNONE (no such code)", "DENY",
            commit(tok[A], create_write(f"instructorLinks/{A}", link_fields(code=CODE_NONE))))
        run(6, "A create QZPRBX (inactive)", "DENY",
            commit(tok[A], create_write(f"instructorLinks/{A}", link_fields(code=CODE_OFF))))
        run(7, "A create supplierUid forged (B)", "DENY",
            commit(tok[A], create_write(f"instructorLinks/{A}", link_fields(supplier=B))))
        run(8, "A create displayName forged", "DENY",
            commit(tok[A], create_write(f"instructorLinks/{A}", link_fields(name="가짜"))))
        run(9, "A create linkedAt client timestamp", "DENY",
            commit(tok[A], create_write(f"instructorLinks/{A}", link_fields(), server_time=False,
                                        client_ts="2026-09-30T00:00:00Z")))
        run(10, "A create instructorLinks/B (other path)", "DENY",
            commit(tok[A], create_write(f"instructorLinks/{B}", link_fields())))
        run(11, "A create valid", "ALLOW",
            commit(tok[A], create_write(f"instructorLinks/{A}", link_fields())))
        run(12, "A update own link (no precondition)", "DENY",
            commit(tok[A], create_write(f"instructorLinks/{A}", link_fields(), create_only=False)))
        run(13, "A delete own link", "DENY", req("DELETE", f"{BASE}/instructorLinks/{A}", tok[A]))

        def has_ts(body: dict) -> tuple[bool, str]:
            ts = ((body.get("fields") or {}).get("linkedAt") or {}).get("timestampValue")
            keys = sorted((body.get("fields") or {}).keys())
            return (bool(ts), f"linkedAt.timestampValue={'yes' if ts else 'NO'} fields={keys}")

        run(14, "A get own link", "ALLOW", req("GET", f"{BASE}/instructorLinks/{A}", tok[A]), check=has_ts)
        run(15, "B get A link", "DENY", req("GET", f"{BASE}/instructorLinks/{A}", tok[B]))
        run(16, "A list instructorLinks", "DENY", req("GET", f"{BASE}/instructorLinks?pageSize=1", tok[A]))
        run(17, "S get suppliers/S", "ALLOW", req("GET", f"{BASE}/suppliers/{S}", tok[S]))
        run(18, "A get suppliers/S", "DENY", req("GET", f"{BASE}/suppliers/{S}", tok[A]))
        run(19, "A create users/A/analyses/probeo0u selfCheckForReference", "DENY",
            commit(tok[A], create_write(f"users/{A}/analyses/probeo0u", {"selfCheckForReference": "x"},
                                        server_time=False)))
        run(20, "A create users/A/analyses/probeo0uok note", "ALLOW",
            commit(tok[A], create_write(f"users/{A}/analyses/probeo0uok", {"note": "x"}, server_time=False)))
        run(21, "B create instructorLinks/B + extra credits:1", "DENY",
            commit(tok[B], create_write(f"instructorLinks/{B}", link_fields(credits=1))))
        run(22, "A PATCH supplierCodes/QZPRBA active=false", "DENY",
            req("PATCH", f"{BASE}/supplierCodes/{CODE_OK}?updateMask.fieldPaths=active", tok[A],
                {"fields": {"active": {"booleanValue": False}}}))
    finally:
        from firebase_admin import auth as fb_auth
        for p in PROBE_PATHS:
            try:
                db.document(p).delete()
            except Exception as e:  # noqa: BLE001 - 뒤처리는 끝까지 간다
                print("cleanup delete failed", p, type(e).__name__, file=sys.stderr)
        for u in (S, A, B):
            try:
                fb_auth.delete_user(u)
                print("auth delete_user ok", u)
            except fb_auth.UserNotFoundError:
                print("auth delete_user not-found", u)
        post = exists_all()
        print("post-exists", dict(zip(PROBE_PATHS, post)))
        n_links = len(list(db.collection("instructorLinks").limit(50).stream()))
        print("instructorLinks count", n_links)

    expected = {1: "ALLOW", 11: "ALLOW", 14: "ALLOW", 17: "ALLOW", 20: "ALLOW"}
    bad = []
    for n, _d, exp, code, note in rows:
        got = "ALLOW" if code == 200 and not note.startswith("linkedAt.timestampValue=NO") else (
            "DENY" if code == 403 else "OTHER")
        if got != exp or expected.get(n, "DENY") != exp:
            bad.append(n)
    passed = len(rows) - len(bad)
    print(f"RESULT {passed}/{len(rows)} match; mismatched rows={bad}; cleanup exists any={any(post)}")
    return 0 if (not bad and len(rows) == 22 and not any(post)) else 1


if __name__ == "__main__":
    sys.exit(main())
