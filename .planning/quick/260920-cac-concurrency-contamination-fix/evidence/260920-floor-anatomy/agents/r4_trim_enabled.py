"""R4 — c3 가 [미확인]으로 남긴 구멍을 직접 판다.

c3 확정 사실: COVERAGE_FLOOR(0.80) 통과 0/856 → 라이브에서 기준 트리밍은 한 번도
안 걸렸다. 즉 **정렬 1단계(구간 탐색)가 사실상 사문**이고, c3 의 oracle/대조군은
전부 그 사문 상태의 window(학생 통째 vs 기준 통째) 위에서만 쟀다.

그러면 c3 의 결론 "정렬은 바닥을 설명 못 한다"는 '트리밍이 꺼진 정렬'에 대한
결론일 뿐일 수 있다. 여기서 그 게이트를 열어본다:
  slide_op   : COVERAGE_FLOOR 만 무력화하고 나머지는 운영 그대로 —
               _slide_windows(F_ref, F_user) 로 기준 window 선택(운영 선택자),
               운영 dtw + per_joint_deviation.
  slide_orc  : 모든 기준 window 시작점을 훑어 **결과 스칼라가 최소**인 window
               (트리밍이 벌 수 있는 최대치, 결과로 고름 — 커브핏이 아니라 상한 측정).
  both_orc   : 학생도 같이 트리밍 — 길이 L in {0.6,0.7,0.8,0.9}*nu, 시작점 격자
               스윕해서 스칼라 최소 (정렬 1단계가 낼 수 있는 최대치의 근사 상한).
편차는 전부 운영 motiondtw.per_joint_deviation / dtw 호출.
"""
from __future__ import annotations
import json, sys, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD
from sunity_shared.analysis.features import feature_vector

ctrl = json.load(open(f"{D}/out/c3_controls.json"))
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()
FLOORS = [("ref-sideway-spin","self"),("ref-kip-up","correct"),("ref-peter-pan","correct"),
          ("ref-power-spin","correct"),("ref-climb","correct"),("ref-combo","correct"),
          ("ref-invert","self"),("ref-foxtop","self"),("ref-foxtop-split","self"),
          ("ref-elbow-twist-sister","correct"),("ref-pdshape","correct")]

def pick(ref_id, label):
    cand = [c for c in ctrl if c["ref"] == ref_id and c["label"] == label]
    named = [c for c in cand if c["vk"]]
    return (named or cand)[0] if cand else None

rows = []
t0 = time.time()
for ref_id, label in FLOORS:
    base = pick(ref_id, label)
    s = students[base["aid"]]; rdoc = refs[ref_id]
    U = H.student_matrix(s); A = H.ref_matrix(rdoc); fps = H.ref_fps_of(rdoc)
    dev_op, m = H.deviate(U, rdoc)
    s_op = H.scalar(dev_op)
    FU, FA = feature_vector(U), feature_vector(A)
    nu, nr = len(U), len(A)

    def eval_win(us, ue, rs, re):
        d, p = MD.dtw(FU[us:ue], FA[rs:re], radius=12)
        return H.scalar(MD.per_joint_deviation(p, U[us:ue], A[rs:re], ref_fps=fps)), d

    # slide_op — 운영 선택자(_slide_windows 최소 DTW 거리)로 기준 window
    cands = MD._slide_windows(FA, FU, 12)
    best_rs, best_d = min(cands, key=lambda c: c[1])
    s_slide_op, _ = eval_win(0, nu, best_rs, best_rs + nu)
    amb = MD._window_ambiguous(cands, best_rs, best_d, nu)

    # slide_orc — 결과 최소 window (트리밍 상한)
    best = (np.inf, None)
    step = max(1, (nr - nu) // 60)
    for rs in range(0, nr - nu + 1, step):
        v, _ = eval_win(0, nu, rs, rs + nu)
        if v < best[0]:
            best = (v, rs)
    s_slide_orc, orc_rs = best

    # both_orc — 학생도 트리밍
    best2 = (np.inf, None)
    for frac in (0.6, 0.7, 0.8, 0.9):
        L = max(8, int(nu * frac))
        ustep = max(1, (nu - L) // 8) if nu > L else 1
        rstep = max(1, (nr - L) // 12) if nr > L else 1
        for us in range(0, nu - L + 1, ustep):
            for rs in range(0, nr - L + 1, rstep):
                v, _ = eval_win(us, us + L, rs, rs + L)
                if v < best2[0]:
                    best2 = (v, (frac, us, rs))
    s_both, both_at = best2

    rows.append(dict(ref=ref_id, label=label, nu=nu, nr=nr, coverage=nu/nr, op=s_op,
                     slide_op=s_slide_op, slide_op_rs=int(best_rs), ambiguous=bool(amb),
                     slide_orc=s_slide_orc, slide_orc_rs=int(orc_rs),
                     both_orc=s_both, both_at=both_at))
    print(f"  {ref_id:24s}{label:8s} cov={nu/nr:.3f} op={s_op:6.2f} slide_op={s_slide_op:6.2f}"
          f"(rs={best_rs},amb={amb}) slide_orc={s_slide_orc:6.2f} both_orc={s_both:6.2f}"
          f"  {time.time()-t0:5.0f}s", flush=True)

json.dump(rows, open(f"{D}/out/r4_trim.json", "w"), indent=1)
print()
print("== 막혀 있던 트리밍 경로를 열면 바닥이 내려가나 ==")
print(f"{'motion':24s}{'lab':6s}{'cov':>6s}{'운영':>7s}{'운영선택자로트림':>12s}{'트림상한':>9s}{'양쪽트림상한':>11s}{'상한대비몫%':>11s}")
for r in rows:
    print(f"{r['ref']:24s}{r['label']:6s}{r['coverage']:>6.3f}{r['op']:>7.1f}{r['slide_op']:>12.1f}"
          f"{r['slide_orc']:>9.1f}{r['both_orc']:>11.1f}{100*(r['op']-r['both_orc'])/r['op']:>11.0f}")
