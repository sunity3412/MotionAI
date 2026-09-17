"""3조합 최종 점수 — 현행 운영 / 회전만 / 묶음.

감점 규칙 출처 = deduction_engine.py:53 "tol 20° · slope 1.2 · per-record -20 ·
execution cap 40". 재구현이 아니라 그 상수를 그대로 적용한다.
편차는 파이프라인 함수(motion_dtw -> per_joint_deviation)로 산출.
"""
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
    pts = np.minimum(exc * SLOPE, REC_CAP)
    raw = float(pts.sum())
    final = int(round(100.0 - min(raw, EXEC_CAP)))
    return dim, dev, exc, raw, final

E = ".planning/quick/260914-rot180-gpu-validation/evidence/docs/"
REFD, ONJ = sys.argv[1], sys.argv[2]
st = json.load(open(f"{REFD}/ref-pdshape.json"))
ref_st = rs(st["angles"], len(st.get("anglesJointKeys") or KEYS), st.get("anglesJointKeys"))
fps_st = float(st.get("anglesRealFps") or 0) or None
on = json.load(open(ONJ))
ref_on = rs(on["motions"]["ref-pdshape"]["angles"], 8, on["jointKeys"])

def load(f):
    d = json.load(open(E + f)); r = d.get("result") or {}
    return rs(d["angles"], len(d.get("anglesJointKeys") or KEYS), d.get("anglesJointKeys")), r

print(f"{'조합':38s}{'angle':>7s}{'초과관절':>9s}{'원감점':>9s}{'상한후':>8s}{'점수':>7s}{'저장값':>9s}")
for name, doc, ref, fps, stored_key in [
    ("현행 운영 (회전 OFF / 저장 기준)",       "run1_off.json", ref_st, fps_st, "run1"),
    ("회전만 켬 (회전 ON / 저장 기준)",        "run3_on.json",  ref_st, fps_st, "run3"),
    ("묶음 (회전 ON / 회전ON 재추출 기준)",     "run3_on.json",  ref_on, None,  None),
]:
    u, r = load(doc)
    dim, dev, exc, raw, fin = seam(u, ref, fps)
    bd = r.get("deductionBreakdown") or {}
    sv = (f"angle {r.get('dimensionScores',{}).get('angle')} / raw {bd.get('executionRawTotal')} / {r.get('overallScore')}점"
          if stored_key else "—")
    print(f"{name:38s}{dim:7d}{int((exc>0).sum()):9d}{-raw:9.1f}{-min(raw,EXEC_CAP):8.1f}{fin:7d}   {sv}")

print()
d = json.load(open(E + "ref_on.json"))
u = rs(d["angles"], len(d.get("anglesJointKeys") or KEYS), d.get("anglesJointKeys"))
for name, ref, fps in [("정은지 자기비교 — 회전만 켬", ref_st, fps_st),
                       ("정은지 자기비교 — 묶음", ref_on, None)]:
    dim, dev, exc, raw, fin = seam(u, ref, fps)
    print(f"{name:38s}{dim:7d}{int((exc>0).sum()):9d}{-raw:9.1f}{-min(raw,EXEC_CAP):8.1f}{fin:7d}")
