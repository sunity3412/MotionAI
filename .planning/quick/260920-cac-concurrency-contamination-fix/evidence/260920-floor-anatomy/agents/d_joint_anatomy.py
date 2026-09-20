"""조사 D — 바닥의 관절 해부.

입력: m13/facts.json (dev[8] = 관절별 median|Δ각도|, H.deviate=운영 _deviation_against 산출)
운영 상수는 전부 운영 모듈에서 import 한다 (재구현 0):
  ipsf_criteria._ANGLE_TOLERANCE_DEG / _SLOPE / _ANGLE_CAP
  deduction_engine.PER_RECORD_DEDUCTION_CAP / EXECUTION_DEDUCTION_CAP / SCORE_FLOOR
"""
from __future__ import annotations
import json, sys, collections
import numpy as np

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
from sunity_shared.analysis import skeleton, ipsf_criteria, deduction_engine  # noqa: E402

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
JK = list(skeleton.JOINT_KEYS)
SHORT = {"left_elbow": "L-elb", "right_elbow": "R-elb", "left_shoulder": "L-sho",
         "right_shoulder": "R-sho", "left_hip": "L-hip", "right_hip": "R-hip",
         "left_knee": "L-kne", "right_knee": "R-kne"}

TOL = ipsf_criteria._ANGLE_TOLERANCE_DEG
SLOPE = ipsf_criteria._SLOPE
CAP_CRIT = ipsf_criteria._ANGLE_CAP
CAP_REC = deduction_engine.PER_RECORD_DEDUCTION_CAP
CAP_EXEC = deduction_engine.EXECUTION_DEDUCTION_CAP
FLOOR = deduction_engine.SCORE_FLOOR

rows = json.load(open(f"{D}/facts.json"))
refs = json.load(open(f"{D}/references_full.json")); refs.pop("_release", None)

by = collections.defaultdict(list)
for r in rows:
    if r.get("dev") and all(np.isfinite(r["dev"])):
        by[(r["ref"], r["label"])].append(r)

MOTIONS = ["ref-kip-up", "ref-peter-pan", "ref-power-spin", "ref-climb",
           "ref-elbow-twist-sister", "ref-pdshape",
           "ref-sideway-spin", "ref-combo", "ref-invert", "ref-foxtop", "ref-foxtop-split"]
LABELS = ["correct", "fault", "self"]


def med(rs, j):
    return float(np.median([r["dev"][j] for r in rs]))


def devmat(rs):
    return np.array([r["dev"] for r in rs], dtype=float)  # (n,8)


out = []
P = out.append

# ─────────────────────────────────────────────────────────────────────
P("=" * 108)
P("1. 동작 x 라벨 x 관절  —  관절별 median |Δ각도| (도).  맨 오른쪽 = 8개의 중앙값(=조사 스칼라)")
P(f"   운영 tol = {TOL}도 (ipsf_criteria._ANGLE_TOLERANCE_DEG). tol 초과 관절은 '*' 표시")
P("=" * 108)
P(f"{'동작':24s}{'라벨':9s}{'n':>4s}" + "".join(f"{SHORT[k]:>9s}" for k in JK)
  + f"{'중앙':>8s}{'최소':>7s}{'최대':>7s}")
table1 = {}
for m in MOTIONS:
    for lab in LABELS:
        rs = by.get((m, lab))
        if not rs:
            continue
        vals = [med(rs, j) for j in range(8)]
        table1[(m, lab)] = vals
        cells = "".join(f"{v:8.1f}" + ("*" if v > TOL else " ") for v in vals)
        P(f"{m:24s}{lab:9s}{len(rs):4d}{cells}{np.median(vals):8.1f}{min(vals):7.1f}{max(vals):7.1f}")
    P("")

# ─────────────────────────────────────────────────────────────────────
P("=" * 108)
P("2. 바닥은 고른가, 1~2개 관절이 지고 있나 — correct/self(실력차 0 바닥) 기준")
P("   집중도 = 상위1 관절 / 8관절 합,  상위2 = 상위2 합 / 8관절 합.  고르면 각각 0.125 / 0.25")
P("=" * 108)
P(f"{'동작':24s}{'라벨':9s}{'상위1':>8s}{'상위2':>8s}{'최대/최소':>10s}{'tol초과 관절수':>14s}  {'큰 순서(상위3)'}")
for m in MOTIONS:
    for lab in ("correct", "self"):
        v = table1.get((m, lab))
        if not v:
            continue
        a = np.array(v); s = a.sum()
        o = np.argsort(-a)
        P(f"{m:24s}{lab:9s}{a[o[0]]/s:8.3f}{(a[o[0]]+a[o[1]])/s:8.3f}"
          f"{a.max()/max(a.min(),1e-9):10.1f}{int((a > TOL).sum()):14d}  "
          + ", ".join(f"{SHORT[JK[i]]} {a[i]:.1f}" for i in o[:3]))

# ─────────────────────────────────────────────────────────────────────
P("")
P("=" * 108)
P("3. correct -> fault 로 갈 때 어느 관절이 움직이나 (Δ = median_fault - median_correct, 도)")
P("   yaml = judging_data/criteria/ref-*.yaml 의 objective angle criteria 보유 관절")
P("   doc  = 기준 doc techniqueProfile.jointExpectations == 'extend' 관절")
P("=" * 108)
import yaml as _yaml
CRIT_DIR = "/Users/kimtaesung/Dev/SunityMotion/backend/judging_data/criteria"
yaml_joints, doc_extend = {}, {}
for m in MOTIONS:
    try:
        d = _yaml.safe_load(open(f"{CRIT_DIR}/{m}.yaml"))
        js = set()
        for mom, lst in (d.get("criteria") or {}).items():
            for c in lst or []:
                js.add(c.get("joint"))
        yaml_joints[m] = js
    except FileNotFoundError:
        yaml_joints[m] = set()
    tp = (refs.get(m) or {}).get("techniqueProfile") or {}
    doc_extend[m] = {k for k, v in (tp.get("jointExpectations") or {}).items() if v == "extend"}

for m in MOTIONS:
    c, f = table1.get((m, "correct")), table1.get((m, "fault"))
    if not c or not f:
        continue
    d = np.array(f) - np.array(c)
    o = np.argsort(-d)
    P(f"\n{m}")
    P(f"  yaml criteria 관절: {sorted(SHORT[j] for j in yaml_joints[m]) or '없음(criteria 0)'}"
      f"   |   doc extend 관절: {sorted(SHORT[j] for j in doc_extend[m]) or '없음'}")
    P(f"  {'관절':>8s}{'correct':>9s}{'fault':>9s}{'Δ':>8s}{'배율':>7s}   표식")
    for i in o:
        tag = []
        if JK[i] in yaml_joints[m]:
            tag.append("yaml")
        if JK[i] in doc_extend[m]:
            tag.append("doc-extend(→angle_vs_ref 제외 대상)")
        P(f"  {SHORT[JK[i]]:>8s}{c[i]:9.1f}{f[i]:9.1f}{d[i]:+8.1f}{f[i]/max(c[i],1e-9):7.2f}   {' '.join(tag)}")

# ─────────────────────────────────────────────────────────────────────
P("")
P("=" * 108)
P("4. 관절 수준 분리 — 관절별 fault/correct 분리비 + 분포 겹침 (n = 재분석 반복 포함)")
P("   겹침 = correct 최대 >= fault 최소 이면 '겹침'(그 관절 하나로는 두 무리를 못 가른다)")
P("=" * 108)
for m in MOTIONS:
    rc, rf = by.get((m, "correct")), by.get((m, "fault"))
    if not rc or not rf:
        continue
    C, F = devmat(rc), devmat(rf)
    P(f"\n{m}   (correct n={len(rc)} 고유영상 {len({r['vk'] for r in rc})} / "
      f"fault n={len(rf)} 고유영상 {len({r['vk'] for r in rf})})")
    P(f"  {'관절':>8s}{'c중앙':>8s}{'f중앙':>8s}{'비율':>7s}{'c최대':>8s}{'f최소':>8s}  판정")
    order = np.argsort(-(np.median(F, 0) / np.maximum(np.median(C, 0), 1e-9)))
    for i in order:
        cm, fm = float(np.median(C[:, i])), float(np.median(F[:, i]))
        sep = "분리" if C[:, i].max() < F[:, i].min() else ("역전" if fm < cm else "겹침")
        P(f"  {SHORT[JK[i]]:>8s}{cm:8.1f}{fm:8.1f}{fm/max(cm,1e-9):7.2f}"
          f"{C[:, i].max():8.1f}{F[:, i].min():8.1f}  {sep}")

# ─────────────────────────────────────────────────────────────────────
P("")
P("=" * 108)
P("5. 집계 방식을 바꾸면 분리가 살아나는가 — 사전에 고정된 순서통계 family (문턱 고르기 없음)")
P("   각 분석마다 8개 관절값을 집계 -> 그 집계치의 correct/fault 중앙값 비율")
P("   fault관절限 = 3절에서 Δ 최대였던 관절 1개만 (같은 데이터로 고른 것 = 커브핏 위험, 표시함)")
P("=" * 108)
AGG = {
    "median(현행)": lambda A: np.median(A, 1),
    "mean": lambda A: A.mean(1),
    "max": lambda A: A.max(1),
    "top2 평균": lambda A: np.sort(A, 1)[:, -2:].mean(1),
    "top3 평균": lambda A: np.sort(A, 1)[:, -3:].mean(1),
    "min": lambda A: A.min(1),
}
P(f"{'동작':24s}" + "".join(f"{k:>14s}" for k in AGG) + f"{'fault관절限':>14s}  (그 관절)")
for m in MOTIONS:
    rc, rf = by.get((m, "correct")), by.get((m, "fault"))
    if not rc or not rf:
        continue
    C, F = devmat(rc), devmat(rf)
    cells = ""
    for k, fn in AGG.items():
        cm, fm = float(np.median(fn(C))), float(np.median(fn(F)))
        cells += f"{fm/max(cm,1e-9):14.2f}"
    d = np.median(F, 0) - np.median(C, 0)
    j = int(np.argmax(d))
    cm, fm = float(np.median(C[:, j])), float(np.median(F[:, j]))
    P(f"{m:24s}{cells}{fm/max(cm,1e-9):14.2f}  ({SHORT[JK[j]]})")

# ─────────────────────────────────────────────────────────────────────
P("")
P("=" * 108)
P("6. 소비처까지 — 운영 감점식을 관절별 dev 에 그대로 적용")
P(f"   over=max(0, dev-{TOL}) / raw=over*{SLOPE} / per-record cap {CAP_REC} / 집계캡 {CAP_EXEC} / 바닥 {FLOOR}")
P("   final = max(FLOOR, 100 - min(CAP_EXEC, Σ|points|))   [angle_vs_reference 계열만, 다른 criterion 0 가정]")
P("=" * 108)


def engine_points(dev_vec, exclude=()):
    """운영 규칙 그대로 — 관절별 record points(절대값) 리스트."""
    pts = []
    for i, jk in enumerate(JK):
        if jk in exclude:
            continue          # profile.expects_extension gate (_emit_reference_relative)
        v = float(dev_vec[i])
        if not np.isfinite(v) or v <= 0.0:
            continue
        over = v - TOL
        if over <= 0.0:
            continue          # deduction_engine: over<=0 -> record 미방출
        capped = round(min(over * SLOPE, CAP_CRIT), 1)
        pts.append(min(capped, CAP_REC))
    return pts


def final_of(dev_vec, exclude=()):
    pts = engine_points(dev_vec, exclude)
    return max(FLOOR, round(100.0 - min(CAP_EXEC, sum(pts)))), len(pts), sum(pts)


P(f"{'동작':24s}{'라벨':9s}{'n':>4s}{'tol초과관절':>12s}{'Σ감점':>9s}{'집계캡히트':>11s}{'final':>8s}"
  f"{'final(doc-extend제외)':>22s}")
cons = {}
for m in MOTIONS:
    for lab in LABELS:
        rs = by.get((m, lab))
        if not rs:
            continue
        fs, ns, ss, hit, fs2 = [], [], [], 0, []
        for r in rs:
            f1, n1, s1 = final_of(r["dev"])
            f2, _, _ = final_of(r["dev"], exclude=doc_extend[m])
            fs.append(f1); ns.append(n1); ss.append(s1); fs2.append(f2)
            hit += 1 if s1 >= CAP_EXEC else 0
        cons[(m, lab)] = (float(np.median(fs)), float(np.median(ns)), float(np.median(ss)))
        P(f"{m:24s}{lab:9s}{len(rs):4d}{np.median(ns):12.1f}{np.median(ss):9.1f}"
          f"{hit/len(rs)*100:10.0f}%{np.median(fs):8.0f}{np.median(fs2):22.0f}")
    P("")

P("=" * 108)
P("6-b. 화면 점수 격차 (correct final - fault final)  <- '이 축이 결함을 점수로 가르는가'")
P("=" * 108)
P(f"{'동작':24s}{'correct final':>15s}{'fault final':>13s}{'격차':>8s}")
for m in MOTIONS:
    c, f = cons.get((m, "correct")), cons.get((m, "fault"))
    if not c or not f:
        continue
    P(f"{m:24s}{c[0]:15.0f}{f[0]:13.0f}{c[0]-f[0]:+8.0f}")

txt = "\n".join(out)
open(f"{D}/out/d_joint_anatomy.txt", "w").write(txt + "\n")
print(txt)
