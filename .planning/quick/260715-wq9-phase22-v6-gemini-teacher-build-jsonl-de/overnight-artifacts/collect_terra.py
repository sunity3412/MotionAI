"""phase22 v6 2교사 수집 — terra(gpt-5.6)로 distill 영상 재분석, 리포트 저장.

오늘 밤엔 병합 안 함(정합성 민감). terra 리포트만 per-video 저장 → 내일 Gemini 라벨과
union 병합. 재개가능(_video_hash 스킵) + 전체구간 프레임 + 재시도 + fault-우선 순서.

env: AWS_PROFILE=sunity-motion. OpenAI 키=SSM /sunity/motion/openai-api-key.
사용: relabel_venv/bin/python collect_terra.py <train.jsonl> <out.jsonl> [model] [max_rows]
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.join(os.getcwd(), "backend", "training"))
from distill import gemini_teacher as gt  # noqa: E402

MODEL = sys.argv[3] if len(sys.argv) > 3 else "gpt-5.6-terra"
MAX_ROWS = int(sys.argv[4]) if len(sys.argv) > 4 else 10**9
_API_KEY = None


def api_key():
    global _API_KEY
    if _API_KEY is None:
        import boto3
        _API_KEY = boto3.client("ssm", region_name="ap-northeast-2").get_parameter(
            Name="/sunity/motion/openai-api-key", WithDecryption=True)["Parameter"]["Value"].strip()
    return _API_KEY


def s3_download(uri, dest):
    import boto3
    bucket, key = uri[len("s3://"):].split("/", 1)
    boto3.client("s3", region_name="ap-northeast-2").download_file(bucket, key, dest)


def _duration(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", video], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def extract_frames(video, n=16):
    d = tempfile.mkdtemp()
    dur = _duration(video)
    fps = max(0.25, n / dur) if dur > 0 else 2.0
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", video,
         "-vf", f"fps={fps:.4f},scale=512:-1", "-frames:v", str(n),
         os.path.join(d, "f%02d.jpg")], check=True)
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".jpg"))[:n]


def call_model(system, user_text, frames, retries=4):
    content = [{"type": "text", "text": user_text}]
    for fp in frames:
        b64 = base64.b64encode(open(fp, "rb").read()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    body = {"model": MODEL, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": content}],
        "response_format": {"type": "json_object"}}
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as resp:
                out = json.loads(resp.read())
            return out["choices"][0]["message"].get("content"), out["choices"][0].get("finish_reason")
        except Exception as exc:  # noqa: BLE001 - 재시도(429/타임아웃/일시장애).
            last = str(exc)[:160]
            time.sleep(min(120, 20 * (attempt + 1)))
    return None, f"error:{last}"


def parse_row(row):
    u = next((m for m in row.get("messages", []) if m.get("role") == "user"), None)
    a = next((m for m in row.get("messages", []) if m.get("role") == "assistant"), None)
    if not u or not a:
        return None
    uri = coords = None
    for p in (u.get("content") or []):
        if isinstance(p, dict) and p.get("type") == "video":
            uri = p.get("video")
        elif isinstance(p, dict) and p.get("type") == "text" and p.get("text", "").startswith("RTMW_Data:"):
            coords, _ = json.JSONDecoder().raw_decode(p["text"][len("RTMW_Data:"):].strip())
    if not uri or coords is None:
        return None
    try:
        gem = json.loads(a.get("content", ""))
    except Exception:
        gem = {}
    return uri, coords, row.get("_motion"), row.get("_video_hash"), gem


def main():
    train_path, out_path = sys.argv[1], sys.argv[2]
    rows = [json.loads(l) for l in open(train_path)]
    distill = [r for r in rows if r.get("_track") == "distill"]

    def nf(r):
        try:
            a = next(m["content"] for m in r["messages"] if m["role"] == "assistant")
            return len(json.loads(a).get("faults") or [])
        except Exception:
            return 0
    # fault-우선 순서(미완주 시 중요한 것부터 확보).
    distill.sort(key=lambda r: -nf(r))

    done = set()
    if os.path.exists(out_path):
        for l in open(out_path):
            try:
                done.add(json.loads(l).get("_video_hash"))
            except Exception:
                pass
    print(f"[setup] model={MODEL} distill={len(distill)} 이미완료={len(done)} max={MAX_ROWS}", flush=True)

    out = open(out_path, "a", encoding="utf-8")
    joints = gt.DEFAULT_TASK_JOINTS
    n_done = n_err = 0
    for i, row in enumerate(distill):
        if n_done >= MAX_ROWS:
            break
        pr = parse_row(row)
        if not pr:
            continue
        uri, coords, motion, vh, gem = pr
        if vh in done:
            continue
        gem_nf = len(gem.get("faults") or [])
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False); tmp.close()
        try:
            s3_download(uri, tmp.name)
            frames = extract_frames(tmp.name, 16)
            system = gt.build_teacher_system_prompt(joints, motion=motion)
            user_text = gt.build_rtmw_text(coords) + (
                "\n\n위 영상 프레임과 좌표를 근거로 결함을 짚어 JSON 리포트를 출력하세요.")
            raw, fin = call_model(system, user_text, frames)
            rep = None
            if raw:
                try:
                    rep = json.loads(raw)
                except Exception:
                    rep = None
            terra_nf = len(rep.get("faults") or []) if rep else -1
            out.write(json.dumps({
                "_video_hash": vh, "s3_uri": uri, "_motion": motion,
                "gemini_fault_count": gem_nf, "terra_fault_count": terra_nf,
                "terra_report": rep, "terra_raw": None if rep else raw,
                "finish_reason": fin, "model": MODEL,
            }, ensure_ascii=False) + "\n")
            out.flush()
            if rep is None:
                n_err += 1
            n_done += 1
            print(f"  [{i+1}/{len(distill)}] {uri.split('/')[-2]} gem={gem_nf} terra={terra_nf} fin={fin}", flush=True)
        except Exception as exc:  # noqa: BLE001
            n_err += 1
            print(f"  [err] {uri}: {str(exc)[:120]}", flush=True)
        finally:
            try:
                os.remove(tmp.name)
            except OSError:
                pass
        time.sleep(0.3)
    out.close()
    print(f"\n[done] processed={n_done} errors={n_err} out={out_path}", flush=True)


if __name__ == "__main__":
    main()
