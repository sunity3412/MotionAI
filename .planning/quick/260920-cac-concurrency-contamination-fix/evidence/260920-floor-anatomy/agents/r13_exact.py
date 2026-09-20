import sys; sys.path.insert(0,"/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H, numpy as np
from sunity_shared.analysis import features, skeleton
from sunity_shared.analysis.temporal import temporal_fill
refs=H.load_references()
print(f"{'motion':24s}{'med|d|':>9s}{'p90':>9s}{'max':>10s}{'frac<1e-6':>11s}")
for mid,r in sorted(refs.items()):
    A=H.ref_matrix(r); keys=r["joints3dKeys"]; nfr=r["joints3dFrames"]; dim=int(r.get("coordDim") or 3)
    K=np.asarray(r["joints3d"],float).reshape(nfr,len(keys),dim)
    n2i={n:i for i,n in enumerate(keys)}
    B=np.asarray(temporal_fill(np.asarray(features.compute_joint_angles(K[:,[n2i[n] for n in skeleton.KEYPOINT_NAMES],:]),float),None),float)
    n=min(len(A),len(B)); d=np.abs(B[:n]-A[:n])
    print(f"{mid:24s}{np.nanmedian(d):9.2e}{np.nanpercentile(d,90):9.2e}{np.nanmax(d):10.2e}{float(np.mean(d<1e-6)):11.4f}")
