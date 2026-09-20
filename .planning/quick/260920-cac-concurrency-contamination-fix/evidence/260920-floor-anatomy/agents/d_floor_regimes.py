"""조사 D 요약 — 바닥에 두 체제가 있는가 (관절따라 도는 바닥 vs 평평한 받침대)."""
from __future__ import annotations
import json, sys, collections
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
from sunity_shared.analysis import ipsf_criteria, deduction_engine  # noqa: E402

TOL, SLOPE = ipsf_criteria._ANGLE_TOLERANCE_DEG, ipsf_criteria._SLOPE
CAPR, CAPE, FLOOR = (deduction_engine.PER_RECORD_DEDUCTION_CAP,
                     deduction_engine.EXECUTION_DEDUCTION_CAP, deduction_engine.SCORE_FLOOR)
rows = json.load(open(f"{D}/facts.json"))
refs = H.load_references()
by = collections.defaultdict(list)
for r in rows:
    if r.get("dev") and all(np.isfinite(r["dev"])):
        by[(r["ref"], r["label"])].append(r)


def final_of(dev):
    tot = 0.0
    for v in dev:
        over = v - TOL
        if over > 0:
            tot += min(round(min(over * SLOPE, ipsf_criteria._ANGLE_CAP), 1), CAPR)
    return max(FLOOR, round(100.0 - min(CAPE, tot)))


out = []
P = out.append
P("=" * 122)
P("9. 바닥의 두 체제 — 관절 구성이 '동작을 따라 도는가(기울기)' 대 '평평한 받침대인가'")
P("   floor      = 실력차0 라벨(correct 우선, 없으면 self)의 8관절 median|Δ| 의 중앙값 (도)")
P("   CV         = 그 8개 관절값의 변동계수(sd/mean). 작을수록 전 관절 고르게 = 평평한 받침대")
P("   r(floor,sd)= 동작 내 8관절에서 floor 와 기준 각도 sd 의 상관. +면 많이 움직이는 관절이 큰 바닥")
P("   tol초과    = 실력차0 상태에서 이미 운영 tol 20도를 넘는 관절 수 / 8")
P("   final(c/f) = 운영 감점식으로 계산한 화면 점수 (angle_vs_reference 계열만)")
P("=" * 122)
P(f"{'동작':24s}{'라벨':8s}{'floor':>7s}{'CV':>7s}{'r(floor,sd)':>13s}{'tol초과':>8s}"
  f"{'refFrames':>11s}{'refFps':>8s}{'DTWdist':>9s}{'final_c':>9s}{'final_f':>9s}{'격차':>7s}")
recs = []
for m in sorted(refs):
    rc, rf = by.get((m, "correct")), by.get((m, "fault"))
    base = rc or by.get((m, "self"))
    if not base:
        continue
    lab = "correct" if rc else "self"
    fl = np.array([np.median([r["dev"][j] for r in base]) for j in range(8)])
    A = H.ref_matrix(refs[m])
    sd = np.array([np.nanstd(A[:, j]) for j in range(8)])
    r = float(np.corrcoef(fl, sd)[0, 1])
    fps = H.ref_fps_of(refs[m])
    dtw = float(np.median([x["dtw"] for x in base]))
    fc = float(np.median([final_of(x["dev"]) for x in base]))
    ff = float(np.median([final_of(x["dev"]) for x in rf])) if rf else float("nan")
    gap = fc - ff if rf else float("nan")
    recs.append((m, float(np.median(fl)), float(fl.std() / fl.mean()), r, int((fl > TOL).sum()),
                 A.shape[0], fps, dtw, fc, ff, gap))
    P(f"{m:24s}{lab:8s}{np.median(fl):7.1f}{fl.std()/fl.mean():7.2f}{r:+13.2f}"
      f"{int((fl > TOL).sum()):6d}/8{A.shape[0]:11d}{(fps or float('nan')):8.2f}{dtw:9.1f}"
      f"{fc:9.0f}{('%.0f' % ff) if rf else '-':>9s}{('%+.0f' % gap) if rf else '-':>7s}")

f_ = np.array([x[1] for x in recs]); cv = np.array([x[2] for x in recs])
rr = np.array([x[3] for x in recs]); nf = np.array([x[5] for x in recs], float)
dd = np.array([x[7] for x in recs])
P("")
P(f"동작 수준 상관 (n={len(recs)} 동작):")
P(f"  floor ~ CV            r={np.corrcoef(f_, cv)[0,1]:+.2f}   (바닥이 높을수록 관절 간 고르다=평평)")
P(f"  floor ~ r(floor,sd)   r={np.corrcoef(f_, rr)[0,1]:+.2f}   (바닥이 높을수록 관절 움직임과 무관해진다)")
P(f"  floor ~ 기준 프레임수  r={np.corrcoef(f_, nf)[0,1]:+.2f}")
P(f"  floor ~ DTW distance  r={np.corrcoef(f_, dd)[0,1]:+.2f}")

txt = "\n".join(out)
open(f"{D}/out/d_floor_regimes.txt", "w").write(txt + "\n")
print(txt)
