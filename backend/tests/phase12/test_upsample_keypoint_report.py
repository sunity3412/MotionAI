"""Phase 12 hotfix (2026-06-11) — upsample_to_fps unit tests.

belle UAT 1차 결과:
  1. 빠른 회전 시 keypoint 끊김
  2. 영상 끝부분 keypoint 정지
  → 분석은 9fps 유지, 저장 시점에 30fps 선형 보간 (Firestore size ~560 KiB 안).
"""

from __future__ import annotations

from sunity_shared.analysis.keypoint_frame import (
    KeypointReport,
    upsample_to_fps,
    _AXIS_POLYLINE_POINTS,
)


def _make_report(frames: int, fps: float = 9.0) -> KeypointReport:
    """2 joint × frames KeypointReport — 단조 증가 좌표로 보간 검증 가능."""
    joints = ["left_shoulder", "right_shoulder"]
    J = len(joints)
    # data flat T*J*2: 각 frame t 의 (x, y) = (t * 0.01, t * 0.02) 모든 joint 동일
    data: list[float] = []
    for t in range(frames):
        for _j in range(J):
            data.append(t * 0.01)
            data.append(t * 0.02)
    confidence = [0.9] * (frames * J)
    reliability = ["high"] * frames
    # axis_data flat T*3*2: 각 point 동일 좌표 (t * 0.005, t * 0.005)
    axis_data: list[float] = []
    for t in range(frames):
        for _p in range(_AXIS_POLYLINE_POINTS):
            axis_data.append(t * 0.005)
            axis_data.append(t * 0.005)
    axis_mask = [True] * (frames * _AXIS_POLYLINE_POINTS)
    return KeypointReport(
        version="1.0",
        joints=joints,
        frames=frames,
        fps=fps,
        data=data,
        confidence=confidence,
        reliability=reliability,
        axis_data=axis_data,
        axis_mask=axis_mask,
        warnings=[],
    )


def test_upsample_no_op_when_target_le_source_fps():
    r = _make_report(frames=10, fps=9.0)
    out = upsample_to_fps(r, target_fps=9.0)
    assert out is r
    out = upsample_to_fps(r, target_fps=5.0)
    assert out is r


def test_upsample_returns_same_when_frames_lt_2():
    r0 = _make_report(frames=0, fps=9.0)
    out0 = upsample_to_fps(r0, target_fps=30.0)
    assert out0 is r0
    r1 = _make_report(frames=1, fps=9.0)
    out1 = upsample_to_fps(r1, target_fps=30.0)
    assert out1 is r1


def test_upsample_9_to_30_increases_frame_count_proportionally():
    # 153 frame at 9 fps = 17 sec → 30 fps target = 510 frame
    r = _make_report(frames=153, fps=9.0)
    out = upsample_to_fps(r, target_fps=30.0)
    assert out.fps == 30.0
    assert out.frames == 510
    assert len(out.data) == 510 * 2 * 2
    assert len(out.confidence) == 510 * 2
    assert len(out.reliability) == 510
    assert len(out.axis_data) == 510 * 3 * 2
    assert len(out.axis_mask) == 510 * 3


def test_upsample_preserves_endpoint_coordinates():
    r = _make_report(frames=10, fps=9.0)
    out = upsample_to_fps(r, target_fps=30.0)
    # 첫 frame 좌표 그대로 (t=0 → x=0, y=0)
    assert out.data[0] == 0.0
    assert out.data[1] == 0.0
    # 마지막 frame 좌표 (t=9 → x=0.09, y=0.18) 유지
    J = 2
    last_off = (out.frames - 1) * J * 2
    assert abs(out.data[last_off] - 0.09) < 1e-9
    assert abs(out.data[last_off + 1] - 0.18) < 1e-9


def test_upsample_linear_interpolation_midpoint():
    # frame 0 = (0, 0), frame 1 = (0.01, 0.02). 30fps 중간 위치 = 약 9/30=0.3
    # at t=0.3 (lo=0, hi=1, w=0.3) → x = 0.003, y = 0.006
    r = _make_report(frames=2, fps=9.0)
    out = upsample_to_fps(r, target_fps=30.0)
    # 2 frame × 9fps = 0.222 sec. 30fps = 6 frame. 1번째 (idx=1) 위치 = 0.3
    # out.data[1 * 2 * 2 + 0] = first joint x at frame 1
    assert out.frames >= 2
    J = 2
    # 보간 위치 1 (= 1 * 9/30 = 0.3)
    x_at_1 = out.data[1 * J * 2 + 0]
    y_at_1 = out.data[1 * J * 2 + 1]
    assert abs(x_at_1 - 0.003) < 1e-9
    assert abs(y_at_1 - 0.006) < 1e-9


def test_upsample_reliability_nearest_neighbor():
    r = _make_report(frames=10, fps=9.0)
    # 5번째 frame 만 'low' 박제
    reliability = ["high"] * 10
    reliability[5] = "low"
    r = KeypointReport(
        version=r.version,
        joints=r.joints,
        frames=r.frames,
        fps=r.fps,
        data=r.data,
        confidence=r.confidence,
        reliability=reliability,
        axis_data=r.axis_data,
        axis_mask=r.axis_mask,
        warnings=r.warnings,
    )
    out = upsample_to_fps(r, target_fps=30.0)
    # frame 5 (1초 미만) = 9fps src_idx 5 / 30fps target_idx 약 5*30/9 ≈ 16-17
    low_count = sum(1 for r in out.reliability if r == "low")
    assert low_count > 0  # nearest neighbor 으로 1개 이상 보존
    high_count = sum(1 for r in out.reliability if r == "high")
    assert high_count > 0  # 나머지는 high
