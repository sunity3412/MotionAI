"""반증 2-b — kip-up correct 는 **어떤 프레임 쌍을 골라도** window 경로로 감점을 못 만드나.

운영 features.window_median_angle_deltas 를 학생 전 프레임 / 기준 전 프레임에 대해
한 번씩 호출해 windowed median 각도(student_deg / reference_deg)를 모은 뒤,
|Δ| 의 전 쌍 상한 = max(max_u S - min_r R, max_r R - min_u S) 를 관절별로 낸다.
(window_median_angle_deltas 의 delta 정의가 정확히 S-R 이므로 상한은 정확하다.)
"""
from __future__ import annotations
import sys, json
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0,D)
import numpy as np
import harness as H
from sunity_shared.analysis import features, skeleton, ipsf_criteria
app=H.app; JK=list(skeleton.JOINT_KEYS); TOL=ipsf_criteria._ANGLE_TOLERANCE_DEG

facts={r["id"]:r for r in json.load(open(f"{D}/facts.json"))}
students={s["id"]:s for s in H.load_students()}
refs=H.load_references()
pick={}
for i,f in facts.items():
    if f["label"] in ("correct","fault"):
        pick.setdefault((f["ref"],f["label"]), i)

def wmed(mat, other, n_self, which):
    """운영 함수로 프레임별 windowed median 을 뽑는다 (상대편 인덱스는 0 고정)."""
    out=np.full((n_self,len(JK)), np.nan)
    for t in range(n_self):
        if which=="s":
            d=features.window_median_angle_deltas(mat, other, user_frame_idx=t, ref_frame_idx=0, window=2)
            key="student_deg"
        else:
            d=features.window_median_angle_deltas(other, mat, user_frame_idx=0, ref_frame_idx=t, window=2)
            key="reference_deg"
        for e in d["deltas"]:
            out[t, JK.index(e["joint"])]=e[key]
    return out

print(f"tol={TOL}")
for (ref,label),sid in sorted(pick.items()):
    s=students[sid]; rdoc=refs[ref]
    ang=H.student_matrix(s); a_ref=H.ref_matrix(rdoc)
    S=wmed(ang, a_ref, ang.shape[0], "s")
    R=wmed(a_ref, ang, a_ref.shape[0], "r")
    bound=[]
    for j in range(len(JK)):
        sv=S[:,j][np.isfinite(S[:,j])]; rv=R[:,j][np.isfinite(R[:,j])]
        if sv.size==0 or rv.size==0: bound.append(float("nan")); continue
        bound.append(max(sv.max()-rv.min(), rv.max()-sv.min()))
    b=np.asarray(bound,dtype=float)
    print(f"{ref:24s}{label:8s} 전쌍 window |Δ| 상한: max {np.nanmax(b):7.1f}  "
          f">tol 관절 {int(np.nansum(b>TOL))}/8   per-joint {[round(float(x),1) for x in b]}")
