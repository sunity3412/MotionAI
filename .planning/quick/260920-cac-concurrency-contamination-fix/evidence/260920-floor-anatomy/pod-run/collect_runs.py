"""Pull together what the pod runs produced.

repeat_results.jsonl  — the champion's own footage, one motion per block, through the
                        production app path on today's code.
jitter_results.jsonl  — five stream-copies of the power-spin clip. Identical frames,
                        different bytes, so each one misses the technique cache and
                        gets a fresh recognizer call. What varies is the recognizer.

For the jitter runs the recognizer's answer is recoverable: the cache document is
keyed by the file's hash, so each variant's hold timestamp can be read back and put
next to the score it produced.
"""
import os, sys, json, glob
import numpy as np

REPO = "/Users/kimtaesung/Dev/SunityMotion"
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, f"{REPO}/backend/shared/python")
from sunity_shared.analysis.technique_cache import compute_video_hash

os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", f"{REPO}/firebase-sa.json")
from google.cloud import firestore
db = firestore.Client(project="sunity-ai-coach")


def load(name):
    p = f"{D}/{name}"
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p):
        line = line.strip()
        if line.startswith("{"):
            out.append(json.loads(line))
    return out


def breakdown(uid, aid):
    d = db.document(f"users/{uid}/analyses/{aid}").get().to_dict() or {}
    r = d.get("result") or {}
    b = r.get("deductionBreakdown") or {}
    recs = [(x.get("criterion"), round(float(x.get("measuredValue") or 0), 1),
             x.get("points")) for x in (b.get("records") or [])]
    return r.get("overallScore"), r.get("dimensionScores") or {}, recs


rep = load("repeat_results.jsonl")
if rep:
    print("=== the champion's own footage, production app path, today's code ===")
    print(f"{'motion':16s}{'run':>4s}{'score':>7s}{'line':>6s}{'angle':>7s}{'stab':>6s}"
          f"   deductions")
    for r in rep:
        if r.get("status") != "done":
            print(f"{str(r.get('motion')):16s}{r.get('run',0):4d}  {r.get('status')} "
                  f"{r.get('errorCode')}")
            continue
        sc, dims, recs = breakdown(r["uid"], r["analysisId"])
        s = " · ".join(f"{c}={v}({p})" for c, v, p in recs) or "(none)"
        print(f"{str(r.get('motion')):16s}{r.get('run',0):4d}{str(sc):>7s}"
              f"{str(dims.get('line','-')):>6s}{str(dims.get('angle','-')):>7s}"
              f"{str(dims.get('stability','-')):>6s}   {s[:70]}")

jit = load("jitter_results.jsonl")
if jit:
    print()
    print("=== five byte-distinct copies of the SAME power-spin clip (cache bypassed) ===")
    hashes = {i: compute_video_hash(f"/Users/Shared/sunity-fx/ps-v{i}.mp4")
              for i in range(1, 6) if os.path.exists(f"/Users/Shared/sunity-fx/ps-v{i}.mp4")}
    cache = {}
    for s in db.collection("gemini_cache").stream():
        d = s.to_dict() or {}
        vh = d.get("video_hash")
        ms = d.get("moments") or []
        if vh and ms:
            ts = {m.get("moment_key"): m.get("timestamp_seconds") for m in ms}
            cache.setdefault(vh, []).append(ts)
    print(f"{'variant':9s}{'score':>7s}{'line':>6s}{'hold s':>8s}{'peak s':>8s}"
          f"   deductions")
    holds, scores = [], []
    for r in jit:
        i = r.get("variant")
        if r.get("status") != "done":
            print(f"#{i:<8d}  {r.get('status')} {r.get('errorCode')}")
            continue
        sc, dims, recs = breakdown(r["uid"], r["analysisId"])
        ts_list = cache.get(hashes.get(i), [])
        ts = ts_list[0] if ts_list else {}
        h, pk = ts.get("hold"), ts.get("peak")
        holds.append(h); scores.append(sc)
        s = " · ".join(f"{c}={v}({p})" for c, v, p in recs) or "(none)"
        print(f"#{i:<8d}{str(sc):>7s}{str(dims.get('line','-')):>6s}"
              f"{(f'{h:8.1f}' if h is not None else '       -')}"
              f"{(f'{pk:8.1f}' if pk is not None else '       -')}   {s[:60]}")
    hv = [h for h in holds if h is not None]
    sv = [s for s in scores if s is not None]
    if hv:
        print(f"\nhold timestamp on identical footage: {min(hv):.1f}s ~ {max(hv):.1f}s "
              f"(clip 10.60s, reference clipRange execPeakS 7)")
    if sv:
        print(f"score on identical footage: {min(sv)} ~ {max(sv)}   "
              f"(100 = no deduction, 80 = leg_extension fired)")
        print(f"false positives: {sum(1 for s in sv if s < 100)}/{len(sv)}")
