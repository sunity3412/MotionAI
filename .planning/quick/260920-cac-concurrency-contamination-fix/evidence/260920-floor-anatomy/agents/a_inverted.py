"""조사 A 단계10 — (1) 보간 흔적(2차차분 0 구간) 비율, (2) 잔차가 '거꾸로 선 프레임'에 몰리나.

역립도 = (어깨 평균 y) - (엉덩이 평균 y)  [pole_aligned 픽셀축, y 클수록 화면 아래]
  > 0 이면 어깨가 엉덩이보다 아래 = 역립.
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

refs = H.load_references(); by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
selfs, seen = [], set()
for f in facts:
    if f["label"] == "self" and f["ref"] not in seen:
        seen.add(f["ref"]); selfs.append(f)
SH = {"ref-combo": 0.5, "ref-foxtop": 0.5, "ref-foxtop-split": 0.0,
      "ref-invert": 1.5, "ref-sideway-spin": 0.5}

def lin_frac(M):
    d2 = M[2:] - 2 * M[1:-1] + M[:-2]
    return float(np.mean(np.abs(d2) < 0.01))

def inverted(rdoc):
    k = rdoc["joints3dKeys"]; n = rdoc["joints3dFrames"]; d = int(rdoc.get("coordDim") or 3)
    K = np.asarray(rdoc["joints3d"], dtype=float).reshape(n, len(k), d)
    i = {nm: j for j, nm in enumerate(k)}
    sy = (K[:, i["left_shoulder"], 1] + K[:, i["right_shoulder"], 1]) / 2
    hy = (K[:, i["left_hip"], 1] + K[:, i["right_hip"], 1]) / 2
    return sy - hy

print("(1) 선형(보간 흔적) 프레임 비율")
print(f"{'motion':24s}{'ref lin%':>10s}{'stu lin%':>10s}{'inv frac(ref)':>15s}")
for f in sorted(selfs, key=lambda x: x["ref"]):
    R = H.ref_matrix(refs[f["ref"]]); U = H.student_matrix(by_id[f["id"]])
    iv = inverted(refs[f["ref"]])
    print(f"{f['ref']:24s}{lin_frac(R)*100:9.1f}%{lin_frac(U)*100:9.1f}%{float(np.mean(iv>0))*100:14.1f}%")
print()
for mid, rdoc in sorted(refs.items()):
    if mid in {f["ref"] for f in selfs}:
        continue
    R = H.ref_matrix(rdoc); iv = inverted(rdoc)
    print(f"{mid:24s}{lin_frac(R)*100:9.1f}%{'-':>10s}{float(np.mean(iv>0))*100:14.1f}%")

print("\n(2) 역립도 구간별 프레임 잔차 (같은 원본 프레임 짝, median |Δ| 도)")
for f in sorted(selfs, key=lambda x: x["ref"]):
    U = H.student_matrix(by_id[f["id"]]); R = H.ref_matrix(refs[f["ref"]])
    nu, nr = U.shape[0], R.shape[0]; scale = nr / nu
    idx = np.clip(np.round(np.arange(nu) * scale + SH[f["ref"]]).astype(int), 0, nr - 1)
    per = np.median(np.abs(U - R[idx]), axis=1)
    iv = inverted(refs[f["ref"]])[idx]
    qs = np.quantile(iv, [0, .25, .5, .75, 1])
    out = []
    for a, b in zip(qs[:-1], qs[1:]):
        sel = (iv >= a) & (iv <= b)
        out.append(f"{np.median(per[sel]):6.1f}" if sel.sum() else "     -")
    up = per[iv <= 0]; dn = per[iv > 0]
    print(f"{f['ref']:24s} 역립도4분위 {' '.join(out)}   |  정립 {np.median(up) if up.size else float('nan'):5.1f} "
          f"(n{up.size})  역립 {np.median(dn) if dn.size else float('nan'):5.1f} (n{dn.size})")

print("\n(3) 11동작: 역립 프레임 비율 vs 바닥")
import collections
g = collections.defaultdict(lambda: collections.defaultdict(list))
for f in facts:
    g[f["ref"]][f["label"]].append(f["scalar"])
print(f"{'motion':24s}{'inv%':>7s}{'correct':>9s}{'fault':>8s}{'self':>8s}")
for mid, rdoc in sorted(refs.items()):
    iv = inverted(rdoc); c = g[mid].get("correct"); fl = g[mid].get("fault"); se = g[mid].get("self")
    fmt = lambda v: f"{np.median(v):9.1f}" if v else f"{'-':>9s}"
    print(f"{mid:24s}{float(np.mean(iv>0))*100:6.1f}%{fmt(c)}{fmt(fl)[2:]}{fmt(se)[2:]}")
