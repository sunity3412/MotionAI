"""반증 r13-F — 바닥이 '포즈 추출 불일치'가 아니라 '저장된 기준 각도가 현재 각도코드와
다른 것'이라면, 기준 angles 를 그 doc 자신의 joints3d 로 **현재 운영 함수**가 다시
계산한 값으로 갈아끼우면 바닥이 내려가야 한다.
"""
import json, sys, collections
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np
from sunity_shared.analysis import features, skeleton

refs = H.load_references(); by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
g = collections.defaultdict(lambda: collections.defaultdict(list))
for f in facts: g[f["ref"]][f["label"]].append(f)

def recomputed(r):
    keys=r["joints3dKeys"]; nfr=r["joints3dFrames"]; dim=int(r.get("coordDim") or 3)
    K=np.asarray(r["joints3d"],float).reshape(nfr,len(keys),dim)
    name2i={n:i for i,n in enumerate(keys)}
    Kp=K[:,[name2i[n] for n in skeleton.KEYPOINT_NAMES],:]
    return np.asarray(features.compute_joint_angles(Kp),float)

def spear(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    return float(np.corrcoef(np.argsort(np.argsort(x)).astype(float),
                             np.argsort(np.argsort(y)).astype(float))[0,1])

print("=== self / correct 바닥: 저장 기준 vs 재계산 기준")
print(f"{'motion':24s}{'label':>8s}{'n':>4s}{'저장기준':>9s}{'재계산기준':>11s}{'감소%':>8s}{'recomp미스':>11s}")
rows=[]
for mid, r in sorted(refs.items()):
    B = recomputed(r)
    fps = H.ref_fps_of(r); rb = H.ref_boundary_of(r)
    A = H.ref_matrix(r)
    mism = float(np.nanmedian(np.abs(B[:min(len(A),len(B))]-A[:min(len(A),len(B))])))
    for lab in ("self","correct"):
        items = g[mid].get(lab)
        if not items: continue
        sel = items[:6]
        old, new = [], []
        for f in sel:
            U = H.student_matrix(by_id[f["id"]])
            old.append(f["scalar"])
            new.append(H.scalar(H.deviate(U, B, ref_boundary=rb, ref_fps=fps)[0]))
        o, n2 = float(np.median(old)), float(np.median(new))
        rows.append((mid,lab,o,n2,mism))
        print(f"{mid:24s}{lab:>8s}{len(sel):4d}{o:9.2f}{n2:11.2f}{100*(o-n2)/o:7.1f}%{mism:11.2f}")

print("\n=== 예측력 비교 (동작별 바닥 vs 예측자)")
base = {}
for mid,lab,o,n2,mism in rows:
    if mid not in base or lab=="correct": base[mid]=(o,mism)
mids=sorted(base); fl=[base[m][0] for m in mids]; ms=[base[m][1] for m in mids]
print("  motions:", len(mids))
print(f"  spearman(바닥, 재계산미스매치) = {spear(fl,ms):.3f}")
