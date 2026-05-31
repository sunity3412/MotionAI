"""폴 축 자동 검출 + 좌표계 정렬.

Phase 1 D-09/D-10/D-11/D-12 + REVIEWS H-2 lazy import / M-2 confidence_level enum.
스피닝 폴은 v1.5 — Phase 1 범위 밖.

D-09: Hough Line Transform + 수직 prior 자동 검출.
D-10: 영상 전체 평균 축 1개 산출 (confidence 가중평균).
D-11: 검출 실패 시 수직 가정 + confidence_level='low'.
D-12: raw + pole-aligned 둘 다 PoseFrame 에 저장. PoleAxis 메타도 저장.
H-2: cv2/scipy module-level import 금지 — 클래스 __init__ 또는 첫 호출 시점에 lazy.
M-2: confidence_level = 'high'|'medium'|'low' enum (numeric 대체).
"""

from .detector import HoughPoleDetector
from .aligner import compute_alignment_matrix, apply_alignment

__all__ = [
    "HoughPoleDetector",
    "compute_alignment_matrix",
    "apply_alignment",
]
