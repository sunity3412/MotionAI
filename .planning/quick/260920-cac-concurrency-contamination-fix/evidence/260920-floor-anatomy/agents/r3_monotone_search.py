"""R3 — 도달 가능한(단조) 시간정렬을 넓게 뒤진다.

R2 로 c3 의 'oracle' 이 하한이 아님은 보였다(자유짝 free_med 가 그 아래).
그러면 진짜 질문이 남는다: **실제로 도달 가능한 정렬**(단조 경로)이 바닥을 얼마나
지우나? c3 는 이 질문에 L2-oracle 하나로 답했다. 여기서는
  - 70개 4관절 부분집합 각각의 비용으로 단조 DTW DP (스칼라는 8개 중 median 이라
    4관절만 맞추면 되는 구조를 그대로 겨냥)
  - 관절별 median 비용 DTW
  - free_med 자유짝을 단조로 투영(PAVA 등장식 DP)
  - 전 8관절 L2 DTW (운영과 같은 비용, window 고정)
넷 중 최선을 '도달 가능한 최선 정렬'로 본다. 편차는 전부 운영
motiondtw.per_joint_deviation 호출.
"""
from __future__ import annotations
import json, sys, itertools, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD

ctrl = json.load(open(f"{D}/out/c3_controls.json"))
orc = {(r["ref"], r["label"], str(r["vk"])): r for r in json.load(open(f"{D}/out/c3_oracle.json"))}
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()

FLOORS = [("ref-sideway-spin","self"),("ref-kip-up","correct"),("ref-peter-pan","correct"),
          ("ref-power-spin","correct"),("ref-climb","correct"),("ref-combo","correct"),
          ("ref-invert","self"),("ref-foxtop","self"),("ref-foxtop-split","self"),
          ("ref-elbow-twist-sister","correct"),("ref-pdshape","correct")]

def pick(ref_id, label):
    cand = [c for c in ctrl if c["ref"] == ref_id and c["label"] == label]
    named = [c for c in cand if c["vk"]]
    return (named or cand)[0] if cand else None

def dtw_path(C):
    """표준 단조 DTW. 행별 벡터화: D[i,:] = P + minacc(M - P)."""
    nu, nr = C.shape
    Dm = np.full((nu + 1, nr + 1), np.inf)
    Dm[0, 0] = 0.0
    for i in range(1, nu + 1):
        ci = C[i - 1]
        prev = Dm[i - 1]
        base = np.minimum(prev[1:], prev[:-1])          # min(D[i-1,j], D[i-1,j-1])
        M = base + ci                                    # 대각/위에서 들어오는 비용
        P = np.cumsum(ci)
        Dm[i, 1:] = P + np.minimum.accumulate(M - P)
    path = []
    i, j = nu, nr
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = int(np.argmin([Dm[i-1, j-1], Dm[i-1, j], Dm[i, j-1]]))
        if k == 0: i, j = i - 1, j - 1
        elif k == 1: i -= 1
        else: j -= 1
    path.reverse()
    return path

def monotone_project(target, nr):
    """target(자유짝 인덱스)을 비감소 정수열로 투영 — L2 최소 (PAVA)."""
    x = np.asarray(target, dtype=float)
    vals, wts = [], []
    for v in x:
        vals.append(v); wts.append(1.0)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2 = vals.pop(); w2 = wts.pop(); v1 = vals.pop(); w1 = wts.pop()
            vals.append((v1*w1 + v2*w2)/(w1+w2)); wts.append(w1+w2)
    out = []
    for v, w in zip(vals, wts):
        out.extend([v]*int(w))
    return np.clip(np.round(np.array(out)).astype(int), 0, nr-1)

rows = []
t0 = time.time()
for ref_id, label in FLOORS:
    base = pick(ref_id, label)
    s = students[base["aid"]]; rdoc = refs[ref_id]
    U = H.student_matrix(s); A = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    dev_op, m = H.deviate(U, rdoc)
    u_seg = U[m.start:m.end]; a_win = A[m.ref_start:m.ref_end]
    nu, nr, J = u_seg.shape[0], a_win.shape[0], a_win.shape[1]
    dif = np.abs(u_seg[:, None, :] - a_win[None, :, :])
    sq = np.nan_to_num(dif ** 2, nan=0.0)
    med = np.nanmedian(dif, axis=2)

    def sc(p):
        return H.scalar(MD.per_joint_deviation(p, u_seg, a_win, ref_fps=fps))

    s_op = H.scalar(dev_op)
    br_med = np.argmin(med, axis=1)
    s_free_med = sc([(u, int(br_med[u])) for u in range(nu)])

    cands = {}
    # (1) 전 8관절 L2 비용 단조 DTW (window 고정)
    cands["mono_all"] = sc(dtw_path(np.sqrt(sq.sum(axis=2))))
    # (2) 관절별 median 비용 단조 DTW
    cands["mono_med"] = sc(dtw_path(med))
    # (3) free_med 를 단조 투영
    cands["mono_proj"] = sc([(u, int(j)) for u, j in enumerate(monotone_project(br_med, nr))])
    # (4) 4관절 부분집합 70개 전부 단조 DTW
    best_sub, best_S = np.inf, None
    for S in itertools.combinations(range(J), 4):
        v = sc(dtw_path(np.sqrt(sq[:, :, list(S)].sum(axis=2))))
        if v < best_sub:
            best_sub, best_S = v, S
    cands["mono_sub4"] = best_sub

    mono_best = float(min(cands.values()))
    o = orc[(ref_id, label, str(base["vk"]))]
    rows.append(dict(ref=ref_id, label=label, nu=nu, nr=nr, op=s_op,
                     c3_oracle=o["dev_oracle_frame"], free_med=s_free_med,
                     mono_best=mono_best, best_subset=list(best_S), **cands))
    print(f"  {ref_id:24s}{label:8s} op={s_op:6.2f} c3orc={o['dev_oracle_frame']:6.2f} "
          f"free_med={s_free_med:6.2f} mono_best={mono_best:6.2f} "
          f"[all={cands['mono_all']:.2f} med={cands['mono_med']:.2f} proj={cands['mono_proj']:.2f} "
          f"sub4={cands['mono_sub4']:.2f}]  {time.time()-t0:5.0f}s", flush=True)

json.dump(rows, open(f"{D}/out/r3_monotone.json", "w"), indent=1)
print()
print("== 도달 가능한(단조) 정렬이 바닥을 얼마나 지우나 ==")
print(f"{'motion':24s}{'lab':6s}{'운영':>7s}{'c3oracle':>9s}{'free_med':>9s}{'mono_best':>10s}"
      f"{'c3주장몫%':>10s}{'단조실측몫%':>12s}")
for r in rows:
    print(f"{r['ref']:24s}{r['label']:6s}{r['op']:>7.1f}{r['c3_oracle']:>9.1f}{r['free_med']:>9.1f}"
          f"{r['mono_best']:>10.1f}{100*(r['op']-r['c3_oracle'])/r['op']:>10.0f}"
          f"{100*(r['op']-r['mono_best'])/r['op']:>12.0f}")
a = [r["op"] for r in rows]; b = [r["mono_best"] for r in rows]; c = [r["free_med"] for r in rows]
print(f"\n바닥 편차폭(최대/최소): 운영 {max(a)/min(a):.1f}배  단조최선 {max(b)/min(b):.1f}배  자유짝 {max(c)/min(c):.1f}배")
