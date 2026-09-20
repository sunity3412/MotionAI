"""R8 — c3 의 나머지 [확인] 주장 검산: 트리밍 0/875 · 분산분해 77/84% · 표본 구조."""
from __future__ import annotations
import json, sys, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H

facts = json.load(open(f"{D}/facts.json"))
refs = H.load_references()
print(f"분석 수 = {len(facts)}")

# (1) 트리밍 census — facts 의 rstart/rend/ustart/uend 로 직접 재판정
ref_trim = user_trim = 0; cov = []
for f in facts:
    rdoc = refs.get(f["ref"])
    if rdoc is None: continue
    nr_full = H.ref_matrix(rdoc).shape[0]
    nu_full = f["frames"]
    if not (f["rstart"] == 0 and f["rend"] == nr_full): ref_trim += 1
    if not (f["ustart"] == 0 and f["uend"] == nu_full): user_trim += 1
    if nu_full < nr_full: cov.append(nu_full / nr_full)
print(f"[검산] 기준 트리밍 {ref_trim}/{len(facts)}   학생 트리밍 {user_trim}/{len(facts)}")
c = np.array(cov)
print(f"[검산] nu<nr {len(c)}건 coverage  min {c.min():.3f} / 중앙 {np.median(c):.3f} / max {c.max():.3f}"
      f"  COVERAGE_FLOOR(0.80) 통과 {int((c>=0.80).sum())}건")

# (2) 분산분해 재현
rows = json.load(open(f"{D}/out/c3_full_oracle.json"))
for name, key in (("운영 DTW", "dev_dtw"), ("oracle", "dev_oracle")):
    g = collections.defaultdict(list)
    for r in rows: g[r["ref"]].append(r[key])
    ratio, _ = H.variance_decomposition(g)
    print(f"[검산] {name}: 동작내 {ratio*100:.0f}%  -> 동작이 정하는 몫 {(1-ratio)*100:.0f}%")

# (3) 표본 구조 — 동작·라벨당 고유 videoKey 수 (n 부풀림 점검)
print()
print(f"{'motion':24s}{'label':8s}{'분석수':>7s}{'고유videoKey':>13s}")
grp = collections.defaultdict(list)
for f in facts: grp[(f["ref"], f["label"])].append(f)
for k in sorted(grp):
    if k[1] not in ("correct", "self"): continue
    vks = {x["vk"] for x in grp[k]}
    print(f"{k[0]:24s}{k[1]:8s}{len(grp[k]):>7d}{len(vks):>13d}")

# (4) 고유 videoKey 1건씩만 남겨 분산분해 재계산 (중복 재분석이 몫을 부풀렸나)
seen = set(); ded = []
for r in rows:
    f = next((x for x in facts if x["id"] == r["id"]), None)
    key = (r["ref"], f["vk"] if f else None, r["label"])
    if key in seen: continue
    seen.add(key); ded.append(r)
for name, key in (("운영 DTW", "dev_dtw"), ("oracle", "dev_oracle")):
    g = collections.defaultdict(list)
    for r in ded: g[r["ref"]].append(r[key])
    ratio, _ = H.variance_decomposition(g)
    print(f"\n[중복제거 n={len(ded)}] {name}: 동작내 {ratio*100:.0f}% -> 동작 몫 {(1-ratio)*100:.0f}%")
