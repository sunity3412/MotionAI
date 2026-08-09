"""지금 나가는 감점 중 "그 순간 신호 요동보다 작은 편차"가 몇 건인가 (관찰 전용).

r01(오른 팔꿈치)에서 드러난 것: 편차 4.3도인데 그 순간 각도 신호는 ±0.5초에
155도를 휘젓는다. 기존 억제 게이트는 **표본 전체 중앙값의 신뢰구간**을 보므로
이런 건을 통과시킨다 — 묻는 질문이 다르다.

여기서는 감점마다 (편차 / 그 순간 신호 요동)을 재서 분포를 낸다. 채점 무접촉.
"""
from __future__ import annotations

import math
import statistics
import sys

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

TRIPLE = {
    "elbow": ("shoulder", "elbow", "hand"),
    "knee": ("hip", "knee", "ankle"),
    "shoulder": ("elbow", "shoulder", "hip"),
    "hip": ("shoulder", "hip", "knee"),
}


def angle(rep, i, side, tri):
    p = [fz._kp_xy(rep, i, f"{side}_{n}") for n in tri]
    if not all(p):
        return None
    v1 = (p[0][0] - p[1][0], p[0][1] - p[1][1])
    v2 = (p[2][0] - p[1][0], p[2][1] - p[1][1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return None
    c = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(c))


def run(uid, aids):
    rows = []
    for aid in aids:
        doc = (fa._db().collection("users").document(uid)
               .collection("analyses").document(aid).get().to_dict())
        res = doc.get("result") or {}
        rep = res.get("keypointReport") or {}
        if not rep:
            continue
        n = int(rep.get("frames") or 0)
        fps = float(rep.get("fps") or 18.0)
        for rec in (res.get("deductionBreakdown") or {}).get("records") or []:
            crit = rec.get("criterion") or ""
            at = rec.get("atFrameIdx")
            dev = rec.get("deviation")
            if at is None or dev is None or "angle_vs_reference__" not in crit:
                continue
            jk = crit.split("__", 1)[1]           # 예: right_elbow
            side, part = jk.split("_", 1)
            tri = TRIPLE.get(part)
            if not tri:
                continue
            center = int(round(at * 2))            # record=9fps → rep=18fps
            half = int(round(0.5 * fps))
            vals = [angle(rep, i, side, tri)
                    for i in range(max(0, center - half), min(n, center + half + 1))]
            vals = [v for v in vals if v is not None]
            if len(vals) < 5:
                continue
            swing = max(vals) - min(vals)
            rows.append((aid[:12], jk, float(dev), rec.get("points"), swing,
                         float(dev) / swing if swing > 1e-6 else float("inf")))

    rows.sort(key=lambda r: r[5])
    print(f"{'doc':<14}{'관절':<16}{'편차':>7}{'점수':>7}{'그순간요동':>11}{'편차/요동':>10}")
    for r in rows:
        flag = "  <-- 요동에 묻힘" if r[5] < 0.10 else ""
        print(f"{r[0]:<14}{r[1]:<16}{r[2]:>6.1f}도{str(r[3]):>7}{r[4]:>9.0f}도{r[5]:>9.2f}{flag}")
    if rows:
        ratios = [r[5] for r in rows]
        buried = [r for r in rows if r[5] < 0.10]
        pts = sum(abs(float(r[3] or 0)) for r in buried)
        print(f"\n감점 {len(rows)}건 · 편차/요동 중앙값 {statistics.median(ratios):.2f}")
        print(f"요동의 10% 미만(= 그 순간엔 사실상 구분 불가): "
              f"{len(buried)}건 ({100*len(buried)/len(rows):.0f}%), 합계 {pts:.1f}점")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2:])
