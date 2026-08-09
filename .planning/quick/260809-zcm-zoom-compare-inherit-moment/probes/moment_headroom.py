"""같은 각도 근거로도 "크게 벌어지는 순간"이 클립 안에 있는가 (관찰 전용).

지금 표시 순간 = record 가 보고한 중앙값에 가장 가까운 프레임(moment.py) =
차이가 딱 평균만큼만 나는 순간. 사용자에겐 가장 안 보이는 축에 가깝다.

여기서는 DTW 짝(align.pairs)을 따라 클립 전체에서 |학생각 − 기준각| 을 재고,
표시 순간의 값과 최대값을 비교한다. 채점·표시 무접촉.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")

from sunity_shared.analysis import compare_render as cr  # noqa: E402

ROOT = Path("/Users/kimtaesung/Dev/SunityMotion/.planning/phases/"
            "35-server-rendered-comparison-video/data")


def run(case: str):
    doc = json.load(open(ROOT / case / "doc.json"))
    align = json.load(open(ROOT / case / "align.json"))
    res = doc["result"]
    u_at, r_at = cr._kp_reader(align, "user"), cr._kp_reader(align, "ref")
    afps = float(align["fps"])
    # curveRefSec[i] = 학생 프레임 i(align fps) 에 대응하는 기준 시각(초) — DTW 워핑 곡선.
    curve = align.get("curveRefSec")
    if not curve:
        print(f"{case}: curveRefSec 없음 — 건너뜀")
        return
    pairs = np.asarray([[i, float(s) * afps] for i, s in enumerate(curve)], dtype=float)

    print(f"\n=== {case} ===")
    print(f"{'관절':<16}{'점수':>7}{'표시순간차':>11}{'클립최대차':>11}{'최대순간':>10}   여유")
    for rec in (res.get("deductionBreakdown") or {}).get("records") or []:
        crit, at = rec.get("criterion") or "", rec.get("atFrameIdx")
        if at is None or "angle_vs_reference__" not in crit:
            continue
        jk = crit.split("__", 1)[1]
        if jk not in cr._ANGLE_TRIPLES:
            continue
        ut_show = float(at) / 9.0
        diffs = []
        for uf, rf in pairs:
            ut, rt = float(uf) / afps, float(rf) / afps
            a = cr._joint_angle(u_at, jk, ut)
            b = cr._joint_angle(r_at, jk, rt)
            if a is None or b is None:
                continue
            diffs.append((abs(a - b), ut, rt))
        if len(diffs) < 10:
            continue
        # 표시 순간의 차이
        idx = int(np.argmin(np.abs(pairs[:, 0] / afps - ut_show)))
        rt_show = float(pairs[idx, 1]) / afps
        a0, b0 = cr._joint_angle(u_at, jk, ut_show), cr._joint_angle(r_at, jk, rt_show)
        cur = abs(a0 - b0) if (a0 is not None and b0 is not None) else float("nan")
        diffs.sort(reverse=True)
        top = diffs[0]
        med = statistics.median([d for d, _, _ in diffs])
        ratio = top[0] / cur if cur and not math.isnan(cur) and cur > 1e-6 else float("inf")
        print(f"{jk:<16}{str(rec.get('points')):>7}{cur:>10.1f}도{top[0]:>10.1f}도"
              f"{top[1]:>9.2f}s   x{ratio:.1f}  (클립중앙 {med:.1f}도)")


if __name__ == "__main__":
    for c in sys.argv[1:]:
        run(c)
