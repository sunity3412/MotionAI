"""R5 — c3 가 쓴 '편차 스칼라'는 소비처가 안 쓰는 숫자다. 소비처 축에서 다시 본다.

소비처(c3 가 스스로 코드로 이은 사슬): md[f"angle_vs_reference__{jk}"] = 관절별 median|Δ|
  → ipsf_criteria.criteria_from_measured_deviations(md) 가 **관절별로** tolerance 20°
    초과면 그 criterion 을 활성화 → 감점 record.
c3 의 모든 실험(oracle/역순/재격자/정렬몫)은 그 8개의 **median 한 개**(스칼라) 위에서
잰다. median-of-8 은 소비처에 없는 숫자다. 정렬이 '20° 를 넘는 관절 수'를 크게 바꾸면
c3 의 스칼라는 조용해도 점수는 움직인다 → c3 의 결론이 무너진다.

여기서는 같은 window 위의 네 정렬(운영 / c3 oracle / 자유짝 free_med / 내가 찾은
도달가능 단조 최선)에 대해 관절별 편차를 내고, 운영 함수
criteria_from_measured_deviations 로 **활성 criterion 수**를 직접 센다.
"""
from __future__ import annotations
import json, sys, itertools, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD
from sunity_shared.analysis import ipsf_criteria as IC

TOL = IC._ANGLE_TOLERANCE_DEG
print(f"운영 tolerance(_ANGLE_TOLERANCE_DEG) = {TOL}")

ctrl = json.load(open(f"{D}/out/c3_controls.json"))
r3 = {(r["ref"], r["label"]): r for r in json.load(open(f"{D}/out/r3_monotone.json"))}
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()
FLOORS = list(r3.keys())

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

def activated(dev):
    md = {f"angle_vs_reference__{jk}": float(d) for jk, d in zip(H.JOINT_KEYS, dev)
          if np.isfinite(d)}
    return sorted(IC.criteria_from_measured_deviations(md))

rows = []
for ref_id, label in FLOORS:
    base = pick(ref_id, label)
    s = students[base["aid"]]; rdoc = refs[ref_id]
    U = H.student_matrix(s); A = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    dev_op, m = H.deviate(U, rdoc)
    u_seg = U[m.start:m.end]; a_win = A[m.ref_start:m.ref_end]
    nu, nr, J = u_seg.shape[0], a_win.shape[0], a_win.shape[1]
    dif = np.abs(u_seg[:, None, :] - a_win[None, :, :])
    sq = np.nan_to_num(dif ** 2, nan=0.0); med = np.nanmedian(dif, axis=2)

    def devs(p): return MD.per_joint_deviation(p, u_seg, a_win, ref_fps=fps)
    br_l2 = np.argmin(sq.sum(axis=2), axis=1)
    dev_orc = devs([(u, int(br_l2[u])) for u in range(nu)])
    br_md = np.argmin(med, axis=1)
    dev_fm = devs([(u, int(br_md[u])) for u in range(nu)])
    # 도달가능 단조 최선: r3 이 고른 최선 경로를 같은 방식으로 재구성
    best = (np.inf, None)
    for cand_p in [dtw_path(np.sqrt(sq.sum(axis=2))), dtw_path(med),
                   dtw_path(np.sqrt(sq[:, :, r3[(ref_id,label)]["best_subset"]].sum(axis=2)))]:
        d = devs(cand_p); v = H.scalar(d)
        if v < best[0]: best = (v, d)
    dev_mono = best[1]

    rec = dict(ref=ref_id, label=label)
    for name, d in (("op", dev_op), ("c3_oracle", dev_orc), ("free_med", dev_fm), ("mono", dev_mono)):
        act = activated(d)
        rec[name] = dict(scalar=H.scalar(d), n_act=len(act),
                         over=float(np.nansum(np.clip(np.asarray(d) - TOL, 0, None))),
                         perjoint=[round(float(x), 1) for x in d])
    rows.append(rec)
    print(f"  {ref_id:24s}{label:8s} 활성관절수 op={rec['op']['n_act']} "
          f"c3orc={rec['c3_oracle']['n_act']} free_med={rec['free_med']['n_act']} mono={rec['mono']['n_act']}"
          f"   초과합 op={rec['op']['over']:6.1f} mono={rec['mono']['over']:6.1f} "
          f"c3orc={rec['c3_oracle']['over']:6.1f} free_med={rec['free_med']['over']:6.1f}", flush=True)

json.dump(rows, open(f"{D}/out/r5_consumer.json", "w"), indent=1)
print()
print("== 소비처 축: 20° 를 넘어 감점 record 를 만드는 관절 (8관절 중) ==")
print(f"{'motion':24s}{'lab':6s}{'운영':>6s}{'단조최선':>9s}{'c3oracle':>9s}{'자유짝':>8s}"
      f"{'| 초과합 운영':>13s}{'단조':>8s}{'c3orc':>8s}{'자유짝':>8s}")
for r in rows:
    print(f"{r['ref']:24s}{r['label']:6s}{r['op']['n_act']:>6d}{r['mono']['n_act']:>9d}"
          f"{r['c3_oracle']['n_act']:>9d}{r['free_med']['n_act']:>8d}"
          f"{r['op']['over']:>13.1f}{r['mono']['over']:>8.1f}{r['c3_oracle']['over']:>8.1f}{r['free_med']['over']:>8.1f}")
