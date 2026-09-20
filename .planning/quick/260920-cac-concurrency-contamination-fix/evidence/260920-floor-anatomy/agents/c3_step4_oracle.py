"""C3 step4 — 정렬의 상한(oracle)과 ref-경계 마스크의 몫.

oracle_frame : 각 학생 프레임이 8관절 L2 가 가장 가까운 기준 프레임을 자유 선택
               (단조 제약 없음). **어떤 시간왜곡으로도 이보다 낮출 수 없다** —
               DTW·warp·trim 을 통틀어 정렬이 도달 가능한 편차의 하한.
oracle_joint : 관절별로 따로 그 관절만 최소화하는 경로 (더 느슨한 하한).
mask_off     : per_joint_deviation(ref_fps=None) — 경계 제외 창을 끈 값.

편차 산출은 전부 운영 motiondtw.per_joint_deviation 호출.
"""
from __future__ import annotations
import json, sys, collections, time
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD

ctrl = {(r["ref"], r["label"], str(r["vk"])): r for r in json.load(open(f"{D}/out/c3_controls.json"))}
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()

out = []
t0 = time.time()
for key, base in sorted(ctrl.items()):
    s = students[base["aid"]]
    rdoc = refs[base["ref"]]
    U = H.student_matrix(s)
    A_ref = H.ref_matrix(rdoc)
    ref_fps = H.ref_fps_of(rdoc)
    dev_a, m = H.deviate(U, rdoc)
    u_seg = U[m.start:m.end]
    a_win = A_ref[m.ref_start:m.ref_end]
    nu, nr, J = u_seg.shape[0], a_win.shape[0], a_win.shape[1]

    # |Δ| 텐서 (nu, nr, J)
    dif = np.abs(u_seg[:, None, :] - a_win[None, :, :])
    cost = np.nansum(dif ** 2, axis=2)  # (nu,nr) 8관절 L2^2
    best_r = np.argmin(cost, axis=1)
    p_orc = [(u, int(best_r[u])) for u in range(nu)]
    dev_orc = MD.per_joint_deviation(p_orc, u_seg, a_win, ref_fps=ref_fps)

    # 관절별 독립 oracle — 관절 j 만 최소화하는 경로로 per_joint_deviation 을 호출하고
    # 그 관절 열만 취한다 (운영 함수 8회 호출).
    per_j = np.empty(J)
    for j in range(J):
        bj = np.argmin(np.nan_to_num(dif[:, :, j], nan=np.inf), axis=1)
        pj = [(u, int(bj[u])) for u in range(nu)]
        per_j[j] = MD.per_joint_deviation(pj, u_seg, a_win, ref_fps=ref_fps)[j]

    dev_off = MD.per_joint_deviation(m.path, u_seg, a_win, ref_fps=None)

    out.append(dict(
        ref=base["ref"], label=base["label"], vk=base["vk"], n_group=base["n_group"],
        dev_dtw=base["dev_dtw"], dev_ident=base["dev_ident"], dev_shuf=base["dev_shuf"],
        dev_dtw_rev=base["dev_dtw_rev"],
        dev_oracle_frame=H.scalar(dev_orc), dev_oracle_joint=float(np.median(per_j)),
        dev_mask_off=H.scalar(dev_off), drop_pct=base["drop_pct"],
    ))
    print(f"  {base['ref']:24s}{base['label']:8s} {time.time()-t0:5.0f}s", flush=True)

json.dump(out, open(f"{D}/out/c3_oracle.json", "w"), indent=1)

print()
print("== 정렬 상한(oracle) — 어떤 시간정렬로도 이 아래로는 못 간다 ==")
print(f"{'motion':24s}{'label':8s}{'n':>4s}{'dtw':>7s}{'ident':>7s}{'orc_f':>7s}{'orc_j':>7s}"
      f"{'shuf':>7s}{'maskoff':>8s}{'정렬여지':>9s}{'잔여바닥%':>10s}")
for r in out:
    room = r["dev_dtw"] - r["dev_oracle_frame"]     # 정렬을 더 잘해서 줄일 수 있는 최대
    resid = 100.0 * r["dev_oracle_frame"] / max(r["dev_dtw"], 1e-9)
    print(f"{r['ref']:24s}{r['label']:8s}{r['n_group']:>4d}{r['dev_dtw']:>7.1f}{r['dev_ident']:>7.1f}"
          f"{r['dev_oracle_frame']:>7.1f}{r['dev_oracle_joint']:>7.1f}{r['dev_shuf']:>7.1f}"
          f"{r['dev_mask_off']:>8.1f}{room:>9.1f}{resid:>10.0f}")
