"""렌더 doc 4건 재산출 — 백업 → 직렬 재분석 → 회수 (quick-260731-iis T3).

목적 두 가지를 한 번에 만든다:
  · §C-2 미검증 항목의 재료 (userVideoSec/refVideoSec 가 실린 재산출 doc)
  · S10 실 doc 판정 재료 (실 학생 x 실 기준 12관절 faultZoom PNG)

안전 규율:
  · 파이프라인은 **동시성 비안전** — 반드시 1건씩, 완료 확인 후 다음 (memory:
    pipeline-not-concurrency-safe-eval-serial).
  · 재분석 전에 doc 전문을 `docs_before/` 로 백업한다 (되돌릴 수 있게).
  · `/analyze` 는 Pod 내부 loopback 으로 호출한다 — 토큰이 로컬 셸/로그/산출 JSON 에
    남지 않는다 (T-iis-05). 토큰 값은 출력하지 않는다.
  · 완료 판정은 Firestore `status`/`updatedAt` 폴링. 상태를 강제로 되돌리지 않는다 —
    거부되거나 updatedAt 이 안 움직이면 중단·보고 (fail-closed, T-iis-04).

모드:
  --list       대상 후보 조회 (점수·mode·referenceMotionId·업로드 키). 쓰기 0.
  --backup     대상 doc 전문 저장.
  --reanalyze  직렬 재분석 + 폴링.
  --collect    재산출 doc 전문 + faultZoom PNG S3 키 목록 저장.

실행 위치 = Pod.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve()


def _find_backend() -> Path:
    for p in _HERE.parents:
        if (p / "backend" / "shared" / "python").is_dir():
            return p / "backend"
    pod = Path("/workspace/SunityMotion/backend")
    if (pod / "shared" / "python").is_dir():
        return pod
    raise RuntimeError("backend 디렉터리를 찾지 못함")


_BACKEND = _find_backend()
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "shared" / "python"))

from sunity_shared import firestore_admin as fa  # noqa: E402

UID = "fvcNXzEqKjgqVxRPVSj1iwFnIpn2"
BUCKET = "sunity-motion-pilot-videos"
ANALYZE_URL = "http://127.0.0.1:8000/analyze"


def _analyses(db) -> list[tuple[str, dict]]:
    col = db.collection("users").document(UID).collection("analyses")
    return [(d.id, d.to_dict() or {}) for d in col.stream()]


def _summary(aid: str, doc: dict) -> dict:
    res = doc.get("result") or {}
    fz = res.get("faultZoomComparisons") or []
    return {
        "analysisId": aid,
        "status": doc.get("status"),
        "mode": doc.get("mode"),
        "referenceMotionId": doc.get("referenceMotionId"),
        "overallScore": res.get("overallScore"),
        "faultZoomCards": len(fz),
        "faultZoomCriteria": [c.get("criterion") for c in fz],
        "userVideoSec": res.get("userVideoSec"),
        "refVideoSec": res.get("refVideoSec"),
        "videoKey": doc.get("videoKey"),
        "updatedAt": doc.get("updatedAt"),
        "createdAt": doc.get("createdAt"),
    }


def do_list(db, out: Path | None) -> int:
    rows = [_summary(a, d) for a, d in _analyses(db)]
    rows.sort(key=lambda r: (r.get("createdAt") or 0))
    hdr = f"{'analysisId':<26}{'status':<10}{'mode':<8}{'score':>6}{'cards':>6}  {'refMotion':<24}key"
    print(hdr, file=sys.stderr)
    for r in rows:
        print(
            f"{r['analysisId']:<26}{str(r['status']):<10}{str(r['mode']):<8}"
            f"{str(r['overallScore']):>6}{r['faultZoomCards']:>6}  "
            f"{str(r['referenceMotionId']):<24}{r.get('videoKey')}",
            file=sys.stderr,
        )
    print(f"\n총 {len(rows)}건", file=sys.stderr)
    if out:
        out.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def do_backup(db, ids: list[str], out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    for aid in ids:
        snap = db.document(f"users/{UID}/analyses/{aid}").get()
        if not getattr(snap, "exists", False):
            print(f"거부: {aid} 문서 부재", file=sys.stderr)
            return 2
        doc = snap.to_dict() or {}
        (out_dir / f"{aid}.json").write_text(
            json.dumps(doc, ensure_ascii=False, default=str)
        )
        s = _summary(aid, doc)
        print(f"  [{aid}] score={s['overallScore']} cards={s['faultZoomCards']} "
              f"userVideoSec={s['userVideoSec']} refVideoSec={s['refVideoSec']} → 백업",
              file=sys.stderr)
    return 0


def _post_analyze(key: str) -> tuple[int, str]:
    token = os.environ.get("RUNPOD_AUTH_TOKEN", "")
    body = json.dumps({"bucket": BUCKET, "key": key}).encode()
    req = urllib.request.Request(
        ANALYZE_URL, data=body,
        headers={"Content-Type": "application/json", "X-RunPod-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()[:300]
    except Exception as exc:  # noqa: BLE001 - 상태코드 없는 실패도 사유를 남긴다
        return -1, repr(exc)[:300]


def do_reanalyze(db, ids: list[str], timeout_s: int) -> int:
    for aid in ids:
        ref = db.document(f"users/{UID}/analyses/{aid}")
        doc0 = ref.get().to_dict() or {}
        key = doc0.get("videoKey")
        if not key:
            print(f"중단: {aid} 업로드 키 부재 — 상태 강제 변경 없이 fail-closed",
                  file=sys.stderr)
            return 2
        prev_updated = doc0.get("updatedAt")
        print(f"\n[{aid}] key={key} prevUpdatedAt={prev_updated} "
              f"prevScore={(doc0.get('result') or {}).get('overallScore')}", file=sys.stderr)

        status, body = _post_analyze(key)
        print(f"  POST /analyze -> {status} {body}", file=sys.stderr)
        if status not in (200, 202):
            print(f"  중단: /analyze 거부 ({status})", file=sys.stderr)
            return 3

        t0 = time.time()
        last = None
        while time.time() - t0 < timeout_s:
            time.sleep(15)
            d = ref.get().to_dict() or {}
            st, up = d.get("status"), d.get("updatedAt")
            if (st, up) != last:
                print(f"    t+{int(time.time()-t0):>4}s status={st} updatedAt={up}",
                      file=sys.stderr)
                last = (st, up)
            if st == "done" and up != prev_updated:
                print(f"  [{aid}] 완료 ({int(time.time()-t0)}s) "
                      f"score={(d.get('result') or {}).get('overallScore')}", file=sys.stderr)
                break
            if st == "failed":
                print(f"  중단: {aid} status=failed error={d.get('error')}", file=sys.stderr)
                return 4
        else:
            print(f"  중단: {aid} 타임아웃 {timeout_s}s — 상태 강제 변경 없이 fail-closed",
                  file=sys.stderr)
            return 5
    return 0


_STAGE = Path("/workspace/_s3stage")


class _StagedS3:
    """`download_file` 만 가로채는 얇은 shim (나머지는 실 클라이언트로 위임).

    왜 필요한가 (2026-07-31 실측 2회): boto3 `download_file` 의 TransferManager
    (멀티스레드)가 서울 리전 GET 에서 행에 걸린다 — 임시파일 0 바이트로 4분+,
    GPU 0%. 반면 **단일 스레드 ranged GET 은 정상**(566~1494 KB/s 실측).
    회선이 아니라 TransferManager 문제다.

    스테이지를 **믿고 쓰지 않는다** — S3 head_object 의 ContentLength 와 크기가
    정확히 같을 때만 사용하고, 다르면 무시하고 단일 스레드로 다시 받는다.
    """

    def __init__(self, real) -> None:
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def download_file(self, Bucket, Key, Filename, **kw):  # noqa: N803
        from boto3.s3.transfer import TransferConfig

        remote = int(self._real.head_object(Bucket=Bucket, Key=Key)["ContentLength"])
        staged = _STAGE / Key
        if staged.is_file() and staged.stat().st_size == remote:
            import shutil

            print(f"    [stage] {Key} 크기 일치({remote}) → 로컬 스테이지 사용",
                  file=sys.stderr, flush=True)
            shutil.copyfile(staged, Filename)
            return
        print(f"    [s3] {Key} 단일 스레드 다운로드 ({remote} bytes)",
              file=sys.stderr, flush=True)
        self._real.download_file(
            Bucket, Key, Filename,
            Config=TransferConfig(use_threads=False,
                                  multipart_threshold=1024 * 1024 * 1024),
        )
        got = Path(Filename).stat().st_size
        if got != remote:
            raise RuntimeError(f"{Key} 다운로드 크기 불일치: {got} != {remote}")


def _load_pipeline():
    """pipeline 모듈 lazy-load — sweep_phase15._load_pipeline 과 동일 관용구.

    신규 분석 path 를 만들지 않는다 (RESEARCH Anti-Pattern "Writing a new analysis path").
    로드 후 모듈 레벨 `_s3` 만 스테이지 shim 으로 감싼다 (프로덕션 코드 변경 0 —
    이 하네스 프로세스 안에서만 유효).
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", str(_BACKEND / "functions" / "pipeline" / "app.py")
    )
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._s3 = _StagedS3(pipeline._s3)
    pipeline._ensure_adapters()
    return pipeline


def do_reprocess_direct(db, ids: list[str]) -> int:
    """direct-process 재산출 — pipeline._process 를 직렬로 1건씩 호출.

    `/analyze` 를 쓰지 못하는 이유(실측): 이 렌더 doc 들의 `videoKey` 는
    `fixtures/phase15/{motion}/{correct|fault}.mp4` 라서 `parse_upload_key` 의
    `uploads/{uid}/{analysisId}.{ext}` 형상에 맞지 않는다. server.py:447 이 그 파서로만
    uid/analysisId 를 복원하므로 fixtures 키는 라우팅 자체가 불가하다.
    원래 이 doc 들을 만든 경로가 `sweep_phase15.py --trigger direct-process` 이고,
    그것이 하는 일이 정확히 `pipeline._process(bucket, sourceS3Key, uid, analysisId)` 다.
    같은 함수를 같은 인자 형상으로 호출한다 — 분기 0.
    """
    pipeline = _load_pipeline()
    rc = 0
    for aid in ids:
        ref = db.document(f"users/{UID}/analyses/{aid}")
        doc0 = ref.get().to_dict() or {}
        key = doc0.get("videoKey")
        if not key:
            print(f"중단: {aid} videoKey 부재 — fail-closed", file=sys.stderr)
            return 2
        prev_updated = doc0.get("updatedAt")
        prev_score = (doc0.get("result") or {}).get("overallScore")
        print(f"\n[{aid}] key={key} prevScore={prev_score} prevUpdatedAt={prev_updated}",
              file=sys.stderr, flush=True)
        t0 = time.time()
        try:
            pipeline._process(BUCKET, key, UID, aid)
        except Exception as exc:  # noqa: BLE001 - 사유를 남기고 중단 (강제 상태변경 0)
            print(f"  _process FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 3
        d = ref.get().to_dict() or {}
        res = d.get("result") or {}
        print(f"  _process OK ({int(time.time()-t0)}s) status={d.get('status')} "
              f"score={res.get('overallScore')} "
              f"cards={len(res.get('faultZoomComparisons') or [])} "
              f"userVideoSec={res.get('userVideoSec')} refVideoSec={res.get('refVideoSec')} "
              f"updatedAt={d.get('updatedAt')}", file=sys.stderr, flush=True)
        if d.get("status") != "done":
            print(f"  경고: status={d.get('status')} (done 아님)", file=sys.stderr)
            rc = 4
        if d.get("updatedAt") == prev_updated:
            print("  경고: updatedAt 미변동 — 재산출이 실제로 일어났는지 확인 필요",
                  file=sys.stderr)
            rc = 5
    return rc


def do_collect(db, ids: list[str], out_dir: Path, keys_out: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    all_keys: list[str] = []
    for aid in ids:
        doc = db.document(f"users/{UID}/analyses/{aid}").get().to_dict() or {}
        (out_dir / f"{aid}.json").write_text(
            json.dumps(doc, ensure_ascii=False, default=str)
        )
        res = doc.get("result") or {}
        for c in res.get("faultZoomComparisons") or []:
            # presigned URL 은 7일 만료 — S3 키를 재구성해 저장한다.
            crit = c.get("criterion")
            if crit:
                all_keys.append(f"results/{UID}/{aid}/zoom_{crit}.png")
                all_keys.append(f"results/{UID}/{aid}/zoom_adv_{crit}.png")
        s = _summary(aid, doc)
        print(f"  [{aid}] status={s['status']} score={s['overallScore']} "
              f"cards={s['faultZoomCards']} userVideoSec={s['userVideoSec']} "
              f"refVideoSec={s['refVideoSec']}", file=sys.stderr)
    keys_out.write_text("\n".join(all_keys))
    print(f"\nPNG 후보 키 {len(all_keys)}개 → {keys_out}", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--backup", action="store_true")
    g.add_argument("--reanalyze", action="store_true")
    g.add_argument("--reprocess-direct", dest="reprocess_direct", action="store_true")
    g.add_argument("--collect", action="store_true")
    ap.add_argument("--ids", nargs="+", default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=Path("/workspace/docs_before"))
    ap.add_argument("--keys-out", type=Path, default=Path("/workspace/zoom_keys.txt"))
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    db = fa._db()
    if args.list:
        return do_list(db, args.out)
    if not args.ids:
        ap.error("--ids 필요")
    if args.backup:
        return do_backup(db, args.ids, args.out_dir)
    if args.reanalyze:
        return do_reanalyze(db, args.ids, args.timeout)
    if args.reprocess_direct:
        return do_reprocess_direct(db, args.ids)
    return do_collect(db, args.ids, args.out_dir, args.keys_out)


if __name__ == "__main__":
    sys.exit(main())
