"""hold_height 모듈 = uff 측정 재현 게이트 (저장 doc, 학생 keypointReport 짝수 프레임 = 파이프라인 raw 9fps 판)."""
import importlib.util, json, pathlib, sys
import numpy as np
REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend/shared/python"))
spec = importlib.util.spec_from_file_location("mra", REPO / "backend/scripts/measure_reference_axis.py")
mra = importlib.util.module_from_spec(spec); spec.loader.exec_module(mra)
app = mra.app
from sunity_shared.analysis import hold_height as hh
H = pathlib.Path(__file__).parent
rd = json.load(open(H / "ref_doc.json"))
R = np.asarray(rd["angles"], float).reshape(-1, 8)
rwin = app._reference_exec_window(rd, app._reference_angles_fps(rd), len(R))
def raw(kr):
    """저장 18fps 판 → 짝수 프레임 = 9fps raw 판."""
    J = len(kr["joints"]); T = kr["frames"]
    X = np.asarray(kr["data"], float).reshape(T, J, 2)[::2]; C = np.asarray(kr["confidence"], float).reshape(T, J)[::2]
    return {"joints": kr["joints"], "frames": X.shape[0], "data": X.reshape(-1).tolist(), "confidence": C.reshape(-1).tolist()}
for name in ("fault_doc.json", "correct_doc.json"):
    d = json.load(open(H / name)); A = np.asarray(d["angles"], float).reshape(-1, 8)
    dev, m = mra.deviate(A, rd)
    uwin = app._student_window_from_match(m, *rwin)
    h = hh.hold_window_heights(raw(d["result"]["keypointReport"]), rd["referenceKeypointReport"], uwin, rwin)
    samp = app._window_constant_samples(A, R, uwin, rwin)
    ls = samp[2][1] - samp[2][2]
    print(f"== {name} 창 {uwin}/{rwin}  왼어깨 부호 {ls:+.2f}")
    for k, v in h.items():
        print(f"   {k:17s} 학생 {v['student']:+.3f} 정은지 {v['reference']:+.3f} 차 {v['diff']:+.3f}  1/3: " + "  ".join(f"{a:+.2f}|{b:+.2f}" for a, b in v["thirds"]))
    for tau in (0.02, 0.03, 0.05, 0.08, 0.10, 0.12, 0.13, 0.15):
        print(f"   noise {tau:.2f} -> {hh.body_low_arm_open(h, ls, noise=tau)}", end=";")
    print()

out = {}
for name in ("fault_doc.json", "correct_doc.json"):
    d = json.load(open(H / name)); A = np.asarray(d["angles"], float).reshape(-1, 8)
    dev, m = mra.deviate(A, rd); uwin = app._student_window_from_match(m, *rwin)
    h = hh.hold_window_heights(raw(d["result"]["keypointReport"]), rd["referenceKeypointReport"], uwin, rwin)
    samp = app._window_constant_samples(A, R, uwin, rwin)
    out[name] = {"heights": {k: {"diff": round(v["diff"], 4), "thirds": [[round(a, 4), round(b, 4)] for a, b in v["thirds"]]} for k, v in h.items()},
                 "left_shoulder_signed": round(samp[2][1] - samp[2][2], 2)}
print(json.dumps(out, ensure_ascii=False))
