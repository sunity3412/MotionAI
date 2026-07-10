"""bake-off 평가 미니셋 RTMW 좌표 사전 추출 (22-06 실행부 — Pod system python 전용).

run_bakeoff 의 real/hard_negative 트랙은 학습 JSONL 과 동일 표현의 RTMW 좌표
(pod_coords 단일 owner)를 입력으로 쓴다. 학습 venv(train_venv)에는 onnxruntime-gpu/
rtmlib 가 없으므로(서빙 의존성 충돌 회피 — setup_training_pod.sh 참조) 좌표 추출은
**system python**(서빙 스택 보유)으로 이 스크립트를 선행 실행해 캐시를 채운다.

Gemini 무접촉(과금 0). S3 재다운로드 없음 — setup 이 prefetch 한
BAKEOFF_FIXTURES_DIR 로컬 파일만 읽는다 (read-only). SERIAL — 동시성 비안전
([[pipeline-not-concurrency-safe-eval-serial]]).

실행 (Pod, full_batch 와 동일 env):
    cd /workspace/SunityMotion/backend
    LD_LIBRARY_PATH=/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib:\
/usr/local/lib/python3.11/dist-packages/nvidia/cublas/lib \
    RTMW_ONNX_PATH=/workspace/rtmw_weights/rtmw-x-384.onnx \
    YOLOX_ONNX_PATH=/workspace/yolox_weights/yolox_m.onnx \
    RTMW_DEVICE=cuda \
    PYTHONPATH=shared/python:training:. python3 evals/phase22/extract_eval_coords.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent.parent
for _p in (BACKEND / "shared" / "python", BACKEND, BACKEND / "training"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from distill import pod_coords  # noqa: E402 — 좌표 표현/캐시 단일 owner.

MANIFEST_PATH = HERE / "fixtures" / "manifest.yaml"


def main() -> int:
    fixtures_dir = Path(os.environ.get("BAKEOFF_FIXTURES_DIR") or "/workspace/bakeoff_fixtures")
    cache_dir = os.environ.get("BAKEOFF_COORDS_CACHE") or "/workspace/phase22_coords_cache"
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))

    reports: list[dict] = []
    for item in manifest.get("items") or []:
        s3_key = item.get("s3_key")
        if not s3_key:
            continue  # synthetic/trap/hard_negative(relocate pending) — 영상 없음.
        key = pod_coords.coords_cache_key({"s3_key": s3_key})
        if pod_coords.load_cached_coords(cache_dir, key) is not None:
            reports.append({"id": item.get("id"), "cache_key": key, "status": "cached"})
            continue
        local = fixtures_dir / s3_key
        rep: dict = {"id": item.get("id"), "cache_key": key}
        if not local.exists():
            rep.update(status="missing_video", note=str(local))
            reports.append(rep)
            continue
        try:
            summary = pod_coords.extract_and_cache(str(local), cache_dir, key)
            rep.update(status="extracted", **summary)
        except Exception as exc:  # noqa: BLE001 - 항목 오류는 집계(배치 지속).
            rep.update(status="error", error=str(exc)[:200])
        reports.append(rep)
        print(f"[coords] {item.get('id')}: {rep.get('status')}", flush=True)

    print(json.dumps(reports, ensure_ascii=False, indent=2))
    missing = [r for r in reports if r.get("status") in ("missing_video", "error")]
    print(f"[summary] total={len(reports)} missing/error={len(missing)}", flush=True)
    print("ALLDONE", flush=True)
    return 0 if not missing else 3


if __name__ == "__main__":
    sys.exit(main())
