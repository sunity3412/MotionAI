"""조사 G 단계 4 — 진짜 고유 영상 수. 파일명/videoKey 는 못 믿는다(같은 영상이 여러 이름).

각 분석의 '기준 11편에 대한 거리벡터'는 그 영상의 지문이다. 같은 영상이면 재추출
잡음만큼만 다르다. 상대거리 <= tol 로 단일연결 군집 → 군집 = 고유 영상 추정치.
tol 은 데이터에 맞춰 고른 문턱이 아니라 sweep 해서 안정 구간을 본다(커브핏 방지).
"""
from __future__ import annotations
import json, collections, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
rows = json.load(open(f"{D}/out/G_match.json"))
REFS = sorted(rows[0]["dist"].keys())
for r in rows:
    r["ok"] = (r["pred"] == r["ref"])
    r["vec"] = np.array([r["dist"][k] for k in REFS], dtype=float)
    r["src"] = r["vk"] or (f"fn:{r['fn']}" if r["fn"] else f"id:{r['id']}")

V = np.vstack([r["vec"] for r in rows])
n = len(rows)
# 상대 L2 거리
norm = np.linalg.norm(V, axis=1)
Dm = np.linalg.norm(V[:, None, :] - V[None, :, :], axis=2) / np.maximum(norm[:, None], 1e-9)

out = []
P = out.append
P("=" * 84)
P("조사 G 보조 2 — 표본의 진짜 크기 (거리벡터 지문 군집)")
P("=" * 84)
P("")
P(f"    {'tol':>7s}{'군집수':>8s}{'군집단위 정확도':>18s}{'최대군집':>9s}")
best = None
for tol in [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.2]:
    A = Dm <= tol
    # union-find
    par = list(range(n))
    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for i in range(n):
        for j in np.nonzero(A[i])[0]:
            a, b = find(i), find(int(j))
            if a != b:
                par[a] = b
    cl = collections.defaultdict(list)
    for i in range(n):
        cl[find(i)].append(rows[i])
    # 군집 x 선택기준 단위 정확도 (다수결)
    units = collections.defaultdict(list)
    for c, rs in cl.items():
        for r in rs:
            units[(c, r["ref"])].append(r)
    k = sum(1 for (c, ref), rs in units.items()
            if collections.Counter(x["pred"] for x in rs).most_common(1)[0][0] == ref)
    P(f"    {tol:7.3f}{len(cl):8d}{k:8d}/{len(units):<4d}{k/len(units)*100:5.1f}%"
      f"{max(len(v) for v in cl.values()):9d}")
    if tol == 0.02:
        best = (cl, units)
P("")
P("    tol 0.005~0.05 구간에서 군집수가 거의 안 변하면 그 수가 고유 영상 추정치다.")
P("")

cl, units = best
P("[군집 목록 — tol=0.02] 각 군집의 이름들(= 같은 영상의 여러 이름)")
P(f"    {'n':>4s} {'선택기준':24s}{'ok':4s}{'frames':>7s}  이름들")
rowsout = []
for c, rs in cl.items():
    refs_ = collections.Counter(r["ref"] for r in rs)
    for ref, cnt in refs_.items():
        sub = [r for r in rs if r["ref"] == ref]
        pred = collections.Counter(r["pred"] for r in sub).most_common(1)[0][0]
        names = sorted({r["src"] for r in sub})
        rowsout.append((cnt, ref, pred == ref, int(np.median([r["frames"] for r in sub])),
                        names, pred))
for cnt, ref, ok, fr, names, pred in sorted(rowsout, key=lambda x: (x[2], x[1], -x[0])):
    nm = " | ".join(s[-42:] for s in names[:3]) + (" ..." if len(names) > 3 else "")
    P(f"    {cnt:4d} {ref:24s}{'OK' if ok else 'X->'+pred.replace('ref-','')[:8]:4s}{fr:7d}  {nm}")

txt = "\n".join(out)
open(f"{D}/out/G_truecount.txt", "w").write(txt)
print(txt)
