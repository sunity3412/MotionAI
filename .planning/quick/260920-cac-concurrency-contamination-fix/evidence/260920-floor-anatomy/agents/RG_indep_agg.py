"""반증 R1 — G_match.json 을 내 손으로 다시 집계한다 (그들 집계 스크립트 미사용)."""
import json, collections
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
rows=json.load(open(f"{D}/out/G_match.json"))
print("rows:",len(rows))
ok=sum(1 for r in rows if r["pred"]==r["ref"])
print("전수 정확도: %d/%d = %.4f"%(ok,len(rows),ok/len(rows)))
# 오분류 쌍
conf=collections.Counter((r["ref"],r["pred"]) for r in rows if r["pred"]!=r["ref"])
print("오분류 쌍:",dict(conf))
# 동작별
bym=collections.defaultdict(lambda:[0,0])
for r in rows:
    bym[r["ref"]][1]+=1
    if r["pred"]==r["ref"]: bym[r["ref"]][0]+=1
for m,(o,n) in sorted(bym.items(), key=lambda kv:-kv[1][1]):
    print("  %-26s %3d/%3d  %.3f"%(m,o,n,o/n))
# label 별
byl=collections.defaultdict(lambda:[0,0])
for r in rows:
    byl[r["label"]][1]+=1
    if r["pred"]==r["ref"]: byl[r["label"]][0]+=1
print("label:",{k:(v[0],v[1]) for k,v in byl.items()})
# climb 제외
nc=[r for r in rows if r["ref"]!="ref-climb"]
print("climb 제외: %d/%d"%(sum(1 for r in nc if r["pred"]==r["ref"]),len(nc)))
# climb 비중 산술 확인
print("climb n=",sum(1 for r in rows if r["ref"]=="ref-climb"), " 비중=%.4f"%(sum(1 for r in rows if r["ref"]=="ref-climb")/len(rows)))
