"""uff Task 2 — kip-up 실수 한 편(dacc4467)에서 잰 사실. 운영 창(ig3 헬퍼) + 저장값만. 쓰기 0.

창 = app._reference_exec_window(기준 clipRange) → app._student_window_from_match(운영 DTW match) — 가장자리만.
각도 = app._window_constant_samples (운영 상수 경로와 같은 함수).
높이 = 저장 2D 키포인트(학생 keypointReport 짝수 프레임 = 각도 프레임, 기준 referenceKeypointReport).
  바닥·몸길이 = 각 영상 자기 '창 이전(서 있는) 프레임'의 발목 y · (발목 y − 어깨 y). 단위 = 서 있을 때 몸길이(어깨~발목) 비.
  i38 과의 교차 확인용으로 frame-height %(바닥 = 발목 y p95)도 같이 낸다.
"""
import importlib.util, json, pathlib, sys
import numpy as np

REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("mra", REPO / "backend/scripts/measure_reference_axis.py")
mra = importlib.util.module_from_spec(spec); spec.loader.exec_module(mra)
app = mra.app
JK = list(mra.JOINT_KEYS)

rd = json.load(open(HERE / "ref_doc.json"))
docs = {"fault": json.load(open(HERE / "fault_doc.json")), "correct": json.load(open(HERE / "correct_doc.json"))}
R = np.asarray(rd["angles"], float).reshape(-1, len(rd["anglesJointKeys"]))
assert list(rd["anglesJointKeys"]) == JK, (rd["anglesJointKeys"], JK)
rfps = app._reference_angles_fps(rd)
rwin = app._reference_exec_window(rd, rfps, len(R))
print(f"기준 fps {rfps} · 창 {rwin} / {len(R)} (clipRange {rd['clipRange']['execStartS']}~{rd['clipRange']['landEndS']}s)")


def kp(kr, stride):
    J = kr["joints"]; T = kr["frames"]; j = {n: i for i, n in enumerate(J)}
    X = np.asarray(kr["data"], float).reshape(T, len(J), 2)[::stride]
    C = np.asarray(kr["confidence"], float).reshape(T, len(J))[::stride]
    return X, C, j


def heights(X, C, j, stand):
    """프레임별 높이(양수 = 바닥 위). stand = 서 있는 프레임 슬라이스."""
    def col(name):
        v = X[:, j[name], 1].copy(); v[C[:, j[name]] < 0.3] = np.nan; return v
    la, ra = col("left_ankle"), col("right_ankle")
    ls, rs = col("left_shoulder"), col("right_shoulder")
    lh, rh = col("left_hip"), col("right_hip")
    lw, rw = col("left_hand"), col("right_hand")
    ank = np.vstack([la, ra]).T; sh = np.nanmean(np.vstack([ls, rs]).T, axis=1)
    floor = float(np.nanmedian(np.nanmean(ank[stand], axis=1)))
    body = float(np.nanmedian(np.nanmean(ank[stand], axis=1) - sh[stand]))
    floor95 = float(np.nanpercentile(ank, 95))
    hip = np.nanmean(np.vstack([lh, rh]).T, axis=1)
    grip = np.nanmin(np.vstack([lw, rw]).T, axis=1)            # 높은 손
    out = {
        "낮은발": (floor - np.nanmax(ank, 1)) / body,
        "높은발": (floor - np.nanmin(ank, 1)) / body,
        "엉덩이": (floor - hip) / body,
        "그립손": (floor - grip) / body,
        "낮은발(손 아래)": (grip - np.nanmax(ank, 1)) / body,     # 음수 = 손보다 아래
        "엉덩이(손 아래)": (grip - hip) / body,
        "낮은발 frame%": (floor95 - np.nanmax(ank, 1)) * 100,
        "엉덩이 frame%": (floor95 - hip) * 100,
    }
    left_top = lw < rw                                            # y 아래로 커짐 → 왼손이 위
    both = np.isfinite(lw) & np.isfinite(rw)
    return out, {"floor": floor, "floor95": floor95, "body": body, "left_top": left_top, "both": both}


res = {}
Xr, Cr, jr = kp(rd["referenceKeypointReport"], 1)
r0, r1 = rwin
Hr, meta_r = heights(Xr, Cr, jr, slice(0, r0))
for intent, d in docs.items():
    A = np.asarray(d["angles"], float).reshape(-1, len(d["anglesJointKeys"]))
    assert list(d["anglesJointKeys"]) == JK
    kr = d["result"]["keypointReport"]
    assert kr["frames"] == 2 * len(A), (kr["frames"], len(A))
    dev, match = mra.deviate(A, rd)
    uwin = app._student_window_from_match(match, r0, r1)
    u0, u1 = uwin
    samples = app._window_constant_samples(A, R, uwin, rwin)
    Xs, Cs, js = kp(kr, 2)
    Hs, meta_s = heights(Xs, Cs, js, slice(0, u0))
    ang = {JK[i]: {"student": s[1], "ref": s[2], "diff": s[1] - s[2]} for i, s in samples.items()}
    hgt = {}
    for k in Hs:
        sw, rw_ = Hs[k][u0:u1], Hr[k][r0:r1]
        thirds = []
        for a in range(3):
            ss = sw[len(sw) * a // 3: len(sw) * (a + 1) // 3]; rr = rw_[len(rw_) * a // 3: len(rw_) * (a + 1) // 3]
            thirds.append((float(np.nanmedian(ss)), float(np.nanmedian(rr))))
        below = float(np.nanmean(sw < np.nanmedian(rw_)))
        hgt[k] = {"student": float(np.nanmedian(sw)), "ref": float(np.nanmedian(rw_)), "diff": float(np.nanmedian(sw) - np.nanmedian(rw_)),
                  "thirds": thirds, "frac_student_below_ref_median": below}
    lt_s = float(np.mean(meta_s["left_top"][u0:u1][meta_s["both"][u0:u1]]))
    lt_r = float(np.mean(meta_r["left_top"][r0:r1][meta_r["both"][r0:r1]]))
    res[intent] = {"window_student": [u0, u1], "n_student": len(A), "score": d["result"]["overallScore"], "dtw": float(match.distance),
                   "angles": ang, "heights": hgt, "left_hand_on_top_frac": {"student": lt_s, "ref": lt_r},
                   "stand": {"student": {k: meta_s[k] for k in ("floor", "floor95", "body")}, "ref": {k: meta_r[k] for k in ("floor", "floor95", "body")}},
                   "path_in_window": [[int(u) + int(match.start), int(r) + int(getattr(match, "ref_start", 0) or 0)] for u, r in match.path
                                      if r0 <= int(r) + int(getattr(match, "ref_start", 0) or 0) < r1]}

# ── 게이트 ──
stored = next(r for r in docs["fault"]["result"]["deductionBreakdown"]["records"] if r["criterion"] == "angle_vs_reference__left_shoulder")["measuredValue"]
got = abs(res["fault"]["angles"]["left_shoulder"]["diff"])
print(f"게이트 왼어깨 상수: 재구성 {got:.2f} vs 저장 measuredValue {stored:.2f} → {'PASS' if abs(got - stored) < 0.05 else 'FAIL'}")

for intent in ("correct", "fault"):
    r = res[intent]
    print(f"\n== {intent}  점수 {r['score']}  학생 창 {r['window_student']}/{r['n_student']}  DTW {r['dtw']:.2f}")
    print(f"   서 있을 때: 학생 바닥 y {r['stand']['student']['floor']:.3f} 몸길이 {r['stand']['student']['body']:.3f} | 정은지 바닥 {r['stand']['ref']['floor']:.3f} 몸길이 {r['stand']['ref']['body']:.3f}")
    print(f"   왼손이 위(그립 위 손)인 프레임 비율: 학생 {r['left_hand_on_top_frac']['student']:.2f} · 정은지 {r['left_hand_on_top_frac']['ref']:.2f}")
    print(f"   {'각도':16s} {'학생':>7s} {'정은지':>7s} {'차':>7s}")
    for k, v in r["angles"].items():
        print(f"   {k:16s} {v['student']:7.1f} {v['ref']:7.1f} {v['diff']:+7.1f}")
    print(f"   {'높이(몸길이 비)':16s} {'학생':>7s} {'정은지':>7s} {'차':>7s}   앞/중/뒤 1/3 (학생|정은지)             학생<정은지중앙값")
    for k, v in r["heights"].items():
        th = "  ".join(f"{a:+.2f}|{b:+.2f}" if "frame" not in k else f"{a:+.1f}|{b:+.1f}" for a, b in v["thirds"])
        fmt = "{:7.2f}" if "frame" not in k else "{:7.1f}"
        print(f"   {k:16s} {fmt.format(v['student'])} {fmt.format(v['ref'])} {('{:+7.2f}' if 'frame' not in k else '{:+7.1f}').format(v['diff'])}   {th}   {v['frac_student_below_ref_median']:.2f}")

json.dump(res, open(HERE / "facts.json", "w"), ensure_ascii=False, indent=1, default=float)
