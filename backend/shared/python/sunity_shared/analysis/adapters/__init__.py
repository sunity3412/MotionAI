"""스키마 변환 어댑터 (33→COCO-17, SMPL-X→COCO-17 등).

RESEARCH §Pattern 3 / Phase 1 D-04 / REVIEWS M-3 grip 확장.

현재 제공:
  - mediapipe_to_coco17: MediaPipe 33 landmark → COCO-17 + 폴 확장 (toe/heel/grip)
"""

from .mediapipe_to_coco17 import (
    convert_landmarks_to_coco17_and_pole_ext,
    MEDIAPIPE_33_TO_COCO17,
    POLE_EXTENSION_MAP,
    GRIP_LEFT_SOURCE_INDICES,
    GRIP_RIGHT_SOURCE_INDICES,
)

__all__ = [
    "convert_landmarks_to_coco17_and_pole_ext",
    "MEDIAPIPE_33_TO_COCO17",
    "POLE_EXTENSION_MAP",
    "GRIP_LEFT_SOURCE_INDICES",
    "GRIP_RIGHT_SOURCE_INDICES",
]
