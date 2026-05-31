"""MediaPipe PoseLandmarker mock result.

detect_for_video 호출 mock — 로컬 macOS (mediapipe wheel 부재) 에서도
어댑터 단위 테스트 가능. MediaPipe library API 형태를 duck-type 으로 모사.

주의: mock landmark 의 visibility / presence 필드 이름은 MediaPipe API 원본 형태.
  어댑터 변환 단계에서 raw_visibility / raw_presence 로 정정 매핑된다 (M-1 D-05).
  따라서 이 fixture 는 library API 형태를 유지한다.

노출 함수:
  make_mock_world_landmarks_33  : 33 개 mock world landmark (visible_indices 제어 가능)
  make_mock_image_landmarks_33  : 33 개 mock image landmark (normalized 0~1)
  make_mock_detection_result    : MediaPipe DetectionResult duck-type
  make_mock_no_human_result     : NoHumanError 트리거 케이스 (pose_landmarks=[])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class _MockLandmark:
    """MediaPipe Landmark duck-type (world / image landmark 공용).

    필드 이름은 MediaPipe API 원본 (visibility / presence).
    어댑터가 raw_visibility / raw_presence 로 변환한다.
    """

    x: float
    y: float
    z: float
    visibility: float
    presence: float


class _MockDetectionResult:
    """MediaPipe PoseLandmarkerResult duck-type."""

    def __init__(
        self,
        pose_world_landmarks: list,
        pose_landmarks: list,
    ) -> None:
        # mediapipe 는 pose_world_landmarks[frame_idx][landmark_idx] 구조
        self.pose_world_landmarks = pose_world_landmarks
        self.pose_landmarks = pose_landmarks


def make_mock_world_landmarks_33(
    visible_indices: Sequence[int] | None = None,
    default_visibility: float = 0.9,
    default_presence: float = 0.9,
) -> list[_MockLandmark]:
    """MediaPipe 33-landmark world landmark 목록 mock.

    visible_indices: 고가시성 landmark 인덱스. 그 외는 visibility=0.1, presence=0.1.
    None 이면 모든 landmark 가 default_visibility / default_presence.
    반환: 33 개 _MockLandmark (MediaPipe API world landmark 형태).
    """
    landmarks = []
    for i in range(33):
        if visible_indices is None or i in visible_indices:
            vis = default_visibility
            pres = default_presence
        else:
            vis = 0.1
            pres = 0.1
        # 간단한 위치값 — 테스트에서 실제 좌표 정확도는 무관
        x = (i % 5) * 0.1
        y = (i // 5) * 0.1
        z = 0.0
        landmarks.append(_MockLandmark(x=x, y=y, z=z, visibility=vis, presence=pres))
    return landmarks


def make_mock_image_landmarks_33(
    default_visibility: float = 0.9,
) -> list[_MockLandmark]:
    """MediaPipe 33-landmark image landmark 목록 mock (normalized 0~1 좌표).

    image landmark 는 presence API 별도 미제공이므로 presence = default_visibility.
    반환: 33 개 _MockLandmark (x, y normalized 0~1, z=0).
    """
    landmarks = []
    for i in range(33):
        x = ((i % 5) * 0.1 + 0.1) % 1.0
        y = ((i // 5) * 0.1 + 0.1) % 1.0
        landmarks.append(
            _MockLandmark(
                x=x,
                y=y,
                z=0.0,
                visibility=default_visibility,
                presence=default_visibility,
            )
        )
    return landmarks


def make_mock_detection_result(
    world_landmarks_33: list | None = None,
    image_landmarks_33: list | None = None,
) -> _MockDetectionResult:
    """MediaPipe PoseLandmarkerResult duck-type 객체 생성.

    world_landmarks_33: None 이면 make_mock_world_landmarks_33() 기본값 사용.
    image_landmarks_33: None 이면 make_mock_image_landmarks_33() 기본값 사용.

    반환: pose_world_landmarks=[[...33...]], pose_landmarks=[[...33...]] 형태.
    (MediaPipe Tasks API 는 프레임당 landmark 를 리스트로 감쌈)
    """
    if world_landmarks_33 is None:
        world_landmarks_33 = make_mock_world_landmarks_33()
    if image_landmarks_33 is None:
        image_landmarks_33 = make_mock_image_landmarks_33()
    return _MockDetectionResult(
        pose_world_landmarks=[world_landmarks_33],
        pose_landmarks=[image_landmarks_33],
    )


def make_mock_no_human_result() -> _MockDetectionResult:
    """사람을 찾지 못한 결과 mock. NoHumanError 트리거 케이스.

    pose_landmarks=[], pose_world_landmarks=[] — 어댑터가 NoHumanError 를 발생시켜야 함.
    """
    return _MockDetectionResult(
        pose_world_landmarks=[],
        pose_landmarks=[],
    )
