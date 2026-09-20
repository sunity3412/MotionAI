"""Pass 1 — collection_group('analyses') 경량 스캔(select projection).
uid/id/mode/referenceMotionId/bodyNormalizationProfile 만. joints3d 는 pass 2."""
import os, json, sys
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/Users/kimtaesung/Dev/SunityMotion/firebase-sa.json")
from google.cloud import firestore

OUT = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13/scan.json"
FIELDS = [
    "status", "mode", "referenceMotionId", "createdAt", "fileName",
    "anglesFrames", "anglesJointKeys", "bodyNormalizationProfile",
    "result.overallScore", "result.dimensionScores", "result.motionAlignment",
    "result.joints3dFrames", "result.coordDim", "result.space",
]
PAGE = 200
db = firestore.Client(project="sunity-ai-coach")
base = db.collection_group("analyses").select(FIELDS).order_by("__name__").limit(PAGE)
rows, last, n = [], None, 0
while True:
    q = base.start_after(last) if last is not None else base
    snaps = list(q.stream())
    if not snaps:
        break
    for s in snaps:
        last = s
        n += 1
        p = str(s.reference.path).split("/")
        if len(p) != 4 or p[0] != "users" or p[2] != "analyses":
            continue
        d = s.to_dict() or {}
        d["_uid"] = p[1]; d["_id"] = p[3]
        rows.append(d)
    if len(snaps) < PAGE:
        break
json.dump(rows, open(OUT, "w"), default=str)
print(f"스캔 문서 {n} · users/*/analyses 형식 {len(rows)}")
from collections import Counter
print("mode:", Counter(r.get("mode") for r in rows))
print("status:", Counter(r.get("status") for r in rows))
tgt = [r for r in rows if r.get("status")=="done" and r.get("referenceMotionId") and r.get("anglesFrames")]
print("target(done+ref+angles):", len(tgt))
print("  mode 분포:", Counter(r.get("mode") for r in tgt))
print("  ref 분포:", Counter(r.get("referenceMotionId") for r in tgt))
print("  bodyProfile 보유:", sum(1 for r in tgt if isinstance(r.get("bodyNormalizationProfile"), dict)))
print("  고유 uid:", len({r["_uid"] for r in tgt}))
