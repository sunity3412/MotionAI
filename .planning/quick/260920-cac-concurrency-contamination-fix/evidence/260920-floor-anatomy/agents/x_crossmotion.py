"""반증 X1 — '시간 셔플 chance' 대조군이 진짜 대조군인가.

주장: "875건 전수에서 real/chance < 1 이 100% → 어느 동작도 chance 가 아니다."
의심: DTW path 는 단조 제약이다. **순서가 있는** 시퀀스는 셔플된 시퀀스보다
      구조적으로 항상 잘 정렬된다 — 내용이 맞든 틀리든. 그렇다면 ratio<1 은
      '이 축에 정보가 있다'가 아니라 '입력이 시간순이다'만 말한다.

검정: 완전히 **다른 동작**을 한 학생(시간순 그대로)을 이 기준에 넣는다.
      그 ratio 도 1 아래로 내려가는가? 내려가면 ratio<1 은 판별력이 없다.

전부 운영 함수 H.deviate(=app._deviation_against) 호출. 재구현 0.
"""
from __future__ import annotations
import json, sys, collections, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

students = H.load_students()
refs = H.load_references()
facts = {f["id"]: f for f in json.load(open(f"{D}/facts.json"))}

# 동작별 대표 학생 1명 (correct 우선, 없으면 self) — 고유 videoKey 기준
rep = {}
for s in students:
    fa = facts.get(s["id"], {})
    lab = fa.get("label")
    if lab not in ("correct", "self"):
        continue
    key = fa.get("ref")
    if key in rep:
        continue
    rep[key] = (s, lab, fa.get("vk"))
print("대표 학생:", {k: v[1] for k, v in sorted(rep.items())})

SEEDS = 2
rows = []
t0 = time.time()
for rid, rdoc in sorted(refs.items()):
    for sid, (s, lab, vk) in sorted(rep.items()):
        M = H.student_matrix(s)
        dev, m = H.deviate(M, rdoc)
        real = H.scalar(dev)
        ch = []
        for k in range(SEEDS):
            rng = np.random.default_rng(7000 + k)
            d2, _ = H.deviate(M[rng.permutation(M.shape[0])], rdoc)
            ch.append(H.scalar(d2))
        chance = float(np.median(ch))
        rows.append(dict(ref=rid, student_motion=sid, label=lab, same=(rid == sid),
                         real=real, chance=chance, ratio=real / chance if chance else float("nan"),
                         dtw=float(m.distance)))
print(f"{len(rows)} pairs in {time.time()-t0:.0f}s\n")

json.dump(rows, open(f"{D}/out/x_crossmotion.json", "w"), indent=1)

same = [r for r in rows if r["same"]]
diff = [r for r in rows if not r["same"]]
print("=== ratio (real/chance) 분포 ===")
for name, rs in (("같은 동작(정은지 correct/self)", same), ("다른 동작(내용 완전 불일치)", diff)):
    v = np.array([r["ratio"] for r in rs], float)
    print(f"{name:32s} n={len(v):3d} median={np.median(v):.3f} "
          f"p10={np.percentile(v,10):.3f} p90={np.percentile(v,90):.3f} "
          f"max={v.max():.3f} <1 비율={100*np.mean(v<1):.0f}%")

print("\n=== 기준별: 같은동작 ratio vs 다른동작 ratio 중앙값 ===")
print(f"{'reference':24s} {'same':>7s} {'diff med':>9s} {'diff min':>9s} "
      f"{'다른동작 중 same 보다 낮은 건수':>28s}")
byref = collections.defaultdict(list)
for r in diff:
    byref[r["ref"]].append(r)
for rid in sorted(refs):
    s_ = [r for r in same if r["ref"] == rid]
    d_ = byref[rid]
    sv = s_[0]["ratio"] if s_ else float("nan")
    dv = np.array([r["ratio"] for r in d_], float)
    lower = int(np.sum(dv < sv))
    print(f"{rid:24s} {sv:7.3f} {np.median(dv):9.3f} {dv.min():9.3f} {lower:20d}/{len(dv)}")
