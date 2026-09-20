"""C3 step6 — 875 전수에 oracle 정렬을 걸고 §13 과 같은 분산분해를 다시 돌린다.

§13: 운영 편차의 79% 를 '어느 동작이냐'가 정한다.
질문: 정렬을 완벽하게(도달 가능한 하한까지) 해도 그 몫이 남나?
"""
from __future__ import annotations
import json, sys, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD

facts = {r["id"]: r for r in json.load(open(f"{D}/facts.json"))}
students = H.load_students(); refs = H.load_references()
rows = []; t0 = time.time()
for i, s in enumerate(students):
    rdoc = refs.get(s["ref"])
    f = facts.get(s["id"])
    if rdoc is None or f is None or not np.isfinite(f["scalar"]):
        continue
    U = H.student_matrix(s); A = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    u_seg = U[f["ustart"]:f["uend"]]; a_win = A[f["rstart"]:f["rend"]]
    dif = np.abs(u_seg[:, None, :] - a_win[None, :, :])
    best_r = np.argmin(np.nansum(dif ** 2, axis=2), axis=1)
    p = [(u, int(best_r[u])) for u in range(u_seg.shape[0])]
    dev = MD.per_joint_deviation(p, u_seg, a_win, ref_fps=fps)
    rows.append(dict(id=s["id"], ref=s["ref"], label=f["label"],
                     dev_dtw=f["scalar"], dev_oracle=H.scalar(dev), overall=f["overall"]))
    if (i + 1) % 200 == 0:
        print(f"  {i+1}/{len(students)} {time.time()-t0:.0f}s", flush=True)
json.dump(rows, open(f"{D}/out/c3_full_oracle.json", "w"))
print(f"완료 {len(rows)} {time.time()-t0:.0f}s\n")

for name, key in (("운영 DTW 정렬", "dev_dtw"), ("oracle 정렬(정렬 상한)", "dev_oracle")):
    g = {}
    for r in rows:
        g.setdefault(r["ref"], []).append(r[key])
    ratio, tab = H.variance_decomposition(g)
    print(f"[{name}] 동작내 분산 = {ratio*100:.0f}%   ->  동작이 정하는 몫 = {(1-ratio)*100:.0f}%")

print()
print("== 동작별 바닥: 운영 vs oracle (correct/self = 실력차 0 바닥) ==")
print(f"{'motion':24s}{'label':8s}{'n':>5s}{'dtw':>8s}{'oracle':>8s}{'정렬몫%':>9s}")
import collections
by = collections.defaultdict(list)
for r in rows:
    by[(r["ref"], r["label"])].append(r)
floor_pairs = []
for k in sorted(by):
    if k[1] not in ("correct", "self"):
        continue
    rs = by[k]
    a = float(np.median([x["dev_dtw"] for x in rs]))
    b = float(np.median([x["dev_oracle"] for x in rs]))
    floor_pairs.append((k[0], a, b))
    print(f"{k[0]:24s}{k[1]:8s}{len(rs):>5d}{a:>8.1f}{b:>8.1f}{100*(a-b)/a:>9.0f}")

from scipy.stats import spearmanr  # noqa
a = [x[1] for x in floor_pairs]; b = [x[2] for x in floor_pairs]
print(f"\n바닥 순위 상관(운영 vs oracle) Spearman rho = {spearmanr(a,b).statistic:+.3f}  n={len(a)}")
print(f"바닥 편차폭(최대/최소): 운영 {max(a)/min(a):.1f}배 -> oracle {max(b)/min(b):.1f}배")

print()
print("== 소비처 확인: 편차 스칼라 vs 저장된 overallScore (동작 내부) ==")
for m in sorted({r["ref"] for r in rows}):
    rs = [r for r in rows if r["ref"] == m and r["overall"] is not None]
    if len(rs) < 8:
        continue
    x = np.array([r["dev_dtw"] for r in rs], float); y = np.array([r["overall"] for r in rs], float)
    if x.std() == 0 or y.std() == 0:
        print(f"  {m:24s} n={len(rs):4d}  (분산 0 — 상관 미정)"); continue
    print(f"  {m:24s} n={len(rs):4d}  r(dev, overallScore) = {np.corrcoef(x,y)[0,1]:+.3f}")
