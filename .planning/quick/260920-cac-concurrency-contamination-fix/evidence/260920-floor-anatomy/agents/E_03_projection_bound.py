"""E-3 — 2D 투영이 관절각을 얼마나 흔들 수 있나 (기하 상한).

운영 각도는 features._angle_deg 가 z=0 좌표 위에서 재는 '이미지평면 3점각'이다
(joints3d z 전량 0 — 메모리 joints3d-is-2d-z-is-all-zero). 따라서 카메라 방위각
(또는 봉 주위 몸의 방위 — 2D 각도에는 같은 물건) 이 δ 만큼 달라지면 같은 3D
자세라도 2D 각이 움직인다. 그 움직임의 분포를 잰다.

방법: 임의 3D 3점(a,b,c) — 관절 길이비는 실제 인체 비율대(0.7~1.4배), 3D 내각
θ 는 5~175° 균일, 방향은 SO(3) 균일. 세로축(폴 축 = 화면 수직) 둘레로 δ 만큼
돌린 뒤 정사영 → 2D 각. |2D각(δ) − 2D각(0)| 분포.
각 계산은 운영 features._angle_deg 를 그대로 호출한다(재구현 0).
"""
import sys
import numpy as np
sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")
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
    """vertex 원점, ba 는 +x, bc 는 3D 내각 theta 만큼 벌어진 임의 방향."""
    th = np.radians(rng.uniform(5, 175, n))
    L1 = rng.uniform(0.7, 1.4, n); L2 = rng.uniform(0.7, 1.4, n)
    ph = rng.uniform(0, 2 * np.pi, n)
    ba = np.stack([L1, np.zeros(n), np.zeros(n)], -1)
    bc = np.stack([L2 * np.cos(th), L2 * np.sin(th) * np.cos(ph), L2 * np.sin(th) * np.sin(ph)], -1)
    R = rand_rot(n)
    return np.einsum("nij,nj->ni", R, ba), np.einsum("nij,nj->ni", R, bc), np.degrees(th)


def yaw(v, deg):
    """화면 수직축(y) 둘레 회전 — 폴이 화면 수직이라는 가정 아래의 '방위각'."""
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    M = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return v @ M.T


def ang2d(ba, bc):
    z = np.zeros(2)
    return np.array([_angle_deg(ba[i, :2], z, bc[i, :2]) for i in range(len(ba))])


BA, BC, TH = build(N)
a0 = ang2d(BA, BC)
print("[기준선] 같은 자세를 2D 로 재는 것 자체의 오차  |2D각 − 3D각|")
e0 = np.abs(a0 - TH); e0 = e0[np.isfinite(e0)]
print(f"   median={np.median(e0):5.1f}  p90={np.percentile(e0,90):5.1f}  max={e0.max():5.1f}  (n={e0.size})")
print()
print("[본문] 방위각 δ 만큼 다른 카메라에서 본 같은 3D 자세의 2D 각 차이")
print(f"{'δ(도)':>7s}{'median':>9s}{'p75':>8s}{'p90':>8s}{'p99':>8s}{'max':>8s}")
rows = {}
for d in (5, 10, 15, 20, 30, 45, 60, 90):
    ad = ang2d(yaw(BA, d), yaw(BC, d))
    e = np.abs(ad - a0); e = e[np.isfinite(e)]
    rows[d] = e
    print(f"{d:7d}{np.median(e):9.2f}{np.percentile(e,75):8.2f}{np.percentile(e,90):8.2f}"
          f"{np.percentile(e,99):8.2f}{e.max():8.2f}")
print()
print("[해석축] 관절 8개 median 의 중앙값(= 이 조사의 '편차 스칼라')로 환산하면")
print("  δ 하나로 생기는 값은 위 표의 median 열에 가깝다 (관절/프레임 median 이 꼬리를 깎으므로).")
print()
print("[조건부] 3D 내각 구간별 median |Δ2D각| (δ=20°)")
e20 = rows[20]
th = TH[: len(e20)]
for lo, hi in ((5, 45), (45, 90), (90, 135), (135, 175)):
    m = (th >= lo) & (th < hi)
    print(f"   θ∈[{lo:3d},{hi:3d})  median={np.median(e20[m]):6.2f}  p90={np.percentile(e20[m],90):6.2f}  n={int(m.sum())}")
