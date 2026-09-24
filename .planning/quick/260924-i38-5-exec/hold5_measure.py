"""유지 구간 상수 — 5동작. 창 = 기준 clipRange(execStartS~landEndS)를 운영 DTW 로 학생 시간축에 옮긴 것(짝은 창 가장자리에만).
상수 = 창 안 짝 없는 중앙값: 발/엉덩이 높이(바닥 p95 기준, 손 기준), 8관절 각도. 비교열 = 운영 DTW 편차(measure_doc)."""
import importlib.util, json, pathlib, sys
import numpy as np
REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
spec = importlib.util.spec_from_file_location("mra", REPO / "backend/scripts/measure_reference_axis.py")
mra = importlib.util.module_from_spec(spec); spec.loader.exec_module(mra)
JK = mra.JOINT_KEYS
S = pathlib.Path(sys.argv[1]); D = json.load(open(S / "fix10.json"))
def kp(kr, stride):
    J = kr["joints"]; T = kr["frames"]; j = {n: i for i, n in enumerate(J)}
    X = np.asarray(kr["data"], float).reshape(T, len(J), 2)[::stride]; C = np.asarray(kr["confidence"], float).reshape(T, len(J))[::stride]
    return X, C, j
def consts(X, C, j):
    """프레임별 상수 후보 (frame-height %). y 는 아래로 커진다."""
    ay = X[:, [j["left_ankle"], j["right_ankle"]], 1].copy(); ay[C[:, [j["left_ankle"], j["right_ankle"]]] < 0.3] = np.nan
    hy = X[:, [j["left_hip"], j["right_hip"]], 1].mean(axis=1)
    handy = X[:, [j["left_hand"], j["right_hand"]], 1].copy(); handy[C[:, [j["left_hand"], j["right_hand"]]] < 0.3] = np.nan
    floor = np.nanpercentile(ay, 95); grip = np.nanmin(handy, axis=1)   # 높은 손 = 그립
    return {"낮은발(바닥)": (floor - np.nanmax(ay, 1)) * 100, "높은발(바닥)": (floor - np.nanmin(ay, 1)) * 100, "엉덩이(바닥)": (floor - hy) * 100,
            "낮은발(손기준)": (grip - np.nanmax(ay, 1)) * 100, "엉덩이(손기준)": (grip - hy) * 100}
def angles(d):
    nj = len(d["anglesJointKeys"]); return np.asarray(d["angles"], float).reshape(-1, nj)
out = {}
for motion in ("kip-up", "power-spin", "climb", "peter-pan", "pdshape"):
    rd = D["refs"][f"ref-{motion}"]; rfps = mra.app._reference_angles_fps(rd); cr = rd["clipRange"]
    r0, r1 = int(round(cr["execStartS"] * rfps)), int(round(cr["landEndS"] * rfps)); R = angles(rd); r1 = min(r1, len(R))
    Xr, Cr, jr = kp(rd["referenceKeypointReport"], 1); Kr = consts(Xr, Cr, jr)
    print(f"\n==== {motion}  기준 exec 창 {cr['execStartS']}~{cr['landEndS']}s = 프레임 [{r0},{r1}) / {len(R)}  ({rfps:.2f}fps)")
    rows = {}; info = {}
    for intent in ("correct", "fault"):
        d = D["docs"][f"{motion}/{intent}"]["doc"]; A = angles(d); Xs, Cs, js = kp(d["result"]["keypointReport"], 2); Ks = consts(Xs, Cs, js)
        dev, m = mra.deviate(A, rd)                       # 운영 정렬(짝) — 창 가장자리에만 쓴다
        us = [u + m.start for u, r in m.path if r0 <= r + m.ref_start < r1]
        u0, u1 = (min(us), max(us) + 1) if us else (0, len(A))
        info[intent] = {"score": d["result"]["overallScore"], "student_window": [u0, u1], "n_student": len(A), "dtw": float(m.distance), "dev": dict(zip(JK, map(float, dev)))}
        for k in Ks: rows.setdefault(k, {})[intent] = float(np.nanmedian(Ks[k][u0:u1]))
        for i, jk in enumerate(JK): rows.setdefault(f"각 {jk}", {})[intent] = float(np.median(A[u0:u1, i]))
        for i, jk in enumerate(JK): rows.setdefault(f"[운영 DTW 편차] {jk}", {})[intent] = float(dev[i])
    for k in Kr: rows[k]["ref"] = float(np.nanmedian(Kr[k][r0:r1]))
    for i, jk in enumerate(JK): rows[f"각 {jk}"]["ref"] = float(np.median(R[r0:r1, i]))
    print(f"  학생 창(DTW 로 옮김): 정타 {info['correct']['student_window']}/{info['correct']['n_student']}  실수 {info['fault']['student_window']}/{info['fault']['n_student']}   저장 점수 정타 {info['correct']['score']} 실수 {info['fault']['score']}   DTW dist {info['correct']['dtw']:.1f}/{info['fault']['dtw']:.1f}")
    print(f"  {'축':26s} {'정은지':>7s} {'정타':>7s} {'실수':>7s}   {'정타−정은지':>9s} {'실수−정은지':>9s}   {'분리':>6s}")
    for k, v in rows.items():
        if "ref" in v:
            dc, df = v["correct"] - v["ref"], v["fault"] - v["ref"]; sep = abs(df) - abs(dc)
            flag = " ◀" if abs(sep) >= 5 else ""
            print(f"  {k:26s} {v['ref']:7.1f} {v['correct']:7.1f} {v['fault']:7.1f}   {dc:+9.1f} {df:+9.1f}   {sep:+6.1f}{flag}")
        else:
            print(f"  {k:26s} {'-':>7s} {v['correct']:7.1f} {v['fault']:7.1f}")
    out[motion] = {"info": info, "rows": rows, "ref_window": [r0, r1], "ref_frames": len(R)}
json.dump(out, open(S / "hold5.json", "w"), indent=1, ensure_ascii=False)
