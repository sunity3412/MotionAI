"""반증 R3 — '875건의 실체는 24~39편' 을 거리벡터가 아니라 원자료(각도 행렬)로 센다."""
import json, hashlib, collections, sys
sys.path.insert(0,".")
import numpy as np
st=json.load(open("students.json"))
f={r["id"]:r for r in json.load(open("facts.json"))}
g=collections.defaultdict(list)
for s in st:
    h=hashlib.md5(np.asarray(s["angles"],dtype=float).tobytes()).hexdigest()
    g[h].append(s["id"])
print("각도행렬 비트-동일 군집 수 =",len(g),"  (분석 875건)")
sizes=sorted((len(v) for v in g.values()),reverse=True)
print("군집 크기 상위:",sizes[:25])
print("크기 1인 군집(고유) =",sum(1 for v in g.values() if len(v)==1))
# 군집별 ref 라벨이 갈리는가 (같은 영상이 다른 기준으로 분석된 경우)
mixed=0
for h,ids in g.items():
    refs={f[i]["ref"] for i in ids}
    if len(refs)>1:
        mixed+=1
        print("  섞인 군집 n=%d refs=%s"%(len(ids),refs))
print("ref 가 섞인 군집 수 =",mixed)
# 프레임수 기준 군집
byT=collections.Counter()
for s in st:
    nj=len(s.get("keys") or [])or 8
    byT[(f[s["id"]]["ref"], len(s["angles"])//nj)]+=1
print("(ref,프레임수) 고유 조합 수 =",len(byT))
