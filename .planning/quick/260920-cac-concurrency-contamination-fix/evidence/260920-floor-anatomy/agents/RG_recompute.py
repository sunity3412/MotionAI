"""반증 R2 — G_match.json 을 운영 함수로 다시 계산해 비트 대조.
전수 재계산은 161초 걸리므로 (a) 오분류 19건 전부 + (b) 무작위 60건 을 재계산한다."""
import json, random, sys
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0,D)
import numpy as np, harness as H
rows={r["id"]:r for r in json.load(open(f"{D}/out/G_match.json"))}
students={s["id"]:s for s in json.load(open(f"{D}/students.json"))}
REFS=H.load_references()
wrong=[i for i,r in rows.items() if r["pred"]!=r["ref"]]
random.seed(7)
rest=random.sample([i for i in rows if i not in set(wrong)],60)
ids=wrong+rest
maxdiff=0.0; flips=0
for aid in ids:
    s=students[aid]; nj=len(s.get("keys") or []) or 8
    m=np.asarray(s["angles"],dtype=float).reshape(-1,nj)
    d={}
    for rid,rdoc in REFS.items():
        dev,match=H.deviate(m,rdoc)
        d[rid]=float(match.distance)
    old=rows[aid]["dist"]
    for rid in d:
        maxdiff=max(maxdiff,abs(d[rid]-old[rid]))
    pred=min(d,key=d.get)
    if pred!=rows[aid]["pred"]:
        flips+=1
        print("FLIP",aid,rows[aid]["pred"],"->",pred)
print(f"재계산 {len(ids)}건 (오분류 {len(wrong)} + 무작위 60)")
print(f"거리 최대 절대차 = {maxdiff:.3e}   argmin 뒤집힘 = {flips}")
