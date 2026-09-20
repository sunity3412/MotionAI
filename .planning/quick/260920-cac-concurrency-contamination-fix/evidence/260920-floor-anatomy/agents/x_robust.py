"""반증 X2/X3 — (X2) n=11 상관의 leave-one-out 견고성, (X3) 내용-대조군 백분위.

X2: '각도 분포 폭이 바닥 크기를 정한다(r=+0.77)' 가 한두 점에 업혀 있나.
X3: 시간-셔플 chance 대신 **내용 대조군**(다른 동작을 시간순 그대로) 기준으로
    pdshape/elbow-twist 의 correct 바닥이 어디 앉는가.
"""
from __future__ import annotations
import json, sys, itertools, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)

stats = json.load(open(f"{D}/out/b_c5_stats.json"))
ana = json.load(open(f"{D}/out/b_c5_analysis.json"))
cc = json.load(open(f"{D}/out/b_c5_crosschance.json"))
xm = json.load(open(f"{D}/out/x_crossmotion.json"))

def pearson(a, b):
    return float(np.corrcoef(np.asarray(a, float), np.asarray(b, float))[0, 1])
def spearman(a, b):
    r = lambda v: np.argsort(np.argsort(np.asarray(v, float))).astype(float)
    return float(np.corrcoef(r(a), r(b))[0, 1])

M = {m["m"]: m for m in ana["motion"]}
mids = sorted(M)

print("=== X2 leave-one-out: rng ~ 바닥 (n=11) ===")
Y = [M[m]["floor"] for m in mids]
X = [stats[m]["agg"]["rng"] for m in mids]
base_p, base_s = pearson(X, Y), spearman(X, Y)
print(f"  전체     pearson={base_p:+.3f} spearman={base_s:+.3f}")
worst = None
for i, m in enumerate(mids):
    xs = [X[j] for j in range(len(mids)) if j != i]
    ys = [Y[j] for j in range(len(mids)) if j != i]
    p, s = pearson(xs, ys), spearman(xs, ys)
    print(f"  -{m:24s} pearson={p:+.3f} spearman={s:+.3f}")
    if worst is None or p < worst[1]:
        worst = (m, p, s)
print(f"  최악 LOO: {worst[0]} pearson={worst[1]:+.3f} spearman={worst[2]:+.3f}")

print("\n=== X2b correct 바닥만 (n=7) leave-one-out: sd ~ 바닥 ===")
cm = [m for m in mids if M[m]["kind"] == "correct"]
Y2 = [M[m]["floor"] for m in cm]
X2 = [stats[m]["agg"]["sd"] for m in cm]
print(f"  전체 n={len(cm)} pearson={pearson(X2,Y2):+.3f} spearman={spearman(X2,Y2):+.3f}")
for i, m in enumerate(cm):
    xs = [X2[j] for j in range(len(cm)) if j != i]
    ys = [Y2[j] for j in range(len(cm)) if j != i]
    print(f"  -{m:24s} pearson={pearson(xs,ys):+.3f} spearman={spearman(xs,ys):+.3f}")

print("\n=== X2c 바닥 정의 혼합(correct 7 + self 4) 확인 — self 만 빼면? ===")
print(f"  correct 만 n=7  rng: pearson={pearson([stats[m]['agg']['rng'] for m in cm],Y2):+.3f} "
      f"spearman={spearman([stats[m]['agg']['rng'] for m in cm],Y2):+.3f}")
sm = [m for m in mids if M[m]["kind"] == "self"]
Y3 = [M[m]["floor"] for m in sm]
print(f"  self 만    n={len(sm)}  rng: pearson={pearson([stats[m]['agg']['rng'] for m in sm],Y3):+.3f}")

print("\n=== X2d 바닥/sd 비율 (스케일 제거 후 남는 것) ===")
for m in mids:
    print(f"  {m:24s} kind={M[m]['kind']:7s} floor={M[m]['floor']:6.2f} "
          f"sd={stats[m]['agg']['sd']:6.2f} floor/sd={M[m]['floor']/stats[m]['agg']['sd']:.3f} "
          f"ratio(=floor/chance)={M[m]['ratio']:.3f}")
v = [M[m]["floor"] / stats[m]["agg"]["sd"] for m in mids]
print(f"  floor/sd  범위 {min(v):.3f}~{max(v):.3f} (배수 {max(v)/min(v):.1f}x)")

print("\n=== X3 내용 대조군(다른 동작, 시간순) 기준 백분위 ===")
by = collections.defaultdict(list)
for r in xm:
    if not r["same"]:
        by[r["ref"]].append(r["ratio"])
# 그룹 실측 ratio (crosschance 전수 중앙값)
g = collections.defaultdict(list)
for r in cc:
    g[(r["ref"], r["label"])].append(r["real"] / r["chance"] if r["chance"] else np.nan)
print(f"{'motion':24s} {'label':8s} {'그룹 ratio':>10s} {'내용대조 med':>12s} "
      f"{'내용대조 min':>12s} {'대조군 중 더 낮은 비율':>22s}")
for mid in sorted(by):
    for lab in ("correct", "self", "fault"):
        rs = g.get((mid, lab))
        if not rs:
            continue
        gr = float(np.median(rs))
        d = np.array(by[mid], float)
        pct = 100.0 * float(np.mean(d < gr))
        print(f"{mid:24s} {lab:8s} {gr:10.3f} {np.median(d):12.3f} {d.min():12.3f} {pct:19.0f}%")
