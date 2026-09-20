"""The floor, measured like for like.

The 875 stored analyses were all extracted before the 2026-09-17 rot180 flip
(only 4 postdate it), so their student angles carry ROT180 off. The live reference
doc now carries rot180_v1. Comparing the two mixes coordinate conventions and
inflates the floor for exactly the motions rot180 touched. The reference versions
subcollection still holds phase4_v1, which is what those analyses were actually
scored against, so the honest comparison uses that.

Columns:
  floor(matched)  same footage as the reference, phase4_v1 on both sides
  floor(live)     same footage vs today's rot180_v1 reference  <- version-mixed
  fault(matched)  the deliberate-mistake take, phase4_v1
  ratio           fault / floor, both matched
"""
import json, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H

facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
vers = json.load(open(f"{D}/ref_versions.json"))
live = H.load_references()

VER_BY_MOTION = {"ref-climb": "quick-260816-r7k"}
VER = "phase4_v1"


def ver_doc(m):
    """A version doc shaped like a reference doc, for H.deviate."""
    v = dict(vers[m].get(VER_BY_MOTION.get(m, VER)) or {})
    if not v.get("angles"):
        return None
    base = live[m]
    for k in ("anglesJointKeys", "clipRange", "baseUntilS", "sharedBaseMotionId",
              "keypointReport", "anglesRealFps"):
        v.setdefault(k, base.get(k))
    return v


def med(rows, rdoc):
    vals = []
    for r in rows:
        dev, _ = H.deviate(H.student_matrix(students[r["id"]]), rdoc)
        vals.append(H.scalar(dev))
    return float(np.median(vals)) if vals else float("nan"), len(vals)


print(f"{'motion':24s}{'floor(matched)':>16s}{'floor(live)':>13s}{'delta':>8s}"
      f"{'fault(matched)':>16s}{'ratio':>8s}{'ref moved':>11s}")
out = []
for m in sorted(live):
    vd = ver_doc(m)
    if vd is None:
        print(f"{m:24s}  no {VER} angles")
        continue
    a_old = np.asarray(vd["angles"], float).reshape(-1, len(vd["anglesJointKeys"]))
    a_new = H.ref_matrix(live[m])
    refmoved = float(np.median(np.abs(a_old - a_new))) if a_old.shape == a_new.shape else float("nan")

    floor_rows = [r for r in facts if r["ref"] == m and r["label"] in ("self", "correct")]
    fault_rows = [r for r in facts if r["ref"] == m and r["label"] == "fault"]
    # one representative per distinct footage is enough: identical footage repeats
    def uniq(rows):
        seen, keep = set(), []
        for r in rows:
            k = (r["frames"], round(r["scalar"], 3))
            if k in seen:
                continue
            seen.add(k); keep.append(r)
        return keep

    fm, nf = med(uniq(floor_rows), vd)
    fl = float(np.median([r["scalar"] for r in floor_rows])) if floor_rows else float("nan")
    ft, nt = med(uniq(fault_rows), vd)
    ratio = ft / fm if fm and np.isfinite(fm) and fm > 0 and np.isfinite(ft) else float("nan")
    out.append(dict(motion=m, floor_matched=fm, floor_live=fl, fault_matched=ft,
                    ratio=ratio, ref_moved=refmoved, n_floor=nf, n_fault=nt))
    f2 = f"{ft:16.2f}" if np.isfinite(ft) else f"{'-':>16s}"
    r2 = f"{ratio:8.2f}" if np.isfinite(ratio) else f"{'-':>8s}"
    print(f"{m:24s}{fm:16.2f}{fl:13.2f}{fl-fm:8.2f}{f2}{r2}{refmoved:11.2f}")

json.dump(out, open(f"{D}/matched_floor.json", "w"))
print()
print("'ref moved' = median |angle change| the 2026-09-17 rot180 promotion made to")
print("              that reference. 0.00 = the promotion did not touch that motion.")
