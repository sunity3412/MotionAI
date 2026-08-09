"""r01(오른 팔꿈치)이 진짜 결함인지 · r02 짝을 더 맞출 수 있는지 — 기계 점검.

원칙: belle 말에 맞추지 않는다. 서로 다른 두 포즈 추출로 교차 확인하고,
차이가 있으면 있는 대로 숫자를 낸다.
  · 소스 A = 분석 파이프라인 keypointReport (채점이 쓴 것)
  · 소스 B = p35 align (영상 정렬이 쓴 것 — 별도 추출)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/kimtaesung/Dev/SunityMotion/backend/shared/python")

from sunity_shared.analysis import compare_render as cr  # noqa: E402

DATA = Path("/Users/kimtaesung/Dev/SunityMotion/.planning/phases/"
            "35-server-rendered-comparison-video/data/pdshapefault")
WORK = Path("/private/tmp/claude-501/-Users-kimtaesung-Dev-SunityMotion/"
            "7d81a5c5-cd3a-46db-8789-ec1c3cfaa699/scratchpad/p35work")

doc = json.load(open(DATA / "doc.json"))
align = json.load(open(DATA / "align.json"))
res = doc["result"]
u_at, r_at = cr._kp_reader(align, "user"), cr._kp_reader(align, "ref")

print("=" * 74)
print("감점 record 원문 (파이프라인이 실제로 낸 값)")
for rec in (res.get("deductionBreakdown") or {}).get("records") or []:
    print(" ", {k: v for k, v in rec.items() if k in (
        "recordId", "criterion", "atFrameIdx", "points", "measuredValue",
        "referenceValue", "deviation", "severity", "unit")})

# 영상이 정한 정지 순간 (probe 없이 build_timeline 재현은 무거우므로 zoom 로그 값 사용)
MOMENTS = {"r00": (8.56, 9.37, "left_elbow"), "r01": (1.22, 2.23, "right_elbow"),
           "r02": (3.22, 2.00, "left_shoulder"), "r03": (3.67, 2.40, "left_knee")}


def series(kp_at, joint, t0, half=0.5, step=1 / 15):
    ts = np.arange(t0 - half, t0 + half + 1e-9, step)
    vals = [(t, cr._joint_angle(kp_at, joint, float(t))) for t in ts]
    return [(t, v) for t, v in vals if v is not None]


def conf_of(kp_at, names, t):
    return {n: round(float(kp_at(n, t)[1]), 2) for n in names}


print("\n" + "=" * 74)
print("r01 오른 팔꿈치 — 진짜 차이인가 (소스 B: 영상정렬 추출)")
ut, rt, _ = MOMENTS["r01"]
us, rs = series(u_at, "right_elbow", ut), series(r_at, "right_elbow", rt)
if us and rs:
    uv = np.array([v for _, v in us])
    rv = np.array([v for _, v in rs])
    print(f"  학생  순간 {cr._joint_angle(u_at,'right_elbow',ut):.1f}도 | "
          f"±0.5초 중앙 {np.median(uv):.1f}도 (폭 {uv.min():.0f}~{uv.max():.0f})")
    print(f"  정은지 순간 {cr._joint_angle(r_at,'right_elbow',rt):.1f}도 | "
          f"±0.5초 중앙 {np.median(rv):.1f}도 (폭 {rv.min():.0f}~{rv.max():.0f})")
    print(f"  중앙값 차이 = {np.median(uv) - np.median(rv):+.1f}도")
print("  신뢰도 학생 ", conf_of(u_at, ("right_shoulder", "right_elbow", "right_wrist"), ut))
print("  신뢰도 정은지", conf_of(r_at, ("right_shoulder", "right_elbow", "right_wrist"), rt))

print("\n  belle 관찰 — '정은지 오른팔이 폴에 더 밀착' 을 수치로:")
poles = {"user": cr._detect_pole(WORK / "u30_1080", align, "user"),
         "ref": cr._detect_pole(WORK / "r30_1080", align, "ref")}
for side, t in (("user", ut), ("ref", rt)):
    p = poles[side]
    if not p:
        print(f"    {side}: 폴 미검출")
        continue
    for joint in ("right_elbow", "right_wrist"):
        s, torso = cr._pole_gap_series(align, side, joint, p["xNorm"])
        i = int(round(t * float(align["fps"])))
        i = max(0, min(len(s) - 1, i))
        print(f"    {side:<4} {joint:<12} 폴까지 거리 = 몸통의 {s[i]:.3f}배  "
              f"(임계 {cr.POLE_MARGIN})")

print("\n" + "=" * 74)
print("r02 왼 어깨 — 더 맞는 순간이 있는가 (짝 자세 거리, 넓게 ±2초)")
ut2, rt2, _ = MOMENTS["r02"]
best = []
for k in range(-60, 61):
    t = rt2 + k / 30.0
    if not (0 <= t <= float(align["refFrames"]) / float(align["fps"])):
        continue
    d = cr._pose_dist(u_at, r_at, ut2, t)
    if d is not None:
        best.append((d, t))
best.sort()
cur = cr._pose_dist(u_at, r_at, ut2, rt2)
print(f"  현재 채택 rt={rt2:.2f}s  거리={cur:.4f}")
print("  ±2초 안 최선 5개:")
for d, t in best[:5]:
    print(f"    rt={t:.2f}s  거리={d:.4f}  ({(d - cur) / cur * 100:+.1f}% vs 현재)  "
          f"이동 {t - rt2:+.2f}s")
print(f"  현재 창(±0.4초) 안 최선 = "
      f"{min([(d, t) for d, t in best if abs(t - rt2) <= 0.4], default=(None, None))}")
