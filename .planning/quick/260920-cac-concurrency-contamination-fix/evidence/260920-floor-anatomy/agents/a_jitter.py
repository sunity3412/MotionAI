"""조사 A 단계4 — 바닥을 만드는 것이 '프레임별 포즈 잡음'인가.

추정기: 2차 차분 d2 = x[t+1]-2x[t]+x[t-1].
  매끈한 운동은 d2 가 작고, iid 잡음 e~N(0,s) 는 d2 잡음성분 sd = sqrt(6)*s.
  median|d2| = 0.6745 * sqrt(6) * s  →  s_hat = median|d2| / (0.6745*sqrt(6)).
(운동의 곡률이 섞이므로 s_hat 은 상한 성격.)

그 s_hat 으로 기준행렬에 독립 잡음을 주입 → 학생 격자(10fps)로 솎아 H.deviate.
포즈 잡음만으로 self 바닥이 재현되면 기전이 닫힌다.
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

STUDENT_FPS = 10.0
K = 0.6745 * np.sqrt(6.0)
refs = H.load_references(); by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
self_by_ref = {}
for f in facts:
    if f["label"] == "self" and f["ref"] not in self_by_ref:
        self_by_ref[f["ref"]] = f

def sigma_hat(M):
    d2 = M[2:] - 2 * M[1:-1] + M[:-2]
    return np.nanmedian(np.abs(d2), axis=0) / K

rng = np.random.default_rng(20260920)
rows = []
print(f"{'motion':24s}{'s_ref':>7s}{'s_stu':>7s}{'inj_med':>9s}{'inj_sd':>7s}"
      f"{'self':>7s}{'corr':>7s}{'fault':>7s}")
import collections
g = collections.defaultdict(lambda: collections.defaultdict(list))
for f in facts:
    g[f["ref"]][f["label"]].append(f["scalar"])

for mid, rdoc in sorted(refs.items()):
    R = H.ref_matrix(rdoc); nr = R.shape[0]; ratio = H.ref_fps_of(rdoc) / STUDENT_FPS
    s_ref = sigma_hat(R)
    sf = self_by_ref.get(mid)
    s_stu = sigma_hat(H.student_matrix(by_id[sf["id"]])) if sf else None
    nu = int(round(nr / ratio))
    idx = np.clip(np.round(np.arange(nu) * ratio).astype(int), 0, nr - 1)
    vals, devs = [], []
    for t in range(5):
        U = R[idx] + rng.normal(0.0, 1.0, size=(nu, R.shape[1])) * s_ref[None, :]
        dev, m = H.deviate(U, rdoc)
        vals.append(H.scalar(dev)); devs.append([float(x) for x in dev])
    c = g[mid].get("correct"); fl = g[mid].get("fault")
    row = dict(motion=mid, sigma_ref=[round(float(x), 2) for x in s_ref],
               sigma_ref_med=float(np.median(s_ref)),
               sigma_stu_med=(float(np.median(s_stu)) if s_stu is not None else None),
               inject_med=float(np.median(vals)), inject_sd=float(np.std(vals)),
               inject_perjoint=[round(float(x), 2) for x in np.median(np.asarray(devs), axis=0)],
               self_scalar=(sf["scalar"] if sf else None),
               correct_med=(float(np.median(c)) if c else None),
               fault_med=(float(np.median(fl)) if fl else None))
    rows.append(row)
    print(f"{mid:24s}{row['sigma_ref_med']:7.2f}"
          f"{(row['sigma_stu_med'] if row['sigma_stu_med'] is not None else float('nan')):7.2f}"
          f"{row['inject_med']:9.2f}{row['inject_sd']:7.2f}"
          f"{(row['self_scalar'] or float('nan')):7.1f}"
          f"{(row['correct_med'] or float('nan')):7.1f}"
          f"{(row['fault_med'] or float('nan')):7.1f}")
json.dump(rows, open(f"{H.D}/out/a_jitter.json", "w"))
