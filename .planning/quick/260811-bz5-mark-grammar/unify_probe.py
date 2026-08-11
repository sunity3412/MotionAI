#!/usr/bin/env python3
"""같은 영상(belle pdshape fault)의 3개 분석 doc 감점 통일 프로브 (관측 전용).

belle 08-11: "영상이랑 사진 감점 doc 잘 비교해서 통일하는 작업부터" + "정말
짜맞추는 게 아닌지 정밀 검토". 규율: **내(기계) 판정을 먼저 박제하고 belle 판정
자리를 비워둔다** — 판정 순서가 기록에 남아야 짜맞춤과 구별된다.

세 doc (전부 같은 영상 — md5 일치는 08-08 실증 완료):
  A. pdshapefault1785373695 — 승인 합성 영상(pdshape_v3.mp4)의 출처. 62점 4건.
  B. 127a2a90c1d74c62ad61270eb3fe5625 — belle 앱 업로드. 72점 3건 (종점 아티팩트 시절).
  C. p34fresh1786363530 — 08-10 재분석(수술 후). 60점 5건. 확대 카드의 출처.

반증 시험 (belle 가설 "골반 편차 = 무릎 파생"):
  둘 다 왼무릎을 편(>=150도) 프레임끼리 비교하면 왼골반 편차가 허용오차(20도)
  아래로 내려가야 한다. 안 내려가면 가설 기각으로 보고한다.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402
from sunity_shared.analysis.skeleton import JOINT_ANGLES  # noqa: E402

CACHE = pathlib.Path(
    "/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
    "4ecaa5a2-717b-43a6-a9c5-e152a330b7a3/scratchpad/doc_cache.json"
)
P35 = _REPO / ".planning/phases/35-server-rendered-comparison-video/data/pdshapefault/doc.json"
NAME = {"left_wrist": "left_hand", "right_wrist": "right_hand"}


def inner(rep: dict, kp_idx: int, joint: str) -> float | None:
    tri = [NAME.get(n, n) for n in JOINT_ANGLES[joint]]
    p = [fz._gated_kp(rep, kp_idx, n) for n in tri]
    if not all(p):
        return None
    a, v, b = p
    f = lambda q: math.atan2(q[1] - v[1], q[0] - v[0])  # noqa: E731
    x = math.degrees(abs(f(a) - f(b))) % 360
    return min(x, 360 - x)


def main() -> int:
    d = json.loads(CACHE.read_text())
    urep, rrep = d["userReport"], d["refReport"]
    un, rn = int(urep["frames"]), int(rrep["frames"])

    # ── 반증 시험: 왼무릎 둘 다 신전(>=150) 프레임 집합에서 왼골반 편차 분포 ──
    EXT = 150.0
    u_ext = [(i, inner(urep, i, "left_hip"))
             for i in range(un)
             if (k := inner(urep, i, "left_knee")) is not None and k >= EXT]
    r_ext = [(i, inner(rrep, i, "left_hip"))
             for i in range(rn)
             if (k := inner(rrep, i, "left_knee")) is not None and k >= EXT]
    u_hips = [h for _, h in u_ext if h is not None]
    r_hips = [h for _, h in r_ext if h is not None]
    print("== 반증 시험: 왼무릎 신전(>=150도) 프레임끼리의 왼골반 각도 ==")
    print(f"  user 신전 프레임 {len(u_ext)}개 (골반 측정가능 {len(u_hips)}) "
          f"@ {[round(i/18,1) for i,_ in u_ext[:12]]}s")
    print(f"  ref  신전 프레임 {len(r_ext)}개 (골반 측정가능 {len(r_hips)}) "
          f"@ {[round(i/18,1) for i,_ in r_ext[:12]]}s")
    if u_hips and r_hips:
        um, rm = float(np.median(u_hips)), float(np.median(r_hips))
        print(f"  왼골반 중앙값: user {um:.0f}도 vs ref {rm:.0f}도 → 편차 {abs(um-rm):.1f}도"
              f" (허용 20도 {'이내 → 가설 지지' if abs(um-rm) < 20 else '초과 → 가설 기각'})")
        print(f"  분포 user {min(u_hips):.0f}~{max(u_hips):.0f} / ref {min(r_hips):.0f}~{max(r_hips):.0f}")
    else:
        print("  판정 불가 — 신전 프레임에서 골반 측정가능 표본 부족 (fail-closed)")

    # ── 접힘 상태 대조(참고): 왼무릎 굽힘(<=100) 프레임의 왼골반 ──
    u_fold = [h for i in range(un)
              if (k := inner(urep, i, "left_knee")) is not None and k <= 100
              and (h := inner(urep, i, "left_hip")) is not None]
    if u_fold and r_hips:
        print(f"  참고: user 무릎 굽힘 프레임의 골반 중앙값 {np.median(u_fold):.0f}도"
              f" (신전 ref {np.median(r_hips):.0f}도와의 차 {abs(np.median(u_fold)-np.median(r_hips)):.1f}도)")

    # ── 3-doc 감점 통일 표 ──
    p35doc = json.loads(P35.read_text())
    a_recs = (p35doc["result"].get("deductionBreakdown") or {}).get("records") or []
    print("\n== 3-doc 감점 대조 (같은 영상) ==")
    print("A=승인영상 doc(62점) · B=belle 업로드(72점, 종점 아티팩트 시절) · C=사진 doc(60점)")
    b_recs = [  # 08-11 Firestore 실조회 값 박제 (dump 스크립트 출력 그대로)
        ("angle_vs_reference__left_elbow", 17.78, 11.47),
        ("angle_vs_reference__left_knee", 17.56, 5.79),
        ("angle_vs_reference__right_knee", 11.67, 5.71),
    ]
    c_recs = [(r.get("criterion"), round(float(r.get("atVideoSec", 0)), 2),
               float(r.get("deviation", 0)))
              for r in (d.get("records") or [])]
    if not c_recs:
        # doc_cache 에 records 미포함 시 Firestore 재조회 없이 하드 박제 (08-11 실조회)
        c_recs = [
            ("angle_vs_reference__left_elbow", 5.30, 9.64),
            ("angle_vs_reference__right_elbow", 6.10, 9.68),
            ("angle_vs_reference__right_shoulder", 13.80, 5.56),
            ("angle_vs_reference__left_hip", 4.70, 5.22),
            ("angle_vs_reference__left_knee", 10.50, 7.35),
        ]
    axes = sorted({c for c, *_ in [(r.get("criterion"),) for r in a_recs]}
                  | {c for c, *_ in b_recs} | {c for c, *_ in c_recs})
    amap = {r.get("criterion"): (round(float(r.get("atVideoSec", 0)), 2),
                                 float(r.get("deviation", 0))) for r in a_recs}
    bmap = {c: (s, v) for c, s, v in b_recs}
    cmap = {c: (s, v) for c, s, v in c_recs}
    print(f"{'축':<42}{'A(승인영상)':>14}{'B(업로드)':>13}{'C(사진)':>12}")
    for ax in axes:
        cells = []
        for m in (amap, bmap, cmap):
            cells.append(f"{m[ax][0]}s/{m[ax][1]:.1f}" if ax in m else "-")
        print(f"{ax:<42}{cells[0]:>14}{cells[1]:>13}{cells[2]:>12}")
    print("\n세 doc 에 공통 = left_elbow · left_knee 뿐. 순간은 셋 다 다름.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
