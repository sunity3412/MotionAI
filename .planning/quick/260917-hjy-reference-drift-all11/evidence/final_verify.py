"""승격 후 실제 해석 경로 검증 — firestore_admin.get_reference_motion 이 무엇을 주나."""
import json, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
sys.path.insert(0, 'backend/scripts')
import e2e_app_path  # noqa: F401  (firebase 초기화)
from sunity_shared import firestore_admin
from sunity_shared.analysis import kismam, skeleton
from sunity_shared.analysis.features import feature_vector
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
KEYS = skeleton.JOINT_KEYS
TOL, SLOPE, REC_CAP, EXEC_CAP = 20.0, 1.2, 20.0, 40.0

ref = firestore_admin.get_reference_motion("ref-pdshape")
print(f"get_reference_motion('ref-pdshape') → pipelineVersion={ref.get('pipelineVersion')} "
      f"activeVersion={ref.get('activeVersion')} anglesFrames={ref.get('anglesFrames')}")
print(f"  referenceKeypointReport v={(ref.get('referenceKeypointReport') or {}).get('version')} "
      f"frames={(ref.get('referenceKeypointReport') or {}).get('frames')}")
print(f"  keypointReport          v={(ref.get('keypointReport') or {}).get('version')} "
      f"frames={(ref.get('keypointReport') or {}).get('frames')}  ← candidate overlay 확인")
print(f"  anglesRealFps={ref.get('anglesRealFps')}")

def rs(flat, n, kin=None):
    a = np.asarray(flat, float)
    if a.ndim == 1: a = a.reshape(-1, n)
    if kin and list(kin) != list(KEYS): a = a[:, [list(kin).index(k) for k in KEYS]]
    return a

ra = rs(ref["angles"], len(ref.get("anglesJointKeys") or KEYS), ref.get("anglesJointKeys"))
E = ".planning/quick/260914-rot180-gpu-validation/evidence/docs/"
print(f"\n{'학생':28s}{'angle':>7s}{'초과':>5s}{'원감점':>9s}{'점수':>7s}")
for f, nm in (("run3_on.json", "belle pdshape (회전ON)"), ("ref_on.json", "정은지 자기비교 (회전ON)")):
    d = json.load(open(E + f))
    u = rs(d["angles"], len(d.get("anglesJointKeys") or KEYS), d.get("anglesJointKeys"))
    fps = float(ref.get("anglesRealFps") or 0) or None
    m = motion_dtw(feature_vector(u), feature_vector(ra), ref_boundary=None)
    us, rw = u[m.start:m.end], ra[m.ref_start:m.ref_end]
    dev = per_joint_deviation(m.path, us, rw, ref_fps=fps)
    ui = np.array([p[0] for p in m.path]); ri = np.array([p[1] for p in m.path])
    um = {k: float(np.nanmedian(us[ui, j])) for j, k in enumerate(KEYS)}
    rm = {k: float(np.nanmedian(rw[ri, j])) for j, k in enumerate(KEYS)}
    dim = kismam.overall_score(kismam.assess(dev, user_angles=um, reference_angles=rm,
                                             target_source="reference_motion"))
    exc = np.maximum(dev - TOL, 0.0); raw = float(np.minimum(exc * SLOPE, REC_CAP).sum())
    print(f"{nm:28s}{dim:7d}{int((exc>0).sum()):5d}{-raw:9.1f}{int(round(100-min(raw,EXEC_CAP))):7d}")
