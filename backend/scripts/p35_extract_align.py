"""Phase 35 — Pod 데이터 조정 CLI 래퍼: 재추출 + 자세거리 정렬 + 짝 재선정 + 마커 좌표.

본체는 sunity_shared.analysis.compare_align 로 이동 (quick-260808-jix 라이브러리화).
이 스크립트에는 S3 회수(JOBS 키 표)·moments 주입·align.json 쓰기·verify 스틸
출력만 남는다 — 운영 경로는 pipeline `_run_deferred_compare_render` 가 같은
build_align 을 로컬 영상 경로로 직접 호출 (S3 키 표 불요).

belle 반려(08-07 "재생 중 딴 동작 · 마커 전부 엉뚱 · 짝 장면 불신")의 뿌리 수리.
렌더의 세 입력을 낡은 doc 리포트 대신 여기서 전부 재생성한다 — compare_align
모듈 docstring 참조.

캐시 정책(quick-260816-k2f, 기본 fresh): 이 스크립트가 쓰는 --workdir(예:
/workspace/p35)는 실행마다 새로 만들어지지 않고 오래 남는 작업 디렉토리다.
S3 원본(JOBS 의 userS3Key/refS3Key)을 새 영상으로 교체해도 s3_download() 의
`dst.exists()` 와 compare_align.extract() 의 *.jpg 존재 체크가 옛 로컬 사본을
그대로 재사용해 버린다 — 원본 내용이 바뀌었는지는 둘 다 확인하지 않는다.
2026-08-16 실측: ref-climb.mp4 를 새 영상으로 교체하고 재추출했는데 climb
슬롯만 옛 refFrames=256(climb/rf15 mtime 06:00)을 재사용했고, climbfault 는
같은 새 ref.mp4(40,928,589B)로 refFrames=119(climbfault/rf15 mtime 09:13)를
정상 산출 — rm -rf 후 재추출하니 climb 도 119 로 정상화됐다. 그래서 기본
동작을 "매 motion 처리 전 파생 캐시(user.mp4/ref.mp4/uf15/rf15/verify) 삭제
후 재생성"으로 바꾼다(belle 승인: "매번 캐시를 다 지우고 돌리는 것을
기본으로"). compare_align.extract() 자체는 손대지 않는다 — shared 코드이고,
운영 경로(pipeline._run_deferred_compare_render)는 분석마다 새 임시 workdir
을 쓰므로 이 존재기반 캐시 구멍에 원래 걸리지 않는다. 반복 실행이 잦아
재다운로드+재추출 비용을 피하고 싶으면 --reuse-cache 로 옛 동작(존재하면
재사용)을 명시적으로 선택한다.

Pod 실행 (프로젝트 /workspace/SunityMotion, doc.json 은 로컬에서 scp 로 주입):
    cd /workspace/SunityMotion/backend && source /workspace/aws_env.sh && \
    RTMW_DEVICE=cuda python3 scripts/p35_extract_align.py --workdir /workspace/p35

산출: {workdir}/{motion}/align.json + verify/*.jpg (오버레이·짝 스틸).
"""
from __future__ import annotations

import argparse
import json
import shutil
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
# climb/climbfault/combo 3행 추가(quick-260816-c3m) — 발굴 스윕 소스 게이트 실증용,
# 이 3건은 렌더 슬롯이 아니다(P35 렌더 미실행, README.md 참조).
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
    "climb": ("fixtures/phase15/climb/correct.mp4", "reference/ref-climb.mp4"),
    "climbfault": ("fixtures/phase15/climb/fault.mp4", "reference/ref-climb.mp4"),
    "combo": ("fixtures/phase15/combo/correct.mp4", "reference/ref-combo.mp4"),
}

# 파생 캐시 화이트리스트(quick-260816-k2f) — 정확한 리터럴 이름 5개만, glob/
# 와일드카드 없음(T-k2f-01 mitigate). doc.json/moments.json/align.json 은
# 의도적으로 화이트리스트 밖이다 — 이 셋은 파생 캐시가 아니라 사전 주입 입력
# (doc.json/moments.json)과 이 스크립트의 최종 산출물(align.json)이라 지우면
# 재생성이 불가능하다.
CACHE_PATHS = ("user.mp4", "ref.mp4", "uf15", "rf15", "verify")


def clean_motion_cache(mdir: Path) -> list[str]:
    """mdir 아래 CACHE_PATHS 중 실제로 존재하는 항목만 삭제하고 삭제한 이름을
    CACHE_PATHS 순서 그대로 반환한다. 디렉토리는 재귀 삭제(shutil.rmtree),
    파일은 단일 삭제(unlink). 화이트리스트 항목이 하나도 없거나 mdir 자체가
    없어도 예외 없이 빈 리스트를 반환한다."""
    removed: list[str] = []
    for name in CACHE_PATHS:
        p = mdir / name
        if not p.exists():
            continue
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        removed.append(name)
    return removed


def maybe_clean_cache(mdir: Path, *, reuse_cache: bool) -> list[str]:
    """reuse_cache=True 면 삭제를 스킵하고 옛 파생 캐시를 그대로 재사용(명시적
    opt-in), False(기본)면 clean_motion_cache(mdir) 에 그대로 위임한다."""
    if reuse_cache:
        return []
    return clean_motion_cache(mdir)


def s3_download(key: str, dst: Path):
    import boto3
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    boto3.client("s3").download_file(BUCKET, key, str(dst))


def process(motion: str, workdir: Path, model, *, reuse_cache: bool = False) -> None:
    mdir = workdir / motion
    removed = maybe_clean_cache(mdir, reuse_cache=reuse_cache)
    if removed:
        print(f"[{motion}] fresh: 파생 캐시 삭제 {removed}", flush=True)
    elif reuse_cache:
        print(f"[{motion}] --reuse-cache: 캐시 재사용(삭제 건너뜀)", flush=True)
    else:
        print(f"[{motion}] fresh: 캐시 없음(첫 실행)", flush=True)

    ukey, rkey = JOBS[motion]
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


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True, type=Path)
    ap.add_argument("--motions", default=",".join(JOBS))
    ap.add_argument(
        "--reuse-cache", action="store_true",
        help=(
            "파생 캐시(user.mp4/ref.mp4/uf15/rf15/verify) 삭제를 건너뛰고 "
            "재사용(기본은 fresh — 매 motion 처리 전 전부 삭제 후 S3 재다운로드"
            "+재추출)"
        ),
    )
    return ap


def main() -> None:
    args = build_arg_parser().parse_args()
    model = compare_align.build_model()
    for m in args.motions.split(","):
        process(m.strip(), args.workdir, model, reuse_cache=args.reuse_cache)
    print("ALL_DONE")


if __name__ == "__main__":
    main()
