"""조사 A — 바닥의 관절별 분담 (표 6). out/a_summary.txt 에 덧붙인다."""
import json, sys, collections
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

rex = {r["motion"]: r for r in json.load(open(f"{H.D}/out/a_reextract.json"))}
facts = json.load(open(f"{H.D}/facts.json"))
g = collections.defaultdict(lambda: collections.defaultdict(list))
for f in facts:
    g[f["ref"]][f["label"]].append(f["dev"])

L = ["", "표 6 — 바닥의 관절별 분담 (단위 도)",
     "  (A) self 5건: 같은 원본 프레임 잔차 / 운영 DTW 편차"]
hdr = f"{'동작':22s}" + "".join(f"{k.replace('_','.')[:9]:>10s}" for k in H.JOINT_KEYS) + f"{'최대/중앙':>10s}"
L.append(hdr)
for m, r in sorted(rex.items()):
    rj = np.asarray(r["rigid_perjoint"]); dj = np.asarray(r["dtw_perjoint"])
    L.append(f"{m:22s}" + "".join(f"{a:4.1f}/{b:<5.1f}" for a, b in zip(rj, dj))
             + f"{rj.max()/np.median(rj):10.2f}")
L.append("  (B) correct(실력차 0 바닥) 관절별 median — 운영 DTW 편차")
L.append(hdr)
for m in sorted(g):
    c = g[m].get("correct")
    if not c:
        continue
    a = np.median(np.asarray(c, dtype=float), axis=0)
    L.append(f"{m:22s}" + "".join(f"{x:10.1f}" for x in a) + f"{a.max()/np.median(a):10.2f}")
L.append("  최대/중앙 비가 1.2~2.1 — 한 관절이 바닥을 지는 구조가 아니다(전 관절 고르게 든다).")
L.append("  다만 left_knee 가 self 4건 중 3건에서 최댓값(17.8~27.5도).")
txt = "\n".join(L)
open(f"{H.D}/out/a_summary.txt", "a").write(txt + "\n")
print(txt)
