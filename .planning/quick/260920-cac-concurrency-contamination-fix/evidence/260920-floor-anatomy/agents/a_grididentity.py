"""조사 A 단계1b — self 학생행렬이 기준행렬의 '같은 원본 프레임'을 담고 있나?

가설: 원본 30fps. 기준 = step2(→14.94fps), 학생(라이브) = step3(→9.97fps).
그러면 학생 row 2k == 기준 row 3k (같은 원본 프레임). 그 등식을 실측한다.
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

refs = H.load_references()
by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
selfs, seen = [], set()
for f in facts:
    if f["label"] == "self" and f["ref"] not in seen:
        seen.add(f["ref"]); selfs.append(f)

for f in sorted(selfs, key=lambda x: x["ref"]):
    U = H.student_matrix(by_id[f["id"]]); R = H.ref_matrix(refs[f["ref"]])
    nu, nr = U.shape[0], R.shape[0]
    # (1) 정확 격자 가설: U[2k] == R[3k]
    K = min(nu // 2, nr // 3)
    d_exact = np.abs(U[0:2*K:2] - R[0:3*K:3])
    # (2) 최근접 행: 각 학생행에 가장 가까운 기준행 거리
    best = []
    for i in range(0, nu, max(1, nu // 60)):
        d = np.nanmedian(np.abs(R - U[i]), axis=1)
        j = int(np.nanargmin(d))
        best.append((i, j, float(d[j]), float(j) / max(i, 1e-9)))
    bj = np.array([b[1] for b in best], dtype=float)
    bi = np.array([b[0] for b in best], dtype=float)
    bd = np.array([b[2] for b in best], dtype=float)
    slope = float(np.polyfit(bi, bj, 1)[0]) if len(bi) > 2 else float("nan")
    print(json.dumps(dict(
        motion=f["ref"], nu=nu, nr=nr,
        exact_grid_hypothesis=dict(
            pairs=int(K),
            median_abs_diff_deg=round(float(np.nanmedian(d_exact)), 4),
            p90=round(float(np.nanpercentile(d_exact, 90)), 4),
            frac_below_0p01deg=round(float(np.mean(d_exact < 0.01)), 4),
        ),
        nearest_ref_row=dict(
            median_dist_deg=round(float(np.median(bd)), 3),
            p90_dist_deg=round(float(np.percentile(bd, 90)), 3),
            slope_j_over_i=round(slope, 4),
        ),
    ), ensure_ascii=False))
