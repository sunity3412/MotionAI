"""temporal_fill 의 스무딩 성분만으로 간극이 닫히는지 — 불확실도 없이 가능한 상한 검증."""
import json, os, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis.features import compute_joint_angles, fill_gaps
from sunity_shared.analysis.skeleton import JOINT_KEYS
from sunity_shared.analysis.temporal import DEFAULT_SMOOTH_WINDOW

def smooth(a, w):
    out = np.array(a, float, copy=True); T, J = a.shape; h = w // 2
    for j in range(J):
        col = a[:, j]
        for t in range(T):
            lo, hi = max(0, t - h), min(T, t + h + 1)
            seg = col[lo:hi]; seg = seg[np.isfinite(seg)]
            if seg.size: out[t, j] = seg.mean()
    return out

REF = sys.argv[1]
print(f"{'기준':24s}{'nan율%':>8s}{'raw Δ':>9s}{'+갭필 Δ':>9s}{'+스무딩 Δ':>10s}{'설명된비율%':>12s}")
for fn in sorted(os.listdir(REF)):
    if not fn.endswith('.json') or fn.startswith('_'): continue
    doc = json.load(open(os.path.join(REF, fn))); mid = fn[:-5]
    T = int(doc['joints3dFrames'])
    a3 = np.asarray(doc['joints3d'], float).reshape(T, 17, 3)
    st = np.asarray(doc['angles'], float).reshape(int(doc['anglesFrames']), -1)
    keys = list(doc.get('anglesJointKeys') or JOINT_KEYS)
    st = st[:, [keys.index(k) for k in JOINT_KEYS]]
    raw = compute_joint_angles(a3); filled = fill_gaps(raw); sm = smooth(filled, DEFAULT_SMOOTH_WINDOW)
    d0 = float(np.nanmedian(np.abs(raw - st))); d1 = float(np.nanmedian(np.abs(filled - st)))
    d2 = float(np.nanmedian(np.abs(sm - st)))
    print(f"{mid:24s}{100*np.isnan(raw).mean():8.1f}{d0:9.2f}{d1:9.2f}{d2:10.2f}{100*(d0-d2)/max(d0,1e-9):12.1f}")
