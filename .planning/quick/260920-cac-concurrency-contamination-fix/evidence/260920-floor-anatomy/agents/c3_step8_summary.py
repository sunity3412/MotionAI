"""C3 최종 — 동작별 바닥을 정렬이 설명하는 몫."""
import json, sys, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)

ctrl = {(r["ref"], r["label"], str(r["vk"])): r for r in json.load(open(f"{D}/out/c3_controls.json"))}
full = json.load(open(f"{D}/out/c3_full_oracle.json"))
rg = {(r["ref"], r["label"], str(r["vk"])): r for r in json.load(open(f"{D}/out/c3_regrid.json"))}

by = collections.defaultdict(list)
for r in full: by[(r["ref"], r["label"])].append(r)

# 각 동작의 '바닥' 행 = correct (없으면 self)
floors = []
for m in sorted({r["ref"] for r in full}):
    lb = "correct" if (m, "correct") in by else ("self" if (m, "self") in by else None)
    if lb is None: continue
    rs = by[(m, lb)]
    reps = [v for k, v in ctrl.items() if k[0] == m and k[1] == lb]
    rep = max(reps, key=lambda x: x["n_group"]) if reps else None
    rgr = [v for k, v in rg.items() if k[0] == m and k[1] == lb]
    rgr = max(rgr, key=lambda x: x["n_group"]) if rgr else None
    floors.append(dict(
        motion=m, label=lb, n=len(rs),
        dtw=float(np.median([x["dev_dtw"] for x in rs])),
        oracle=float(np.median([x["dev_oracle"] for x in rs])),
        ident=rep["dev_ident"] if rep else float("nan"),
        rev=rep["dev_dtw_rev"] if rep else float("nan"),
        shuf=rep["dev_shuf"] if rep else float("nan"),
        regrid=rgr["dev_regrid_dtw"] if rgr else float("nan"),
    ))

print("== C3 최종: 동작별 바닥을 정렬이 설명하는 몫 ==")
print("  바닥 = 실력차 0 조건(correct = 정은지 성공 테이크 / self = 기준 영상 그 자체)")
print()
print(f"{'동작':24s}{'라벨':7s}{'n':>4s}{'운영':>7s}{'oracle':>8s}{'정렬몫%':>9s}"
      f"{'ident':>7s}{'역순':>7s}{'무작위':>8s}{'재격자':>8s}{'시간화살표':>10s}")
for f in sorted(floors, key=lambda x: x["dtw"]):
    share = 100 * (f["dtw"] - f["oracle"]) / f["dtw"]
    arrow = f["rev"] / f["dtw"]
    print(f"{f['motion']:24s}{f['label']:7s}{f['n']:>4d}{f['dtw']:>7.1f}{f['oracle']:>8.1f}"
          f"{share:>9.0f}{f['ident']:>7.1f}{f['rev']:>7.1f}{f['shuf']:>8.1f}"
          f"{f['regrid']:>8.1f}{arrow:>10.2f}")
print()
print("  정렬몫% = (운영편차 - oracle편차)/운영편차. oracle = 단조제약 없이 8관절 L2 최소인")
print("            기준 프레임을 학생 프레임마다 자유 선택 → 어떤 시간왜곡도 이 아래 불가.")
print("  시간화살표 = 기준을 시간 역순으로 뒤집어 재정렬했을 때 편차 배수. 1.0 = 시간 방향 무의미.")
print()
sh = [100*(f['dtw']-f['oracle'])/f['dtw'] for f in floors]
ar = [f['rev']/f['dtw'] for f in floors]
print(f"  정렬몫 범위 = {min(sh):.0f}% ~ {max(sh):.0f}%  (즉 바닥의 {100-max(sh):.0f}~{100-min(sh):.0f}% 는 정렬로 못 지운다)")
print(f"  시간화살표 최저 = {min(ar):.2f} ({floors[int(np.argmin(ar))]['motion']})")

# 살아있는 4동작 vs 죽은 2동작
live = [f for f in floors if f["motion"] in ("ref-kip-up","ref-peter-pan","ref-power-spin","ref-climb")]
dead = [f for f in floors if f["motion"] in ("ref-pdshape","ref-elbow-twist-sister")]
print()
print("== 살아있는 4동작 vs 죽은 2동작 ==")
for nm, grp in (("살아있음(4)", live), ("죽음(2)", dead)):
    a = np.mean([100*(f['dtw']-f['oracle'])/f['dtw'] for f in grp])
    b = np.mean([f['rev']/f['dtw'] for f in grp])
    c = np.mean([f['oracle'] for f in grp])
    print(f"  {nm:12s} 정렬몫 평균 {a:4.0f}%   시간화살표 평균 {b:.2f}   oracle 바닥 평균 {c:5.1f}도")
