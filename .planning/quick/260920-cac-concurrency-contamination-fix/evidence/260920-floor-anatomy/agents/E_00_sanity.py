"""E-0 sanity: joints3d(2D, z=0) 에서 운영 features.compute_joint_angles 를 돌려
저장된 angles 와 일치하는지 확인. 일치해야 아래 시점 기술자 분석이 '같은 좌표'
위에서 논하는 것이 된다."""
import json, sys
import numpy as np
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
import harness as H
from sunity_shared.analysis import features

refs = H.load_references()
print(f"{'motion':24s}{'T':>5s}{'xrange':>22s}{'yrange':>22s}{'maxabs|Δang|':>14s}{'med|Δang|':>11s}")
for m, r in sorted(refs.items()):
    nk = len(r["joints3dKeys"])
    kp = np.asarray(r["joints3d"], float).reshape(-1, nk, 3)
    ang_stored = H.ref_matrix(r)
    ang_calc = features.compute_joint_angles(kp)
    d = np.abs(ang_calc - ang_stored)
    d = d[np.isfinite(d)]
    x = kp[:, :, 0]; y = kp[:, :, 1]
    print(f"{m:24s}{kp.shape[0]:5d}{f'[{np.nanmin(x):.0f},{np.nanmax(x):.0f}]':>22s}"
          f"{f'[{np.nanmin(y):.0f},{np.nanmax(y):.0f}]':>22s}"
          f"{(d.max() if d.size else float('nan')):14.4f}{(np.median(d) if d.size else float('nan')):11.4f}")
