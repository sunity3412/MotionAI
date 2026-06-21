"""fault_zoom 확대 비교 이미지 생성 단위테스트 (belle 2026-06-21).

순수 — PIL/numpy 외 의존 0 (S3/네트워크/firestore import 금지). 합성 프레임 +
합성 keypointReport 로 인덱싱(프레임배열 fps vs report fps 분리) + crop + PNG 출력 +
좌표 부재/미매핑 관절 skip 을 못 박는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_SHARED = Path(__file__).resolve().parents[1] / "shared" / "python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from sunity_shared.analysis import fault_zoom as fz  # noqa: E402


def _frames(n: int, h: int = 200, w: int = 120) -> np.ndarray:
    a = np.zeros((n, h, w, 3), dtype=np.uint8)
    for i in range(n):
        a[i, :, :, 0] = (i * 10) % 255
    return a


def _report(n: int, fps: float, joints=("left_knee", "right_knee", "left_hip")):
    nj = len(joints)
    data: list[float] = []
    for _f in range(n):
        for _j in range(nj):
            data += [0.5, 0.5]  # 중앙
    return {"joints": list(joints), "frames": n, "fps": fps, "data": data}


def test_build_produces_valid_png_with_deficit_marker():
    comps = fz.build_fault_zoom_comparisons(
        _frames(18), _frames(9), _report(18, 18.0), _report(9, 9.0),
        worst_seconds=0.5,
        fault_joints=["left_knee", "right_knee"],
        joint_deltas={"left_knee": 23.0},
        frames_fps=9.0,
    )
    assert len(comps) == 2
    by_joint = {c["joint"]: c for c in comps}
    assert by_joint["left_knee"]["deficitDeg"] == 23.0
    assert by_joint["right_knee"]["deficitDeg"] is None
    for c in comps:
        assert c["png"][:4] == b"\x89PNG", "유효 PNG 시그니처"


def test_unmapped_joint_skipped():
    # left_hand 는 report.joints 에 없음 → 좌표 부재 → skip (빈 결과).
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=0.5, fault_joints=["left_hand"], joint_deltas=None,
        frames_fps=9.0,
    )
    assert comps == []


def test_dedup_and_max_items():
    comps = fz.build_fault_zoom_comparisons(
        _frames(9), _frames(9), _report(9, 9.0), _report(9, 9.0),
        worst_seconds=None,  # None → 중앙 프레임 (graceful)
        fault_joints=["left_knee", "left_knee", "right_knee", "left_hip"],
        joint_deltas=None, frames_fps=9.0, max_items=2,
    )
    joints = [c["joint"] for c in comps]
    assert joints == ["left_knee", "right_knee"], "중복 제거 + max_items 2"


def test_none_frames_graceful():
    assert fz.build_fault_zoom_comparisons(
        None, None, {}, {}, 0.0, ["left_knee"], None
    ) == []
