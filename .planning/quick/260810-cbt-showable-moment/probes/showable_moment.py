"""조건부 표시 순간이 클립에 있는가 — (차이 큼) ∧ (양쪽 포즈 신뢰) ∧ (정렬 신뢰).

관찰 전용. 채점·표시·렌더 산출 무접촉.

지금 표시 순간 = record 가 보고한 집계값에 가장 가까운 프레임(`moment.py`)이고,
그 값은 클립 중앙값이라 **사용자에게 가장 안 보이는 축**이다(08-09 실측: 표시 순간의
실제 차이가 클립 중앙값보다 작다 — pdshapefault 6.6도 vs 17.4도 등).

"그럼 최대 차이 순간을 보여주자"는 08-09 에 폐기됐다 — 뽑아보니 150~177도인데
전부 두 사람이 다른 국면이거나 포즈가 깨진 구간이었다. 그래서 여기서는 차이만 보지
않고 **세 조건을 동시에** 걸어 후보를 세운다.

임계는 새로 만들지 않는다. 셋 다 기존 게이트/승인본에서 되읽는다:

  ① 차이       — 곡선 전수. 참고선 = 20도(`260620-18r` 마커 강조 임계 = IPSF 허용오차)
  ② 포즈 신뢰   — 표시에 실제로 쓰이는 keypoint 3점이 conf >= 0.5 (`fault_zoom._KP_CONF_MIN`)
                 + 붕괴 아님(몸통 >= 0.4×클립중앙, 가로/세로 >= 0.25 — `collapse_scan.py` 실측)
  ③ 정렬 신뢰   — 짝 자세거리가 **그 카드가 이미 승인받은 정지 순간의 짝 거리 이하**
                 (`align.pairs[rid].poseDist`). 승인 코퍼스 수준 = 통과선이므로
                 "정렬을 더 나쁘게 만드는 순간"은 원리적으로 후보가 못 된다.

실행:
  cd backend && .venv/bin/python ../.planning/quick/260810-cbt-showable-moment/probes/showable_moment.py [case...]
  (case 생략 = 로컬 픽스처 전부. GPU·Firestore 불필요)
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

CONF_MIN = cr.KP_CONF_MIN          # 0.5 — 표시 게이트에서 되읽음
TORSO_MIN_FRAC = 0.4               # collapse_scan.py 08-09 실측 신호
ASPECT_MIN = 0.25                  # 같음 (한 줄로 뭉침 탐지)
VISIBLE_DEG = 20.0                 # 참고선: 기존 마커 강조 임계(IPSF 허용오차 정합)
SWING_HALF_S = 0.5                 # 요동 창 — signal_vs_deviation.py 와 동일

_TORSO = ("left_shoulder", "right_shoulder", "left_hip", "right_hip")


def _series(align: dict, side: str):
    """프레임별 (몸통 길이, 가로/세로비) — 붕괴 판정용. align kp 좌표계 그대로."""
    aj = align["joints17"]
    F = int(align[f"{side}Frames"])
    kp = np.asarray(align[f"{side}Kp"], dtype=float).reshape(F, len(aj), 2)
    sc = np.asarray(align[f"{side}Score"], dtype=float)
    idx = {n: aj.index(n) for n in _TORSO}
    sh = (kp[:, idx["left_shoulder"]] + kp[:, idx["right_shoulder"]]) / 2
    hp = (kp[:, idx["left_hip"]] + kp[:, idx["right_hip"]]) / 2
    torso = np.linalg.norm(sh - hp, axis=1)
    aspect = np.full(F, np.nan)
    for i in range(F):
        m = sc[i] >= 0.3
        if int(m.sum()) < 6:
            continue
        xs, ys = kp[i, m, 0], kp[i, m, 1]
        h = float(ys.max() - ys.min())
        if h > 1e-9:
            aspect[i] = float(xs.max() - xs.min()) / h
    return torso, aspect


def _ok_frame(torso, aspect, med: float, i: int) -> bool:
    if i < 0 or i >= len(torso):
        return False
    if not np.isfinite(torso[i]) or torso[i] < TORSO_MIN_FRAC * med:
        return False
    a = aspect[i]
    return not (np.isfinite(a) and a < ASPECT_MIN)


def _swing(kp_at, joint: str, t: float, afps: float) -> float | None:
    """그 순간 관절각 요동 — ±0.5초 창의 max−min (신뢰 프레임만)."""
    step = 1.0 / afps
    n = int(round(SWING_HALF_S / step))
    vals = []
    for k in range(-n, n + 1):
        v = cr._joint_angle(kp_at, joint, t + k * step, conf_min=0.3)
        if v is not None:
            vals.append(v)
    if len(vals) < 5:
        return None
    return max(vals) - min(vals)


def run(case: str) -> list[dict]:
    d = ROOT / case
    doc = json.load(open(d / "doc.json"))
    align = json.load(open(d / "align.json"))
    res = doc["result"]
    curve = align.get("curveRefSec")
    pairs = align.get("pairs") or {}
    if not curve:
        print(f"\n=== {case} === curveRefSec 없음 — 건너뜀")
        return []

    afps = float(align["fps"])
    uF, rF = int(align["userFrames"]), int(align["refFrames"])
    try:
        u_at, r_at = cr._kp_reader(align, "user"), cr._kp_reader(align, "ref")
    except (KeyError, ValueError) as e:
        print(f"\n=== {case} === kp 트랙 없음({e}) — 건너뜀")
        return []
    ut_all, ua_all = _series(align, "user")
    rt_all, ra_all = _series(align, "ref")
    umed = statistics.median([v for v in ut_all if np.isfinite(v) and v > 0])
    rmed = statistics.median([v for v in rt_all if np.isfinite(v) and v > 0])

    print(f"\n=== {case} ===  user {uF}f / ref {rF}f @ {afps}fps  "
          f"torso중앙 u={umed:.4f} r={rmed:.4f}")

    out = []
    for rec in (res.get("deductionBreakdown") or {}).get("records") or []:
        crit = rec.get("criterion") or ""
        if "angle_vs_reference__" not in crit:
            continue
        jk = crit.split("__", 1)[1]
        if jk not in cr._ANGLE_TRIPLES:
            continue
        rid = (rec.get("recordId") or "").split(":")[0]
        pair = pairs.get(rid)
        if not pair:
            print(f"  {rid} {jk:<15} align.pairs 에 짝 없음 — 건너뜀")
            continue

        ut0 = float(pair["atVideoSec"])
        rt0 = float(pair["refVideoSec"])
        pd0 = pair.get("poseDist")
        pd0 = float(pd0) if pd0 is not None else None
        a0 = cr._joint_angle(u_at, jk, ut0, conf_min=CONF_MIN)
        b0 = cr._joint_angle(r_at, jk, rt0, conf_min=CONF_MIN)
        d0 = abs(a0 - b0) if (a0 is not None and b0 is not None) else None
        sw0 = _swing(u_at, jk, ut0, afps)

        # 클립 전수 스캔 — 게이트별 탈락 census 동반
        fail = {"conf": 0, "collapse": 0, "align": 0}
        cands = []
        for i in range(uF):
            ut = i / afps
            rt = float(curve[i])
            ri = int(round(rt * afps))
            a = cr._joint_angle(u_at, jk, ut, conf_min=CONF_MIN)
            b = cr._joint_angle(r_at, jk, rt, conf_min=CONF_MIN)
            if a is None or b is None:
                fail["conf"] += 1
                continue
            if not (_ok_frame(ut_all, ua_all, umed, i)
                    and _ok_frame(rt_all, ra_all, rmed, ri)):
                fail["collapse"] += 1
                continue
            pd = cr._pose_dist(u_at, r_at, ut, rt)
            if pd is None or (pd0 is not None and pd > pd0):
                fail["align"] += 1
                continue
            cands.append({"i": i, "ut": ut, "rt": rt, "d": abs(a - b), "pd": pd})

        row = {"case": case, "rid": rid, "joint": jk, "points": rec.get("points"),
               "deviation": rec.get("deviation"), "d0": d0, "sw0": sw0, "pd0": pd0,
               "ut0": ut0, "rt0": rt0, "n_cand": len(cands), "fail": fail}

        if cands:
            best = max(cands, key=lambda c: c["d"])
            sw = _swing(u_at, jk, best["ut"], afps)
            row.update({"best": best, "sw": sw,
                        "n_ge20": sum(1 for c in cands if c["d"] >= VISIBLE_DEG),
                        "n_ge2x": sum(1 for c in cands if d0 and c["d"] >= 2 * d0)})
            r0 = (d0 / sw0) if (d0 and sw0) else None
            r1 = (best["d"] / sw) if sw else None
            print(f"  {rid} {jk:<15} pts={rec.get('points')} dev={rec.get('deviation')}")
            print(f"      현행 표시  {ut0:6.2f}s ↔ {rt0:5.2f}s  차이 "
                  f"{'-' if d0 is None else f'{d0:5.1f}도'}  짝거리 "
                  f"{'-' if pd0 is None else f'{pd0:.3f}'}  "
                  f"요동 {'-' if sw0 is None else f'{sw0:5.1f}도'}  "
                  f"편차/요동 {'-' if r0 is None else f'{r0:.2f}'}")
            print(f"      후보 {len(cands):3d}개 (20도↑ {row['n_ge20']} / 2배↑ {row['n_ge2x']})"
                  f"  최선 {best['ut']:6.2f}s ↔ {best['rt']:5.2f}s  차이 "
                  f"{best['d']:5.1f}도  짝거리 {best['pd']:.3f}  "
                  f"요동 {'-' if sw is None else f'{sw:5.1f}도'}  "
                  f"편차/요동 {'-' if r1 is None else f'{r1:.2f}'}"
                  f"   {'← 개선 x%.1f' % (best['d'] / d0) if d0 else ''}")
        else:
            print(f"  {rid} {jk:<15} pts={rec.get('points')} — **후보 0개** "
                  f"(현행 차이 {'-' if d0 is None else f'{d0:.1f}도'})")
        print(f"      탈락: 신뢰 {fail['conf']} / 붕괴 {fail['collapse']} / "
              f"정렬 {fail['align']}  (총 {uF} 프레임)")
        out.append(row)
    return out


if __name__ == "__main__":
    cases = sys.argv[1:] or sorted(p.name for p in ROOT.iterdir()
                                   if p.is_dir() and (p / "align.json").exists())
    rows = []
    for c in cases:
        rows.extend(run(c))

    print("\n" + "=" * 108)
    print("종합 — 조건부 표시 순간이 있는가")
    print(f"{'case':<14}{'rid':<5}{'관절':<15}{'현행차이':>9}{'후보':>6}"
          f"{'최선차이':>9}{'배수':>7}{'현행 편차/요동':>15}{'최선 편차/요동':>15}")
    have = 0
    for r in rows:
        d0 = r["d0"]
        b = r.get("best")
        r0 = (d0 / r["sw0"]) if (d0 and r["sw0"]) else None
        r1 = (b["d"] / r["sw"]) if (b and r.get("sw")) else None
        mult = (b["d"] / d0) if (b and d0) else None
        if b:
            have += 1
        print(f"{r['case']:<14}{r['rid']:<5}{r['joint']:<15}"
              f"{'-' if d0 is None else f'{d0:8.1f}도'}{r['n_cand']:>6}"
              f"{'-' if not b else f'{b[chr(100)]:8.1f}도'}"
              f"{'-' if mult is None else f'x{mult:5.1f}'}"
              f"{'-' if r0 is None else f'{r0:14.2f}'}"
              f"{'-' if r1 is None else f'{r1:14.2f}'}")
    print(f"\nrecord {len(rows)}건 중 조건 동시 만족 후보를 가진 것 = {have}건")
