"""오프라인 게이트 — 수정판 _measured_phrase_variants 를 09-24 저장 doc 10편에 (gate10.py 와 같은 재구성)."""
import importlib.util, json, pathlib, sys, logging
import numpy as np
REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend/shared/python")); sys.path.insert(0, str(REPO / "backend"))
spec = importlib.util.spec_from_file_location("mra", REPO / "backend/scripts/measure_reference_axis.py")
mra = importlib.util.module_from_spec(spec); spec.loader.exec_module(mra)
app = mra.app
from sunity_shared import models
from sunity_shared.analysis import hold_height as hh
logging.basicConfig(level=logging.INFO, format="%(message)s")
S = pathlib.Path(__file__).parent
data = json.loads((S / "offline_cache_0924.json").read_text())
def raw(kr):
    J = len(kr["joints"]); T = kr["frames"]
    X = np.asarray(kr["data"], float).reshape(T, J, 2)[::2]; C = np.asarray(kr["confidence"], float).reshape(T, J)[::2]
    return {"joints": kr["joints"], "frames": X.shape[0], "data": X.reshape(-1).tolist(), "confidence": C.reshape(-1).tolist()}
for uid, aid, ref, intent in data["runs"]:
    d = data["docs"][aid]; rd = data["refs"][ref]
    A = np.asarray(d["angles"], float).reshape(-1, 8); R = np.asarray(rd["angles"], float).reshape(-1, 8)
    rwin = app._reference_exec_window(rd, app._reference_angles_fps(rd), len(R))
    dev, m = mra.deviate(A, rd)
    recs = d["result"]["deductionBreakdown"]["records"]
    uwin = app._student_window_from_match(m, *rwin) if rwin else None
    samp = app._window_constant_samples(A, R, uwin, rwin) if uwin else {}
    const = []
    for r in recs:
        c = r.get("criterion", "")
        if c.startswith("angle_vs_reference__"):
            jk = c.split("__", 1)[1]; j = list(mra.JOINT_KEYS).index(jk)
            if j in samp and abs(abs(samp[j][1] - samp[j][2]) - float(r["measuredValue"])) < 0.02:
                const.append(jk)
    stu_kp = raw(d["result"]["keypointReport"])
    print(f"===== {ref} {intent} score={d['result']['overallScore']} records={[r['criterion'] for r in recs]} const={const}")
    out = app._measured_phrase_variants(
        mode=models.MODE_EXPERT, motion_id=ref, reference_motion_id=ref, result=d["result"], angles=A, reference_angles=R,
        reference_exec_window=rwin, reference_dtw_match=m, student_keypoint_report=stu_kp,
        reference_keypoint_report=rd["referenceKeypointReport"], constant_joints=const, uid=uid, analysis_id=aid,
        student_fps=9.9733, reference_fps=app._reference_angles_fps(rd))
    print("   variants:", {k: (v["pattern"], v["atFrameIdx"], round(v["atVideoSec"],2), round(v["atRefVideoSec"],2)) for k, v in out.items()} or "-")
    for k, v in out.items():
        for slot, text in v["slots"].items(): print(f"     {slot}: {text}")
