"""새 버전(rot180_v1) 으로 채점하면 몇 점인가 — 09-17 예측(86)과 대조."""
from __future__ import annotations
import json, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis import kismam, skeleton
from sunity_shared.analysis.features import feature_vector
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
KEYS = skeleton.JOINT_KEYS
TOL, SLOPE, REC_CAP, EXEC_CAP = 20.0, 1.2, 20.0, 40.0

def rs(flat, n, kin=None):
    a = np.asarray(flat, float)
    if a.ndim == 1: a = a.reshape(-1, n)
    if kin and list(kin) != list(KEYS): a = a[:, [list(kin).index(k) for k in KEYS]]
    return a

def seam(user, ref, fps):
    m = motion_dtw(feature_vector(user), feature_vector(ref), ref_boundary=None)
    us, rw = user[m.start:m.end], ref[m.ref_start:m.ref_end]
    dev = per_joint_deviation(m.path, us, rw, ref_fps=fps)
    ui = np.array([p[0] for p in m.path]); ri = np.array([p[1] for p in m.path])
    um = {k: float(np.nanmedian(us[ui, j])) for j, k in enumerate(KEYS)}
    rm = {k: float(np.nanmedian(rw[ri, j])) for j, k in enumerate(KEYS)}
    dim = kismam.overall_score(kismam.assess(dev, user_angles=um, reference_angles=rm,
                                             target_source="reference_motion"))
    exc = np.maximum(dev - TOL, 0.0)
    raw = float(np.minimum(exc * SLOPE, REC_CAP).sum())
    return dim, dev, exc, raw, int(round(100.0 - min(raw, EXEC_CAP)))

E = ".planning/quick/260914-rot180-gpu-validation/evidence/docs/"
NEW, OLD = sys.argv[1], sys.argv[2]
def refload(d, mid):
    doc = json.load(open(f"{d}/{mid}.json"))
    a = rs(doc["angles"], len(doc.get("anglesJointKeys") or KEYS), doc.get("anglesJointKeys"))
    return a, (float(doc.get("anglesRealFps") or 0) or None)

print(f"{'학생 / 기준':44s}{'프레임':>7s}{'angle':>7s}{'초과':>5s}{'원감점':>9s}{'점수':>7s}")
for docname, label in (("run3_on.json", "belle pdshape (실수강생)"), ("ref_on.json", "정은지 자기비교")):
    d = json.load(open(E + docname))
    u = rs(d["angles"], len(d.get("anglesJointKeys") or KEYS), d.get("anglesJointKeys"))
    for refdir, rl in ((OLD, "현행 라이브 기준"), (NEW, "★ rot180_v1 새 버전")):
        ra, rf = refload(refdir, "ref-pdshape")
        dim, dev, exc, raw, fin = seam(u, ra, rf)
        print(f"{label + ' / ' + rl:44s}{len(ra):7d}{dim:7d}{int((exc>0).sum()):5d}{-raw:9.1f}{fin:7d}")
    print()
