"""조사 A 단계8 — 같은 영상을 다시 분석하면 각도행렬이 얼마나 달라지나(재현성).

같은 videoKey 의 분석들을 짝지어 |Δ각도| 분포를 낸다. 프레임 수가 같으므로
시간축은 통제돼 있다 — 순수한 포즈 추출 재현성이다.
"""
import json, sys, collections, itertools
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

facts = json.load(open(f"{H.D}/facts.json"))
by_id = {s["id"]: s for s in H.load_students()}
fact_by_id = {f["id"]: f for f in facts}

g = collections.defaultdict(list)
for f in facts:
    if f["vk"]:
        g[f["vk"]].append(f["id"])

rows = []
print(f"{'videoKey':46s}{'n':>4s}{'distinct':>9s}{'pair med|d|':>12s}{'p90':>8s}"
      f"{'max':>8s}{'scalar med':>11s}{'scalar sd':>10s}")
for vk, ids in sorted(g.items()):
    if len(ids) < 2:
        continue
    mats = {i: H.student_matrix(by_id[i]) for i in ids}
    # 서로 다른 행렬이 몇 종인가
    sigs = {}
    for i, M in mats.items():
        k = (M.shape, float(np.nansum(M)))
        sigs.setdefault(round(k[1], 6), []).append(i)
    ids2 = [v[0] for v in sigs.values()]          # 행렬 종류별 대표 1개
    meds, p90s, mx = [], [], 0.0
    for a, b in itertools.combinations(ids2, 2):
        A, B = mats[a], mats[b]
        if A.shape != B.shape:
            continue
        d = np.abs(A - B)
        meds.append(float(np.nanmedian(d))); p90s.append(float(np.nanpercentile(d, 90)))
        mx = max(mx, float(np.nanmax(d)))
    sc = np.array([fact_by_id[i]["scalar"] for i in ids])
    r = dict(vk=vk, n=len(ids), distinct=len(ids2),
             pair_med=(float(np.median(meds)) if meds else 0.0),
             pair_p90=(float(np.median(p90s)) if p90s else 0.0), pair_max=mx,
             scalar_med=float(np.median(sc)), scalar_sd=float(sc.std()),
             ref=fact_by_id[ids[0]]["ref"], label=fact_by_id[ids[0]]["label"])
    rows.append(r)
    print(f"{vk[:45]:46s}{r['n']:4d}{r['distinct']:9d}{r['pair_med']:12.2f}"
          f"{r['pair_p90']:8.2f}{r['pair_max']:8.1f}{r['scalar_med']:11.2f}{r['scalar_sd']:10.3f}")
json.dump(rows, open(f"{H.D}/out/a_rerun.json", "w"))
