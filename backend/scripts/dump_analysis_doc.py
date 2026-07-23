"""Firestore 분석 문서 덤프 헬퍼 — A-0 게이트 증거 + 목업 실데이터 (관찰 전용).

belle 실 doc(uid csKWYvI3WCPYPysNQ9KkWecaUvq1 / analysis
071df9f894d64d1696f106e613f51f5c)을 uid/analysisId 키로 Firestore 에서 읽어,
"짚은 부위(pointed) vs 활성 항목(shown) vs 실측(measured)" 대조에 필요한 값들을
stdout 에 원문 그대로 방출한다:
  - result.visionVeto.faultJoints / faultJointDeficits / status
  - result.deductionBreakdown.records[].criterion  (= activatedCriteria 집합)
  - result.faultZoomComparisons[]  (joint/region/deficitDeg/userFrameIdx/
    refFrameIdx/refMatch/tier/kind/imageUrl)
  - result.seedObservation.window_joints / fallback_joints (있으면)

--download-pngs <dir> 지정 시 각 faultZoomComparisons[].imageUrl (presigned GET
URL)을 <dir>/ 로 내려받아 오퍼레이터가 직접 눈으로 연다 (D-19).

이 스크립트는 관찰 전용이다 — 채점/분석 코드 무접촉 (D-20). 기존 accessor
firestore_admin.get_analysis 를 재사용하며, firebase-admin 클라이언트를 직접
초기화하지 않는다. 빈/결측 값은 그대로 빈 값으로 찍힌다 — except: pass 로 삼키지
않는다 (D-18: 틀리면 걸리는 장치).

크리덴셜:
    로컬:  FIREBASE_SA_PATH=firebase-sa.json  (repo 루트에 존재)
    Pod:   FIREBASE_SA_PATH=/workspace/firebase-sa.json 또는 SSM FIREBASE_SA_PARAM
    (하드코딩 금지 — CLAUDE.md / Parameter Store. T-33-01)

실행 (로컬):
    cd backend && FIREBASE_SA_PATH=../firebase-sa.json \
      python3 scripts/dump_analysis_doc.py \
      --uid csKWYvI3WCPYPysNQ9KkWecaUvq1 \
      --analysis-id 071df9f894d64d1696f106e613f51f5c \
      --download-pngs /tmp/a0_pngs
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent  # scripts/ → backend
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sunity_shared import firestore_admin as fa  # noqa: E402

# belle 실 doc (D-10) 기본값
DEFAULT_UID = "csKWYvI3WCPYPysNQ9KkWecaUvq1"
DEFAULT_ANALYSIS_ID = "071df9f894d64d1696f106e613f51f5c"


def _print_header(uid: str, analysis_id: str) -> None:
    creds = os.environ.get("FIREBASE_SA_PATH") or os.environ.get(
        "FIREBASE_SA_PARAM"
    )
    print("=" * 78, flush=True)
    print("dump_analysis_doc — 관찰 전용 (채점 무접촉, D-20)", flush=True)
    print(f"  uid          = {uid}", flush=True)
    print(f"  analysisId   = {analysis_id}", flush=True)
    print(f"  creds (env)  = FIREBASE_SA_PATH/PARAM -> {creds!r}", flush=True)
    print("=" * 78, flush=True)


def _dump_value(label: str, value) -> None:
    """값을 원문 그대로 방출 — 빈/None 도 그대로 보이게 (D-18)."""
    try:
        rendered = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        rendered = repr(value)
    print(f"\n### {label}", flush=True)
    print(rendered, flush=True)


def _download_pngs(comparisons: list, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n### download-pngs -> {out_dir}", flush=True)
    if not comparisons:
        print("  (faultZoomComparisons 비어 있음 — 내려받을 crop 0개, D-18)", flush=True)
        return
    for i, item in enumerate(comparisons):
        joint = item.get("joint") if isinstance(item, dict) else None
        url = item.get("imageUrl") if isinstance(item, dict) else None
        if not url:
            print(f"  [{i}] joint={joint!r} imageUrl 결측 — 스킵 (빈 값 노출, D-18)", flush=True)
            continue
        dest = out_dir / f"crop_{i:02d}_{joint or 'unknown'}.png"
        # 다운로드 실패는 조용히 넘기지 않고 예외 메시지를 그대로 노출한다 (D-18).
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
                data = resp.read()
            dest.write_bytes(data)
            print(f"  [{i}] joint={joint!r} -> {dest} ({len(data)} bytes)", flush=True)
        except Exception as exc:  # noqa: BLE001 - 실패를 삼키지 않고 노출
            print(f"  [{i}] joint={joint!r} DOWNLOAD FAILED: {exc!r}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Firestore 분석 문서 덤프 (관찰 전용)")
    ap.add_argument("--uid", default=DEFAULT_UID)
    ap.add_argument("--analysis-id", default=DEFAULT_ANALYSIS_ID)
    ap.add_argument(
        "--download-pngs",
        default=None,
        metavar="DIR",
        help="faultZoomComparisons[].imageUrl 를 DIR 로 내려받아 눈으로 연다 (D-19)",
    )
    args = ap.parse_args()

    _print_header(args.uid, args.analysis_id)

    doc = fa.get_analysis(args.uid, args.analysis_id)
    if doc is None:
        print(
            "\nDOC NOT FOUND — uid/analysisId 경로에 문서 없음. "
            "A-0 표를 조작하지 말 것 (STOP, D-18).",
            flush=True,
        )
        return 2

    res = doc.get("result") or {}
    vv = res.get("visionVeto") or {}
    bd = res.get("deductionBreakdown") or {}
    records = bd.get("records") if isinstance(bd, dict) else None
    so = res.get("seedObservation") or {}
    comparisons = res.get("faultZoomComparisons") or []

    print(f"\n(doc top-level keys: {sorted(doc.keys())})", flush=True)
    print(f"(result keys: {sorted(res.keys())})", flush=True)

    _dump_value("doc.status", doc.get("status"))
    _dump_value("doc.mode", doc.get("mode"))
    _dump_value("result.overallScore", res.get("overallScore"))

    _dump_value("visionVeto.status", vv.get("status"))
    _dump_value("visionVeto.faultJoints (짚은 부위 / pointed)", vv.get("faultJoints"))
    _dump_value("visionVeto.faultJointDeficits", vv.get("faultJointDeficits"))

    # activatedCriteria = 화면 항목(records[].criterion) 집합 (shown)
    criteria = None
    if isinstance(records, list):
        criteria = [r.get("criterion") for r in records if isinstance(r, dict)]
    _dump_value(
        "deductionBreakdown.records[].criterion (활성 항목 / shown)", criteria
    )
    _dump_value("deductionBreakdown.records[] (full)", records)

    _dump_value(
        "seedObservation.window_joints (실측 primary / measured)",
        so.get("window_joints"),
    )
    _dump_value(
        "seedObservation.fallback_joints (실측 fallback / measured)",
        so.get("fallback_joints"),
    )

    # faultZoomComparisons — crop 카드 전수 (joint/region/tier/frame idx/imageUrl)
    slim = []
    for item in comparisons:
        if not isinstance(item, dict):
            slim.append(item)
            continue
        slim.append(
            {
                k: item.get(k)
                for k in (
                    "joint",
                    "region",
                    "deficitDeg",
                    "kind",
                    "tier",
                    "refMatch",
                    "refMatched",
                    "userFrameIdx",
                    "refFrameIdx",
                    "imageUrl",
                )
            }
        )
    _dump_value("faultZoomComparisons[] (crop 카드 전수)", slim)

    if args.download_pngs:
        _download_pngs(comparisons, Path(args.download_pngs))

    return 0


if __name__ == "__main__":
    sys.exit(main())
