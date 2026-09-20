"""The champion's own footage sometimes scores 10.

358 stored analyses of 정은지's own clips (the same handful of files re-run) include
46 that came out under 100, down to 10. Same video, same code path. This pulls the
deduction breakdown for the low ones and asks what fired.
"""
import os, json, collections
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
facts = json.load(open(f"{D}/facts.json"))
scan = {r["_id"]: r for r in json.load(open(f"{D}/scan.json"))}

low = [r for r in facts
       if r["label"] in ("correct", "self")
       and r["overall"] is not None and r["overall"] < 100]
low.sort(key=lambda r: r["overall"])
print(f"under-100 champion analyses: {len(low)}")

db = firestore.Client(project="sunity-ai-coach")
F = ["result.deductionBreakdown", "result.overallScore", "result.visionVeto",
     "result.comparison", "result.dimensionScores", "result.motionAlignment",
     "result.keypointReport", "createdAt", "result.aiSynthesisMeta"]
out = {}
CH = 50
for i in range(0, len(low), CH):
    ch = low[i:i + CH]
    refs = [db.document(f"users/{r['uid']}/analyses/{r['id']}") for r in ch]
    for s in db.get_all(refs, field_paths=F):
        out[s.id] = s.to_dict() or {}
json.dump(out, open(f"{D}/outliers.json", "w"), default=str)

print(f"\n{'motion':24s}{'score':>6s}{'vk':>10s}  criteria that fired")
for r in low:
    d = (out.get(r["id"]) or {}).get("result") or {}
    b = d.get("deductionBreakdown") or {}
    recs = b.get("records") or []
    s = " · ".join(
        f"{x.get('criterion')}={round(float(x.get('measuredValue') or 0), 1)}({x.get('points')})"
        for x in recs) or "(records 0)"
    same = "same file" if r["vk"] else "vk null"
    print(f"{r['ref']:24s}{r['overall']:6.0f}{same:>10s}  {s[:120]}")

print()
print("criteria frequency among champion analyses that lost points:")
c = collections.Counter()
for r in low:
    d = (out.get(r["id"]) or {}).get("result") or {}
    for x in ((d.get("deductionBreakdown") or {}).get("records") or []):
        c[x.get("criterion")] += 1
for k, v in c.most_common():
    print(f"   {str(k):40s} {v}")
