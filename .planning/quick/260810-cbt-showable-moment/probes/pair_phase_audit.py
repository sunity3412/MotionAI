"""후보 프레임이 정말 "같은 국면"인가 — 짝거리 분포 + 양쪽 각도 실값 (관찰 전용).

`showable_moment.py` 1차가 후보를 찾긴 했는데 최선 후보의 차이가 125~168도로 나왔다.
08-09 에 폐기된 "최대 차이 순간"(전부 다른 국면/깨진 포즈)과 같은 크기다. 그래서
정렬 게이트가 실제로 무엇을 통과시키는지 먼저 본다:

  · 승인본 정지 순간의 짝거리 `pd0` 가 클립 분포에서 어디인가
  · 최선 후보에서 **양쪽 각도의 실값**(|차이| 아니라 a_user, a_ref) — 175 대 46 이면
    "같은 결함이 더 크게" 가 아니라 다른 국면이다
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import compare_render as cr  # noqa: E402

ROOT = REPO / ".planning/phases/35-server-rendered-comparison-video/data"


def run(case: str):
    d = ROOT / case
    doc = json.load(open(d / "doc.json"))
    align = json.load(open(d / "align.json"))
    curve = align.get("curveRefSec")
    pairs = align.get("pairs") or {}
    if not curve:
        return
    afps = float(align["fps"])
    uF = int(align["userFrames"])
    try:
        u_at, r_at = cr._kp_reader(align, "user"), cr._kp_reader(align, "ref")
    except (KeyError, ValueError):
        return

    # 클립 전체 짝거리 분포 (DTW 곡선을 따라)
    pds = []
    for i in range(uF):
        pd = cr._pose_dist(u_at, r_at, i / afps, float(curve[i]))
        if pd is not None:
            pds.append(pd)
    if not pds:
        return
    q = np.percentile(pds, [0, 10, 25, 50, 75, 100])
    print(f"\n=== {case} ===  DTW 곡선 짝거리 분포 "
          f"min {q[0]:.3f} / p10 {q[1]:.3f} / p25 {q[2]:.3f} / "
          f"중앙 {q[3]:.3f} / p75 {q[4]:.3f} / max {q[5]:.3f}   (n={len(pds)})")

    for rec in (doc["result"].get("deductionBreakdown") or {}).get("records") or []:
        crit = rec.get("criterion") or ""
        if "angle_vs_reference__" not in crit:
            continue
        jk = crit.split("__", 1)[1]
        if jk not in cr._ANGLE_TRIPLES:
            continue
        rid = (rec.get("recordId") or "").split(":")[0]
        pair = pairs.get(rid)
        if not pair:
            continue
        ut0, rt0 = float(pair["atVideoSec"]), float(pair["refVideoSec"])
        pd0 = float(pair["poseDist"])
        pct = 100.0 * sum(1 for p in pds if p <= pd0) / len(pds)
        a0 = cr._joint_angle(u_at, jk, ut0, conf_min=cr.KP_CONF_MIN)
        b0 = cr._joint_angle(r_at, jk, rt0, conf_min=cr.KP_CONF_MIN)
        print(f"  {rid} {jk:<15} 승인 짝거리 {pd0:.3f} = 클립 상위 {pct:.0f}% 안 "
              f"| 각도 나 {'-' if a0 is None else f'{a0:.1f}'} 대 정은지 "
              f"{'-' if b0 is None else f'{b0:.1f}'}")

        # 정렬 상위 10% 안에서만 최대 차이 — "같은 국면" 을 강하게 요구
        thr = float(q[1])
        best = None
        rows = []
        for i in range(uF):
            ut, rt = i / afps, float(curve[i])
            a = cr._joint_angle(u_at, jk, ut, conf_min=cr.KP_CONF_MIN)
            b = cr._joint_angle(r_at, jk, rt, conf_min=cr.KP_CONF_MIN)
            if a is None or b is None:
                continue
            pd = cr._pose_dist(u_at, r_at, ut, rt)
            if pd is None or pd > thr:
                continue
            rows.append((abs(a - b), ut, rt, a, b, pd))
        if rows:
            rows.sort(reverse=True)
            print(f"      정렬 p10({thr:.3f}) 이하 후보 {len(rows)}개 — 상위 3:")
            for dv, ut, rt, a, b, pd in rows[:3]:
                print(f"        {ut:6.2f}s ↔ {rt:5.2f}s  차이 {dv:5.1f}도 "
                      f"(나 {a:5.1f} 대 {b:5.1f})  짝거리 {pd:.3f}")
            med = statistics.median([r[0] for r in rows])
            print(f"      그 안 차이 중앙값 {med:.1f}도")
        else:
            print(f"      정렬 p10({thr:.3f}) 이하 후보 0개")


if __name__ == "__main__":
    cases = sys.argv[1:] or sorted(p.name for p in ROOT.iterdir()
                                   if p.is_dir() and (p / "align.json").exists())
    for c in cases:
        run(c)
