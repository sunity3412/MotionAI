"""Phase 35 — Pod 데이터 조정 CLI 래퍼: 재추출 + 자세거리 정렬 + 짝 재선정 + 마커 좌표.

본체는 sunity_shared.analysis.compare_align 로 이동 (quick-260808-jix 라이브러리화).
이 스크립트에는 S3 회수(JOBS 키 표)·moments 주입·align.json 쓰기·verify 스틸
출력만 남는다 — 운영 경로는 pipeline `_run_deferred_compare_render` 가 같은
build_align 을 로컬 영상 경로로 직접 호출 (S3 키 표 불요).

belle 반려(08-07 "재생 중 딴 동작 · 마커 전부 엉뚱 · 짝 장면 불신")의 뿌리 수리.
렌더의 세 입력을 낡은 doc 리포트 대신 여기서 전부 재생성한다 — compare_align
모듈 docstring 참조.

Pod 실행 (프로젝트 /workspace/SunityMotion, doc.json 은 로컬에서 scp 로 주입):
    cd /workspace/SunityMotion/backend && source /workspace/aws_env.sh && \
    RTMW_DEVICE=cuda python3 scripts/p35_extract_align.py --workdir /workspace/p35

산출: {workdir}/{motion}/align.json + verify/*.jpg (오버레이·짝 스틸).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sunity_shared.analysis import compare_align  # noqa: E402

BUCKET = "sunity-motion-pilot-videos"

# motion → (user_key, ref_key). doc.json 은 {workdir}/{motion}/doc.json 필수(사전 주입).
JOBS: dict[str, tuple[str, str]] = {
    "elbow": ("fixtures/phase15/elbow-twist-sister/fault.mp4", "reference/ref-elbow-twist-sister.mp4"),
    "powerspin": ("fixtures/phase15/power-spin/fault.mp4", "reference/ref-power-spin.mp4"),
    "pdshape": ("fixtures/phase15/pdshape/correct.mp4", "reference/ref-pdshape.mp4"),
    "kipup": ("fixtures/phase15/kip-up/fault.mp4", "reference/ref-kip-up.mp4"),
    "realupload": ("uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/071df9f894d64d1696f106e613f51f5c.mp4",
                   "reference/ref-power-spin.mp4"),
    "pdshapefault": ("uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/pdshapefault1785373695.mp4",
                     "reference/ref-pdshape.mp4"),
    "peterpan": ("uploads/csKWYvI3WCPYPysNQ9KkWecaUvq1/peterpanfault1785373695.mp4",
                 "reference/ref-peter-pan.mp4"),
}


def s3_download(key: str, dst: Path):
    import boto3
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    boto3.client("s3").download_file(BUCKET, key, str(dst))


def process(motion: str, workdir: Path, model) -> None:
    ukey, rkey = JOBS[motion]
    mdir = workdir / motion
    doc = json.load(open(mdir / "doc.json"))
    records = doc["result"].get("deductionBreakdown", {}).get("records", [])
    moments_path = mdir / "moments.json"
    inject = json.load(open(moments_path)) if moments_path.exists() else {}

    uvid, rvid = mdir / "user.mp4", mdir / "ref.mp4"
    s3_download(ukey, uvid)
    s3_download(rkey, rvid)

    align = compare_align.build_align(
        uvid, rvid, records, mdir,
        model=model, moments=inject, verify_dir=mdir / "verify",
    )
    out = {"motion": motion, **align}
    json.dump(out, open(mdir / "align.json", "w"))
    print(f"[{motion}] frames u={align['userFrames']} r={align['refFrames']} "
          f"pairs={list(align['pairs'])} -> align.json", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True, type=Path)
    ap.add_argument("--motions", default=",".join(JOBS))
    args = ap.parse_args()
    model = compare_align.build_model()
    for m in args.motions.split(","):
        process(m.strip(), args.workdir, model)
    print("ALL_DONE")


if __name__ == "__main__":
    main()
