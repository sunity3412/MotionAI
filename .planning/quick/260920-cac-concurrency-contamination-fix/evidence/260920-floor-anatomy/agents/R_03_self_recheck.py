"""R-3 (반증) — 판정의 가장 무거운 다리(self 행: 카메라 불일치 0 인데 바닥 2.3~17.2)를
facts.json 을 믿지 말고 students.json 원본에서 운영 _deviation_against 로 다시 낸다.
동시에 (a) 그 self 분석이 정말 같은 motion 의 기준과 비교됐는지, (b) 프레임 수/fps
격자가 기준과 얼마나 다른지 — '같은 영상인데 왜 0 이 아닌가' 의 후보를 같이 찍는다.
"""
import json, sys, collections
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H

refs = H.load_references()
students = {s["id"]: s for s in H.load_students()}
facts = json.load(open(f"{D}/facts.json"))

print(f"{'id':26s}{'ref':24s}{'label':8s}{'vk':30s}{'facts.scalar':>13s}{'재계산':>9s}"
      f"{'stuT':>7s}{'refT':>7s}{'dtw':>8s}")
rows = []
for r in facts:
    if r["label"] != "self":
        continue
    s = students.get(r["id"])
    rdoc = refs.get(r["ref"])
    if s is None or rdoc is None:
        print("  MISSING", r["id"], r["ref"]); continue
    ua = H.student_matrix(s)
    dev, m = H.deviate(ua, rdoc)
    sc = H.scalar(dev)
    rt = H.ref_matrix(rdoc).shape[0]
    rows.append(dict(id=r["id"], ref=r["ref"], vk=r["vk"], facts=r["scalar"], recomputed=sc,
                     stuT=int(ua.shape[0]), refT=int(rt), dtw=float(m.distance),
                     ref_fps=H.ref_fps_of(rdoc)))
    print(f"{r['id'][:24]:26s}{r['ref']:24s}{r['label']:8s}{r['vk'][:28]:30s}"
          f"{r['scalar']:13.2f}{sc:9.2f}{ua.shape[0]:7d}{rt:7d}{m.distance:8.1f}")
json.dump(rows, open(f"{D}/out/R_03_self_recheck.json", "w"), ensure_ascii=False, indent=1)
d = np.array([abs(x["facts"] - x["recomputed"]) for x in rows])
print()
print(f"facts.json 대비 재계산 최대 차이 = {d.max():.6f}도 (n={d.size})")
print()
print("기준 doc 의 angles fps vs self 분석의 프레임수 — 같은 영상, 다른 시간 격자인가")
for x in rows:
    print(f"   {x['ref']:24s} stuT={x['stuT']:5d}  refT={x['refT']:5d}  ref_fps={x['ref_fps']}")
