"""반증 r13-E — 운영 격자 구조(비율 1.5, 절반만 격자 일치)를 실제 포즈로 재현한 대조.

기준 = R[0::2] (7.5fps),  학생 = R[0::3] (5fps)  -> 비율 정확히 1.5.
학생행의 절반은 기준행과 **완전히 같은 행**(위상 0), 나머지 절반은 기준 두 행 사이
(위상차 1/15초 = 운영의 2배). 포즈 추출은 완전히 동일(보간 0, 새 포즈 0).
운영 geometry(위상차 1/30초)는 이 값의 대략 절반에 해당한다.

비교군:
  full_subset : 학생 = 기준행의 순수 부분집합 (a_gridfloor 의 ratio 격자와 같은 구조)
  disjoint    : 학생 = R[1::2], 공유행 0
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

refs = H.load_references()
facts = json.load(open(f"{H.D}/facts.json"))
import collections
g = collections.defaultdict(lambda: collections.defaultdict(list))
for f in facts: g[f["ref"]][f["label"]].append(f["scalar"])

print(f"{'motion':24s}{'half-lattice':>13s}{'full_subset':>12s}{'disjoint':>9s}{'adj_med':>8s}{'self바닥':>9s}{'correct바닥':>12s}")
rows=[]
for mid, rdoc in sorted(refs.items()):
    R = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    Re = R[0::2]                      # 기준 7.5fps
    Uh = R[0::3]                      # 학생 5fps, 절반 격자 일치
    Us = Re[0::3]                     # 순수 부분집합 (7.5->2.5fps) 비교용
    Ud = R[1::2][:len(Re)]            # 공유행 0
    rf = fps/2.0
    v_h = H.scalar(H.deviate(Uh, Re, ref_fps=rf)[0])
    v_s = H.scalar(H.deviate(Us, Re, ref_fps=rf)[0])
    v_d = H.scalar(H.deviate(Ud, Re, ref_fps=rf)[0])
    adj = float(np.median(np.median(np.abs(np.diff(R,axis=0)),axis=1)))
    se = g[mid].get("self"); c = g[mid].get("correct")
    rows.append((mid,v_h,v_s,v_d,adj,se,c))
    print(f"{mid:24s}{v_h:13.3f}{v_s:12.3f}{v_d:9.3f}{adj:8.2f}"
          f"{(np.median(se) if se else float('nan')):9.2f}{(np.median(c) if c else float('nan')):12.2f}")
print("\n운영 geometry 환산(위상차 절반) 추정 = half-lattice 의 약 1/2")
for mid,v_h,v_s,v_d,adj,se,c in rows:
    base = np.median(se) if se else (np.median(c) if c else None)
    if base: print(f"  {mid:24s} 격자몫 추정 ~{v_h/2:5.2f}도  /  바닥 {base:5.2f}도  = {100*v_h/2/base:5.1f}%")
