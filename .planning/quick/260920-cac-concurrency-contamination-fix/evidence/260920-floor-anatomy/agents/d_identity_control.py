"""조사 D 통제군 — 바닥이 '집계·DTW 기계'에서 나는가, '입력'에서 나는가.

(a) identity : 기준 행렬 그 자체를 학생으로 -> H.deviate (운영 _deviation_against)
(b) 9fps 격자: 기준을 학생 격자(9fps)로 최근접 재표집해 학생으로 투입
(c) live self/correct : facts.json 의 실제 바닥
(a)가 0 이면 기계는 결백하다. (b)-(a) 가 시간격자 몫. (c)-(b) 가 나머지(재추출/포즈/실력).
"""
from __future__ import annotations
import json, sys, collections
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

SHORT = {"left_elbow": "L-elb", "right_elbow": "R-elb", "left_shoulder": "L-sho",
         "right_shoulder": "R-sho", "left_hip": "L-hip", "right_hip": "R-hip",
         "left_knee": "L-kne", "right_knee": "R-kne"}
rows = json.load(open(f"{D}/facts.json"))
refs = H.load_references()
by = collections.defaultdict(list)
for r in rows:
    if r.get("dev") and all(np.isfinite(r["dev"])):
        by[(r["ref"], r["label"])].append(r)

out = []
P = out.append
P("=" * 104)
P("10. 통제군 — 기준을 학생으로 되먹였을 때의 관절별 편차")
P("    (a) identity  : 같은 행렬, 같은 시간격자")
P("    (b) 9fps 재표집: 같은 영상, 학생 격자(운영 추출 fps)로 최근접 재표집")
P("    (c) live 바닥  : correct(없으면 self) 실측")
P("=" * 104)
P(f"{'동작':24s}{'(a)identity':>13s}{'(b)9fps':>10s}{'(c)live':>9s}{'라벨':>9s}"
  f"{'(b) 관절 최대':>14s}{'(a)dtw':>9s}{'(b)dtw':>9s}")
STUDENT_FPS = 9.0
detail = []
for m in sorted(refs):
    rd = refs[m]
    A = H.ref_matrix(rd)
    fps = H.ref_fps_of(rd) or 15.0
    da, ma = H.deviate(A, rd)
    n9 = max(2, int(round(A.shape[0] * STUDENT_FPS / fps)))
    idx = np.clip(np.round(np.linspace(0, A.shape[0] - 1, n9)).astype(int), 0, A.shape[0] - 1)
    db, mb = H.deviate(A[idx], rd)
    base = by.get((m, "correct")) or by.get((m, "self"))
    lab = "correct" if by.get((m, "correct")) else ("self" if by.get((m, "self")) else "-")
    c = float(np.median([np.median(r["dev"]) for r in base])) if base else float("nan")
    detail.append((m, da, db, base, lab))
    P(f"{m:24s}{H.scalar(da):13.2f}{H.scalar(db):10.2f}{c:9.1f}{lab:>9s}"
      f"{np.nanmax(db):14.1f}{ma.distance:9.1f}{mb.distance:9.1f}")

P("")
P("=" * 104)
P("11. (b) 9fps 재표집 — 관절별. 실력·체형·촬영각도가 전부 같은(동일 영상) 조건의 관절 구성")
P("=" * 104)
P(f"{'동작':24s}" + "".join(f"{SHORT[k]:>9s}" for k in H.JOINT_KEYS) + f"{'CV':>7s}")
for m, da, db, base, lab in detail:
    cv = float(np.nanstd(db) / max(np.nanmean(db), 1e-9))
    P(f"{m:24s}" + "".join(f"{v:9.1f}" for v in db) + f"{cv:7.2f}")

P("")
P("=" * 104)
P("12. 분해 — 바닥의 몇 도가 어디서 나는가 (동작별, 스칼라 기준)")
P("=" * 104)
P(f"{'동작':24s}{'기계(a)':>9s}{'시간격자(b-a)':>14s}{'나머지(c-b)':>13s}{'live(c)':>9s}{'라벨':>9s}")
for m, da, db, base, lab in detail:
    if not base:
        continue
    a, b = H.scalar(da), H.scalar(db)
    c = float(np.median([np.median(r["dev"]) for r in base]))
    P(f"{m:24s}{a:9.2f}{b - a:14.2f}{c - b:13.2f}{c:9.1f}{lab:>9s}")

txt = "\n".join(out)
open(f"{D}/out/d_identity_control.txt", "w").write(txt + "\n")
print(txt)
