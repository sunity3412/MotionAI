"""How much of the same-video floor is pure temporal sampling?

The reference angle series is stored on a ~14.94 fps grid. The live student path
re-extracts the SAME footage on a ~9.96 fps grid (empirically exactly 2/3 the row
count for every motion). Two thirds of the student samples therefore land at
instants that do NOT exist in the stored reference series.

Nearest-neighbour decimation cannot show this cost: every decimated row is a
verbatim copy of a stored row, so DTW matches it back exactly and the deviation is
0. To measure the real cost we must sample the reference series at OFF-GRID times,
which is what a different fps actually does. Linear interpolation is an optimistic
stand-in (a real re-extraction runs the pose model on the true intermediate frame,
which can only differ more), so this is a LOWER BOUND on the temporal component.

Also reported: inter-frame motion of the stored reference series, which is what
sets that lower bound.
"""
import json, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H

facts = json.load(open(f"{D}/facts.json"))
refs = H.load_references()


def interp_at(a, times):
    """Linear interpolation of (T,J) at fractional row positions."""
    T = len(a)
    t = np.clip(times, 0, T - 1)
    lo = np.floor(t).astype(int)
    hi = np.clip(lo + 1, 0, T - 1)
    w = (t - lo)[:, None]
    return a[lo] * (1 - w) + a[hi] * w


print(f"{'motion':24s}{'T':>5s}{'inter-frame':>13s}{'grid LB':>10s}"
      f"{'live floor':>12s}{'grid share':>12s}")
out = []
for m in sorted(refs):
    a = H.ref_matrix(refs[m])
    T = len(a)
    n = int(round(T * 2 / 3))

    # inter-frame motion of the stored series: median |a[i+1]-a[i]| over joints/time
    interframe = float(np.median(np.abs(np.diff(a, axis=0))))

    # sample at the student grid, which is off-grid for 2 of every 3 samples
    worst = 0.0
    for phase in (0.0, 1 / 3, 2 / 3):
        times = (np.arange(n) + phase) * (T - 1) / max(n - 1, 1)
        dev, _ = H.deviate(interp_at(a, times), refs[m])
        worst = max(worst, H.scalar(dev))

    live = [r["scalar"] for r in facts
            if r["ref"] == m and r["label"] in ("self", "correct")]
    livemed = float(np.median(live)) if live else float("nan")
    share = worst / livemed * 100 if livemed and np.isfinite(livemed) and livemed > 0 else float("nan")
    out.append(dict(motion=m, T=T, interframe=interframe, grid_lb=worst,
                    live=livemed, share=share))
    print(f"{m:24s}{T:5d}{interframe:13.2f}{worst:10.2f}{livemed:12.2f}{share:11.1f}%")

json.dump(out, open(f"{D}/grid_effect.json", "w"))
print()
print("inter-frame = median |angle change| between consecutive stored reference rows (deg)")
print("grid LB     = deviation when the SAME pose data is read on the student grid")
print("              (linear interpolation -> optimistic lower bound)")
print("live floor  = the live pipeline re-running that same footage end to end")
print("grid share  = grid LB / live floor")
