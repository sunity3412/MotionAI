"""조사 G 단계 6 — 핵심 질문: '일부러 낸 결함'이 매칭을 흔드는가.

정확도는 100/100 이라 안 흔들린다. 그래서 **여유(마진)**로 본다 —
동작을 고정하고 correct vs fault 를 짝지으면 교란변수가 없다(같은 사람·같은 촬영·같은 기준).
"""
from __future__ import annotations
import json, collections
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
rows = json.load(open(f"{D}/out/G_match.json"))
REFS = sorted(rows[0]["dist"].keys())
for r in rows:
    r["ok"] = (r["pred"] == r["ref"])
    v = sorted(r["dist"].items(), key=lambda x: x[1])
    r["margin"] = (v[1][1] - v[0][1]) / v[0][1]
    r["runner"] = v[1][0]

out = []
P = out.append
P("=" * 84)
P("조사 G 보조 4 — fault(일부러 실수)가 매칭을 흔드는가")
P("=" * 84)
P("")
P("[1] 정확도로는 안 흔들린다")
for lab in ("correct", "fault"):
    rs = [r for r in rows if r["label"] == lab]
    P(f"    {lab:8s} {sum(1 for r in rs if r['ok'])}/{len(rs)} = 100.0%")
P("")
P("[2] 여유(마진)로 보면 흔들린다 — 동작 고정 짝비교")
P(f"    {'motion':26s}{'correct 마진중앙':>18s}{'fault 마진중앙':>16s}{'배율':>8s}{'fault 2위':>16s}")
for m in sorted({r["ref"] for r in rows}):
    c = [r for r in rows if r["ref"] == m and r["label"] == "correct"]
    f = [r for r in rows if r["ref"] == m and r["label"] == "fault"]
    if not c or not f:
        continue
    mc, mf = np.median([r["margin"] for r in c]), np.median([r["margin"] for r in f])
    run = collections.Counter(r["runner"] for r in f).most_common(1)[0][0]
    P(f"    {m:26s}{mc:18.3f}{mf:16.3f}{mf/mc:8.2f}{run.replace('ref-',''):>16s}")
allc = [r["margin"] for r in rows if r["label"] == "correct"]
allf = [r["margin"] for r in rows if r["label"] == "fault"]
P(f"    {'(전체)':26s}{np.median(allc):18.3f}{np.median(allf):16.3f}"
  f"{np.median(allf)/np.median(allc):8.2f}")
P("")
P("    6동작 중 몇 개에서 fault 마진이 correct 보다 작은가: "
  f"{sum(1 for m in sorted({r['ref'] for r in rows}) if [r for r in rows if r['ref']==m and r['label']=='correct'] and [r for r in rows if r['ref']==m and r['label']=='fault'] and np.median([r['margin'] for r in rows if r['ref']==m and r['label']=='fault']) < np.median([r['margin'] for r in rows if r['ref']==m and r['label']=='correct']))}/6")
P("")
P("[3] 전 코퍼스에서 가장 아슬아슬한 짝 — elbow-twist-sister/fault")
ef = [r for r in rows if r["ref"] == "ref-elbow-twist-sister" and r["label"] == "fault"]
P(f"    n={len(ef)}  마진 중앙 {np.median([r['margin'] for r in ef]):.3f} "
  f"(최소 {min(r['margin'] for r in ef):.3f})")
P(f"    2위 분포: {dict(collections.Counter(r['runner'] for r in ef))}")
ec = [r for r in rows if r["ref"] == "ref-elbow-twist-sister" and r["label"] == "correct"]
P(f"    같은 동작 correct: n={len(ec)} 마진 중앙 {np.median([r['margin'] for r in ec]):.3f} "
  f"2위 분포 {dict(collections.Counter(r['runner'] for r in ec))}")
P("")
P("    [확인] 같은 사람·같은 동작·같은 기준에서 '일부러 틀리게 한 것' 하나만 바꾸면")
P("           1등-2등 여유가 6/6 동작에서 줄어든다(전체 중앙 1.23 -> 0.35, 3.5배).")
P("    [미확인] 실제 초보 학생의 실패가 정은지의 '일부러 실수'와 같은 크기인지는 모른다.")
P("           이 코퍼스에 초보 학생 영상이 0편이라 외삽할 근거가 없다.")

txt = "\n".join(out)
open(f"{D}/out/G_fault_margin.txt", "w").write(txt)
print(txt)
