#!/usr/bin/env python3
"""P35 신선 doc 드라이버 — climb·climbfault·combo 3건, SIM_UID 직접 _process (Pod 전용).

quick-260816-c3m. belle 질문("pdshape, 파워스핀, 엘보하고있고, 피터팬 하고 있고,
킵업이랑 콤보 남은건가?")에 답하기 위한 재료 생산 — climb·combo 를 다음 발굴
스윕(discover_sweep.py, quick-260814-ehz-5) 대상에 올리려면 P35 렌더 입력 데이터
(doc.json+align.json)가 먼저 있어야 한다. phase34_fresh_reanalysis.py 의
SIM_UID·direct-process 선례를 그대로 재사용한다 — 새 분석 경로 0,
pipeline._process 직접 호출(sweep_phase15.py --trigger direct-process 와 동일
정신, source 는 fixtures/ 원본 그대로 넘겨 uploads/ COPY 0).

Pod 실행 (프로젝트 /workspace/SunityMotion — NLF 는 torch.cuda.is_available()
자동감지라 RTMW_DEVICE 불필요, align.json 재추출은 p35_extract_align.py 몫):
    cd /workspace/SunityMotion/backend && source /workspace/aws_env.sh && \
    python3 scripts/p35_new_motion_docs.py --outdir /workspace/p35

로컬 dry-run (Firestore/S3/GPU 접촉 0 — identity self-check 만):
    backend/.venv/bin/python backend/scripts/p35_new_motion_docs.py \
      --outdir .planning/quick/260816-c3m-climb-combo-p35/.dryrun --dry-run
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
for _p in (BACKEND / "shared" / "python", BACKEND):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# belle 의 실 Firebase 계정이 아니다 — phase34_fresh_reanalysis.py 의 SIM_UID
# 리터럴 그대로 재사용 (T-c3m-01 mitigate, 파일럿 내부 sim 계정). belle 실uid
# 문자열은 이 파일에 절대 등장시키지 않는다(Task 3 verify 가 grep 으로 강제).
SIM_UID = "fvcNXzEqKjgqVxRPVSj1iwFnIpn2"
DEFAULT_BUCKET = "sunity-motion-pilot-videos"

# slot(p35_extract_align.py 의 JOBS 키와 반드시 동일) -> (sourceS3Key, referenceMotionId).
# S3 실물 확인(2026-08-16 head-object): climb correct 40.9MB, climb fault 31.6MB,
# combo correct 318MB/61.98초(2160x3840 30fps — ffprobe 실측, fault.mp4 는 S3 부재라
# correct 1건만 처리). 동작명을 리터럴로 분기하는 코드는 0 — 아래는 전부 이 표
# 순회로만 처리한다.
ITEMS: dict[str, tuple[str, str]] = {
    "climb": ("fixtures/phase15/climb/correct.mp4", "ref-climb"),
    "climbfault": ("fixtures/phase15/climb/fault.mp4", "ref-climb"),
    "combo": ("fixtures/phase15/combo/correct.mp4", "ref-combo"),
}


def _load_pipeline_module():
    """pipeline app.py 를 경로 import.

    phase34_fresh_reanalysis.py `_load_pipeline_module` / sweep_phase15.py
    `_load_pipeline` 와 동일 패턴 — 새 분석 로직 0, 기존 `_process` 재사용
    (RESEARCH Anti-Pattern "Writing a new analysis path" 금지).
    """
    path = BACKEND / "functions" / "pipeline" / "app.py"
    spec = importlib.util.spec_from_file_location("pipeline_app_p35new", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fresh_analysis_id(slot: str) -> str:
    """영숫자 전용 analysisId (sweep_phase15.py _self_check_identities 규율 —
    s3keys.py:18 의 [A-Za-z0-9]+ 를 통과해야 하므로 하이픈/언더스코어 절대 금지)."""
    analysis_id = f"p35new{slot}{int(time.time())}"
    if not re.match(r"^[A-Za-z0-9]+$", analysis_id):
        raise RuntimeError(
            f"analysisId {analysis_id!r} 가 영숫자([A-Za-z0-9]+)가 아님 — "
            "슬롯명에 비영숫자 문자가 섞였다 (sweep_phase15.py 규율 위반)"
        )
    return analysis_id


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--outdir", required=True, type=Path)
    p.add_argument("--bucket", default=DEFAULT_BUCKET)
    p.add_argument(
        "--slots", default=",".join(ITEMS),
        help="쉼표구분 slot 부분집합 (기본 ITEMS 전체)",
    )
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    slots = [s.strip() for s in args.slots.split(",") if s.strip()]
    unknown = [s for s in slots if s not in ITEMS]
    if unknown:
        print(
            f"ERROR: 알 수 없는 slot {unknown} (ITEMS 키: {list(ITEMS)})",
            file=sys.stderr,
        )
        return 2

    if args.dry_run:
        for slot in slots:
            source_key, ref_motion_id = ITEMS[slot]
            analysis_id = _fresh_analysis_id(slot)
            print(
                f"[dry-run] slot={slot} analysisId={analysis_id} "
                f"sourceS3Key={source_key} referenceMotionId={ref_motion_id}"
            )
        print("[dry-run] Firestore 쓰기 0 / _process 호출 0 / S3 접근 0")
        return 0

    from sunity_shared import firestore_admin, models

    db = firestore_admin._db()  # noqa: SLF001 - phase34_fresh_reanalysis.py 선례
    pipeline = _load_pipeline_module()

    successes: list[str] = []
    failures: list[dict] = []
    for slot in slots:
        source_key, ref_motion_id = ITEMS[slot]
        analysis_id = _fresh_analysis_id(slot)
        now = int(time.time() * 1000)
        doc = {
            "analysisId": analysis_id,
            "uid": SIM_UID,
            "mode": models.MODE_EXPERT,
            "status": models.STATUS_QUEUED,
            "videoKey": source_key,
            "videoFormat": "mp4",
            "fileSizeBytes": 0,
            "createdAt": now,
            "updatedAt": now,
            "referenceMotionId": ref_motion_id,
            "sourceLabel": f"p35_new_motion_docs:{slot}",
        }
        db.collection("users").document(SIM_UID).collection("analyses").document(
            analysis_id
        ).set(doc)
        print(
            f"[{slot}] fresh doc uid={SIM_UID} analysisId={analysis_id} "
            f"ref={ref_motion_id} source={source_key} (원본 무접촉, uploads copy 0)"
        )

        t0 = time.time()
        try:
            pipeline._process(args.bucket, source_key, SIM_UID, analysis_id)  # noqa: SLF001
        except Exception as exc:  # noqa: BLE001 - slot 실패는 다음 slot 으로 계속 진행
            dt = time.time() - t0
            failures.append({
                "slot": slot,
                "analysisId": analysis_id,
                "error": f"{type(exc).__name__}: {exc}",
                "afterSec": round(dt, 1),
            })
            print(
                f"[{slot}] _process FAILED after {dt:.1f}s: "
                f"{type(exc).__name__}: {exc}"
            )
            continue
        dt = time.time() - t0

        out = firestore_admin.get_analysis(SIM_UID, analysis_id) or {}
        if out.get("status") != models.STATUS_DONE:
            failures.append({
                "slot": slot,
                "analysisId": analysis_id,
                "error": f"status={out.get('status')!r} (STATUS_DONE 아님)",
                "afterSec": round(dt, 1),
            })
            print(
                f"[{slot}] _process 완료 {dt:.1f}s 이나 "
                f"status={out.get('status')} (DONE 아님)"
            )
            continue

        slot_dir = args.outdir / slot
        slot_dir.mkdir(parents=True, exist_ok=True)
        # Firestore Timestamp 대비 default=str.
        (slot_dir / "doc.json").write_text(
            json.dumps(out, ensure_ascii=False, default=str)
        )
        n_records = len(
            ((out.get("result") or {}).get("deductionBreakdown") or {}).get(
                "records"
            )
            or []
        )
        successes.append(slot)
        print(f"[{slot}] _process 완료 {dt:.1f}s status=done records={n_records}")

    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2))
        print(f"성공 {len(successes)}/{len(slots)}: {successes}")
        return 1
    print(f"전체 성공 {len(successes)}/{len(slots)}: {successes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
