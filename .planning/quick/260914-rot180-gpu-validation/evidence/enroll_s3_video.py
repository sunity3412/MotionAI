#!/usr/bin/env python3
"""이미 S3 에 있는 영상을 재업로드 없이 분석 대상으로 등록한다 (서버측 copy).

`upload_only.py` 는 로컬 파일을 PUT 한다. 픽스처처럼 이미 버킷에 있는 영상
(예: fixtures/phase15/pdshape/correct.mp4, 81MB)은 내려받았다 올릴 이유가 없다 —
같은 버킷 안에서 S3 서버측 복사로 `uploads/{uid}/{analysisId}.mp4` 키만 만들면 된다.

앱 순서 규율은 그대로 지킨다: upload-url(analysisId 발급) → **Firestore 문서 먼저**
→ 오브젝트 생성. 문서를 나중에 쓰면 파이프라인이 meta 를 못 읽어 조용히 mode3 로
떨어진다(demo-only-pod-bring-up-procedure).

presigned PUT URL 은 쓰지 않는다 — 키 규약(s3keys.build_upload_key)이 결정적이라
같은 키를 copy 로 만들어도 파이프라인 입장에서는 구분이 없다.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import boto3

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "scripts"))

import e2e_app_path as e2e  # noqa: E402

BUCKET = "sunity-motion-pilot-videos"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-key", required=True, help="같은 버킷 안 원본 키")
    ap.add_argument("--mode", required=True, choices=["mode1", "mode3"])
    ap.add_argument("--reference")
    ap.add_argument("--uid")
    ap.add_argument("--profile", default="sunity-motion")
    a = ap.parse_args()

    s3 = boto3.Session(profile_name=a.profile, region_name="ap-northeast-2").client("s3")
    head = s3.head_object(Bucket=BUCKET, Key=a.source_key)
    size = int(head["ContentLength"])
    fmt = "mov" if a.source_key.lower().endswith(".mov") else "mp4"
    name = a.source_key.rsplit("/", 1)[-1]

    uid, token = (e2e.signin_custom(a.uid) if a.uid else e2e.anon_signin())

    body = {"mode": a.mode, "fileName": name, "format": fmt, "fileSizeBytes": size}
    if a.reference:
        body["referenceMotionId"] = a.reference
    up = e2e.http_json(
        f"{e2e.API_BASE}/upload-url", body, {"Authorization": f"Bearer {token}"}
    )
    analysis_id = up["analysisId"]

    # 앱 순서 2 — 문서 먼저
    db = e2e.firestore_client()
    now = int(time.time() * 1000)
    doc = {
        "analysisId": analysis_id, "mode": a.mode, "status": "uploading",
        "fileName": name, "createdAt": now, "updatedAt": now, "learningOptIn": False,
    }
    if a.reference:
        doc["referenceMotionId"] = a.reference
    db.document(f"users/{uid}/analyses/{analysis_id}").set(doc)

    # 앱 순서 3 — 오브젝트 생성 (서버측 copy, 바이트 왕복 0)
    dest = f"uploads/{uid}/{analysis_id}.{fmt}"
    ctype = "video/quicktime" if fmt == "mov" else "video/mp4"
    s3.copy_object(
        Bucket=BUCKET, Key=dest,
        CopySource={"Bucket": BUCKET, "Key": a.source_key},
        ContentType=ctype, MetadataDirective="REPLACE",
    )

    print(json.dumps({
        "uid": uid, "analysisId": analysis_id, "bucket": BUCKET,
        "key": dest, "sourceKey": a.source_key, "sizeBytes": size,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
