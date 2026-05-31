"""pose_lifters — 2D keypoints → 3D lift 어댑터 패키지.

Plan 01-08: spike(backend/research/spikes/) 코드를 production grade 로 승격.

라이선스:
  MotionBERT (Walter0807/MotionBERT, Apache 2.0):
    https://github.com/Walter0807/MotionBERT/blob/main/LICENSE
    상업적 사용, 수정, 배포 모두 허용. 저작권 고지 필요.
    가중치 파일 (best_epoch.bin) 은 git 추적 금지 — Pod에 scp로만 배치.
    .gitignore 등록 완료: backend/shared/python/sunity_shared/analysis/pose_lifters/weights/

포함 모듈:
  motionbert_lifter.py  — MotionBertLifter: (T,17,2|3) → (T,17,3) 3D lift
  mediapipe_to_h36m17.py — MP33 → H3.6M 17-joint 매핑 + H3.6M → COCO-17 역변환
"""

from .mediapipe_to_h36m17 import (
    H36M_IDX,
    H36M_JOINT_NAMES,
    H36M_TO_COCO17_LIMB_PAIRS,
    NUM_H36M_JOINTS,
    convert_mp33_to_h36m17,
    h36m17_to_coco17_subset,
)
from .motionbert_lifter import MotionBertLifter

__all__ = [
    "MotionBertLifter",
    "convert_mp33_to_h36m17",
    "h36m17_to_coco17_subset",
    "H36M_IDX",
    "H36M_JOINT_NAMES",
    "H36M_TO_COCO17_LIMB_PAIRS",
    "NUM_H36M_JOINTS",
]
