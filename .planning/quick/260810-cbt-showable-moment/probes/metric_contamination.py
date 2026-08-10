"""`편차 ÷ 요동` 지표가 fps 라벨 오차에 오염됐는가 (관찰 전용).

08-09 의 `signal_vs_deviation.py` 는 감점마다 (편차 ÷ 그 순간 요동)을 재서 20건 중
17건을 "묻힘"으로 판정했다. 그 계산의 두 입력이 모두 라벨 fps 를 쓴다:

  · 창의 **중심** = `atFrameIdx × 2` (record 9fps → report 18fps 가정)
  · 창의 **폭**   = `0.5 × report fps(18)` 프레임

실제는 report 트랙이 ~19.99fps(솎음 step 3 뒤 ×2 업샘플)이므로 중심이 최대 ~1.1초
어긋나고 창 폭도 ~10% 짧다. 여기서는 같은 지표를 **교정 앵커·교정 폭**으로 다시 재서
판정이 뒤집히는 건수를 센다. 뒤집히면 그 지표로 시스템을 고칠 수 없다.

usage: metric_contamination.py <video_dir> [case...]
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

ROOT = REPO / ".planning/phases/35-server-rendered-comparison-video/data"
TARGET_FPS = 9.0
BURIED = 0.10          # 08-09 판정선
SWING_HALF_S = 0.5
TRIPLE = {"elbow": ("shoulder", "elbow", "hand"), "knee": ("hip", "knee", "ankle"),
          "shoulder": ("elbow", "shoulder", "hip"), "hip": ("shoulder", "hip", "knee")}
USER_VIDEO = {"pdshapefault": "pdshapefault1785373695.mp4",
              "peterpan": "peterpanfault1785373695.mp4",
              "elbow": "elbow_fault.mp4", "powerspin": "powerspin_fault.mp4"}


def angle(rep, i, side, tri):
    p = [fz._kp_xy(rep, i, f"{side}_{n}") for n in tri]
    if not all(p):
        return None
    v1 = (p[0][0] - p[1][0], p[0][1] - p[1][1])
    v2 = (p[2][0] - p[1][0], p[2][1] - p[1][1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return None
    c = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(c))


def swing(rep, n, center: float, half_frames: int, side, tri):
    lo, hi = max(0, int(round(center)) - half_frames), min(n, int(round(center)) + half_frames + 1)
    vals = [angle(rep, i, side, tri) for i in range(lo, hi)]
    vals = [v for v in vals if v is not None]
    return (max(vals) - min(vals)) if len(vals) >= 5 else None


def src_fps(v: Path) -> float:
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=avg_frame_rate", "-of", "csv=p=0",
                        str(v)], capture_output=True, text=True, check=True).stdout.strip()
    a, b = o.split("/")
    return float(a) / float(b)


def run(vdir: Path, case: str):
    doc = json.load(open(ROOT / case / "doc.json"))
    res = doc["result"]
    rep = res.get("keypointReport") or {}
    if not rep:
        return []
    n = int(rep.get("frames") or 0)
    label_fps = float(rep.get("fps") or 18.0)
    vid = vdir / USER_VIDEO.get(case, "")
    if not vid.exists():
        return []
    s = src_fps(vid)
    pose_fps = s / max(1, round(s / TARGET_FPS))       # 실제 솎음 rate
    up = round(label_fps / TARGET_FPS)                 # report = pose 트랙의 정수배 업샘플
    real_rep_fps = pose_fps * up
    rows = []
    for rec in (res.get("deductionBreakdown") or {}).get("records") or []:
        crit, at, dev = (rec.get("criterion") or ""), rec.get("atFrameIdx"), rec.get("deviation")
        if at is None or dev is None or "angle_vs_reference__" not in crit:
            continue
        jk = crit.split("__", 1)[1]
        side, part = jk.split("_", 1)
        tri = TRIPLE.get(part)
        if not tri:
            continue
        # 08-09 판정 (라벨 기준)
        sw_old = swing(rep, n, at * up, int(round(SWING_HALF_S * label_fps)), side, tri)
        # 교정 (앵커·폭 모두 실제 rate)
        sw_new = swing(rep, n, at * up, int(round(SWING_HALF_S * real_rep_fps)), side, tri)
        r_old = (float(dev) / sw_old) if sw_old else None
        r_new = (float(dev) / sw_new) if sw_new else None
        flip = ""
        if r_old is not None and r_new is not None:
            if (r_old < BURIED) != (r_new < BURIED):
                flip = "  ★판정 뒤집힘"
        rows.append((case, (rec.get("recordId") or "").split(":")[0], jk, float(dev),
                     sw_old, sw_new, r_old, r_new, flip))
    print(f"\n=== {case} ===  report 라벨 {label_fps:.1f}fps / 실제 {real_rep_fps:.2f}fps "
          f"(창 폭 {int(round(SWING_HALF_S*label_fps))} → "
          f"{int(round(SWING_HALF_S*real_rep_fps))} 프레임)")
    for r in rows:
        print(f"  {r[1]:<5}{r[2]:<15}편차{r[3]:6.1f}도  요동 "
              f"{'-' if r[4] is None else f'{r[4]:5.0f}'} → "
              f"{'-' if r[5] is None else f'{r[5]:5.0f}'}도   비율 "
              f"{'-' if r[6] is None else f'{r[6]:.3f}'} → "
              f"{'-' if r[7] is None else f'{r[7]:.3f}'}{r[8]}")
    return rows


if __name__ == "__main__":
    vdir = Path(sys.argv[1])
    allr = []
    for c in (sys.argv[2:] or ["elbow", "pdshapefault", "peterpan", "powerspin"]):
        allr.extend(run(vdir, c))
    fl = [r for r in allr if r[8]]
    b_old = [r for r in allr if r[6] is not None and r[6] < BURIED]
    b_new = [r for r in allr if r[7] is not None and r[7] < BURIED]
    print(f"\n{len(allr)}건 — '묻힘' 판정 라벨기준 {len(b_old)}건 → 교정기준 {len(b_new)}건, "
          f"뒤집힘 {len(fl)}건")
    print("주의: 이 표는 창 **폭** 교정만 반영한다. 창 **중심**(=표시 순간) 교정은 "
          "corrected_pairs.py 가 다루며, 지표의 앵커가 최대 1.1초 어긋난다는 사실 자체가 "
          "이 지표를 belle 판정과 대조하기 전에 먼저 고쳐야 하는 이유다.")
