"""검증된 채점 seam(어제 verify_score.py)으로 학생 4편 x 기준 2벌.

seam 은 어제 belle pdshape 60->87 / 정은지 60->100 을 재현해 검증됐다.
★ 한계: 학생 doc 이 전부 회전 OFF 분석본이다. 회전이 기준을 바꾼 동작에서는
   학생 OFF x 기준 ON 이라는 비대칭 비교가 되어 점수가 구조적으로 나빠진다
   (인계서 경고, 본 측정에서 pdshape 95->46 으로 재현됨).
   따라서 '회전 무영향' 동작의 수치만 배포 효과로 읽을 수 있다.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, 'backend/shared/python')
from sunity_shared.analysis import kismam, skeleton
from sunity_shared.analysis.features import feature_vector
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
KEYS = skeleton.JOINT_KEYS
TOL, SLOPE, REC_CAP, EXEC_CAP = 20.0, 1.2, 20.0, 40.0

def rs(flat, n, kin=None):
    a = np.asarray(flat, float)
    if a.ndim == 1: a = a.reshape(-1, n)
    if kin and list(kin) != list(KEYS): a = a[:, [list(kin).index(k) for k in KEYS]]
    return a

def seam(user, ref, fps):
    m = motion_dtw(feature_vector(user), feature_vector(ref), ref_boundary=None)
    us, rw = user[m.start:m.end], ref[m.ref_start:m.ref_end]
    dev = per_joint_deviation(m.path, us, rw, ref_fps=fps)
    ui = np.array([p[0] for p in m.path]); ri = np.array([p[1] for p in m.path])
    um = {k: float(np.nanmedian(us[ui, j])) for j, k in enumerate(KEYS)}
    rm = {k: float(np.nanmedian(rw[ri, j])) for j, k in enumerate(KEYS)}
    dim = kismam.overall_score(kismam.assess(dev, user_angles=um, reference_angles=rm,
                                             target_source="reference_motion"))
    exc = np.maximum(dev - TOL, 0.0)
    raw = float(np.minimum(exc * SLOPE, REC_CAP).sum())
    return dim, exc, raw, int(round(100.0 - min(raw, EXEC_CAP)))

EV = Path(sys.argv[1])
ROT_NOOP = {"ref-climb","ref-kip-up","ref-peter-pan","ref-power-spin","ref-sideway-spin"}
DOCS = Path(".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/docs_after")

def refload(tag, mid):
    d = json.load(open(EV/"refdirs"/tag/f"{mid}.json"))
    return rs(d["angles"], len(d["anglesJointKeys"]), d["anglesJointKeys"]), (d.get("anglesRealFps") or None)

rows=[]
for p in sorted(DOCS.glob("*.json")):
    d = json.loads(p.read_text())
    mid = (d.get("result") or {}).get("moveName") or d.get("moveName") or d.get("referenceMotionId")
    if not (EV/"refdirs"/"before"/f"{mid}.json").exists(): continue
    u = rs(d["angles"], len(d["anglesJointKeys"]), d["anglesJointKeys"])
    r={}
    for tag in ("before","after"):
        ra, rf = refload(tag, mid)
        r[tag] = seam(u, ra, rf)
    rows.append((mid, r, mid in ROT_NOOP))

print(f"{'동작':<24}{'배포전':>7}{'배포후':>7}{'이동':>7}   {'읽을 수 있나'}")
print("-"*74)
for mid, r, noop in sorted(rows, key=lambda t: (not t[2], t[0])):
    b, a = r["before"][3], r["after"][3]
    note = "O 회전 무영향 -> 배포 효과로 읽힘" if noop else "X 회전이 바꾼 편 -> 학생 OFF 라 비대칭(무효)"
    print(f"{mid:<24}{b:>7}{a:>7}{a-b:>+7}   {note}")
json.dump([{"move":m,"before":r["before"][3],"after":r["after"][3],
            "rot_noop":n,"before_raw":r["before"][2],"after_raw":r["after"][2]}
           for m,r,n in rows], open(EV/"scores_validated.json","w"), ensure_ascii=False, indent=1)
