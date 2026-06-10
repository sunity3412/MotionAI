"""Phase 12 Wave 0A 단위 테스트 공통 fixture — PoseFrame + Keypoint2D factory.

Phase 9 conftest 패턴 mirror. Phase 12 의 RTMW keypoints_2d wiring + axis polyline +
kismam.assess() 3 kwarg 검증 test 가 공통으로 쓰는 factory helper.

Cite: 12-00-PLAN.md Task T5 + Phase 9 backend/tests/phase09/conftest.py 정합.
"""

from __future__ import annotations

from sunity_shared.analysis.pose_frame import Keypoint2D, PoseFrame
from sunity_shared.analysis.skeleton import KEYPOINT_NAMES


def _make_keypoint_2d(
    *,
    x: float = 0.5,
    y: float = 0.5,
    vis: float = 0.9,
) -> Keypoint2D:
    """Keypoint2D frozen dataclass — Phase 12 R1 + R6 정합.

    Keypoint2D = (x, y, visibility) 3 필드만 (Landmark2D 의 raw_visibility/raw_presence
    와 별개). default (0.5, 0.5, 0.9) = 화면 중앙 + high reliability.
    """
    return Keypoint2D(x=x, y=y, visibility=vis)


def _make_pose_frame(
    *,
    frame_idx: int = 0,
    timestamp_ms: int = 0,
    keypoints_2d: dict[str, Keypoint2D] | None = None,
) -> PoseFrame:
    """PoseFrame factory — keypoints_2d 박제 + 나머지 필드 default.

    Phase 12 axis polyline test 의 source. keypoints_2d=None (default) 시 PoseFrame
    의 R1 fallback path 시뮬 (RTMW adapter image dim 0 case 와 동일 의미).

    Phase 12 R2 test 시 keypoints_2d 박제 dict 넘기면 compute_axis_frames 가 폴리라인 산출.
    """
    return PoseFrame(
        frame_index=frame_idx,
        timestamp_ms=timestamp_ms,
        raw_landmarks_33={},
        keypoints_3d={},
        keypoints_3d_pole_aligned={},
        keypoints_2d=keypoints_2d,
        pole_extension_landmarks=None,
        pole_axis=None,
        reliability="high",
        body_shape=None,
    )


def _make_default_keypoints_2d_full() -> dict[str, Keypoint2D]:
    """COCO-17 17 joint 모두 default Keypoint2D 박제 — axis polyline full case test.

    좌우 어깨 / 골반 / 무릎 각 좌우 = 6 박제 (axis 3 point) + 17 keypoint 전수.
    각 (x, y) 는 분리된 위치 박제 — midpoint 계산이 (0.5, 0.5) 단일 점 아니게.
    """
    # 좌측 (x=0.3), 우측 (x=0.7), 어깨 y=0.2 / 골반 y=0.5 / 무릎 y=0.8 박제.
    pos: dict[str, tuple[float, float]] = {
        "nose": (0.5, 0.1),
        "left_eye": (0.45, 0.08),
        "right_eye": (0.55, 0.08),
        "left_ear": (0.40, 0.10),
        "right_ear": (0.60, 0.10),
        "left_shoulder": (0.3, 0.2),
        "right_shoulder": (0.7, 0.2),
        "left_elbow": (0.25, 0.35),
        "right_elbow": (0.75, 0.35),
        "left_wrist": (0.20, 0.50),
        "right_wrist": (0.80, 0.50),
        "left_hip": (0.35, 0.5),
        "right_hip": (0.65, 0.5),
        "left_knee": (0.35, 0.8),
        "right_knee": (0.65, 0.8),
        "left_ankle": (0.35, 0.95),
        "right_ankle": (0.65, 0.95),
    }
    return {name: _make_keypoint_2d(x=x, y=y) for name, (x, y) in pos.items()}


def _make_pose_frames_sequence(
    *,
    n_frames: int = 10,
    fps: int = 9,
    with_keypoints_2d: bool = True,
) -> list[PoseFrame]:
    """n 개 PoseFrame list — timestamp_ms 자동 박제 (fps 기반).

    Phase 12 axis polyline batch test (compute_axis_frames) 용.
    with_keypoints_2d=False 시 keypoints_2d=None (R1 fallback 시뮬).
    """
    if n_frames <= 0:
        return []
    if fps <= 0:
        raise ValueError("fps must be positive")
    dt_ms = int(1000.0 / fps)
    kp = _make_default_keypoints_2d_full() if with_keypoints_2d else None
    return [
        _make_pose_frame(
            frame_idx=i,
            timestamp_ms=i * dt_ms,
            keypoints_2d=kp,
        )
        for i in range(n_frames)
    ]


# Sanity check — COCO_KEYPOINT_NAMES 와 _make_default_keypoints_2d_full 의 17 keypoint 정합.
assert set(_make_default_keypoints_2d_full().keys()) == set(KEYPOINT_NAMES)
