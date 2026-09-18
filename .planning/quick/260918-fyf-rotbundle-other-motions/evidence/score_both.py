"""학생 4편 x 기준 2벌(배포 전/후) 채점 — 파이프라인 코드 직접 호출 (재구현 0).

호출 형태 출처 = 260917-hjy/evidence/rescore2.py (그 자체가 pipeline/app.py:7981-8004 전사).
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
TOL = 20.0

def reshape(flat, keys_in, frames):
    a = np.asarray(flat, float).reshape(int(frames), len(keys_in))
    if list(keys_in) != list(KEYS):
        a = a[:, [list(keys_in).index(k) for k in KEYS]]
    return a

def score(user, ref, ref_fps):
    m = motion_dtw(feature_vector(user), feature_vector(ref), ref_boundary=None)
    us, rw = user[m.start:m.end], ref[m.ref_start:m.ref_end]
    dev = per_joint_deviation(m.path, us, rw, ref_fps=ref_fps)
    ui = np.array([p[0] for p in m.path]); ri = np.array([p[1] for p in m.path])
    um = {k: float(np.nanmedian(us[ui, j])) for j, k in enumerate(KEYS)}
    rm = {k: float(np.nanmedian(rw[ri, j])) for j, k in enumerate(KEYS)}
    a = kismam.assess(dev, user_angles=um, reference_angles=rm, target_source="reference_motion")
    excess = np.maximum(dev - TOL, 0.0)
    return kismam.overall_score(a), dev, excess

EV = Path(sys.argv[1])
live = json.load(open(EV/"ref_live_deployed.json"))
prev = json.load(open(EV/"ref_phase4_v1.json"))
DOCS = Path(".planning/quick/260731-iis-33-g-c-4-a-track-reference-12-joint-18fp/docs_after")

rows = []
for p in sorted(DOCS.glob("*.json")):
    d = json.loads(p.read_text())
    mv = (d.get("result") or {}).get("moveName") or d.get("moveName") or d.get("referenceMotionId")
    if mv not in live or mv not in prev:
        print(f"  {p.stem}: 기준 {mv} 없음 — 건너뜀"); continue
    U = reshape(d["angles"], d["anglesJointKeys"], d["anglesFrames"])
    out = {}
    for tag, src in (("before", prev[mv]), ("after", live[mv])):
        R = reshape(src["angles"], src["jointKeys"], src["numFrames"])
        out[tag] = score(U, R, src.get("fps") or 15.0)
    stored = (d.get("result") or {}).get("overallScore") or d.get("overallScore")
    rows.append({
        "doc": p.stem, "move": mv, "storedOverall": stored,
        "before_angle": out["before"][0], "after_angle": out["after"][0],
        "before_dev": out["before"][1].tolist(), "after_dev": out["after"][1].tolist(),
        "before_excess_sum": float(out["before"][2].sum()), "after_excess_sum": float(out["after"][2].sum()),
        "before_excess_n": int((out["before"][2] > 0).sum()), "after_excess_n": int((out["after"][2] > 0).sum()),
    })

print(f"{'동작':<26}{'배포전':>8}{'배포후':>8}{'이동':>8}{'초과관절':>12}{'초과합°':>16}")
print("-"*80)
for r in rows:
    dlt = r["after_angle"] - r["before_angle"]
    mark = "  ★악화" if dlt < 0 else ("  개선" if dlt > 0 else "")
    print(f"{r['move']:<26}{r['before_angle']:>8}{r['after_angle']:>8}{dlt:>+8}"
          f"{r['before_excess_n']:>6}->{r['after_excess_n']:<5}"
          f"{r['before_excess_sum']:>8.1f}->{r['after_excess_sum']:<7.1f}{mark}")
json.dump(rows, open(EV/"scores_before_after.json","w"), ensure_ascii=False, indent=1)
print(f"\n저장: {EV/'scores_before_after.json'}")
