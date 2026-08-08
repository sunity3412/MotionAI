"""E 저더 재현성 검사 — 같은 입력의 두 렌더(FAIL본 vs PASS본)에서 이벤트 수 비교.

freeze 구간은 mp4 자체에서 검출(긴 정지 run)해 재생 구간을 역산한다 —
report.json 이 없는 PASS본도 같은 잣대로 잴 수 있게.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))
from sunity_shared.analysis import compare_verify as cv  # noqa: E402

SP = Path("/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
          "662d3ac6-6a65-4779-a98a-b26d8c1f988f/scratchpad")


def scan(mp4: Path, label: str):
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([cv.FF, "-y", "-loglevel", "error", "-i", str(mp4),
                    "-vf", "fps=30,scale=360:-2", str(tmp / "%05d.png")], check=True)
    paths = sorted(tmp.glob("*.png"))
    imgs = [np.asarray(Image.open(p).convert("L"), dtype=float) for p in paths]
    half = imgs[0].shape[1] // 2
    out = {}
    for name, sl in (("user", slice(None, half)), ("ref", slice(half, None))):
        diffs = np.array([np.mean(np.abs(b[:, sl] - a[:, sl]))
                          for a, b in zip(imgs, imgs[1:])])
        # freeze = 전체 프레임 정지(양 패널 동시) 60프레임(2s) 이상 run — 재생 구간 역산
        full = np.array([np.mean(np.abs(b - a)) for a, b in zip(imgs, imgs[1:])])
        frozen = full < 0.05
        regions, i, n = [], 0, len(frozen)
        start = 0
        while i < n:
            if frozen[i]:
                j = i
                while j < n and frozen[j]:
                    j += 1
                if j - i >= 60:  # 2s+ = freeze 구간
                    if i - start > 15:
                        regions.append((start, i))
                    start = j
                i = j
            else:
                i += 1
        if n - start > 15:
            regions.append((start, n))
        ev_all = []
        for (a, b) in regions:
            seg = diffs[a:b]
            if len(seg) < 3:
                continue
            for t in cv.stutter_stop_events(seg):
                ev_all.append(round(a / 30.0 + t, 2))
        out[name] = (len(ev_all), cv.worst_stutter_window(sorted(ev_all)), sorted(ev_all))
    print(f"[{label}] 재생구간 {len(regions)}개")
    for name, (tot, worst, ts) in out.items():
        flag = "FAIL" if worst >= cv.STUTTER_FAIL_COUNT else "PASS"
        print(f"  {name}: total={tot} worst2s={worst} -> {flag}  times={ts[:12]}")
    return out


scan(SP / "p34fail" / "compare.mp4", "run1 (리그 FAIL 판정본)")
scan(SP / "p34ok.mp4", "run2 (리그 PASS 판정본, S3 부착본)")
