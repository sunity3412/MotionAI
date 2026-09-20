"""조사 F 세부 — 캡 도달 per-group, profile 영향, 라이브 mode, 상관."""
import sys, json, collections
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import numpy as np
rows = json.load(open(f"{D}/out/F_finals.json"))
scan = {r["_id"]: r for r in json.load(open(f"{D}/scan.json"))}

ref_rows = [r for r in rows if r["profile_mode"] == "ref"]
none_rows = {r["id"]: r for r in rows if r["profile_mode"] == "none"}

# 1. profile 유무가 final 을 바꾸나
diff = [(r["id"], r["qa_final"], none_rows[r["id"]]["qa_final"])
        for r in ref_rows if r["qa_final"] != none_rows[r["id"]]["qa_final"]]
print(f"1) profile(ref) vs profile(None) final 불일치: {len(diff)}/{len(ref_rows)}건")
for x in diff[:8]:
    print("   ", x)

# 2. 축 단독 md vs 전체 md
d2 = [r for r in ref_rows if r["qa_final"] != r["qa_axis_final"]]
print(f"2) md 전체 vs angle_vs_reference 만: final 불일치 {len(d2)}/{len(ref_rows)}건"
      "  → 불일치 0 이면 화면 감점 전량이 이 축에서 나온 것")

# 3. 캡/바닥 per-group
print("\n3) per-group 캡 도달 (profile=ref, quant 가용)")
g = collections.defaultdict(list)
for r in ref_rows:
    g[(r["ref"], r["label"])].append(r)
print(f"{'동작':24s}{'라벨':8s}{'n':>4s}{'final=100':>10s}{'final=60(캡)':>13s}"
      f"{'execRaw med':>12s}{'execRaw max':>12s}{'final med':>10s}{'final min':>10s}{'final max':>10s}")
for k in sorted(g):
    v = g[k]
    f100 = sum(1 for x in v if x["qa_final"] == 100)
    f60 = sum(1 for x in v if x["qa_final"] == 60)
    er = [abs(x["qa_exec_raw"]) for x in v if x["qa_exec_raw"] is not None]
    fl = [x["qa_final"] for x in v]
    print(f"{k[0]:24s}{k[1]:8s}{len(v):4d}{f100:10d}{f60:13d}"
          f"{np.median(er):12.1f}{max(er):12.1f}{np.median(fl):10.0f}{min(fl):10d}{max(fl):10d}")

# 4. correct/fault 분리 — 점수로
print("\n4) 화면 점수 분리 (correct median − fault median, +면 정상 방향)")
for m in sorted({r["ref"] for r in ref_rows}):
    c = [x["qa_final"] for x in ref_rows if x["ref"] == m and x["label"] == "correct"]
    f = [x["qa_final"] for x in ref_rows if x["ref"] == m and x["label"] == "fault"]
    if not c or not f:
        continue
    sc = [x["scalar"] for x in ref_rows if x["ref"] == m and x["label"] == "correct"]
    sf = [x["scalar"] for x in ref_rows if x["ref"] == m and x["label"] == "fault"]
    # 겹침: correct 최저 vs fault 최고
    ov = sum(1 for a in c for b in f if a <= b) / (len(c) * len(f))
    print(f"   {m:24s} 편차 {np.median(sc):5.1f}→{np.median(sf):5.1f} (x{np.median(sf)/np.median(sc):4.2f})"
          f"   점수 {np.median(c):5.0f}→{np.median(f):5.0f} (Δ{np.median(c)-np.median(f):+5.0f})"
          f"   correct<=fault 쌍비율 {ov:5.1%}")

# 5. 라이브 mode
print("\n5) 라이브 doc 의 mode 분포 (이 698건)")
cm = collections.Counter(scan.get(r["id"], {}).get("mode") for r in ref_rows)
print("   ", dict(cm))
byref = collections.defaultdict(collections.Counter)
for r in ref_rows:
    byref[r["ref"]][scan.get(r["id"], {}).get("mode")] += 1
for m in sorted(byref):
    print(f"   {m:24s}{dict(byref[m])}")

# 6. 라이브 overall 과 내 계산의 상관
lo = np.array([r["overall"] for r in ref_rows if r["overall"] is not None], float)
mi = np.array([r["qa_final"] for r in ref_rows if r["overall"] is not None], float)
print(f"\n6) 라이브 overall vs 내 계산 qa_final: r={np.corrcoef(lo, mi)[0,1]:+.3f} n={len(lo)}")
sc = np.array([r["scalar"] for r in ref_rows if r["overall"] is not None], float)
print(f"   라이브 overall vs 편차 스칼라: r={np.corrcoef(lo, sc)[0,1]:+.3f}")
print(f"   내 계산 qa_final vs 편차 스칼라: r={np.corrcoef(mi, sc)[0,1]:+.3f}")

# 7. 편차 스칼라 → 점수 전이함수 (구간별)
print("\n7) 편차 스칼라 구간 → 내 계산 final (전이함수)")
bins = [0, 5, 10, 15, 20, 25, 30, 100]
for a, b in zip(bins, bins[1:]):
    v = [r["qa_final"] for r in ref_rows if a <= r["scalar"] < b]
    if v:
        print(f"   편차 [{a:3d},{b:3d}) n={len(v):4d}  final median={np.median(v):5.0f} "
              f"min={min(v)} max={max(v)}  =100 비율 {sum(1 for x in v if x==100)/len(v):5.1%}")
