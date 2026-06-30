"""Phase 10 최종 no-FP eval — 정은지 success 영상 full pipeline → SafetyFlag 위양성 0.

POD GPU 전용 (RTMW + recognizer). belle 2026-06-30 결정: success 영상 full _process.

핵심: 정은지가 정확히 수행한(label=success) Mode-1 영상에서는 어떤 SafetyFlag 도
발화하면 안 된다 — D-02 LOCAL+TEMPORAL AND-게이트(자세 AND 통제 상실)가 통제된 고수
동작을 위양성으로 찍지 않는다는 production-faithful 증명. 한 영상에서라도 flag 가 뜨면
그 자체가 위양성 후보(belle 도메인 확인 대상)다.

real-elite (T,17,4) fixture(이미 GREEN)는 D-05 만 키포인트-레벨로 검증한다. 이 eval 은
D-02/D-03/D-04/D-06 까지 포함한 전체 SafetyFlag 레이어를 full _process 경로로 검증한다.

phase15_keys.json 의 label=='success' & mode=='mode1' 항목(정은지 정타)을 sweep_phase15
와 동일한 direct-process 경로로 돌린다. _process 가 Firestore doc 에 safetyFlags 를 쓰면
(complete_analysis, set merge) 그 doc 을 읽어 집계한다.

Usage (Pod, run_demo_sweep.sh 와 동일 env 필요 — AWS/RTMW cuda/cuDNN LD_PATH/Gemini/Cerebras/Firebase):
  cd /workspace/SunityMotion/backend
  export PYTHONPATH=shared/python:.
  python3 scripts/eval_phase10_nofp.py --keys-file scripts/phase15_keys.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import uuid
from pathlib import Path

import boto3  # noqa: F401  (env/credential sanity; firestore_admin/_process 가 사용)

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "shared" / "python"))

from sunity_shared import firestore_admin as fa, models  # noqa: E402

_EVAL_UID = "nofp10-eval"


def _load_pipeline():
    spec = importlib.util.spec_from_file_location(
        "sunity_pipeline_app", BACKEND / "functions" / "pipeline" / "app.py"
    )
    pipeline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipeline)
    pipeline._ensure_adapters()
    return pipeline


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keys-file", default=str(BACKEND / "scripts" / "phase15_keys.json"))
    ap.add_argument("--bucket", default="sunity-motion-pilot-videos")
    args = ap.parse_args()

    data = json.loads(Path(args.keys_file).read_text(encoding="utf-8"))
    items = [
        it
        for it in data.get("items", [])
        if it.get("label") == "success" and it.get("mode") == "mode1"
    ]
    if not items:
        print("success/mode1 항목 없음 — eval 대상 0", file=sys.stderr)
        return 1

    print(f"Phase 10 no-FP eval — {len(items)} success(mode1) 정은지 영상", flush=True)
    pipeline = _load_pipeline()
    db = fa._db()

    rows: list[tuple[str, object, list]] = []
    for i, it in enumerate(items, start=1):
        motion = it.get("motionId", "?")
        key = it["sourceS3Key"]
        aid = uuid.uuid4().hex[:12]
        print(f"\n[{i}/{len(items)}] {motion}  _process {key}", flush=True)
        try:
            pipeline._process(args.bucket, key, _EVAL_UID, aid)
        except Exception as exc:  # noqa: BLE001
            print(f"  _process FAILED — {type(exc).__name__}: {exc}", flush=True)
            rows.append((motion, "ERROR", [str(exc)]))
            continue
        snap = fa._doc(models.analysis_doc_path(_EVAL_UID, aid)).get()
        doc = (snap.to_dict() if snap.exists else {}) or {}
        flags = doc.get("safetyFlags") or []
        types = [f.get("flagType") for f in flags]
        print(f"  status={doc.get('status')}  safetyFlags={len(flags)}  {types}", flush=True)
        rows.append((motion, len(flags), flags))

    print("\n===== Phase 10 no-FP summary (success = 정은지 정타) =====", flush=True)
    fp = 0
    err = 0
    for motion, n, info in rows:
        if n == "ERROR":
            err += 1
            print(f"  {motion:24s} ERROR  {info[0][:80]}")
            continue
        if isinstance(n, int) and n > 0:
            fp += 1
            detail = [(f.get("flagType"), f.get("severity")) for f in info]
            print(f"  {motion:24s} {n} flag  FALSE-POSITIVE  {detail}")
        else:
            print(f"  {motion:24s} 0 flag  clean")
    print(
        f"\nFP videos: {fp}/{len(rows)} (target 0) | ERRORs: {err} | "
        f"clean: {len(rows) - fp - err}",
        flush=True,
    )
    return 0 if (fp == 0 and err == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
