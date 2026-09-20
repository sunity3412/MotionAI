"""반증 X6 — '180도 천장 기각' 을 version-matched 바닥으로 다시 검정한다.

조사 B 의 기각 근거 2개:
  (a) 관절 단위 n=88 에서 동작효과 제거 후 d180 상관이 −0.136
  (b) d180<30 관절의 바닥/chance(0.265) < d180>=60 의 0.369
둘 다 rot180_v1 기준으로 잰 바닥 위에서 계산됐다. matched 로 다시 낸다.
"""
from __future__ import annotations
import json, sys, collections, hashlib
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

live = H.load_references()
vers = json.load(open(f"{D}/ref_versions.json"))
facts = json.load(open(f"{D}/facts.json"))
students = {s["id"]: s for s in H.load_students()}
VER = {"ref-climb": "quick-260816-r7k"}

def ver_doc(m):
    v = dict(vers[m].get(VER.get(m, "phase4_v1")) or {})
    if not v.get("angles"): return None
    for k in ("anglesJointKeys","clipRange","baseUntilS","sharedBaseMotionId",
              "keypointReport","anglesRealFps","anglesFrames"):
        v.setdefault(k, live[m].get(k))
    return v

bykey = collections.defaultdict(list)
for f in facts: bykey[(f["ref"], f["label"])].append(f)

def uniq_students(mid, lab, cap=6):
    seen, keep = set(), []
    for f in sorted(bykey.get((mid, lab), []), key=lambda x: x["id"]):
        s = students.get(f["id"])
        if s is None: continue
        h = hashlib.md5(np.asarray(s["angles"], float).tobytes()).hexdigest()
        if h in seen: continue
        seen.add(h); keep.append(s)
        if len(keep) >= cap: break
    return keep

rows = []
for mid in sorted(live):
    vd = ver_doc(mid)
    if vd is None: continue
    lab = "correct" if bykey.get((mid, "correct")) else "self"
    ss = uniq_students(mid, lab)
    if not ss: continue
    M = H.ref_matrix(vd)
    devs = []
    for s in ss:
        dev, _ = H.deviate(H.student_matrix(s), vd)
        devs.append(dev)
    dev_med = np.median(np.vstack(devs), axis=0)
    # analytic chance (전 프레임쌍) — matched 기준으로
    T = M.shape[0]
    iu = np.triu_indices(T, k=1)
    for j, jk in enumerate(H.JOINT_KEYS):
        col = M[:, j]
        rows.append(dict(m=mid, jk=jk, dev=float(dev_med[j]),
                         ch=float(np.median(np.abs(col[iu[0]] - col[iu[1]]))),
                         sd=float(col.std(ddof=0)), rng=float(col.max()-col.min()),
                         iqr=float(np.percentile(col,75)-np.percentile(col,25)),
                         d180=float(np.median(180.0-col)),
                         fd=float(np.median(np.abs(np.diff(col))))))
json.dump(rows, open(f"{D}/out/x_ceiling_rematched.json","w"), indent=1)

def pearson(a,b): return float(np.corrcoef(np.asarray(a,float),np.asarray(b,float))[0,1])
def spearman(a,b):
    r=lambda v: np.argsort(np.argsort(np.asarray(v,float))).astype(float)
    return float(np.corrcoef(r(a),r(b))[0,1])

print(f"=== 관절 단위 n={len(rows)} (version-matched 바닥) ===")
Y=[r["dev"] for r in rows]
for f in ("sd","rng","iqr","d180","fd","ch"):
    X=[r[f] for r in rows]
    print(f"  {f:5s} pearson={pearson(X,Y):+.3f} spearman={spearman(X,Y):+.3f}")
print("  -- 동작 효과 제거(중심화) --")
byM=collections.defaultdict(list)
for r in rows: byM[r["m"]].append(r)
cent={}
for f in ("dev","sd","rng","iqr","d180","fd","ch"):
    v=[]
    for m,rs in byM.items():
        a=np.array([r[f] for r in rs],float); v.extend(a-a.mean())
    cent[f]=v
for f in ("sd","rng","iqr","d180","fd","ch"):
    print(f"  {f:5s} pearson={pearson(cent[f],cent['dev']):+.3f} spearman={spearman(cent[f],cent['dev']):+.3f}")

near=[r for r in rows if r["d180"]<30]; far=[r for r in rows if r["d180"]>=60]
print(f"\n=== 180 천장 직접 검정 (matched) ===")
print(f"  근처(d180<30, n={len(near)}): 바닥 med={np.median([r['dev'] for r in near]):.2f} "
      f"chance={np.median([r['ch'] for r in near]):.2f} 바닥/chance={np.median([r['dev']/r['ch'] for r in near]):.3f}")
print(f"  먼  (d180>=60,n={len(far)}): 바닥 med={np.median([r['dev'] for r in far]):.2f} "
      f"chance={np.median([r['ch'] for r in far]):.2f} 바닥/chance={np.median([r['dev']/r['ch'] for r in far]):.3f}")
