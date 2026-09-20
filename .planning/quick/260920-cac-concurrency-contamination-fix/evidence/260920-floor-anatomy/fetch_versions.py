"""Pull the reference versions subcollection so the floor can be measured
like-for-like: the 875 stored analyses were extracted with ROT180 off (before
2026-09-17), so they must be compared against the pre-rot180 reference angles.

Also reports when the stored analyses were created, to find any that ran after
the 2026-09-17 flip (those would be the only rot180-on student extractions).
"""
import os, json, collections, datetime
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
db = firestore.Client(project="sunity-ai-coach")

MOTIONS = ["ref-climb", "ref-combo", "ref-elbow-twist-sister", "ref-foxtop",
           "ref-foxtop-split", "ref-invert", "ref-kip-up", "ref-pdshape",
           "ref-peter-pan", "ref-power-spin", "ref-sideway-spin"]

out = {}
for m in MOTIONS:
    subs = list(db.collection(f"reference/{m}/versions").stream())
    out[m] = {}
    for s in subs:
        d = s.to_dict() or {}
        out[m][s.id] = d
    print(f"{m:24s} versions: {sorted(out[m])}")
json.dump(out, open(f"{D}/ref_versions.json", "w"), default=str)

print()
print("=== stored analysis createdAt distribution ===")
scan = json.load(open(f"{D}/scan.json"))
b = {r["id"] for r in json.load(open(f"{D}/baseline.json"))}
months = collections.Counter()
after_flip = []
FLIP = datetime.datetime(2026, 9, 17, 5, 0, tzinfo=datetime.timezone.utc)
for r in scan:
    if r["_id"] not in b:
        continue
    ts = r.get("createdAt")
    try:
        dt = datetime.datetime.fromtimestamp(int(ts) / 1000, datetime.timezone.utc)
    except (TypeError, ValueError):
        months["unknown"] += 1
        continue
    months[dt.strftime("%Y-%m")] += 1
    if dt >= FLIP:
        after_flip.append((r["_id"], r["referenceMotionId"], dt.isoformat()))
for k in sorted(months):
    print(f"  {k}: {months[k]}")
print(f"\ncreated after the 2026-09-17 rot180 flip: {len(after_flip)}")
for x in after_flip[:20]:
    print("   ", x)
