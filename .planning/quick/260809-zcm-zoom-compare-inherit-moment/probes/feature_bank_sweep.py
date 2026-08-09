"""감점마다 여러 피처를 나란히 재서 "무엇으로 말했어야 하나"를 판정 (관찰 전용).

지금 파이프라인은 관절 각도 하나만 보고 카드를 만든다. 다른 후보를 재지도 않으므로
"각도가 최선이었나"를 판정할 자리가 없다. 여기서 후보를 다 재서 표로 만든다.

공통 척도 = |학생 − 기준| ÷ (그 순간 그 피처가 오가는 폭). 단위(도·배율)가 달라도
비교된다. 폴 x 는 손목 중앙값 근사 — 실 검출과 대조해 오차 0.007/0.0002 확인함.

채점·표시 무접촉. 산출은 표 하나.
"""
from __future__ import annotations

import collections
import math
import statistics
import sys

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

TRIPLE = {"elbow": ("shoulder", "elbow", "hand"), "knee": ("hip", "knee", "ankle"),
          "shoulder": ("elbow", "shoulder", "hip"), "hip": ("shoulder", "hip", "knee")}
HALF_S = 0.5


def xy(rep, i, n):
    return fz._kp_xy(rep, i, n)


def torso(rep, i):
    ls, rs = xy(rep, i, "left_shoulder"), xy(rep, i, "right_shoulder")
    lh, rh = xy(rep, i, "left_hip"), xy(rep, i, "right_hip")
    if not (ls and rs and lh and rh):
        return None, None, None
    sh = ((ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2)
    hp = ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2)
    d = math.dist(sh, hp)
    return (d if d > 1e-4 else None), sh, hp


def pole_x(rep, n):
    vals = []
    for i in range(n):
        for w in ("left_hand", "right_hand"):
            p = xy(rep, i, w)
            c = fz._kp_conf(rep, i, w)
            if p and (c is None or c >= 0.5):
                vals.append(p[0])
    return statistics.median(vals) if len(vals) >= 10 else None


# ── 피처들 — 전부 (report, frame, side, joint_part) → 스칼라 ────────────────
def f_angle(rep, i, side, part, px):
    tri = TRIPLE.get(part)
    if not tri:
        return None
    p = [xy(rep, i, f"{side}_{n}") for n in tri]
    if not all(p):
        return None
    v1 = (p[0][0] - p[1][0], p[0][1] - p[1][1])
    v2 = (p[2][0] - p[1][0], p[2][1] - p[1][1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, (v1[0]*v2[0] + v1[1]*v2[1]) / (n1*n2)))))


def f_pole_gap(rep, i, side, part, px):
    """그 관절이 폴에서 뜬 거리 (몸통 단위)."""
    if px is None:
        return None
    p = xy(rep, i, f"{side}_{part}")
    t, _, _ = torso(rep, i)
    if not p or not t:
        return None
    return abs(p[0] - px) / t


def f_trunk_tilt(rep, i, side, part, px):
    """몸통이 수직(=폴)에서 기운 각. 폴이 수직이므로 폴 정렬과 같은 뜻."""
    t, sh, hp = torso(rep, i)
    if not t:
        return None
    return math.degrees(math.atan2(abs(sh[0] - hp[0]), abs(sh[1] - hp[1]) + 1e-9))


def f_limb_from_axis(rep, i, side, part, px):
    """그 관절이 몸 중심선에서 벗어난 거리 (몸통 단위)."""
    t, sh, hp = torso(rep, i)
    p = xy(rep, i, f"{side}_{part}")
    if not t or not p:
        return None
    # 중심선(어깨중점-골반중점)까지 점-직선 거리
    ax, ay = hp[0], hp[1]
    bx, by = sh[0], sh[1]
    num = abs((by - ay) * p[0] - (bx - ax) * p[1] + bx * ay - by * ax)
    den = math.hypot(by - ay, bx - ax) + 1e-9
    return (num / den) / t


def f_symmetry(rep, i, side, part, px):
    """좌우 같은 관절의 각도 차 (한쪽만 무너졌는지)."""
    a = f_angle(rep, i, "left", part, px)
    b = f_angle(rep, i, "right", part, px)
    return None if (a is None or b is None) else abs(a - b)


FEATURES = [("각도", f_angle), ("폴 거리", f_pole_gap), ("몸통 기울기", f_trunk_tilt),
            ("중심선 이탈", f_limb_from_axis), ("좌우 비대칭", f_symmetry)]


def local(rep, i, side, part, px, fn, half):
    vals = [fn(rep, j, side, part, px)
            for j in range(max(0, i - half), i + half + 1)]
    vals = [v for v in vals if v is not None]
    return vals


def run(uid, aids):
    out = []
    for aid in aids:
        doc = (fa._db().collection("users").document(uid)
               .collection("analyses").document(aid).get().to_dict())
        res = doc.get("result") or {}
        mid = doc.get("referenceMotionId")
        u_rep = res.get("keypointReport") or {}
        r_rep = (fa.get_reference_motion(mid) or {}).get("referenceKeypointReport") or {}
        if not u_rep or not r_rep:
            continue
        u_n, r_n = int(u_rep["frames"]), int(r_rep["frames"])
        u_px, r_px = pole_x(u_rep, u_n), pole_x(r_rep, r_n)
        u_half = int(round(HALF_S * float(u_rep.get("fps") or 18)))
        r_half = int(round(HALF_S * float(r_rep.get("fps") or 18)))
        cards = {c.get("criterion"): c for c in res.get("faultZoomComparisons") or []}
        for rec in (res.get("deductionBreakdown") or {}).get("records") or []:
            crit, at = rec.get("criterion") or "", rec.get("atFrameIdx")
            if at is None or "angle_vs_reference__" not in crit:
                continue
            card = cards.get(crit)
            if not card or card.get("refFrameIdx") is None:
                continue
            jk = crit.split("__", 1)[1]
            side, part = jk.split("_", 1)
            ui, ri = int(at) * 2, int(card["refFrameIdx"])
            row = {"doc": aid[:12], "joint": jk, "points": rec.get("points")}
            for name, fn in FEATURES:
                uv = local(u_rep, ui, side, part, u_px, fn, u_half)
                rv = local(r_rep, ri, side, part, r_px, fn, r_half)
                if len(uv) < 5 or len(rv) < 5:
                    continue
                um, rm = statistics.median(uv), statistics.median(rv)
                swing = max(max(uv) - min(uv), max(rv) - min(rv))
                if swing < 1e-6:
                    continue
                row[name] = (abs(um - rm) / swing, um, rm)
            out.append(row)

    names = [n for n, _ in FEATURES]
    print(f"{'doc':<13}{'관절':<15}{'점수':>6}  " + "".join(f"{n:>13}" for n in names) + "   최선")
    win = collections.Counter()
    for r in out:
        cells = ""
        best, bestv = None, -1.0
        for n in names:
            if n in r:
                v = r[n][0]
                cells += f"{v:>13.2f}"
                if v > bestv:
                    best, bestv = n, v
            else:
                cells += f"{'-':>13}"
        win[best] += 1
        print(f"{r['doc']:<13}{r['joint']:<15}{str(r['points']):>6}  {cells}   {best}")
    print("\n무엇으로 말했어야 하나 (분리도 최대 피처):")
    for k, v in win.most_common():
        print(f"  {k}: {v}건 ({100*v/max(1,len(out)):.0f}%)")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2:])
