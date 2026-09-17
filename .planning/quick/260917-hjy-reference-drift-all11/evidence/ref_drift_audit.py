"""기준 11편 좌표 건전성 전수 측정 — GPU 불필요, 저장 joints3d 만 사용.

정의는 evidence/joints3d_metrics.py 와 동일(09-13 decompose.py:71-83 출처).
추가로 관절각을 저장 좌표에서 재계산해 저장 angles 와 대조한다.
"""
from __future__ import annotations
import json, os, sys
import numpy as np

sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES, JOINT_ANGLES, JOINT_KEYS

IDX = {n: i for i, n in enumerate(KEYPOINT_NAMES)}
BONES = ((5, 7), (7, 9), (6, 8), (8, 10), (11, 13), (13, 15), (12, 14), (14, 16))
BONE_LABEL = ("L상완", "L전완", "R상완", "R전완", "L허벅", "L정강", "R허벅", "R정강")
# 관절각을 이루는 두 선분 중 BONES 집합에 속하는 것들
JOINT_BONES = {"left_elbow": (0, 1), "right_elbow": (2, 3), "left_shoulder": (0,),
               "right_shoulder": (2,), "left_hip": (4,), "right_hip": (6,),
               "left_knee": (4, 5), "right_knee": (6, 7)}

def torso(a):
    return np.linalg.norm(a[:, [5, 6], :].mean(1) - a[:, [11, 12], :].mean(1), axis=-1)

def coords(doc):
    t = int(doc["joints3dFrames"]); j = len(doc.get("joints3dKeys") or KEYPOINT_NAMES)
    a = np.asarray(doc["joints3d"], float).reshape(t, j, 3)
    return a

def bone_p90(xy):
    tor = torso(xy); out = []
    for (i, j) in BONES:
        L = np.linalg.norm(xy[:, i, :] - xy[:, j, :], axis=-1) / (tor + 1e-9)
        med = np.nanmedian(L) + 1e-9
        out.append(float(np.nanpercentile(np.abs(np.log((L + 1e-9) / med)), 90)))
    return np.array(out)

def collapse(xy):
    return int(sum(len(set(map(tuple, np.round(xy[t], 1)))) <= 8 for t in range(len(xy))))

def angles_from(xy):
    T = len(xy); out = np.full((T, len(JOINT_KEYS)), np.nan)
    for k, key in enumerate(JOINT_KEYS):
        a, v, c = (IDX[n] for n in JOINT_ANGLES[key])
        u = xy[:, a, :] - xy[:, v, :]; w = xy[:, c, :] - xy[:, v, :]
        nu = np.linalg.norm(u, axis=-1); nw = np.linalg.norm(w, axis=-1)
        cos = np.clip((u * w).sum(-1) / (nu * nw + 1e-9), -1, 1)
        ang = np.degrees(np.arccos(cos)); ang[(nu < 1e-6) | (nw < 1e-6)] = np.nan
        out[:, k] = ang
    return out

REF = sys.argv[1]
rows = []
for fn in sorted(os.listdir(REF)):
    if not fn.endswith(".json") or fn.startswith("_"): continue
    doc = json.load(open(os.path.join(REF, fn))); mid = fn[:-5]
    a = coords(doc)
    # 세로축 판정: 분산이 큰 쪽이 실제 세로 슬롯
    var = [float(np.var(a[:, :, i])) for i in range(3)]
    xy = a[:, :, :2]
    bp = bone_p90(xy)
    rec = angles_from(xy)
    stored = np.asarray(doc["angles"], float).reshape(int(doc["anglesFrames"]), -1)
    keys = list(doc.get("anglesJointKeys") or JOINT_KEYS)
    order = [keys.index(k) for k in JOINT_KEYS]
    stored = stored[:, order]
    n = min(len(rec), len(stored))
    d = np.abs(rec[:n] - stored[:n])
    rows.append(dict(id=mid, frames=len(a), var=var, collapse=collapse(xy),
                     torso=float(np.nanmedian(torso(xy))), bone=bp.tolist(),
                     bone_mean=float(bp.mean()), bone_max=float(bp.max()),
                     recon_med_absdiff=float(np.nanmedian(d)),
                     recon_p95_absdiff=float(np.nanpercentile(d[np.isfinite(d)], 95)) if np.isfinite(d).any() else float("nan"),
                     stored_med=np.nanmedian(stored, axis=0).tolist()))
json.dump(rows, open(os.path.join(REF, "_audit.json"), "w"), indent=1)

print(f"{'기준':24s}{'프레임':>6s}{'붕괴':>5s}{'몸통px':>8s}{'뼈위반평균':>10s}{'뼈위반최악':>10s}{'각도재계산Δ중앙':>16s}")
for r in rows:
    print(f"{r['id']:24s}{r['frames']:6d}{r['collapse']:5d}{r['torso']:8.1f}"
          f"{r['bone_mean']:10.3f}{r['bone_max']:10.3f}{r['recon_med_absdiff']:16.3f}")
print()
print(f"{'기준':24s}" + "".join(f"{b:>8s}" for b in BONE_LABEL))
for r in rows:
    print(f"{r['id']:24s}" + "".join(f"{v:8.2f}" for v in r["bone"]))
