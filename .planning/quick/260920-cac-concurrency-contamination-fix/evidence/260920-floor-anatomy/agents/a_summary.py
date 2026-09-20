"""조사 A 최종 표 — out/a_summary.txt 로 저장."""
import json, sys, collections
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

gf = json.load(open(f"{H.D}/out/a_gridfloor.json"))
gf2 = {r["motion"]: r for r in json.load(open(f"{H.D}/out/a_gridfloor2.json"))}
rex = {r["motion"]: r for r in json.load(open(f"{H.D}/out/a_reextract.json"))}
facts = json.load(open(f"{H.D}/facts.json"))
refs = H.load_references()

g = collections.defaultdict(lambda: collections.defaultdict(list))
for f in facts:
    g[f["ref"]][f["label"]].append(f["scalar"])

def gfv(m, tag):
    v = [r["scalar"] for r in gf if r["motion"] == m and r["grid"].startswith(tag)]
    return float(np.median(v)) if v else float("nan")

def inverted_frac(rdoc):
    k = rdoc["joints3dKeys"]; n = rdoc["joints3dFrames"]; d = int(rdoc.get("coordDim") or 3)
    K = np.asarray(rdoc["joints3d"], dtype=float).reshape(n, len(k), d)
    i = {nm: j for j, nm in enumerate(k)}
    sy = (K[:, i["left_shoulder"], 1] + K[:, i["right_shoulder"], 1]) / 2
    hy = (K[:, i["left_hip"], 1] + K[:, i["right_hip"], 1]) / 2
    return float(np.mean(sy - hy > 0))

L = []
A = L.append
A("표 1 — 11동작 시간격자 바닥 (기준 행렬을 그 자체로부터 재샘플링, 포즈 데이터 동일)")
A("  지표 = 이 축의 그 스칼라(관절별 median|Δ| 8개의 중앙값), 단위 도")
A(f"{'동작':24s}{'ref fps':>8s}{'ref행':>6s}{'identity':>9s}{'ratio(→10fps)':>14s}"
  f"{'step2':>7s}{'step3':>7s}{'interp0.5*':>11s}")
for m in sorted(refs):
    A(f"{m:24s}{H.ref_fps_of(refs[m]):8.2f}{H.ref_matrix(refs[m]).shape[0]:6d}"
      f"{gfv(m,'identity'):9.3f}{gfv(m,'ratio'):14.3f}{gfv(m,'step2'):7.3f}"
      f"{gfv(m,'step3'):7.3f}{gf2[m]['interp0.5']:11.3f}")
A("  * interp0.5 = 기준 행 '사이' 시점을 선형보간으로 세운 격자 — 격자 몫의 상한(실제 포즈 아님)")
A("  * ratio 격자에서 정렬 스텝의 67% 가 |Δ|=0 (원본 행과 정확히 짝) → median 0.")
A("    같은 격자의 mean|Δ| 는 1.05~2.93 도 (median 이 아니었다면 0 이 아니다).")
A("")
A("표 2 — self 4+1건 바닥 분해 (학생 = 기준 영상 그 자체)")
A(f"{'동작':24s}{'운영 편차':>10s}{'격자(정확)':>11s}{'격자(보간상한)':>15s}"
  f"{'같은원본프레임':>15s}{'자유매칭하한':>13s}{'격자몫%':>9s}")
for m in ["ref-combo", "ref-foxtop", "ref-foxtop-split", "ref-invert", "ref-sideway-spin"]:
    r = rex[m]; grid = gf2[m]["interp0.5"]
    A(f"{m:24s}{r['live_scalar']:10.2f}{gfv(m,'ratio'):11.3f}{grid:15.2f}"
      f"{r['rigid_scalar']:15.2f}{r['free_scalar']:13.2f}{grid/r['live_scalar']*100:8.0f}%")
A("  같은원본프레임 = 학생 row 2k ↔ 기준 row 3k (원본 30fps 에서 6프레임마다 겹침, 시프트 스캔 최적)")
A("  자유매칭하한 = 각 학생행에 임의의 기준행을 붙여도 남는 잔차 (단조성 없음 — 도달 불가 하한)")
A("")
A("표 3 — 바닥과 '역립 프레임 비율'")
A(f"{'동작':24s}{'역립%':>7s}{'correct':>9s}{'fault':>8s}{'self':>7s}{'같은프레임잔차':>15s}")
pairs = []
for m in sorted(refs):
    iv = inverted_frac(refs[m]) * 100
    c = g[m].get("correct"); fl = g[m].get("fault"); se = g[m].get("self")
    floor = np.median(c) if c else (np.median(se) if se else None)
    if floor is not None:
        pairs.append((iv, floor))
    A(f"{m:24s}{iv:6.1f}%"
      f"{(np.median(c) if c else float('nan')):9.1f}{(np.median(fl) if fl else float('nan')):8.1f}"
      f"{(np.median(se) if se else float('nan')):7.1f}"
      f"{(rex[m]['rigid_scalar'] if m in rex else float('nan')):15.2f}")
iv = np.array([p[0] for p in pairs]); fo = np.array([p[1] for p in pairs])
def spear(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])
A(f"  역립% vs 바닥  Spearman rho = {spear(iv,fo):.3f}  (n={len(pairs)}, correct 우선·없으면 self)")
m2 = [p for p in pairs if p[0] > 2]
A(f"  climb(역립 0.8%, 바닥 7.7) 제외 시 rho = {spear(np.array([p[0] for p in m2]),np.array([p[1] for p in m2])):.3f}")
A("")
A("표 4 — 같은 videoKey 재분석의 각도행렬 재현성 (시간축 통제, 순수 추출 재현성)")
rr = json.load(open(f"{H.D}/out/a_rerun.json"))
A(f"{'videoKey':46s}{'n':>4s}{'median|Δ|':>11s}{'p90':>8s}")
for r in rr:
    A(f"{r['vk'][:45]:46s}{r['n']:4d}{r['pair_med']:11.2f}{r['pair_p90']:8.2f}")
A("")
A("표 5 — 소비처 (코드로 이은 사슬) + 실제 overallScore")
A("  per_joint_deviation → md['angle_vs_reference__{jk}'] (app.py:2861)")
A("  → ipsf_criteria._REFERENCE_RELATIVE_CRITERIA tolerance=20.0 (ipsf_criteria.py:158)")
A("  → deduction_engine: over = max(0, dev - 20)  (deduction_engine.py:623) → tally → overallScore")
A(f"{'동작':24s}{'label':8s}{'n':>4s}{'편차':>7s}{'20°초과 관절수':>14s}{'초과합(도)':>11s}{'overall중앙':>12s}")
fb = collections.defaultdict(list)
for f in facts:
    if f["label"] in ("correct", "fault", "self"):
        fb[(f["ref"], f["label"])].append(f)
for (ref, lab), rows in sorted(fb.items()):
    dv = np.asarray([r["dev"] for r in rows], dtype=float)
    ov = [r["overall"] for r in rows if r["overall"] is not None]
    A(f"{ref:24s}{lab:8s}{len(rows):4d}{np.median([r['scalar'] for r in rows]):7.1f}"
      f"{np.median((dv>20).sum(axis=1)):14.1f}{np.median(np.maximum(0,dv-20).sum(axis=1)):11.1f}"
      f"{(np.median(ov) if ov else float('nan')):12.1f}")
txt = "\n".join(L)
open(f"{H.D}/out/a_summary.txt", "w").write(txt + "\n")
print(txt)
