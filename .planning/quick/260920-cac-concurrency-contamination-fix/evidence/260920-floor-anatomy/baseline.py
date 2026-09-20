import json, numpy as np, sys, time
sys.path.insert(0, "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13")
import harness as H

students = H.load_students(); refs = H.load_references()
rows = []
t0 = time.time()
for i, s in enumerate(students):
    rd = refs.get(s["ref"])
    if rd is None:
        continue
    try:
        dev, m = H.deviate(H.student_matrix(s), rd)
    except Exception as e:
        rows.append(dict(id=s["id"], uid=s["uid"], ref=s["ref"], err=str(e)[:80])); continue
    rows.append(dict(id=s["id"], uid=s["uid"], ref=s["ref"], frames=s["frames"],
                     dev=[float(x) for x in dev], scalar=H.scalar(dev),
                     dtw=float(m.distance), ustart=int(m.start), uend=int(m.end),
                     rstart=int(m.ref_start), rend=int(m.ref_end), plen=len(m.path),
                     overall=s.get("overall"), body=s.get("body"),
                     tier=(s.get("motionAlignment") or {}).get("tier")))
    if (i+1) % 100 == 0:
        print(f"  {i+1}/{len(students)}  {time.time()-t0:.0f}s", flush=True)
json.dump(rows, open(f"{H.D}/baseline.json","w"))
ok = [r for r in rows if "scalar" in r and np.isfinite(r["scalar"])]
print(f"\n완료 {len(ok)}/{len(rows)}  {time.time()-t0:.0f}s")
groups = {}
for r in ok: groups.setdefault(r["ref"], []).append(r["scalar"])
ratio, tab = H.variance_decomposition(groups)
print(f"\n{'동작':26s}{'n':>5s}{'중앙':>8s}{'평균':>8s}{'sd':>7s}{'최소':>8s}{'최대':>8s}")
for g in sorted(tab, key=lambda k: -tab[k]["median"]):
    t = tab[g]
    print(f"{g:26s}{t['n']:5d}{t['median']:8.1f}{t['mean']:8.1f}{t['sd']:7.2f}{t['lo']:8.1f}{t['hi']:8.1f}")
print(f"\n동작내 분산이 전체 분산을 설명하는 비율 = {ratio*100:.0f}%  (동작이 정하는 몫 = {(1-ratio)*100:.0f}%)")
