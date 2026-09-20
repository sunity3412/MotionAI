"""반증 r13-F' — 재계산에 운영 후처리(temporal_fill)를 붙여 다시 대조하고,
그 재계산 기준으로 갈아끼웠을 때 바닥이 내려가는지 본다."""
import json, sys, collections
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np
from sunity_shared.analysis import features, skeleton
from sunity_shared.analysis.temporal import temporal_fill

refs = H.load_references(); by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
g = collections.defaultdict(lambda: collections.defaultdict(list))
for f in facts: g[f["ref"]][f["label"]].append(f)

def recomputed(r, fill=True):
    keys=r["joints3dKeys"]; nfr=r["joints3dFrames"]; dim=int(r.get("coordDim") or 3)
    K=np.asarray(r["joints3d"],float).reshape(nfr,len(keys),dim)
    name2i={n:i for i,n in enumerate(keys)}
    Kp=K[:,[name2i[n] for n in skeleton.KEYPOINT_NAMES],:]
    A=np.asarray(features.compute_joint_angles(Kp),float)
    return np.asarray(temporal_fill(A, None),float) if fill else A

print(f"{'motion':24s}{'raw NaN%':>9s}{'raw 미스':>9s}{'fill 미스':>10s}{'저장바닥':>9s}{'재계산바닥':>11s}{'label':>8s}")
rows=[]
for mid, r in sorted(refs.items()):
    A = H.ref_matrix(r)
    Braw = recomputed(r, fill=False); B = recomputed(r, fill=True)
    n=min(len(A),len(B))
    nanf=float(np.mean(~np.isfinite(Braw)))*100
    m_raw=float(np.nanmedian(np.abs(Braw[:n]-A[:n])))
    m_fil=float(np.nanmedian(np.abs(B[:n]-A[:n])))
    fps=H.ref_fps_of(r); rb=H.ref_boundary_of(r)
    lab = "self" if g[mid].get("self") else ("correct" if g[mid].get("correct") else None)
    o=n2=float("nan")
    if lab:
        sel=g[mid][lab][:5]
        old=[f["scalar"] for f in sel]
        new=[]
        for f in sel:
            U=H.student_matrix(by_id[f["id"]])
            new.append(H.scalar(H.deviate(U, B, ref_boundary=rb, ref_fps=fps)[0]))
        o,n2=float(np.median(old)),float(np.median(new))
    rows.append((mid,lab,o,n2,m_raw,m_fil))
    print(f"{mid:24s}{nanf:8.2f}%{m_raw:9.2f}{m_fil:10.2f}{o:9.2f}{n2:11.2f}{str(lab):>8s}")
json.dump(rows, open("r13_rebake2.json","w"))
