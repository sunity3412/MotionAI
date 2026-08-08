#!/usr/bin/env python3
"""Phase 34 수술 ① belle-FAIL 측 Pod 검증 러너 (quick-260808-r82 POD-VERIFY.md 절차 3~5).

GPU Pod 전용 — belle 08-08 반려 doc(127a2a90)의 user·ref 영상을 S3 에서 받아
compare_align.build_align(GPU 재추출)을 돌리고 align_quality 판정을 출력한다.
기대 = FAIL (반려 실측 근거: 이탈 국면 측정 + 종점 아티팩트 짝 + low_global_confidence).
CPU 갈음 금지 — CPU align 은 GPU align 과 다름이 실측됨(리그 E 13% vs 28%).

read-only: Firestore·S3 에 어떤 쓰기도 하지 않는다. 산출물은 --workdir 에만.

    RTMW_DEVICE=cuda python3 backend/scripts/phase34_pod_verify.py \
        --workdir /workspace/p34_verify

exit 0 = 기대대로 FAIL (게이트가 belle 반려 케이스를 걸러냄 — 절차 종결, 결과
라인을 POD-VERIFY.md 에 추기). exit 1 = PASS (임계 재캘리브레이션 라운드 필요 —
승인 5편 전건 PASS 유지 조건 하에서만, test_align_quality_calibration.py 가 게이트).
exit 2 = 실행 실패(입력 회수 불가 등).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

BELLE_UID = "csKWYvI3WCPYPysNQ9KkWecaUvq1"
BELLE_ANALYSIS_ID = "127a2a90c1d74c62ad61270eb3fe5625"
DEFAULT_BUCKET = "sunity-motion-pilot-videos"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--uid", default=BELLE_UID)
    p.add_argument("--analysis-id", default=BELLE_ANALYSIS_ID)
    p.add_argument("--bucket", default=DEFAULT_BUCKET)
    p.add_argument("--workdir", default="/workspace/p34_verify")
    args = p.parse_args()

    import boto3

    from sunity_shared import firestore_admin, s3keys
    from sunity_shared.analysis import compare_align

    work = Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)

    doc = firestore_admin.get_analysis(args.uid, args.analysis_id)
    if not doc:
        print(f"ERROR: doc 조회 실패 uid={args.uid} id={args.analysis_id}", file=sys.stderr)
        return 2
    (work / "belle_doc.json").write_text(
        json.dumps(doc, ensure_ascii=False, default=str), encoding="utf-8"
    )

    records = ((doc.get("result") or {}).get("deductionBreakdown") or {}).get("records") or []
    ref_id = doc.get("referenceMotionId")
    file_name = str(doc.get("fileName") or "")
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "mp4"
    user_key = s3keys.build_upload_key(args.uid, args.analysis_id, ext)
    ref_key = f"reference/{ref_id}.mp4"
    print(f"doc OK — records={len(records)} ref={ref_id}")
    print(f"user_key={user_key}\nref_key={ref_key}")

    s3 = boto3.client("s3")
    user_mp4 = work / f"user.{ext}"
    ref_mp4 = work / "ref.mp4"
    for key, dst in ((user_key, user_mp4), (ref_key, ref_mp4)):
        if not dst.exists():
            try:
                s3.download_file(args.bucket, key, str(dst))
            except Exception as exc:  # noqa: BLE001 - 회수 실패는 절차 중단 사유
                print(f"ERROR: S3 회수 실패 {key}: {exc}", file=sys.stderr)
                return 2
        print(f"  {dst.name}: {dst.stat().st_size} bytes")

    align = compare_align.build_align(user_mp4, ref_mp4, records, work)
    (work / "align.json").write_text(json.dumps(align), encoding="utf-8")
    ok, lines = compare_align.align_quality(align)
    print("\n".join(lines))
    print("VERDICT:", "PASS" if ok else "FAIL", "(기대 = FAIL)")
    return 1 if ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
