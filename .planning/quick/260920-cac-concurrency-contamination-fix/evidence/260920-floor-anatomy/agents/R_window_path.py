"""반증 2 — 운영의 pointed-joint window 경로를 끄고 잰 것이 아닌가.

app.py:2812 주석: "jk ∈ vision_pointed_joints AND jk ∈ wm_by_joint → worst-window
median 방출 — **kip-up 어깨 Δ40° 처럼 국소 결함이 전체 DTW path median 에서 tol
미만으로 희석되던 '표시는 40° 인데 감점 0' 해소.**"

F_* 재구성은 vision_pointed_joints=None 으로 돌았다 = 전 관절 DTW fallback =
그 주석이 말하는 **해소 이전** 경로. 그래서 kip-up 분리 0 이 나올 수 있다.

여기서는 운영 함수 features.window_median_angle_deltas 를 DTW path 의 모든
(u,r) 쌍에 대해 호출해, 그 동작에서 window 경로가 **낼 수 있는 값의 범위**를 잰다.
Gemini 가 어느 프레임/관절을 짚는지는 오프라인에서 모른다 → 상한(worst window)과
중앙(median window)을 둘 다 남긴다. 재구현 0.
"""
from __future__ import annotations
import sys, json, collections, statistics as st
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0,D)
import numpy as np
import harness as H
from sunity_shared.analysis import features, skeleton, ipsf_criteria
app=H.app
JK=list(skeleton.JOINT_KEYS)
TOL=ipsf_criteria._ANGLE_TOLERANCE_DEG

facts={r["id"]:r for r in json.load(open(f"{D}/facts.json"))}
students={s["id"]:s for s in H.load_students()}
refs=H.load_references()

# 동작×라벨×videoKey 당 1건만 (같은 영상 재분석은 sd 0.03~1.04도로 동일)
pick={}
for i,f in facts.items():
    if f["label"] not in ("correct","fault"): continue
    pick.setdefault((f["ref"],f["label"],f["vk"] or ""), i)

rows=[]
for (ref,label,vk),sid in sorted(pick.items()):
    s=students[sid]; rdoc=refs[ref]
    ang=H.student_matrix(s); nj=ang.shape[1]
    dev,match,user_seg,a_ref=app._deviation_against(
        ang, np.asarray(rdoc["angles"],dtype=float), nj,
        ref_boundary=H.ref_boundary_of(rdoc), ref_fps=H.ref_fps_of(rdoc))
    path=match.path; start=match.start
    # path 를 균등 표집(최대 200 스텝) — 운영 함수 호출 비용 관리
    step=max(1,len(path)//200)
    worst={j:0.0 for j in JK}
    allvals=collections.defaultdict(list)
    for k in range(0,len(path),step):
        u,r=path[k]
        wm=features.window_median_angle_deltas(
            ang, a_ref, user_frame_idx=int(start)+int(u), ref_frame_idx=int(r), window=2)
        for e in wm["deltas"]:
            j=e.get("joint")
            if j in worst:
                v=abs(float(e.get("delta_deg",0.0)))
                worst[j]=max(worst[j],v); allvals[j].append(v)
    rows.append(dict(ref=ref,label=label,vk=vk,id=sid,
        dtw_dev={j:float(dev[i]) for i,j in enumerate(JK)},
        worst={j:worst[j] for j in JK},
        med={j:float(np.median(allvals[j])) if allvals[j] else float('nan') for j in JK},
        n_dtw_over=sum(1 for i,j in enumerate(JK) if dev[i]>TOL),
        n_worst_over=sum(1 for j in JK if worst[j]>TOL),
        plen=len(path)))
    print(f"{ref:24s}{label:8s}{vk[:38]:40s} DTW>tol {rows[-1]['n_dtw_over']}  "
          f"worstwindow>tol {rows[-1]['n_worst_over']}  "
          f"maxDTW {max(dev):5.1f}  maxWORST {max(worst.values()):6.1f}", flush=True)

json.dump(rows, open(f"{D}/out/G_window_path.json","w"), indent=1)
