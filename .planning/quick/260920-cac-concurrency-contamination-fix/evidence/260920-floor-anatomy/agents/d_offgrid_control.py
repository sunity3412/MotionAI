"""조사 D 통제군 2 — 시간격자 몫을 제대로 잰다.

(b) 최근접 재표집은 기준 프레임 값을 그대로 고르므로 DTW 가 무손실로 되돌린다(전부 0.00).
    실제 라이브는 기준 격자와 겹치지 않는 '사이 순간'을 샘플한다.
(b2) 기준 각도를 9fps 격자에 선형보간(위상 반스텝 어긋나게)해 학생으로 투입.
     같은 영상·같은 사람·같은 포즈추정 결과 위에서 '샘플 순간만' 다르게 한 조건.
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

STUDENT_FPS = 9.0
out = []
P = out.append
P("=" * 112)
P("13. 통제군 2 — 같은 영상, 샘플 '순간'만 어긋나게 (9fps 선형보간, 위상 반스텝)")
P("    기계(identity)=0.00 은 이미 확인됨. 여기서 나오는 값 = 순수 시간격자 몫의 상한")
P("=" * 112)
P(f"{'동작':24s}{'(b2)스칼라':>11s}{'(b2)최대관절':>13s}{'(c)live바닥':>12s}"
  f"{'시간격자 몫':>12s}{'나머지':>9s}{'라벨':>9s}")
det = []
for m in sorted(refs):
    rd = refs[m]
    A = H.ref_matrix(rd)
    fps = H.ref_fps_of(rd) or 15.0
    T = A.shape[0]
    n9 = max(2, int(round(T * STUDENT_FPS / fps)))
    # 위상 반스텝 어긋난 9fps 격자 (기준 프레임 사이 순간)
    step = (T - 1) / max(n9 - 1, 1)
    t = np.clip(np.arange(n9) * step + step / 2.0, 0, T - 1)
    lo = np.floor(t).astype(int); hi = np.minimum(lo + 1, T - 1); w = (t - lo)[:, None]
    B = A[lo] * (1 - w) + A[hi] * w
    db, mb = H.deviate(B, rd)
    base = by.get((m, "correct")) or by.get((m, "self"))
    lab = "correct" if by.get((m, "correct")) else ("self" if by.get((m, "self")) else "-")
    c = float(np.median([np.median(r["dev"]) for r in base])) if base else float("nan")
    s = H.scalar(db)
    det.append((m, db, c, lab))
    P(f"{m:24s}{s:11.2f}{np.nanmax(db):13.2f}{c:12.1f}{s:12.2f}{c - s:9.2f}{lab:>9s}")

P("")
P("=" * 112)
P("14. (b2) 관절별 — 시간격자만 어긋났을 때의 관절 구성 (live 바닥의 관절 구성과 비교용)")
P("=" * 112)
P(f"{'동작':24s}" + "".join(f"{SHORT[k]:>9s}" for k in H.JOINT_KEYS))
for m, db, c, lab in det:
    P(f"{m:24s}" + "".join(f"{v:9.2f}" for v in db))

f_ = np.array([x[2] for x in det if np.isfinite(x[2])])
g_ = np.array([H.scalar(x[1]) for x in det if np.isfinite(x[2])])
P("")
P(f"시간격자 몫이 live 바닥에서 차지하는 비중(중앙): {np.median(g_ / np.maximum(f_, 1e-9)) * 100:.1f}%")
P(f"시간격자 몫 ~ live 바닥 상관: r={np.corrcoef(g_, f_)[0, 1]:+.2f}")

txt = "\n".join(out)
open(f"{D}/out/d_offgrid_control.txt", "w").write(txt + "\n")
print(txt)
