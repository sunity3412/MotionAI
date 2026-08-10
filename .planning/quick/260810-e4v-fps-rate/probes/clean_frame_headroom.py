"""붕괴 카드를 살릴 프레임이 얼마나 가까이 있나 (관찰 전용 — 수리 전 전제 확인).

belle 08-10: **"놉 되게끔 해야함"** — 붕괴 카드를 사진 없이 내리는 게 아니라 붕괴 아닌
프레임으로 옮겨 **사진을 유지**한다. 그 수리가 성립하는지는 하나에 걸려 있다:
**깨끗한 프레임이 창 안에 있는가.**

창을 넓히는 것은 공짜가 아니다(08-09 실측: "창을 넓히면 종전 실패가 재발" — 붕괴 흡인).
그래서 "얼마나 넓혀야 하는가"를 먼저 재고, 그 거리가 감점을 대표하지 못할 만큼 멀면
그 카드는 다른 방법이 필요하다는 뜻이다.

판정 기준(`card_defect_census.py` 와 같은 출처):
  붕괴 = 같은 점 뭉침 >= 2  또는  한 세로선(폴) >= 4
  표시 = 그 관절 삼각 3점이 전부 conf >= `fault_zoom._KP_CONF_MIN`

usage: clean_frame_headroom.py <uid> <analysisId>
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend" / "shared" / "python"))

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_ANGLES  # noqa: E402

NAME_MAP = {"left_wrist": "left_hand", "right_wrist": "right_hand"}
SAME_PT, SAME_X = 2, 4


def is_collapsed(rep, idx) -> bool:
    js = rep.get("joints") or []
    ok = [(round(p[0], 4), round(p[1], 4))
          for p in (fz._kp_xy(rep, idx, n) for n in js) if p]
    if not ok:
        return True
    dup = Counter(ok)
    xs = Counter(p[0] for p in ok)
    return (sum(c for c in dup.values() if c > 1) >= SAME_PT
            or max(xs.values()) >= SAME_X)


def drawable(rep, idx, joint) -> bool:
    tri = [NAME_MAP.get(n, n) for n in JOINT_ANGLES.get(joint, ())]
    if not tri:
        return False
    for n in tri:
        c = fz._kp_conf(rep, idx, n)
        if c is None or c < fz._KP_CONF_MIN or fz._kp_xy(rep, idx, n) is None:
            return False
    return True


def nearest(rep, idx, joint, n_frames, fps, require_draw: bool):
    for d in range(n_frames):
        for k in ((idx,) if d == 0 else (idx - d, idx + d)):
            if 0 <= k < n_frames and not is_collapsed(rep, k) \
                    and (not require_draw or drawable(rep, k, joint)):
                return k, d, d / fps
    return None, None, None


def run(uid: str, aid: str):
    doc = (fa._db().collection("users").document(uid)
           .collection("analyses").document(aid).get().to_dict())
    res = doc["result"]
    urep = res["keypointReport"]
    ref = fa.get_reference_motion((res.get("comparison") or {}).get("referenceMotionId")) or {}
    rrep = ref.get("referenceKeypointReport") or {}
    ufps, rfps = float(urep.get("fps") or 18), float(rrep.get("fps") or 18)
    un, rn = int(urep.get("frames") or 0), int(rrep.get("frames") or 0)

    print(f"{'카드':<15}{'패널':<8}{'현재':>6}{'붕괴':>6}"
          f"{'깨끗 최근접':>13}{'거리':>14}{'표시가능 최근접':>18}")
    worst = 0.0
    for c in res.get("faultZoomComparisons") or []:
        j = c.get("joint")
        for who, rep, idx, n, fps in (("나", urep, c.get("userFrameIdx"), un, ufps),
                                      ("정은지", rrep, c.get("refFrameIdx"), rn, rfps)):
            if idx is None:
                continue
            idx = int(idx)
            col = is_collapsed(rep, idx)
            _k1, d1, s1 = nearest(rep, idx, j, n, fps, require_draw=False)
            _k2, d2, s2 = nearest(rep, idx, j, n, fps, require_draw=True)
            if col and s1 is not None:
                worst = max(worst, s1)
            print(f"{j if who == '나' else '':<15}{who:<8}{idx:>6}{'★' if col else '-':>6}"
                  f"{str(_k1):>13}"
                  f"{'-' if d1 is None else f'{d1}f / {s1 * 1000:.0f}ms':>14}"
                  f"{'-' if d2 is None else f'{_k2} ({d2}f / {s2 * 1000:.0f}ms)':>18}")
    print(f"\n붕괴 카드가 깨끗한 프레임까지 가야 하는 최대 거리 = {worst * 1000:.0f}ms")
    print("거리 0 = 지금 프레임이 이미 깨끗. '표시가능' = 붕괴 아님 **그리고** 표시 게이트 통과.")


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
