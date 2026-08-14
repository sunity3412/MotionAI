"""GPT 2번째 교사 단건 테스트 — Gemini가 놓친 영상에 GPT가 결함을 잡는지.

프레임 추출(ffmpeg) + OpenAI 비전(urllib 직접 HTTP, SDK 우회) + 교사 프롬프트 재사용.
사용: relabel_venv/bin/python gpt_teacher_test.py <rows.jsonl> <motion_substr> [model]
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.join(os.getcwd(), "backend", "training"))
from distill import gemini_teacher as gt  # noqa: E402


def s3_download(uri, dest):
    import boto3
    bucket, key = uri[len("s3://"):].split("/", 1)
    boto3.client("s3", region_name="ap-northeast-2").download_file(bucket, key, dest)


def _duration(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", video],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def extract_frames(video, n=16):
    # 전체 구간에 걸쳐 고르게 n장 추출(앞부분 준비 구간만 뽑히는 문제 방지).
    d = tempfile.mkdtemp()
    dur = _duration(video)
    fps = max(0.25, n / dur) if dur > 0 else 2.0
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", video,
         "-vf", f"fps={fps:.4f},scale=512:-1", "-frames:v", str(n),
         os.path.join(d, "f%02d.jpg")],
        check=True,
    )
    frames = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".jpg"))
    return frames[:n]


def openai_vision(api_key, model, system, user_text, frame_paths):
    content = [{"type": "text", "text": user_text}]
    for fp in frame_paths:
        b64 = base64.b64encode(open(fp, "rb").read()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": content}],
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        out = json.loads(resp.read())
    ch = out["choices"][0]
    content = ch["message"].get("content")
    if not content:
        print(f"[debug] finish_reason={ch.get('finish_reason')} "
              f"refusal={ch['message'].get('refusal')} usage={out.get('usage')}", flush=True)
    return content


def main():
    rows_path, motion_sub = sys.argv[1], sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "gpt-4o"
    import boto3
    api_key = boto3.client("ssm", region_name="ap-northeast-2").get_parameter(
        Name="/sunity/motion/openai-api-key", WithDecryption=True)["Parameter"]["Value"].strip()

    row = None
    for l in open(rows_path):
        r = json.loads(l)
        u = next(m for m in r["messages"] if m["role"] == "user")
        uri = next(p["video"] for p in u["content"] if isinstance(p, dict) and p.get("type") == "video")
        if motion_sub.lower() in uri.lower():
            coords_txt = next(p["text"] for p in u["content"] if isinstance(p, dict) and p.get("type") == "text")
            coords, _ = json.JSONDecoder().raw_decode(coords_txt[len("RTMW_Data:"):].strip())
            old = json.loads(next(m["content"] for m in r["messages"] if m["role"] == "assistant"))
            row = (uri, coords, r.get("_motion"), old)
            break
    if not row:
        print("행 못 찾음"); return
    uri, coords, motion, old = row
    print(f"영상: {uri}  motion={motion}  Gemini 기존 fault={len(old.get('faults') or [])}", flush=True)

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False); tmp.close()
    s3_download(uri, tmp.name)
    frames = extract_frames(tmp.name, 12)
    print(f"프레임 {len(frames)}장 추출", flush=True)
    system = gt.build_teacher_system_prompt(gt.DEFAULT_TASK_JOINTS, motion=motion)
    user_text = gt.build_rtmw_text(coords) + (
        "\n\n위 영상 프레임과 좌표를 근거로 결함을 짚어 JSON 리포트를 출력하세요."
    )
    print(f"=== GPT({model}) 호출 ===", flush=True)
    raw = openai_vision(api_key, model, system, user_text, frames)
    try:
        rep = json.loads(raw)
        faults = rep.get("faults") or []
        print(f"GPT fault 개수: {len(faults)}", flush=True)
        for f in faults:
            if isinstance(f, dict):
                print(f"  - {f.get('body_part')} / {f.get('fault_category')} / {str(f.get('measurement_basis',''))[:60]}")
        print("coaching:", str(rep.get("coaching"))[:200])
    except Exception as e:
        print("파싱 실패:", str(e)[:100], "raw앞부분:", raw[:300])
    os.remove(tmp.name)


if __name__ == "__main__":
    main()
