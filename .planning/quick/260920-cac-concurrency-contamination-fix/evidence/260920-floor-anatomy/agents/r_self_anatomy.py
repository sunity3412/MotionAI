"""반증 R2 — 'self' 바닥이 정말 입력 키포인트에서 나는가, 아니면 시간대응(정렬)에서 나는가.

주장: identity 통제 0.00 + 시간격자 1~2도 → 남는 건 키포인트.
반증 축: identity 통제는 **같은 행렬**이라 자명하게 0 이다(퇴화 통제). 정렬이 바닥을
만드는 경로는 identity 로 배제되지 않는다. 그래서 정렬-무관 하한을 따로 잰다:

  분위수 편차(quantile) = 두 시계열의 '값 분포' 차이. 시간 대응을 **완전히 자유롭게**
  풀었을 때 남는 값 차이 (순서보존 매칭의 최적 비용). 
    live floor ≈ quantile  → 정렬은 이미 최적, 남은 건 값 자체 = 키포인트 (주장 지지)
    live floor >> quantile → 같은 값 분포인데 시간 대응이 못 붙었다 = 기계/정렬 (주장 반증)
"""
from __future__ import annotations
import json, sys, collections
import numpy as np

D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
import harness as H  # noqa: E402

JK = H.JOINT_KEYS
SHORT = {"left_elbow": "L-elb", "right_elbow": "R-elb", "left_shoulder": "L-sho",
         "right_shoulder": "R-sho", "left_hip": "L-hip", "right_hip": "R-hip",
         "left_knee": "L-kne", "right_knee": "R-kne"}

rows = json.load(open(f"{D}/facts.json"))
refs = H.load_references()
students = {s["id"]: s for s in H.load_students()}

out, P = [], None
out = []
P = out.append


def quantile_dev(u, r, n=400):
    """정렬-무관 하한: 두 열의 분위수 함수 차이의 median |Δ| (도)."""
    u = u[np.isfinite(u)]; r = r[np.isfinite(r)]
    if u.size < 2 or r.size < 2:
        return float("nan")
    g = np.linspace(0, 1, n)
    return float(np.median(np.abs(np.quantile(u, g) - np.quantile(r, g))))


P("=" * 118)
P("R2-A. self/correct 바닥의 해부 — live DTW 바닥 vs 정렬-무관 분위수 하한")
P("  live   = facts.dev (운영 _deviation_against 산출) 의 그 라벨 중앙값")
P("  quant  = 같은 두 시계열의 분위수 편차 (시간 대응을 자유롭게 푼 하한)")
P("  live-quant 가 크면 = 값은 맞는데 시간 대응이 못 붙은 것 = 기계/정렬 몫")
P("=" * 118)
P(f"{'동작':24s}{'라벨':8s}{'live':>7s}{'quant':>7s}{'정렬몫':>8s}{'정렬몫%':>9s}"
  f"{'U프레임':>8s}{'R프레임':>8s}{'매칭ref%':>9s}{'매칭U%':>8s}")

by = collections.defaultdict(list)
for r in rows:
    if r.get("dev") and all(np.isfinite(r["dev"])):
        by[(r["ref"], r["label"])].append(r)

summary = []
for m in sorted(refs):
    rd = refs[m]
    for lab in ("correct", "self"):
        rs = by.get((m, lab))
        if not rs:
            continue
        R = H.ref_matrix(rd)
        # 대표 1건 (그 라벨 중 스칼라가 중앙값에 가장 가까운 분석)
        sc = [r["scalar"] for r in rs]
        pick = rs[int(np.argmin([abs(s - np.median(sc)) for s in sc]))]
        U = H.student_matrix(students[pick["id"]])
        live_j = [float(np.median([r["dev"][j] for r in rs])) for j in range(len(JK))]
        q_j = [quantile_dev(U[:, j], R[:, j]) for j in range(len(JK))]
        live, q = float(np.median(live_j)), float(np.median(q_j))
        rcov = (pick["rend"] - pick["rstart"] + 1) / R.shape[0] * 100 if pick["rend"] is not None else float("nan")
        ucov = (pick["uend"] - pick["ustart"] + 1) / U.shape[0] * 100 if pick["uend"] is not None else float("nan")
        P(f"{m:24s}{lab:8s}{live:7.1f}{q:7.1f}{live-q:8.1f}{(live-q)/live*100 if live else 0:8.0f}%"
          f"{U.shape[0]:8d}{R.shape[0]:8d}{rcov:8.0f}%{ucov:7.0f}%")
        summary.append((m, lab, live, q, live_j, q_j))
        break  # 라벨 하나만 (correct 우선)

P("")
P("=" * 118)
P("R2-B. 관절별 — live 바닥 vs 분위수 하한 (도)")
P("=" * 118)
P(f"{'동작':24s}{'':6s}" + "".join(f"{SHORT[j]:>9s}" for j in JK))
for m, lab, live, q, live_j, q_j in summary:
    P(f"{m:24s}{'live':>6s}" + "".join(f"{v:9.1f}" for v in live_j))
    P(f"{'':24s}{'quant':>6s}" + "".join(f"{v:9.1f}" for v in q_j))
    P(f"{'':24s}{'차':>6s}" + "".join(f"{a-b:9.1f}" for a, b in zip(live_j, q_j)))

P("")
P("=" * 118)
P("R2-C. self 라벨의 정체 확인 — videoKey 가 그 동작의 기준 영상인가")
P("=" * 118)
for r in rows:
    if r["label"] == "self":
        P(f"  {r['ref']:24s} vk={r['vk']}  frames={r['frames']}  dtw={r['dtw']:.1f}  scalar={r['scalar']:.1f}")

P("")
P("=" * 118)
P("R2-D. 추출기 계보 — 학생 경로 extractor vs 기준 doc 메타")
P("=" * 118)
P("  학생 extractor 분포: " + str(collections.Counter(
    json.dumps(r.get("extractor"), ensure_ascii=False) for r in rows).most_common(5)))
for m in sorted(refs):
    rd = refs[m]
    meta = {k: rd.get(k) for k in ("poseEngine", "extractor", "engine", "backbone",
                                   "createdAt", "updatedAt", "anglesFrames", "version",
                                   "pipelineVersion", "sourceVersion")}
    P(f"  {m:24s}" + " ".join(f"{k}={v}" for k, v in meta.items() if v is not None))

txt = "\n".join(out)
open(f"{D}/out/r_self_anatomy.txt", "w").write(txt + "\n")
print(txt)
