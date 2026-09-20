"""Same audit, but with the video identified rather than assumed.

The cache is keyed by video hash, so a document tagged motion=ref-pdshape could be
the fault clip rather than the reference clip, and the two have different lengths.
The production hash function over the local fixture files removes that ambiguity for
the five clips we downloaded.
"""
import os, sys, json, collections
import numpy as np

REPO = "/Users/kimtaesung/Dev/SunityMotion"
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, f"{REPO}/backend/shared/python")
sys.path.insert(0, D)
from sunity_shared.analysis.technique_cache import compute_video_hash
import harness as H

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", f"{REPO}/firebase-sa.json")
from google.cloud import firestore

FX = "/Users/Shared/sunity-fx"
CLIPS = {}
for m in ("pdshape", "power-spin", "climb", "peter-pan", "kip-up"):
    p = f"{FX}/{m}-correct.mp4"
    if os.path.exists(p):
        CLIPS[compute_video_hash(p)] = f"ref-{m}"

refs = H.load_references()
dur = {}
for m, r in refs.items():
    nj = len(r["anglesJointKeys"])
    dur[m] = (len(r["angles"]) // nj) / float(r.get("anglesRealFps") or 14.94)

print("identified reference clips by content hash:")
for h, m in CLIPS.items():
    print(f"   {m:18s} {h[:16]}...  clip {dur[m]:5.2f}s  execPeakS "
          f"{(refs[m].get('clipRange') or {}).get('execPeakS')}")

db = firestore.Client(project="sunity-ai-coach")
rows = []
for s in db.collection("gemini_cache").stream():
    d = s.to_dict() or {}
    ms = d.get("moments") or []
    if not ms:
        continue
    vh = d.get("video_hash") or s.id.split("__")[0].split(":")[-1]
    motion = CLIPS.get(vh)
    if motion is None:
        continue
    ts = {mm.get("moment_key"): float(mm.get("timestamp_seconds"))
          for mm in ms
          if mm.get("moment_key") and mm.get("timestamp_seconds") is not None}
    rows.append((motion, s.id, ts, d.get("created_at")))

print(f"\ncache entries for those exact clips: {len(rows)}")
print(f"\n{'motion':16s}{'clip s':>7s}{'setup':>7s}{'hold':>7s}{'peak':>7s}{'release':>8s}"
      f"{'hold/clip':>10s}{'execPeakS':>10s}")
by = collections.defaultdict(list)
for motion, did, ts, ca in sorted(rows):
    c = dur[motion]
    h = ts.get("hold")
    by[motion].append(h)
    def g(k):
        v = ts.get(k)
        return f"{v:7.1f}" if v is not None else f"{'-':>7s}"
    hp = f"{h/c*100:9.0f}%" if h is not None else f"{'-':>10s}"
    print(f"{motion:16s}{c:7.2f}{g('setup')}{g('hold')}{g('peak')}{g('release'):>8s}"
          f"{hp}{str((refs[motion].get('clipRange') or {}).get('execPeakS')):>10s}")

print()
print("hold time spread on the SAME clip (this is what picks the scoring window):")
for m, v in by.items():
    a = np.array([x for x in v if x is not None])
    if a.size:
        print(f"   {m:16s} n={a.size}  hold {a.min():.1f}s ~ {a.max():.1f}s "
              f"(clip {dur[m]:.1f}s, execPeakS {(refs[m].get('clipRange') or {}).get('execPeakS')})")
