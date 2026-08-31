#!/usr/bin/env python3
"""6동작 잘못된예시/잘된예시 페어 스윕 — mode1, 직렬 (파이프라인 동시성 비안전).

각 런은 backend/scripts/e2e_app_path.py (앱 동일 경로). 결과를 JSONL 로 append.
판정: 동작별 fault overall < correct overall. not_pole/no_human 실패는 그대로 기록
(안전 게이트 작동 — 점수 역전과 구분).
"""
import json
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
VID = pathlib.Path("/Users/kimtaesung/Downloads/정은지 선수 추가 영상")
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("sweep_results.jsonl")
PY = str(REPO / "backend/.venv/bin/python")
DRIVER = str(REPO / "backend/scripts/e2e_app_path.py")

JOBS = [
    # (motion, kind, video path, referenceMotionId)
    ("peter-pan", "correct", VID / "잘된 예시/fixtures:peter-pan-correct.mp4", "ref-peter-pan"),
    ("power-spin", "fault", VID / "파워스핀(잘못된예시).mp4", "ref-power-spin"),
    ("power-spin", "correct", VID / "잘된 예시/fixtures:power-spin-correct.mp4", "ref-power-spin"),
    ("climb", "fault", VID / "클라임(잘못된예시).mp4", "ref-climb"),
    ("climb", "correct", VID / "잘된 예시/fixtures:climb-correct.mp4", "ref-climb"),
    ("kip-up", "fault", VID / "킵업(잘못된예시).mp4", "ref-kip-up"),
    ("kip-up", "correct", VID / "잘된 예시/fixtures:kip-up-correct.mp4", "ref-kip-up"),
    ("elbow-twist-sister", "fault", VID / "엘보트위스트시스터(잘못된예시).mp4", "ref-elbow-twist-sister"),
    ("elbow-twist-sister", "correct", VID / "잘된 예시/fixtures:elbow-twist-sister-correct.mp4", "ref-elbow-twist-sister"),
    ("pdshape", "fault", VID / "pdshape(정확한명칭없음,잘못되예시).mp4", "ref-pdshape"),
    ("pdshape", "correct", VID / "잘된 예시/fixtures:pdshape-correct.mp4  .mp4", "ref-pdshape"),
]

def main() -> None:
    for motion, kind, video, ref in JOBS:
        assert video.exists(), f"missing video: {video}"
    for i, (motion, kind, video, ref) in enumerate(JOBS, 1):
        t0 = time.time()
        p = subprocess.run(
            [PY, DRIVER, "--video", str(video), "--mode", "mode1", "--reference", ref, "--timeout", "600"],
            capture_output=True, text=True, timeout=900,
        )
        try:
            row = json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:
            row = {"status": "driver_error", "stderr": p.stderr[-400:], "stdout": p.stdout[-200:]}
        row.update({"motion": motion, "kind": kind, "video": video.name, "reference": ref,
                    "wallSec": round(time.time() - t0)})
        with OUT.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"[{i}/{len(JOBS)}] {motion} {kind}: status={row.get('status')} elapsed={row.get('wallSec')}s", flush=True)

if __name__ == "__main__":
    main()
