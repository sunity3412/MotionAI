"""조사 F 사전탐침 — 운영 builder 1회 호출이 되는지 / facts dev 와 같은지 / 소요시간."""
import sys, time, json
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import numpy as np
import harness as H

facts = {r["id"]: r for r in json.load(open(f"{D}/facts.json"))}
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()

sid = next(i for i, r in facts.items() if r["ref"] == "ref-kip-up" and r["label"] == "correct")
s = students[sid]
rdoc = refs[s["ref"]]
t0 = time.time()
dev, match = H.deviate(H.student_matrix(s), rdoc)
t1 = time.time()
print("deviate", round(t1 - t0, 2), "s")
print("facts dev :", [round(x, 3) for x in facts[sid]["dev"]])
print("fresh dev :", [round(float(x), 3) for x in dev])

# 운영 builder 호출 (profile=None — 이 축 단독 격리)
md_err = {}
md = H.app._build_deduction_measured_deviations(
    angles=H.student_matrix(s), profile=None, assessments=None,
    dimension_scores=None, quantification=None,
    reference_dtw_match=match,
    reference_angles=np.asarray(rdoc["angles"], dtype=float),
    ref_fps=H.ref_fps_of(rdoc),
    measurement_error_out=md_err,
)
print("builder t", round(time.time() - t1, 2), "s")
print("md:", {k: round(v, 2) for k, v in md.items() if isinstance(v, float)})
print("measurement_error:", {k: tuple(round(float(x), 2) for x in v) for k, v in md_err.items()})
