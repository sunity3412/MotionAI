"""E 저더 이벤트 위치 실측 — FAIL mp4 에서 어느 절대 초에 스터터가 잡히는지.

리그 코드(compare_verify verify E 절)와 동일 절차를 복제하되, 이벤트의
**절대 출력 초**를 함께 뽑는다 (리그는 개수만 보고한다).
"""
import json
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
          "662d3ac6-6a65-4779-a98a-b26d8c1f988f/scratchpad/p34fail")
mp4 = SP / "compare.mp4"
report = json.loads((SP / "report.json").read_text())
actual = float(report["outDurationS"])
regions = cv.playback_regions(report, actual)
print("재생 구간:", [(round(a, 2), round(b, 2)) for a, b in regions])

tmp = Path(tempfile.mkdtemp())
allev = {"user": [], "ref": []}
for (rs, re_) in regions:
    if re_ - rs < 0.5:
        continue
    for f in tmp.glob("*.png"):
        f.unlink()
    subprocess.run([cv.FF, "-y", "-loglevel", "error", "-ss", str(rs), "-t", str(re_ - rs),
                    "-i", str(mp4), "-vf", "fps=30,scale=360:-2", str(tmp / "%04d.png")],
                   check=True)
    imgs = [np.asarray(Image.open(p).convert("L"), dtype=float)
            for p in sorted(tmp.glob("*.png"))]
    if len(imgs) < 3:
        continue
    half = imgs[0].shape[1] // 2
    for label, sl in (("user", slice(None, half)), ("ref", slice(half, None))):
        diffs = np.array([np.mean(np.abs(b[:, sl] - a[:, sl]))
                          for a, b in zip(imgs, imgs[1:])])
        ev = cv.stutter_stop_events(diffs)
        for t in ev:
            allev[label].append(round(rs + t, 2))
        if ev:
            print(f"  구간 {rs:.1f}~{re_:.1f} {label}: 이벤트 {len(ev)}건 "
                  f"@절대초 {[round(rs + t, 2) for t in ev]}")
            # 그 구간 diff 프로파일 요약
            print(f"    diffs: median={np.median(diffs):.3f} p85={np.percentile(diffs,85):.3f} "
                  f"min={diffs.min():.3f} max={diffs.max():.3f} n={len(diffs)}")

for label in ("user", "ref"):
    ev = sorted(allev[label])
    print(f"{label}: total={len(ev)} worst2s={cv.worst_stutter_window(ev)} times={ev}")
