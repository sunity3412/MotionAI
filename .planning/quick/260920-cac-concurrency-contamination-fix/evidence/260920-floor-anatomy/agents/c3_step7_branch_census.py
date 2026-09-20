"""C3 step7 — find_action_segment 분기 전수 조사 (875건).

각 분석마다 실제 운영 find_action_segment 를 호출하고, 분기 판정을 운영 상수·
운영 헬퍼(_slide_windows/_window_ambiguous)로 동일하게 재평가해 일치를 검증한다.
"""
from __future__ import annotations
import json, sys, collections, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD

facts = {r["id"]: r for r in json.load(open(f"{D}/facts.json"))}
students = H.load_students(); refs = H.load_references()
cnt = collections.Counter(); cov_all = []; mism = 0; rows = []
t0 = time.time()
for s in students:
    rdoc = refs.get(s["ref"]); f = facts.get(s["id"])
    if rdoc is None or f is None:
        continue
    U = H.student_matrix(s); A = H.ref_matrix(rdoc)
    nu, nr = U.shape[0], A.shape[0]
    rb = H.ref_boundary_of(rdoc)
    Fu, Fr = H.app.feature_vector(U), H.app.feature_vector(A)
    if nu == nr:
        br = "equal_whole"
    elif nu > nr:
        br = "user_slide"
    else:
        cov = nu / nr; cov_all.append(cov)
        if cov < MD.COVERAGE_FLOOR:
            br = "failclosed_coverage"
        else:
            cands = MD._slide_windows(Fr, Fu, 12)
            brs, bd = min(cands, key=lambda c: c[1])
            if MD._window_ambiguous(cands, brs, bd, nu):
                br = "failclosed_ambiguous"
            elif rb is not None and not (brs < rb < brs + nu):
                br = "failclosed_boundary"
            else:
                br = "ref_slide"
    seg = MD.find_action_segment(Fu, Fr, ref_boundary=rb)
    whole = (seg == ((0, nu), (0, nr)))
    pred_whole = br.startswith("failclosed") or br == "equal_whole"
    if whole != pred_whole:
        mism += 1
    cnt[(s["ref"], br)] += 1
    rows.append(dict(id=s["id"], ref=s["ref"], label=f["label"], nu=nu, nr=nr,
                     cov=(nu / nr), branch=br, ref_trimmed=bool(seg[1] != (0, nr)),
                     user_trimmed=bool(seg[0] != (0, nu))))
json.dump(rows, open(f"{D}/out/c3_branch_census.json", "w"))

print(f"전수 {len(rows)}건, 분기 예측-실제 불일치 {mism}건, {time.time()-t0:.0f}s\n")
tot = collections.Counter(r["branch"] for r in rows)
print("== 분기 전수 ==")
for k, v in tot.most_common():
    print(f"  {k:22s} {v:5d}  ({100*v/len(rows):.1f}%)")
print(f"\n  기준(ref) 이 실제로 트리밍된 분석 = {sum(r['ref_trimmed'] for r in rows)} / {len(rows)}")
print(f"  학생(user) 이 실제로 트리밍된 분석 = {sum(r['user_trimmed'] for r in rows)} / {len(rows)}")
c = np.array(cov_all)
print(f"\n  nu<nr 인 {len(c)}건의 coverage: min {c.min():.3f} / 중앙 {np.median(c):.3f} / max {c.max():.3f}"
      f"   (COVERAGE_FLOOR = {MD.COVERAGE_FLOOR})")
print(f"  COVERAGE_FLOOR 통과 = {int((c >= MD.COVERAGE_FLOOR).sum())} 건")
print()
print("== 동작별 분기 ==")
for k in sorted(cnt):
    print(f"  {k[0]:24s} {k[1]:22s} {cnt[k]:5d}")
