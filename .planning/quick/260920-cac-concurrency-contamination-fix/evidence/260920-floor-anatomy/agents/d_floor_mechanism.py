"""조사 D 보강 — 바닥을 지는 관절이 '어떤 관절'인가, 그 관절의 무엇이 바닥을 정하나.

가설 (b): 그 관절이 그 동작에서 많이 움직일수록 시간정렬 오차가 |Δ각도| 로 증폭된다.
  -> 관절별 바닥 vs 기준 시퀀스의 그 관절 각도 변동폭(sd / IQR / 프레임간 변화율).
운영 함수만 사용: harness.ref_matrix (= 기준 doc angles reshape, 운영 _deviation_against 입력과 동일).
"""
from __future__ import annotations
import json, sys, collections
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

JK = H.JOINT_KEYS
SHORT = {"left_elbow": "L-elb", "right_elbow": "R-elb", "left_shoulder": "L-sho",
         "right_shoulder": "R-sho", "left_hip": "L-hip", "right_hip": "R-hip",
         "left_knee": "L-kne", "right_knee": "R-kne"}

rows = json.load(open(f"{D}/facts.json"))
refs = H.load_references()
students = {s["id"]: s for s in H.load_students()}

by = collections.defaultdict(list)
for r in rows:
    if r.get("dev") and all(np.isfinite(r["dev"])):
        by[(r["ref"], r["label"])].append(r)

out = []
P = out.append
P("=" * 100)
P("7. 관절별 바닥 vs 그 관절의 기준 시퀀스 각도 변동폭")
P("   floor  = correct(없으면 self) 라벨의 그 관절 median |Δ| (도)")
P("   ref_sd = 기준 doc angles 그 관절 열의 표준편차 (도)  <- 그 동작에서 그 관절이 얼마나 움직이나")
P("   ref_iqr= 같은 열의 IQR,  ref_step = 프레임간 |변화| 의 median (도/프레임)")
P("=" * 100)
pool = []
for m in sorted({r["ref"] for r in rows}):
    rd = refs.get(m)
    if rd is None:
        continue
    rs = by.get((m, "correct")) or by.get((m, "self"))
    if not rs:
        continue
    lab = "correct" if by.get((m, "correct")) else "self"
    A = H.ref_matrix(rd)
    P(f"\n{m}  (바닥 라벨={lab}, n={len(rs)}, 기준 프레임 {A.shape[0]})")
    P(f"  {'관절':>8s}{'floor':>8s}{'ref_sd':>9s}{'ref_iqr':>9s}{'ref_step':>10s}")
    fl, sd, iq, st = [], [], [], []
    for j, jk in enumerate(JK):
        f = float(np.median([r["dev"][j] for r in rs]))
        col = A[:, j]; col = col[np.isfinite(col)]
        s = float(np.std(col)); q = float(np.percentile(col, 75) - np.percentile(col, 25))
        p = float(np.median(np.abs(np.diff(col)))) if col.size > 1 else float("nan")
        fl.append(f); sd.append(s); iq.append(q); st.append(p)
        P(f"  {SHORT[jk]:>8s}{f:8.1f}{s:9.1f}{q:9.1f}{p:10.2f}")
        pool.append((m, jk, f, s, q, p))
    r_sd = np.corrcoef(fl, sd)[0, 1]
    r_iq = np.corrcoef(fl, iq)[0, 1]
    r_st = np.corrcoef(fl, st)[0, 1]
    P(f"  동작 내 8관절 상관: floor~ref_sd r={r_sd:+.2f}  floor~ref_iqr r={r_iq:+.2f}  floor~ref_step r={r_st:+.2f}")

F = np.array([p[2] for p in pool]); S = np.array([p[3] for p in pool])
Q = np.array([p[4] for p in pool]); T = np.array([p[5] for p in pool])
ok = np.isfinite(F) & np.isfinite(S) & np.isfinite(Q) & np.isfinite(T)
P("")
P(f"전체 pool (동작x관절 {int(ok.sum())}쌍) 상관:")
P(f"  floor ~ ref_sd   r={np.corrcoef(F[ok], S[ok])[0,1]:+.2f}   (설명력 R^2={np.corrcoef(F[ok],S[ok])[0,1]**2*100:.0f}%)")
P(f"  floor ~ ref_iqr  r={np.corrcoef(F[ok], Q[ok])[0,1]:+.2f}")
P(f"  floor ~ ref_step r={np.corrcoef(F[ok], T[ok])[0,1]:+.2f}   (설명력 R^2={np.corrcoef(F[ok],T[ok])[0,1]**2*100:.0f}%)")

# 관절이 동작을 넘어 체계적으로 바닥을 지는가 (관절 고유 문제인가)
P("")
P("=" * 100)
P("8. 그 관절이 동작을 넘어 체계적으로 바닥을 지는가 — 동작 안에서의 순위(1=가장 큼) 평균")
P("   관절 고유 문제(예: 무릎 추정이 늘 나쁘다)면 순위가 동작마다 일정해야 한다")
P("=" * 100)
rank = collections.defaultdict(list)
for m in sorted({p[0] for p in pool}):
    vals = {p[1]: p[2] for p in pool if p[0] == m}
    order = sorted(vals, key=lambda k: -vals[k])
    for i, jk in enumerate(order):
        rank[jk].append(i + 1)
P(f"  {'관절':>8s}{'평균순위':>10s}{'sd':>7s}{'n동작':>7s}   동작별 순위")
for jk in sorted(rank, key=lambda k: np.mean(rank[k])):
    a = np.array(rank[jk])
    P(f"  {SHORT[jk]:>8s}{a.mean():10.2f}{a.std():7.2f}{len(a):7d}   {list(a)}")
P("  (무작위면 평균순위 4.5, sd ~2.3)")

txt = "\n".join(out)
open(f"{D}/out/d_floor_mechanism.txt", "w").write(txt + "\n")
print(txt)
