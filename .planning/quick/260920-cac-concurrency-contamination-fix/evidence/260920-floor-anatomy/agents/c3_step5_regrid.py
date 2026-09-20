"""C3 step5 — 시간격자 불일치를 제거하면 바닥이 내려가나.

학생 각도를 기준의 프레임 수(nr)로 선형 보간 재격자 → 1:1 항등 대응.
self 케이스(같은 영상)면 이것은 '두 추출이 같은 시간 격자였다면' 의 조건이다.
편차는 운영 per_joint_deviation 호출 (path = 항등).
보간은 진단용 근사임을 명시 — 각도의 선형보간.
"""
from __future__ import annotations
import json, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD

ctrl = {(r["ref"], r["label"], str(r["vk"])): r for r in json.load(open(f"{D}/out/c3_controls.json"))}
orc = {(r["ref"], r["label"], str(r["vk"])): r for r in json.load(open(f"{D}/out/c3_oracle.json"))}
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()

print(f"{'motion':24s}{'label':8s}{'nu':>5s}{'nr':>5s}{'cov':>6s}{'dtw':>7s}{'regrid':>8s}"
      f"{'rg_dtw':>8s}{'orc_f':>7s}")
out = []
for key, base in sorted(ctrl.items()):
    s = students[base["aid"]]; rdoc = refs[base["ref"]]
    U = H.student_matrix(s); A = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    nu, nr = U.shape[0], A.shape[0]
    # 학생을 기준 격자(nr)로 선형 재격자
    tu = np.linspace(0.0, 1.0, nu); tr = np.linspace(0.0, 1.0, nr)
    Ur = np.column_stack([np.interp(tr, tu, U[:, j]) for j in range(U.shape[1])])
    p_id = [(i, i) for i in range(nr)]
    dev_rg = MD.per_joint_deviation(p_id, Ur, A, ref_fps=fps)
    # 재격자본을 운영 경로에 그대로 통과 (nu==nr → equal_whole, DTW 는 정렬만)
    dev_rgd, m2 = H.deviate(Ur, rdoc)
    o = orc[key]
    print(f"{base['ref']:24s}{base['label']:8s}{nu:>5d}{nr:>5d}{nu/nr:>6.3f}"
          f"{base['dev_dtw']:>7.1f}{H.scalar(dev_rg):>8.1f}{H.scalar(dev_rgd):>8.1f}"
          f"{o['dev_oracle_frame']:>7.1f}")
    out.append(dict(ref=base["ref"], label=base["label"], vk=base["vk"], n_group=base["n_group"],
                    nu=nu, nr=nr, cov=nu/nr, dev_dtw=base["dev_dtw"],
                    dev_regrid_identity=H.scalar(dev_rg), dev_regrid_dtw=H.scalar(dev_rgd),
                    dev_oracle=o["dev_oracle_frame"]))
json.dump(out, open(f"{D}/out/c3_regrid.json", "w"), indent=1)
