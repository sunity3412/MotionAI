"""조사 G 단계 7 — 정은지 fixture/reference 가 아닌 '내용'이 몇 편인가를 엄밀히."""
from __future__ import annotations
import json, collections, numpy as np
D = "."
rows = json.load(open("out/G_match.json"))
REFS = sorted(rows[0]["dist"].keys())
for r in rows:
    r["ok"] = (r["pred"] == r["ref"])
    r["vec"] = np.array([r["dist"][k] for k in REFS])
    r["src"] = r["vk"] or (f"fn:{r['fn']}" if r["fn"] else f"id:{r['id']}")
V = np.vstack([r["vec"] for r in rows]); n = len(rows)
nm = np.linalg.norm(V, axis=1)
Dm = np.linalg.norm(V[:, None, :] - V[None, :, :], axis=2) / np.maximum(nm[:, None], 1e-9)
for tol in (0.02, 0.05):
    par = list(range(n))
    def find(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    A = Dm <= tol
    for i in range(n):
        for j in np.nonzero(A[i])[0]:
            a, b = find(i), find(int(j))
            if a != b: par[a] = b
    cl = collections.defaultdict(list)
    for i in range(n): cl[find(i)].append(rows[i])
    anchored, free = [], []
    for c, rs in cl.items():
        has = any((r["vk"] or "").startswith(("fixtures/", "reference/")) for r in rs)
        (anchored if has else free).append(rs)
    fixfr = {(int(np.median([r["frames"] for r in rs])), rs[0]["ref"]) for rs in anchored}
    print(f"tol={tol}  총군집 {len(cl)}  fixture/reference 로 확인된 군집 {len(anchored)}  "
          f"그 외 {len(free)}")
    ok = 0
    for rs in sorted(free, key=lambda x: (x[0]["ref"], -len(x))):
        fr = int(np.median([r["frames"] for r in rs]))
        same = (fr, rs[0]["ref"]) in fixfr
        good = sum(1 for r in rs if r["ok"]); ok += (good == len(rs))
        names = sorted({r["src"] for r in rs})
        print(f"   {'OK' if good==len(rs) else 'X '} n={len(rs):3d} {rs[0]['ref']:24s}"
              f" {fr:4d}f {'[fixture 와 같은 프레임수]' if same else '[새 내용]':26s}"
              f" {' | '.join(s[-38:] for s in names[:2])}")
    print(f"   -> 전부 맞춘 군집 {ok}/{len(free)}")
    print()
