"""배포 전(pre_phase4 백업) / 배포 후(라이브) 기준 각도를 1회 읽기로 로컬에 박제.

이후 모든 분석은 로컬 파일만 읽는다 (Firestore 읽기 최소화).
"""
import json, sys
from pathlib import Path
sys.path.insert(0, 'backend/scripts')
import e2e_app_path as e2e

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
db = e2e.firestore_client()

def angles_of(data):
    flat = data.get("angles"); keys = data.get("anglesJointKeys") or data.get("jointKeys")
    fr = data.get("anglesFrames") or data.get("numFrames")
    if not flat or not keys or not fr: return None
    return {"angles": flat, "jointKeys": list(keys), "numFrames": int(fr),
            "fps": data.get("anglesFps") or data.get("fps")}

live, prev = {}, {}
reads = 0
for d in db.collection("reference").stream():
    reads += 1
    if d.id.startswith("_"): continue
    a = angles_of(d.to_dict())
    if a: live[d.id] = a
    snap = db.collection("reference").document(d.id).collection("versions").document("pre_phase4").get()
    reads += 1
    if snap.exists:
        a2 = angles_of(snap.to_dict())
        if a2: prev[d.id] = a2

json.dump(live, open(OUT/"ref_live_deployed.json","w"))
json.dump(prev, open(OUT/"ref_pre_phase4.json","w"))
print(f"Firestore 읽기 {reads}회")
print(f"배포 후(라이브) {len(live)}편: {sorted(live)}")
print(f"배포 전(pre_phase4) {len(prev)}편: {sorted(prev)}")
missing = sorted(set(live) - set(prev))
if missing: print(f"★ 백업 없는 동작: {missing}")
