"""Pass 2a — target 875건의 angles + 기준 11편 전체. get_all 배치."""
import os, json, time
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
scan = json.load(open(f"{D}/scan.json"))
tgt = [r for r in scan if r.get("status")=="done" and r.get("referenceMotionId") and r.get("anglesFrames")]
db = firestore.Client(project="sunity-ai-coach")

FIELDS = ["angles", "anglesJointKeys", "anglesFrames", "anglesExtractedBy"]
out = []
CH = 100
for i in range(0, len(tgt), CH):
    chunk = tgt[i:i+CH]
    refs = [db.document(f"users/{r['_uid']}/analyses/{r['_id']}") for r in chunk]
    got = {s.reference.path: (s.to_dict() or {}) for s in db.get_all(refs, field_paths=FIELDS)}
    for r in chunk:
        d = got.get(f"users/{r['_uid']}/analyses/{r['_id']}", {})
        a = d.get("angles")
        if not a:
            continue
        out.append({
            "id": r["_id"], "uid": r["_uid"], "ref": r["referenceMotionId"],
            "frames": d.get("anglesFrames"), "keys": d.get("anglesJointKeys"),
            "extractor": d.get("anglesExtractedBy"),
            "createdAt": r.get("createdAt"),
            "overall": (r.get("result") or {}).get("overallScore"),
            "dims": (r.get("result") or {}).get("dimensionScores"),
            "motionAlignment": (r.get("result") or {}).get("motionAlignment"),
            "body": r.get("bodyNormalizationProfile"),
            "angles": a,
        })
    print(f"  {min(i+CH,len(tgt))}/{len(tgt)}", flush=True)

json.dump(out, open(f"{D}/students.json","w"))
print("학생 저장:", len(out))

# 기준 11편 — 전체 문서(joints3d 포함)
rdocs = list(db.collection("reference").stream())
refs_out = {}
for s in rdocs:
    d = s.to_dict() or {}
    refs_out[d.get("motionId") or s.id] = d
json.dump(refs_out, open(f"{D}/references_full.json","w"), default=str)
print("기준 저장:", len(refs_out), list(refs_out))
