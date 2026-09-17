"""mode1 채점 seam 로컬 재실행 — 학생 doc 하나를 두 기준(저장 / 회전ON)으로 채점.

파이프라인 코드를 그대로 호출(재구현 금지). 호출 형태 출처 = pipeline/app.py:7981-8004.
"""
from __future__ import annotations
import json, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis import kismam, skeleton
from sunity_shared.analysis.features import feature_vector
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
KEYS = skeleton.JOINT_KEYS
TOL = 20.0  # deduction_engine 허용오차 (저장 감점 근거로 역산 검증됨)

def reshape(flat, n, keys_in=None):
    a = np.asarray(flat, float)
    if a.ndim == 1: a = a.reshape(-1, n)
    if keys_in and list(keys_in) != list(KEYS):
        a = a[:, [list(keys_in).index(k) for k in KEYS]]
    return a

def run(user, ref, ref_fps, label):
    m = motion_dtw(feature_vector(user), feature_vector(ref), ref_boundary=None)
    us, rw = user[m.start:m.end], ref[m.ref_start:m.ref_end]
    dev = per_joint_deviation(m.path, us, rw, ref_fps=ref_fps)
    ui = np.array([p[0] for p in m.path]); ri = np.array([p[1] for p in m.path])
    um = {k: float(np.nanmedian(us[ui, j])) for j, k in enumerate(KEYS)}
    rm = {k: float(np.nanmedian(rw[ri, j])) for j, k in enumerate(KEYS)}
    a = kismam.assess(dev, user_angles=um, reference_angles=rm, target_source="reference_motion")
    dim = kismam.overall_score(a)
    excess = np.maximum(dev - TOL, 0.0)
    print(f"--- {label} ---")
    print(f"  {'관절':16s}{'편차°':>9s}{'초과(감점씨앗)°':>18s}")
    for j, k in enumerate(KEYS):
        mark = " *" if excess[j] > 0 else ""
        print(f"  {k:16s}{dev[j]:9.2f}{excess[j]:18.2f}{mark}")
    print(f"  ** angle 차원 = {dim} · 초과 관절 {int((excess>0).sum())}개 · 초과합 {excess.sum():.1f}° **")
    return dim, dev, excess

DOC, REFDIR, ONJSON, NAME = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
d = json.load(open(DOC)); r = d.get("result") or {}
user = reshape(d["angles"], len(d.get("anglesJointKeys") or KEYS), d.get("anglesJointKeys"))
print(f"[{NAME}] 학생 각도 {user.shape} · 저장 결과 overall={r.get('overallScore')} dims={r.get('dimensionScores')}")
bd = r.get("deductionBreakdown") or {}
print(f"          rawTotal={bd.get('executionRawTotal')} cap={bd.get('executionCap')} 기록={len(bd.get('records') or [])}\n")

st = json.load(open(f"{REFDIR}/ref-pdshape.json"))
ref_st = reshape(st["angles"], len(st.get("anglesJointKeys") or KEYS), st.get("anglesJointKeys"))
d1, _, e1 = run(user, ref_st, float(st.get("anglesRealFps") or 0) or None, "현행: 저장 기준 (회전 미교정)")
print()
on = json.load(open(ONJSON))
ref_on = reshape(on["motions"]["ref-pdshape"]["angles"], 8, on["jointKeys"])
d2, _, e2 = run(user, ref_on, None, "제안: 회전ON 재추출 기준")
print(f"\n=== [{NAME}] angle 차원 {d1} -> {d2} · 초과합 {e1.sum():.1f}° -> {e2.sum():.1f}° ===")
