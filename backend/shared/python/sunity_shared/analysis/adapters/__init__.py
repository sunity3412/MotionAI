"""스키마 변환 어댑터 (33→COCO-17, 133→COCO-17 등).

RESEARCH §Pattern 3 / Phase 1 D-04 / REVIEWS M-3 grip 확장.

현재 제공:
  - mediapipe_to_coco17: MediaPipe 33 landmark → COCO-17 + 폴 확장 (toe/heel/grip)
  - rtmw_133_to_coco17: RTMW 133 wholebody → COCO-17 + 폴 확장 + D-20 원본 보존 (Plan 01-21)

POLE_EXTENSION_MAP, GRIP_LEFT/RIGHT_SOURCE_INDICES 는 RTMW 어댑터 버전 기본 노출.
MediaPipe 버전은 MEDIAPIPE_ prefix 로 구분.
"""

from .mediapipe_to_coco17 import (
    convert_landmarks_to_coco17_and_pole_ext,
    MEDIAPIPE_33_TO_COCO17,
    POLE_EXTENSION_MAP as MEDIAPIPE_POLE_EXTENSION_MAP,
    GRIP_LEFT_SOURCE_INDICES as MEDIAPIPE_GRIP_LEFT_SOURCE_INDICES,
    GRIP_RIGHT_SOURCE_INDICES as MEDIAPIPE_GRIP_RIGHT_SOURCE_INDICES,
)
from .rtmw_133_to_coco17 import (
    convert_rtmw_keypoints_to_coco17_and_pole_ext,
    RTMW_133_TO_COCO17,
    POLE_EXTENSION_MAP,
    GRIP_LEFT_SOURCE_INDICES,
    GRIP_RIGHT_SOURCE_INDICES,
)

__all__ = [
    # MediaPipe 어댑터 (기존 경로 유지)
    "convert_landmarks_to_coco17_and_pole_ext",
    "MEDIAPIPE_33_TO_COCO17",
    "MEDIAPIPE_POLE_EXTENSION_MAP",
    "MEDIAPIPE_GRIP_LEFT_SOURCE_INDICES",
    "MEDIAPIPE_GRIP_RIGHT_SOURCE_INDICES",
    # RTMW 어댑터 (Plan 01-21 신설)
    "convert_rtmw_keypoints_to_coco17_and_pole_ext",
    "RTMW_133_TO_COCO17",
    "POLE_EXTENSION_MAP",
    "GRIP_LEFT_SOURCE_INDICES",
    "GRIP_RIGHT_SOURCE_INDICES",
]
