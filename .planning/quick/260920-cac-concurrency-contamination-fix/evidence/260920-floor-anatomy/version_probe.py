"""Was the floor introduced by a reference reprocessing, not by the instrument?

The live reference docs carry activeVersion/pipelineVersion and reprocessedAt.
The repo fixture set (backend/evals/realfixture/fixtures/reference/) was pulled on
2026-08-02 and carries the version that was live then. If the two disagree, every
student analysis in Firestore was scored against the OLD reference angles, and the
floor measured against the CURRENT reference angles is a version artifact, not an
instrument property.

Test: compare the repo-fixture reference angles against the live reference angles
for the same motion, frame for frame (identical row counts => identical grid).
"""
import json, os, sys
import numpy as np

REPO = "/Users/kimtaesung/Dev/SunityMotion"
FX = f"{REPO}/backend/evals/realfixture/fixtures/reference"
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H

refs = H.load_references()

print("=== live reference doc versions ===")
print(f"{'motion':24s}{'activeVersion':>16s}{'pipelineVersion':>18s}{'reprocessedAt':>30s}")
for m in sorted(refs):
    r = refs[m]
    print(f"{m:24s}{str(r.get('activeVersion')):>16s}{str(r.get('pipelineVersion')):>18s}"
          f"{str(r.get('reprocessedAt'))[:28]:>30s}")

print()
print("=== repo fixture (pulled 2026-08-02) vs live reference, same motion ===")
print(f"{'motion':24s}{'fixture ver':>14s}{'fx rows':>9s}{'live rows':>10s}"
      f"{'median |d| deg':>16s}{'p90':>8s}{'frac>10deg':>12s}")
for m in sorted(refs):
    p = f"{FX}/{m}.json"
    if not os.path.exists(p):
        continue
    fx = json.load(open(p))
    nj = len(fx["anglesJointKeys"])
    a_fx = np.asarray(fx["angles"], float).reshape(-1, nj)
    a_live = H.ref_matrix(refs[m])
    ver = str(fx.get("activeVersion"))
    if len(a_fx) != len(a_live):
        print(f"{m:24s}{ver:>14s}{len(a_fx):9d}{len(a_live):10d}"
              f"{'row count differs':>16s}")
        continue
    d = np.abs(a_fx - a_live)
    print(f"{m:24s}{ver:>14s}{len(a_fx):9d}{len(a_live):10d}"
          f"{float(np.median(d)):16.2f}{float(np.percentile(d,90)):8.2f}"
          f"{float((d>10).mean()):12.2f}")

print()
print("=== what the floor becomes when the OLD (phase4_v1) reference is used ===")
facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
print(f"{'motion':24s}{'floor vs live ref':>19s}{'floor vs 2026-08 ref':>22s}")
for m in sorted(refs):
    p = f"{FX}/{m}.json"
    if not os.path.exists(p):
        continue
    rows = [r for r in facts if r["ref"] == m and r["label"] in ("self", "correct")]
    if not rows:
        continue
    fx = json.load(open(p))
    a_stu = H.student_matrix(students[rows[0]["id"]])
    live_floor = float(np.median([r["scalar"] for r in rows]))
    dev_old, _ = H.deviate(a_stu, fx)     # fixture doc has the same shape as a ref doc
    print(f"{m:24s}{live_floor:19.2f}{H.scalar(dev_old):22.2f}")
