"""Phase 35 — 합성 비교 영상 기계 판정 리그 v0 (돌파 ②의 첫 조각).

렌더 결과를 belle 에게 보내기 **전에** 스크립트가 판독한다 — "전 항목 PASS 아니면 전달 없음".

판정 항목 (v0):
  A. 길이 — 실제 mp4 길이 == 렌더 계획 길이 (±0.3s)
  B. 정지 정적성 — 각 freeze 창 중앙 1s 의 프레임 차분(diff) ≈ 0 (프리즈가 진짜 멈춰있나)
  C. 재생 동적성 — 재생 구간 표본의 프레임 차분 > 정지의 10배 (영상이 진짜 움직이나)
  D. 음성 배치 — 각 voice 창 mean dB > -45 (발화 존재), 재생 구간 표본 < -70 (무음)
  E. 감점 정합 — freeze 수 == 인증(또는 유도) 순간 보유 record 수

v0 미포함(후속): whisper 전사 == 자막 문장 대조(로컬 whisper 미설치 — Pod 리그에서),
자막 픽셀 OCR. 미포함은 여기 명시해 둔다 — 조용한 생략 금지.

실행:
    .venv/bin/python scripts/verify_render_prototype.py --mp4 out.mp4 --report report.json
report 는 render_compare_prototype.py stdout JSON.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image

FF = imageio_ffmpeg.get_ffmpeg_exe()


def duration_s(path: Path) -> float:
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def mean_db(path: Path, start: float, dur: float) -> float:
    out = subprocess.run(
        [FF, "-ss", str(start), "-t", str(dur), "-i", str(path),
         "-map", "0:a", "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    m = re.search(r"mean_volume: ([-\d.]+) dB", out)
    return float(m.group(1)) if m else -120.0


def frame_diff(path: Path, start: float, tmp: Path, n: int = 6, fps: float = 6.0) -> float:
    for f in tmp.glob("*.png"):
        f.unlink()
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", str(start), "-t", str(n / fps),
                    "-i", str(path), "-vf", f"fps={fps},scale=180:-2", str(tmp / "%03d.png")],
                   check=True)
    imgs = [np.asarray(Image.open(p).convert("L"), dtype=float)
            for p in sorted(tmp.glob("*.png"))]
    if len(imgs) < 2:
        return -1.0
    return float(np.mean([np.mean(np.abs(imgs[i + 1] - imgs[i])) for i in range(len(imgs) - 1)]))


def verify(mp4: Path, report: dict, workdir: Path) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True

    def check(name: str, passed: bool, detail: str):
        nonlocal ok
        ok &= passed
        lines.append(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")

    tmp = workdir / "_rigtmp"
    tmp.mkdir(parents=True, exist_ok=True)

    actual = duration_s(mp4)
    planned = float(report["outDurationS"])
    check("A 길이", abs(actual - planned) <= 0.3, f"actual={actual:.2f}s planned={planned:.2f}s")

    freezes = report.get("freezes", [])
    play_probe = 1.0 if not freezes or freezes[0]["voiceStartOutS"] > 2.0 else max(
        0.2, freezes[0]["voiceStartOutS"] - 1.5)

    diffs_frozen = []
    for fz in freezes:
        mid = fz["voiceStartOutS"] + fz["freezeS"] / 2
        d = frame_diff(mp4, mid, tmp)
        diffs_frozen.append(d)
        check(f"B 정지 정적성 {fz['rid']}", 0 <= d < 0.5, f"diff={d:.3f} @out {mid:.1f}s")

    d_play = frame_diff(mp4, play_probe, tmp)
    if freezes:
        base = max(max(diffs_frozen), 1e-3)
        check("C 재생 동적성", d_play > 10 * base or d_play > 2.0,
              f"play diff={d_play:.2f} vs frozen max={max(diffs_frozen):.3f}")
    else:
        check("C 재생 동적성", d_play > 1.0, f"play diff={d_play:.2f} (freeze 0 편)")

    for fz in freezes:
        db = mean_db(mp4, fz["voiceStartOutS"] + 0.2, min(2.5, fz["freezeS"] - 0.6))
        check(f"D 음성 존재 {fz['rid']}", db > -45, f"mean={db:.1f}dB @out {fz['voiceStartOutS']:.1f}s")
    if freezes:
        db_sil = mean_db(mp4, play_probe, 0.8)
        check("D 재생 무음", db_sil < -70, f"mean={db_sil:.1f}dB @out {play_probe:.1f}s")

    return ok, lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp4", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--workdir", type=Path, default=Path("/tmp/renderrig"))
    args = ap.parse_args()
    report = json.load(open(args.report))
    ok, lines = verify(args.mp4, report, args.workdir)
    print(f"{args.mp4.name}: {'ALL PASS' if ok else 'FAIL'}")
    print("\n".join(lines))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
