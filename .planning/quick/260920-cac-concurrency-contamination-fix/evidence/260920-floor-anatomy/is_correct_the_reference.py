"""Is fixtures/phase15/{motion}/correct.mp4 the same footage as reference/ref-{motion}.mp4?

Test by content, not by filename: decimate the stored reference angle series to the
student grid (2/3 rate) and compare against the 'correct' fixture's stored angles
frame-by-frame. Same footage -> near-identical traces. Different take -> not.
Control: do the same against the 'fault' fixture.
"""
import json, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H

facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()

PAIRS = ["ref-kip-up", "ref-peter-pan", "ref-power-spin", "ref-climb",
         "ref-elbow-twist-sister", "ref-pdshape"]
SELF = ["ref-foxtop", "ref-foxtop-split", "ref-invert", "ref-sideway-spin", "ref-combo"]


def pick(ref, label):
    rows = [r for r in facts if r["ref"] == ref and r["label"] == label]
    return rows[0] if rows else None


def resample_to(a, n):
    """Nearest-neighbour decimation of (T,J) onto n rows — what an fps step does."""
    idx = np.clip(np.round(np.linspace(0, len(a) - 1, n)).astype(int), 0, len(a) - 1)
    return a[idx]


def compare(a, b):
    """Per-joint median |delta| after length-matching by resampling the longer one."""
    n = min(len(a), len(b))
    A, B = resample_to(a, n), resample_to(b, n)
    d = np.abs(A - B)
    return float(np.median(d)), float(np.median(np.median(d, axis=0)))


print(f"{'motion':24s}{'ref T':>7s}{'stu T':>7s}{'T ratio':>9s}"
      f"{'median|d| vs ref':>18s}{'per-joint med':>15s}")
for m in PAIRS + SELF:
    rd = refs[m]
    a_ref = H.ref_matrix(rd)
    for label in ("correct", "fault", "self"):
        row = pick(m, label)
        if not row:
            continue
        a_stu = H.student_matrix(students[row["id"]])
        raw, perj = compare(a_ref, a_stu)
        print(f"{m + '/' + label:24s}{len(a_ref):7d}{len(a_stu):7d}"
              f"{len(a_stu)/len(a_ref):9.4f}{raw:18.2f}{perj:15.2f}")
    print()

print("Reading: 'median|d| vs ref' near 0 => same footage (only resampling differs).")
print("         large => genuinely different video.")
