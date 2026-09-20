"""조사 A 단계1c — self 4+1건의 관절별 분포 대조 (학생 vs 기준)."""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

refs = H.load_references(); by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
selfs, seen = [], set()
for f in facts:
    if f["label"] == "self" and f["ref"] not in seen:
        seen.add(f["ref"]); selfs.append(f)
print("JOINT_KEYS:", H.JOINT_KEYS)
for f in sorted(selfs, key=lambda x: x["ref"]):
    s = by_id[f["id"]]
    U = H.student_matrix(s); R = H.ref_matrix(refs[f["ref"]])
    dev, match = H.deviate(U, refs[f["ref"]])
    print("\n---", f["ref"], " scalar(live)=", round(f["scalar"],3), " scalar(recomputed)=", round(H.scalar(dev),3))
    print("body:", json.dumps(s.get("body"), ensure_ascii=False))
    print(f"{'joint':22s} {'u_med':>8s} {'r_med':>8s} {'d_med':>8s} {'u_sd':>7s} {'r_sd':>7s} {'u_rng':>7s} {'r_rng':>7s} {'dev':>7s}")
    for j, jk in enumerate(H.JOINT_KEYS):
        u = U[:, j]; r = R[:, j]
        u = u[np.isfinite(u)]; r = r[np.isfinite(r)]
        print(f"{jk:22s} {np.median(u):8.2f} {np.median(r):8.2f} {np.median(u)-np.median(r):8.2f} "
              f"{u.std():7.2f} {r.std():7.2f} {np.ptp(u):7.1f} {np.ptp(r):7.1f} {dev[j]:7.2f}")
