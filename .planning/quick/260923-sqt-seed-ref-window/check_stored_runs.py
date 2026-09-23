"""감점 seed 의 기준 창 인덱싱 확인 (읽기 전용, 운영 함수 호출만).

가설: _build_deduction_measured_deviations 의 DTW fallback 이 window-local path 로
**전체** 기준 배열을 인덱싱한다 -> ref_start>0 이면 기준의 엉뚱한 프레임과 비교.
판정 재료: (1) 실제 분석에서 ref_start>0 이 나오는가 (2) 그때 저장된 감점 measuredValue 가
'전체 배열' 계산과 일치하는가 '창 슬라이스' 계산과 일치하는가.
"""
import importlib.util, json, pathlib, sys
import numpy as np

REPO = pathlib.Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend/shared/python"))
spec = importlib.util.spec_from_file_location("pipeapp", str(REPO / "backend/functions/pipeline/app.py"))
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
from sunity_shared.analysis import motiondtw, segments, skeleton

import firebase_admin
from firebase_admin import credentials, firestore
firebase_admin.initialize_app(credentials.Certificate(str(REPO / "firebase-sa.json")))
db = firestore.client()

RUNS = [  # 2026-09-22 gnj 런 (지난 세션 transcript 에서 복원)
    ("hohsgAIG1GSGvR9GRUtdgxYHBzT2", "9fbe0cab92ec4c26a0e65d2c83151eae"),
    ("1Zx7HJJT7ddl97ggQ2U7QIMN9Sk1", "9fd006aa9ddc427989fc2e5333e906ab"),
    ("PxM3cZkUvVSxcGbBDswtARLEYIK2", "c59042f4bc3f45c8a3ca5310a3d92d65"),
    ("MJ93ILDBESPUM14QmHQ6Q1T45gn1", "d44ddb0cf47f4ee2b9a1809b95153e19"),
    ("3tF01LOYZYRiMCQyNBrRhizJm212", "e28c760cc8ad42999f5dde9fd3c33a84"),
    ("tIftxhf1J5UNOAxWV7ljzS2gunl2", "027817a635e2480eb20755a283dd8fef"),
    ("vI6Bjq1K8uONW807tXWIO774AKB3", "8f5510aa9ae547c8a7d0265eb9679ef2"),
    ("KAi6p4ubcfVMvo8TfvytTkzNp0j2", "e83811d3cc484887b0aef315346f8aae"),
    ("FQVENFYcElbLPo8ukylcc2D5il43", "b468337d704a4b73b187f69c5798ff70"),
    ("0Vab2WWwRIUtACG2q802xbogOb02", "d023d584779348a8922464486090b50a"),
    ("16WrOWwza8gJzF6JRIL0FaxPrz93", "0d43112933134c30a4db352724f74ee8"),
]
JK = list(skeleton.JOINT_KEYS)
refs = {}
out = []
for uid, aid in RUNS:
    d = db.document(f"users/{uid}/analyses/{aid}").get().to_dict() or {}
    r = d.get("result") or {}
    pick = lambda k: r.get(k) if r.get(k) is not None else d.get(k)
    keys, flat = pick("anglesJointKeys"), pick("angles")
    mref = d.get("referenceMotionId")
    if not flat or not mref:
        print(aid[:8], "angles/ref 없음", d.get("status")); continue
    S = np.asarray(flat, float).reshape(-1, len(keys))
    if mref not in refs:
        refs[mref] = db.document(f"reference/{mref}").get().to_dict() or {}
    rd = refs[mref]
    nj = len(rd.get("anglesJointKeys") or []) or skeleton.NUM_JOINTS
    rb = None
    if rd.get("sharedBaseMotionId") and rd.get("baseUntilS") is not None and rd.get("clipRange"):
        rb = segments.ref_boundary_frame(rd["clipRange"], rd["baseUntilS"], len(rd["angles"]) // nj)
    fps = app._reference_angles_fps(rd) or None
    dev_win, m, useg, a_ref = app._deviation_against(S, rd["angles"], nj, ref_boundary=rb, ref_fps=fps)
    # 운영 seed builder 와 같은 호출(전체 a_ref)
    dev_full = motiondtw.per_joint_deviation(m.path, S[m.start:m.end], a_ref, ref_fps=fps)
    recs = ((r.get("deductionBreakdown") or {}).get("records")) or []
    stored = {}
    for rec in recs:
        cid = rec.get("criterion") or rec.get("criterionId") or ""
        if str(cid).startswith("angle_vs_reference__"):
            stored[cid.split("__", 1)[1]] = rec.get("measuredValue")
    seed_obs = r.get("seedObservation") or {}
    row = dict(aid=aid[:8], ref=mref, nu=len(S), nr=len(a_ref), start=m.start, end=m.end,
               ref_start=m.ref_start, ref_end=m.ref_end, dist=round(m.distance, 2),
               score=r.get("overallScore"),
               win={k: round(float(v), 1) for k, v in zip(JK, dev_win)},
               full={k: round(float(v), 1) for k, v in zip(JK, dev_full)},
               stored=stored, seedObs={k: seed_obs.get(k) for k in ("window_joints", "fallback_joints")})
    out.append(row)
    print(f"{aid[:8]} {mref:22s} nu={len(S):4d} nr={len(a_ref):4d} user=[{m.start},{m.end}) "
          f"ref=[{m.ref_start},{m.ref_end}) dist={m.distance:6.2f} score={r.get('overallScore')}")
    if m.ref_start > 0:
        for k in JK:
            a, b = float(dev_win[JK.index(k)]), float(dev_full[JK.index(k)])
            print(f"     {k:16s} 창={a:6.1f}  전체배열={b:6.1f}  저장={stored.get(k)}")
    elif stored:
        print("     저장 measuredValue:", stored, " 창계산:", {k: round(float(dev_win[JK.index(k)]),1) for k in stored})
json.dump(out, open(pathlib.Path(__file__).with_suffix(".json"), "w"), ensure_ascii=False, indent=1)
