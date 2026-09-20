"""조사 F — 전이함수 검증(운영 상수로 손계산 == tally.final) + 억제 영향 + 민감도."""
import sys, json, collections
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
import numpy as np
from sunity_shared.analysis import ipsf_criteria, deduction_engine

TOL = ipsf_criteria._ANGLE_TOLERANCE_DEG
SLOPE = ipsf_criteria._SLOPE
CCAP = ipsf_criteria._ANGLE_CAP
RCAP = deduction_engine.PER_RECORD_DEDUCTION_CAP
ECAP = deduction_engine.EXECUTION_DEDUCTION_CAP
FLOOR = deduction_engine.SCORE_FLOOR
print(f"운영 상수: tol={TOL} slope={SLOPE} criterion_cap={CCAP} "
      f"record_cap={RCAP} execution_cap={ECAP} score_floor={FLOOR} baseline=100")
print(f"  관절 1개 포화점: dev = tol + record_cap/slope = {TOL + RCAP/SLOPE:.2f}도 → -20점")
print(f"  집계캡 도달: 포화 관절 {ECAP/RCAP:.0f}개 → final {100-ECAP:.0f} (바닥)")

rows = [r for r in json.load(open(f"{D}/out/F_finals.json")) if r["profile_mode"] == "ref"]

def hand(md):
    pts = []
    for k, v in md.items():
        if not k.startswith("angle_vs_reference__"):
            continue
        over = max(0.0, v - TOL)
        if over <= 0:
            continue
        capped = round(min(over * SLOPE, CCAP), 1)
        pts.append(min(capped, RCAP))
    s = round(sum(pts), 1)
    return int(max(FLOOR, round(100 - min(ECAP, s))))

# 억제가 없는 경로(qa_nosupp)와 손계산이 같아야 한다
bad = [(r["id"], hand(r["md"]), r["qa_nosupp_final"]) for r in rows
       if hand(r["md"]) != r["qa_nosupp_final"]]
print(f"\n손계산 == tally.final(억제 off): 불일치 {len(bad)}/{len(rows)}건")
for x in bad[:5]:
    print("  ", x)

d = [r["qa_final"] - r["qa_nosupp_final"] for r in rows]
print(f"\n측정불확실도 억제가 살려준 점수: median {np.median(d):+.1f}  "
      f"최대 {max(d):+d}  발생 {sum(1 for x in d if x>0)}/{len(rows)}건")

print("\n민감도(이 축이 화면에 번역되는 비율):")
print(f"  허용오차 {TOL}도 이하 = 0점. 그 위로 1도당 {SLOPE}점.")
print(f"  관절 하나가 낼 수 있는 최대 감점 {RCAP}점(= dev {TOL+RCAP/SLOPE:.1f}도에서 포화).")
print(f"  전체 감점 상한 {ECAP}점 → 이 축만으로 도달 가능한 최저 화면 점수 {100-ECAP:.0f}점.")

# 편차 스칼라 1도 변화 → 점수 변화 (구간 회귀 대신 실측 인접구간 차)
print("\n실측 전이(편차 스칼라 → final, 1도 폭 구간 median):")
for lo in range(0, 32, 2):
    v = [r["qa_final"] for r in rows if lo <= r["scalar"] < lo + 2]
    if len(v) >= 3:
        print(f"   [{lo:2d},{lo+2:2d}) n={len(v):4d} final median {np.median(v):5.1f} "
              f"범위 {min(v)}~{max(v)}")
