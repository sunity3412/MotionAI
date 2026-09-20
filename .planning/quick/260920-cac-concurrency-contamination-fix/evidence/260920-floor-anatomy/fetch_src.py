import os, json, collections
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
scan=json.load(open(f"{D}/scan.json"))
tgt=[r for r in scan if r.get("status")=="done" and r.get("referenceMotionId") and r.get("anglesFrames")]
db=firestore.Client(project="sunity-ai-coach")
F=["videoKey","sourceLabel","fileName","learningOptIn","createdAt"]
out={}
CH=150
for i in range(0,len(tgt),CH):
    ch=tgt[i:i+CH]
    refs=[db.document(f"users/{r['_uid']}/analyses/{r['_id']}") for r in ch]
    for s in db.get_all(refs, field_paths=F):
        out[s.id]=s.to_dict() or {}
json.dump(out, open(f"{D}/src.json","w"), default=str)
print("fetched", len(out))
