"""반증 R3 — 통제군을 바꾼다: 행렬은 그대로 두고 **정렬 경로만** 갈아끼운다.

주장의 identity 통제(같은 행렬 넣기)는 퇴화다 — DTW 가 대각선을 고르면 자명히 0 이다.
그래서 이 통제는 반대로 간다: live 와 **같은 두 행렬**(학생 재추출본 vs 기준 doc)에
  (a) 운영 DTW 가 고른 경로          → live 바닥
  (b) 선형 대응 경로(시간 비례)      → self 라벨에서는 이게 '참 대응'이다(같은 영상)
  (c) (scale, offset) 격자 위 최적 선형 경로 → 트리밍 차이까지 흡수한 선형 최선
을 각각 넣는다. deviation 계산은 전부 운영 `motiondtw.per_joint_deviation`.

(b)/(c) 가 (a) 보다 크게 낮으면 받침대의 그만큼은 **값이 아니라 경로**에서 난다.
"""
from __future__ import annotations
import json, sys, collections
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402
from sunity_shared.analysis import motiondtw  # noqa: E402

JK = H.JOINT_KEYS
rows = json.load(open(f"{D}/facts.json"))
refs = H.load_references()
students = {s["id"]: s for s in H.load_students()}


def lin_path(tu, tr, u0=0.0, u1=1.0):
    """학생 [u0,u1] 구간을 기준 전체에 시간 비례로 대응시킨 경로."""
    n = max(tu, tr)
    us = np.clip(np.round((u0 + (u1 - u0) * np.linspace(0, 1, n)) * (tu - 1)).astype(int), 0, tu - 1)
    rs = np.clip(np.round(np.linspace(0, 1, n) * (tr - 1)).astype(int), 0, tr - 1)
    return list(zip(us.tolist(), rs.tolist()))


def sc(dev):
    d = np.asarray(dev, float); d = d[np.isfinite(d)]
    return float(np.median(d)) if d.size else float("nan")


by = collections.defaultdict(list)
for r in rows:
    if r.get("dev") and all(np.isfinite(r["dev"])):
        by[(r["ref"], r["label"])].append(r)

out, P = [], None
out = []
P = out.append
P("=" * 112)
P("R3. 경로 통제 — 같은 두 행렬에 경로만 갈아끼운다 (deviation = 운영 per_joint_deviation)")
P("  (a) DTW    : 운영 _deviation_against 가 고른 경로 (= live 바닥)")
P("  (b) 선형    : 시간 비례 대응 (self 라벨에서는 참 대응)")
P("  (c) 최선선형: (시작,끝) 격자 위 선형 경로 중 최소")
P("=" * 112)
P(f"{'동작':24s}{'라벨':8s}{'(a)DTW':>8s}{'(b)선형':>8s}{'(c)최선선형':>11s}"
  f"{'a-c':>7s}{'경로몫%':>9s}{'최선(시작,끝)':>14s}")

res = []
for m in sorted(refs):
    rd = refs[m]
    R = H.ref_matrix(rd)
    rfps = H.ref_fps_of(rd)
    for lab in ("self", "correct", "fault"):
        rs = by.get((m, lab))
        if not rs:
            continue
        scs = [r["scalar"] for r in rs]
        pick = rs[int(np.argmin([abs(s - np.median(scs)) for s in scs]))]
        U = H.student_matrix(students[pick["id"]])
        dev_dtw, match = H.deviate(U, rd)
        a = sc(dev_dtw)
        b = sc(motiondtw.per_joint_deviation(lin_path(U.shape[0], R.shape[0]), U, R, ref_fps=rfps))
        best, bestk = np.inf, None
        for u0 in np.linspace(0.0, 0.30, 13):
            for u1 in np.linspace(0.70, 1.0, 13):
                v = sc(motiondtw.per_joint_deviation(
                    lin_path(U.shape[0], R.shape[0], u0, u1), U, R, ref_fps=rfps))
                if v < best:
                    best, bestk = v, (u0, u1)
        P(f"{m:24s}{lab:8s}{a:8.1f}{b:8.1f}{best:11.1f}{a-best:7.1f}"
          f"{(a-best)/a*100 if a else 0:8.0f}%{f'({bestk[0]:.2f},{bestk[1]:.2f})':>14s}")
        res.append((m, lab, a, b, best))
    P("")

P("요약 — 실력차0 라벨(correct 우선, 없으면 self)만:")
seen = set()
tot = []
for m, lab, a, b, c in res:
    if m in seen or lab == "fault":
        continue
    if lab == "correct" or not any(x[0] == m and x[1] == "correct" for x in res):
        seen.add(m); tot.append((m, lab, a, b, c))
for m, lab, a, b, c in tot:
    P(f"  {m:24s}{lab:8s} DTW {a:5.1f} → 최선선형 {c:5.1f}   경로가 만든 몫 {a-c:5.1f}도 ({(a-c)/a*100:.0f}%)")
P("")
P(f"  경로몫 중앙값: {np.median([(a-c)/a*100 for _, _, a, _, c in tot]):.0f}%")
txt = "\n".join(out)
open(f"{D}/out/r_path_control.txt", "w").write(txt + "\n")
print(txt)
