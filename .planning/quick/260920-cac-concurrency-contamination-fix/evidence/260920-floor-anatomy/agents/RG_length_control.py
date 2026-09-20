"""반증 R6 — 이전 조사가 '안 돌렸다'고 남긴 대조군: 같은 영상의 '길이만' 바꾼다.

내용(자세 시퀀스)은 그대로 두고 시간축만 선형 보간으로 늘리거나 줄여서
운영 H.deviate 의 argmin 이 뒤집히는지 본다. DTW 는 시간 왜곡에 불변해야 하므로
뒤집히면 그건 내용이 아니라 길이가 argmin 을 정한다는 뜻이다.
"""
import json, sys
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0,D)
import numpy as np, harness as H
rows={r["id"]:r for r in json.load(open(f"{D}/out/G_match.json"))}
st={s["id"]:s for s in json.load(open(f"{D}/students.json"))}
REFS=H.load_references()

def resample(m,T):
    n=len(m)
    if T==n: return m.copy()
    x=np.linspace(0,n-1,T)
    out=np.empty((T,m.shape[1]))
    for j in range(m.shape[1]):
        out[:,j]=np.interp(x,np.arange(n),m[:,j])
    return out

def argmin_of(m):
    d={}
    for rid,rdoc in REFS.items():
        _dev,mt=H.deviate(m,rdoc)
        d[rid]=float(mt.distance)
    s=sorted(d.items(),key=lambda kv:kv[1])
    return s[0][0],s[0][1],s[1][0],s[1][1],d

# 대상 선정: climb 4군집 대표 1건씩
picks={}
for aid,r in rows.items():
    if r["ref"]!="ref-climb": continue
    key=(r["frames"], r["pred"])
    picks.setdefault(key,aid)
print("climb 대표 표본:",{k:rows[v]["fn"] or rows[v]["vk"] for k,v in picks.items()})
print()
LENS=[50,62,80,100,120,138,160,172,200,240,298]
for (fr,pred),aid in sorted(picks.items()):
    s=st[aid]; nj=len(s.get("keys") or [])or 8
    m=np.asarray(s["angles"],dtype=float).reshape(-1,nj)
    src=(rows[aid]["fn"] or rows[aid]["vk"] or aid)
    print(f"--- 원본 {fr}프레임  pred={pred}  src={src[-40:]}")
    for T in LENS:
        mm=resample(m,T)
        best,bd,sec,sd,d=argmin_of(mm)
        flag="" if best=="ref-climb" else "  <-- climb 아님"
        print("    T=%4d  argmin=%-20s d=%7.2f   d(climb)=%7.2f d(sideway)=%7.2f%s"%(
            T,best.replace("ref-",""),bd,d["ref-climb"],d["ref-sideway-spin"],flag))
    print()
