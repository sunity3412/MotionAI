"""회전 효과만 분리 — 같은 코드·같은 날 추출한 OFF vs ON. 저장 시점 변수 제거."""
import json, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis.skeleton import JOINT_KEYS
off = json.load(open(sys.argv[1])); on = json.load(open(sys.argv[2]))
ok_, nk = list(off["jointKeys"]), list(on["jointKeys"])
print("== 회전 OFF → ON 이 기준 각도를 얼마나 움직이나 (같은 코드/같은 실행) ==")
print(f"{'기준':24s}" + "".join(f"{k.replace('left_','L.').replace('right_','R.'):>12s}" for k in JOINT_KEYS) + f"{'최대':>8s}{'>20':>5s}")
tot = 0; changed = 0
for mid in sorted(off["motions"]):
    A = np.asarray(off["motions"][mid]["angles"], float)[:, [ok_.index(k) for k in JOINT_KEYS]]
    B = np.asarray(on["motions"][mid]["angles"], float)[:, [nk.index(k) for k in JOINT_KEYS]]
    n = min(len(A), len(B))
    d = np.nanmedian(B[:n], 0) - np.nanmedian(A[:n], 0)
    over = int((np.abs(d) > 20).sum()); tot += over
    if np.abs(d).max() > 1e-9: changed += 1
    cells = "".join((f"{v:12.1f}" if abs(v) <= 20 else f"{('*%.1f' % v):>12s}") for v in d)
    print(f"{mid:24s}{cells}{np.abs(d).max():8.1f}{over:5d}")
print(f"\n회전이 각도를 바꾼 기준 = {changed}/11편 · 20° 초과 관절 = {tot}/88개")
