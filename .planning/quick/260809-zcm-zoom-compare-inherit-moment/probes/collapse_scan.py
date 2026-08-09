"""붕괴 프레임(스켈레톤이 폴 위 한 줄로 뭉침) 탐지 가능성 실측 (관찰 전용).

신호 후보
  ① 몸통 길이(어깨중점-골반중점) / 클립 중앙값        — 뭉치면 급감
  ② keypoint 산포의 가로/세로 비 (가로폭 / 세로폭)      — 한 줄이면 0 에 수렴
  ③ reliability 라벨 (report 가 이미 갖고 있는 것)
"""
from __future__ import annotations

import collections
import statistics
import sys

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402


def mid(rep, i, a, b):
    pa, pb = fz._kp_xy(rep, i, a), fz._kp_xy(rep, i, b)
    if pa is None or pb is None:
        return None
    return ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)


def metrics(rep, i):
    sh, hp = mid(rep, i, "left_shoulder", "right_shoulder"), mid(rep, i, "left_hip", "right_hip")
    torso = None
    if sh and hp:
        torso = ((sh[0] - hp[0]) ** 2 + (sh[1] - hp[1]) ** 2) ** 0.5
    xs, ys = [], []
    for j in rep.get("joints") or []:
        p = fz._kp_xy(rep, i, j)
        if p:
            xs.append(p[0])
            ys.append(p[1])
    aspect = None
    if len(xs) >= 6:
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        aspect = w / h if h > 1e-9 else None
    return torso, aspect


def run(uid, aid):
    doc = (fa._db().collection("users").document(uid)
           .collection("analyses").document(aid).get().to_dict())
    res = doc["result"]
    rep = res["keypointReport"]
    n = int(rep.get("frames") or 0)
    rel = rep.get("reliability") or []
    torsos, aspects = [], []
    for i in range(n):
        t, a = metrics(rep, i)
        torsos.append(t)
        aspects.append(a)
    tv = [t for t in torsos if t]
    med = statistics.median(tv)
    print(f"frames={n}  torso 중앙={med:.4f}")
    print("reliability 라벨 분포:", collections.Counter(rel).most_common())

    bad = [i for i, t in enumerate(torsos) if t is not None and t < 0.4 * med]
    narrow = [i for i, a in enumerate(aspects) if a is not None and a < 0.25]
    print(f"몸통<40% 중앙값 프레임: {len(bad)}/{n} ({100*len(bad)/n:.0f}%)")
    print(f"가로/세로<0.25 (한 줄) 프레임: {len(narrow)}/{n} ({100*len(narrow)/n:.0f}%)")
    both = sorted(set(bad) & set(narrow))
    print(f"둘 다: {len(both)} → {both[:40]}")

    # 카드가 그 프레임 위에 서 있는가
    for c in res.get("faultZoomComparisons") or []:
        i = int(c.get("userFrameIdx") or -1)
        t, a = metrics(rep, i)
        flag = []
        if t is not None and t < 0.4 * med:
            flag.append("몸통붕괴")
        if a is not None and a < 0.25:
            flag.append("한줄")
        lab = rel[i] if 0 <= i < len(rel) else "?"
        print(f"  카드 {c.get('joint'):<15} rep={i:<4} torso={t and f'{t:.4f}'} "
              f"({t and 100*t/med:.0f}%) aspect={a and f'{a:.2f}'} rel={lab} "
              f"{'<-- ' + '+'.join(flag) if flag else ''}")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
