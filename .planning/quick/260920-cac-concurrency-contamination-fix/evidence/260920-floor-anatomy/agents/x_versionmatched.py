"""반증 X5 — 조사 B 의 '바닥' 은 기준 doc **버전 불일치** 산물이다.

사실: 875건 학생 추출은 2026-06-17~09-06 이고, 그때 활성 기준은 phase4_v1 이다.
      `H.load_references()` 가 주는 live doc 은 **rot180_v1**(2026-09-17 뒤집기 후)이며
      11/11 전부 live == rot180_v1 이다(ref_versions.json 대조).
      즉 조사 B 는 rot180 **전** 학생을 rot180 **후** 기준에 댔다.

여기서 같은 운영 함수로 두 판을 나란히 낸다 — matched(phase4_v1) vs live(rot180_v1).
동작별 바닥 / chance / 비율 / C5 상관 전부 재계산.
"""
from __future__ import annotations
import json, sys, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

live = H.load_references()
vers = json.load(open(f"{D}/ref_versions.json"))
facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
stats_live = json.load(open(f"{D}/out/b_c5_stats.json"))
VER = {"ref-climb": "quick-260816-r7k"}   # climb 만 phase4_v1 프레임수가 다름(version_vs_score 선례)


def ver_doc(m):
    v = dict(vers[m].get(VER.get(m, "phase4_v1")) or {})
    if not v.get("angles"):
        return None
    for k in ("anglesJointKeys", "clipRange", "baseUntilS", "sharedBaseMotionId",
              "keypointReport", "anglesRealFps", "anglesFrames"):
        v.setdefault(k, live[m].get(k))
    return v


def angle_stats(M):
    per = {}
    for j, jk in enumerate(H.JOINT_KEYS):
        col = M[:, j][np.isfinite(M[:, j])]
        per[jk] = dict(sd=float(col.std(ddof=0)), rng=float(col.max() - col.min()),
                       iqr=float(np.percentile(col, 75) - np.percentile(col, 25)),
                       d180=float(np.median(180.0 - col)))
    return {k: float(np.median([per[jk][k] for jk in H.JOINT_KEYS]))
            for k in ("sd", "rng", "iqr", "d180")}, per


# 동작·라벨별 고유 학생(각도 해시 기준) 최대 6명
bykey = collections.defaultdict(list)
for f in facts:
    bykey[(f["ref"], f["label"])].append(f)
import hashlib
def uniq_students(mid, lab, cap=6):
    seen, keep = set(), []
    for f in sorted(bykey.get((mid, lab), []), key=lambda x: x["id"]):
        s = students.get(f["id"])
        if s is None:
            continue
        h = hashlib.md5(np.asarray(s["angles"], float).tobytes()).hexdigest()
        if h in seen:
            continue
        seen.add(h); keep.append(s)
        if len(keep) >= cap:
            break
    return keep


def floor_of(mid, rdoc, lab, cap=6):
    ss = uniq_students(mid, lab, cap)
    if not ss:
        return None, None, 0
    reals, chs = [], []
    for s in ss:
        M = H.student_matrix(s)
        dev, _ = H.deviate(M, rdoc)
        reals.append(H.scalar(dev))
        c = []
        for k in range(2):
            rng = np.random.default_rng(7000 + k)
            d2, _ = H.deviate(M[rng.permutation(M.shape[0])], rdoc)
            c.append(H.scalar(d2))
        chs.append(float(np.median(c)))
    return float(np.median(reals)), float(np.median(chs)), len(ss)


rows = []
print(f"{'motion':24s} {'kind':8s} | {'matched 바닥':>12s} {'live 바닥':>10s} {'차이%':>7s} | "
      f"{'m ratio':>8s} {'l ratio':>8s}")
for mid in sorted(live):
    vd = ver_doc(mid)
    if vd is None:
        print(f"{mid:24s} -- matched version 없음"); continue
    kind = "correct" if bykey.get((mid, "correct")) else "self"
    fm, cm, nm = floor_of(mid, vd, kind)
    fl, cl, nl = floor_of(mid, live[mid], kind)
    if fm is None or fl is None:
        continue
    ag_m, per_m = angle_stats(H.ref_matrix(vd))
    rows.append(dict(m=mid, kind=kind, n=nm, floor_m=fm, chance_m=cm, ratio_m=fm / cm,
                     floor_l=fl, chance_l=cl, ratio_l=fl / cl, **{f"m_{k}": v for k, v in ag_m.items()},
                     l_sd=stats_live[mid]["agg"]["sd"], l_rng=stats_live[mid]["agg"]["rng"],
                     l_iqr=stats_live[mid]["agg"]["iqr"], l_d180=stats_live[mid]["agg"]["dist180_median"]))
    print(f"{mid:24s} {kind:8s} | {fm:12.2f} {fl:10.2f} {100*(fl-fm)/fm:6.0f}% | "
          f"{fm/cm:8.3f} {fl/cl:8.3f}")

json.dump(rows, open(f"{D}/out/x_versionmatched.json", "w"), indent=1)

def pearson(a, b): return float(np.corrcoef(np.asarray(a,float), np.asarray(b,float))[0,1])
def spearman(a, b):
    r = lambda v: np.argsort(np.argsort(np.asarray(v, float))).astype(float)
    return float(np.corrcoef(r(a), r(b))[0, 1])

print("\n=== C5 상관 재계산 (n=%d) ===" % len(rows))
print(f"{'feature':10s} {'live(조사B가 쓴 판)':>22s} {'version-matched':>18s}")
for f in ("sd", "rng", "iqr", "d180"):
    Xl = [r[f"l_{f}"] for r in rows]; Yl = [r["floor_l"] for r in rows]
    Xm = [r[f"m_{f}"] for r in rows]; Ym = [r["floor_m"] for r in rows]
    print(f"{f:10s} p={pearson(Xl,Yl):+.3f} s={spearman(Xl,Yl):+.3f}   "
          f"p={pearson(Xm,Ym):+.3f} s={spearman(Xm,Ym):+.3f}")

print("\n=== tol 20도 대비 — 이 축이 감점을 내는가 ===")
print(f"{'motion':24s} {'matched 바닥':>12s} {'>20?':>5s} | {'live 바닥':>10s} {'>20?':>5s}")
for r in rows:
    print(f"{r['m']:24s} {r['floor_m']:12.2f} {str(r['floor_m']>20):>5s} | "
          f"{r['floor_l']:10.2f} {str(r['floor_l']>20):>5s}")
