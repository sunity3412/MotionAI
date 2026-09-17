"""저장 기준 angles vs 재추출 angles — 관절별 드리프트 전수.

두 시퀀스는 길이가 다르다(저장 ~15fps, 재추출 ~10fps). 같은 동작이므로
관절별 '시간 중앙값'을 비교한다 — 09-14 REFERENCE-IS-BROKEN.md §3 과 같은 정의.
"""
import json, os, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis.skeleton import JOINT_KEYS

TOL = 20.0  # 허용오차(도) — 09-14 §3
REF, NEW, LABEL = sys.argv[1], sys.argv[2], sys.argv[3]
new = json.load(open(NEW)); nk = list(new["jointKeys"]); motions = new["motions"]
rows = []
for mid in sorted(motions):
    p = os.path.join(REF, f"{mid}.json")
    if not os.path.exists(p): continue
    doc = json.load(open(p))
    st = np.asarray(doc["angles"], float).reshape(int(doc["anglesFrames"]), -1)
    sk = list(doc.get("anglesJointKeys") or JOINT_KEYS)
    st = st[:, [sk.index(k) for k in JOINT_KEYS]]
    na = np.asarray(motions[mid]["angles"], float)[:, [nk.index(k) for k in JOINT_KEYS]]
    dm = np.nanmedian(st, 0) - np.nanmedian(na, 0)
    rows.append(dict(id=mid, stored_frames=st.shape[0], new_frames=na.shape[0],
                     delta=dm.tolist(), absmax=float(np.abs(dm).max()),
                     n_over=int((np.abs(dm) > TOL).sum())))
json.dump(rows, open(os.path.join(REF, f"_drift_{LABEL}.json"), "w"), indent=1)

print(f"== 저장본 vs 재추출({LABEL}) — 관절 중앙각 차이(도), 허용오차 {TOL:.0f}° ==")
print(f"{'기준':24s}{'프레임(저장→재)':>16s}" + "".join(f"{k.replace('left_','L.').replace('right_','R.'):>12s}" for k in JOINT_KEYS) + f"{'최대':>8s}{'초과':>5s}")
tot = 0
for r in rows:
    tot += r["n_over"]
    cells = "".join((f"{v:12.1f}" if abs(v) <= TOL else f"{('*%.1f' % v):>12s}") for v in r["delta"])
    print(f"{r['id']:24s}{f'{r[chr(115)+chr(116)+chr(111)+chr(114)+chr(101)+chr(100)+chr(95)+chr(102)+chr(114)+chr(97)+chr(109)+chr(101)+chr(115)]}→{r[chr(110)+chr(101)+chr(119)+chr(95)+chr(102)+chr(114)+chr(97)+chr(109)+chr(101)+chr(115)]}':>16s}{cells}{r['absmax']:8.1f}{r['n_over']:5d}")
print(f"\n합계: 88개 관절-기준 쌍 중 허용오차 {TOL:.0f}° 초과 = {tot}개 ({100*tot/max(len(rows)*8,1):.0f}%)")
print(f"기준 {len(rows)}편 중 1개 이상 초과 = {sum(1 for r in rows if r['n_over'])}편")
