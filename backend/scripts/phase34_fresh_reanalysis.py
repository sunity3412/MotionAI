#!/usr/bin/env python3
"""Phase 34 신선 재분석 드라이버 — 원본 영상 그대로, 새 파이프라인, sim 계정 (Pod 전용).

belle 반려 doc(127a2a90)의 **원본 업로드 영상**을 수술 ②③① 반영 파이프라인으로
처음부터 재분석한다. 원 doc 는 무접촉 — sweep_phase15 direct-process 선례대로
SOURCE 키와 analysis identity 를 분리해 sim uid 아래 fresh doc 을 만든다
(uploads/ COPY 0, notification 발화 0, _process 직접 1회).

검증 대상 (quick-260808-r82 POD-VERIFY 6절 + 조건 체인):
  - 수술 ② live: 방출 records 의 atVideoSec 이 이탈 국면(원 17.56/17.78s)을 벗어나는가.
  - 수술 ③ live: side_match 그립 거울상 관측 로그 (스왑 미적용).
  - 수술 ① live: compare_render 스테이지가 tier 아닌 align_quality 로 진입 판정 —
    양품이면 리그 A~H 전건 판정까지 (ALL PASS 시 sim doc 에 done 부착).

    source /workspace/_reprocess_env.sh && \
    RECOGNIZER_BACKEND=gemini GEMINI_API_KEY=... python3 \
      backend/scripts/phase34_fresh_reanalysis.py

원 doc 대비 records 비교 표를 stdout 에 출력한다. exit 0 = 분석 done, 그 외 실패.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SIM_UID = "fvcNXzEqKjgqVxRPVSj1iwFnIpn2"
BELLE_UID = "csKWYvI3WCPYPysNQ9KkWecaUvq1"
BELLE_ANALYSIS_ID = "127a2a90c1d74c62ad61270eb3fe5625"
DEFAULT_BUCKET = "sunity-motion-pilot-videos"


def _load_pipeline_module():
    """pipeline app.py 를 경로 import (rerun_compare_stage 선례 — 분기 0, 코드 1벌)."""
    path = BACKEND / "functions" / "pipeline" / "app.py"
    spec = importlib.util.spec_from_file_location("pipeline_app_p34", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fmt_records(records) -> list[str]:
    out = []
    for r in records or []:
        if isinstance(r, dict):
            out.append(
                f"  {r.get('recordId') or '-'} {r.get('criterion')}"
                f" at={r.get('atVideoSec')} points={r.get('points')}"
            )
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--uid", default=SIM_UID, help="fresh doc 소유 uid (sim)")
    p.add_argument("--source-uid", default=BELLE_UID)
    p.add_argument("--source-analysis-id", default=BELLE_ANALYSIS_ID)
    p.add_argument("--bucket", default=DEFAULT_BUCKET)
    args = p.parse_args()

    from sunity_shared import firestore_admin, models, s3keys

    src = firestore_admin.get_analysis(args.source_uid, args.source_analysis_id)
    if not src:
        print("ERROR: source doc 조회 실패", file=sys.stderr)
        return 2
    file_name = str(src.get("fileName") or "")
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "mp4"
    video_key = s3keys.build_upload_key(args.source_uid, args.source_analysis_id, ext)
    ref_id = src.get("referenceMotionId")
    src_records = ((src.get("result") or {}).get("deductionBreakdown") or {}).get("records") or []

    new_id = f"p34fresh{int(time.time())}"  # 영숫자만 (sweep HIGH 2 규율)
    now = int(time.time() * 1000)
    doc = {
        "analysisId": new_id,
        "uid": args.uid,
        "mode": src.get("mode") or models.MODE_EXPERT,
        "status": models.STATUS_QUEUED,
        "videoKey": video_key,
        "videoFormat": ext,
        "fileSizeBytes": 0,
        "createdAt": now,
        "updatedAt": now,
        "sourceLabel": f"phase34_fresh_reanalysis:{args.source_analysis_id}",
    }
    if ref_id:
        doc["referenceMotionId"] = ref_id
    db = firestore_admin._db()  # noqa: SLF001 - sweep_phase15 선례(fa._db())
    db.collection("users").document(args.uid).collection("analyses").document(new_id).set(doc)
    print(f"fresh doc 생성: uid={args.uid} analysisId={new_id} mode={doc['mode']} ref={ref_id}")
    print(f"SOURCE key={video_key} (원 doc 무접촉)")

    pipeline = _load_pipeline_module()
    t0 = time.time()
    pipeline._process(args.bucket, video_key, args.uid, new_id)  # noqa: SLF001
    dt = time.time() - t0

    out = firestore_admin.get_analysis(args.uid, new_id) or {}
    res = out.get("result") or {}
    bd = res.get("deductionBreakdown") or {}
    print(f"\n== 분석 완료 {dt:.1f}s — status={out.get('status')} score={res.get('overallScore')}")
    print("-- 원 doc records (수술 전 산출):")
    print("\n".join(_fmt_records(src_records)) or "  (없음)")
    print("-- fresh records (수술 후):")
    print("\n".join(_fmt_records(bd.get("records"))) or "  (없음)")
    rc = res.get("renderedCompare")
    print(f"-- renderedCompare: {json.dumps(rc, ensure_ascii=False) if rc else '(필드 없음 — 스킵 계열)'}")
    ma = res.get("motionAlignment") or {}
    print(f"-- motionAlignment.tier: {ma.get('tier')} reason={ma.get('reason')}")
    return 0 if out.get("status") == models.STATUS_DONE else 1


if __name__ == "__main__":
    raise SystemExit(main())
