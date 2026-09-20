"""조사 F 집계 — 동작 × correct/fault 최종점수표 + 캡 도달 + 라이브 overall 대조."""
import sys, json, collections
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import numpy as np
rows = json.load(open(f"{D}/out/F_finals.json"))


def med(v):
    v = [x for x in v if x is not None]
    return float(np.median(v)) if v else float("nan")


for pm in ("ref", "none"):
    R = [r for r in rows if r["profile_mode"] == pm]
    g = collections.defaultdict(list)
    for r in R:
        g[(r["ref"], r["label"])].append(r)
    print("=" * 120)
    print(f"[profile={pm}]  운영 builder md → deduction_engine.tally → breakdown.final")
    print(f"{'동작':24s}{'라벨':8s}{'n':>4s}{'편차':>7s}{'축키':>5s}"
          f"{'final':>7s}{'execRaw':>9s}{'execCap':>9s}{'rec':>4s}{'sup':>4s}"
          f"{'축단독':>7s}{'억제off':>8s}{'quantN':>8s}{'라이브':>7s}")
    for k in sorted(g):
        v = g[k]
        lo = [x["overall"] for x in v if x["overall"] is not None]
        print(f"{k[0]:24s}{k[1]:8s}{len(v):4d}"
              f"{med([x['scalar'] for x in v]):7.1f}"
              f"{med([x['n_axis_keys'] for x in v]):5.0f}"
              f"{med([x['qa_final'] for x in v]):7.0f}"
              f"{med([x['qa_exec_raw'] for x in v]):9.1f}"
              f"{med([x['qa_exec_capped'] for x in v]):9.1f}"
              f"{med([x['qa_n_records'] for x in v]):4.0f}"
              f"{med([x['qa_n_suppressed'] for x in v]):4.0f}"
              f"{med([x['qa_axis_final'] for x in v]):7.0f}"
              f"{med([x['qa_nosupp_final'] for x in v]):8.0f}"
              f"{med([x['qn_final'] for x in v]):8.0f}"
              f"{(med(lo) if lo else float('nan')):7.1f}")
    print()

print("=" * 120)
for pm in ("ref", "none"):
    R = [r for r in rows if r["profile_mode"] == pm]
    fl = [r["qa_final"] for r in R]
    er = [abs(r["qa_exec_raw"]) for r in R if r["qa_exec_raw"] is not None]
    print(f"[profile={pm}] final n={len(fl)}  =100: {sum(1 for x in fl if x==100)} "
          f"({100*sum(1 for x in fl if x==100)/len(fl):.0f}%)  "
          f"=60(실행캡 바닥): {sum(1 for x in fl if x==60)} "
          f"({100*sum(1 for x in fl if x==60)/len(fl):.0f}%)  "
          f"=25(scoreFloor): {sum(1 for x in fl if x==25)}")
    print(f"   |execRaw| median={med(er):.1f} p90={np.percentile(er,90):.1f} max={max(er):.1f}"
          f"  >=40(집계캡 히트) {sum(1 for x in er if x>=40)}/{len(er)} "
          f"({100*sum(1 for x in er if x>=40)/len(er):.0f}%)")
print()

# 감점을 낸 criterion 종류
print("=" * 120)
R = [r for r in rows if r["profile_mode"] == "ref"]
c = collections.Counter()
for r in R:
    for x in r["qa_crit"]:
        c[x.split("__")[0]] += 1
print("record criterion 분포(profile=ref):", dict(c))
print("축 키만 md 에 있는 분석 비율:",
      f"{sum(1 for r in R if all(k.startswith('angle_vs_reference__') for k in r['md_keys']))}/{len(R)}")
print()

# 라이브 overall 대조
print("=" * 120)
R = [r for r in rows if r["profile_mode"] == "ref" and r["overall"] is not None]
d = [r["overall"] - r["qa_final"] for r in R]
print(f"라이브 overall 보유 {len(R)}건 · 라이브 − 내계산(qa): median {med(d):+.1f} "
      f"평균 {np.mean(d):+.1f}  |Δ|<0.5 일치 {sum(1 for x in d if abs(x)<0.5)}건 "
      f"({100*sum(1 for x in d if abs(x)<0.5)/len(d):.0f}%)")
g = collections.defaultdict(list)
for r in R:
    g[(r["ref"], r["label"])].append(r)
print(f"{'동작':24s}{'라벨':8s}{'n':>4s}{'라이브med':>10s}{'라이브고유값':>34s}{'내계산med':>10s}")
for k in sorted(g):
    v = g[k]
    lo = [x["overall"] for x in v]
    print(f"{k[0]:24s}{k[1]:8s}{len(v):4d}{med(lo):10.1f}"
          f"{str(sorted(set(lo))[:6]):>34s}{med([x['qa_final'] for x in v]):10.1f}")
