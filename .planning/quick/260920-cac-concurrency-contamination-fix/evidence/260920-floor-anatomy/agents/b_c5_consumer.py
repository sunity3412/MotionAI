"""조사 B — 소비처 연결. 편차(도) → 운영 deduction 엔진 → 화면 점수(final).

이 축 하나만 md 에 실어 `deduction_engine.tally` (운영 함수)를 그대로 호출한다.
  criterion  angle_vs_reference__{jk} (8개), tolerance 20.0°, slope 1.2, per-record cap 20,
  execution 집계 cap 40, final = max(25, round(100 + execution_capped)).
real(실제 분석) 과 chance(학생 프레임 셔플 = 시간정보 0) 둘 다 통과시켜 비교한다.
"""
from __future__ import annotations
import json, sys, time
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402
from sunity_shared.analysis import deduction_engine as DE  # noqa: E402


class _Q:  # quantification stub — status ok, notch substrate 없음(reach 미발화)
    quantificationStatus = "ok"


def axis_score(dev):
    md = {f"angle_vs_reference__{jk}": float(d)
          for jk, d in zip(H.JOINT_KEYS, dev) if np.isfinite(d)}
    b = DE.tally(_Q(), None, dimension_overall=100.0, measured_deviations=md,
                 dimension_scores=None, baseline_kind=None)
    pts = sum(abs(r.points) for r in b.records)
    return b.final, pts, len(b.records)


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
    dev, m = H.deviate(M, rdoc)
    f_real, p_real, n_real = axis_score(dev)
    cd = []
    for k in range(SEEDS):
        rng = np.random.default_rng(7000 + k)
        d2, _ = H.deviate(M[rng.permutation(M.shape[0])], rdoc)
        cd.append(d2)
    dev_ch = np.median(np.vstack(cd), axis=0)
    f_ch, p_ch, n_ch = axis_score(dev_ch)
    fa = facts.get(s["id"], {})
    rows.append(dict(id=s["id"], ref=s["ref"], label=fa.get("label", "unknown"),
                     scalar=H.scalar(dev), scalar_ch=H.scalar(dev_ch),
                     dev=[float(x) for x in dev], dev_ch=[float(x) for x in dev_ch],
                     final=f_real, pts=p_real, nrec=n_real,
                     final_ch=f_ch, pts_ch=p_ch, nrec_ch=n_ch,
                     stored_overall=fa.get("overall")))
    if n % 200 == 0:
        print(f"  {n}/{len(students)} {time.time()-t0:.0f}s", flush=True)

json.dump(rows, open(f"{D}/out/b_c5_consumer.json", "w"))
print(f"done {len(rows)} {time.time()-t0:.0f}s\n")

g = {}
for r in rows:
    g.setdefault((r["ref"], r["label"]), []).append(r)
hdr = (f"{'motion':24s} {'label':8s} {'n':>4s} | {'dev':>6s} {'devCh':>6s} {'r/c':>5s} | "
       f"{'rec>20':>6s} {'recCh':>6s} | {'pts':>6s} {'ptsCh':>6s} | {'final':>5s} {'finCh':>5s}")
print(hdr); print("-" * len(hdr))
tbl = []
for (mid, lab), rs in sorted(g.items()):
    med = lambda k: float(np.median([r[k] for r in rs]))
    row = dict(motion=mid, label=lab, n=len(rs), dev=med("scalar"), dev_ch=med("scalar_ch"),
               nrec=med("nrec"), nrec_ch=med("nrec_ch"), pts=med("pts"), pts_ch=med("pts_ch"),
               final=med("final"), final_ch=med("final_ch"))
    tbl.append(row)
    print(f"{mid:24s} {lab:8s} {len(rs):4d} | {row['dev']:6.2f} {row['dev_ch']:6.2f} "
          f"{row['dev']/row['dev_ch']:5.2f} | {row['nrec']:6.1f} {row['nrec_ch']:6.1f} | "
          f"{row['pts']:6.1f} {row['pts_ch']:6.1f} | {row['final']:5.0f} {row['final_ch']:5.0f}")
json.dump(tbl, open(f"{D}/out/b_c5_consumer_table.json", "w"), indent=1)
