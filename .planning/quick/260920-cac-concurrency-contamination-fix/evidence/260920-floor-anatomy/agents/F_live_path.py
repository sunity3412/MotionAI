"""조사 F — 라이브 doc 이 어느 채점 경로를 탔는지 역추적.

dimension_overall = dimensions.overall_from_dimensions(result.dimensionScores)
  · 폴백 경로(measured_deviations=None 또는 활성 criterion 0 + quant 불가):
      final == max(SCORE_FLOOR, round(dimension_overall))
  · 2트랙 경로: final == max(25, round(100 - min(40, Σ감점)))  → 감점 0 이면 100
라이브 overallScore 와 대조해 분류한다. (deductionBreakdown 자체는 로컬에 없다 — 이 분류는
간접 증거다.)
"""
import sys, json, collections
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
import numpy as np
from sunity_shared.analysis import dimensions, deduction_engine

rows = [r for r in json.load(open(f"{D}/out/F_finals.json")) if r["profile_mode"] == "ref"]
st = {s["id"]: s for s in json.load(open(f"{D}/students.json"))}
FLOOR = deduction_engine.SCORE_FLOOR

cls = collections.Counter()
per = collections.defaultdict(collections.Counter)
det = []
for r in rows:
    dims = st[r["id"]].get("dims") or {}
    if not dims or r["overall"] is None:
        cls["dims/overall 없음"] += 1
        continue
    dim_overall = dimensions.overall_from_dimensions(dims)
    fb = int(max(FLOOR, round(dim_overall)))
    live = r["overall"]
    if live == fb and live != 100:
        k = "폴백 서명 (final == max(25, dimension_overall))"
    elif live == 100:
        k = "감점 0 (final==100)"
    else:
        k = "감점 발생 (2트랙)"
    cls[k] += 1
    per[r["ref"]][k] += 1
    det.append((r["id"], r["ref"], r["label"], live, fb, dim_overall, r["qa_final"], k))

print("라이브 698건 채점 경로 역추적:")
for k, v in cls.most_common():
    print(f"   {k:46s}{v:5d}  ({100*v/len(rows):.0f}%)")
print()
for m in sorted(per):
    print(f"   {m:24s}{dict(per[m])}")

# 감점이 발생한 건에서 내 축 재구성이 그 감점을 얼마나 설명하나
d2 = [x for x in det if x[7] == "감점 발생 (2트랙)"]
if d2:
    live = np.array([x[3] for x in d2], float)
    mine = np.array([x[6] for x in d2], float)
    print(f"\n감점 발생 {len(d2)}건: 라이브 overall vs 내 축-단독 재구성 "
          f"r={np.corrcoef(live, mine)[0,1]:+.3f}  "
          f"라이브 median {np.median(live):.0f} / 내 재구성 median {np.median(mine):.0f}")
    print(f"   라이브가 내 재구성보다 낮은 건 {sum(1 for a,b in zip(live,mine) if a<b)}건 "
          f"(= 이 축 밖의 감점이 더 있었다)")
json.dump([{k: v for k, v in zip(
    ("id","ref","label","live","fallback_pred","dim_overall","my_axis_final","class"), x)}
    for x in det], open(f"{D}/out/F_live_path.json", "w"))
print("\n저장:", f"{D}/out/F_live_path.json")
