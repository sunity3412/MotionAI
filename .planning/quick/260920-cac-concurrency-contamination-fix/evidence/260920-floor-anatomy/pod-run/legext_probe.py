"""Why does leg_extension fire on the champion's own power-spin, and why 88.69 today?

The criterion reads the representative pose of a hold window and charges the knees
against 180 degrees. ref-power-spin.yaml scopes that EXTEND to hold_moment; the code
picks the lowest-variance sub-window instead (dimensions._select_window, whose own
docstring records belle rejecting this exact false positive on 2026-08-31).

Same video, three angle series:
  reference   : the stored ref-power-spin angles (the champion's clip at ~14.94 fps)
  pre-flip    : student analyses of that same clip, extracted before ROT180 was on
  post-flip   : today's fresh analysis, ROT180 on

Production functions only.
"""
from __future__ import annotations
import json, os, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import dimensions, technique
from sunity_shared.analysis.skeleton import JOINT_KEYS

KNEE_EXTEND = technique.TechniqueProfile(
    name="파워스핀", category="recognized",
    joint_expectations={"left_knee": "extend", "right_knee": "extend"},
    motion_id="ref-power-spin",
)


def report(tag, a):
    sliced, (s, e) = dimensions._select_window(a, KNEE_EXTEND)
    rep = np.nanmean(sliced, axis=0)
    dev = dimensions.extension_deviation(a, KNEE_EXTEND)
    lk, rk = JOINT_KEYS.index("left_knee"), JOINT_KEYS.index("right_knee")
    worst = min(rep[lk], rep[rk])
    ls = dimensions.line_score(a, KNEE_EXTEND)
    print(f"{tag:34s} T={len(a):4d} window=[{s:4d},{e:4d}) "
          f"knee_rep L={rep[lk]:6.1f} R={rep[rk]:6.1f} worst={worst:6.1f} "
          f"deficit={max(dev[lk], dev[rk]):6.1f} line_score={ls}")
    return float(worst)


refs = H.load_references()
a_ref = H.ref_matrix(refs["ref-power-spin"])
print("=== the champion's power-spin, three ways ===")
report("reference stored angles", a_ref)

facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
pre = [r for r in facts if r["ref"] == "ref-power-spin" and r["label"] == "correct"]
vals = []
for r in pre[:6]:
    vals.append(report(f"pre-flip {r['id'][:12]}", H.student_matrix(students[r["id"]])))
print(f"   pre-flip worst-knee over {len(vals)} re-analyses: "
      f"{min(vals):.1f} ~ {max(vals):.1f}")

# today's fresh run
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
                      "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore
db = firestore.Client(project="sunity-ai-coach")
d = db.document("users/mDYDeZWzF6b3qToAy4xKu7FQK3f2/"
                "analyses/db8b271f5db345c285086592f9a33749").get().to_dict() or {}
if d.get("angles"):
    nj = len(d["anglesJointKeys"])
    a_new = np.asarray(d["angles"], float).reshape(-1, nj)
    report("post-flip (today, ROT180 on)", a_new)
    print()
    print("reference vs today, same clip, per joint median |delta| after length match:")
    n = min(len(a_ref), len(a_new))
    idx_r = np.round(np.linspace(0, len(a_ref) - 1, n)).astype(int)
    idx_n = np.round(np.linspace(0, len(a_new) - 1, n)).astype(int)
    dd = np.abs(a_ref[idx_r] - a_new[idx_n])
    for i, k in enumerate(JOINT_KEYS):
        print(f"   {k:16s} {np.median(dd[:, i]):6.1f}")
else:
    print("today's doc has no angles field")
