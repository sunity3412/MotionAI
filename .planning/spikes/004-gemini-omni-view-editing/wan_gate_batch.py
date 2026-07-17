"""Spike 008 — Wan2.7-VideoEdit (DashScope) 카메라 앵글 게이트.

Omni(004-iii-b)와 동일 10건·동일 프롬프트·동일 측정. 입력 = S3 presigned URL.
비동기: create task → 15s 폴링 → video_url 다운로드(24h 유효 — 즉시 저장).
journal(wan_out/journal.json) 멱등 재개. 키 = SSM /sunity/motion/dashscope-api-key.

사용: python3 wan_gate_batch.py [--only power-spin]  (스모크 = --only)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
GATE_IN = HERE / "gate_in"
WAN_OUT = HERE / "wan_out"
JOURNAL = WAN_OUT / "journal.json"

BASE = "https://dashscope-intl.aliyuncs.com"
CREATE = f"{BASE}/api/v1/services/aigc/video-generation/video-synthesis"
TASK = f"{BASE}/api/v1/tasks/{{task_id}}"

PROMPT = (
    "Rotate the camera 90 degrees to view the performer from her left side. "
    "Keep the performer's pose, body positions, motion and timing exactly identical "
    "to the original video. Do not change the speed, the pole position, or the room. "
    "Only the camera viewpoint changes."
)

CLIPS = [
    "power-spin", "sideway-spin", "peter-pan", "elbow-twist-sister", "Chair-spin",
    "Diamond-Spin", "sliding-spin", "invert", "kip-up", "straddle-invert",
]

S3_PREFIX = "s3://sunity-motion-pilot-videos/_eval-tmp/spike008"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def http_json(url: str, key: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body else "GET")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    if body is not None:
        req.add_header("X-DashScope-Async", "enable")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def presign(name: str) -> str:
    key = f"{S3_PREFIX}/{name}.mp4"
    subprocess.run(
        ["aws", "s3", "cp", str(GATE_IN / f"{name}.mp4"), key,
         "--profile", "sunity-motion", "--quiet"],
        check=True,
    )
    out = subprocess.run(
        ["aws", "s3", "presign", key, "--expires-in", "86400", "--profile", "sunity-motion"],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.strip()


def main() -> None:
    api_key = os.environ["DASHSCOPE_API_KEY"]
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    WAN_OUT.mkdir(exist_ok=True)
    journal = json.loads(JOURNAL.read_text()) if JOURNAL.exists() else {}

    for name in CLIPS:
        if only and name != only:
            continue
        e = journal.get(name, {})
        out_path = WAN_OUT / f"{name}.mp4"
        if e.get("status") == "done" and out_path.exists():
            log(f"{name}: skip (done)")
            continue
        try:
            task_id = e.get("task_id")
            if not task_id:
                url = presign(name)
                body = {
                    "model": "wan2.7-videoedit",
                    "input": {
                        "prompt": PROMPT,
                        "media": [{"type": "video", "url": url}],
                    },
                    "parameters": {"resolution": "720P", "watermark": False,
                                   "prompt_extend": False, "seed": 42},
                }
                r = http_json(CREATE, api_key, body)
                task_id = r["output"]["task_id"]
                journal[name] = {"status": "created", "task_id": task_id}
                JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=1))
                log(f"{name}: task {task_id}")
            t0 = time.time()
            while True:
                r = http_json(TASK.format(task_id=task_id), api_key)
                st = r["output"]["task_status"]
                if st == "SUCCEEDED":
                    vurl = r["output"]["video_url"]
                    urllib.request.urlretrieve(vurl, out_path)
                    usage = r.get("usage", {})
                    journal[name] = {"status": "done", "task_id": task_id,
                                     "elapsed_s": round(time.time() - t0, 1),
                                     "usage": usage,
                                     "out_mb": round(out_path.stat().st_size / 1e6, 2)}
                    JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=1))
                    log(f"{name}: done {journal[name]['out_mb']}MB usage={usage}")
                    break
                if st in ("FAILED", "CANCELED", "UNKNOWN"):
                    msg = json.dumps(r.get("output", {}), ensure_ascii=False)[:300]
                    journal[name] = {"status": "error", "task_id": task_id, "error": msg}
                    JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=1))
                    log(f"{name}: {st} {msg}")
                    break
                if time.time() - t0 > 900:
                    log(f"{name}: timeout (task_id 보존 — 재실행 시 이어 폴링)")
                    break
                time.sleep(15)
        except Exception as ex:  # noqa: BLE001 - 항목 단위 기록 후 계속
            journal[name] = {**journal.get(name, {}), "status": "error", "error": str(ex)[:300]}
            JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=1))
            log(f"{name}: ERROR {ex}")

    done = [k for k, v in journal.items() if v.get("status") == "done"]
    log(f"finished: {len(done)} done -> {sorted(done)}")


if __name__ == "__main__":
    main()
