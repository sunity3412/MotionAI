"""반증 조사 r13 — self 바닥이 정말 '같은 원본 프레임의 포즈 불일치'인가.

세 가지를 잰다.
 (1) 자유매칭이 고른 기준행이 rigid 예측에서 얼마나 떨어져 있나 (국소인가 산발인가)
 (2) 채점 거리를 직접 최소화하는 **단조** 정렬(DTW on scored cost)의 스칼라
     -> 단조 시간지도로 도달 가능한 포즈 불일치 상한
 (3) 두 시리즈의 인접행 변화량(시간 해상도 감각) + rigid 잔차의 shift 민감도
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

def scored(pairs, U, R):
    """운영 스칼라와 같은 집계 — 관절별 median|Δ| 8개의 중앙값 (경계마스크 없음)."""
    d = np.abs(U[pairs[:,0]] - R[pairs[:,1]])
    return float(np.median(np.median(d, axis=0))), np.median(d, axis=0)

def monotone_dtw(C):
    """C(n,m) 비용행렬에 대한 전역 DTW 경로 (step (1,1),(1,0),(0,1))."""
    n, m = C.shape
    D = np.full((n+1, m+1), np.inf); D[0,0] = 0.0
    P = np.zeros((n+1, m+1), dtype=np.int8)
    for i in range(1, n+1):
        prev = D[i-1]; cur = D[i]
        Ci = C[i-1]
        # 순차 (0,1) 의존 때문에 행 내부는 루프
        for j in range(1, m+1):
            a = prev[j-1]; b = prev[j]; c = cur[j-1]
            k = 0 if (a <= b and a <= c) else (1 if b <= c else 2)
            cur[j] = Ci[j-1] + (a if k==0 else (b if k==1 else c))
            P[i,j] = k
    i, j, path = n, m, []
    while i > 0 and j > 0:
        path.append((i-1, j-1))
        k = P[i,j]
        if k == 0: i, j = i-1, j-1
        elif k == 1: i -= 1
        else: j -= 1
    path.reverse()
    return np.asarray(path, dtype=int)

res = []
for f in sorted(selfs, key=lambda x: x["ref"]):
    mid = f["ref"]
    U = H.student_matrix(by_id[f["id"]]); R = H.ref_matrix(refs[mid])
    nu, nr = U.shape[0], R.shape[0]
    scale = nr / nu

    # 운영
    dev, m = H.deviate(U, refs[mid])
    live = H.scalar(dev)

    # rigid best shift + 민감도
    curve = {}
    best = None
    for sh in np.arange(-6, 6.01, 0.5):
        idx = np.round(np.arange(nu) * scale + sh)
        ok = (idx >= 0) & (idx <= nr - 1); idxi = idx[ok].astype(int)
        pairs = np.stack([np.nonzero(ok)[0], idxi], axis=1)
        v, _ = scored(pairs, U, R)
        curve[round(float(sh),1)] = round(v,3)
        if best is None or v < best[0]: best = (v, float(sh))
    rigid_v, rigid_sh = best
    # 먼 시프트(무관 짝) 대조: ±30 행
    far = []
    for sh in (-40, -30, 30, 40):
        idx = np.round(np.arange(nu) * scale + sh)
        ok = (idx >= 0) & (idx <= nr - 1); idxi = idx[ok].astype(int)
        pairs = np.stack([np.nonzero(ok)[0], idxi], axis=1)
        far.append(round(scored(pairs, U, R)[0], 3))

    # 인접행 변화량
    adj_r = float(np.median(np.median(np.abs(np.diff(R, axis=0)), axis=1)))
    adj_u = float(np.median(np.median(np.abs(np.diff(U, axis=0)), axis=1)))

    # 자유 매칭 위치
    C = np.zeros((nu, nr))
    for i in range(nu):
        C[i] = np.median(np.abs(R - U[i]), axis=1)
    free_rows = np.argmin(C, axis=1)
    pred = np.round(np.arange(nu) * scale + rigid_sh)
    off = free_rows - pred
    off_med = float(np.median(np.abs(off)))
    within3 = float(np.mean(np.abs(off) <= 3))
    within10 = float(np.mean(np.abs(off) <= 10))

    # 단조 최적 정렬 (채점 거리 직접 최소화)
    mp = monotone_dtw(C)
    mono_v, mono_pj = scored(mp, U, R)
    # 단조 경로의 ref 위치가 rigid 예측에서 얼마나 떨어지나
    mono_off = np.abs(mp[:,1] - np.round(mp[:,0] * scale + rigid_sh))
    r = dict(motion=mid, nu=nu, nr=nr, live=round(live,3),
             rigid=round(rigid_v,3), rigid_sh=rigid_sh, far=far,
             adj_ref=round(adj_r,3), adj_stu=round(adj_u,3),
             free_off_med=off_med, free_within3=round(within3,3), free_within10=round(within10,3),
             mono=round(mono_v,3), mono_perjoint=[round(float(x),2) for x in mono_pj],
             mono_off_med=float(np.median(mono_off)), mono_off_p90=float(np.percentile(mono_off,90)),
             curve={k:curve[k] for k in sorted(curve)})
    res.append(r); print(json.dumps(r, ensure_ascii=False), flush=True)
json.dump(res, open("r13_probe.json","w"))
