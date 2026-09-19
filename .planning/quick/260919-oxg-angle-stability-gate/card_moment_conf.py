"""카드가 고른 그 순간·그 관절의 신뢰도 — 표시가 왜 안 나오나를 정확히 짚는다.

각도 표시 조건 = 꼭짓점 + 이웃 2점이 **모두** conf >= 0.5 (양측 대칭).
ANGLE_BAKE_MAP: shoulder->(elbow,hip) · hip->(knee,shoulder) · knee->(ankle,hip) · elbow->(hand,shoulder)
"""
from __future__ import annotations
import os, sys
import numpy as np
sys.path.insert(0, os.path.abspath("backend/shared/python"))
os.environ.setdefault("FIREBASE_SA_PATH", os.path.abspath("firebase-sa.json"))
from sunity_shared import firestore_admin as fa  # noqa: E402
db = fa._db()  # noqa: SLF001
MAP={"shoulder":("elbow","hip"),"hip":("knee","shoulder"),"knee":("ankle","hip"),"elbow":("hand","shoulder")}
THR=0.5

def conf_at(kr, idx, name):
    joints=kr.get("joints") or []; c=kr.get("confidence")
    if not c or name not in joints: return None
    a=np.asarray(c,dtype=float)
    if a.ndim==1: a=a.reshape(-1,len(joints))
    if not (0<=idx<a.shape[0]): return None
    v=a[idx, joints.index(name)]
    return float(v) if np.isfinite(v) else None

rows=[]; miss_joint=0
for usnap in db.collection("users").limit(30).stream():
    for asnap in usnap.reference.collection("analyses").limit(25).stream():
        d=asnap.to_dict() or {}; res=d.get("result") or {}
        kr=res.get("keypointReport") or {}
        if not kr.get("confidence"): continue
        for c in res.get("faultZoomComparisons") or []:
            crit=str(c.get("criterion") or "")
            ui=c.get("userFrameIdx")
            if not crit.startswith("angle_vs_reference__") or not isinstance(ui,int): continue
            j=crit.split("__",1)[1]           # 예 left_knee
            side,_,suf = j.partition("_")
            if suf not in MAP: continue
            n1,n2 = MAP[suf]
            names=[j, f"{side}_{n1}", f"{side}_{n2}"]
            cs=[conf_at(kr, ui, n) for n in names]
            if any(x is None for x in cs):
                miss_joint+=1; continue
            rows.append({"aid":asnap.id[:8],"crit":j,"confs":cs,
                         "vertex":cs[0],"min":min(cs),"pass":all(x>=THR for x in cs),
                         "userMarked":c.get("userMarked")})
print(f"각도 대상 카드 {len(rows)}장  (관절 결측으로 제외 {miss_joint}장)")
if rows:
    vt=np.array([r["vertex"] for r in rows]); mn=np.array([r["min"] for r in rows])
    ok=np.array([r["pass"] for r in rows])
    print(f"꼭짓점 신뢰도  중앙값={np.median(vt):.3f}")
    print(f"3점 최소값     중앙값={np.median(mn):.3f}   ← 각도 표시를 여는 값")
    print()
    print(f"현행 0.5 로 3점 전부 통과 : {ok.sum()}/{len(rows)}  ({100*ok.mean():.0f}%)")
    for t in (0.45,0.40,0.35,0.30):
        p=(mn>=t).mean()
        print(f"  문턱 {t:.2f} 라면      : {int((mn>=t).sum())}/{len(rows)}  ({100*p:.0f}%)")
    print()
    print("실패 카드의 병목 (3점 중 어느 것이 최소인가):")
    from collections import Counter
    bn=Counter()
    for r in rows:
        if r["pass"]: continue
        k=int(np.argmin(r["confs"]))
        bn[("꼭짓점","이웃1","이웃2")[k]]+=1
    print("  ", dict(bn))
