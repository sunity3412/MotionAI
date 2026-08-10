"""정렬은 "지적 관절을 뺀 나머지 몸"으로 잰다 — 두 조건의 직교화 (관찰 전용).

1차 측정에서 (차이 큼) 과 (정렬 신뢰) 가 서로를 잡아먹었다. 이유는 구조적이다:
`_pose_dist` 는 **문제 관절의 위치 차이까지 포함해서** 짝거리를 재므로, "잘 맞는 짝에서
큰 차이" 를 찾는 요구가 자기모순에 가깝다. 정렬을 좋게 하면 그 관절도 같아진다.

그래서 여기서는 정렬을 **지적 관절 3점을 제외한 나머지 몸**으로 잰다(`pd_rest`).
그러면 두 축이 직교한다:

  · pd_rest 작음  = 두 사람이 같은 국면·같은 방위에 있다
  · d 큼          = 그런데 그 부위만 크게 벌어져 있다

이것이 코치가 실제로 하는 말의 구조다 — "다른 건 같은데 이 부위가 다르다".

임계는 새로 만들지 않는다. 후보는 **현행 승인 순간을 두 축에서 동시에 이기는**
프레임만 (Pareto 우세): pd_rest <= pd_rest0 그리고 d > d0. 우세 프레임이 없으면
현행 유지(fail-closed) — 승인본 무접촉이 규칙 자체에서 성립한다.

붕괴 게이트 동반: 몸통 >= 0.4×클립중앙 · 가로/세로 >= 0.25 (`collapse_scan.py` 실측 신호),
표시 keypoint conf >= 0.5 (`fault_zoom._KP_CONF_MIN`) — 양쪽 다.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import compare_render as cr  # noqa: E402

ROOT = REPO / ".planning/phases/35-server-rendered-comparison-video/data"

CONF_MIN = cr.KP_CONF_MIN
TORSO_MIN_FRAC = 0.4
ASPECT_MIN = 0.25
REST_CONF = 0.35        # `_pose_dist` 와 같은 값 — 나머지 몸 평균에 쓸 관절 선별
REST_MIN_JOINTS = 6     # `_pose_dist` 와 같은 값


def _pose_vec(kp_at, joints, t):
    """골반 원점·몸통 1 정규화 좌표 + conf (관절 이름 → (xy, conf))."""
    pts, conf = {}, {}
    for n in joints:
        p, c = kp_at(n, t)
        pts[n], conf[n] = np.asarray(p, dtype=float), float(c)
    sh = (pts["left_shoulder"] + pts["right_shoulder"]) / 2
    hp = (pts["left_hip"] + pts["right_hip"]) / 2
    torso = float(np.linalg.norm(sh - hp))
    if torso < 1e-6 or not np.isfinite(torso):
        return None, None, None
    return {n: (pts[n] - hp) / torso for n in joints}, conf, torso


def pd_rest(u_at, r_at, joints, ut, rt, exclude: set[str]) -> float | None:
    """지적 관절 3점을 제외한 나머지 몸의 평균 L2 — 국면·방위 일치도."""
    a, ca, _ = _pose_vec(u_at, joints, ut)
    b, cb, _ = _pose_vec(r_at, joints, rt)
    if a is None or b is None:
        return None
    use = [n for n in joints
           if n not in exclude and ca[n] >= REST_CONF and cb[n] >= REST_CONF]
    if len(use) < REST_MIN_JOINTS:
        return None
    return float(np.mean([np.linalg.norm(a[n] - b[n]) for n in use]))


def _shape_series(align, side, joints):
    F = int(align[f"{side}Frames"])
    kp = np.asarray(align[f"{side}Kp"], dtype=float).reshape(F, len(joints), 2)
    sc = np.asarray(align[f"{side}Score"], dtype=float)
    idx = {n: joints.index(n) for n in
           ("left_shoulder", "right_shoulder", "left_hip", "right_hip")}
    sh = (kp[:, idx["left_shoulder"]] + kp[:, idx["right_shoulder"]]) / 2
    hp = (kp[:, idx["left_hip"]] + kp[:, idx["right_hip"]]) / 2
    torso = np.linalg.norm(sh - hp, axis=1)
    aspect = np.full(F, np.nan)
    for i in range(F):
        m = sc[i] >= 0.3
        if int(m.sum()) >= 6:
            h = float(kp[i, m, 1].max() - kp[i, m, 1].min())
            if h > 1e-9:
                aspect[i] = float(kp[i, m, 0].max() - kp[i, m, 0].min()) / h
    return torso, aspect


def _intact(torso, aspect, med, i) -> bool:
    if i < 0 or i >= len(torso) or not np.isfinite(torso[i]):
        return False
    if torso[i] < TORSO_MIN_FRAC * med:
        return False
    a = aspect[i]
    return not (np.isfinite(a) and a < ASPECT_MIN)


def run(case: str) -> list[dict]:
    d = ROOT / case
    doc = json.load(open(d / "doc.json"))
    align = json.load(open(d / "align.json"))
    curve = align.get("curveRefSec")
    pairs = align.get("pairs") or {}
    if not curve:
        return []
    afps, uF = float(align["fps"]), int(align["userFrames"])
    joints = list(align["joints17"])
    try:
        u_at, r_at = cr._kp_reader(align, "user"), cr._kp_reader(align, "ref")
    except (KeyError, ValueError):
        return []
    ut_s, ua_s = _shape_series(align, "user", joints)
    rt_s, ra_s = _shape_series(align, "ref", joints)
    umed = statistics.median([v for v in ut_s if np.isfinite(v) and v > 0])
    rmed = statistics.median([v for v in rt_s if np.isfinite(v) and v > 0])

    print(f"\n=== {case} ===")
    rows = []
    for rec in (doc["result"].get("deductionBreakdown") or {}).get("records") or []:
        crit = rec.get("criterion") or ""
        if "angle_vs_reference__" not in crit:
            continue
        jk = crit.split("__", 1)[1]
        if jk not in cr._ANGLE_TRIPLES:
            continue
        rid = (rec.get("recordId") or "").split(":")[0]
        pair = pairs.get(rid)
        if not pair:
            continue
        tri = set(cr._ANGLE_TRIPLES[jk])
        ut0, rt0 = float(pair["atVideoSec"]), float(pair["refVideoSec"])
        a0 = cr._joint_angle(u_at, jk, ut0, conf_min=CONF_MIN)
        b0 = cr._joint_angle(r_at, jk, rt0, conf_min=CONF_MIN)
        d0 = abs(a0 - b0) if (a0 is not None and b0 is not None) else None
        pr0 = pd_rest(u_at, r_at, joints, ut0, rt0, tri)

        # 클립 전수 — 나머지몸 정렬 분포 + Pareto 우세 후보
        rest_all, cands = [], []
        for i in range(uF):
            ut, rt = i / afps, float(curve[i])
            pr = pd_rest(u_at, r_at, joints, ut, rt, tri)
            if pr is not None:
                rest_all.append(pr)
            a = cr._joint_angle(u_at, jk, ut, conf_min=CONF_MIN)
            b = cr._joint_angle(r_at, jk, rt, conf_min=CONF_MIN)
            if a is None or b is None or pr is None:
                continue
            if not (_intact(ut_s, ua_s, umed, i)
                    and _intact(rt_s, ra_s, rmed, int(round(rt * afps)))):
                continue
            cands.append({"i": i, "ut": ut, "rt": rt, "d": abs(a - b), "pr": pr,
                          "a": a, "b": b})

        pct = (100.0 * sum(1 for p in rest_all if p <= pr0) / len(rest_all)
               if (pr0 is not None and rest_all) else None)
        dom = [c for c in cands
               if pr0 is not None and c["pr"] <= pr0 and d0 is not None and c["d"] > d0]
        best = max(dom, key=lambda c: c["d"]) if dom else None

        print(f"  {rid} {jk:<15} pts={rec.get('points')} dev={rec.get('deviation')}")
        print(f"      현행  {ut0:6.2f}s ↔ {rt0:5.2f}s  차이 "
              f"{'-' if d0 is None else f'{d0:5.1f}도'}  나머지몸 정렬 "
              f"{'-' if pr0 is None else f'{pr0:.3f}'}"
              f"{'' if pct is None else f' (클립 상위 {pct:.0f}%)'}"
              f"  각도 {'-' if a0 is None else f'{a0:.0f}'} 대 "
              f"{'-' if b0 is None else f'{b0:.0f}'}")
        if best:
            print(f"      우세 후보 {len(dom):3d}개 → 최선 {best['ut']:6.2f}s ↔ "
                  f"{best['rt']:5.2f}s  차이 {best['d']:5.1f}도 (x{best['d']/d0:.1f}) "
                  f"나머지몸 정렬 {best['pr']:.3f} (현행보다 "
                  f"{'좋음' if best['pr'] <= pr0 else '나쁨'})  각도 "
                  f"{best['a']:.0f} 대 {best['b']:.0f}")
        else:
            why = ("현행 차이 산출 불가(각도 미표시)" if d0 is None
                   else "두 축 동시 우세 프레임 없음")
            print(f"      우세 후보 0개 — {why}  (게이트 통과 후보 {len(cands)}개)")
        rows.append({"case": case, "rid": rid, "joint": jk, "d0": d0, "pr0": pr0,
                     "pct": pct, "n_dom": len(dom), "best": best,
                     "n_cand": len(cands), "points": rec.get("points")})
    return rows


if __name__ == "__main__":
    cases = sys.argv[1:] or sorted(p.name for p in ROOT.iterdir()
                                   if p.is_dir() and (p / "align.json").exists())
    allrows = []
    for c in cases:
        allrows.extend(run(c))
    print("\n" + "=" * 100)
    print("종합 — 나머지몸 정렬 기준")
    print(f"{'case':<14}{'rid':<5}{'관절':<15}{'현행차이':>9}{'현행정렬':>9}{'상위%':>7}"
          f"{'우세':>6}{'최선차이':>9}{'최선정렬':>9}")
    for r in allrows:
        b = r["best"]
        print(f"{r['case']:<14}{r['rid']:<5}{r['joint']:<15}"
              f"{'-' if r['d0'] is None else f'{r[chr(100)+chr(48)]:8.1f}도'}"
              f"{'-' if r['pr0'] is None else f'{r[chr(112)+chr(114)+chr(48)]:9.3f}'}"
              f"{'-' if r['pct'] is None else f'{r[chr(112)+chr(99)+chr(116)]:6.0f}%'}"
              f"{r['n_dom']:>6}"
              f"{'-' if not b else f'{b[chr(100)]:8.1f}도'}"
              f"{'-' if not b else f'{b[chr(112)+chr(114)]:9.3f}'}")
    n_have = sum(1 for r in allrows if r["best"])
    print(f"\nrecord {len(allrows)}건 중 두 축 동시 우세 후보 보유 = {n_have}건")
