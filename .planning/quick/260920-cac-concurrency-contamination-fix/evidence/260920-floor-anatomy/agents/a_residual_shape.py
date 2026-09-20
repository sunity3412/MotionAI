"""조사 A 단계5 — 같은 원본 프레임 짝의 잔차가 시간축 어디에 몰려 있나."""
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

for f in sorted(selfs, key=lambda x: x["ref"]):
    U = H.student_matrix(by_id[f["id"]]); R = H.ref_matrix(refs[f["ref"]])
    nu, nr = U.shape[0], R.shape[0]; scale = nr / nu
    sh = {"ref-combo": 0.5, "ref-foxtop": 0.5, "ref-foxtop-split": 0.0,
          "ref-invert": 1.5, "ref-sideway-spin": 0.5}[f["ref"]]
    idx = np.clip(np.round(np.arange(nu) * scale + sh).astype(int), 0, nr - 1)
    d = np.abs(U - R[idx])          # (nu, 8)
    per_frame = np.median(d, axis=1)
    print(f"\n=== {f['ref']}  nu={nu}  frame-median|d| : med={np.median(per_frame):.2f} "
          f"p10={np.percentile(per_frame,10):.2f} p90={np.percentile(per_frame,90):.2f} "
          f"frac<3deg={np.mean(per_frame<3):.3f} frac>20deg={np.mean(per_frame>20):.3f}")
    # 10 구간 요약
    B = 10
    edges = np.linspace(0, nu, B + 1).astype(int)
    print("  구간별 median:", " ".join(f"{np.median(per_frame[a:b]):5.1f}" for a, b in zip(edges[:-1], edges[1:])))
    # 관절별: 부호 있는 차이의 중앙값(=계통 편향) vs |차이| 중앙값(=총량)
    sd = np.median(U - R[idx], axis=0)
    ad = np.median(d, axis=0)
    print("  joint      :", " ".join(f"{k[:9]:>9s}" for k in H.JOINT_KEYS))
    print("  signed med :", " ".join(f"{x:9.2f}" for x in sd))
    print("  |diff| med :", " ".join(f"{x:9.2f}" for x in ad))
    print("  bias/total :", " ".join(f"{abs(a)/b*100:8.0f}%" for a, b in zip(sd, ad)))
