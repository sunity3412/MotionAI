"""R2 — c3 의 'oracle' 이 정말 정렬의 하한인가?

c3 주장: "학생 프레임마다 8관절 L2 가 최소인 기준 프레임을 자유 선택 → 어떤
시간왜곡(DTW·warp·trim)도 이 아래로 못 간다."

문제: 채점이 쓰는 스칼라는 L2 가 아니다.
  per_joint_deviation = 관절별 **median over path steps** of |Δ|  (8개)
  scalar              = 그 8개의 **median**  →  8관절 중 4개만 낮으면 낮아진다.
L2 를 최소화하는 짝은 이 스칼라의 최소화가 아니다. 따라서 c3 의 'oracle' 은
하한이 아닐 수 있다. 여기서는 같은 window·같은 운영 함수(per_joint_deviation)로
  (a) 자유 짝(비단조) 을 다른 기준으로 고른 경로
  (b) **단조 경로(실제로 도달 가능한 시간정렬)** — subset 비용 DTW DP
를 만들어 c3 oracle 아래로 내려가는지 본다. 내려가면 c3 의 하한 주장은 무너진다.

편차 산출은 전부 운영 motiondtw.per_joint_deviation 호출. 재구현 0.
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

def dtw_dp(C):
    """비용행렬 C(nu,nr) 위의 표준 단조 DTW 경로 — 실제 시간정렬이 낼 수 있는 경로."""
    nu, nr = C.shape
    INF = np.inf
    Dm = np.full((nu + 1, nr + 1), INF)
    Dm[0, 0] = 0.0
    for i in range(1, nu + 1):
        row = Dm[i]; prev = Dm[i - 1]; ci = C[i - 1]
        for j in range(1, nr + 1):
            row[j] = ci[j - 1] + min(prev[j], row[j - 1], prev[j - 1])
    path = []
    i, j = nu, nr
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        step = int(np.argmin([Dm[i-1, j-1], Dm[i-1, j], Dm[i, j-1]]))
        if step == 0: i, j = i - 1, j - 1
        elif step == 1: i -= 1
        else: j -= 1
    path.reverse()
    return path

rows = []
t0 = time.time()
for ref_id, label in FLOORS:
    base = pick(ref_id, label)
    s = students[base["aid"]]; rdoc = refs[ref_id]
    U = H.student_matrix(s); A = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    dev_op, m = H.deviate(U, rdoc)
    u_seg = U[m.start:m.end]; a_win = A[m.ref_start:m.ref_end]
    nu, nr, J = u_seg.shape[0], a_win.shape[0], a_win.shape[1]
    dif = np.abs(u_seg[:, None, :] - a_win[None, :, :])          # (nu,nr,J)
    sq = np.nan_to_num(dif ** 2, nan=0.0)

    def free(costmat):
        br = np.argmin(costmat, axis=1)
        p = [(u, int(br[u])) for u in range(nu)]
        return H.scalar(MD.per_joint_deviation(p, u_seg, a_win, ref_fps=fps)), p

    s_op = H.scalar(dev_op)
    s_l2, _ = free(np.nansum(sq, axis=2))                         # c3 의 oracle 재현
    s_med, _ = free(np.nanmedian(dif, axis=2))                    # 스칼라를 직접 겨냥한 자유 짝

    # 부분집합(4관절) 자유 짝 — 스칼라는 8관절 중 median 이라 4개만 맞으면 된다
    best = (np.inf, None)
    subs = list(itertools.combinations(range(J), 4))
    scored = []
    for S in subs:
        v, _ = free(sq[:, :, list(S)].sum(axis=2))
        scored.append((v, S))
        if v < best[0]:
            best = (v, S)
    scored.sort()
    s_sub4 = best[0]

    # 단조 경로(도달 가능한 시간정렬) — 상위 3 subset 에 대해 DTW DP
    mono = []
    for v, S in scored[:3]:
        C = np.sqrt(sq[:, :, list(S)].sum(axis=2))
        p = dtw_dp(C)
        mono.append(H.scalar(MD.per_joint_deviation(p, u_seg, a_win, ref_fps=fps)))
    C = np.nanmedian(dif, axis=2)
    mono.append(H.scalar(MD.per_joint_deviation(dtw_dp(C), u_seg, a_win, ref_fps=fps)))
    s_mono = float(min(mono))

    o = orc[(ref_id, label, str(base["vk"]))]
    rows.append(dict(ref=ref_id, label=label, nu=nu, nr=nr,
                     op=s_op, c3_oracle=o["dev_oracle_frame"], repro_l2=s_l2,
                     free_med=s_med, free_sub4=s_sub4, best_subset=list(best[1]),
                     mono_best=s_mono, monos=mono, orc_joint=o["dev_oracle_joint"]))
    print(f"  {ref_id:24s}{label:8s} nu={nu:4d} nr={nr:4d}  op={s_op:6.2f}  c3orc={o['dev_oracle_frame']:6.2f}"
          f"  free_med={s_med:6.2f}  free_sub4={s_sub4:6.2f}  MONO={s_mono:6.2f}   {time.time()-t0:5.0f}s", flush=True)

json.dump(rows, open(f"{D}/out/r2_bound.json", "w"), indent=1)

print()
print("== c3 'oracle' 은 하한인가 ==")
print(f"{'motion':24s}{'lab':6s}{'운영':>7s}{'c3oracle':>9s}{'free_med':>9s}{'free_s4':>8s}{'MONO(도달가능)':>15s}"
      f"{'c3정렬몫%':>10s}{'실제정렬몫%(mono)':>18s}")
for r in rows:
    c3_share = 100 * (r["op"] - r["c3_oracle"]) / r["op"]
    mono_share = 100 * (r["op"] - r["mono_best"]) / r["op"]
    print(f"{r['ref']:24s}{r['label']:6s}{r['op']:>7.1f}{r['c3_oracle']:>9.1f}{r['free_med']:>9.1f}"
          f"{r['free_sub4']:>8.1f}{r['mono_best']:>15.1f}{c3_share:>10.0f}{mono_share:>18.0f}")
