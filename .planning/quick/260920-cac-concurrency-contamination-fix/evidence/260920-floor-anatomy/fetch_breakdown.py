"""What did production actually deduct, and on which criteria?

Section 14-5 reconstructed the score with the vision_pointed_joints branch off, so
it is a lower bound for this axis alone. The live docs record what production really
did: result.deductionBreakdown.records carries the criterion id and the measured
value for every deduction that fired, with every branch on.

Sampled per (motion, label) rather than swept, to stay well inside the Firestore
free-tier read cap.
"""
import os, json, collections
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
facts = json.load(open(f"{D}/facts.json"))
scan = {r["_id"]: r for r in json.load(open(f"{D}/scan.json"))}

PER_GROUP = 4
groups = collections.defaultdict(list)
for r in facts:
    if r["label"] in ("correct", "fault", "self"):
        groups[(r["ref"], r["label"])].append(r)

targets = []
for k, rows in groups.items():
    rows.sort(key=lambda r: -(scan[r["id"]].get("createdAt") or 0))
    targets.extend(rows[:PER_GROUP])
print("fetching", len(targets), "docs")

db = firestore.Client(project="sunity-ai-coach")
F = ["result.deductionBreakdown", "result.overallScore", "result.dimensionScores",
     "result.comparison", "result.visionVeto", "result.motionAlignment", "createdAt"]
out = {}
CH = 50
for i in range(0, len(targets), CH):
    ch = targets[i:i + CH]
    refs = [db.document(f"users/{r['uid']}/analyses/{r['id']}") for r in ch]
    for s in db.get_all(refs, field_paths=F):
        out[s.id] = s.to_dict() or {}
json.dump(out, open(f"{D}/breakdown.json", "w"), default=str)
print("saved", len(out))
