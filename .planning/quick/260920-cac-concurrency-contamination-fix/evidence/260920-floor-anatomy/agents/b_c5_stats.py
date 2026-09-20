"""조사 B (C5) — 각도 범위/천장 가설.

1) 기준 11편 각도 통계 (관절별 mean/sd/range, 180 으로부터의 거리, 프레임간 |Δ|)
2) chance level — 시간정보를 파괴했을 때 이 지표가 내는 값
   (a) analytic: 모든 프레임쌍 |Δ| 의 중앙값 (관절별 → 관절 중앙값)
   (b) operational: 기준 각도 행렬의 프레임을 무작위 셔플 → H.deviate(운영 함수) 호출
3) lag 곡선 — 시간 어긋남 k 프레임일 때 median|Δ| (0 에서 chance 까지 어떻게 오르나)

전부 운영 함수(H.deviate → app._deviation_against → motiondtw.per_joint_deviation) 호출.
"""
from __future__ import annotations
import json, sys, os
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

refs = H.load_references()
facts = json.load(open(f"{D}/facts.json"))

out = {}

for mid, rdoc in sorted(refs.items()):
    M = H.ref_matrix(rdoc)           # (T,J)
    T, J = M.shape
    rec = {"frames": T, "fps": H.ref_fps_of(rdoc), "boundary": H.ref_boundary_of(rdoc)}

    # --- 1) 관절별 기술통계 -------------------------------------------------
    per = {}
    for j, jk in enumerate(H.JOINT_KEYS):
        col = M[:, j]
        col = col[np.isfinite(col)]
        d180 = 180.0 - col
        fd = np.abs(np.diff(col)) if col.size > 1 else np.array([0.0])
        per[jk] = dict(
            mean=float(col.mean()), sd=float(col.std(ddof=0)),
            lo=float(col.min()), hi=float(col.max()),
            rng=float(col.max() - col.min()),
            iqr=float(np.percentile(col, 75) - np.percentile(col, 25)),
            dist180_mean=float(d180.mean()),
            dist180_median=float(np.median(d180)),
            frame_dabs_median=float(np.median(fd)),
            frame_dabs_mean=float(fd.mean()),
        )
    rec["per_joint"] = per
    # 전 관절 통합 (이 조사 스칼라와 같은 집계 = 관절 중앙값)
    rec["agg"] = {
        k: float(np.median([per[jk][k] for jk in H.JOINT_KEYS]))
        for k in ("sd", "rng", "iqr", "dist180_mean", "dist180_median",
                  "frame_dabs_median", "frame_dabs_mean")
    }
    rec["agg"]["sd_pooled"] = float(np.std(M[np.isfinite(M)], ddof=0))

    # --- 2a) analytic chance: 전 프레임쌍 --------------------------------
    # |a[t1,j]-a[t2,j]| 의 중앙값 (t1<t2 전쌍). T<=931 → 최대 ~43만쌍, 메모리 OK.
    ch = {}
    iu = np.triu_indices(T, k=1)
    for j, jk in enumerate(H.JOINT_KEYS):
        col = M[:, j]
        dif = np.abs(col[iu[0]] - col[iu[1]])
        ch[jk] = float(np.median(dif))
    rec["chance_analytic_per_joint"] = ch
    rec["chance_analytic"] = float(np.median([ch[jk] for jk in H.JOINT_KEYS]))

    # --- 2b) operational chance: 셔플 → 운영 deviate ----------------------
    sc, devs = [], []
    for seed in range(8):
        rng = np.random.default_rng(1000 + seed)
        Ms = M[rng.permutation(T)]
        dev, match = H.deviate(Ms, rdoc)
        devs.append(dev)
        sc.append(H.scalar(dev))
    rec["chance_shuffle_scalar_median"] = float(np.median(sc))
    rec["chance_shuffle_scalar_lo"] = float(np.min(sc))
    rec["chance_shuffle_scalar_hi"] = float(np.max(sc))
    rec["chance_shuffle_per_joint"] = {
        jk: float(np.median([d[i] for d in devs])) for i, jk in enumerate(H.JOINT_KEYS)
    }

    # --- 3) lag 곡선 -------------------------------------------------------
    lag = {}
    for k in (1, 2, 3, 5, 8, 12, 20, 30, 50):
        if k >= T:
            continue
        v = [float(np.median(np.abs(M[k:, j] - M[:-k, j]))) for j in range(J)]
        lag[k] = float(np.median(v))
    rec["lag_curve"] = lag

    # --- 운영 자기비교 (셔플 없음) = 구조적 0 확인 -------------------------
    dev0, m0 = H.deviate(M, rdoc)
    rec["identity_scalar"] = H.scalar(dev0)
    rec["identity_dtw"] = float(m0.distance)

    out[mid] = rec
    print(f"{mid:26s} T={T:4d} chance_an={rec['chance_analytic']:6.2f} "
          f"chance_shuf={rec['chance_shuffle_scalar_median']:6.2f} "
          f"sd={rec['agg']['sd']:6.2f} rng={rec['agg']['rng']:7.2f} "
          f"d180={rec['agg']['dist180_median']:6.2f} "
          f"fd={rec['agg']['frame_dabs_median']:5.2f} id={rec['identity_scalar']:.3f}")

json.dump(out, open(f"{D}/out/b_c5_stats.json", "w"), indent=1)
print("\nwrote out/b_c5_stats.json")
