"""전역 교정이 점수를 얼마 움직이나 — 기준 경계 마진 9 → 8 프레임 (관찰 전용).

belle 질문: "표시 전용부터 하면 후속 작업이 또 생기는 것 아닌가."
그래서 전역 교정의 **점수 표면을 먼저 특정**했다. `_pipeline_frame_fps()` 소비처 중
채점에 닿는 것은 실질적으로 하나다:

    motiondtw.ref_boundary_step_mask:  margin = ceil(REF_BOUNDARY_EXCLUDE_S * ref_fps)

  · mode3 (ref_fps = 파이프라인 fps):  ceil(0.5×9.0)=5  →  ceil(0.5×9.997)=5   **불변**
  · mode1 (ref_fps = 기준 리포트 fps): ceil(0.5×18.0)=9 →  ceil(0.5×14.93)=8   **1프레임**

즉 전역 교정의 점수 영향은 **mode1 의 기준 경계 제외가 양끝에서 1프레임 좁아지는 것**
뿐이다(그 밖에는 Gemini 프롬프트의 초 라벨 문자열). 이 스크립트는 그 1프레임이 관절별
편차 median 을 실제로 얼마 움직이는지 로컬에서 잰다 — 채점 코드는 호출만 하고 무접촉.

usage: score_delta_ref_fps.py [case...]   (Firestore 읽기 필요 — 기준 angles)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "backend" / "shared" / "python"))

from sunity_shared import firestore_admin as fa  # noqa: E402
from sunity_shared.analysis import motiondtw as md  # noqa: E402
from sunity_shared.analysis import skeleton  # noqa: E402
from sunity_shared.analysis import temporal  # noqa: E402
from sunity_shared.analysis.features import compute_joint_angles, feature_vector  # noqa: E402

ROOT = REPO / ".planning/phases/35-server-rendered-comparison-video/data"
# 기준 영상 실측 길이(ffprobe) — 실제 rate = frames / duration
REF_DUR = {"ref-pdshape": 15.766667, "ref-peter-pan": 8.600000,
           "ref-power-spin": 10.533333, "ref-elbow-twist-sister": 21.866667,
           "ref-kip-up": 7.800000}


def user_angles_from_doc(res: dict) -> np.ndarray:
    keys = res.get("joints3dKeys") or []
    n = int(res.get("joints3dFrames") or 0)
    flat = np.asarray(res.get("joints3d") or [], dtype=float)
    if not (keys and n and flat.size == n * len(keys) * 3):
        raise ValueError("joints3d 형상 불량")
    arr = flat.reshape(n, len(keys), 3)
    coco = skeleton.to_coco17_array(arr, keys) if hasattr(skeleton, "to_coco17_array") \
        else arr
    # 파이프라인은 DTW 전에 temporal_fill 을 통과시킨다(features.feature_vector
    # 독스트링: "결측은 미리 fill_gaps 권장"). NaN 을 남기면 dtw 가 무한 재귀한다.
    return temporal.temporal_fill(compute_joint_angles(coco))


def run(case: str):
    doc = json.load(open(ROOT / case / "doc.json"))
    res = doc["result"]
    mid = (res.get("comparison") or {}).get("referenceMotionId")
    if not mid:
        print(f"{case}: referenceMotionId 없음 — 건너뜀")
        return
    ref = fa.get_reference_motion(mid) or {}
    ra = ref.get("angles")
    rn = int(ref.get("anglesFrames") or 0)
    label_fps = float((ref.get("referenceKeypointReport") or {}).get("fps") or 18.0)
    dur = REF_DUR.get(mid)
    if not (ra and rn and dur):
        print(f"{case}: 기준 angles/길이 미비 — 건너뜀")
        return
    real_fps = rn / dur
    J = len(ref.get("anglesJointKeys") or skeleton.JOINT_KEYS)

    try:
        ua = user_angles_from_doc(res)
    except Exception as e:  # noqa: BLE001 — 관찰 전용
        print(f"{case}: 사용자 각도 산출 실패({e}) — 건너뜀")
        return

    a_ref = temporal.temporal_fill(np.asarray(ra, dtype=float).reshape(-1, J))
    match = md.motion_dtw(feature_vector(ua), feature_vector(a_ref))
    user_seg = ua[match.start:match.end]
    a_ref_win = a_ref[match.ref_start:match.ref_end]

    d_lab = md.per_joint_deviation(match.path, user_seg, a_ref_win, ref_fps=label_fps)
    d_real = md.per_joint_deviation(match.path, user_seg, a_ref_win, ref_fps=real_fps)
    m_lab = math.ceil(md.REF_BOUNDARY_EXCLUDE_S * label_fps)
    m_real = math.ceil(md.REF_BOUNDARY_EXCLUDE_S * real_fps)

    print(f"\n=== {case} ({mid}) ===  기준 {rn}프레임 / {dur:.2f}s → 실제 "
          f"{real_fps:.2f}fps (라벨 {label_fps:.1f})   마진 {m_lab} → {m_real} 프레임")
    keys = ref.get("anglesJointKeys") or list(skeleton.JOINT_KEYS)
    worst = 0.0
    for i, k in enumerate(keys):
        a, b = float(d_lab[i]), float(d_real[i])
        if np.isnan(a) and np.isnan(b):
            continue
        delta = (b - a) if not (np.isnan(a) or np.isnan(b)) else float("nan")
        if not np.isnan(delta):
            worst = max(worst, abs(delta))
        flag = "  ←" if (not np.isnan(delta) and abs(delta) >= 0.1) else ""
        print(f"   {k:<16}{a:8.3f}도 → {b:8.3f}도   Δ {delta:+7.3f}{flag}")
    print(f"   최대 |Δ| = {worst:.3f}도")
    return worst


if __name__ == "__main__":
    cases = sys.argv[1:] or ["elbow", "pdshapefault", "peterpan", "powerspin", "kipup"]
    worsts = []
    for c in cases:
        w = run(c)
        if w is not None:
            worsts.append((c, w))
    print("\n" + "=" * 60)
    for c, w in worsts:
        print(f"{c:<16} 최대 편차 이동 {w:.3f}도")
    print("\n감점 점수는 편차×slope 라 이 Δ 가 점수 이동의 상한 근거가 된다 "
          "(0 이면 전역 교정도 점수 무접촉).")
