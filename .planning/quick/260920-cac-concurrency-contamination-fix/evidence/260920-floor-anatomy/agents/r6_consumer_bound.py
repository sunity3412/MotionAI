"""R6 — 소비처 축에서 '정렬이 지울 수 있는 감점의 상한'.

R5 로 드러난 것: c3 의 스칼라(median-of-8)는 소비처가 안 쓴다. 소비처는 관절별
20° 초과분이다. 그리고 죽은 2동작(elbow/pdshape)에서 **실력차 0 바닥이 실제로 감점
record 를 5~6개 만든다**. 그러면 질문은 하나다 —
  **도달 가능한 정렬로 그 감점을 얼마나 지울 수 있나?**
여기서는 정렬 후보를 넓게(단조 DTW: L2 / 관절별 median / 4관절 부분집합 70개 비용,
 그리고 기준·학생 window 트리밍까지) 만들고 **초과합(Σ max(0, dev−20))을 최소화하는
경로**를 고른다. 결과로 고르는 상한 측정이다(문턱값 튜닝 아님 — 20° 는 운영 상수
_ANGLE_TOLERANCE_DEG 그대로, 건드리지 않는다).
"""
from __future__ import annotations
import json, sys, itertools, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD
from sunity_shared.analysis import ipsf_criteria as IC
from sunity_shared.analysis.features import feature_vector

TOL = IC._ANGLE_TOLERANCE_DEG
ctrl = json.load(open(f"{D}/out/c3_controls.json"))
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()
TARGETS = [("ref-elbow-twist-sister","correct"),("ref-pdshape","correct"),
           ("ref-invert","self"),("ref-foxtop","self"),("ref-foxtop-split","self")]

def pick(ref_id, label):
    cand = [c for c in ctrl if c["ref"] == ref_id and c["label"] == label]
    named = [c for c in cand if c["vk"]]
    return (named or cand)[0] if cand else None

def dtw_path(C):
    nu, nr = C.shape
    Dm = np.full((nu + 1, nr + 1), np.inf); Dm[0, 0] = 0.0
    for i in range(1, nu + 1):
        ci = C[i - 1]; prev = Dm[i - 1]
        M = np.minimum(prev[1:], prev[:-1]) + ci
        P = np.cumsum(ci)
        Dm[i, 1:] = P + np.minimum.accumulate(M - P)
    path = []; i, j = nu, nr
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = int(np.argmin([Dm[i-1, j-1], Dm[i-1, j], Dm[i, j-1]]))
        if k == 0: i, j = i-1, j-1
        elif k == 1: i -= 1
        else: j -= 1
    path.reverse(); return path

def over(dev):
    d = np.asarray(dev, dtype=float)
    return float(np.nansum(np.clip(d - TOL, 0, None)))

def nact(dev):
    md = {f"angle_vs_reference__{jk}": float(x) for jk, x in zip(H.JOINT_KEYS, dev) if np.isfinite(x)}
    return len(IC.criteria_from_measured_deviations(md))

rows = []
t0 = time.time()
for ref_id, label in TARGETS:
    base = pick(ref_id, label)
    s = students[base["aid"]]; rdoc = refs[ref_id]
    U = H.student_matrix(s); A = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    dev_op, m = H.deviate(U, rdoc)
    o_op, a_op = over(dev_op), nact(dev_op)
    nu_full, nr_full = len(U), len(A)

    best = (np.inf, None, None)   # (over, tag, dev)
    def consider(us, ue, rs, re, C, tag):
        global best
        p = dtw_path(C)
        d = MD.per_joint_deviation(p, U[us:ue], A[rs:re], ref_fps=fps)
        v = over(d)
        if v < best[0]:
            best = (v, tag, d)

    windows = [(0, nu_full, 0, nr_full, "full")]
    # 트리밍 window 도 후보 — 기준 슬라이드(막혀 있는 경로) + 양쪽 트리밍 격자
    for frac in (1.0, 0.8, 0.6):
        L = max(8, int(nu_full * frac))
        for us in range(0, nu_full - L + 1, max(1, (nu_full - L)//4) if nu_full > L else 1):
            for rs in range(0, nr_full - L + 1, max(1, (nr_full - L)//8) if nr_full > L else 1):
                windows.append((us, us + L, rs, rs + L, f"trim{frac}"))
    seen = set()
    for (us, ue, rs, re, tag) in windows:
        if (us, ue, rs, re) in seen:
            continue
        seen.add((us, ue, rs, re))
        u_seg = U[us:ue]; a_win = A[rs:re]
        dif = np.abs(u_seg[:, None, :] - a_win[None, :, :])
        sq = np.nan_to_num(dif ** 2, nan=0.0)
        consider(us, ue, rs, re, np.sqrt(sq.sum(axis=2)), tag + "/L2")
        consider(us, ue, rs, re, np.nanmedian(dif, axis=2), tag + "/med")
        if tag == "full":
            for S in itertools.combinations(range(u_seg.shape[1]), 4):
                consider(us, ue, rs, re, np.sqrt(sq[:, :, list(S)].sum(axis=2)), f"full/sub{S}")
    o_best, tag, d_best = best
    rows.append(dict(ref=ref_id, label=label, over_op=o_op, nact_op=a_op,
                     over_best=o_best, nact_best=nact(d_best), tag=tag,
                     dev_op=[round(float(x),1) for x in dev_op],
                     dev_best=[round(float(x),1) for x in d_best]))
    print(f"  {ref_id:24s}{label:8s} 초과합 {o_op:6.1f} -> {o_best:6.1f}  활성 {a_op} -> {nact(d_best)}"
          f"   최선경로={tag}   {time.time()-t0:5.0f}s", flush=True)

json.dump(rows, open(f"{D}/out/r6_consumer_bound.json", "w"), indent=1)
print()
print("== 도달 가능한 정렬이 '실력차 0 바닥이 만든 감점'을 지울 수 있나 ==")
print(f"{'motion':24s}{'lab':6s}{'초과합_운영':>11s}{'초과합_정렬최선':>15s}{'지운몫%':>9s}{'활성 운영->최선':>15s}")
for r in rows:
    share = 100*(r["over_op"]-r["over_best"])/r["over_op"] if r["over_op"] > 0 else float('nan')
    print(f"{r['ref']:24s}{r['label']:6s}{r['over_op']:>11.1f}{r['over_best']:>15.1f}{share:>9.0f}"
          f"{r['nact_op']:>9d} -> {r['nact_best']:<4d}")
