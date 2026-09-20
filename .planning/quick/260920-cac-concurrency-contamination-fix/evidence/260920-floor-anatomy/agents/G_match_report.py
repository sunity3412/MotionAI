"""조사 G 단계 2 — 매칭 정확도 집계. 계산은 G_match_compute.py 가 이미 했다.

여기서는 argmin / 마진 / 혼동표만 집계한다(새 채점 로직 0).
마진 정의 = (2등 거리 - 1등 거리) / 1등 거리 (§11-1 이 쓴 '1등 대비 2등 상대거리').
"""
from __future__ import annotations
import json, collections, sys
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
rows = json.load(open(f"{D}/out/G_match.json"))
REFS = sorted(rows[0]["dist"].keys())


def margin(d):
    v = sorted((x for x in d.values() if np.isfinite(x)))
    if len(v) < 2:
        return float("nan")
    return (v[1] - v[0]) / v[0] if v[0] > 0 else float("inf")


for r in rows:
    r["ok"] = (r["pred"] == r["ref"])
    r["margin"] = margin(r["dist"])
    r["src"] = r["vk"] or (f"fn:{r['fn']}" if r["fn"] else f"id:{r['id']}")


def acc(rs):
    n = len(rs)
    k = sum(1 for r in rs if r["ok"])
    return k, n, (k / n * 100 if n else float("nan"))


def q(vals):
    a = np.asarray([v for v in vals if np.isfinite(v)], dtype=float)
    if a.size == 0:
        return "n/a"
    return (f"n={a.size} min={a.min():.3f} p25={np.percentile(a,25):.3f} "
            f"med={np.median(a):.3f} p75={np.percentile(a,75):.3f} max={a.max():.3f}")


out = []
P = out.append

P("=" * 78)
P("조사 G — 매칭 정확도 재검 (전수 875건, 운영 motion_dtw 거리 argmin)")
P("=" * 78)
P("")
k, n, p = acc(rows)
P(f"[1] 분석 단위 전수 정확도 : {k}/{n} = {p:.1f}%")

# --- 고유 영상 단위 -----------------------------------------------------------
bysrc = collections.defaultdict(list)
for r in rows:
    bysrc[r["src"]].append(r)
# 한 소스 영상이 여러 ref 로 분석된 경우가 있으므로 (src, ref) 를 단위로 본다
bysrcref = collections.defaultdict(list)
for r in rows:
    bysrcref[(r["src"], r["ref"])].append(r)

uniq_major = []   # 다수결 예측이 맞나
uniq_mean = []    # 소스별 정확도 평균 (macro)
for (src, ref), rs in sorted(bysrcref.items()):
    preds = collections.Counter(r["pred"] for r in rs)
    maj = preds.most_common(1)[0][0]
    uniq_major.append(dict(src=src, ref=ref, n=len(rs), maj=maj, ok=(maj == ref),
                           acc=sum(1 for r in rs if r["ok"]) / len(rs),
                           label=collections.Counter(r["label"] for r in rs).most_common(1)[0][0],
                           preds=dict(preds)))
    uniq_mean.append(sum(1 for r in rs if r["ok"]) / len(rs))

km = sum(1 for u in uniq_major if u["ok"])
P(f"[2] 고유영상 단위 정확도  : {km}/{len(uniq_major)} = {km/len(uniq_major)*100:.1f}%  "
  f"(영상별 다수결 예측)")
P(f"    영상별 정확도 단순평균: {np.mean(uniq_mean)*100:.1f}%  (macro, 재분석 수 무관)")
P("")
P(f"    * 고유 소스 {len(bysrc)}개 / (소스,선택기준) 쌍 {len(uniq_major)}개 / 분석 {n}건")
P(f"    * 중복 배수 중앙값 {np.median([u['n'] for u in uniq_major]):.0f}회 "
  f"(최대 {max(u['n'] for u in uniq_major)}회)")
P("")

# --- label 별 ----------------------------------------------------------------
P("[3] label 별 정확도")
P(f"    {'label':10s}{'분석단위':>16s}{'고유영상단위':>18s}")
for lab in ["correct", "fault", "self", "upload", "unknown"]:
    rs = [r for r in rows if r["label"] == lab]
    if not rs:
        continue
    k1, n1, p1 = acc(rs)
    us = [u for u in uniq_major if u["label"] == lab]
    k2 = sum(1 for u in us if u["ok"])
    P(f"    {lab:10s}{k1:5d}/{n1:<5d}{p1:5.1f}%{k2:8d}/{len(us):<4d}"
      f"{(k2/len(us)*100 if us else float('nan')):6.1f}%")
P("")

# --- correct vs fault 동작별 ---------------------------------------------------
P("[4] correct(정은지 제대로) vs fault(정은지 일부러 실수) — 동작별")
P(f"    {'motion':26s}{'correct':>16s}{'fault':>16s}")
motions = sorted({r["ref"] for r in rows})
for m in motions:
    c = [r for r in rows if r["ref"] == m and r["label"] == "correct"]
    f = [r for r in rows if r["ref"] == m and r["label"] == "fault"]
    def fmt(rs):
        if not rs:
            return "-"
        k, nn, pp = acc(rs)
        return f"{k}/{nn} {pp:5.1f}%"
    P(f"    {m:26s}{fmt(c):>16s}{fmt(f):>16s}")
P("")

# --- 혼동표 ------------------------------------------------------------------
P("[5] 혼동 — 선택기준(정답) x argmin(예측), 분석 단위")
conf = collections.Counter((r["ref"], r["pred"]) for r in rows)
byref = collections.Counter(r["ref"] for r in rows)
for m in motions:
    tot = byref[m]
    hits = conf[(m, m)]
    P(f"    {m:26s} {hits:4d}/{tot:<4d} {hits/tot*100:5.1f}%")
    for (a, b), c in sorted(conf.items(), key=lambda x: -x[1]):
        if a == m and b != m:
            P(f"        -> {b:26s} {c:4d}")
P("")
P("[6] 오분류 쌍 전체 (분석 단위, 건수순)")
miss = [(a, b, c) for (a, b), c in conf.items() if a != b]
for a, b, c in sorted(miss, key=lambda x: -x[2]):
    labs = collections.Counter(r["label"] for r in rows if r["ref"] == a and r["pred"] == b)
    P(f"    {a:26s} -> {b:26s} {c:4d}  {dict(labs)}")
P("")

# --- 마진 --------------------------------------------------------------------
P("[7] 마진 분포 ((2등-1등)/1등)")
P(f"    맞춘 것 : {q([r['margin'] for r in rows if r['ok']])}")
P(f"    틀린 것 : {q([r['margin'] for r in rows if not r['ok']])}")
P("")
P("    label 별 (맞춘 것 / 틀린 것)")
for lab in ["correct", "fault", "self", "upload", "unknown"]:
    rs = [r for r in rows if r["label"] == lab]
    if not rs:
        continue
    P(f"      {lab:8s} 맞춤 {q([r['margin'] for r in rs if r['ok']])}")
    P(f"      {lab:8s} 틀림 {q([r['margin'] for r in rs if not r['ok']])}")
P("")

# --- 업로드 전용 --------------------------------------------------------------
P("[8] 실제 사용자 업로드만 (videoKey 가 uploads/ 로 시작)")
ups = [r for r in rows if (r["vk"] or "").startswith("uploads/")]
k, n2, p2 = acc(ups)
P(f"    분석 단위 {k}/{n2} = {p2:.1f}%   (label=upload {sum(1 for r in ups if r['label']=='upload')}건 "
  f"+ 파일명이 fault 인 업로드 {sum(1 for r in ups if r['label']!='upload')}건)")
upsrc = collections.defaultdict(list)
for r in ups:
    upsrc[(r["vk"], r["ref"])].append(r)
ku = sum(1 for kk, rs in upsrc.items()
         if collections.Counter(r["pred"] for r in rs).most_common(1)[0][0] == kk[1])
P(f"    고유영상 단위 {ku}/{len(upsrc)} = {ku/len(upsrc)*100:.1f}%")
P("")
P(f"    {'videoKey':62s}{'선택기준':24s}{'n':>3s} {'예측(다수결)':24s}{'마진중앙':>9s}")
for (vk, ref), rs in sorted(upsrc.items()):
    preds = collections.Counter(r["pred"] for r in rs)
    maj = preds.most_common(1)[0][0]
    mk = "OK " if maj == ref else "X  "
    P(f"    {mk}{vk[-58:]:59s}{ref:24s}{len(rs):3d} {maj:24s}"
      f"{np.median([r['margin'] for r in rs]):9.3f}")
P("")

# --- 고유영상 상세표 -----------------------------------------------------------
P("[9] 고유영상 x 선택기준 상세 (n>=1, 오분류 먼저)")
P(f"    {'ok':3s}{'source':52s}{'선택기준':24s}{'n':>4s}{'정확도':>8s} 예측분포")
for u in sorted(uniq_major, key=lambda x: (x["ok"], x["ref"], x["src"])):
    P(f"    {'OK ' if u['ok'] else 'X  '}{u['src'][-50:]:52s}{u['ref']:24s}{u['n']:4d}"
      f"{u['acc']*100:7.1f}% {u['preds']}")

txt = "\n".join(out)
open(f"{D}/out/G_match_report.txt", "w").write(txt)
print(txt)
