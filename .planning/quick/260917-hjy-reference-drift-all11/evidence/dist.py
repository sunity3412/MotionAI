"""중앙값 외 분포(p10/p50/p90)로도 저장본↔재추출이 일치하는지 — 중앙값 우연일치 배제."""
import json, os, sys
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis.skeleton import JOINT_KEYS
REF, NEW = sys.argv[1], sys.argv[2]
new = json.load(open(NEW)); nk = list(new["jointKeys"])
print(f"{'기준':24s}{'|Δp10|최대':>11s}{'|Δp50|최대':>11s}{'|Δp90|최대':>11s}{'|Δ산포|최대':>12s}{'판정':>8s}")
worst = []
for mid in sorted(new["motions"]):
    doc = json.load(open(os.path.join(REF, f"{mid}.json")))
    st = np.asarray(doc["angles"], float).reshape(int(doc["anglesFrames"]), -1)
    sk = list(doc.get("anglesJointKeys") or JOINT_KEYS)
    st = st[:, [sk.index(k) for k in JOINT_KEYS]]
    na = np.asarray(new["motions"][mid]["angles"], float)[:, [nk.index(k) for k in JOINT_KEYS]]
    q = [10, 50, 90]
    S = np.nanpercentile(st, q, axis=0); N = np.nanpercentile(na, q, axis=0)
    d = np.abs(S - N)
    spread = np.abs((S[2] - S[0]) - (N[2] - N[0]))   # p90-p10 산포 차
    ok = max(d.max(), spread.max()) <= 20.0
    worst.append((float(max(d.max(), spread.max())), mid))
    print(f"{mid:24s}{d[0].max():11.1f}{d[1].max():11.1f}{d[2].max():11.1f}{spread.max():12.1f}{'OK' if ok else '★초과':>8s}")
worst.sort(reverse=True)
print(f"\n전체 최악 = {worst[0][1]} {worst[0][0]:.1f}°  (허용오차 20°)")
