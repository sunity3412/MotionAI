"""E-6 — 경쟁 가설 대조: 시점 불일치 vs 기준측 키포인트 저신뢰 비율.

둘 다 '동작별 바닥'을 설명한다고 주장할 수 있다. 어느 쪽이 순서를 맞히나.
저신뢰 비율은 기준 doc 의 keypointReport.confidence (T×8 flat) 에서 곧장 나온다 —
운영이 저장한 값이고, 같은 doc 의 angles 는 temporal_fill 이 그 저신뢰 구간을
보간해 만든 것이다(E-5 검증: temporal_fill(compute_joint_angles(joints3d)) 가
저장 angles 를 median 0.003° 로 재현).
"""
import json, sys, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D); sys.path.insert(0, f"{D}/out")
import harness as H

refs = H.load_references()
facts = json.load(open(f"{D}/facts.json"))
byref = collections.defaultdict(lambda: collections.defaultdict(list))
for r in facts:
    byref[r["ref"]][r["label"]].append(r["scalar"])

rows = []
for m, r in sorted(refs.items()):
    conf = np.asarray(r["keypointReport"]["confidence"], float)
    co = byref[m]["correct"]; se = byref[m]["self"]; fa = byref[m]["fault"]
    floor = np.median(co) if co else (np.median(se) if se else None)
    src = "correct" if co else ("self" if se else "-")
    rows.append(dict(motion=m, floor=float(floor) if floor is not None else None, floor_src=src,
                     n=len(co) if co else (len(se) if se else 0),
                     fault=float(np.median(fa)) if fa else None,
                     low_conf=float((conf < 0.5).mean()),
                     med_conf=float(np.median(conf)),
                     p10_conf=float(np.percentile(conf, 10))))


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    ra = np.argsort(np.argsort(a)).astype(float); rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    return round(float((ra @ rb) / np.sqrt((ra @ ra) * (rb @ rb))), 3), int(a.size)


print(f"{'motion':24s}{'바닥°':>8s}{'출처':>9s}{'n':>5s}{'fault°':>8s}{'저신뢰%':>9s}{'medConf':>9s}")
for x in sorted(rows, key=lambda z: (z["floor"] is None, z["floor"] or 0)):
    print(f"{x['motion']:24s}{(x['floor'] if x['floor'] is not None else float('nan')):8.1f}"
          f"{x['floor_src']:>9s}{x['n']:5d}"
          f"{(x['fault'] if x['fault'] is not None else float('nan')):8.1f}"
          f"{x['low_conf']:9.1%}{x['med_conf']:9.3f}")
fl = [x["floor"] for x in rows]; lc = [x["low_conf"] for x in rows]; mc = [x["med_conf"] for x in rows]
print()
print("Spearman(저신뢰 프레임비율, 바닥)  n=11:", spearman(lc, fl))
print("Spearman(median conf,     바닥)  n=11:", spearman(mc, fl))
json.dump(rows, open(f"{D}/out/E_06_rival.json", "w"), ensure_ascii=False, indent=1)

# Gemini C — '촬영 각도가 문제인가' 를 운영이 스스로 판정한 필드
FX = "/Users/kimtaesung/Dev/SunityMotion/backend/evals/realfixture/fixtures"
print()
print("geminiC (운영 자체 촬영각도 판정) — 리포 fixture 4건:")
for fn in ("pdshapeCorrect1785373695", "kipupFault1785373695",
           "elbowtwistsisterFault1785373695", "powerspinFault1785373695"):
    g = json.load(open(f"{FX}/{fn}.json")).get("geminiC") or {}
    print(f"   {fn[:26]:28s} camera_angle_problematic={str(g.get('camera_angle_problematic')):6s}"
          f" occlusion_severe={str(g.get('occlusion_severe')):6s} grip_visible={str(g.get('grip_visible')):6s}")
    if g.get("notes_ko"):
        print(f"      notes_ko: {str(g['notes_ko'])[:160]}")
