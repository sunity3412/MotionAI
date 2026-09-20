"""조사 G 단계 5 — (a) 마진 겹침 재검(§11-1 '겹치지 않는다' 주장), (b) 길이 편향."""
from __future__ import annotations
import json, collections, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

rows = json.load(open(f"{D}/out/G_match.json"))
REFS = sorted(rows[0]["dist"].keys())
refs = H.load_references()
RLEN = {k: H.ref_matrix(v).shape[0] for k, v in refs.items()}

for r in rows:
    r["ok"] = (r["pred"] == r["ref"])
    v = sorted(r["dist"].values())
    r["margin"] = (v[1] - v[0]) / v[0]
    r["dmin"] = v[0]
    r["src"] = r["vk"] or (f"fn:{r['fn']}" if r["fn"] else f"id:{r['id']}")

out = []
P = out.append
P("=" * 84)
P("조사 G 보조 3 — 마진 겹침 / 길이 편향")
P("=" * 84)
P("")
P("[a] §11-1 은 '맞춘 것 최소 0.069 vs 틀린 것 최대 0.056 — 겹치지 않는다'고 적었다.")
bad = [r for r in rows if not r["ok"]]
good = [r for r in rows if r["ok"]]
bmax = max(r["margin"] for r in bad)
low = sorted([r for r in good if r["margin"] <= bmax], key=lambda r: r["margin"])
P(f"    전수 875: 틀린 것 최대 마진 = {bmax:.3f}")
P(f"             맞춘 것 중 그 이하 = {len(low)}건  -> {'겹친다' if low else '겹치지 않는다'}")
for r in low:
    P(f"       margin={r['margin']:.3f}  {r['ref']:24s} {r['src'][-44:]}")
P("")
P(f"    맞춘 것 최소 마진 = {min(r['margin'] for r in good):.3f} "
  f"(§11-1 은 0.069 라 적었다 — 표본이 달라 직접 비교 불가)")
P("")
P("    ★ 관측은 '오분류가 한 쌍이고 그 마진이 낮다'이지 '문턱 X가 옳다'가 아니다.")
P("      전수에서는 맞춘 것도 같은 띠에 들어온다 — 마진만으로 거절선을 못 긋는다.")
P("")

P("[b] 길이 편향 — 정규화 DTW 거리가 시퀀스 길이를 탄다")
fr = np.array([r["frames"] for r in rows], dtype=float)
dm = np.array([r["dmin"] for r in rows], dtype=float)


def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


P(f"    학생 프레임수 vs 1등거리        Spearman r = {spearman(fr, dm):+.3f}  (n={len(rows)})")
# 분석 내부 — 기준 길이 vs 그 기준까지의 거리
rs_ = []
for r in rows:
    d = np.array([r["dist"][k] for k in REFS])
    L = np.array([RLEN[k] for k in REFS], dtype=float)
    rs_.append(spearman(L, d))
P(f"    (분석 내부) 기준 길이 vs 거리   Spearman r 중앙값 = {np.median(rs_):+.3f} "
  f"[p25 {np.percentile(rs_,25):+.3f}, p75 {np.percentile(rs_,75):+.3f}]")
P("")
P("    기준을 학생자리에 넣은 11x11 행평균 (행=길이순)")
mat = json.load(open(f"{D}/out/G_ref_x_ref.json"))
for k in sorted(RLEN, key=lambda x: RLEN[x]):
    vals = [v for kk, v in mat[k].items() if kk != k]
    P(f"      {k:26s} len={RLEN[k]:4d}  타기준까지 평균거리={np.mean(vals):6.1f}")
lens = np.array([RLEN[k] for k in sorted(RLEN, key=lambda x: RLEN[x])], dtype=float)
means = np.array([np.mean([v for kk, v in mat[k].items() if kk != k])
                  for k in sorted(RLEN, key=lambda x: RLEN[x])])
P(f"      -> Spearman(길이, 평균거리) = {spearman(lens, means):+.3f}  (n=11)")
P("")
P("    [확인] 긴 시퀀스를 학생자리에 넣으면 정규화 거리가 전반적으로 작아진다.")
P("    [미확인] 그 편향이 argmin 을 뒤집는 경로는 코드로 못 이었다 — climb 오분류 4개 중")
P("             틀린 쪽이 긴 클립(138·172프레임)이고 맞은 쪽이 짧은 클립(62·80)이라는")
P("             상관만 관측했다. 같은 영상을 길이만 바꿔 넣은 대조군은 안 돌렸다.")

txt = "\n".join(out)
open(f"{D}/out/G_margin_overlap.txt", "w").write(txt)
print(txt)
