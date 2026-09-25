"""벌림 규칙 오프라인 게이트 — 09-24 저장 10편, 운영 DTW(mra.deviate) + 기준 창으로 split_phase 를 재구성."""
import importlib.util, json, pathlib, sys, logging
import numpy as np
REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend/shared/python")); sys.path.insert(0, str(REPO / "backend"))
spec = importlib.util.spec_from_file_location("mra", REPO / "backend/scripts/measure_reference_axis.py")
mra = importlib.util.module_from_spec(spec); spec.loader.exec_module(mra); app = mra.app
from sunity_shared.analysis import split_phase, technique
logging.basicConfig(level=logging.WARNING)
S = pathlib.Path(__file__).parent
data = json.loads((S / "offline_cache_0924.json").read_text())
print(f"{'동작':12s} {'판':8s} {'게이트':6s} {'학생':>6s} {'기준':>6s} {'부족분':>7s}  국면(학생/기준)  n  → md split_angle / 감점(tol20, 관절캡 -20)")
for uid, aid, ref, intent in data["runs"]:
    d = data["docs"][aid]; rd = data["refs"][ref]
    A = np.asarray(d["angles"], float).reshape(-1, 8); R = np.asarray(rd["angles"], float).reshape(-1, 8)
    rwin = app._reference_exec_window(rd, app._reference_angles_fps(rd), len(R))
    dev, m = mra.deviate(A, rd)
    start = int(getattr(m, "start", 0) or 0); rstart = int(getattr(m, "ref_start", 0) or 0)
    pairs = [(int(u) + start, int(r) + rstart) for u, r in (getattr(m, "path", None) or [])]
    uwin = app._student_window_from_match(m, *rwin) if rwin else None
    skp = np.asarray(d["result"]["joints3d"], float).reshape(int(d["result"]["joints3dFrames"]), 17, -1)
    rkp = np.asarray(rd["joints3d"], float).reshape(int(rd["joints3dFrames"]), 17, -1)
    out = split_phase.final_phase_split(skp[:, :, :3], rkp[:, :, :3], rwin, pairs, u_win=uwin) if rwin else None
    gate = ref in technique.SPLIT_LINE_ELEMENTS
    if out is None:
        print(f"{ref[4:]:12s} {intent:8s} {'ON' if gate else 'off':6s}  None (창 {rwin})"); continue
    deficit = max(0.0, out["deficitDeg"]); over = max(0.0, deficit - 20.0); pts = -min(over * 1.0, 20.0) if gate else 0.0
    print(f"{ref[4:]:12s} {intent:8s} {'ON' if gate else 'off':6s} {out['studentDeg']:6.1f} {out['referenceDeg']:6.1f} {out['deficitDeg']:+7.1f}  {out['studentPhase']}/{out['referencePhase']} {out['nStudent']}/{out['nReference']}  → {deficit:.1f} / {pts:+.1f}{'' if gate else ' (게이트 밖: 미방출)'}")
