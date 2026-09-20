"""조사 B — 소비처 (운영 배선 그대로: builder + measurement_error CI 억제 + tally).

app.py 운영 경로와 같은 두 함수를 직접 호출한다 — 재구현 0.
  _build_deduction_measured_deviations(...)  → md + measurement_error_out(CI)
  deduction_engine.tally(..., measurement_error=...) → records/final

주의(운영 사실): builder 는 `reference_angles` 로 **전체 a_ref** 를 받고 path 는
window-local 이다(app.py:8267 reference_angles_for_veto = a_ref). 여기서도 똑같이 준다.
profile=None → expects_extension 차단 없음 = 8관절 전부 방출(이 축 단독 상한).
"""
from __future__ import annotations
import json, sys, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402
from harness import app  # noqa: E402
from sunity_shared.analysis import deduction_engine as DE  # noqa: E402


class _Q:
    quantificationStatus = "ok"


def axis_consume(user_angles, rdoc):
    """운영 두 함수 호출 → (dev, final, points, n_records, n_suppressed)."""
    a_ref = H.ref_matrix(rdoc)
    ref_fps = H.ref_fps_of(rdoc)
    dev, match, user_seg, a_ref_full = app._deviation_against(
        np.asarray(user_angles, float), a_ref.reshape(-1), a_ref.shape[1],
        ref_boundary=H.ref_boundary_of(rdoc), ref_fps=ref_fps,
    )
    me: dict = {}
    md = app._build_deduction_measured_deviations(
        angles=np.asarray(user_angles, float), profile=None, assessments=None,
        dimension_scores=None, quantification=None,
        reference_dtw_match=match, reference_angles=a_ref_full,
        measurement_error_out=me, ref_fps=ref_fps,
    )
    md = {k: v for k, v in (md or {}).items() if k.startswith("angle_vs_reference__")}
    b = DE.tally(_Q(), None, dimension_overall=100.0, measured_deviations=md,
                 dimension_scores=None, baseline_kind=None, measurement_error=me)
    pts = sum(abs(r.points) for r in b.records)
    return (np.asarray(dev, float), b.final, pts, len(b.records),
            len(b.suppressed_records), md, me)


students = H.load_students()
refs = H.load_references()
facts = {f["id"]: f for f in json.load(open(f"{D}/facts.json"))}

SEEDS = 4
rows = []
t0 = time.time()
for n, s in enumerate(students):
    rdoc = refs.get(s["ref"])
    if rdoc is None:
        continue
    M = H.student_matrix(s)
    dev, fin, pts, nrec, nsup, md, me = axis_consume(M, rdoc)
    # chance — 학생 프레임 셔플(시간정보 0), 같은 소비 경로
    chs = []
    for k in range(SEEDS):
        rng = np.random.default_rng(7000 + k)
        d2, f2, p2, r2, s2, _, _ = axis_consume(M[rng.permutation(M.shape[0])], rdoc)
        chs.append((H.scalar(d2), f2, p2, r2, s2))
    fa = facts.get(s["id"], {})
    rows.append(dict(
        id=s["id"], ref=s["ref"], label=fa.get("label", "unknown"),
        scalar=H.scalar(dev), final=fin, pts=pts, nrec=nrec, nsup=nsup,
        nmd=len(md),
        scalar_ch=float(np.median([c[0] for c in chs])),
        final_ch=float(np.median([c[1] for c in chs])),
        pts_ch=float(np.median([c[2] for c in chs])),
        nrec_ch=float(np.median([c[3] for c in chs])),
        nsup_ch=float(np.median([c[4] for c in chs])),
        stored_overall=fa.get("overall"),
    ))
    if n % 200 == 0:
        print(f"  {n}/{len(students)} {time.time()-t0:.0f}s", flush=True)

json.dump(rows, open(f"{D}/out/b_c5_consumer_ci.json", "w"))
print(f"done {len(rows)} {time.time()-t0:.0f}s\n")

g = {}
for r in rows:
    g.setdefault((r["ref"], r["label"]), []).append(r)
hdr = (f"{'motion':24s} {'label':8s} {'n':>4s} | {'dev':>6s} {'devCh':>6s} | "
       f"{'rec':>4s} {'sup':>4s} {'pts':>6s} {'FIN':>4s} | "
       f"{'recCh':>5s} {'supCh':>5s} {'ptsCh':>6s} {'FINch':>5s} | {'stored':>6s}")
print(hdr); print("-" * len(hdr))
tbl = []
for (mid, lab), rs in sorted(g.items()):
    med = lambda k: float(np.median([r[k] for r in rs if r[k] is not None])) if any(
        r[k] is not None for r in rs) else float("nan")
    row = dict(motion=mid, label=lab, n=len(rs), dev=med("scalar"), dev_ch=med("scalar_ch"),
               nrec=med("nrec"), nsup=med("nsup"), pts=med("pts"), final=med("final"),
               nrec_ch=med("nrec_ch"), nsup_ch=med("nsup_ch"), pts_ch=med("pts_ch"),
               final_ch=med("final_ch"), stored=med("stored_overall"))
    tbl.append(row)
    print(f"{mid:24s} {lab:8s} {len(rs):4d} | {row['dev']:6.2f} {row['dev_ch']:6.2f} | "
          f"{row['nrec']:4.0f} {row['nsup']:4.0f} {row['pts']:6.1f} {row['final']:4.0f} | "
          f"{row['nrec_ch']:5.0f} {row['nsup_ch']:5.0f} {row['pts_ch']:6.1f} {row['final_ch']:5.0f} | "
          f"{row['stored']:6.0f}")
json.dump(tbl, open(f"{D}/out/b_c5_consumer_ci_table.json", "w"), indent=1)
