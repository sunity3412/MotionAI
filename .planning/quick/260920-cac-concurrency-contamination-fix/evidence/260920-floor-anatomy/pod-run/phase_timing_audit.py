"""Is the phase recognizer's timing wrong only on power-spin, or everywhere?

Today's fresh run put all four phases of a 10.6 second clip inside the first 2.3
seconds. The 170 legacy gemini_cache documents still carry the moments the
recognizer returned for earlier analyses, so the pattern can be checked without
spending anything.

Reference clip lengths come from the reference docs (anglesFrames / anglesRealFps),
and each reference also carries its own clipRange, which is what the phase times
should look like.
"""
import os, sys, json, collections
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS",
                      "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore

refs = H.load_references()
clip = {}
for m, r in refs.items():
    nj = len(r["anglesJointKeys"])
    T = len(r["angles"]) // nj
    fps = float(r.get("anglesRealFps") or 14.94)
    clip[m] = dict(dur=T / fps, cr=r.get("clipRange") or {})

db = firestore.Client(project="sunity-ai-coach")
docs = [s for s in db.collection("gemini_cache").stream()]
print(f"gemini_cache docs: {len(docs)}")

rows = []
for s in docs:
    d = s.to_dict() or {}
    ms = d.get("moments") or []
    if not ms:
        continue
    motion = d.get("motion")
    ts = {}
    for mm in ms:
        k = mm.get("moment_key")
        t = mm.get("timestamp_seconds")
        if k is not None and t is not None:
            ts[k] = float(t)
    if not ts:
        continue
    rows.append((motion, s.id, ts))

print(f"docs carrying moments: {len(rows)}")
print()
hdr = f"{'motion':24s}{'clip s':>7s}{'setup':>7s}{'hold':>7s}{'peak':>7s}{'release':>8s}{'last/clip':>10s}{'execPeakS':>10s}"
print(hdr)
frac = collections.defaultdict(list)
for motion, did, ts in sorted(rows, key=lambda r: str(r[0])):
    dur = clip.get(motion, {}).get("dur")
    cr = clip.get(motion, {}).get("cr") or {}
    last = max(ts.values()) if ts else float("nan")
    f = last / dur if dur else float("nan")
    if motion:
        frac[motion].append(f)
    def g(k):
        v = ts.get(k)
        return f"{v:7.1f}" if v is not None else f"{'-':>7s}"
    print(f"{str(motion):24s}{(dur or float('nan')):7.1f}{g('setup')}{g('hold')}{g('peak')}"
          f"{g('release'):>8s}{f*100:9.0f}%{str(cr.get('execPeakS')):>10s}")

print()
print("last phase time as a fraction of the clip, by motion (1.0 = the phases span the clip)")
for m, v in sorted(frac.items(), key=lambda kv: np.median(kv[1])):
    a = np.array(v)
    print(f"   {m:24s} n={len(a):3d}  median {np.median(a)*100:5.0f}%  "
          f"min {a.min()*100:4.0f}%  max {a.max()*100:4.0f}%")
