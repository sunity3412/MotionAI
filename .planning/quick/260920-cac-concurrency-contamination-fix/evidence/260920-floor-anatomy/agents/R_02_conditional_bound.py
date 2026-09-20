"""R-2 (반증) — E-3 의 투영 왜곡 상한은 '균일한 임의 자세' 위에서 잰 것이다.
E-3 스스로 δ=20° 에서 3D 내각이 45~135° 인 구간은 median 13.6°, 바깥은 4.8~5.0°
라고 적었다 — 2.8 배 차이다. 실제 동작의 각도 분포가 민감 구간에 몰려 있다면
E-3 의 median 곡선은 과소 상한이고, '바닥을 만들려면 δ≈69° 가 필요하다'도 과대다.

방법: E-3 시뮬을 그대로 다시 돌리되(같은 rng seed, 같은 운영 _angle_deg 호출),
각 표본의 δ=0 2D 각 a0 를 그 동작의 실제 저장 angles 분포에 맞춰 중요도 가중한다.
  w(sample) = p_motion(a0) / p_sim(a0)      (5도 폭 히스토그램)
그러고 가중 median |Δ| 곡선을 내고, 실측 바닥을 만들려면 필요한 δ 를 역산한다.
새 채점 코드는 없다 — 각도는 운영 features._angle_deg, 실측 각도는 저장 angles.
"""
import json, sys
import numpy as np
D = "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/feb97ca3-32a3-41c9-90c9-710b0eeb7095/scratchpad/m13"
sys.path.insert(0, D)
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
import harness as H
from sunity_shared.analysis.features import _angle_deg

rng = np.random.default_rng(20260920)
N = 40000


def rand_rot(n):
    q = rng.normal(size=(n, 4)); q /= np.linalg.norm(q, axis=1, keepdims=True)
    w, x, y, z = q.T
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
        np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
        np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1),
    ], 1)


def build(n):
    th = np.radians(rng.uniform(5, 175, n))
    L1 = rng.uniform(0.7, 1.4, n); L2 = rng.uniform(0.7, 1.4, n)
    ph = rng.uniform(0, 2 * np.pi, n)
    ba = np.stack([L1, np.zeros(n), np.zeros(n)], -1)
    bc = np.stack([L2 * np.cos(th), L2 * np.sin(th) * np.cos(ph), L2 * np.sin(th) * np.sin(ph)], -1)
    R = rand_rot(n)
    return np.einsum("nij,nj->ni", R, ba), np.einsum("nij,nj->ni", R, bc), np.degrees(th)


def yaw(v, deg):
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    M = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return v @ M.T


def ang2d(ba, bc):
    z = np.zeros(2)
    return np.array([_angle_deg(ba[i, :2], z, bc[i, :2]) for i in range(len(ba))])


BA, BC, TH = build(N)
a0 = ang2d(BA, BC)
DELTAS = (5, 10, 15, 20, 30, 45, 60, 90)
E = {d: np.abs(ang2d(yaw(BA, d), yaw(BC, d)) - a0) for d in DELTAS}

EDGES = np.arange(0, 185, 5.0)
sim_h, _ = np.histogram(a0[np.isfinite(a0)], bins=EDGES, density=True)
sim_bin = np.clip(np.digitize(a0, EDGES) - 1, 0, len(EDGES) - 2)


def wmedian(x, w):
    ok = np.isfinite(x) & (w > 0)
    x, w = x[ok], w[ok]
    o = np.argsort(x); x, w = x[o], w[o]
    c = np.cumsum(w) / w.sum()
    return float(x[np.searchsorted(c, 0.5)])


refs = H.load_references()
facts = json.load(open(f"{D}/facts.json"))
import collections
floors = collections.defaultdict(lambda: collections.defaultdict(list))
for r in facts:
    floors[r["ref"]][r["label"]].append(r["scalar"])

print("동작별 실제 각도 분포로 가중한 median |Δ2D각| 곡선 (도)")
hdr = "".join(f"{d:>8d}" for d in DELTAS)
print(f"{'motion':24s}{'바닥°':>7s}{'민감구간%':>10s}{hdr}{'필요δ(가중)':>12s}{'필요δ(E3)':>11s}")
E3_M = np.array([0.0, 2.23, 4.42, 6.52, 8.59, 12.50, 18.03, 22.38, 25.96])
E3_D = np.array([0, 5, 10, 15, 20, 30, 45, 60, 90])
out = []
for m, r in sorted(refs.items()):
    A = H.ref_matrix(r).ravel()
    A = A[np.isfinite(A)]
    emp_h, _ = np.histogram(A, bins=EDGES, density=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(sim_h > 0, emp_h / sim_h, 0.0)
    w = ratio[sim_bin]
    curve = [wmedian(E[d], w) for d in DELTAS]
    co = floors[m]["correct"]; se = floors[m]["self"]
    floor = float(np.median(co)) if co else (float(np.median(se)) if se else float("nan"))
    sens = float(((A >= 45) & (A <= 135)).mean())
    xs = np.array([0] + list(DELTAS), float); ys = np.array([0.0] + curve)
    need_w = float(np.interp(floor, ys, xs, left=0, right=np.inf))
    need_e3 = float(np.interp(floor, E3_M, E3_D, left=0, right=np.inf))
    out.append(dict(motion=m, floor=floor, sens=sens, curve=curve,
                    need_weighted=need_w, need_e3=need_e3))
    cs = "".join(f"{c:8.2f}" for c in curve)
    print(f"{m:24s}{floor:7.1f}{sens:10.1%}{cs}"
          f"{(need_w if np.isfinite(need_w) else 999):12.0f}{(need_e3 if np.isfinite(need_e3) else 999):11.0f}")
json.dump(out, open(f"{D}/out/R_02_conditional_bound.json", "w"), ensure_ascii=False, indent=1)
print()
print("(필요δ 999 = 그 곡선의 δ=90° 로도 바닥에 도달 못함)")
