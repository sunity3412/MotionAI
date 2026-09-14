#!/usr/bin/env python3
"""분석 문서를 종결까지 폴링하고 전문을 JSON 으로 떨군다.

e2e_app_path.py 의 폴링부만 떼어낸 것 — 차이는 두 가지다:
  · 종결 상태 판정에서 Lambda 가 죽은 URL 로 POST 했다가 남긴 **일시적 failed** 를
    종결로 오인하지 않는다 (--ignore-early-failed). Pod 가 이어서 덮어쓴다.
  · 요약만 찍지 않고 doc 전문을 파일로 저장한다 — joints3d 재계산에 필요하다
    (dump_analysis_doc.py 는 joints3d/dimensionScores/unjudgedJoints 를 안 찍는다).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "scripts"))

import e2e_app_path as e2e  # noqa: E402

TERMINAL = ("completed", "done", "error")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uid", required=True)
    ap.add_argument("--analysis-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--ignore-early-failed-sec", type=int, default=120,
                    help="이 시간 안에 나타난 failed 는 Lambda 의 죽은-URL POST 잔재로 보고 무시")
    a = ap.parse_args()

    db = e2e.firestore_client()
    ref = db.document(f"users/{a.uid}/analyses/{a.analysis_id}")
    t0 = time.time()
    snap: dict = {}
    seen: list[str] = []
    while time.time() - t0 < a.timeout:
        snap = ref.get().to_dict() or {}
        status = snap.get("status", "?")
        if not seen or seen[-1] != status:
            seen.append(status)
            print(f"  [{round(time.time()-t0):4d}s] {status}", flush=True)
        if status in TERMINAL:
            break
        if status == "failed" and time.time() - t0 > a.ignore_early_failed_sec:
            break
        time.sleep(10)

    pathlib.Path(a.out).write_text(
        json.dumps(snap, ensure_ascii=False, default=str), encoding="utf-8"
    )
    res = snap.get("result") or {}
    print(json.dumps({
        "analysisId": a.analysis_id,
        "status": snap.get("status"),
        "elapsedSec": round(time.time() - t0),
        "statusTrail": seen,
        "errorCode": snap.get("errorCode"),
        "overallScore": res.get("overallScore"),
        "dimensionScores": res.get("dimensionScores"),
        "unjudgedJoints": res.get("unjudgedJoints"),
        "visionVetoStatus": (res.get("visionVeto") or {}).get("status"),
        "joints3dFrames": res.get("joints3dFrames"),
        "out": a.out,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
