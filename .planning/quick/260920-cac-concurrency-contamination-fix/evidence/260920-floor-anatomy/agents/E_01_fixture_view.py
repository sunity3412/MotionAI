"""E-1 — 리포 fixture 4건(학생측 joints3d 보유)의 시점 기술자 vs 해당 기준.

운영 H.deviate (pipeline/app.py::_deviation_against) 로 편차도 같이 낸다.
"""
import json, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D); sys.path.insert(0, f"{D}/out")
import harness as H, E_view as V

FX = "/Users/kimtaesung/Dev/SunityMotion/backend/evals/realfixture/fixtures"
CASES = [
    ("pdshapeCorrect1785373695",       "ref-pdshape",            "correct"),
    ("kipupFault1785373695",           "ref-kip-up",             "fault"),
    ("elbowtwistsisterFault1785373695","ref-elbow-twist-sister",  "fault"),
    ("powerspinFault1785373695",       "ref-power-spin",         "fault"),
]
refs = H.load_references()
rows = []
print(f"{'case':30s}{'label':8s}{'dev°':>7s}{'gemC.cam_problem':>18s}  descriptors(student | ref | Δ)")
for fn, mid, lab in CASES:
    d = json.load(open(f"{FX}/{fn}.json"))
    r = refs[mid]
    kps, kpr = V.kp_of(d), V.kp_of(r)
    ss, sr = V.summary(kps), V.summary(kpr)
    ua = H.student_matrix({"angles": d["angles"], "keys": d["anglesJointKeys"]})
    dev, match = H.deviate(ua, r)
    sc = H.scalar(dev)
    gc = d.get("geminiC") or {}
    print(f"\n{fn:30s}{lab:8s}{sc:7.2f}{str(gc.get('camera_angle_problematic')):>18s}"
          f"   dtw={match.distance:.1f}")
    for n in V.NAMES:
        print(f"    {n:16s} stu={ss[n]:8.3f}  ref={sr[n]:8.3f}  d={ss[n]-sr[n]:+8.3f}")
    rows.append(dict(case=fn, motion=mid, label=lab, scalar=sc, stu=ss, ref=sr,
                     cam_problem=gc.get("camera_angle_problematic"),
                     occl=gc.get("occlusion_severe"), notes=gc.get("notes_ko")))
json.dump(rows, open(f"{D}/out/E_01_fixture_view.json", "w"), ensure_ascii=False, indent=1)
