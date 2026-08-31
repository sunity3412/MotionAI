#!/usr/bin/env python3
"""E2E — 앱과 동일 경로 (upload-url → Firestore 문서 먼저 → S3 PUT → 완료 폴링).

memory demo-only-pod-bring-up-procedure 의 순서 규율 그대로:
문서를 PUT 뒤에 쓰면 파이프라인이 meta 를 못 읽어 조용히 mode3 로 떨어진다.
계약: {mode, fileName, format, fileSizeBytes, referenceMotionId} camelCase.

사용: backend/.venv/bin/python backend/scripts/e2e_app_path.py --video <path> --mode mode1|mode3 [--reference <refId>] [--uid <uid>]
uid 를 주면 그 계정으로 이어서 분석(mode3 전후 페어용). 안 주면 익명 신규.
출력: JSON 한 줄 {uid, analysisId, status, elapsedSec, doc 요약}

실증: 2026-08-31 Pod 검증 4런(mode1 postureAxes 확인 · mode3 전후 페어 · 75초 코칭 재측정)
을 이 스크립트로 완주. firebase-admin 필요(backend/.venv 에 있음), Admin SA json = 리포 루트.
"""
import argparse
import json
import sys
import time
import urllib.request
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]

def env_val(key: str) -> str:
    for line in (REPO / "app/.env").read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"missing {key} in app/.env")

API_KEY = env_val("EXPO_PUBLIC_FIREBASE_API_KEY")
API_BASE = env_val("EXPO_PUBLIC_API_BASE_URL")

def http_json(url: str, body: dict | None = None, headers: dict | None = None, method: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"))
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def anon_signin() -> tuple[str, str]:
    r = http_json(f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}", {"returnSecureToken": True})
    return r["localId"], r["idToken"]

def signin_custom(uid: str) -> tuple[str, str]:
    """기존 uid 로 이어가기 — admin custom token 발급 후 교환 (mode3 페어용)."""
    import firebase_admin
    from firebase_admin import auth as fb_auth, credentials
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(REPO / "sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json")))
    ct = fb_auth.create_custom_token(uid).decode()
    r = http_json(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={API_KEY}", {"token": ct, "returnSecureToken": True})
    return uid, r["idToken"]

def firestore_client():
    import firebase_admin
    from firebase_admin import credentials, firestore
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(str(REPO / "sunity-ai-coach-firebase-adminsdk-fbsvc-7055d7d3d1.json")))
    return firestore.client()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--mode", required=True, choices=["mode1", "mode3"])
    ap.add_argument("--reference")
    ap.add_argument("--uid")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()

    vp = pathlib.Path(a.video)
    fmt = "mov" if vp.suffix.lower() == ".mov" else "mp4"
    size = vp.stat().st_size

    uid, token = (signin_custom(a.uid) if a.uid else anon_signin())

    body = {"mode": a.mode, "fileName": vp.name, "format": fmt, "fileSizeBytes": size}
    if a.reference:
        body["referenceMotionId"] = a.reference
    up = http_json(f"{API_BASE}/upload-url", body, {"Authorization": f"Bearer {token}"})
    analysis_id = up["analysisId"]
    upload_url = up["uploadUrl"]

    # 앱 순서 2: Firestore 문서 먼저 (loading.tsx:158 형태)
    db = firestore_client()
    now = int(time.time() * 1000)
    doc = {
        "analysisId": analysis_id, "mode": a.mode, "status": "uploading",
        "fileName": vp.name, "createdAt": now, "updatedAt": now,
        "learningOptIn": False,
    }
    if a.reference:
        doc["referenceMotionId"] = a.reference
    db.document(f"users/{uid}/analyses/{analysis_id}").set(doc)

    # 앱 순서 3: S3 PUT (Content-Type = presign 과 동일해야 함, api.ts 규율)
    ctype = "video/quicktime" if fmt == "mov" else "video/mp4"
    req = urllib.request.Request(upload_url, data=vp.read_bytes(), method="PUT")
    req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=300) as r:
        assert 200 <= r.status < 300, f"S3 PUT {r.status}"

    t0 = time.time()
    status = "uploading"
    snap = {}
    while time.time() - t0 < a.timeout:
        snap = db.document(f"users/{uid}/analyses/{analysis_id}").get().to_dict() or {}
        status = snap.get("status", "?")
        if status in ("completed", "failed", "done", "error"):
            break
        time.sleep(10)

    coach_keys = [k for k in snap.keys() if "coach" in k.lower() or "joint" in k.lower() or "score" in k.lower() or "progress" in k.lower() or "delta" in k.lower()]
    print(json.dumps({
        "uid": uid, "analysisId": analysis_id, "status": status,
        "elapsedSec": round(time.time() - t0),
        "errorCode": snap.get("errorCode"),
        "overallScore": snap.get("overallScore"),
        "docKeys": sorted(snap.keys()),
        "coachRelatedKeys": sorted(coach_keys),
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
