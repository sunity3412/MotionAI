"""라이브 무접촉 확인 + 새 버전 검증."""
import json, os, sys
import numpy as np
sys.path.insert(0, 'backend/scripts')
import e2e_app_path as e2e
db = e2e.firestore_client()
IDS = ["ref-climb","ref-combo","ref-elbow-twist-sister","ref-foxtop","ref-foxtop-split",
       "ref-invert","ref-kip-up","ref-pdshape","ref-peter-pan","ref-power-spin","ref-sideway-spin"]
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)

rel = db.document("reference/_release").get()
print("reference/_release =", rel.to_dict() if rel.exists else "(없음)")
print()
print(f"{'기준':24s}{'라이브 pipelineVersion':>24s}{'라이브 변경?':>12s}{'새버전 프레임':>12s}{'joints3d':>10s}")
prev = {f[:-5]: json.load(open(f"{sys.argv[2]}/{f}")) for f in os.listdir(sys.argv[2]) if f.endswith('.json') and not f.startswith('_')}
for mid in IDS:
    top = db.document(f"reference/{mid}").get().to_dict() or {}
    v = db.document(f"reference/{mid}/versions/rot180_v1").get()
    vd = v.to_dict() if v.exists else {}
    if vd:
        json.dump(vd, open(os.path.join(OUT, f"{mid}.json"), "w"), default=str)
    old = prev.get(mid, {})
    same = (np.array_equal(np.asarray(top.get("angles") or [], float),
                           np.asarray(old.get("angles") or [], float))
            and top.get("pipelineVersion") == old.get("pipelineVersion"))
    print(f"{mid:24s}{str(top.get('pipelineVersion')):>24s}{('무변화' if same else '★변경됨'):>12s}"
          f"{str(vd.get('anglesFrames')):>12s}{('있음' if vd.get('joints3d') else '없음'):>10s}")
