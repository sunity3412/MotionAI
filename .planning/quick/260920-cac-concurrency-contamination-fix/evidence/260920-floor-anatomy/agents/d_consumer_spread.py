"""조사 D — 소비처 분포 (중앙값 한 점이 아니라 분석 하나하나)."""
from __future__ import annotations
import json, sys, collections
import numpy as np
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
from sunity_shared.analysis import ipsf_criteria, deduction_engine  # noqa: E402

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
TOL, SLOPE, CAPC = ipsf_criteria._ANGLE_TOLERANCE_DEG, ipsf_criteria._SLOPE, ipsf_criteria._ANGLE_CAP
CAPR, CAPE, FL = (deduction_engine.PER_RECORD_DEDUCTION_CAP,
                  deduction_engine.EXECUTION_DEDUCTION_CAP, deduction_engine.SCORE_FLOOR)
rows = json.load(open(f"{D}/facts.json"))
by = collections.defaultdict(list)
for r in rows:
    if r.get("dev") and all(np.isfinite(r["dev"])):
        by[(r["ref"], r["label"])].append(r)


def pts(dev):
    return [min(round(min((v - TOL) * SLOPE, CAPC), 1), CAPR) for v in dev if v - TOL > 0]


out = []
P = out.append
P("=" * 104)
P("15. 소비처 분포 — 분석 875건 하나하나에 운영 감점식 적용")
P(f"    record 0건 = 그 분석은 이 축에서 감점이 하나도 안 난다 (화면 100점)")
P("=" * 104)
P(f"{'동작':24s}{'라벨':9s}{'n':>4s}{'record0건 비율':>15s}{'최대관절dev 중앙':>17s}"
  f"{'final 중앙':>11s}{'final 범위':>14s}")
for m in ["ref-kip-up", "ref-peter-pan", "ref-power-spin", "ref-climb",
          "ref-elbow-twist-sister", "ref-pdshape", "ref-sideway-spin",
          "ref-combo", "ref-invert", "ref-foxtop", "ref-foxtop-split"]:
    for lab in ("correct", "fault", "self"):
        rs = by.get((m, lab))
        if not rs:
            continue
        zero = sum(1 for r in rs if not pts(r["dev"]))
        fin = [max(FL, round(100 - min(CAPE, sum(pts(r["dev"]))))) for r in rs]
        mx = [max(r["dev"]) for r in rs]
        P(f"{m:24s}{lab:9s}{len(rs):4d}{zero/len(rs)*100:14.0f}%{np.median(mx):17.1f}"
          f"{np.median(fin):11.0f}{f'{min(fin):.0f}~{max(fin):.0f}':>14s}")
    P("")
txt = "\n".join(out)
open(f"{D}/out/d_consumer_spread.txt", "w").write(txt + "\n")
print(txt)
