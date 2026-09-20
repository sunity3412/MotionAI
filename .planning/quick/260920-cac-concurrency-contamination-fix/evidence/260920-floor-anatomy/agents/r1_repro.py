"""R1 — c3 의 oracle 수치를 먼저 그대로 재현한다(재현 안 되면 즉시 refuted)."""
from __future__ import annotations
import json, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD

ctrl = json.load(open(f"{D}/out/c3_controls.json"))
orc = {(r["ref"], r["label"], str(r["vk"])): r for r in json.load(open(f"{D}/out/c3_oracle.json"))}
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()

TARGET = [("ref-pdshape", "correct"), ("ref-elbow-twist-sister", "correct"),
          ("ref-kip-up", "correct"), ("ref-foxtop", "self"), ("ref-power-spin", "correct")]
print(f"{'group':38s}{'nu':>5s}{'nr':>5s}{'dtw_old':>9s}{'dtw_new':>9s}{'orc_old':>9s}{'orc_new':>9s}")
for base in ctrl:
    if (base["ref"], base["label"]) not in TARGET or base["vk"] is None:
        continue
    s = students[base["aid"]]; rdoc = refs[base["ref"]]
    U = H.student_matrix(s); A = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    dev, m = H.deviate(U, rdoc)
    u_seg = U[m.start:m.end]; a_win = A[m.ref_start:m.ref_end]
    dif = np.abs(u_seg[:, None, :] - a_win[None, :, :])
    br = np.argmin(np.nansum(dif ** 2, axis=2), axis=1)
    dv = MD.per_joint_deviation([(u, int(br[u])) for u in range(u_seg.shape[0])], u_seg, a_win, ref_fps=fps)
    o = orc[(base["ref"], base["label"], str(base["vk"]))]
    print(f"{base['ref']+'/'+base['label']:38s}{u_seg.shape[0]:>5d}{a_win.shape[0]:>5d}"
          f"{o['dev_dtw']:>9.3f}{H.scalar(dev):>9.3f}{o['dev_oracle_frame']:>9.3f}{H.scalar(dv):>9.3f}")
