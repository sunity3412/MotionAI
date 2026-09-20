"""R7 — 결정 실험: 같은 window 위에서 DTW 비용만 바꾼 '평범한 정렬 한 벌'이
죽은 2동작의 바닥을 얼마나 내리나, 그리고 fault 와의 분리는 어떻게 되나.

경로: 운영 window 그대로(트리밍 없음) + 단조 DTW, 비용 = 관절별 |Δ| 의 median
      (운영은 feature_vector = [각도, α·속도, β·가속] 의 L2).
      => 트리밍도 아니고 비단조 cherry-pick 도 아닌, 그냥 다른 정렬 한 벌.
편차는 운영 motiondtw.per_joint_deviation, 활성 criterion 은 운영
ipsf_criteria.criteria_from_measured_deviations.
전 그룹(대표 1건이 아니라 라벨별 전 분석)에 건다.
"""
from __future__ import annotations
import json, sys, collections, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD
from sunity_shared.analysis import ipsf_criteria as IC
TOL = IC._ANGLE_TOLERANCE_DEG

facts = {r["id"]: r for r in json.load(open(f"{D}/facts.json"))}
students = H.load_students()
refs = H.load_references()

def dtw_path(C):
    nu, nr = C.shape
    Dm = np.full((nu + 1, nr + 1), np.inf); Dm[0, 0] = 0.0
    for i in range(1, nu + 1):
        ci = C[i - 1]; prev = Dm[i - 1]
        M = np.minimum(prev[1:], prev[:-1]) + ci
        P = np.cumsum(ci); Dm[i, 1:] = P + np.minimum.accumulate(M - P)
    path = []; i, j = nu, nr
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = int(np.argmin([Dm[i-1, j-1], Dm[i-1, j], Dm[i, j-1]]))
        if k == 0: i, j = i-1, j-1
        elif k == 1: i -= 1
        else: j -= 1
    path.reverse(); return path

def over(d):
    return float(np.nansum(np.clip(np.asarray(d, float) - TOL, 0, None)))
def nact(d):
    md = {f"angle_vs_reference__{jk}": float(x) for jk, x in zip(H.JOINT_KEYS, d) if np.isfinite(x)}
    return len(IC.criteria_from_measured_deviations(md))

WANT = {("ref-elbow-twist-sister","correct"),("ref-elbow-twist-sister","fault"),
        ("ref-pdshape","correct"),("ref-pdshape","fault"),
        ("ref-kip-up","correct"),("ref-kip-up","fault"),
        ("ref-power-spin","correct"),("ref-power-spin","fault"),
        ("ref-peter-pan","correct"),("ref-peter-pan","fault")}
agg = collections.defaultdict(lambda: collections.defaultdict(list))
t0 = time.time(); n = 0
for s in students:
    f = facts.get(s["id"])
    if not f or (f["ref"], f["label"]) not in WANT:
        continue
    rdoc = refs.get(f["ref"])
    if rdoc is None: continue
    U = H.student_matrix(s); A = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    dev_op, m = H.deviate(U, rdoc)
    u_seg = U[m.start:m.end]; a_win = A[m.ref_start:m.ref_end]
    dif = np.abs(u_seg[:, None, :] - a_win[None, :, :])
    dev_med = MD.per_joint_deviation(dtw_path(np.nanmedian(dif, axis=2)), u_seg, a_win, ref_fps=fps)
    k = (f["ref"], f["label"])
    agg[k]["op_scalar"].append(H.scalar(dev_op)); agg[k]["med_scalar"].append(H.scalar(dev_med))
    agg[k]["op_over"].append(over(dev_op)); agg[k]["med_over"].append(over(dev_med))
    agg[k]["op_nact"].append(nact(dev_op)); agg[k]["med_nact"].append(nact(dev_med))
    n += 1
    if n % 50 == 0: print(f"  {n} {time.time()-t0:.0f}s", flush=True)

out = {}
print()
print("== 운영정렬 vs '비용만 바꾼 정렬'(같은 window, 단조) — 전 분석 ==")
print(f"{'motion':24s}{'lab':8s}{'n':>4s}{'스칼라 운영':>11s}{'→비용변경':>10s}"
      f"{'초과합 운영':>12s}{'→변경':>8s}{'활성 운영':>9s}{'→변경':>7s}")
for k in sorted(agg):
    a = agg[k]
    row = dict(n=len(a["op_scalar"]),
               op_scalar=float(np.median(a["op_scalar"])), med_scalar=float(np.median(a["med_scalar"])),
               op_over=float(np.median(a["op_over"])), med_over=float(np.median(a["med_over"])),
               op_nact=float(np.median(a["op_nact"])), med_nact=float(np.median(a["med_nact"])))
    out["|".join(k)] = row
    print(f"{k[0]:24s}{k[1]:8s}{row['n']:>4d}{row['op_scalar']:>11.1f}{row['med_scalar']:>10.1f}"
          f"{row['op_over']:>12.1f}{row['med_over']:>8.1f}{row['op_nact']:>9.1f}{row['med_nact']:>7.1f}")
json.dump(out, open(f"{D}/out/r7_decisive.json", "w"), indent=1)

print()
print("== 분리비(fault/correct) — 정렬을 바꾸면 분리가 좋아지나 나빠지나 ==")
for mot in sorted({k[0] for k in agg}):
    c, fl = out.get(f"{mot}|correct"), out.get(f"{mot}|fault")
    if not c or not fl: continue
    print(f"  {mot:24s} 스칼라 운영 {fl['op_scalar']/c['op_scalar']:.2f}배 -> 비용변경 "
          f"{fl['med_scalar']/c['med_scalar']:.2f}배   |  초과합 운영 "
          f"{c['op_over']:.1f}/{fl['op_over']:.1f} -> 변경 {c['med_over']:.1f}/{fl['med_over']:.1f}")
