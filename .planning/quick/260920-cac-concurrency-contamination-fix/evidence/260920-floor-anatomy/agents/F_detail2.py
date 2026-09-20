"""조사 F 세부 2 — 데드존/캡 반사실, 라이브 재현성, ref window 동일성."""
import sys, json, collections
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import numpy as np
rows = [r for r in json.load(open(f"{D}/out/F_finals.json")) if r["profile_mode"] == "ref"]

# A. builder 가 쓰는 reference_angles(전체 a_ref) == 점수경로 window 인가
mis = [r for r in rows if not (r["ref_start"] == 0 and r["ref_end"] == r["a_ref_T"])]
print(f"A) builder 는 전체 a_ref 를, _deviation_against 는 a_ref[ref_start:ref_end] 를 쓴다.")
print(f"   이 코퍼스에서 두 창이 다른 분석: {len(mis)}/{len(rows)}건 "
      f"(ref_start 전부 0, ref_end==a_ref_T)")

# B. tol 20도를 넘는 관절 수 = 실제 감점 seed 수
print("\nB) tol 20도 초과 관절 수 (= 화면 감점 record 를 만든 관절 수)")
g = collections.defaultdict(list)
for r in rows:
    over = sum(1 for k, v in r["md"].items() if k.startswith("angle_vs_reference__") and v > 20.0)
    r["_over"] = over
    g[(r["ref"], r["label"])].append(r)
print(f"{'동작':24s}{'라벨':8s}{'n':>4s}{'초과관절 med':>12s}{'초과0건 비율':>13s}"
      f"{'최대편차관절 med':>16s}")
for k in sorted(g):
    v = g[k]
    ov = [x["_over"] for x in v]
    mx = [max([d for kk, d in x["md"].items() if kk.startswith("angle_vs_reference__")] or [0])
          for x in v]
    print(f"{k[0]:24s}{k[1]:8s}{len(v):4d}{np.median(ov):12.0f}"
          f"{sum(1 for x in ov if x==0)/len(ov):13.1%}{np.median(mx):16.1f}")

# C. 실행캡(-40) 반사실 — 캡이 없었다면
print("\nC) 실행 집계캡 -40 반사실 (캡 없으면 final = max(25, 100 - |execRaw|))")
for m in sorted({r["ref"] for r in rows}):
    for lab in ("correct", "fault"):
        v = [r for r in rows if r["ref"] == m and r["label"] == lab]
        if not v:
            continue
        er = [abs(r["qa_exec_raw"]) for r in v if r["qa_exec_raw"] is not None]
        fl = [r["qa_final"] for r in v]
        nocap = [max(25, round(100 - x)) for x in er]
        print(f"   {m:24s}{lab:8s} n={len(v):3d} 캡적용 {np.median(fl):5.0f}  "
              f"캡없음 {np.median(nocap):5.0f}")

# D. 같은 영상(videoKey) 재분석 안에서의 흔들림 — 라이브 vs 내 재구성
print("\nD) 같은 videoKey 재분석 내 표준편차 (n>=5 인 vk 만)")
byvk = collections.defaultdict(list)
for r in rows:
    byvk[r["vk"]].append(r)
print(f"{'videoKey':56s}{'n':>4s}{'내 final sd':>12s}{'라이브 overall sd':>18s}"
      f"{'라이브 범위':>16s}")
tot_mine, tot_live = [], []
for vk, v in sorted(byvk.items(), key=lambda kv: -len(kv[1])):
    vk = vk or "(videoKey 없음)"
    if len(v) < 5:
        continue
    mine = np.std([x["qa_final"] for x in v], ddof=0)
    lo = [x["overall"] for x in v if x["overall"] is not None]
    live = np.std(lo, ddof=0) if lo else float("nan")
    tot_mine.append(mine); tot_live.append(live)
    print(f"{vk[:56]:56s}{len(v):4d}{mine:12.2f}{live:18.2f}"
          f"{f'{min(lo):.0f}~{max(lo):.0f}':>16s}")
print(f"   {'중앙값':56s}{'':4s}{np.median(tot_mine):12.2f}{np.median(tot_live):18.2f}")

# E. 억제(measurement_error) 가 점수를 얼마나 살렸나
print("\nE) 측정불확실도 억제(suppressed) 의 점수 영향")
d = [(r["qa_nosupp_final"] - r["qa_final"]) for r in rows]
print(f"   억제 없었으면 final 이 median {np.median(d):+.1f}점 더 낮았다 "
      f"(0 아닌 건수 {sum(1 for x in d if x!=0)}/{len(d)}, 최대 {max(d)}점)")
