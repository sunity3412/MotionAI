"""창 안 운영 DTW 짝별 높이 차 + 표식 관절 신뢰도 → 대표 짝 후보."""
import json, pathlib
import numpy as np
H = pathlib.Path(__file__).parent
facts = json.load(open(H / "facts.json")); fd = json.load(open(H / "fault_doc.json")); rd = json.load(open(H / "ref_doc.json"))
def kp(kr, stride):
    J = kr["joints"]; T = kr["frames"]; j = {n: i for i, n in enumerate(J)}
    X = np.asarray(kr["data"], float).reshape(T, len(J), 2)[::stride]; C = np.asarray(kr["confidence"], float).reshape(T, len(J))[::stride]
    return X, C, j
Xs, Cs, j = kp(fd["result"]["keypointReport"], 2); Xr, Cr, _ = kp(rd["referenceKeypointReport"], 1)
f = facts["fault"]; st = f["stand"]
def hts(X, C, fl, body):
    ank = X[:, [j["left_ankle"], j["right_ankle"]], 1]; hip = X[:, [j["left_hip"], j["right_hip"]], 1].mean(1)
    grip = X[:, [j["left_hand"], j["right_hand"]], 1].min(1)
    return (fl - ank.max(1)) / body, (fl - hip) / body, (grip - hip) / body
lf_s, hip_s, hh_s = hts(Xs, Cs, st["student"]["floor"], st["student"]["body"])
lf_r, hip_r, hh_r = hts(Xr, Cr, st["ref"]["floor"], st["ref"]["body"])
mark = ["left_shoulder", "left_elbow", "left_hand", "left_ankle", "right_ankle"]
cnt = {}
for u, r in f["path_in_window"]:
    cnt[u] = cnt.get(u, 0) + 1
rows = []
for u, r in f["path_in_window"]:
    cmin = min(min(Cs[u, j[m]] for m in mark), min(Cr[r, j[m]] for m in mark))
    rows.append((u, r, lf_s[u] - lf_r[r], hip_s[u] - hip_r[r], hh_s[u] - hh_r[r], cmin, cnt[u]))
tgt_lf, tgt_hip = f["heights"]["낮은발"]["diff"], f["heights"]["엉덩이"]["diff"]
print(f"창 상수 차: 낮은발 {tgt_lf:+.2f} 엉덩이 {tgt_hip:+.2f}")
print(" u(s)     r(s)    d낮은발 d엉덩이 d엉덩이(손) conf_min 정체")
for u, r, a, b, c, cm, n in rows:
    flag = " <" if abs(a - tgt_lf) < 0.05 and abs(b - tgt_hip) < 0.04 and cm >= 0.5 and n == 1 else ""
    print(f"{u:3d}({u/9.9733:4.2f}) {r:3d}({r/15:4.2f})  {a:+.2f}  {b:+.2f}   {c:+.2f}     {cm:.2f}   {n}{flag}")
