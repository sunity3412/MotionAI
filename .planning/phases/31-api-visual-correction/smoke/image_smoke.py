"""31-01 Task 2 — 이미지 편집 모델 스모크 실호출 (D-03 모델 확정 근거).

목적: `wan2.7-image-pro`(1순위) vs `qwen-image-edit-plus`(폴백)을 동일 fixture·동일 프롬프트로
실호출해 (a) 이미지 편집 모드 지원 여부, (b) latency, (c) usage/과금 단위, (d) 모더레이션 차단률,
(e) **async taskId 지원 여부**를 실측한다. (e)가 릴리스 게이트다 — 4차 리뷰 B4-02:
v1 은 async-only 이므로 sync 전용 모델이 chosen 이면 RESULTS.json.blocked=true.

제약 (계획서 Task 2 + threat_model):
- T-31-01: 키는 SSM `/sunity/motion/dashscope-api-key` → env 경유만. 리터럴·stdout 로깅 금지.
  presigned URL 도 로깅하지 않는다(서명 포함).
- T-31-02: 산출 이미지는 **세션 scratch 전용**. `.planning` 하위 저장 금지.
- T-31-03: MAX_CALLS=8 (모델당 4). belle 승인 상한(privacy_decision.json.spendApproval).
- 7차 H7-05: 입력 프레임은 **전용 VisualInputBucket** 에만 올린다(VideoBucket 사용 금지).
  버킷명은 `infra/visual_input_bucket.json` 단일 출처에서 읽는다(하드코딩 금지 — 8차 H8-07).
  각 호출 종료 후 exact key delete_object + HEAD 404 검증.

사용:
    python3 image_smoke.py --fixtures-dir <scratch>/fixtures --out-dir <scratch>/smoke_out
    python3 image_smoke.py ... --dry-run     # 과금 호출 0, 배선만 검증

엔드포인트 근거 (2026-07-20 alibabacloud.com/help/en/model-studio 조회):
- wan2.7-image-pro : POST /api/v1/services/aigc/image-generation/generation
                     + header X-DashScope-Async: enable → output.task_id
                     → GET /api/v1/tasks/{task_id} 폴링 (SUCCEEDED/FAILED)
- qwen-image-edit-plus : POST /api/v1/services/aigc/multimodal-generation/generation (동기)
공통 body: input.messages[0].content = [{"image": <url>}, {"text": <prompt>}]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).parent
PHASE_DIR = HERE.parent
BUCKET_MANIFEST = PHASE_DIR / "infra" / "visual_input_bucket.json"

SSM_KEY_NAME = "/sunity/motion/dashscope-api-key"
AWS_PROFILE = "sunity-motion"

BASE = "https://dashscope-intl.aliyuncs.com"
WAN_CREATE = f"{BASE}/api/v1/services/aigc/image-generation/generation"
QWEN_CREATE = f"{BASE}/api/v1/services/aigc/multimodal-generation/generation"
TASK_URL = f"{BASE}/api/v1/tasks/{{task_id}}"

# T-31-03 지출 가드 — belle 승인 상한. 초과 시 하드 스톱.
MAX_CALLS = 8
MAX_CALLS_PER_MODEL = 4

S3_SMOKE_PREFIX = "visual-input/_smoke"
PRESIGN_EXPIRES_S = 3600  # 1h (계획서 Task 2)
POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 300

# fixture 4종 — 직립1 / 도립1 / 좌1 / 우1 (계획서 Task 2).
# targetDeg 는 육안 판정 기준값이며 정밀 실측은 31-13 harness 가 RTMW 로 수행한다.
FIXTURES = [
    {
        "id": "chair-spin-upright-left-knee",
        "file": "Chair-spin.png",
        "jointKey": "left_knee",
        "targetDeg": 175,
        "category": ["upright", "left"],
        "prompt": (
            "Correct the athlete's left knee to full extension (about 175 degrees), "
            "straightening the trailing leg. Keep the person's identity, face, hair, "
            "clothing, the vertical pole, and the background unchanged."
        ),
    },
    {
        "id": "invert-inverted-left-knee",
        "file": "invert.png",
        "jointKey": "left_knee",
        "targetDeg": 175,
        "category": ["inverted", "left", "motion_blur"],
        "prompt": (
            "Correct the athlete's left knee to full extension (about 175 degrees) "
            "in this inverted pose. Keep the person's identity, face, hair, clothing, "
            "the vertical pole, and the background unchanged."
        ),
    },
    {
        "id": "power-spin-inverted-right-knee",
        "file": "power-spin.png",
        "jointKey": "right_knee",
        "targetDeg": 175,
        "category": ["inverted", "right", "occlusion"],
        "prompt": (
            "Correct the athlete's right knee to full extension (about 175 degrees), "
            "straightening the leg that is bent behind the pole. Keep the person's "
            "identity, face, hair, clothing, the vertical pole, and the background unchanged."
        ),
    },
    {
        "id": "sideway-spin-upright-right-knee",
        "file": "sideway-spin.png",
        "jointKey": "right_knee",
        "targetDeg": 175,
        "category": ["upright", "right", "occlusion"],
        "prompt": (
            "Correct the athlete's right knee to full extension (about 175 degrees), "
            "straightening the tucked leg away from the pole. Keep the person's identity, "
            "face, hair, clothing, the vertical pole, and the background unchanged."
        ),
    },
]

MODELS = [
    {"name": "wan2.7-image-pro", "mode": "async", "url": WAN_CREATE},
    {"name": "qwen-image-edit-plus", "mode": "sync", "url": QWEN_CREATE},
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def bucket_name() -> str:
    """8차 H8-07 — 버킷명 단일 출처. 하드코딩 금지."""
    d = json.loads(BUCKET_MANIFEST.read_text())
    return d["bucketName"]


def load_api_key() -> str:
    """T-31-01 — SSM SecureString → 메모리. 값은 어디에도 출력하지 않는다."""
    env = os.environ.get("DASHSCOPE_API_KEY")
    if env:
        return env
    out = subprocess.run(
        ["aws", "ssm", "get-parameter", "--name", SSM_KEY_NAME,
         "--with-decryption", "--profile", AWS_PROFILE,
         "--query", "Parameter.Value", "--output", "text"],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.strip()


def s3_put_and_presign(local: Path, key: str, bucket: str) -> str:
    subprocess.run(
        ["aws", "s3", "cp", str(local), f"s3://{bucket}/{key}",
         "--profile", AWS_PROFILE, "--quiet"],
        check=True,
    )
    out = subprocess.run(
        ["aws", "s3", "presign", f"s3://{bucket}/{key}",
         "--expires-in", str(PRESIGN_EXPIRES_S), "--profile", AWS_PROFILE],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.strip()  # 반환값은 로깅 금지 (서명 포함)


def s3_delete_and_verify(key: str, bucket: str) -> bool:
    """exact key 삭제 + HEAD 404 검증 (7차 H7-05)."""
    subprocess.run(
        ["aws", "s3api", "delete-object", "--bucket", bucket, "--key", key,
         "--profile", AWS_PROFILE],
        check=False, capture_output=True,
    )
    head = subprocess.run(
        ["aws", "s3api", "head-object", "--bucket", bucket, "--key", key,
         "--profile", AWS_PROFILE],
        check=False, capture_output=True, text=True,
    )
    return head.returncode != 0  # 404 = 삭제 확인


def http_json(url: str, key: str, body: dict | None = None,
              async_header: bool = False) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body else "GET")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    if async_header:
        req.add_header("X-DashScope-Async", "enable")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"_raw": raw[:500]}


def build_body(model: str, image_url: str, prompt: str) -> dict:
    return {
        "model": model,
        "input": {"messages": [{"role": "user", "content": [
            {"image": image_url},
            {"text": prompt},
        ]}]},
        "parameters": {"n": 1, "watermark": False, "prompt_extend": False},
    }


def extract_image_urls(payload: dict) -> list[str]:
    out = payload.get("output", {})
    urls: list[str] = []
    for ch in out.get("choices", []) or []:
        for c in ch.get("message", {}).get("content", []) or []:
            if isinstance(c, dict) and c.get("image"):
                urls.append(c["image"])
    return urls


def is_moderation(payload: dict) -> bool:
    blob = json.dumps(payload, ensure_ascii=False).lower()
    return any(t in blob for t in
               ("data_inspection", "prohibited", "content_policy", "inappropriate", "risk"))


def run_one(model: dict, fx: dict, image_url: str, api_key: str,
            out_dir: Path) -> dict:
    """단발 호출 1건. async 여부·latency·usage·모더레이션을 기록한다."""
    rec: dict = {
        "model": model["name"], "fixture": fx["id"], "jointKey": fx["jointKey"],
        "declared_mode": model["mode"], "async_task_id_returned": False,
        "http_status": None, "latency_s": None, "usage": None,
        "moderation_blocked": False, "ok": False, "saved_image": None, "error": None,
    }
    t0 = time.time()
    body = build_body(model["name"], image_url, fx["prompt"])
    status, payload = http_json(model["url"], api_key, body,
                                async_header=(model["mode"] == "async"))
    rec["http_status"] = status

    task_id = payload.get("output", {}).get("task_id")
    if task_id:
        rec["async_task_id_returned"] = True
        deadline = time.time() + POLL_TIMEOUT_S
        while time.time() < deadline:
            time.sleep(POLL_INTERVAL_S)
            st_code, payload = http_json(TASK_URL.format(task_id=task_id), api_key)
            tstat = payload.get("output", {}).get("task_status")
            if tstat in ("SUCCEEDED", "FAILED", "CANCELED", "UNKNOWN"):
                rec["task_status"] = tstat
                break
        else:
            rec["error"] = "poll_timeout"

    rec["latency_s"] = round(time.time() - t0, 1)
    rec["usage"] = payload.get("usage")
    rec["moderation_blocked"] = is_moderation(payload)

    urls = extract_image_urls(payload)
    if urls:
        dest = out_dir / f"{model['name']}__{fx['id']}.png"
        try:
            urllib.request.urlretrieve(urls[0], dest)
            rec["saved_image"] = str(dest)   # scratch 경로만 (T-31-02)
            rec["ok"] = True
        except Exception as e:  # noqa: BLE001 - 다운로드 실패는 기록 후 계속
            rec["error"] = f"download_failed: {type(e).__name__}"
    elif not rec["error"]:
        rec["error"] = (payload.get("message")
                        or json.dumps(payload.get("output", {}), ensure_ascii=False)[:300]
                        or f"http_{status}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    fx_dir = Path(args.fixtures_dir)
    out_dir = Path(args.out_dir)
    if str(out_dir.resolve()).startswith(str(PHASE_DIR.resolve())):
        log("FATAL: out-dir 이 .planning 하위다 — T-31-02 위반. scratch 경로를 쓸 것.")
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    bucket = bucket_name()
    log(f"bucket={bucket} fixtures={len(FIXTURES)} models={len(MODELS)} MAX_CALLS={MAX_CALLS}")

    if args.dry_run:
        for m in MODELS:
            for fx in FIXTURES:
                assert (fx_dir / fx["file"]).exists(), f"fixture 없음: {fx['file']}"
                build_body(m["name"], "https://example.invalid/x.png", fx["prompt"])
        log("dry-run OK — 배선/fixture 검증 완료, 과금 호출 0")
        return 0

    api_key = load_api_key()
    run_id = uuid.uuid4().hex[:12]
    calls = 0
    records: list[dict] = []
    uploaded: list[str] = []

    try:
        for fx in FIXTURES:
            key = f"{S3_SMOKE_PREFIX}/{run_id}/{fx['file']}"
            s3_put_and_presign(fx_dir / fx["file"], key, bucket)  # 업로드
            uploaded.append(key)

        for model in MODELS:
            per_model = 0
            for fx in FIXTURES:
                if calls >= MAX_CALLS or per_model >= MAX_CALLS_PER_MODEL:
                    log(f"상한 도달 — {model['name']} 중단 (calls={calls})")
                    break
                key = f"{S3_SMOKE_PREFIX}/{run_id}/{fx['file']}"
                url = s3_put_and_presign(fx_dir / fx["file"], key, bucket)
                calls += 1
                per_model += 1
                log(f"call {calls}/{MAX_CALLS}: {model['name']} <- {fx['id']}")
                rec = run_one(model, fx, url, api_key, out_dir)
                records.append(rec)
                log(f"  status={rec['http_status']} async={rec['async_task_id_returned']} "
                    f"ok={rec['ok']} {rec['latency_s']}s err={rec['error']}")
    finally:
        deleted = {k: s3_delete_and_verify(k, bucket) for k in set(uploaded)}
        log(f"S3 정리: {sum(deleted.values())}/{len(deleted)} HEAD 404 확인")

    raw = out_dir / "raw_calls.json"
    raw.write_text(json.dumps(
        {"run_id": run_id, "calls_used": calls, "max_calls": MAX_CALLS,
         "bucket": bucket, "s3_cleanup_verified": all(deleted.values()) if uploaded else None,
         "records": records}, ensure_ascii=False, indent=1))
    log(f"완료 — calls={calls}/{MAX_CALLS}, raw={raw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
