"""Do the two extractions of the SAME footage agree on the SAME source frame?

Reference angles: rtmw-x-384-direct, target 18 fps -> effective ~14.94 fps.
Student angles:   live pipeline,     target  9 fps -> effective ~9.96 fps.
Row counts confirm the ratio is exactly 2/3 for every motion, i.e. the source
video was decimated with step 2 (reference) and step 3 (student). Therefore

    student row i   <-> source frame 3i
    reference row j <-> source frame 2j

and they are the SAME source frame whenever 3i == 2j, i.e. for even i at j = 3i/2.

On those coincident rows the only thing that can differ is the pose path itself
(model invocation, detector box, input resolution, preprocessing). On the odd rows
the extra difference is temporal. Splitting the two tells us which one owns the floor.
"""
import json, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H

facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()

print(f"{'motion':24s}{'ref T':>6s}{'stu T':>6s}{'coincident':>11s}"
      f"{'SAME-frame':>12s}{'off-frame':>11s}{'live floor':>12s}")
out = []
for m in sorted(refs):
    rows = [r for r in facts if r["ref"] == m and r["label"] in ("self", "correct")]
    if not rows:
        continue
    a_ref = H.ref_matrix(refs[m])
    a_stu = H.student_matrix(students[rows[0]["id"]])
    Tr, Ts = len(a_ref), len(a_stu)
    if abs(Ts / Tr - 2 / 3) > 0.01:
        print(f"{m:24s} ratio {Ts/Tr:.4f} not 2/3 — skipped")
        continue

    same, off = [], []
    for i in range(Ts):
        j = i * 3 / 2
        if i % 2 == 0:                       # exact same source frame
            jj = int(j)
            if jj < Tr:
                same.append(np.abs(a_stu[i] - a_ref[jj]))
        else:                                # falls between two reference rows
            lo, hi = int(np.floor(j)), int(np.ceil(j))
            if hi < Tr:
                mid = 0.5 * (a_ref[lo] + a_ref[hi])
                off.append(np.abs(a_stu[i] - mid))
    s_med = float(np.median(np.median(np.array(same), axis=0))) if same else float("nan")
    o_med = float(np.median(np.median(np.array(off), axis=0))) if off else float("nan")
    live = float(np.median([r["scalar"] for r in rows]))
    out.append(dict(motion=m, same=s_med, off=o_med, live=live, n_same=len(same)))
    print(f"{m:24s}{Tr:6d}{Ts:6d}{len(same):11d}{s_med:12.2f}{o_med:11.2f}{live:12.2f}")

json.dump(out, open(f"{D}/same_frame_probe.json", "w"))
print()
print("SAME-frame = median |angle difference| on rows that are the identical source frame.")
print("             Nothing temporal can contribute here. This is the pose path alone.")
print("off-frame  = rows sampled between two reference rows (pose path + temporal).")
