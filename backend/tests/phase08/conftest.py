"""Phase 8 단위 테스트 공통 fixture — programmatic factory 박제 활용.

REVIEWS Cycle 1 R9 권고 정합 — JSON fixture 박제는 Plan 08-01 이 본 conftest 위에 박제.

기존 backend/tests/conftest.py 가 parents[1]/shared/python 을 sys.path 에 자동 주입
하므로 본 파일은 별도 path 주입 X.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .fixtures._factory import (
    make_body_profile,
    make_keypoint2d,
    make_keypoint3d,
    make_keypoint3d_aligned,
    make_pole_axis,
    make_pole_axis_measurement,
    make_pole_line_2d,
    make_pose_frame,
)

# Phase 8 fixture 디렉토리 — Plan 08-01 JSON 박제 시 활용.
PHASE08_FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def synthetic_pose_frames() -> list:
    """60 frame 합성 PoseFrame 리스트 — shoulder y=0.3, hip y=0.6 박제.

    image_2d + pole_aligned + world_3d 3 공간 모두 채움.
    median_torso_length 검증용 (image_2d 시 ~0.3, pole_aligned 시 동일).
    """
    frames = []
    for i in range(60):
        kp2d = {
            "left_shoulder": make_keypoint2d(0.45, 0.3),
            "right_shoulder": make_keypoint2d(0.55, 0.3),
            "left_hip": make_keypoint2d(0.46, 0.6),
            "right_hip": make_keypoint2d(0.54, 0.6),
        }
        kp3d_aligned = {
            "left_shoulder": make_keypoint3d_aligned(-0.1, 0.0, 0.0),
            "right_shoulder": make_keypoint3d_aligned(0.1, 0.0, 0.0),
            "left_hip": make_keypoint3d_aligned(-0.1, -0.3, 0.0),
            "right_hip": make_keypoint3d_aligned(0.1, -0.3, 0.0),
        }
        kp3d = {
            "left_shoulder": make_keypoint3d(-0.1, 1.5, 0.0, confidence=0.9),
            "right_shoulder": make_keypoint3d(0.1, 1.5, 0.0, confidence=0.9),
            "left_hip": make_keypoint3d(-0.1, 1.2, 0.0, confidence=0.9),
            "right_hip": make_keypoint3d(0.1, 1.2, 0.0, confidence=0.9),
        }
        frames.append(
            make_pose_frame(
                frame_index=i,
                timestamp_ms=i * 33,
                keypoints_2d=kp2d,
                keypoints_3d_pole_aligned=kp3d_aligned,
                keypoints_3d=kp3d,
                reliability="high",
            )
        )
    return frames


@pytest.fixture
def synthetic_body_profile():
    """BodyNormalizationProfile 7 필드 박제 — asymmetry 필드 없음 (REVIEWS H1)."""
    return make_body_profile()


@pytest.fixture
def synthetic_pole_axis_measurement():
    """PoleAxisMeasurement 박제 — vertical line + vertical axis."""
    line = make_pole_line_2d()
    axis = make_pole_axis()
    return make_pole_axis_measurement(line=line, axis_3d=axis)
