"""반증 R7 — '85.9% = climb 과대표집' 을 실제 시간순 표본으로 검증."""
import json, collections, datetime
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
scan={}
for r in json.load(open(f"{D}/scan.json")):
    scan.setdefault(r["_id"], r)
rows={r["id"]:r for r in json.load(open(f"{D}/out/G_match.json"))}
def ts(v):
    if v is None: return None
    if isinstance(v,str):
        try: return datetime.datetime.fromisoformat(v).timestamp()
        except Exception: return None
    v=float(v)
    return v/1000.0 if v>1e11 else v
have=[]
for i in rows:
    r=scan.get(i)
    if not r: continue
    t=ts(r.get("createdAt"))
    if t is not None: have.append((t,i))
have.sort()
print("createdAt 있는 분석 = %d / %d"%(len(have),len(rows)))
print("기간: %s ~ %s"%(datetime.datetime.utcfromtimestamp(have[0][0]).date(),
                      datetime.datetime.utcfromtimestamp(have[-1][0]).date()))
def acc(ids):
    o=sum(1 for i in ids if rows[i]["pred"]==rows[i]["ref"]); return o,len(ids),o/len(ids)
print()
print("85.9%% 재현 조건: 78건 중 오답 11건 (78*0.141 = 11.0). climb 코퍼스 오답률 = 19/38 = 50%%")
print("  -> climb 18건이 '평균적으로' 들어오면 오답 기대 9건 = 88.5%%. 11건이려면 climb 오답률 61%%.")
print()
for n in (78,):
    for name,sub in (("가장 오래된",[i for _,i in have[:n]]),("가장 최근",[i for _,i in have[-n:]])):
        o,t,a=acc(sub)
        cl=[i for i in sub if rows[i]["ref"]=="ref-climb"]
        clw=sum(1 for i in cl if rows[i]["pred"]!=rows[i]["ref"])
        print("%s %d건 -> 정확도 %d/%d = %.4f | climb %d건 그중 오답 %d | 전체 오답 %d"%(
            name,n,o,t,a,len(cl),clw,t-o))
        print("   동작분포:",dict(collections.Counter(rows[i]["ref"] for i in sub)))
print()
o=0
for k,(_,i) in enumerate(have,1):
    o+= rows[i]["pred"]==rows[i]["ref"]
    if k in (40,50,60,70,78,80,90,100,131,150,200,400,846):
        cl=sum(1 for _,j in have[:k] if rows[j]["ref"]=="ref-climb")
        print("  오래된 %4d건 누적 정확도 %.4f  (climb %3d건 = %.1f%%)"%(k,o/k,cl,cl/k*100))
print()
# 85.9% 에 가장 가까운 연속 윈도우 78건이 존재하나
best=None
for s in range(0,len(have)-78+1):
    ids=[i for _,i in have[s:s+78]]
    a=acc(ids)[2]
    if best is None or abs(a-0.859)<abs(best[1]-0.859): best=(s,a)
print("시간 연속 78건 윈도우 중 85.9%% 에 가장 가까운 것: start=%d 정확도 %.4f"%best)
