"""반증 X4 — 소비처 주장의 '화면 점수' 부분을 라이브 저장 점수와 대조한다.

조사 B 의 [확인, 오늘 코드 기준] 문장 3건:
  (a) pdshape 역전이 **화면 점수**까지 간다 (correct 60 vs fault 79)
  (b) kip-up 3.20배 분리가 **화면**에 0점으로 도착한다 (100/100)
  (c) elbow-twist 는 실력차 0 에 이미 −14점 (86)

라이브 doc 에 저장된 overallScore(=화면 점수)와 나란히 놓는다.
생성 시각으로 쪼개 '코드 세대' 해명이 성립하는지도 본다.
"""
from __future__ import annotations
import json, sys, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)

rows = json.load(open(f"{D}/out/b_c5_consumer_ci.json"))
students = {s["id"]: s for s in json.load(open(f"{D}/students.json"))}
for r in rows:
    r["createdAt"] = students.get(r["id"], {}).get("createdAt")

g = collections.defaultdict(list)
for r in rows:
    g[(r["ref"], r["label"])].append(r)

print("=== 오늘 코드 축-단독 FINAL vs 라이브 저장 overallScore ===")
print(f"{'motion':24s} {'label':8s} {'n':>4s} {'오늘FIN':>7s} {'저장med':>7s} "
      f"{'저장=100%':>9s} {'일치%':>6s} {'저장 min~max':>13s}")
for k in sorted(g):
    rs = g[k]
    fin = np.median([r["final"] for r in rs])
    st = [r["stored_overall"] for r in rs if r["stored_overall"] is not None]
    if not st:
        continue
    agree = 100.0 * np.mean([abs(r["final"] - r["stored_overall"]) <= 2
                             for r in rs if r["stored_overall"] is not None])
    print(f"{k[0]:24s} {k[1]:8s} {len(rs):4d} {fin:7.0f} {np.median(st):7.0f} "
          f"{100*np.mean([v==100 for v in st]):8.0f}% {agree:5.0f}% "
          f"{min(st):6.0f}~{max(st):<6.0f}")

print("\n=== 세대 해명 검정: 생성 시기별 (pdshape/kip-up/elbow-twist correct·fault) ===")
for mid in ("ref-pdshape", "ref-kip-up", "ref-elbow-twist-sister"):
    for lab in ("correct", "fault"):
        rs = [r for r in g.get((mid, lab), []) if r["createdAt"] and r["stored_overall"] is not None]
        if not rs:
            continue
        rs.sort(key=lambda r: r["createdAt"])
        buckets = collections.defaultdict(list)
        for r in rs:
            buckets[str(r["createdAt"])[:7]].append(r)
        print(f"\n  {mid} / {lab}  (오늘코드 축단독 FIN median="
              f"{np.median([r['final'] for r in rs]):.0f})")
        for mon in sorted(buckets):
            bs = buckets[mon]
            print(f"    {mon}  n={len(bs):3d}  저장 med={np.median([r['stored_overall'] for r in bs]):3.0f}  "
                  f"저장=100 {100*np.mean([r['stored_overall']==100 for r in bs]):3.0f}%  "
                  f"오늘FIN med={np.median([r['final'] for r in bs]):3.0f}")

print("\n=== 세 주장 직접 판정 ===")
def med(mid, lab, key):
    rs = g.get((mid, lab), [])
    v = [r[key] for r in rs if r[key] is not None]
    return float(np.median(v)) if v else float("nan")

print(f"(a) pdshape 역전: 오늘코드 correct={med('ref-pdshape','correct','final'):.0f} "
      f"fault={med('ref-pdshape','fault','final'):.0f}  ||  "
      f"라이브 correct={med('ref-pdshape','correct','stored_overall'):.0f} "
      f"fault={med('ref-pdshape','fault','stored_overall'):.0f}")
print(f"(b) kip-up 분리소멸: 오늘코드 correct={med('ref-kip-up','correct','final'):.0f} "
      f"fault={med('ref-kip-up','fault','final'):.0f}  ||  "
      f"라이브 correct={med('ref-kip-up','correct','stored_overall'):.0f} "
      f"fault={med('ref-kip-up','fault','stored_overall'):.0f}")
print(f"(c) elbow 실력차0에 -14: 오늘코드 correct={med('ref-elbow-twist-sister','correct','final'):.0f}"
      f"  ||  라이브 correct={med('ref-elbow-twist-sister','correct','stored_overall'):.0f}")
