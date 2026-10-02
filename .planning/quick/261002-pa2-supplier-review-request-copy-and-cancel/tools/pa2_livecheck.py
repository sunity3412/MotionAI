"""quick-261002-pa2 배포 뒤 확인 P0~P4 — 오케스트레이터가 배포 (2) 뒤에 돌린다. 지금은 만들어 두기만 했다.

쓰기: Firestore 0 · S3 0. 부작용 = 대상 uid 의 Firebase Auth lastSignIn 메타데이터 갱신(signInWithCustomToken)
뿐 — thx_livecheck.py 와 같은 방식. 대상 uid 가 명단 밖(active False)이면 P1~P4 는 403 not_invited 가 정답이다.

사용(리포 루트에서):
  AWS_PROFILE=sunity-motion FIREBASE_SA_PATH=$PWD/firebase-sa.json \
    backend/.venv/bin/python <scratchpad>/pa2_livecheck.py --uid <공급자 uid> [--p4-ref <queued/review 가 아닌 본인 refId>]
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path.cwd()
ENV = dict(
    line.split("=", 1)
    for line in (REPO / "app/.env").read_text(encoding="utf-8").splitlines()
    if line.startswith("EXPO_PUBLIC_") and "=" in line
)
API = ENV["EXPO_PUBLIC_API_BASE_URL"].strip().rstrip("/")
WEB_KEY = ENV["EXPO_PUBLIC_FIREBASE_API_KEY"].strip()
URL = f"{API}/reference/upload-url"


def _post(body: dict, token: str | None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read() or b"{}"
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:200].decode(errors="replace")}


def _id_token(uid: str) -> str:
    import firebase_admin
    from firebase_admin import auth, credentials

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(os.environ["FIREBASE_SA_PATH"]))
    custom = auth.create_custom_token(uid).decode()
    req = urllib.request.Request(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={WEB_KEY}",
        data=json.dumps({"token": custom, "returnSecureToken": True}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["idToken"]


def _public_doc(ref_id: str) -> dict | None:
    from firebase_admin import firestore

    snap = firestore.client().document(f"reference/{ref_id}").get()
    return snap.to_dict() if snap.exists else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uid", required=True)
    ap.add_argument("--p4-ref", default=None)
    a = ap.parse_args()
    rows = []
    rows.append(("P0", "무토큰 cancel", *_post({"cancel": True, "refId": secrets.token_hex(16)}, None)))
    token = _id_token(a.uid)
    rows.append(("P1", "probe", *_post({"probe": True}, token)))
    rows.append(("P2", "임의 32hex cancel", *_post({"cancel": True, "refId": secrets.token_hex(16)}, token)))
    rows.append(("P3", "ref-kip-up cancel", *_post({"cancel": True, "refId": "ref-kip-up"}, token)))
    if a.p4_ref:
        before = _public_doc(a.p4_ref)
        rows.append(("P4", f"본인 {a.p4_ref[:8]}… cancel", *_post({"cancel": True, "refId": a.p4_ref}, token)))
        after = _public_doc(a.p4_ref)
        print(f"P4 doc 전후 동일 = {before == after} (status {None if before is None else before.get('registrationStatus')})")
    for pid, what, status, body in rows:
        err = body.get("error", {}) if isinstance(body, dict) else {}
        code = err.get("code") if err else ("probe" if body.get("probe") else body.get("registrationStatus"))
        print(f"{pid}\t{what}\t{status}\t{code}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
