"""반증 R4 — 출처 분류기(G_provenance.provenance) 가 무엇을 근거로 'B.정은지 fixture' 로
   보냈는지 감사한다. vk 없이 파일명 정규식만으로 B 가 된 행을 전부 드러낸다."""
import json, re, collections, sys
D="/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
rows=json.load(open(f"{D}/out/G_match.json"))
FIXTURE_FN = re.compile(r"잘못된|잘못되|fixtures:|correct|fault|fail|ok\.mp4|-1080|_user\.mp4|okr\d|failr\d")
def prov(r):
    vk=r["vk"] or ""; fn=r["fn"] or ""
    if vk.startswith("reference/"): return "A"
    if vk.startswith("fixtures/"): return "B-vk"
    if vk.startswith("uploads/"): return "D"
    if "talkv" in fn or fn.startswith("_dJMca"): return "C"
    if "belle" in fn.lower(): return "E"
    if FIXTURE_FN.search(fn): return "B-regex"
    return "F"
c=collections.Counter(prov(r) for r in rows)
print("분류 결과:",dict(c))
print("B 합계 =",c["B-vk"]+c["B-regex"])
print()
print("--- vk 없이 '파일명 정규식만'으로 정은지 fixture 판정된 행 ---")
g=collections.Counter()
for r in rows:
    if prov(r)=="B-regex":
        g[(r["fn"],r["ref"],r["frames"])]+=1
for (fn,ref,fr),n in sorted(g.items(), key=lambda kv:-kv[1]):
    hit=FIXTURE_FN.search(fn).group(0)
    print(f"  x{n:3d}  match='{hit}'  frames={fr:4d}  ref={ref:24s} fn={fn}")
print()
print("--- '_user.mp4' 로만 정은지 fixture 가 된 행 ---")
u=[r for r in rows if prov(r)=="B-regex" and FIXTURE_FN.search(r['fn']).group(0)=="_user.mp4"]
print("  건수 =",len(u), " 고유 파일명 =",sorted({r['fn'] for r in u}))
print()
print("--- F(출처불명) 로 남은 행의 파일명 ---")
fcnt=collections.Counter((r["fn"] or "<none>", r["ref"], r["frames"]) for r in rows if prov(r)=="F")
for (fn,ref,fr),n in sorted(fcnt.items(), key=lambda kv:-kv[1]):
    print(f"  x{n:3d}  frames={fr:4d}  ref={ref:24s} fn={fn}")
