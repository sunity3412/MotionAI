"""마진 9→8 이 감점 유무를 뒤집는가 — 허용오차 경계 통과 전수 (관찰 전용).

U3 백필은 기준 경계 제외 마진을 `ceil(0.5s × 18.0)=9` → `ceil(0.5s × 14.93)=8` 프레임으로
좁힌다. 260810-cbt 는 편차 median 이동이 ≤0.6도라고 쟀지만, **크기만으로는 안전을
단정할 수 없다** — `reference_relative` 감점은

    over = max(0.0, d − tolerance)      (deduction_engine.py:609, tolerance 20.0, slope 1.2)

이므로 `d` 가 20.0 을 건너면 **감점 카드가 생기거나 사라진다**. 0.6도가 경계 위에 놓이면
0.6도짜리 이동이 카드 1장을 바꾼다. 여기서 그 통과를 전수로 센다.

임계·기울기는 `ipsf_criteria.CRITERION_GROUPS` 에서 되읽는다(자의 수치 0).

usage: boundary_flip.py [case...]   (Firestore 읽기 — 기준 angles/실측 rate)
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
from sunity_shared.analysis import ipsf_criteria as ic  # noqa: E402
from sunity_shared.analysis import motiondtw as md  # noqa: E402
from sunity_shared.analysis import skeleton, temporal  # noqa: E402
from sunity_shared.analysis.features import compute_joint_angles, feature_vector  # noqa: E402
from sunity_shared.analysis.frame_extractor import effective_fps  # noqa: E402

ROOT = REPO / ".planning/phases/35-server-rendered-comparison-video/data"
# 기준 영상 실측 (ffprobe) — src_fps 로 실효 rate 를 유도한다(백필 스크립트와 동일 식)
REF_SRC = {"ref-pdshape": 29.8734, "ref-peter-pan": 29.7683,
           "ref-power-spin": 30.0, "ref-elbow-twist-sister": 29.9087,
           "ref-kip-up": 30.0}


def crit_for(jk: str):
    cid = f"angle_vs_reference__{jk}"
    for c in ic.CRITERION_GROUPS:
        if c.get("id") == cid:
            return cid, float(c["tolerance"]), float(c.get("slope") or 1.0)
    return cid, None, None


def user_angles(res: dict):
    keys, n = res.get("joints3dKeys") or [], int(res.get("joints3dFrames") or 0)
    flat = np.asarray(res.get("joints3d") or [], dtype=float)
    if not (keys and n and flat.size == n * len(keys) * 3):
        return None
    return temporal.temporal_fill(compute_joint_angles(flat.reshape(n, len(keys), 3)))


def run(case: str):
    doc = json.load(open(ROOT / case / "doc.json"))
    res = doc["result"]
    mid = (res.get("comparison") or {}).get("referenceMotionId")
    ref = fa.get_reference_motion(mid) or {}
    ra, rn = ref.get("angles"), int(ref.get("anglesFrames") or 0)
    label = float((ref.get("referenceKeypointReport") or {}).get("fps") or 18.0)
    src = REF_SRC.get(mid)
    ua = user_angles(res)
    if not (ra and rn and src and ua is not None):
        print(f"{case}: 재료 미비 — 건너뜀")
        return []
    real = effective_fps(src, label)
    keys = ref.get("anglesJointKeys") or list(skeleton.JOINT_KEYS)
    a_ref = temporal.temporal_fill(np.asarray(ra, dtype=float).reshape(-1, len(keys)))

    match = md.motion_dtw(feature_vector(ua), feature_vector(a_ref))
    seg, win = ua[match.start:match.end], a_ref[match.ref_start:match.ref_end]
    d_lab = md.per_joint_deviation(match.path, seg, win, ref_fps=label)
    d_real = md.per_joint_deviation(match.path, seg, win, ref_fps=real)
    m_lab = math.ceil(md.REF_BOUNDARY_EXCLUDE_S * label)
    m_real = math.ceil(md.REF_BOUNDARY_EXCLUDE_S * real)

    print(f"\n=== {case} ({mid}) === 라벨 {label:.1f} → 실측 {real:.3f}fps  "
          f"마진 {m_lab} → {m_real} 프레임")
    rows = []
    for i, jk in enumerate(keys):
        cid, tol, slope = crit_for(jk)
        if tol is None:
            continue
        a, b = float(d_lab[i]), float(d_real[i])
        if math.isnan(a) or math.isnan(b):
            continue
        em_a, em_b = a > tol, b > tol
        pt_a, pt_b = max(0.0, a - tol) * slope, max(0.0, b - tol) * slope
        near = min(abs(a - tol), abs(b - tol))
        flip = "  ★생김" if (em_b and not em_a) else ("  ★사라짐" if (em_a and not em_b) else "")
        warn = "  (경계 0.6도 이내)" if (not flip and near <= 0.6) else ""
        rows.append((case, jk, a, b, tol, em_a, em_b, pt_a, pt_b, near, bool(flip)))
        print(f"   {jk:<16}{a:7.3f} → {b:7.3f}도 (tol {tol:.0f})  감점 "
              f"{'O' if em_a else '·'}→{'O' if em_b else '·'}  "
              f"{-pt_a:6.2f} → {-pt_b:6.2f}점  경계까지 {near:6.3f}도{flip}{warn}")
    return rows


if __name__ == "__main__":
    cases = sys.argv[1:] or ["elbow", "pdshapefault", "peterpan", "powerspin", "kipup"]
    allr = []
    for c in cases:
        allr.extend(run(c))
    flips = [r for r in allr if r[10]]
    near = [r for r in allr if not r[10] and r[9] <= 0.6]
    dpts = sum(abs(r[8] - r[7]) for r in allr)
    print("\n" + "=" * 74)
    print(f"관절-동작 조합 {len(allr)}건 검사")
    print(f"  감점 유무 **뒤집힘**: {len(flips)}건" +
          ("" if not flips else " → " + ", ".join(f"{r[0]}/{r[1]}" for r in flips)))
    print(f"  뒤집히진 않았지만 경계 0.6도 이내: {len(near)}건" +
          ("" if not near else " → " + ", ".join(f"{r[0]}/{r[1]}({r[9]:.2f}도)" for r in near)))
    print(f"  점수 이동 합계(절대값): {dpts:.2f}점")
    print("\n한계: 이 표는 로컬에서 DTW 를 재구성한 근사다(confidence 가중 temporal_fill "
          "미전달). 그리고 noise-floor 억제(deduction_engine 의 median 신뢰구간 게이트)는 "
          "여기서 재현하지 않았다 — 그 게이트도 경계를 갖는다.")
