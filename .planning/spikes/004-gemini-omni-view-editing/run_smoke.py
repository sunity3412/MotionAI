"""Spike 004-iii-a — Omni API smoke: 폴스포츠 클립 1건 카메라 앵글 회전.

검증: Given 우리 AI Studio 키 + power-spin 8초 클립,
when gemini-omni-flash-preview 에 영상 + 앵글 회전 지시,
then 앵글 변경 영상 출력 + 지연/비용 실측.

과금: 출력 ~8-10초 × $0.10/s ≈ $1. belle 승인 완료 (2026-07-17).
실행: GEMINI_API_KEY 는 SSM /sunity/motion/gemini-api-key 에서 주입.
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

from google import genai

HERE = Path(__file__).parent
INPUT = HERE / "input_power_spin_8s.mp4"
OUT_DIR = HERE / "smoke_out"
OUT_DIR.mkdir(exist_ok=True)

PROMPT = (
    "Rotate the camera 90 degrees to view the performer from her left side. "
    "Keep the performer's pose, body positions, motion and timing exactly identical "
    "to the original video. Do not change the speed, the pole position, or the room. "
    "Only the camera viewpoint changes."
)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    client = genai.Client()
    events: list[dict] = []
    t0 = time.time()

    log(f"upload: {INPUT.name} ({INPUT.stat().st_size/1e6:.1f}MB)")
    video_file = client.files.upload(file=str(INPUT))
    while getattr(video_file.state, "name", str(video_file.state)) == "PROCESSING":
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)
    state = getattr(video_file.state, "name", str(video_file.state))
    t_upload = time.time() - t0
    events.append({"stage": "upload", "elapsed_s": round(t_upload, 1), "state": state})
    log(f"upload done state={state} elapsed={t_upload:.1f}s uri={video_file.uri}")
    if state == "FAILED":
        return 1

    t1 = time.time()
    log("interactions.create ...")
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=[
            {"type": "document", "uri": video_file.uri},
            {"type": "text", "text": PROMPT},
        ],
        response_format={"type": "video", "delivery": "uri", "aspect_ratio": "9:16"},
    )
    log(f"interaction id={getattr(interaction, 'id', '?')}")

    video_output = getattr(interaction, "output_video", None)
    if video_output is None:
        log(f"NO output_video — raw: {interaction}")
        return 2

    out_path = OUT_DIR / "power_spin_side_view.mp4"
    if getattr(video_output, "uri", None):
        file_name = video_output.uri.split("/")[-1]
        while True:
            f_info = client.files.get(name=f"files/{file_name}")
            st = getattr(f_info.state, "name", str(f_info.state))
            if st == "ACTIVE":
                break
            if st == "FAILED":
                log("generation FAILED")
                return 3
            time.sleep(5)
        video_bytes = client.files.download(file=video_output.uri)
        out_path.write_bytes(video_bytes)
    elif getattr(video_output, "data", None):
        out_path.write_bytes(base64.b64decode(video_output.data))
    else:
        log(f"output_video has neither uri nor data: {video_output}")
        return 4

    t_gen = time.time() - t1
    events.append({"stage": "generate+download", "elapsed_s": round(t_gen, 1)})
    log(f"saved {out_path} ({out_path.stat().st_size/1e6:.1f}MB) gen_elapsed={t_gen:.1f}s")

    (OUT_DIR / "smoke_log.json").write_text(
        json.dumps(
            {
                "model": "gemini-omni-flash-preview",
                "prompt": PROMPT,
                "input": INPUT.name,
                "events": events,
                "total_elapsed_s": round(time.time() - t0, 1),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
