"""The canonical table: what this axis does to the screen score, version-matched.

Investigation F ran the same trace against today's live reference docs. Every stored
analysis but four predates the 2026-09-17 rot180 promotion, so for the six motions
that promotion touched the live comparison mixes an un-flipped student with a
flipped reference. This reruns it against the reference version that was actually
live when each analysis ran, which is the only honest comparison.

Full production config, same as F: profile from the reference doc's techniqueProfile,
quantification available, production tally.
"""
from __future__ import annotations
import collections, json, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import deduction_engine, technique

app = H.app
facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
vers = json.load(open(f"{D}/ref_versions.json"))
live = H.load_references()
VER_BY_MOTION = {"ref-climb": "quick-260816-r7k"}


class QuantOK:
    quantificationStatus = "ok"
    bodyRelativeNotches = None
    windowMedianAngleDeltas = None


def ver_doc(m):
    v = dict(vers[m].get(VER_BY_MOTION.get(m, "phase4_v1")) or {})
    if not v.get("angles"):
        return None
    for k in ("anglesJointKeys", "clipRange", "baseUntilS", "sharedBaseMotionId",
              "keypointReport", "anglesRealFps", "techniqueProfile", "motionId"):
        v.setdefault(k, live[m].get(k))
    return v


def profile_from(rdoc, m):
    tp = rdoc.get("techniqueProfile") or {}
    return technique.TechniqueProfile(
        name=tp.get("name") or "미상",
        category=tp.get("category") or "unknown",
        joint_expectations=dict(tp.get("jointExpectations") or {}),
        motion_id=m,
    )


def run(sid, rdoc, m):
    ang = H.student_matrix(students[sid])
    nj = len(rdoc["anglesJointKeys"])
    dev, match, _u, a_ref = app._deviation_against(
        ang, np.asarray(rdoc["angles"], float), nj,
        ref_boundary=H.ref_boundary_of(rdoc), ref_fps=H.ref_fps_of(rdoc))
    prof = profile_from(rdoc, m)
    merr: dict = {}
    md = app._build_deduction_measured_deviations(
        angles=ang, profile=prof, assessments=None, dimension_scores=None,
        quantification=None, reference_dtw_match=match, reference_angles=a_ref,
        ref_fps=H.ref_fps_of(rdoc), measurement_error_out=merr)
    b = deduction_engine.tally(
        QuantOK(), None, dimension_overall=100, measured_deviations=dict(md),
        dimension_scores=None, baseline_kind=app._baseline_kind_for_profile(prof),
        measurement_error=merr)
    nkeys = sum(1 for k in md if k.startswith("angle_vs_reference__"))
    return H.scalar(dev), b.final, nkeys


print(f"{'motion':24s}{'label':9s}{'n':>4s}{'dev':>7s}{'axis keys':>10s}"
      f"{'score':>7s}{'range':>11s}{'=100':>6s}{'=60':>5s}")
res = collections.defaultdict(dict)
for m in sorted(live):
    vd = ver_doc(m)
    if vd is None:
        continue
    for label in ("correct", "self", "fault"):
        rows = [r for r in facts if r["ref"] == m and r["label"] == label]
        if not rows:
            continue
        devs, fins, keys = [], [], []
        for r in rows:
            d, f, k = run(r["id"], vd, m)
            devs.append(d); fins.append(f); keys.append(k)
        fa = np.array(fins, float)
        res[m][label] = float(np.median(fa))
        print(f"{m:24s}{label:9s}{len(rows):4d}{np.median(devs):7.1f}"
              f"{int(np.median(keys)):10d}{np.median(fa):7.0f}"
              f"{f'{fa.min():.0f}~{fa.max():.0f}':>11s}"
              f"{int((fa == 100).sum()):6d}{int((fa == 60).sum()):5d}")

print()
print(f"{'motion':24s}{'clean(정은지 본인)':>20s}{'fault(일부러)':>16s}{'separation':>12s}")
for m in sorted(res):
    clean = res[m].get("correct", res[m].get("self"))
    fault = res[m].get("fault")
    if clean is None:
        continue
    sep = f"{clean - fault:+.0f}" if fault is not None else "-"
    fs = f"{fault:.0f}" if fault is not None else "-"
    print(f"{m:24s}{clean:20.0f}{fs:>16s}{sep:>12s}")
json.dump({m: dict(v) for m, v in res.items()}, open(f"{D}/final_table.json", "w"))
