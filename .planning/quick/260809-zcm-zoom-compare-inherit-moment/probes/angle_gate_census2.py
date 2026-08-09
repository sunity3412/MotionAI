"""확대 비교 각도 미표시 사유 전수 조사 + 근방 프레임 가용성 (관찰 전용).

fault_zoom 의 실제 게이트 함수를 그대로 호출한다(재구현 0). 카드 payload 의
userFrameIdx/refFrameIdx 는 rep 인덱스(fault_zoom.py:3043).

usage: python3 angle_gate_census2.py <uid> <aid> [<aid> ...]
"""
from __future__ import annotations

import collections
import sys

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import fault_zoom as fz  # noqa: E402

RADIUS_REP = 4  # _MOMENT_ANCHOR_RADIUS(2) @9fps → rep(18fps) 환산


def drawable(crit, members, u_rep, ukp, r_rep, rkp, u_res, r_res):
    """(u_vertex, r_vertex, u_spec, r_spec) 성립 여부 → 사유 문자열."""
    uv = fz.criterion_vertex_xy(crit, members, u_rep, ukp, None, u_res)
    rv = fz.criterion_vertex_xy(crit, members, r_rep, rkp, None, r_res)
    if uv is None:
        return "user_crop_relaxed"
    if rv is None:
        return "ref_crop_relaxed"
    us = fz.build_angle_bake_spec(crit, members, u_rep, ukp, u_res)
    if us is None:
        return "user_gate"
    rs = fz.build_angle_bake_spec(crit, members, r_rep, rkp, r_res)
    if rs is None:
        return "ref_gate"
    return "DRAWN"


def census(uid: str, aid: str, tally: collections.Counter, near: collections.Counter):
    doc = (
        fa._db().collection("users").document(uid)
        .collection("analyses").document(aid).get().to_dict()
    )
    res = doc.get("result") or {}
    motion_id = doc.get("referenceMotionId")
    u_rep = res.get("keypointReport") or {}
    ref_doc = fa.get_reference_motion(motion_id) or {}
    r_rep = ref_doc.get("referenceKeypointReport") or {}
    if not u_rep or not r_rep:
        print(f"  {aid} skip (report 없음)")
        return
    u_n = int(u_rep.get("frames") or 0)
    r_n = int(r_rep.get("frames") or 0)

    print(f"\n=== {aid[:14]}  {motion_id}  score={res.get('overallScore')} ===")
    for card in res.get("faultZoomComparisons") or []:
        joint, crit = card.get("joint"), card.get("criterion")
        if not crit:
            tally["advisory(설계상 원)"] += 1
            continue
        members = (joint,)
        ukp, rkp = int(card.get("userFrameIdx") or 0), int(card.get("refFrameIdx") or 0)
        u_res = fz._gated_kp
        r_res = fz.make_reference_anchor_resolver(motion_id, crit)
        verdict = drawable(crit, members, u_rep, ukp, r_rep, rkp, u_res, r_res)
        tally[verdict] += 1

        # 근방 창(±RADIUS_REP, 두 측 같은 오프셋)에 그릴 수 있는 프레임이 있는가
        hits = []
        for d in range(-RADIUS_REP, RADIUS_REP + 1):
            uu, rr = ukp + d, rkp + d
            if not (0 <= uu < u_n and 0 <= rr < r_n):
                continue
            if drawable(crit, members, u_rep, uu, r_rep, rr, u_res, r_res) == "DRAWN":
                hits.append(d)
        if verdict == "DRAWN":
            near["이미 그려짐"] += 1
        elif hits:
            near[f"근방에 있음(최소 |d|={min(abs(h) for h in hits)})"] += 1
        else:
            near["근방 전무"] += 1
        print(f"  {joint:<15} {verdict:<18} 근방drawable={hits if hits else '없음'}")


if __name__ == "__main__":
    uid = sys.argv[1]
    tally: collections.Counter = collections.Counter()
    near: collections.Counter = collections.Counter()
    for aid in sys.argv[2:]:
        census(uid, aid, tally, near)
    print("\n===== 집계 (criterion 카드) =====")
    for k, v in tally.most_common():
        print(f"  {k:<24} {v}")
    print("----- 근방 창 가용성 -----")
    for k, v in near.most_common():
        print(f"  {k:<28} {v}")
