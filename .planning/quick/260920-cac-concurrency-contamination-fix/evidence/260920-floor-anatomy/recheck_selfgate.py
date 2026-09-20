"""Re-run the SUMMARY 12-2 validity gate two ways.

(A) The way 12-2 did it: feed the reference's OWN STORED angle matrix in as the
    student. That is an identity comparison -> deviation 0 by construction.
(B) The way the live pipeline actually does it: the video is re-extracted on the
    student time grid (2/3 of the reference rate) and re-posed, then compared.
    Simulated here by decimating the stored reference angles to the student grid.
    Measured empirically by the label='self'/'correct' analyses, which ARE the
    reference footage re-run through the live pipeline.

If (A) gives 0 and (B) does not, 12-2's gate never tested anything.
"""
import json, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H

facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
refs = H.load_references()

MOTIONS = sorted(refs)
print(f"{'motion':24s}{'A: stored-angles self':>22s}{'B: decimated 2/3 self':>23s}"
      f"{'C: live self/correct':>22s}")
rows = []
for m in MOTIONS:
    rd = refs[m]
    a_ref = H.ref_matrix(rd)

    # (A) identity — what 12-2 measured
    devA, _ = H.deviate(a_ref, rd)
    sA = H.scalar(devA)

    # (B) same pose data, student time grid only
    n = int(round(len(a_ref) * 2 / 3))
    idx = np.clip(np.round(np.linspace(0, len(a_ref) - 1, n)).astype(int), 0, len(a_ref) - 1)
    devB, _ = H.deviate(a_ref[idx], rd)
    sB = H.scalar(devB)

    # (C) empirical: the live pipeline re-running the reference footage
    live = [r["scalar"] for r in facts
            if r["ref"] == m and r["label"] in ("self", "correct")]
    sC = float(np.median(live)) if live else float("nan")

    rows.append((m, sA, sB, sC, len(live)))
    cs = f"{sC:6.2f}(n{len(live)})" if live else "     -"
    print(f"{m:24s}{sA:22.4f}{sB:23.2f}{cs:>22s}")

print()
a = np.array([r[1] for r in rows])
b = np.array([r[2] for r in rows])
c = np.array([r[3] for r in rows if np.isfinite(r[3])])
print(f"(A) stored-angles self  : max {a.max():.4f}  -> 12-2 saw 0 everywhere")
print(f"(B) time-grid-only self : {b.min():.2f} ~ {b.max():.2f}  (pose data identical)")
print(f"(C) live self/correct   : {c.min():.2f} ~ {c.max():.2f}")
print()
print("(C) minus (B) = the part that is NOT the time grid (pose re-extraction etc.)")
for m, sA, sB, sC, n in rows:
    if np.isfinite(sC):
        print(f"  {m:24s} live {sC:6.2f} = grid {sB:6.2f} + rest {sC - sB:6.2f}")
json.dump([dict(motion=m, identity=sA, grid_only=sB, live=sC, n=n) for m, sA, sB, sC, n in rows],
          open(f"{D}/selfgate.json", "w"))
