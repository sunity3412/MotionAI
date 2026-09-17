"""pdshape 4자 대조: 저장 angles / 저장 joints3d 재계산 / GPU 재추출 OFF / GPU 재추출 ON."""
import json, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES, JOINT_ANGLES, JOINT_KEYS
IDX = {n: i for i, n in enumerate(KEYPOINT_NAMES)}

def ang(xy):
    T = len(xy); out = np.full((T, 8), np.nan)
    for k, key in enumerate(JOINT_KEYS):
        a, v, c = (IDX[n] for n in JOINT_ANGLES[key])
        u = xy[:, a] - xy[:, v]; w = xy[:, c] - xy[:, v]
        nu = np.linalg.norm(u, -1 if u.ndim == 1 else -1, keepdims=False); nw = np.linalg.norm(w, axis=-1)
        nu = np.linalg.norm(u, axis=-1)
        cos = np.clip((u * w).sum(-1) / (nu * nw + 1e-9), -1, 1)
        out[:, k] = np.degrees(np.arccos(cos))
    return out

doc = json.load(open(sys.argv[1] + "/ref-pdshape.json"))
T = int(doc["joints3dFrames"])
a3 = np.asarray(doc["joints3d"], float).reshape(T, 17, 3)
stored = np.asarray(doc["angles"], float).reshape(int(doc["anglesFrames"]), -1)
keys = list(doc.get("anglesJointKeys") or JOINT_KEYS)
stored = stored[:, [keys.index(k) for k in JOINT_KEYS]]

E = ".planning/quick/260914-rot180-gpu-validation/evidence/"
def gpu(f):
    d = json.load(open(E + f)); m = d["motions"]["ref-pdshape"]
    if isinstance(m, dict):
        for kk in ("angles", "medians", "median", "values"):
            if kk in m: return kk, m[kk], {k: v for k, v in m.items() if k != kk}
        return None, None, m
    return None, m, {}

for f in ("ref_angles_off.json", "ref_angles_on.json"):
    kk, v, rest = gpu(f)
    print(f, "-> field:", kk, "| rest:", {k: (str(v2)[:60]) for k, v2 in list(rest.items())[:8]})

rec_xy = ang(a3[:, :, :2])
rec_xz = ang(a3[:, :, [0, 2]])
print()
print(f"{'관절':16s}{'저장angles':>12s}{'j3d재계산xy':>14s}{'j3d재계산xz':>14s}")
for k, key in enumerate(JOINT_KEYS):
    print(f"{key:16s}{np.nanmedian(stored[:, k]):12.1f}{np.nanmedian(rec_xy[:, k]):14.1f}{np.nanmedian(rec_xz[:, k]):14.1f}")
