"""저장 joints3d 에 실제 파이프라인 함수를 적용해 저장 angles 와 대조."""
import json, os, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis.features import compute_joint_angles, fill_gaps
from sunity_shared.analysis.skeleton import JOINT_KEYS

REF = sys.argv[1]
print(f"{'기준':24s}{'raw Δ중앙':>11s}{'fill Δ중앙':>11s}{'fill Δp95':>11s}{'nan율%':>8s}{'완전일치%':>10s}")
rows = []
for fn in sorted(os.listdir(REF)):
    if not fn.endswith('.json') or fn.startswith('_'): continue
    doc = json.load(open(os.path.join(REF, fn))); mid = fn[:-5]
    T = int(doc['joints3dFrames'])
    a3 = np.asarray(doc['joints3d'], float).reshape(T, 17, 3)
    stored = np.asarray(doc['angles'], float).reshape(int(doc['anglesFrames']), -1)
    keys = list(doc.get('anglesJointKeys') or JOINT_KEYS)
    stored = stored[:, [keys.index(k) for k in JOINT_KEYS]]
    raw = compute_joint_angles(a3)
    filled = fill_gaps(raw)
    n = min(len(raw), len(stored))
    d_raw = np.abs(raw[:n] - stored[:n]); d_fill = np.abs(filled[:n] - stored[:n])
    nanrate = 100.0 * np.isnan(raw).mean()
    exact = 100.0 * (d_fill < 0.01).mean()
    rows.append((mid, float(np.nanmedian(d_raw)), float(np.nanmedian(d_fill)),
                 float(np.nanpercentile(d_fill, 95)), float(nanrate), float(exact)))
    print(f"{mid:24s}{rows[-1][1]:11.3f}{rows[-1][2]:11.3f}{rows[-1][3]:11.3f}{nanrate:8.1f}{exact:10.1f}")
json.dump(rows, open(os.path.join(REF, '_libcheck.json'), 'w'), indent=1)
