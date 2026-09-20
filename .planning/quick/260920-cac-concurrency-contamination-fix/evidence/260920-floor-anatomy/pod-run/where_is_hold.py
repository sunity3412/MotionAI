"""Where did the scored hold window sit, and what does the geometric one say?

The doc stores mission.baselineDeviation = 91.31 against targetValue 180, so the
scored right knee was 88.69 degrees. The geometric hold window (dimensions.hold_window,
lowest variance) puts the same knee at about 171. Somewhere between them is a window
the Gemini phase hint pointed at. This locates it by searching the stored angle series
for the window whose mean right knee reproduces 88.69.
"""
from __future__ import annotations
import os, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import dimensions
from sunity_shared.analysis.skeleton import JOINT_KEYS

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
                      "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore

db = firestore.Client(project="sunity-ai-coach")
d = db.document("users/mDYDeZWzF6b3qToAy4xKu7FQK3f2/"
                "analyses/db8b271f5db345c285086592f9a33749").get().to_dict() or {}
nj = len(d["anglesJointKeys"])
a = np.asarray(d["angles"], float).reshape(-1, nj)
T = len(a)
rk = JOINT_KEYS.index("right_knee")
lk = JOINT_KEYS.index("left_knee")
TARGET = 88.69
fps = T / (d.get("result", {}).get("keypointReport", {}).get("frames") or T) * 0  # unused

print(f"stored series: T={T}")
gs, ge = dimensions.hold_window(a)
print(f"geometric hold window      [{gs:3d},{ge:3d})  right_knee mean "
      f"{np.nanmean(a[gs:ge, rk]):6.1f}  left {np.nanmean(a[gs:ge, lk]):6.1f}")

# every window of the geometric width, ranked by how close its mean knee is to 88.69
w = ge - gs
best = []
for s in range(0, T - w + 1):
    m = float(np.nanmean(a[s:s + w, rk]))
    best.append((abs(m - TARGET), s, m, float(np.nanmean(a[s:s + w, lk]))))
best.sort()
print(f"\nwindows of width {w} whose mean right knee lands on {TARGET}:")
for diff, s, m, ml in best[:4]:
    frac = s / T
    print(f"   [{s:3d},{s+w:3d})  = {frac*100:4.0f}%~{(s+w)/T*100:3.0f}% of the clip"
          f"   right {m:6.1f}  left {ml:6.1f}")

print(f"\nright knee over the clip, in tenths:")
for i in range(10):
    s, e = int(T * i / 10), int(T * (i + 1) / 10)
    seg = a[s:e, rk]
    print(f"   {i*10:3d}-{(i+1)*10:3d}%  mean {np.nanmean(seg):6.1f}  min {np.nanmin(seg):6.1f}")

print(f"\nfraction of the clip with right knee under 160: "
      f"{float((a[:, rk] < 160).mean())*100:.0f}%")
print(f"geometric window verdict : knee {np.nanmean(a[gs:ge, rk]):.1f} "
      f"-> deficit {max(0, 180-np.nanmean(a[gs:ge, rk])):.1f} -> under tol 20, no deduction")
print(f"scored window verdict    : knee {TARGET} -> deficit {180-TARGET:.1f} "
      f"-> over tol, -20 and line_score 0 (micro-bent under 160)")
