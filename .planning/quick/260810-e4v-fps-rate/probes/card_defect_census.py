"""확대 비교 카드의 결함을 세 종류로 갈라 센다 (관찰 전용).

belle 08-10 실물 판정: "같은 자세라고 느껴지지 않는데" + "붉은색 표시방향이 아예 다르네".
두 관찰이 **서로 다른 원인**이었다. 카드마다 아래 셋을 따로 재서 갈라 준다:

  ① 붕괴      — 서로 다른 관절이 같은 점/같은 세로선(폴)에 뭉침. conf 게이트가 못 잡는다
                (right_elbow 실측: 팔꿈치 conf 0.57 로 통과했는데 12관절 중 10개가 한 x).
                증상 = 사이각 0도, 링이 엉뚱한 부위.
  ② 국면 불일치 — 포즈는 깨끗한데 동작 단계가 다름(다리 모음 vs 스플릿). 짝 선정의 몫.
  ③ 방위 차이  — 포즈·국면 다 괜찮은데 폴 기준 몸 방위가 달라 표시 ray 방향이 벌어짐.
                카메라 1대의 원리 한계 — 짝을 잘 골라도 남는다.

★①이 ②③보다 급하다: 붕괴 카드는 감점 −11.6 을 달고 나가면서 사용자에게 엉뚱한 부위를
가리킨다. 08-09 에 "카드 30장 중 4장"으로 발견됐고 아직 살아 있다.

usage: card_defect_census.py <uid> <analysisId>
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend" / "shared" / "python"))

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_ANGLES  # noqa: E402

NAME_MAP = {"left_wrist": "left_hand", "right_wrist": "right_hand"}  # 리포트 이름공간
COLLAPSE_SAME_PT = 2   # 같은 점에 뭉친 관절 수 — 이 이상이면 붕괴 의심
COLLAPSE_SAME_X = 4    # 한 세로선(폴)에 몰린 관절 수
RAY_DIFF_DEG = 35.0    # 표시 방향 차 — 임의 눈금(belle 판정이 정답표)


def collapse(rep, idx):
    js = rep.get("joints") or []
    pts = [(n, fz._kp_xy(rep, idx, n)) for n in js]
    ok = [(n, (round(p[0], 4), round(p[1], 4))) for n, p in pts if p]
    dup = Counter(p for _, p in ok)
    xs = Counter(p[0] for _, p in ok)
    confs = [c for c in (fz._kp_conf(rep, idx, n) for n in js) if c is not None]
    return (sum(c for c in dup.values() if c > 1),
            max(xs.values()) if xs else 0,
            sum(1 for c in confs if c < 0.5), len(confs))


def rays(rep, idx, joint):
    tri = [NAME_MAP.get(n, n) for n in JOINT_ANGLES[joint]]
    p = [fz._kp_xy(rep, idx, n) for n in tri]
    if not all(p):
        return None
    a, v, b = p
    f = lambda q: math.degrees(math.atan2(q[1] - v[1], q[0] - v[0])) % 360  # noqa: E731
    inner = abs(f(a) - f(b))
    return f(a), f(b), min(inner, 360 - inner)


def run(uid: str, aid: str):
    doc = (fa._db().collection("users").document(uid)
           .collection("analyses").document(aid).get().to_dict())
    res = doc["result"]
    urep = res["keypointReport"]
    ref = fa.get_reference_motion((res.get("comparison") or {}).get("referenceMotionId")) or {}
    rrep = ref.get("referenceKeypointReport") or {}
    recs = {(r.get("criterion") or "").split("__")[-1]: r
            for r in (res.get("deductionBreakdown") or {}).get("records") or []}

    print(f"{'카드':<15}{'감점':>7}{'붕괴 나':>16}{'붕괴 정은지':>16}"
          f"{'사이각 나/정은지':>18}{'ray Δ':>8}   정체")
    tally = Counter()
    for c in res.get("faultZoomComparisons") or []:
        j, ui, ri = c.get("joint"), c.get("userFrameIdx"), c.get("refFrameIdx")
        if ui is None or ri is None:
            continue
        up, ux, ul, uc = collapse(urep, int(ui))
        rp, rx, rl, rc = collapse(rrep, int(ri))
        col = (up >= COLLAPSE_SAME_PT or ux >= COLLAPSE_SAME_X
               or rp >= COLLAPSE_SAME_PT or rx >= COLLAPSE_SAME_X)
        U = rays(urep, int(ui), j) if j in JOINT_ANGLES else None
        R = rays(rrep, int(ri), j) if j in JOINT_ANGLES else None
        rd = None
        if U and R:
            d = lambda x, y: min(abs(x - y), 360 - abs(x - y))  # noqa: E731
            rd = max(d(U[0], R[0]), d(U[1], R[1]))
        kind = ("① 붕괴" if col else
                "③ 방위 차이" if (rd is not None and rd >= RAY_DIFF_DEG) else
                "정상 후보(② 국면은 사람 판정)")
        tally[kind.split()[0]] += 1
        print(f"{j:<15}{str(recs.get(j,{}).get('points')):>7}"
              f"{f'{up}pt/{ux}x/{ul}of{uc}':>16}{f'{rp}pt/{rx}x/{rl}of{rc}':>16}"
              f"{'-' if not U or not R else f'{U[2]:.0f}/{R[2]:.0f}도':>18}"
              f"{'-' if rd is None else f'{rd:.0f}도':>8}   {kind}")
    print("\n집계:", dict(tally))
    print("붕괴 = 같은 점 뭉침 >= 2 또는 한 세로선 >= 4. conf 게이트(0.5)가 못 잡는 축이다.")
    print("② 국면 불일치는 수치로 못 가린다 — 사진을 사람이 봐야 한다(belle 판정이 정답표).")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
