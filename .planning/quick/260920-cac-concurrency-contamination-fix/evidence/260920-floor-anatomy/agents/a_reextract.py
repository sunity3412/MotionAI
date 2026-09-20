"""조사 A 단계3 — 포즈 재추출 몫.

학생(10fps, step3) 격자와 기준(15fps, step2) 격자는 원본 30fps 에서 6프레임마다
겹친다 → 학생 row 2k 와 기준 row 3k 는 **같은 원본 프레임**이다.
그 짝의 잔차 = 시간축이 0 인 조건에서의 포즈 재추출 몫.

동시에
  (a) 강체 시간지도(배율 1.5 고정, 시프트 스캔) 최적 잔차
  (b) 자유 매칭(각 학생행 -> 임의 기준행 최근접) 잔차 = 정렬이 무한히 좋아도 남는 바닥
  (c) 좌우 라벨 스왑 가설 (rot180 차이) 검정
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

SWAP = [1, 0, 3, 2, 5, 4, 7, 6]  # left<->right 열 교환
refs = H.load_references(); by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
selfs, seen = [], set()
for f in facts:
    if f["label"] == "self" and f["ref"] not in seen:
        seen.add(f["ref"]); selfs.append(f)

res = []
for f in sorted(selfs, key=lambda x: x["ref"]):
    U = H.student_matrix(by_id[f["id"]]); R = H.ref_matrix(refs[f["ref"]])
    nu, nr = U.shape[0], R.shape[0]
    scale = nr / nu  # ~1.4975

    # (0) 같은 원본 프레임 짝: U[2k] <-> R[3k], 시프트 스캔으로 최적 오프셋 확인
    best = None
    for sh in np.arange(-6, 6.01, 0.5):
        idx = np.round(np.arange(nu) * scale + sh)
        ok = (idx >= 0) & (idx <= nr - 1)
        idx = idx[ok].astype(int)
        d = np.abs(U[ok] - R[idx])
        v = float(np.median(d))
        if best is None or v < best[0]:
            best = (v, float(sh), d)
    rigid_med, rigid_sh, rigid_d = best

    # (c) 좌우 스왑
    idx = np.round(np.arange(nu) * scale + rigid_sh)
    ok = (idx >= 0) & (idx <= nr - 1); idx = idx[ok].astype(int)
    d_id = np.abs(U[ok] - R[idx])
    d_sw = np.abs(U[ok] - R[idx][:, SWAP])
    swap_better_frac = float(np.mean(np.median(d_sw, axis=1) < np.median(d_id, axis=1)))

    # (b) 자유 매칭 최근접 (8관절 median 거리 최소인 기준행)
    free_rows = []
    for i in range(nu):
        dd = np.median(np.abs(R - U[i]), axis=1)
        free_rows.append(int(np.argmin(dd)))
    free_rows = np.asarray(free_rows)
    d_free = np.abs(U - R[free_rows])

    # 운영 경로 (DTW)
    dev, m = H.deviate(U, refs[f["ref"]])

    r = dict(
        motion=f["ref"], nu=nu, nr=nr, scale=round(scale, 4),
        live_scalar=round(H.scalar(dev), 3),
        rigid_shift=rigid_sh,
        rigid_scalar=round(float(np.median(np.median(rigid_d, axis=0))), 3),
        rigid_perjoint=[round(float(x), 2) for x in np.median(rigid_d, axis=0)],
        free_scalar=round(float(np.median(np.median(d_free, axis=0))), 3),
        free_perjoint=[round(float(x), 2) for x in np.median(d_free, axis=0)],
        dtw_perjoint=[round(float(x), 2) for x in dev],
        swap_scalar=round(float(np.median(np.median(d_sw, axis=0))), 3),
        swap_better_frac=round(swap_better_frac, 3),
        free_row_monotonic_frac=round(float(np.mean(np.diff(free_rows) >= 0)), 3),
    )
    res.append(r)
    print(json.dumps(r, ensure_ascii=False))
json.dump(res, open(f"{H.D}/out/a_reextract.json", "w"))
