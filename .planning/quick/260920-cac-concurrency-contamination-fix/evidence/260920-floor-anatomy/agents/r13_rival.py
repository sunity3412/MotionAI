"""반증 r13-B — (1) 겹치지 않는 격자 대조(동일 포즈, 위상차 1프레임)
                (2) 바닥을 설명하는 경쟁 예측자: 역립% vs 각속도 vs 각도 산포
"""
import json, sys, collections
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

refs = H.load_references()
facts = json.load(open(f"{H.D}/facts.json"))

def inverted(rdoc):
    k = rdoc["joints3dKeys"]; n = rdoc["joints3dFrames"]; d = int(rdoc.get("coordDim") or 3)
    K = np.asarray(rdoc["joints3d"], dtype=float).reshape(n, len(k), d)
    i = {nm: j for j, nm in enumerate(k)}
    sy = (K[:, i["left_shoulder"], 1] + K[:, i["right_shoulder"], 1]) / 2
    hy = (K[:, i["left_hip"], 1] + K[:, i["right_hip"], 1]) / 2
    return sy - hy

def spearman(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    rx = np.argsort(np.argsort(x)).astype(float); ry = np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])

print("=== (1) 겹치지 않는 격자 대조: ref=R[0::2](7.5fps), student=R[1::2] — 같은 포즈, 공유행 0, 위상차 1프레임(0.067s)")
print(f"{'motion':24s}{'disjoint':>10s}{'subset(same rows)':>19s}{'adj_med(15fps)':>16s}")
dis = {}
for mid, rdoc in sorted(refs.items()):
    R = H.ref_matrix(rdoc)
    Re, Ro = R[0::2], R[1::2]
    n = min(len(Re), len(Ro))
    dev, m = H.deviate(Ro[:n], Re[:n], ref_fps=H.ref_fps_of(rdoc) / 2.0)
    v = H.scalar(dev)
    dev2, _ = H.deviate(Re[:n], Re[:n], ref_fps=H.ref_fps_of(rdoc) / 2.0)
    adj = float(np.median(np.median(np.abs(np.diff(R, axis=0)), axis=1)))
    dis[mid] = v
    print(f"{mid:24s}{v:10.3f}{H.scalar(dev2):19.3f}{adj:16.3f}")

print("\n=== (2) 바닥 vs 경쟁 예측자 (11동작)")
g = collections.defaultdict(lambda: collections.defaultdict(list))
for f in facts:
    g[f["ref"]][f["label"]].append(f["scalar"])
rows = []
for mid, rdoc in sorted(refs.items()):
    R = H.ref_matrix(rdoc)
    c = g[mid].get("correct"); se = g[mid].get("self")
    floor = float(np.median(c)) if c else (float(np.median(se)) if se else None)
    src = "correct" if c else ("self" if se else "-")
    if floor is None:
        continue
    iv = float(np.mean(inverted(rdoc) > 0)) * 100
    adj = float(np.median(np.median(np.abs(np.diff(R, axis=0)), axis=1)))
    adjm = float(np.mean(np.abs(np.diff(R, axis=0))))
    sd = float(np.mean(np.std(R, axis=0)))
    rng = float(np.mean(np.ptp(R, axis=0)))
    rows.append((mid, src, floor, iv, adj, adjm, sd, rng))
print(f"{'motion':24s}{'src':>8s}{'floor':>8s}{'inv%':>7s}{'adjmed':>8s}{'adjmean':>9s}{'sd':>7s}{'range':>7s}")
for r in rows:
    print(f"{r[0]:24s}{r[1]:>8s}{r[2]:8.1f}{r[3]:7.1f}{r[4]:8.2f}{r[5]:9.2f}{r[6]:7.1f}{r[7]:7.1f}")
fl = [r[2] for r in rows]
for name, k in (("inv%", 3), ("adj_med", 4), ("adj_mean", 5), ("sd", 6), ("range", 7)):
    v = [r[k] for r in rows]
    keep = [i for i, r in enumerate(rows) if r[0] != "ref-climb"]
    print(f"  spearman(floor, {name:9s}) = {spearman(fl, v):6.3f}   climb제외 {spearman([fl[i] for i in keep], [v[i] for i in keep]):6.3f}")

# self 만 (같은 종류의 측정끼리)
srows = [r for r in rows if r[1] == "self"]
print("\n  self 만 (n=%d):" % len(srows))
if len(srows) >= 3:
    for name, k in (("inv%", 3), ("adj_med", 4), ("sd", 6)):
        print(f"    spearman = {spearman([r[2] for r in srows], [r[k] for r in srows]):6.3f}  ({name})")
crows = [r for r in rows if r[1] == "correct"]
print("  correct 만 (n=%d):" % len(crows))
for name, k in (("inv%", 3), ("adj_med", 4), ("sd", 6)):
    print(f"    spearman = {spearman([r[2] for r in crows], [r[k] for r in crows]):6.3f}  ({name})")
