"""C3 step1 — facts.json 의 DTW 정렬 산출물을 label x motion 으로 집계.

읽는 것: dtw(정규화 거리), plen(path 길이), ustart/uend/rstart/rend, frames, tier.
새 계산 0 — 전부 이미 운영 _deviation_against 가 낸 값이다.
"""
import json, collections
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
rows = json.load(open(f"{D}/facts.json"))

by = collections.defaultdict(list)
for r in rows:
    by[(r["ref"], r["label"])].append(r)

def med(vs):
    a = np.asarray([v for v in vs if v is not None], dtype=float)
    return float(np.median(a)) if a.size else float("nan")

motions = sorted({r["ref"] for r in rows})
order = ["correct", "fault", "self", "upload", "unknown"]

print("== A. label x motion: DTW 정규화거리 / path 길이 / window ==")
hdr = f"{'motion':26s}{'label':9s}{'n':>4s}{'dev':>7s}{'dtw':>8s}{'plen':>7s}{'uframes':>9s}{'useg':>7s}{'rseg':>7s}{'rfull':>7s}{'trim':>7s}"
print(hdr)
for m in motions:
    for lb in order:
        rs = by.get((m, lb))
        if not rs:
            continue
        uframes = med([r["frames"] for r in rs])
        useg = med([r["uend"] - r["ustart"] for r in rs])
        rseg = med([r["rend"] - r["rstart"] for r in rs])
        # ref 전체 길이는 facts 에 없다 -> rend 가 최대인 값 (통째면 rend==nr)
        rfull = max((r["rend"] for r in rs))
        trim = sum(1 for r in rs if (r["ustart"], r["uend"]) != (0, r["frames"]) or r["rstart"] != 0)
        print(f"{m:26s}{lb:9s}{len(rs):>4d}{med([r['scalar'] for r in rs]):>7.1f}"
              f"{med([r['dtw'] for r in rs]):>8.2f}{med([r['plen'] for r in rs]):>7.0f}"
              f"{uframes:>9.0f}{useg:>7.0f}{rseg:>7.0f}{rfull:>7d}{trim:>4d}/{len(rs):<3d}")

print()
print("== B. correct vs fault: DTW 거리가 갈리나 ==")
print(f"{'motion':26s}{'dtw_c':>8s}{'dtw_f':>8s}{'ratio':>7s}{'dev_c':>7s}{'dev_f':>7s}{'dev_ratio':>10s}")
for m in motions:
    c, f = by.get((m, "correct")), by.get((m, "fault"))
    if not (c and f):
        continue
    dc, df = med([r["dtw"] for r in c]), med([r["dtw"] for r in f])
    vc, vf = med([r["scalar"] for r in c]), med([r["scalar"] for r in f])
    print(f"{m:26s}{dc:>8.2f}{df:>8.2f}{df/dc:>7.2f}{vc:>7.1f}{vf:>7.1f}{vf/vc:>10.2f}")

print()
print("== C. window 선정 분기 (ustart/uend vs frames, rstart/rend) ==")
cnt = collections.Counter()
for r in rows:
    u_whole = (r["ustart"] == 0 and r["uend"] == r["frames"])
    r_whole = (r["rstart"] == 0)
    cnt[(r["ref"], "u_whole" if u_whole else "u_slid", "r_whole" if r_whole else "r_slid")] += 1
for k in sorted(cnt):
    print(f"  {k[0]:26s} {k[1]:8s} {k[2]:8s} n={cnt[k]}")

print()
print("== D. tier 분포 ==")
t = collections.Counter((r["ref"], r["tier"]) for r in rows)
for k in sorted(t, key=lambda x: (x[0], str(x[1]))):
    print(f"  {k[0]:26s} tier={k[1]!s:14s} n={t[k]}")

print()
print("== E. dev vs dtw 상관 (동작 내부, correct+fault 합침) ==")
for m in motions:
    rs = [r for r in rows if r["ref"] == m and r["label"] in ("correct", "fault")]
    if len(rs) < 8:
        continue
    x = np.array([r["dtw"] for r in rs]); y = np.array([r["scalar"] for r in rs])
    if x.std() == 0 or y.std() == 0:
        continue
    print(f"  {m:26s} n={len(rs):4d}  r(dtw,dev) = {np.corrcoef(x,y)[0,1]:+.3f}")
