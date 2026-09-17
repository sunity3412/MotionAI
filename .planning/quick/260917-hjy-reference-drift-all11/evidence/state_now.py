import json, os, sys
import numpy as np
sys.path.insert(0, 'backend/scripts')
import e2e_app_path as e2e
db = e2e.firestore_client()
IDS = ["ref-climb","ref-combo","ref-elbow-twist-sister","ref-foxtop","ref-foxtop-split",
       "ref-invert","ref-kip-up","ref-pdshape","ref-peter-pan","ref-power-spin","ref-sideway-spin"]
rel = db.document("reference/_release").get()
print("reference/_release =", (rel.to_dict() if rel.exists else None))
prev = {f[:-5]: json.load(open(f"{sys.argv[1]}/{f}")) for f in os.listdir(sys.argv[1]) if f.endswith('.json') and not f.startswith('_')}
print(f"\n{'기준':24s}{'activeVersion':>16s}{'pipelineVersion':>18s}{'angles 변경?':>14s}{'pre_phase4 백업':>16s}")
for mid in IDS:
    d = db.document(f"reference/{mid}").get().to_dict() or {}
    old = prev.get(mid, {})
    changed = not np.array_equal(np.asarray(d.get("angles") or [], float),
                                 np.asarray(old.get("angles") or [], float))
    bk = db.document(f"reference/{mid}/versions/pre_phase4").get()
    print(f"{mid:24s}{str(d.get('activeVersion')):>16s}{str(d.get('pipelineVersion')):>18s}"
          f"{('★변경됨' if changed else '무변화'):>14s}{('있음' if bk.exists else '없음'):>16s}")
