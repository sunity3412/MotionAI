"""반증 r13-D — 프레임 일치(coincidence) 전제에 힘을 준다.

'학생 홀수행은 기준 두 프레임 사이' 가 참이면, 그 행만 **선형보간 기준**으로 바꾸면
잔차가 반프레임 몫만큼 떨어져야 한다(짝수행은 보간=원행이라 변화 0).
또 전역 소수 시프트 곡선의 최소점이 0 이 아니면 두 추출은 애초에 같은 프레임을 안 본다.
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

refs = H.load_references(); by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
selfs, seen = [], set()
for f in facts:
    if f["label"] == "self" and f["ref"] not in seen:
        seen.add(f["ref"]); selfs.append(f)

def interp_at(R, pos):
    pos = np.clip(pos, 0, R.shape[0]-1)
    lo = np.floor(pos).astype(int); hi = np.minimum(lo+1, R.shape[0]-1)
    w = (pos-lo)[:, None]
    return R[lo]*(1-w) + R[hi]*w

for f in sorted(selfs, key=lambda x: x["ref"]):
    mid=f["ref"]; U=H.student_matrix(by_id[f["id"]]); R=H.ref_matrix(refs[mid])
    nu,nr=U.shape[0],R.shape[0]; scale=nr/nu
    # 전역 소수 시프트 곡선 (보간 기준)
    grid=np.arange(-2.0,2.001,0.05)
    vals=[]
    for sh in grid:
        pos=np.arange(nu)*scale+sh
        ok=(pos>=0)&(pos<=nr-1)
        vals.append(float(np.median(np.median(np.abs(U[ok]-interp_at(R,pos[ok])),axis=1))))
    vals=np.asarray(vals); k=int(np.argmin(vals)); sh=float(grid[k])
    pos=np.arange(nu)*scale+sh; ok=(pos>=0)&(pos<=nr-1)
    frac=np.abs(pos-np.round(pos))
    near=np.median(np.abs(U-R[np.clip(np.round(pos).astype(int),0,nr-1)]),axis=1)
    itp =np.median(np.abs(U-interp_at(R,pos)),axis=1)
    on=(frac<0.12)&ok; off=(frac>0.38)&ok
    adj=float(np.median(np.median(np.abs(np.diff(R,axis=0)),axis=1)))
    print(f"{mid:20s} best_frac_shift={sh:+.2f}  min={vals[k]:6.2f}  at0={vals[np.argmin(np.abs(grid))]:6.2f}"
          f"  adj/2={adj/2:5.2f}")
    print(f"{'':20s}  near-row : on {np.median(near[on]):6.2f}  off {np.median(near[off]):6.2f}")
    print(f"{'':20s}  interp   : on {np.median(itp[on]):6.2f}  off {np.median(itp[off]):6.2f}"
          f"   (off 개선 {np.median(near[off])-np.median(itp[off]):+.2f}, on 개선 {np.median(near[on])-np.median(itp[on]):+.2f})")
