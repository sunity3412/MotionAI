"""E-2 — DTW 로 짝지어진 프레임쌍 위에서 시점 기술자 불일치를 잰다.

왜 짝쌍인가: 같은 동작의 같은 순간끼리 비교하면 '자세가 달라서 생긴 기술자 차이'가
줄고, 카메라(=투영 방위)처럼 클립 전체에 걸린 계통 차이만 남는다.
  · 계통 성분 = 짝쌍 log 비의 중앙값  (카메라/봉 주위 방위 같은 지속 차이)
  · 산포 성분 = 짝쌍 log 비의 IQR     (자세 차이로 생기는 흔들림)

짝쌍은 운영 _deviation_against 가 돌려준 match.path 를 그대로 쓴다(재구현 0).
"""
import json, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D); sys.path.insert(0, f"{D}/out")
import harness as H, E_view as V

FX = "/Users/kimtaesung/Dev/SunityMotion/backend/evals/realfixture/fixtures"
CASES = [
    ("pdshapeCorrect1785373695",        "ref-pdshape",            "correct"),
    ("kipupFault1785373695",            "ref-kip-up",             "fault"),
    ("elbowtwistsisterFault1785373695", "ref-elbow-twist-sister", "fault"),
    ("powerspinFault1785373695",        "ref-power-spin",         "fault"),
]
# §13/오늘 표의 라이브 correct 바닥 (동작별)
LIVE_CORRECT = {"ref-pdshape": 24.3, "ref-kip-up": 2.8,
                "ref-elbow-twist-sister": 22.2, "ref-power-spin": 7.5}
LIVE_FAULT = {"ref-pdshape": 23.0, "ref-kip-up": 8.8,
              "ref-elbow-twist-sister": 23.6, "ref-power-spin": 20.1}

refs = H.load_references()
rows = []
for fn, mid, lab in CASES:
    d = json.load(open(f"{FX}/{fn}.json"))
    r = refs[mid]
    ds = V.descriptors(V.kp_of(d))
    dr = V.descriptors(V.kp_of(r))
    ua = H.student_matrix({"angles": d["angles"], "keys": d["anglesJointKeys"]})
    dev, m = H.deviate(ua, r)
    path = np.asarray(m.path, dtype=int)
    ui = m.start + path[:, 0]
    ri = m.ref_start + path[:, 1]
    rec = dict(case=fn, motion=mid, label=lab, dev=H.scalar(dev), dtw=float(m.distance),
               npairs=int(len(path)),
               live_correct=LIVE_CORRECT[mid], live_fault=LIVE_FAULT[mid])
    for k in ("sw_torso", "hw_torso", "ear_torso"):
        a, b = ds[k][ui], dr[k][ri]
        ok = np.isfinite(a) & np.isfinite(b) & (a > 1e-6) & (b > 1e-6)
        lr = np.log(a[ok] / b[ok])
        rec[f"{k}_sysdex"] = float(np.median(lr))           # 계통(카메라형)
        rec[f"{k}_iqr"] = float(np.percentile(lr, 75) - np.percentile(lr, 25))  # 산포(자세형)
    for k in ("body_tilt_deg", "sh_axis_deg"):
        a, b = ds[k][ui], dr[k][ri]
        ok = np.isfinite(a) & np.isfinite(b)
        rec[f"{k}_sysdeg"] = float(np.median(a[ok] - b[ok]))
        rec[f"{k}_iqrdeg"] = float(np.percentile(a[ok] - b[ok], 75) - np.percentile(a[ok] - b[ok], 25))
    for k in ("lr_uparm", "lr_forearm", "lr_thigh", "lr_shank"):
        a, b = ds[k][ui], dr[k][ri]
        ok = np.isfinite(a) & np.isfinite(b)
        rec[f"{k}_sys"] = float(np.median(a[ok] - b[ok]))
    rows.append(rec)

H_ = ("case", "label", "dev", "dtw", "sw_torso_sysdex", "sw_torso_iqr",
      "hw_torso_sysdex", "body_tilt_deg_sysdeg", "sh_axis_deg_sysdeg", "ear_torso_sysdex")
print(f"{'case':22s}{'lab':8s}{'dev°':>7s}{'dtw':>7s}{'sw_sys':>9s}{'sw_iqr':>9s}"
      f"{'hw_sys':>9s}{'tilt_sys':>10s}{'shax_sys':>10s}{'ear_sys':>9s}")
for r_ in rows:
    print(f"{r_['case'][:20]:22s}{r_['label']:8s}{r_['dev']:7.2f}{r_['dtw']:7.1f}"
          f"{r_['sw_torso_sysdex']:9.3f}{r_['sw_torso_iqr']:9.3f}{r_['hw_torso_sysdex']:9.3f}"
          f"{r_['body_tilt_deg_sysdeg']:10.2f}{r_['sh_axis_deg_sysdeg']:10.2f}{r_['ear_torso_sysdex']:9.3f}")

# 복합 시점 불일치 = 계통 성분들의 크기 합 (스케일 맞춤: 각도는 /30 도)
for r_ in rows:
    r_["view_mismatch"] = (abs(r_["sw_torso_sysdex"]) + abs(r_["hw_torso_sysdex"])
                           + abs(r_["ear_torso_sysdex"])
                           + abs(r_["body_tilt_deg_sysdeg"]) / 30.0
                           + abs(r_["sh_axis_deg_sysdeg"]) / 30.0)
print()
print(f"{'case':22s}{'view_mismatch':>15s}{'dev°':>8s}{'live_correct':>14s}{'live_fault':>12s}")
for r_ in sorted(rows, key=lambda x: -x["view_mismatch"]):
    print(f"{r_['case'][:20]:22s}{r_['view_mismatch']:15.3f}{r_['dev']:8.2f}"
          f"{r_['live_correct']:14.1f}{r_['live_fault']:12.1f}")


def spearman(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    ra = ra - ra.mean(); rb = rb - rb.mean()
    return float((ra @ rb) / np.sqrt((ra @ ra) * (rb @ rb)))


vm = np.array([r_["view_mismatch"] for r_ in rows])
print()
print("Spearman(view_mismatch, fixture dev)      n=4:", round(spearman(vm, [r_["dev"] for r_ in rows]), 3))
print("Spearman(view_mismatch, live correct floor) n=4:", round(spearman(vm, [r_["live_correct"] for r_ in rows]), 3))
print("Spearman(view_mismatch, live fault  floor) n=4:", round(spearman(vm, [r_["live_fault"] for r_ in rows]), 3))
f3 = [r_ for r_ in rows if r_["label"] == "fault"]
print("fault-only n=3 Spearman(view_mismatch, dev):",
      round(spearman([r_["view_mismatch"] for r_ in f3], [r_["dev"] for r_ in f3]), 3))
json.dump(rows, open(f"{D}/out/E_02_matched_pairs.json", "w"), ensure_ascii=False, indent=1)
