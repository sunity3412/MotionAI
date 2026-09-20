"""조사 B 핵심 대조군 — 그 분석 그대로에서 '시간정보만' 파괴했을 때의 chance level.

같은 학생 각도행렬 / 같은 기준 doc / 같은 운영 함수(H.deviate → _deviation_against).
학생 프레임 순서만 무작위 셔플(4 seed) → DTW 가 시간축에서 아무 정보도 못 얻는 조건.
실제 편차가 이 chance 에 얼마나 붙어 있나 = 그 동작 축에 정보가 있나.
"""
from __future__ import annotations
import json, sys, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

students = H.load_students()
refs = H.load_references()
facts = {f["id"]: f for f in json.load(open(f"{D}/facts.json"))}

SEEDS = 4
res = []
t0 = time.time()
for n, s in enumerate(students):
    rdoc = refs.get(s["ref"])
    if rdoc is None:
        continue
    fa = facts.get(s["id"], {})
    M = H.student_matrix(s)
    dev, m = H.deviate(M, rdoc)
    real = H.scalar(dev)
    ch = []
    for k in range(SEEDS):
        rng = np.random.default_rng(7000 + k)
        d2, m2 = H.deviate(M[rng.permutation(M.shape[0])], rdoc)
        ch.append(H.scalar(d2))
    res.append(dict(id=s["id"], ref=s["ref"], label=fa.get("label", "unknown"),
                    vk=fa.get("vk"), frames=M.shape[0], real=real,
                    chance=float(np.median(ch)), chance_lo=float(np.min(ch)),
                    chance_hi=float(np.max(ch)), dtw=float(m.distance),
                    dev=[float(x) for x in dev]))
    if n % 100 == 0:
        print(f"  {n}/{len(students)} {time.time()-t0:.0f}s", flush=True)

json.dump(res, open(f"{D}/out/b_c5_crosschance.json", "w"))
print(f"done {len(res)} in {time.time()-t0:.0f}s")

# 집계
g = {}
for r in res:
    g.setdefault((r["ref"], r["label"]), []).append(r)
hdr = f"{'motion':24s} {'label':8s} {'n':>4s} {'real':>7s} {'chance':>7s} {'real/ch':>8s}"
print("\n" + hdr); print("-" * len(hdr))
tbl = []
for (mid, lab), rs in sorted(g.items()):
    real = float(np.median([r["real"] for r in rs]))
    ch = float(np.median([r["chance"] for r in rs]))
    ratios = [r["real"] / r["chance"] for r in rs if r["chance"] > 0]
    rat = float(np.median(ratios))
    tbl.append(dict(motion=mid, label=lab, n=len(rs), real=real, chance=ch, ratio=rat,
                    real_sd=float(np.std([r['real'] for r in rs], ddof=0)),
                    ratio_lo=float(np.min(ratios)), ratio_hi=float(np.max(ratios))))
    print(f"{mid:24s} {lab:8s} {len(rs):4d} {real:7.2f} {ch:7.2f} {rat:8.3f}")
json.dump(tbl, open(f"{D}/out/b_c5_crosschance_table.json", "w"), indent=1)
