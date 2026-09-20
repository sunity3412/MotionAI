"""Did the reference_relative axis move scores, or did a version mismatch move them?

The axis deducts only above _ANGLE_TOLERANCE_DEG = 20 (kismam reuse, ipsf_criteria.py).
Version-matched floors sit at 2.3-17.7 deg, i.e. under that tolerance. Version-mixed
floors (pre-rot180 student vs today's rot180_v1 reference) sit at 2.3-24.3, i.e. over
it for the motions rot180 touched.

So the same analyses can score 100 or well under 100 depending only on which
reference version they are compared against. This runs both and prints the pair.
Production functions only.
"""
from __future__ import annotations
import collections, json, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import deduction_engine

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
              "keypointReport", "anglesRealFps"):
        v.setdefault(k, live[m].get(k))
    return v


def run(sid, rdoc):
    ang = H.student_matrix(students[sid])
    nj = len(rdoc["anglesJointKeys"])
    dev, match, _u, a_ref = app._deviation_against(
        ang, np.asarray(rdoc["angles"], float), nj,
        ref_boundary=H.ref_boundary_of(rdoc), ref_fps=H.ref_fps_of(rdoc))
    merr: dict = {}
    md = app._build_deduction_measured_deviations(
        angles=ang, profile=None, assessments=None, dimension_scores=None,
        quantification=None, reference_dtw_match=match, reference_angles=a_ref,
        ref_fps=H.ref_fps_of(rdoc), measurement_error_out=merr)
    b = deduction_engine.tally(
        QuantOK(), None, dimension_overall=100, measured_deviations=dict(md),
        dimension_scores=None, baseline_kind=app._baseline_kind_for_profile(None),
        measurement_error=merr)
    over = sum(1 for k, v in md.items()
               if k.startswith("angle_vs_reference__") and float(v) > 20.0)
    return H.scalar(dev), b.final, over


def uniq(rows):
    seen, keep = set(), []
    for r in rows:
        k = (r["frames"], round(r["scalar"], 3))
        if k in seen:
            continue
        seen.add(k); keep.append(r)
    return keep


print(f"{'motion':24s}{'label':9s}{'dev matched':>12s}{'score':>7s}"
      f"{'dev live':>10s}{'score':>7s}{'joints>20 m/l':>15s}")
agg = collections.defaultdict(list)
for m in sorted(live):
    vd = ver_doc(m)
    if vd is None:
        continue
    for label in ("correct", "self", "fault"):
        rows = uniq([r for r in facts if r["ref"] == m and r["label"] == label])
        if not rows:
            continue
        r = rows[0]
        dm, fm, om = run(r["id"], vd)
        dl, fl, ol = run(r["id"], live[m])
        agg[label].append((fm, fl))
        print(f"{m:24s}{label:9s}{dm:12.2f}{fm:7.0f}{dl:10.2f}{fl:7.0f}"
              f"{om:8d} /{ol:5d}")
print()
for label, v in agg.items():
    a = np.array(v, dtype=float)
    print(f"{label:9s} n={len(v):2d}   matched-version median score {np.median(a[:,0]):5.0f}"
          f"   live-reference median score {np.median(a[:,1]):5.0f}")
print()
print("tolerance for this axis = 20 deg (_ANGLE_TOLERANCE_DEG, ipsf_criteria.py).")
print("'joints>20 m/l' = how many of the 8 joints clear it, matched vs live reference.")
