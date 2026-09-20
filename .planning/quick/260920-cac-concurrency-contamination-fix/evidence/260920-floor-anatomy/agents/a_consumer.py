"""조사 A 단계11 — 바닥이 화면 점수에 닿나 (소비처 추적).

코드 사슬(확인):
  per_joint_deviation -> md["angle_vs_reference__{jk}"]  (app.py:2861)
  -> ipsf_criteria._REFERENCE_RELATIVE_CRITERIA (tolerance=20.0, LINEAR, cap)
  -> deduction_engine: over = max(0, dev - 20)  (deduction_engine.py:623)
여기서는 그 위에서 **관절 20도 초과 개수**와 실제 저장된 overallScore 를 대조한다.
"""
import json, sys, collections
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H
import numpy as np

TOL = 20.0
facts = json.load(open(f"{H.D}/facts.json"))
g = collections.defaultdict(list)
for f in facts:
    if f["label"] in ("correct", "fault", "self"):
        g[(f["ref"], f["label"])].append(f)

print(f"{'motion':24s}{'label':8s}{'n':>4s}{'scalar med':>11s}"
      f"{'over20 관절수 med':>18s}{'sum over20 med':>15s}{'overall med':>12s}{'overall min':>12s}")
for (ref, lab), rows in sorted(g.items()):
    dv = np.asarray([r["dev"] for r in rows], dtype=float)
    over = np.maximum(0.0, dv - TOL)
    cnt = (dv > TOL).sum(axis=1)
    ov = [r["overall"] for r in rows if r["overall"] is not None]
    print(f"{ref:24s}{lab:8s}{len(rows):4d}"
          f"{np.median([r['scalar'] for r in rows]):11.1f}"
          f"{np.median(cnt):18.1f}{np.median(over.sum(axis=1)):15.1f}"
          f"{(np.median(ov) if ov else float('nan')):12.1f}"
          f"{(min(ov) if ov else float('nan')):12.1f}")
