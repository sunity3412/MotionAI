"""반증 R5 — 표5·표6(마진) 을 내 손으로 다시 계산."""
import json, collections, numpy as np
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
rows=json.load(open(f"{D}/out/G_match.json"))
for r in rows:
    v=sorted(r["dist"].values())
    r["m"]=(v[1]-v[0])/v[0]
    r["ok"]=r["pred"]==r["ref"]
    # 2위
    s=sorted(r["dist"].items(), key=lambda kv:kv[1])
    r["second"]=s[1][0]
print("[표5 재계산] 동작 고정 correct vs fault 마진 중앙")
dec=0
for m in sorted({r["ref"] for r in rows}):
    c=[r for r in rows if r["ref"]==m and r["label"]=="correct"]
    f=[r for r in rows if r["ref"]==m and r["label"]=="fault"]
    if not c or not f: continue
    mc,mf=np.median([r["m"] for r in c]),np.median([r["m"] for r in f])
    dec += mf<mc
    sec=collections.Counter(r["second"] for r in f).most_common(1)[0]
    print("  %-26s correct %.3f (n%d)  fault %.3f (n%d)  ratio %.2f  fault2위=%s %d/%d"%(m,mc,len(c),mf,len(f),mf/mc,sec[0],sec[1],len(f)))
print("  감소한 동작 수 = %d"%dec)
ac=[r["m"] for r in rows if r["label"]=="correct"]; af=[r["m"] for r in rows if r["label"]=="fault"]
print("  전체 중앙 correct %.3f  fault %.3f  ratio %.2f"%(np.median(ac),np.median(af),np.median(af)/np.median(ac)))
print()
print("[표6 재계산] 마진 겹침")
bad=[r for r in rows if not r["ok"]]; good=[r for r in rows if r["ok"]]
bmax=max(r["m"] for r in bad)
print("  틀린 것 n=%d min %.3f med %.3f max %.3f"%(len(bad),min(r["m"] for r in bad),np.median([r["m"] for r in bad]),bmax))
print("  맞춘 것 n=%d min %.3f med %.3f max %.3f"%(len(good),min(r["m"] for r in good),np.median([r["m"] for r in good]),max(r["m"] for r in good)))
ov=[r for r in good if r["m"]<=bmax]
print("  틀린 것 최대(%.3f) 이하에 들어온 맞춘 것 = %d건"%(bmax,len(ov)))
print("  그 %d건의 ref 분포:"%len(ov), collections.Counter(r["ref"] for r in ov))
print("  그 %d건의 label 분포:"%len(ov), collections.Counter(r["label"] for r in ov))
print()
print("[길이-거리 상관] 학생 프레임수 vs 1등거리")
from scipy.stats import spearmanr
fr=[r["frames"] for r in rows]; d1=[min(r["dist"].values()) for r in rows]
print("  Spearman = %.3f (n=%d)"%(spearmanr(fr,d1).statistic,len(rows)))
