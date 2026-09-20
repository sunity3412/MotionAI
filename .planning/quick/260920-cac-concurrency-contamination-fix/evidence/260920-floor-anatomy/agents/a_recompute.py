"""조사 A 단계6 — 기준 doc 의 저장 angles 가 현재 각도 코드로 재현되나.

기준 doc 은 joints3d(플랫)도 갖고 있다. 현재 운영 함수 compute_joint_angles 로
다시 계산해 저장된 angles 와 대조한다.
  일치  -> 각도 산식은 그대로. 차이는 상류(keypoint 추출)에 있다.
  불일치-> 기준 angles 는 지금 파이프라인과 다른 산식/전처리로 구워진 것.
"""
import json, sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np
from sunity_shared.analysis import features, skeleton

refs = H.load_references()
print(f"{'motion':24s}{'j3dFrames':>10s}{'nk':>4s}{'dim':>4s}{'z!=0%':>7s}"
      f"{'recomp vs stored |d| med':>26s}{'p90':>8s}{'frac<1e-6':>10s}")
for mid, r in sorted(refs.items()):
    A = H.ref_matrix(r)
    j3 = r.get("joints3d"); keys = r.get("joints3dKeys"); nfr = r.get("joints3dFrames")
    if not j3:
        print(f"{mid:24s}{'-':>10s}")
        continue
    nk = len(keys); dim = int(r.get("coordDim") or 3)
    K = np.asarray(j3, dtype=float).reshape(nfr, nk, dim)
    zfrac = float(np.mean(np.abs(K[:, :, 2]) > 1e-9)) if dim >= 3 else float("nan")
    # keypoint 순서를 skeleton.KEYPOINT_NAMES 로 재배열
    name2i = {n: i for i, n in enumerate(keys)}
    try:
        order = [name2i[n] for n in skeleton.KEYPOINT_NAMES]
    except KeyError as e:
        print(f"{mid:24s} keypoint 이름 불일치 {e}")
        continue
    Kp = K[:, order, :]
    B = np.asarray(features.compute_joint_angles(Kp), dtype=float)
    n = min(B.shape[0], A.shape[0])
    d = np.abs(B[:n] - A[:n])
    print(f"{mid:24s}{nfr:10d}{nk:4d}{dim:4d}{zfrac*100:6.1f}%"
          f"{np.nanmedian(d):26.4f}{np.nanpercentile(d,90):8.3f}"
          f"{float(np.mean(d < 1e-6)):10.4f}")
