"""C3 step2/3/4 — 정렬 파괴 대조군 + find_action_segment 분기 계측 + ref-경계 마스크.

전부 운영 함수 호출. 새로 구현한 것은 '경로(path)'뿐이고, 편차 산출은
motiondtw.per_joint_deviation (운영 함수) 에 그대로 넘긴다.

대조 조건
  dtw       : 운영 그대로 (_deviation_against → motion_dtw → per_joint_deviation)
  ident     : 같은 window, DTW 없이 선형 시간 대응 (u -> round(u*(nr-1)/(nu-1)))
  rev_ident : 같은 window, 선형 대응을 기준 시간축 역순으로
  dtw_rev   : 기준 시퀀스를 통째로 뒤집어 다시 정렬 (운영 _deviation_against 재호출)
  shuf      : 같은 window, 기준 프레임을 균일 무작위로 짝 (시간정보 0) — 5 seed 평균
"""
from __future__ import annotations
import json, sys, collections, time
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H
from sunity_shared.analysis import motiondtw as MD

rows = {r["id"]: r for r in json.load(open(f"{D}/facts.json"))}
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()

# (ref,label,vk) 그룹당 대표 1건
groups = collections.defaultdict(list)
for r in rows.values():
    groups[(r["ref"], r["label"], r["vk"])].append(r["id"])
reps = {k: sorted(v)[0] for k, v in groups.items()}

def linear_path(nu, nr, reverse=False):
    if nu == 1:
        js = [0]
    else:
        js = [int(round(u * (nr - 1) / (nu - 1))) for u in range(nu)]
    if reverse:
        js = [nr - 1 - j for j in js]
    return [(u, js[u]) for u in range(nu)]

out = []
t0 = time.time()
for k in sorted(reps, key=lambda x: (x[0], x[1], str(x[2]))):
    ref_id, label, vk = k
    aid = reps[k]
    s = students[aid]
    rdoc = refs.get(ref_id)
    if rdoc is None:
        continue
    U = H.student_matrix(s)
    A_ref = H.ref_matrix(rdoc)
    ref_fps = H.ref_fps_of(rdoc)
    ref_b = H.ref_boundary_of(rdoc)

    # --- (a) 운영 그대로 ---
    dev_a, m = H.deviate(U, rdoc)
    u_seg = U[m.start:m.end]
    a_win = A_ref[m.ref_start:m.ref_end]
    nu, nr = a_win.shape[0] if False else u_seg.shape[0], a_win.shape[0]

    # --- step4: ref-경계 마스크가 버리는 스텝 비율 (운영 함수) ---
    mask = MD.ref_boundary_step_mask(m.path, nr, ref_fps) if ref_fps else None
    if mask is None:
        kept, floor, applied = len(m.path), 0, False
    else:
        kept = int(mask.sum()); floor = MD._boundary_keep_floor(len(m.path))
        applied = kept >= floor

    # --- step3: find_action_segment 분기 계측 (운영 상수/함수로 판정) ---
    nu_full, nr_full = U.shape[0], A_ref.shape[0]
    Fu, Fr = H.app.feature_vector(U), H.app.feature_vector(A_ref)
    if nu_full == nr_full:
        branch = "equal_whole"; amb = None; cov = 1.0
    elif nu_full > nr_full:
        branch = "user_slide"; amb = None; cov = float("nan")
    else:
        cov = nu_full / nr_full
        if cov < MD.COVERAGE_FLOOR:
            branch = "failclosed_coverage"; amb = None
        else:
            cands = MD._slide_windows(Fr, Fu, 12)
            best_rs, best_d = min(cands, key=lambda c: c[1])
            amb = MD._window_ambiguous(cands, best_rs, best_d, nu_full)
            if amb:
                branch = "failclosed_ambiguous"
            elif ref_b is not None and not (best_rs < ref_b < best_rs + nu_full):
                branch = "failclosed_boundary"
            else:
                branch = "ref_slide"
    # 분기 판정이 실제 반환과 일치하는지 검증
    seg = MD.find_action_segment(Fu, Fr, ref_boundary=ref_b)
    actual_whole = (seg == ((0, nu_full), (0, nr_full)))
    pred_whole = branch.startswith("failclosed") or branch == "equal_whole"
    agree = (actual_whole == pred_whole)

    # --- (b~e) 대조군 ---
    p_id = linear_path(nu, nr)
    p_rv = linear_path(nu, nr, reverse=True)
    dev_id = MD.per_joint_deviation(p_id, u_seg, a_win, ref_fps=ref_fps)
    dev_rv = MD.per_joint_deviation(p_rv, u_seg, a_win, ref_fps=ref_fps)
    dev_dr, m_dr = H.deviate(U, A_ref[::-1].copy(), ref_boundary=None, ref_fps=ref_fps)
    shuf = []
    for seed in range(5):
        rng = np.random.default_rng(seed)
        p_sh = [(u, int(rng.integers(0, nr))) for u in range(nu)]
        shuf.append(H.scalar(MD.per_joint_deviation(p_sh, u_seg, a_win, ref_fps=ref_fps)))

    out.append(dict(
        ref=ref_id, label=label, vk=vk, aid=aid, n_group=len(groups[k]),
        nu_full=nu_full, nr_full=nr_full, coverage=cov, branch=branch,
        ambiguous=amb, agree=bool(agree), ref_boundary=ref_b, ref_fps=ref_fps,
        plen=len(m.path), kept=kept, drop_pct=100.0 * (1 - kept / max(len(m.path), 1)),
        floor=floor, mask_applied=bool(applied),
        dtw_dist=float(m.distance), dtw_rev_dist=float(m_dr.distance),
        dev_dtw=H.scalar(dev_a), dev_ident=H.scalar(dev_id),
        dev_rev_ident=H.scalar(dev_rv), dev_dtw_rev=H.scalar(dev_dr),
        dev_shuf=float(np.mean(shuf)), dev_shuf_sd=float(np.std(shuf)),
    ))
    print(f"  {ref_id:24s}{label:8s} {branch:22s} done {time.time()-t0:.0f}s", flush=True)

json.dump(out, open(f"{D}/out/c3_controls.json", "w"), indent=1)
print(f"\n{len(out)} groups, {time.time()-t0:.0f}s")
