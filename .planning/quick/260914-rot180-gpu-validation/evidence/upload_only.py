#!/usr/bin/env python3
"""앱 순서대로 업로드만 하고 멈춘다 — 분석 트리거는 호출자가 Pod 에 직접 건다.

왜 별도 스크립트인가 (2026-09-14):
  파이프라인 Lambda 의 RUNPOD_ANALYZE_URL 이 죽은 Pod 을 가리키고 있고, 그 env 를
  갱신하려면 RUNPOD_AUTH_TOKEN 을 읽어야 한다. 토큰을 세션에 꺼내지 않기 위해
  Lambda 를 건드리지 않고 Pod 에 직접 위임한다. 감사로 확정된 사실:
  위임 분기에서 Lambda 가 하는 일은 status=queued write 와 {bucket,key} POST 뿐이고
  (functions/pipeline/app.py:9095-9103) mode/referenceMotionId 는 Pod 가 Firestore 에서
  직접 읽는다(app.py:7540,7604). 즉 Pod 직접 호출은 분석 산출이 동일하다.

  단 S3 PUT 은 S3 이벤트를 발생시키므로 Lambda 가 한 번 돌아 죽은 URL 로 POST 했다가
  실패하고 fail_analysis 를 쓴다. 그 예외는 lambda_handler 가 **삼키므로**(app.py:9119)
  SQS 재시도는 없다 — 즉 failed write 는 딱 한 번이고, 이어서 Pod 가 덮어쓴다.
  그래서 호출자는 Lambda 의 failed write 가 지나간 뒤에 Pod 을 트리거해야 한다.

앱 순서 규율은 e2e_app_path.py 그대로: upload-url → Firestore 문서 먼저 → S3 PUT.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "scripts"))

import e2e_app_path as e2e  # noqa: E402  — 순서 규율·인증을 그대로 재사용


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--mode", required=True, choices=["mode1", "mode3"])
    ap.add_argument("--reference")
    ap.add_argument("--uid")
    a = ap.parse_args()

    vp = pathlib.Path(a.video)
    fmt = "mov" if vp.suffix.lower() == ".mov" else "mp4"
    size = vp.stat().st_size

    uid, token = (e2e.signin_custom(a.uid) if a.uid else e2e.anon_signin())

    body = {"mode": a.mode, "fileName": vp.name, "format": fmt, "fileSizeBytes": size}
    if a.reference:
        body["referenceMotionId"] = a.reference
    up = e2e.http_json(
        f"{e2e.API_BASE}/upload-url", body, {"Authorization": f"Bearer {token}"}
    )
    analysis_id = up["analysisId"]

    # 앱 순서 2 — 문서 먼저 (PUT 뒤에 쓰면 meta 를 못 읽어 조용히 mode3 로 떨어진다)
    db = e2e.firestore_client()
    now = int(time.time() * 1000)
    doc = {
        "analysisId": analysis_id,
        "mode": a.mode,
        "status": "uploading",
        "fileName": vp.name,
        "createdAt": now,
        "updatedAt": now,
        "learningOptIn": False,
    }
    if a.reference:
        doc["referenceMotionId"] = a.reference
    db.document(f"users/{uid}/analyses/{analysis_id}").set(doc)

    # 앱 순서 3 — S3 PUT (Content-Type 은 presign 과 동일해야 한다, api.ts 규율)
    ctype = "video/quicktime" if fmt == "mov" else "video/mp4"
    req = urllib.request.Request(up["uploadUrl"], data=vp.read_bytes(), method="PUT")
    req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=600) as r:
        assert 200 <= r.status < 300, f"S3 PUT {r.status}"

    print(json.dumps({
        "uid": uid,
        "analysisId": analysis_id,
        "bucket": "sunity-motion-pilot-videos",
        "key": f"uploads/{uid}/{analysis_id}.{fmt}",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
