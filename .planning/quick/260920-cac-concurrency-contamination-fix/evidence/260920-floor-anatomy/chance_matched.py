"""Floor against chance, version-matched.

Investigation B put the floor at 82-86 percent of chance for pdshape and
elbow-twist, which reads as "that measurement is nearly uninformative". Both the
floor and the chance level there were computed against today's rot180_v1
reference while the student side predates the flip. Redone against the reference
version each analysis actually ran on.

chance = pair every student frame with a uniformly random reference frame (time
information destroyed), scored through the production per_joint_deviation.
"""
from __future__ import annotations
import json, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw

facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
vers = json.load(open(f"{D}/ref_versions.json"))
live = H.load_references()
VER_BY_MOTION = {"ref-climb": "quick-260816-r7k"}
SEEDS = (11, 22, 33, 44, 55)


def ver_doc(m):
    v = dict(vers[m].get(VER_BY_MOTION.get(m, "phase4_v1")) or {})
    if not v.get("angles"):
        return None
    for k in ("anglesJointKeys", "clipRange", "baseUntilS", "sharedBaseMotionId",
              "keypointReport", "anglesRealFps"):
        v.setdefault(k, live[m].get(k))
    return v


print(f"{'motion':24s}{'floor':>8s}{'chance':>9s}{'ratio':>7s}"
      f"{'floor(live)':>12s}{'ratio(live)':>12s}")
rows = []
for m in sorted(live):
    vd = ver_doc(m)
    if vd is None:
        continue
    cand = [r for r in facts if r["ref"] == m and r["label"] in ("self", "correct")]
    if not cand:
        continue
    sid = cand[0]["id"]
    ang = H.student_matrix(students[sid])

    def floor_and_chance(rdoc):
        a_ref = H.ref_matrix(rdoc)
        dev, match = H.deviate(ang, rdoc)
        f = H.scalar(dev)
        seg = ang[match.start:match.end]
        win = a_ref[match.ref_start:match.ref_end]
        ch = []
        for sd in SEEDS:
            rng = np.random.default_rng(sd)
            path = [(i, int(rng.integers(0, len(win)))) for i in range(len(seg))]
            ch.append(H.scalar(motiondtw.per_joint_deviation(path, seg, win)))
        return f, float(np.median(ch))

    fm, cm = floor_and_chance(vd)
    fl, cl = floor_and_chance(live[m])
    rows.append(dict(motion=m, floor=fm, chance=cm, ratio=fm / cm,
                     floor_live=fl, ratio_live=fl / cl))
    print(f"{m:24s}{fm:8.2f}{cm:9.2f}{fm/cm:7.3f}{fl:12.2f}{fl/cl:12.3f}")

json.dump(rows, open(f"{D}/chance_matched.json", "w"))
print()
print("ratio near 1 = the measurement is no better than pairing frames at random.")
