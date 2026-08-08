"""수술 ③ 가설 기계검증 — 그립팔 좌우 거울상 doc(elbow)에서 ref L/R 스왑이 편차를 개선하는가.

검출기 투자 전 가설 자체를 판정한다 (스크린 v0 선례: 전신 미러 위치공간 기각).
변형 3종: none / arms(elbow+shoulder) / full(4쌍 전부) — 각각 DTW 재정렬 포함.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path("/Users/kimtaesung/Dev/SunityMotion")
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from sunity_shared.analysis.features import feature_vector
from sunity_shared.analysis.motiondtw import motion_dtw, per_joint_deviation
from sunity_shared.analysis.skeleton import JOINT_KEYS

DATA = REPO / ".planning/phases/35-server-rendered-comparison-video/data"
CACHE = REPO / ".planning/quick/260808-r82-phase-34-3/data/reference_angles"
SLOTS = ["elbow", "powerspin", "kipup", "pdshapefault", "peterpan", "pdshape", "realupload"]

PAIRS = [("left_elbow", "right_elbow"), ("left_shoulder", "right_shoulder"),
         ("left_hip", "right_hip"), ("left_knee", "right_knee")]


def swap_cols(a, keys, pairs):
    out = a.copy()
    for l, r in pairs:
        li, ri = keys.index(l), keys.index(r)
        out[:, [li, ri]] = out[:, [ri, li]]
    return out


def rescore(user, a_ref, ref_fps):
    match = motion_dtw(feature_vector(user), feature_vector(a_ref))
    dev = per_joint_deviation(
        match.path, user[match.start:match.end],
        a_ref[match.ref_start:match.ref_end],
        ref_fps=float(ref_fps) if ref_fps else None)
    return dev, match


for slot in SLOTS:
    doc = json.loads((DATA / slot / "doc.json").read_text())
    keys = list(doc["anglesJointKeys"])
    user = np.asarray(doc["angles"], float).reshape(-1, len(keys))
    mid = doc["referenceMotionId"]
    rc = json.loads((CACHE / f"{mid}.json").read_text())
    a_ref = np.asarray(rc["angles"], float).reshape(-1, len(keys))
    fps = rc.get("keypointReportFps")

    d0, m0 = rescore(user, a_ref, fps)
    d_arm, m1 = rescore(user, swap_cols(a_ref, keys, PAIRS[:2]), fps)
    d_full, m2 = rescore(user, swap_cols(a_ref, keys, PAIRS), fps)

    arm_idx = [keys.index(k) for p in PAIRS[:2] for k in p]
    leg_idx = [keys.index(k) for p in PAIRS[2:] for k in p]
    print(f"\n== {slot} (ref={mid}) dtw_dist none={m0.distance:.4f} arms={m1.distance:.4f} full={m2.distance:.4f}")
    print(f"   arm devs  none={np.round(d0[arm_idx],1)} mean={np.nanmean(d0[arm_idx]):.2f}")
    print(f"             arms={np.round(d_arm[arm_idx],1)} mean={np.nanmean(d_arm[arm_idx]):.2f}")
    print(f"             full={np.round(d_full[arm_idx],1)} mean={np.nanmean(d_full[arm_idx]):.2f}")
    print(f"   leg devs  none={np.round(d0[leg_idx],1)} mean={np.nanmean(d0[leg_idx]):.2f}")
    print(f"             full={np.round(d_full[leg_idx],1)} mean={np.nanmean(d_full[leg_idx]):.2f}")

print("\n\n===== 변형 B: 정렬 원본 유지, per-joint 짝만 스왑 (pairing-only) =====")
for slot in SLOTS:
    doc = json.loads((DATA / slot / "doc.json").read_text())
    keys = list(doc["anglesJointKeys"])
    user = np.asarray(doc["angles"], float).reshape(-1, len(keys))
    mid = doc["referenceMotionId"]
    rc = json.loads((CACHE / f"{mid}.json").read_text())
    a_ref = np.asarray(rc["angles"], float).reshape(-1, len(keys))
    fps = rc.get("keypointReportFps")

    match = motion_dtw(feature_vector(user), feature_vector(a_ref))
    seg = user[match.start:match.end]
    win = a_ref[match.ref_start:match.ref_end]
    kw = dict(ref_fps=float(fps)) if fps else {}
    d0 = per_joint_deviation(match.path, seg, win, **kw)
    d_pair = per_joint_deviation(match.path, seg, swap_cols(win, keys, PAIRS[:2]), **kw)
    arm_idx = [keys.index(k) for p in PAIRS[:2] for k in p]
    print(f"{slot:14s} arm none={np.round(d0[arm_idx],1)} mean={np.nanmean(d0[arm_idx]):.2f} | pair-swap={np.round(d_pair[arm_idx],1)} mean={np.nanmean(d_pair[arm_idx]):.2f}")
