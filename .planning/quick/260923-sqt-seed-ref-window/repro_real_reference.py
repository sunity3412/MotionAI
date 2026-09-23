"""재현: 기준 창이 0 이 아닐 때 감점 seed 가 기준의 엉뚱한 프레임과 비교하는가.

학생 = 정은지 기준 영상 자신의 뒷부분(앞 k 프레임을 잘라낸 것). 같은 영상이므로
올바른 정렬이면 편차 0 이어야 한다. 운영 경로 그대로 호출:
  _deviation_against  ->  match(ref_start=k), a_ref(전체)
  _build_deduction_measured_deviations(reference_dtw_match=match, reference_angles=a_ref)
"""
import importlib.util, pathlib, sys
import numpy as np

REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend/shared/python"))
spec = importlib.util.spec_from_file_location("pipeapp", str(REPO / "backend/functions/pipeline/app.py"))
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
from sunity_shared.analysis import skeleton, technique, vision_veto

import firebase_admin
from firebase_admin import credentials, firestore
firebase_admin.initialize_app(credentials.Certificate(str(REPO / "firebase-sa.json")))
db = firestore.client()

JK = list(skeleton.JOINT_KEYS)
prof = technique.TechniqueProfile(name="미등록", category="unknown", joint_expectations={})
quant = vision_veto.VisionQuantificationResult(
    quantificationStatus="available", angleDeltas=None, bodyRelativeNotches=None,
    windowMedianAngleDeltas=None, warnings=())

for mid in ("ref-kip-up", "ref-power-spin", "ref-climb"):
    rd = db.document(f"reference/{mid}").get().to_dict()
    nj = len(rd["anglesJointKeys"])
    R = np.asarray(rd["angles"], float).reshape(-1, nj)
    fps = app._reference_angles_fps(rd) or None
    nr = len(R)
    for k in (int(nr * 0.10), int(nr * 0.15)):
        S = R[k:].copy()                     # 학생 = 기준 영상의 뒷부분 (nu/nr >= 0.8)
        dev, m, _seg, a_ref = app._deviation_against(S, rd["angles"], nj, ref_fps=fps)
        md = app._build_deduction_measured_deviations(
            angles=S, profile=prof, assessments=[], dimension_scores={},
            quantification=quant, reference_dtw_match=m, reference_angles=a_ref,
            ref_fps=fps,
        )
        seed = {j: md.get(f"angle_vs_reference__{j}", 0.0) for j in JK}
        print(f"{mid:16s} 앞 {k:3d}프레임 절단  nu/nr={len(S)/nr:.2f}  창=[{m.ref_start},{m.ref_end})  "
              f"점수경로 편차 최대 {float(np.max(dev)):.1f}도 | 감점 seed 최대 {max(seed.values()):.1f}도")
        worst = sorted(seed.items(), key=lambda kv: -kv[1])[:3]
        print("      감점 seed 상위:", ", ".join(f"{j} {v:.1f}" for j, v in worst))

# ── 소비처까지: 감점 엔진 → 최종 점수 ──
from sunity_shared.analysis import deduction_engine
print("\n--- 소비처(감점 엔진 → 점수) ---")
for mid in ("ref-kip-up", "ref-power-spin", "ref-climb"):
    rd = db.document(f"reference/{mid}").get().to_dict()
    nj = len(rd["anglesJointKeys"])
    R = np.asarray(rd["angles"], float).reshape(-1, nj)
    fps = app._reference_angles_fps(rd) or None
    k = int(len(R) * 0.15)
    S = R[k:].copy()
    dev, m, _seg, a_ref = app._deviation_against(S, rd["angles"], nj, ref_fps=fps)
    for label, ref_arr in (("운영(전체 배열)", a_ref), ("창 슬라이스", a_ref[m.ref_start:m.ref_end])):
        me = {}
        md = app._build_deduction_measured_deviations(
            angles=S, profile=prof, assessments=[], dimension_scores={},
            quantification=quant, reference_dtw_match=m, reference_angles=ref_arr,
            ref_fps=fps, measurement_error_out=me,
        )
        bd = deduction_engine.tally(quant, None, dimension_overall=100, measured_deviations=md,
                                    dimension_scores={}, baseline_kind="floor", measurement_error=me)
        recs = [(r.criterion if hasattr(r, "criterion") else r.get("criterion"),
                 round(float(getattr(r, "deduction", 0) or 0), 1)) for r in bd.records]
        sup = len(getattr(bd, "suppressed_records", []) or [])
        print(f"{mid:16s} 창=[{m.ref_start},{m.ref_end}) {label:14s} 최종 {bd.final}  감점 {recs}  억제 {sup}건")
