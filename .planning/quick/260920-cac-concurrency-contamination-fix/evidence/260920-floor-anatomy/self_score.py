"""The number the decision turns on: if the champion uploads her own footage and it
is scored on the reference_relative axis (the wiring proposed in SUMMARY 11-3/12),
what score comes out?

SUMMARY 12-2 answered this by feeding the reference's own STORED angle matrix in as
the student. That is an identity comparison, so the deviation is 0 by construction
and the gate passed vacuously. The live path re-extracts the footage, and that
re-extraction disagrees with the stored reference by 2.3 to 15.8 degrees depending
on the motion. This script feeds that real floor through the production tally.

Versions are matched: the stored analyses predate the 2026-09-17 rot180 flip, so
they are compared against the reference version that was live when they ran.
Production functions only, no reimplementation.
"""
from __future__ import annotations
import json, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import deduction_engine, skeleton

app = H.app
facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
vers = json.load(open(f"{D}/ref_versions.json"))
live = H.load_references()

VER_BY_MOTION = {"ref-climb": "quick-260816-r7k"}
VER = "phase4_v1"


class QuantOK:
    quantificationStatus = "ok"
    bodyRelativeNotches = None
    windowMedianAngleDeltas = None


def ver_doc(m):
    v = dict(vers[m].get(VER_BY_MOTION.get(m, VER)) or {})
    if not v.get("angles"):
        return None
    for k in ("anglesJointKeys", "clipRange", "baseUntilS", "sharedBaseMotionId",
              "keypointReport", "anglesRealFps"):
        v.setdefault(k, live[m].get(k))
    return v


def score(sid, rdoc):
    s = students[sid]
    ang = H.student_matrix(s)
    a_flat = np.asarray(rdoc["angles"], dtype=float)
    nj = len(rdoc["anglesJointKeys"])
    dev, match, _user_seg, a_ref = app._deviation_against(
        ang, a_flat, nj,
        ref_boundary=H.ref_boundary_of(rdoc), ref_fps=H.ref_fps_of(rdoc),
    )
    merr: dict = {}
    md = app._build_deduction_measured_deviations(
        angles=ang, profile=None, assessments=None, dimension_scores=None,
        quantification=None, reference_dtw_match=match, reference_angles=a_ref,
        ref_fps=H.ref_fps_of(rdoc), measurement_error_out=merr,
    )
    axis = {k: v for k, v in md.items() if k.startswith("angle_vs_reference__")}
    b = deduction_engine.tally(
        QuantOK(), None, dimension_overall=100,
        measured_deviations=dict(md), dimension_scores=None,
        baseline_kind=app._baseline_kind_for_profile(None), measurement_error=merr,
    )
    return H.scalar(dev), len(axis), b.final, b.execution_raw_total, b.execution_capped_total


print(f"{'motion':24s}{'floor deg':>10s}{'axis md keys':>13s}{'FINAL':>7s}"
      f"{'exec raw':>10s}{'exec capped':>13s}   what the video is")
rows = []
for m in sorted(live):
    rd = ver_doc(m)
    if rd is None:
        continue
    cand = [r for r in facts if r["ref"] == m and r["label"] in ("self", "correct")]
    if not cand:
        continue
    r = cand[0]
    sc, nk, fin, raw, cap = score(r["id"], rd)
    rows.append(dict(motion=m, floor=sc, keys=nk, final=fin, raw=raw, capped=cap))
    print(f"{m:24s}{sc:10.2f}{nk:13d}{fin:7.0f}{raw:10.1f}{cap:13.1f}"
          f"   champion's own footage")

json.dump(rows, open(f"{D}/self_score.json", "w"))
print()
fins = [r["final"] for r in rows]
print(f"champion scored against her own footage: {min(fins):.0f} to {max(fins):.0f}")
print("SUMMARY 12-2 reported this gate as passing with md empty and score untouched.")
