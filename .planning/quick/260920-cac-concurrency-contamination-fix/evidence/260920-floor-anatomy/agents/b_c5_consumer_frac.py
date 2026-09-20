"""소비처 요약 — 오늘 코드에 통과시켰을 때 이 축이 점수를 건드리는 비율."""
import json, collections, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
rows = json.load(open(f"{D}/out/b_c5_consumer_ci.json"))
g = collections.defaultdict(list)
for r in rows:
    g[(r["ref"], r["label"])].append(r)
hdr = (f"{'motion':24s} {'label':8s} {'n':>4s} | {'dev':>6s} {'FIN':>4s} {'FINch':>5s} | "
       f"{'감점발화%':>9s} {'억제만%':>8s} {'무접촉%':>8s} | {'FIN=100%':>9s}")
print(hdr); print("-" * len(hdr))
for k, rs in sorted(g.items()):
    n = len(rs)
    fire = sum(1 for r in rs if r["nrec"] > 0) / n * 100
    supo = sum(1 for r in rs if r["nrec"] == 0 and r["nsup"] > 0) / n * 100
    none = sum(1 for r in rs if r["nrec"] == 0 and r["nsup"] == 0) / n * 100
    f100 = sum(1 for r in rs if r["final"] >= 100) / n * 100
    print(f"{k[0]:24s} {k[1]:8s} {n:4d} | {np.median([r['scalar'] for r in rs]):6.2f} "
          f"{np.median([r['final'] for r in rs]):4.0f} {np.median([r['final_ch'] for r in rs]):5.0f} | "
          f"{fire:9.0f} {supo:8.0f} {none:8.0f} | {f100:9.0f}")
