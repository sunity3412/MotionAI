"""신뢰도가 낮으면 좌표가 실제로 틀렸나 — 문턱을 내려도 되는지의 결정적 사실.

신뢰도는 정확도가 아니다. 저신뢰 프레임의 각도가 시간축 이웃과 크게 어긋나면
좌표가 튄 것이고(문턱 유지가 옳다), 매끄러운 궤적 위에 앉아 있으면
문턱이 멀쩡한 데이터를 버리는 것이다(문턱을 내려야 한다).

지표 = |angle(t) - median(angle, t±2)| (도). 같은 관절의 시간적 자기일관성.
"""
from __future__ import annotations
import os, sys
import numpy as np
sys.path.insert(0, os.path.abspath("backend/shared/python"))
os.environ.setdefault("FIREBASE_SA_PATH", os.path.abspath("firebase-sa.json"))
from sunity_shared import firestore_admin as fa  # noqa: E402
db = fa._db()  # noqa: SLF001

buckets={k:[] for k in ("<0.30","0.30-0.35","0.35-0.40","0.40-0.45","0.45-0.50","0.50-0.60","0.60-0.70",">=0.70")}
def bk(c):
    for lo,hi,k in ((0,.30,"<0.30"),(.30,.35,"0.30-0.35"),(.35,.40,"0.35-0.40"),(.40,.45,"0.40-0.45"),
                    (.45,.50,"0.45-0.50"),(.50,.60,"0.50-0.60"),(.60,.70,"0.60-0.70"),(.70,9,">=0.70")):
        if lo<=c<hi: return k
    return ">=0.70"

docs=0
for usnap in db.collection("users").limit(30).stream():
    for asnap in usnap.reference.collection("analyses").limit(25).stream():
        d=asnap.to_dict() or {}; res=d.get("result") or {}
        kr=res.get("keypointReport") or {}
        ang=d.get("angles"); keys=d.get("anglesJointKeys"); nf=d.get("anglesFrames")
        conf=kr.get("confidence"); joints=kr.get("joints") or []
        if not (ang and keys and nf and conf and joints): continue
        A=np.asarray(ang,dtype=float).reshape(int(nf), len(keys))
        C=np.asarray(conf,dtype=float)
        if C.ndim==1: C=C.reshape(-1,len(joints))
        # angles(9fps) 와 keypointReport(rep fps) 는 축이 다르다 — 비율로 대응
        if A.shape[0]<7 or C.shape[0]<7: continue
        docs+=1
        ratio=C.shape[0]/A.shape[0]
        for jn,k in enumerate(keys):
            if k not in joints: continue
            ci=joints.index(k)
            series=A[:,jn]
            for t in range(2, A.shape[0]-2):
                w=series[t-2:t+3]
                if not np.all(np.isfinite(w)): continue
                dev=abs(series[t]-np.median(np.delete(w,2)))
                ct=int(round(t*ratio))
                if not (0<=ct<C.shape[0]): continue
                c=C[ct,ci]
                if not np.isfinite(c): continue
                buckets[bk(float(c))].append(float(dev))
        if docs>=25: break
    if docs>=25: break

print(f"docs={docs}   지표 = |각도(t) − 이웃 중앙값| (도, 낮을수록 좌표가 안정)\n")
print(f"{'신뢰도 구간':<12}{'표본':>8}{'중앙값':>9}{'p75':>8}{'p90':>8}{'>20도 비율':>11}")
for k in ("<0.30","0.30-0.35","0.35-0.40","0.40-0.45","0.45-0.50","0.50-0.60","0.60-0.70",">=0.70"):
    v=np.asarray(buckets[k])
    if v.size<30: 
        print(f"{k:<12}{v.size:>8}  (표본 부족)"); continue
    mark=""
    if k=="0.45-0.50": mark="  <- 문턱 바로 아래"
    if k=="0.50-0.60": mark="  <- 문턱 바로 위"
    print(f"{k:<12}{v.size:>8}{np.median(v):>9.2f}{np.percentile(v,75):>8.2f}{np.percentile(v,90):>8.2f}{100*(v>20).mean():>10.1f}%{mark}")
