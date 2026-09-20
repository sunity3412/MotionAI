"""Same source frame, two extractions: do the KEYPOINTS disagree, and how?

Joint angles are invariant to global translation/rotation/scale, so a floor of
32 deg cannot come from a different crop or a different pole-alignment rotation.
It has to be relative geometry: individual keypoints landing somewhere else.

The repo fixture set carries joints3d for BOTH sides of four motions, so this runs
with no network. Row i of the student is source frame 3i; row j of the reference is
source frame 2j; even i pairs with j = 3i/2 on the identical source frame.

Reported per joint on those coincident frames, after Procrustes alignment
(translation + uniform scale + rotation removed, since those cannot move an angle):
  - residual position error, normalised by torso length
  - how often the error is large (a joint placed somewhere else entirely)
"""
import json, os
import numpy as np

REPO = "/Users/kimtaesung/Dev/SunityMotion"
FX = f"{REPO}/backend/evals/realfixture/fixtures"
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"

PAIRS = {
    "ref-pdshape": "pdshapeCorrect1785373695.json",
    "ref-kip-up": "kipupFault1785373695.json",
    "ref-power-spin": "powerspinFault1785373695.json",
    "ref-elbow-twist-sister": "elbowtwistsisterFault1785373695.json",
}


def kp(doc, nested):
    src = doc.get("result", doc) if nested else doc
    keys = src.get("joints3dKeys") or doc.get("joints3dKeys")
    n = src.get("joints3dFrames") or doc.get("joints3dFrames")
    flat = src.get("joints3d") or doc.get("joints3d")
    a = np.asarray(flat, dtype=float).reshape(n, len(keys), 3)
    return a[:, :, :2], list(keys)


def procrustes(A, B):
    """Best similarity transform of A onto B; returns transformed A."""
    ok = np.isfinite(A).all(1) & np.isfinite(B).all(1)
    if ok.sum() < 3:
        return A
    a, b = A[ok], B[ok]
    ca, cb = a.mean(0), b.mean(0)
    a0, b0 = a - ca, b - cb
    sa = np.sqrt((a0 ** 2).sum()) or 1.0
    sb = np.sqrt((b0 ** 2).sum()) or 1.0
    U, _, Vt = np.linalg.svd((a0 / sa).T @ (b0 / sb))
    R = (U @ Vt).T
    return ((A - ca) / sa) @ R.T * sb + cb


ANG = ["left_elbow", "right_elbow", "left_shoulder", "right_shoulder",
       "left_hip", "right_hip", "left_knee", "right_knee"]

for motion, fname in PAIRS.items():
    rpath = f"{FX}/reference/{motion}.json"
    spath = f"{FX}/{fname}"
    if not (os.path.exists(rpath) and os.path.exists(spath)):
        print(f"{motion}: fixture missing, skipped")
        continue
    rdoc, sdoc = json.load(open(rpath)), json.load(open(spath))
    R, rk = kp(rdoc, nested=False)
    S, sk = kp(sdoc, nested=True)
    if rk != sk:
        print(f"{motion}: joint key order differs, skipped")
        continue
    ratio = len(S) / len(R)
    label = "SAME footage" if abs(ratio - 2 / 3) < 0.01 else "different footage"
    print(f"\n=== {motion}  ref {len(R)} rows / student {len(S)} rows "
          f"(ratio {ratio:.4f} -> {label}) ===")
    if abs(ratio - 2 / 3) > 0.01:
        print("   not the same footage; keypoint comparison is not meaningful here")
        continue

    torso = []
    resid = {k: [] for k in rk}
    for i in range(0, len(S), 2):
        j = int(i * 3 / 2)
        if j >= len(R):
            break
        a = procrustes(S[i], R[j])
        t = np.linalg.norm(R[j][rk.index("left_shoulder")] - R[j][rk.index("left_hip")])
        if not np.isfinite(t) or t <= 0:
            continue
        torso.append(t)
        d = np.linalg.norm(a - R[j], axis=1) / t
        for n_, k in enumerate(rk):
            resid[k].append(d[n_])

    if not torso:
        print("   no usable frames")
        continue
    print(f"   coincident frames: {len(torso)}   median torso px: {np.median(torso):.1f}")
    print(f"   {'joint':20s}{'median resid':>14s}{'p90':>8s}{'frac>0.25 torso':>17s}")
    rank = sorted(rk, key=lambda k: -np.median(resid[k]))
    for k in rank[:10]:
        v = np.array(resid[k])
        mark = "  <- angle joint" if k in ANG else ""
        print(f"   {k:20s}{np.median(v):14.3f}{np.percentile(v,90):8.3f}"
              f"{float((v>0.25).mean()):17.2f}{mark}")
