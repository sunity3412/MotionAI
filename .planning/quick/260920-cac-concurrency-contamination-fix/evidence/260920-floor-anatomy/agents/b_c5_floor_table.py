"""조사 B — 동작별 바닥(실측) 재산출 + 통계·chance 와 나란히."""
from __future__ import annotations
import json, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

facts = json.load(open(f"{D}/facts.json"))
stats = json.load(open(f"{D}/out/b_c5_stats.json"))

g = {}
for f in facts:
    g.setdefault((f["ref"], f["label"]), []).append(f)

rows = []
for mid in sorted(stats):
    st = stats[mid]
    r = dict(motion=mid, T=st["frames"],
             sd=st["agg"]["sd"], rng=st["agg"]["rng"], iqr=st["agg"]["iqr"],
             d180=st["agg"]["dist180_median"], fd=st["agg"]["frame_dabs_median"],
             chance_an=st["chance_analytic"], chance_shuf=st["chance_shuffle_scalar_median"])
    for lab in ("correct", "fault", "self"):
        v = [x["scalar"] for x in g.get((mid, lab), []) if np.isfinite(x["scalar"])]
        r[lab] = float(np.median(v)) if v else None
        r[lab + "_n"] = len(v)
        r[lab + "_sd"] = float(np.std(v, ddof=0)) if v else None
        # 실제 쓰인 ref window (rstart,rend) 중앙값
        w = [(x["rstart"], x["rend"]) for x in g.get((mid, lab), []) if x.get("rend")]
        r[lab + "_win"] = (int(np.median([a for a, _ in w])), int(np.median([b for _, b in w]))) if w else None
    rows.append(r)

hdr = (f"{'motion':24s} {'T':>4s} {'corr':>6s} {'self':>6s} {'fault':>6s} | "
       f"{'chAn':>6s} {'chShuf':>6s} | {'c/chAn':>6s} {'c/chSh':>6s} {'s/chSh':>6s} | "
       f"{'sd':>6s} {'rng':>6s} {'iqr':>6s} {'d180':>6s} {'fd':>5s}")
print(hdr); print("-" * len(hdr))
for r in rows:
    def fm(x, w=6, p=2):
        return f"{x:{w}.{p}f}" if x is not None else " " * (w - 1) + "-"
    cra = r["correct"] / r["chance_an"] if r["correct"] else None
    crs = r["correct"] / r["chance_shuf"] if r["correct"] else None
    srs = r["self"] / r["chance_shuf"] if r["self"] else None
    print(f"{r['motion']:24s} {r['T']:4d} {fm(r['correct'])} {fm(r['self'])} {fm(r['fault'])} | "
          f"{fm(r['chance_an'])} {fm(r['chance_shuf'])} | {fm(cra)} {fm(crs)} {fm(srs)} | "
          f"{fm(r['sd'])} {fm(r['rng'])} {fm(r['iqr'])} {fm(r['d180'])} {fm(r['fd'],5)}")

json.dump(rows, open(f"{D}/out/b_c5_floor_table.json", "w"), indent=1)

# --- 상관 (문턱 안 고른다 — 예측력 유무만) ---------------------------------
def spearman(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])

def pearson(a, b):
    return float(np.corrcoef(np.asarray(a, float), np.asarray(b, float))[0, 1])

print("\n=== 예측력: 동작별 바닥 ~ 각도 통계 (n 작음, 문턱 선택 없음) ===")
for target in ("correct", "self"):
    sub = [r for r in rows if r[target] is not None]
    y = [r[target] for r in sub]
    print(f"\n[{target} 바닥] n={len(sub)} ({', '.join(r['motion'] for r in sub)})")
    for feat in ("sd", "rng", "iqr", "d180", "fd", "chance_an", "chance_shuf", "T"):
        x = [r[feat] for r in sub]
        print(f"  {feat:11s} pearson={pearson(x,y):+.3f}  spearman={spearman(x,y):+.3f}")

# correct+self 합쳐 11 동작 커버 (동작당 1 바닥: correct 있으면 correct, 없으면 self)
sub = []
for r in rows:
    v = r["correct"] if r["correct"] is not None else r["self"]
    if v is not None:
        sub.append((r, v))
print(f"\n[바닥 통합 (correct 우선, 없으면 self)] n={len(sub)}")
y = [v for _, v in sub]
for feat in ("sd", "rng", "iqr", "d180", "fd", "chance_an", "chance_shuf", "T"):
    x = [r[feat] for r, _ in sub]
    print(f"  {feat:11s} pearson={pearson(x,y):+.3f}  spearman={spearman(x,y):+.3f}")
