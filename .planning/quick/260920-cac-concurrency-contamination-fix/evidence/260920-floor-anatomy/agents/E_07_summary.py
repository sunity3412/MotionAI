"""E-7 — 조사 E 결과 통합표.

세 가지를 한 화면에 놓는다:
  (a) 동작별 바닥 (correct 있으면 correct, 없으면 self)
  (b) 시점 불일치 (fixture 4건만 — 학생 joints3d 보유 전부)
  (c) 경쟁 설명: 기준측 저신뢰 비율 / temporal_fill 보수량
"""
import json, sys, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D); sys.path.insert(0, f"{D}/out")
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
import harness as H
from sunity_shared.analysis import features


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b); a, b = a[ok], b[ok]
    ra = np.argsort(np.argsort(a)).astype(float); rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    return round(float((ra @ rb) / np.sqrt((ra @ ra) * (rb @ rb))), 3), int(a.size)


refs = H.load_references()
facts = json.load(open(f"{D}/facts.json"))
byref = collections.defaultdict(lambda: collections.defaultdict(list))
for r in facts:
    byref[r["ref"]][r["label"]].append(r["scalar"])
vm = {r["motion"]: r for r in json.load(open(f"{D}/out/E_04_share.json"))}
pairs = {r["motion"]: r for r in json.load(open(f"{D}/out/E_02_matched_pairs.json"))}

rows = []
for m, r in sorted(refs.items()):
    nk = len(r["joints3dKeys"])
    kp = np.asarray(r["joints3d"], float).reshape(-1, nk, 3)
    raw = features.compute_joint_angles(kp)
    stored = H.ref_matrix(r)
    d = np.abs(raw - stored); d = d[np.isfinite(d)]
    repair = float(np.median(d))                    # temporal_fill 이 실제로 옮긴 양
    conf = np.asarray(r["keypointReport"]["confidence"], float)
    co, se = byref[m]["correct"], byref[m]["self"]
    floor = float(np.median(co)) if co else (float(np.median(se)) if se else float("nan"))
    rows.append(dict(motion=m, floor=floor, src="correct" if co else ("self" if se else "-"),
                     low_conf=float((conf < 0.5).mean()), repair=repair,
                     view_mm=vm[m]["d_max"] if m in vm else None,
                     view_cap=vm[m]["sim_cap"] if m in vm else None,
                     sw_sys=pairs[m]["sw_torso_sysdex"] if m in pairs else None))

print(f"{'motion':24s}{'바닥°':>7s}{'출처':>8s}{'저신뢰%':>9s}{'fill보수°':>10s}"
      f"{'시점δ상한°':>12s}{'시점설명가능°':>14s}{'sw계통%':>9s}")
for x in sorted(rows, key=lambda z: z["floor"]):
    vmm = f"{x['view_mm']:12.1f}" if x["view_mm"] is not None else f"{'-':>12s}"
    vcp = f"{x['view_cap']:14.2f}" if x["view_cap"] is not None else f"{'-':>14s}"
    sws = f"{(np.exp(x['sw_sys'])-1)*100:8.1f}%" if x["sw_sys"] is not None else f"{'-':>9s}"
    print(f"{x['motion']:24s}{x['floor']:7.1f}{x['src']:>8s}{x['low_conf']:9.1%}{x['repair']:10.2f}{vmm}{vcp}{sws}")

fl = [x["floor"] for x in rows]
print()
print("=== 순서 예측력 (Spearman) ===")
print("  저신뢰 프레임비율 → 바닥      n=11:", spearman([x["low_conf"] for x in rows], fl))
print("  temporal_fill 보수량 → 바닥   n=11:", spearman([x["repair"] for x in rows], fl))
sub = [x for x in rows if x["view_mm"] is not None]
print("  시점 불일치 δ상한 → 바닥      n=4 :", spearman([x["view_mm"] for x in sub], [x["floor"] for x in sub]))
print("  시점 불일치 δ상한 → fixture dev n=4 :",
      spearman([x["view_mm"] for x in sub], [pairs[x["motion"]]["dev"] for x in sub]))
print("  |sw 계통 불일치| → fixture dev n=4 :",
      spearman([abs(pairs[x["motion"]]["sw_torso_sysdex"]) for x in sub],
               [pairs[x["motion"]]["dev"] for x in sub]))
print("  짝쌍 산포(sw IQR) → fixture dev n=4 :",
      spearman([pairs[x["motion"]]["sw_torso_iqr"] for x in sub],
               [pairs[x["motion"]]["dev"] for x in sub]))
print()
print("=== 기준 11편 자체의 시점 기술자 분산 (기술자가 자세에 오염된 증거) ===")
import E_view as V
sw = [V.summary(V.kp_of(refs[m]))["sw_torso"] for m in refs]
print(f"  sw_torso  min={min(sw):.3f} max={max(sw):.3f} (같은 사람·같은 스튜디오·captureViews=1 인데 2.0배 폭)")
json.dump(rows, open(f"{D}/out/E_07_summary.json", "w"), ensure_ascii=False, indent=1)
