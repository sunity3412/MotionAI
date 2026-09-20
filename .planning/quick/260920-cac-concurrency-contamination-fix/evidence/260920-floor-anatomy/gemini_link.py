"""Does the champion score 10 exactly when Gemini failed?

Section 9-1 established the inversion: when the Gemini recognizer fails, the
FallbackRecognizer fills every joint sitting at 150 degrees or more as "must
extend", which manufactures a line dimension and an ipsf_absolute leg_extension
target on motions whose yaml deliberately has none (belle removed knee EXTEND from
pdshape and peter-pan on 2026-06-27). Nobody measured what that costs.

The stored analyses carry the recognizer's own record, so this reads it directly
for the 46 champion analyses that lost points and, as a control, for a sample that
scored 100 on the same files.
"""
import os, json, collections
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
facts = json.load(open(f"{D}/facts.json"))

champ = [r for r in facts if r["label"] in ("correct", "self") and r["overall"] is not None]
low = [r for r in champ if r["overall"] < 100]
hi = [r for r in champ if r["overall"] == 100]
# control: same motions, same files, full marks
bym = collections.defaultdict(list)
for r in hi:
    bym[r["ref"]].append(r)
ctrl = [x for m in bym for x in bym[m][:4]]
targets = low + ctrl
print(f"low {len(low)} + control {len(ctrl)} = {len(targets)} docs")

db = firestore.Client(project="sunity-ai-coach")
F = ["geminiB", "geminiC", "techniqueProfile", "result.overallScore",
     "result.dimensionScores", "result.tips"]
out = {}
for i in range(0, len(targets), 50):
    ch = targets[i:i + 50]
    refs = [db.document(f"users/{r['uid']}/analyses/{r['id']}") for r in ch]
    for s in db.get_all(refs, field_paths=F):
        out[s.id] = s.to_dict() or {}
json.dump(out, open(f"{D}/gemini_link.json", "w"), default=str)


def profile_of(d):
    tp = d.get("techniqueProfile") or {}
    je = tp.get("jointExpectations") or {}
    ext = sorted(k for k, v in je.items() if str(v).lower() == "extend")
    return tp.get("category"), ext


print(f"\n{'group':8s}{'motion':22s}{'score':>6s}{'category':>16s}  EXTEND joints")
rows = []
for tag, group in (("LOW", low), ("100", ctrl)):
    for r in sorted(group, key=lambda x: x["overall"]):
        d = out.get(r["id"]) or {}
        cat, ext = profile_of(d)
        rows.append((tag, r["ref"], r["overall"], cat, tuple(ext)))
        if tag == "LOW" or len(ext) > 0:
            print(f"{tag:8s}{r['ref']:22s}{r['overall']:6.0f}{str(cat):>16s}  {ext}")

print()
print("category frequency")
for tag in ("LOW", "100"):
    c = collections.Counter(x[3] for x in rows if x[0] == tag)
    n = sum(c.values())
    print(f"  {tag}: " + " · ".join(f"{k}={v}/{n}" for k, v in c.most_common()))
print()
print("has at least one EXTEND joint")
for tag in ("LOW", "100"):
    g = [x for x in rows if x[0] == tag]
    e = sum(1 for x in g if x[4])
    print(f"  {tag}: {e}/{len(g)}")
