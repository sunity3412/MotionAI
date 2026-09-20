"""반증 1 — kip-up '분리 0점'이 데드존 때문인가 억제 때문인가 + profile 불변 재검."""
import sys, json, collections, statistics as st
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0,D)
import numpy as np
rows=json.load(open(f"{D}/out/F_finals.json"))
facts={r["id"]:r for r in json.load(open(f"{D}/facts.json"))}
ref_rows=[r for r in rows if r["profile_mode"]=="ref"]
none_rows={r["id"]:r for r in rows if r["profile_mode"]=="none"}

# (a) profile 불변 재검
mm=[r["id"] for r in ref_rows if r["qa_final"]!=none_rows[r["id"]]["qa_final"]]
print(f"profile(ref) vs profile(none) final 불일치: {len(mm)}/{len(ref_rows)}")

# (b) 그룹별: 억제 on/off 두 경로 + 고유 videoKey 수
g=collections.defaultdict(list)
for r in ref_rows: g[(r["ref"],r["label"])].append(r)
print(f"\n{'동작':26s}{'라벨':8s}{'n':>4s}{'vk':>4s}{'편차':>7s}{'qa':>6s}{'nosupp':>8s}{'supp건':>7s}{'maxjoint':>9s}{'>20관절median':>14s}")
out={}
for k in sorted(g):
    rs=g[k]
    vk=len({r["vk"] for r in rs})
    dev_max=[max(r["dev"]) for r in rs]
    nover=[sum(1 for v in r["md"].values() if v>20.0) for r in rs]
    qa=[r["qa_final"] for r in rs]; ns=[r["qa_nosupp_final"] for r in rs]
    out[k]=dict(qa=qa,ns=ns)
    print(f"{k[0]:26s}{k[1]:8s}{len(rs):4d}{vk:4d}{st.median([r['scalar'] for r in rs]):7.1f}"
          f"{st.median(qa):6.1f}{st.median(ns):8.1f}{sum(1 for r in rs if r['qa_final']>r['qa_nosupp_final']):7d}"
          f"{st.median(dev_max):9.1f}{st.median(nover):14.1f}")

print("\n동작별 correct-fault 분리 (qa=억제on / nosupp=억제off)")
for m in sorted({k[0] for k in g}):
    if (m,"correct") in out and (m,"fault") in out:
        c,f=out[(m,"correct")],out[(m,"fault")]
        print(f"  {m:26s} qa {st.median(c['qa'])-st.median(f['qa']):+6.1f}   "
              f"nosupp {st.median(c['ns'])-st.median(f['ns']):+6.1f}")
