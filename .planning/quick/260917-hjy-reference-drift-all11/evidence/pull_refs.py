"""기준 11편 Firestore 1회 읽기 -> 로컬 JSON. 이후 모든 분석은 로컬 파일만 읽는다."""
import json, os, sys
sys.path.insert(0, 'backend/scripts')
import e2e_app_path as e2e

OUT = sys.argv[1]
db = e2e.firestore_client()
docs = list(db.collection('reference').stream())
print(f"reference 컬렉션 문서 {len(docs)}개 (읽기 {len(docs)}회)")
meta = []
for d in docs:
    data = d.to_dict()
    path = os.path.join(OUT, f"{d.id}.json")
    with open(path, 'w') as f:
        json.dump(data, f, default=str)
    keys = sorted(data.keys())
    meta.append({
        "id": d.id,
        "bytes": os.path.getsize(path),
        "reprocessedAt": str(data.get("reprocessedAt")),
        "pipelineVersion": data.get("pipelineVersion"),
        "hasJoints3d": "joints3d" in data,
        "joints3dFrames": data.get("joints3dFrames"),
        "hasAngles": "angles" in data,
        "anglesFrames": data.get("anglesFrames"),
        "anglesJointKeys": data.get("anglesJointKeys"),
        "space": data.get("joints3dSpace") or data.get("space"),
        "keys": keys,
    })
with open(os.path.join(OUT, "_meta.json"), "w") as f:
    json.dump(meta, f, indent=1, ensure_ascii=False, default=str)
for m in meta:
    print(f"  {m['id']:22s} j3d={m['hasJoints3d']}({m['joints3dFrames']}) ang={m['hasAngles']}({m['anglesFrames']}) {m['pipelineVersion']} {m['reprocessedAt'][:19]}")
