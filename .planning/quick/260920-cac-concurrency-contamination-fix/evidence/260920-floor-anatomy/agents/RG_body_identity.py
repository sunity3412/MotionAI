"""반증 R8 — '785/875 가 정은지->정은지 문제' 와 '초보 학생 영상 0편' 을
   체형 프로파일(bodyNormalizationProfile) 로 검사한다.
   같은 영상 재분석 간 산포(계기 잡음) 대비 talkv/출처불명 영상이 fixture 군과
   떨어져 있는지 본다."""
import json, collections, numpy as np, re
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
f=json.load(open(f"{D}/facts.json"))
rows={r["id"]:r for r in json.load(open(f"{D}/out/G_match.json"))}
FIELDS=["shoulderHipRatio","estimatedHeightScale","legScale","armScale"]
def vec(r):
    b=r.get("body") or {}
    v=[b.get(k) for k in FIELDS]
    return None if any(x is None for x in v) else np.array(v,dtype=float)
def src(r): return r["vk"] or (f"fn:{r['fn']}" if r["fn"] else f"id:{r['id']}")
def kind(r):
    vk=r["vk"] or ""; fn=r["fn"] or ""
    if vk.startswith("reference/"): return "A.reference"
    if vk.startswith("fixtures/"): return "B.fixture"
    if vk.startswith("uploads/"): return "D.uploads"
    if "talkv" in fn: return "C.talkv"
    return "F.기타"
g=collections.defaultdict(list)
for r in f:
    v=vec(r)
    if v is None: continue
    g[(kind(r),src(r),r["ref"])].append(v)
# 같은 소스 내부 산포 = 계기 잡음
within=[]
for k,vs in g.items():
    if len(vs)>=3:
        a=np.array(vs); within.append(a.std(axis=0))
W=np.median(np.array(within),axis=0)
print("계기 잡음 (같은 영상 재분석 내부 sd, 중앙값):", dict(zip(FIELDS,np.round(W,4))))
# fixture 군 중심
fixv=np.array([v for k,vs in g.items() if k[0]=="B.fixture" for v in vs])
mu=fixv.mean(axis=0); sd=fixv.std(axis=0)
print("정은지 fixture 군 평균:", dict(zip(FIELDS,np.round(mu,3))))
print("정은지 fixture 군 sd  :", dict(zip(FIELDS,np.round(sd,3))))
print()
print("--- 소스별 평균 체형, fixture 군 중심으로부터 z 거리 ---")
out=[]
for (kd,s,ref),vs in g.items():
    a=np.array(vs); m=a.mean(axis=0)
    z=float(np.linalg.norm((m-mu)/sd))
    out.append((z,kd,s,ref,len(vs),m))
for z,kd,s,ref,n,m in sorted(out,reverse=True)[:18]:
    print("  z=%5.2f  %-12s n=%3d %-24s %s"%(z,kd,n,ref,s[-42:]))
print()
zb=[z for z,kd,*_ in out if kd=="B.fixture"]
print("fixture 소스들의 z 분포: n=%d med %.2f max %.2f"%(len(zb),np.median(zb),max(zb)))
for lab in ("C.talkv","D.uploads","F.기타","A.reference"):
    zz=[z for z,kd,*_ in out if kd==lab]
    if zz: print("%-12s z: n=%d med %.2f max %.2f"%(lab,len(zz),np.median(zz),max(zz)))
