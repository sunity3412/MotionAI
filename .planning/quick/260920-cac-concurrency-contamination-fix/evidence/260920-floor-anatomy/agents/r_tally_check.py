"""반증 R1 — 주장의 소비처 표 [6]/[15] 를 운영 deduction_engine.tally() 로 다시 낸다.

주장의 d_consumer_spread.py 는 tally() 를 호출하지 않고 감점식을 손으로 다시 썼다
(상수만 import). 여기서는 md 를 만들어 **운영 tally() 에 그대로 넣는다**.
"""
from __future__ import annotations
import json, sys, collections
import numpy as np
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
from sunity_shared.analysis import deduction_engine, ipsf_criteria  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_KEYS  # noqa: E402

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
TOL, SLOPE, CAPC = ipsf_criteria._ANGLE_TOLERANCE_DEG, ipsf_criteria._SLOPE, ipsf_criteria._ANGLE_CAP
CAPR, CAPE, FL = (deduction_engine.PER_RECORD_DEDUCTION_CAP,
                  deduction_engine.EXECUTION_DEDUCTION_CAP, deduction_engine.SCORE_FLOOR)


class Q:  # quantification stub — status 'ok', reach substrate 없음
    quantificationStatus = "ok"
    bodyRelativeNotches = None
    windowMedianAngleDeltas = None


class FC:  # Gemini 무지목 (fault_context)
    supported_differences = ()


def hand(dev):  # 주장이 쓴 손-산식 그대로
    pts = [min(round(min((v - TOL) * SLOPE, CAPC), 1), CAPR) for v in dev if v - TOL > 0]
    return int(max(FL, round(100 - min(CAPE, sum(pts))))), len(pts)


def engine(dev):  # 운영 tally()
    md = {f"angle_vs_reference__{jk}": float(v) for jk, v in zip(JOINT_KEYS, dev)
          if np.isfinite(v) and v > 0.0}
    b = deduction_engine.tally(
        Q(), FC(), dimension_overall=100.0, measured_deviations=md,
        dimension_scores={}, baseline_kind="floor",
    )
    return int(b.final), len(b.records)


rows = json.load(open(f"{D}/facts.json"))
by = collections.defaultdict(list)
for r in rows:
    if r.get("dev") and all(np.isfinite(r["dev"])):
        by[(r["ref"], r["label"])].append(r)

out, P = [], None
out = []
P = out.append
P("=" * 96)
P("R1. 소비처 표를 운영 deduction_engine.tally() 로 재산출 — 손-산식과 대조")
P("=" * 96)
P(f"{'동작':24s}{'라벨':8s}{'n':>4s}{'손final':>9s}{'엔진final':>10s}{'불일치':>8s}{'rec수 불일치':>12s}")
mismatch_f = mismatch_r = total = 0
tbl = {}
for m in ["ref-kip-up", "ref-peter-pan", "ref-power-spin", "ref-climb",
          "ref-elbow-twist-sister", "ref-pdshape", "ref-sideway-spin",
          "ref-combo", "ref-invert", "ref-foxtop", "ref-foxtop-split"]:
    for lab in ("correct", "fault", "self"):
        rs = by.get((m, lab))
        if not rs:
            continue
        hf, ef, dm, dr = [], [], 0, 0
        for r in rs:
            a, an = hand(r["dev"]); b, bn = engine(r["dev"])
            hf.append(a); ef.append(b)
            dm += (a != b); dr += (an != bn)
        total += len(rs); mismatch_f += dm; mismatch_r += dr
        tbl[(m, lab)] = float(np.median(ef))
        P(f"{m:24s}{lab:8s}{len(rs):4d}{np.median(hf):9.0f}{np.median(ef):10.0f}"
          f"{dm:8d}{dr:12d}")
P("")
P(f"전체 {total}건 — final 불일치 {mismatch_f}건, record수 불일치 {mismatch_r}건")
P("")
P("격차(fault중앙 − correct중앙, 엔진 산출):")
for m in ["ref-kip-up", "ref-peter-pan", "ref-power-spin", "ref-climb",
          "ref-elbow-twist-sister", "ref-pdshape"]:
    c, f = tbl.get((m, "correct")), tbl.get((m, "fault"))
    if c is not None and f is not None:
        P(f"  {m:24s} correct {c:5.0f}  fault {f:5.0f}   격차 {f-c:+.0f}")
txt = "\n".join(out)
open(f"{D}/out/r_tally_check.txt", "w").write(txt + "\n")
print(txt)
