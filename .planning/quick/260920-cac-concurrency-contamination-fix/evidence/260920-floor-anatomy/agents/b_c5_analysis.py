"""조사 B 최종 분석 — C5(각도 범위/천장) 가설 판정.

(1) 동작별 바닥 ~ 각도 통계 예측력 (문턱 선택 0)
(2) 바닥/chance 비율 ~ 각도 통계 (= raw 바닥에서 스케일을 뺀 잔차에도 설명력이 있나)
(3) 관절 단위 검정 (11동작 x 8관절) — 그 관절의 분포 폭이 그 관절의 바닥을 예측하나
(4) lag 등가 — 바닥이 '몇 프레임 어긋남'에 해당하나
(5) 180도 천장 — 직접 검정
"""
from __future__ import annotations
import json, sys, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

stats = json.load(open(f"{D}/out/b_c5_stats.json"))
cc = json.load(open(f"{D}/out/b_c5_crosschance.json"))
JK = H.JOINT_KEYS

def pearson(a, b):
    return float(np.corrcoef(np.asarray(a, float), np.asarray(b, float))[0, 1])
def spearman(a, b):
    r = lambda v: np.argsort(np.argsort(np.asarray(v, float))).astype(float)
    return float(np.corrcoef(r(a), r(b))[0, 1])

g = collections.defaultdict(list)
for r in cc:
    g[(r["ref"], r["label"])].append(r)

# 동작별 '바닥' = correct 우선, 없으면 self
floor, floor_kind, floor_dev, chance, chance_dev = {}, {}, {}, {}, {}
for mid in stats:
    for lab in ("correct", "self"):
        rs = g.get((mid, lab))
        if rs:
            floor[mid] = float(np.median([r["real"] for r in rs]))
            floor_kind[mid] = lab
            floor_dev[mid] = np.median(np.vstack([r["dev"] for r in rs]), axis=0)
            chance[mid] = float(np.median([r["chance"] for r in rs]))
            break
mids = sorted(floor)

print("=== (1)(2) 동작 단위 (n=%d) ===" % len(mids))
feats = ("sd", "rng", "iqr", "dist180_median", "frame_dabs_median")
Y = [floor[m] for m in mids]
R = [floor[m] / chance[m] for m in mids]
print(f"{'feature':18s} {'~바닥 pear':>11s} {'spear':>7s} | {'~비율 pear':>11s} {'spear':>7s}")
for f in feats + ("chance_analytic_agg", "chance_shuffle"):
    if f == "chance_analytic_agg":
        X = [stats[m]["chance_analytic"] for m in mids]
    elif f == "chance_shuffle":
        X = [chance[m] for m in mids]
    else:
        X = [stats[m]["agg"][f] for m in mids]
    print(f"{f:18s} {pearson(X,Y):11.3f} {spearman(X,Y):7.3f} | {pearson(X,R):11.3f} {spearman(X,R):7.3f}")

print("\n동작별 바닥/chance (1.0 = 정보 0)")
print(f"{'motion':24s} {'kind':8s} {'floor':>7s} {'chance':>7s} {'ratio':>7s} {'sd':>7s} {'d180':>7s}")
for m in mids:
    print(f"{m:24s} {floor_kind[m]:8s} {floor[m]:7.2f} {chance[m]:7.2f} "
          f"{floor[m]/chance[m]:7.3f} {stats[m]['agg']['sd']:7.2f} {stats[m]['agg']['dist180_median']:7.2f}")

# ── (3) 관절 단위 (11 x 8 = 88) ────────────────────────────────────────────
print("\n=== (3) 관절 단위 검정 (n=%d) ===" % (len(mids) * 8))
rows = []
for m in mids:
    st = stats[m]
    for i, jk in enumerate(JK):
        rows.append(dict(m=m, jk=jk, dev=float(floor_dev[m][i]),
                         ch=st["chance_analytic_per_joint"][jk],
                         ch_sh=st["chance_shuffle_per_joint"][jk],
                         sd=st["per_joint"][jk]["sd"], rng=st["per_joint"][jk]["rng"],
                         iqr=st["per_joint"][jk]["iqr"],
                         d180=st["per_joint"][jk]["dist180_median"],
                         fd=st["per_joint"][jk]["frame_dabs_median"]))
Y = [r["dev"] for r in rows]
for f in ("sd", "rng", "iqr", "d180", "fd", "ch", "ch_sh"):
    X = [r[f] for r in rows]
    print(f"  {f:6s} pearson={pearson(X,Y):+.3f} spearman={spearman(X,Y):+.3f}")
# 동작 효과 제거(동작별 평균 차감) 후 = 순수 '관절 분포 폭' 효과
print("  -- 동작 효과 제거(동작별 중심화) --")
byM = collections.defaultdict(list)
for r in rows: byM[r["m"]].append(r)
cent = {}
for f in ("dev", "sd", "rng", "iqr", "d180", "fd", "ch"):
    v = []
    for m, rs in byM.items():
        a = np.array([r[f] for r in rs], float)
        v.extend(a - a.mean())
    cent[f] = v
for f in ("sd", "rng", "iqr", "d180", "fd", "ch"):
    print(f"  {f:6s} pearson={pearson(cent[f],cent['dev']):+.3f} spearman={spearman(cent[f],cent['dev']):+.3f}")

# ── (4) lag 등가 ───────────────────────────────────────────────────────────
print("\n=== (4) lag 등가 — 바닥이 '몇 프레임 시간 어긋남'에 해당하나 (fps~14.95) ===")
print(f"{'motion':24s} {'floor':>7s} {'lag1':>6s} {'lag3':>6s} {'lag8':>6s} {'lag20':>6s} {'lag50':>6s} {'chance':>7s} {'~equiv':>8s}")
for m in mids:
    lc = {int(k): v for k, v in stats[m]["lag_curve"].items()}
    ks = sorted(lc)
    eq = None
    for k in ks:
        if lc[k] >= floor[m]:
            eq = k; break
    if eq is None: eq = f">{ks[-1]}"
    row = " ".join(f"{lc.get(k, float('nan')):6.1f}" for k in (1, 3, 8, 20, 50))
    print(f"{m:24s} {floor[m]:7.2f} {row} {stats[m]['chance_analytic']:7.2f} {str(eq):>8s}")

# ── (5) 180도 천장 직접 검정 — 관절 단위 ───────────────────────────────────
print("\n=== (5) 180도 천장 가설 — 관절 단위 ===")
near = [r for r in rows if r["d180"] < 30]
far = [r for r in rows if r["d180"] >= 60]
print(f"  180 근처 관절(d180<30, n={len(near)}): 바닥 median={np.median([r['dev'] for r in near]):.2f}, "
      f"sd median={np.median([r['sd'] for r in near]):.2f}, chance={np.median([r['ch'] for r in near]):.2f}")
print(f"  180 먼  관절(d180>=60, n={len(far)}): 바닥 median={np.median([r['dev'] for r in far]):.2f}, "
      f"sd median={np.median([r['sd'] for r in far]):.2f}, chance={np.median([r['ch'] for r in far]):.2f}")
print(f"  두 집단 바닥/chance: near={np.median([r['dev']/r['ch'] for r in near]):.3f} "
      f"far={np.median([r['dev']/r['ch'] for r in far]):.3f}")

json.dump(dict(motion=[dict(m=m, kind=floor_kind[m], floor=floor[m], chance=chance[m],
                            ratio=floor[m] / chance[m]) for m in mids],
               joint=rows), open(f"{D}/out/b_c5_analysis.json", "w"), indent=1)
