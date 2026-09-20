"""조사 G 단계 3 — 표본 출처 분해 + 오분류 해부 + 기준끼리의 거리(문제 자체의 난이도).

정확도가 '무엇에 대한' 정확도인지 가르는 것이 목적이다.
"""
from __future__ import annotations
import json, collections, re, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
rows = json.load(open(f"{D}/out/G_match.json"))
students = {s["id"]: s for s in json.load(open(f"{D}/students.json"))}
REFS = sorted(rows[0]["dist"].keys())

FIXTURE_FN = re.compile(r"잘못된|잘못되|fixtures:|correct|fault|fail|ok\.mp4|-1080|_user\.mp4|okr\d|failr\d")


def provenance(r):
    vk = r["vk"] or ""
    fn = r["fn"] or ""
    if vk.startswith("reference/"):
        return "A.정은지 기준영상 자체"
    if vk.startswith("fixtures/"):
        return "B.정은지 fixture(성공/실패 페어)"
    if vk.startswith("uploads/"):
        return "D.실제 업로드"
    if "talkv" in fn or fn.startswith("_dJMca"):
        return "C.talkv 외부영상"
    if "belle" in fn.lower():
        return "E.belle 본인촬영"
    if FIXTURE_FN.search(fn):
        return "B.정은지 fixture(성공/실패 페어)"
    return "F.출처불명"


for r in rows:
    r["ok"] = (r["pred"] == r["ref"])
    r["prov"] = provenance(r)
    r["src"] = r["vk"] or (f"fn:{r['fn']}" if r["fn"] else f"id:{r['id']}")

out = []
P = out.append
P("=" * 84)
P("조사 G 보조 — 이 정확도가 '무엇에 대한' 정확도인가")
P("=" * 84)
P("")
P("[A] 출처별 정확도 (분석 단위 / 고유소스 단위)")
P(f"    {'출처':34s}{'분석':>14s}{'고유소스':>14s}")
bysrc = collections.defaultdict(list)
for r in rows:
    bysrc[(r["src"], r["ref"])].append(r)
for prov in sorted({r["prov"] for r in rows}):
    rs = [r for r in rows if r["prov"] == prov]
    k = sum(1 for r in rs if r["ok"])
    srcs = {(r["src"], r["ref"]) for r in rs}
    ks = sum(1 for s in srcs
             if collections.Counter(x["pred"] for x in bysrc[s]).most_common(1)[0][0] == s[1])
    P(f"    {prov:34s}{k:5d}/{len(rs):<5d}{k/len(rs)*100:5.1f}%{ks:6d}/{len(srcs):<4d}"
      f"{ks/len(srcs)*100:6.1f}%")
P("")
P("    ※ A/B 는 정은지 영상을 정은지 기준에 붙이는 문제다 — 같은 사람·같은 촬영.")
P("      학생 매칭 난이도의 하한이지 학생 매칭 정확도가 아니다.")
P("")

P("[B] 오분류 19건 해부 — 전부 ref-climb -> ref-sideway-spin")
bad = [r for r in rows if not r["ok"]]
P(f"    {'source':52s}{'frames':>7s}{'d(climb)':>10s}{'d(sideway)':>11s}{'차':>8s}")
seen = {}
for r in sorted(bad, key=lambda x: x["src"]):
    seen.setdefault(r["src"], []).append(r)
for src, rs in sorted(seen.items()):
    dc = np.median([r["dist"]["ref-climb"] for r in rs])
    ds = np.median([r["dist"]["ref-sideway-spin"] for r in rs])
    fr = np.median([r["frames"] for r in rs])
    P(f"    {src[-50:]:52s}{fr:7.0f}{dc:10.2f}{ds:11.2f}{dc-ds:8.2f}  x{len(rs)}")
P("")
P("    맞춘 climb 19건(정은지 fixture + belle 촬영) 비교군")
good = [r for r in rows if r["ref"] == "ref-climb" and r["ok"]]
seen2 = {}
for r in good:
    seen2.setdefault(r["src"], []).append(r)
for src, rs in sorted(seen2.items()):
    dc = np.median([r["dist"]["ref-climb"] for r in rs])
    ds = np.median([r["dist"]["ref-sideway-spin"] for r in rs])
    fr = np.median([r["frames"] for r in rs])
    P(f"    {src[-50:]:52s}{fr:7.0f}{dc:10.2f}{ds:11.2f}{dc-ds:8.2f}  x{len(rs)}")
P("")

P("[C] 기준 11편 서로의 DTW 거리 — 문제 자체가 갈라지는가")
P("    (운영 motion_dtw. 행=학생자리에 넣은 기준, 열=비교 기준)")
import harness as H  # noqa: E402
refs = H.load_references()
mat = {}
for a in REFS:
    ma = H.ref_matrix(refs[a])
    row = {}
    for b in REFS:
        _dev, m = H.deviate(ma, refs[b])
        row[b] = float(m.distance)
    mat[a] = row
short = {k: k.replace("ref-", "")[:9] for k in REFS}
P("    " + f"{'':14s}" + "".join(f"{short[b]:>10s}" for b in REFS))
for a in REFS:
    P("    " + f"{short[a]:14s}" + "".join(f"{mat[a][b]:10.1f}" for b in REFS))
P("")
P("    각 기준을 학생자리에 넣었을 때 argmin 이 자기 자신인가:")
for a in REFS:
    best = min(mat[a], key=mat[a].get)
    v = sorted(mat[a].values())
    marg = (v[1] - v[0]) / v[0] if v[0] > 0 else float("inf")
    P(f"      {a:26s} argmin={best:26s} {'OK' if best==a else 'X'}  마진={marg:.3f}")
P("")
P("    climb <-> sideway-spin 상호거리: "
  f"{mat['ref-climb']['ref-sideway-spin']:.2f} / {mat['ref-sideway-spin']['ref-climb']:.2f}  "
  f"(climb 자기거리 {mat['ref-climb']['ref-climb']:.2f}, "
  f"sideway 자기거리 {mat['ref-sideway-spin']['ref-sideway-spin']:.2f})")
P("")
P("[D] 우연 수준 대조 — 라벨을 섞으면 얼마가 나오나")
prior = collections.Counter(r["ref"] for r in rows)
n = len(rows)
maj = max(prior.values()) / n * 100
chance = sum((c / n) ** 2 for c in prior.values()) * 100
P(f"    균등 11지선다 = 9.1%  ·  최빈 기준 항상찍기 = {maj:.1f}%  ·  사전분포 무작위 = {chance:.1f}%")
P(f"    실측 = {sum(1 for r in rows if r['ok'])/n*100:.1f}%")

txt = "\n".join(out)
open(f"{D}/out/G_provenance.txt", "w").write(txt)
json.dump({a: mat[a] for a in mat}, open(f"{D}/out/G_ref_x_ref.json", "w"), indent=1)
print(txt)
