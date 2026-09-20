"""조사 A 단계9 — temporal_fill 의 평활창이 '프레임 단위'라서 생기는 격자 의존 몫.

temporal.DEFAULT_SMOOTH_WINDOW = 5 프레임 (초 아님).
  기준 축 ~14.95fps → 5프레임 = 0.334초
  학생 축 ~ 9.98fps → 5프레임 = 0.501초
같은 원본 프레임이라도 두 축은 **다른 시간 창**으로 평활된 값을 담는다.
저장된 angles 는 이미 평활 후라 단계2(행 고르기)로는 이 몫이 보이지 않는다.

여기서는 기준 시리즈에 운영 _smooth_column 을 한 번 더 걸어(창 확대의 대리)
  (a) 그 자체로 얼마나 움직이나
  (b) 추가 평활이 학생 시리즈에 **가까워지게** 하나
를 잰다.
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np
from sunity_shared.analysis import temporal

def ma(M, w):
    bad = np.zeros(M.shape[0], dtype=bool)
    return np.stack([temporal._smooth_column(M[:, c].copy(), bad, w, 0.25)
                     for c in range(M.shape[1])], axis=1)

refs = H.load_references(); by_id = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{H.D}/facts.json"))
selfs, seen = [], set()
for f in facts:
    if f["label"] == "self" and f["ref"] not in seen:
        seen.add(f["ref"]); selfs.append(f)
SH = {"ref-combo": 0.5, "ref-foxtop": 0.5, "ref-foxtop-split": 0.0,
      "ref-invert": 1.5, "ref-sideway-spin": 0.5}

print("(a) 기준에 MA 를 한 번 더 걸면 값이 얼마나 움직이나 (median |Δ| 도)")
print(f"{'motion':24s}{'+MA3':>8s}{'+MA5':>8s}{'+MA7':>8s}")
for mid, rdoc in sorted(refs.items()):
    R = H.ref_matrix(rdoc)
    print(f"{mid:24s}" + "".join(f"{np.median(np.abs(ma(R,w)-R)):8.2f}" for w in (3,5,7)))

print("\n(b) 추가 평활이 학생 시리즈에 가까워지게 하나 (같은 원본 프레임 짝, median |Δ|)")
print(f"{'motion':24s}{'raw':>8s}{'+MA3':>8s}{'+MA5':>8s}{'+MA7':>8s}{'학생+MA3 vs 기준':>18s}")
for f in sorted(selfs, key=lambda x: x["ref"]):
    U = H.student_matrix(by_id[f["id"]]); R = H.ref_matrix(refs[f["ref"]])
    nu, nr = U.shape[0], R.shape[0]; scale = nr / nu
    idx = np.clip(np.round(np.arange(nu) * scale + SH[f["ref"]]).astype(int), 0, nr - 1)
    vals = [np.median(np.abs(U - R[idx]))]
    for w in (3, 5, 7):
        vals.append(np.median(np.abs(U - ma(R, w)[idx])))
    rev = np.median(np.abs(ma(U, 3) - R[idx]))
    print(f"{f['ref']:24s}" + "".join(f"{v:8.2f}" for v in vals) + f"{rev:18.2f}")
