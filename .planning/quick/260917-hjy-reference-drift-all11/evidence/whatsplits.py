"""두 필드를 가르는 변환 후보를 좁힌다: 비등방 스케일 / 프레임 오프셋 / 좌우스왑."""
import json, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis.features import compute_joint_angles
from sunity_shared.analysis.skeleton import JOINT_KEYS

def load(p):
    doc = json.load(open(p)); T = int(doc['joints3dFrames'])
    a3 = np.asarray(doc['joints3d'], float).reshape(T, 17, 3)
    st = np.asarray(doc['angles'], float).reshape(int(doc['anglesFrames']), -1)
    keys = list(doc.get('anglesJointKeys') or JOINT_KEYS)
    return a3, st[:, [keys.index(k) for k in JOINT_KEYS]]

REF = sys.argv[1]
for mid in ('ref-sideway-spin', 'ref-pdshape', 'ref-kip-up'):
    a3, st = load(f"{REF}/{mid}.json")
    base = float(np.nanmedian(np.abs(compute_joint_angles(a3) - st)))
    # 1) 비등방 스케일 스윕
    best = min(((float(np.nanmedian(np.abs(compute_joint_angles(a3 * np.array([1.0, r, 1.0])) - st))), r)
                for r in np.arange(0.3, 3.01, 0.05)))
    # 2) 프레임 오프셋 스윕
    offs = []
    for k in range(-8, 9):
        rec = compute_joint_angles(a3)
        if k >= 0: d = np.abs(rec[k:] - st[:len(st) - k]) if k else np.abs(rec - st)
        else: d = np.abs(rec[:k] - st[-k:])
        offs.append((float(np.nanmedian(d)), k))
    bo = min(offs)
    # 3) 좌우 스왑
    sw = list(range(17))
    for l, r_ in ((1,2),(3,4),(5,6),(7,8),(9,10),(11,12),(13,14),(15,16)): sw[l], sw[r_] = sw[r_], sw[l]
    dsw = float(np.nanmedian(np.abs(compute_joint_angles(a3[:, sw, :]) - st)))
    print(f"{mid:22s} 기본 {base:7.3f} | 비등방최적 r={best[1]:.2f} -> {best[0]:7.3f} "
          f"| 오프셋최적 k={bo[1]:+d} -> {bo[0]:7.3f} | 좌우스왑 {dsw:7.3f}")
