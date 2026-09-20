import json, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
c = json.load(open(f"{D}/out/c3_controls.json"))

print("== 3. find_action_segment 분기 (대표 47군, 라이브 875건 전수 커버) ==")
br = collections.Counter((r["branch"], r["agree"]) for r in c)
for k, v in br.items():
    print(f"  {k[0]:22s} agree={k[1]}  groups={v}  (analyses={sum(x['n_group'] for x in c if x['branch']==k[0])})")
print("  coverage(nu/nr) 분포:", " ".join(f"{r['coverage']:.3f}" for r in c if np.isfinite(r["coverage"]))[:200])
cov = [r["coverage"] for r in c if np.isfinite(r["coverage"])]
print(f"  coverage min={min(cov):.3f} max={max(cov):.3f}  COVERAGE_FLOOR=0.80 -> 전부 미달")

print()
print("== 4. ref-경계 마스크가 버리는 스텝 ==")
print(f"{'motion':24s}{'label':8s}{'ref_fps':>8s}{'plen':>6s}{'kept':>6s}{'drop%':>7s}{'floor':>6s}{'applied':>8s}")
for r in sorted(c, key=lambda x: (x["ref"], x["label"])):
    print(f"{r['ref']:24s}{r['label']:8s}{r['ref_fps']:>8.2f}{r['plen']:>6d}{r['kept']:>6d}"
          f"{r['drop_pct']:>7.1f}{r['floor']:>6d}{str(r['mask_applied']):>8s}")

print()
print("== 2. 정렬 파괴 대조군 (편차 스칼라, 도) ==")
print(f"{'motion':24s}{'label':8s}{'n':>4s}{'dtw':>7s}{'ident':>7s}{'rev_id':>7s}{'dtwrev':>7s}{'shuf':>7s}"
      f"{'id-dtw':>8s}{'shuf-dtw':>9s}{'설명몫%':>9s}")
for r in sorted(c, key=lambda x: (x["ref"], x["label"])):
    gain_id = r["dev_ident"] - r["dev_dtw"]
    gain_sh = r["dev_shuf"] - r["dev_dtw"]
    frac = 100.0 * gain_id / gain_sh if gain_sh > 1e-9 else float("nan")
    print(f"{r['ref']:24s}{r['label']:8s}{r['n_group']:>4d}{r['dev_dtw']:>7.1f}{r['dev_ident']:>7.1f}"
          f"{r['dev_rev_ident']:>7.1f}{r['dev_dtw_rev']:>7.1f}{r['dev_shuf']:>7.1f}"
          f"{gain_id:>8.1f}{gain_sh:>9.1f}{frac:>9.0f}")

print()
print("== 2b. DTW 거리: 정방향 vs 역순 기준 ==")
print(f"{'motion':24s}{'label':8s}{'dtw':>8s}{'dtw_rev':>9s}{'rev/fwd':>8s}")
for r in sorted(c, key=lambda x: (x["ref"], x["label"])):
    print(f"{r['ref']:24s}{r['label']:8s}{r['dtw_dist']:>8.1f}{r['dtw_rev_dist']:>9.1f}"
          f"{r['dtw_rev_dist']/max(r['dtw_dist'],1e-9):>8.2f}")
