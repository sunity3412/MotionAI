"""If the EXTEND criterion ignored the phase hint, what would change?

Repair option 1 in section 17-8 is: measure the EXTEND criterion on the geometric
hold window only (dimensions.hold_window, the lowest-variance segment), ignoring the
recognizer's phase hint. Its blast radius is measurable on the stored corpus without
re-running anything.

Scope: ref-power-spin, the only motion whose yaml carries EXTEND joints, and the only
one where the criterion is by design rather than by recognizer accident. For those
analyses the EXTEND joints are known from the yaml (both knees), so the geometric
score can be recomputed exactly.
"""
from __future__ import annotations
import json, sys, collections
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import dimensions, technique
from sunity_shared.analysis.skeleton import JOINT_KEYS

KNEES = technique.TechniqueProfile(
    name="파워스핀", category="recognized",
    joint_expectations={"left_knee": "extend", "right_knee": "extend"},
    motion_id="ref-power-spin",
)

facts = json.load(open(f"{D}/facts.json"))
scan = {r["_id"]: r for r in json.load(open(f"{D}/scan.json"))}
students = {s["id"]: s for s in H.load_students()}

rows = []
for r in facts:
    if r["ref"] != "ref-power-spin":
        continue
    dims = (scan[r["id"]].get("result") or {}).get("dimensionScores") or {}
    if "line" not in dims:
        continue
    a = H.student_matrix(students[r["id"]])
    geo = dimensions.line_score(a, KNEES)
    dev = dimensions.extension_deviation(a, KNEES)
    worst = float(max(dev[JOINT_KEYS.index("left_knee")],
                      dev[JOINT_KEYS.index("right_knee")]))
    ded = -min(20.0, round(max(0.0, worst - 20.0) * 1.2, 1))
    rows.append(dict(id=r["id"], label=r["label"], stored_line=dims["line"],
                     stored_score=r.get("overall"), geo_line=geo,
                     geo_deduction=ded))

print(f"ref-power-spin analyses carrying a line dimension: {len(rows)}")
print()
print(f"{'label':10s}{'n':>5s}{'stored line=0':>15s}{'geometric line=0':>18s}"
      f"{'stored line med':>17s}{'geometric med':>15s}")
by = collections.defaultdict(list)
for r in rows:
    by[r["label"]].append(r)
for lab, v in sorted(by.items()):
    sl = [x["stored_line"] for x in v]
    gl = [x["geo_line"] for x in v if x["geo_line"] is not None]
    print(f"{lab:10s}{len(v):5d}{sum(1 for x in sl if x == 0):15d}"
          f"{sum(1 for x in gl if x == 0):18d}"
          f"{np.median(sl):17.0f}{np.median(gl):15.0f}")

print()
print("what option 1 would change, per analysis:")
chg = collections.Counter()
for r in rows:
    if r["geo_line"] is None:
        chg["geometric gives no line"] += 1
    elif r["stored_line"] == 0 and r["geo_line"] > 0:
        chg[f"{r['label']}: 0 -> {r['geo_line']} (false positive removed)"] += 1
    elif r["stored_line"] > 0 and r["geo_line"] == 0:
        chg[f"{r['label']}: {r['stored_line']} -> 0 (fault newly caught)"] += 1
    elif r["stored_line"] == r["geo_line"]:
        chg[f"{r['label']}: unchanged"] += 1
    else:
        chg[f"{r['label']}: {r['stored_line']} -> {r['geo_line']}"] += 1
for k, v in sorted(chg.items(), key=lambda kv: -kv[1]):
    print(f"   {v:4d}  {k}")

print()
print("the point that decides it: does the geometric window still catch the fault clip?")
for lab in ("correct", "fault"):
    v = [x for x in rows if x["label"] == lab]
    if not v:
        continue
    gl = [x["geo_line"] for x in v if x["geo_line"] is not None]
    gd = [x["geo_deduction"] for x in v]
    print(f"   {lab:8s} n={len(v):3d}  geometric line {min(gl)}~{max(gl)}  "
          f"leg_extension {min(gd):.1f}~{max(gd):.1f}")
