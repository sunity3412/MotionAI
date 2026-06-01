"""RTMPose COCO-17 → H3.6M 17-joint 매핑 어댑터 (Plan 01-10 spike).

Plan 01-09 에서 AlphaPose 라이선스가 Noncommercial Only 로 차단되어,
belle 결정 (2026-06-01) = Option B-1 (RTMPose, Apache 2.0) 채택.
RTMPose-l (MMPose, OpenMMLab) 의 COCO-17 키포인트 출력을 Plan 01-08 production
MotionBERT lifter (`pose_lifters/motionbert_lifter.py`) 가 기대하는 H3.6M 17-joint
정규화 입력 (T, 17, 2) 로 변환한다.

라이선스:
  MMPose / mmcv / mmengine / mmdet: Apache License 2.0
    https://github.com/open-mmlab/mmpose/blob/main/LICENSE
    https://github.com/open-mmlab/mmcv/blob/main/LICENSE
    https://github.com/open-mmlab/mmengine/blob/main/LICENSE
    https://github.com/open-mmlab/mmdetection/blob/main/LICENSE
  RTMPose-l checkpoint (download.openmmlab.com): MMPose 프로젝트의 Apache 2.0
    적용 (OpenMMLab 모델 zoo).
  본 어댑터: 운영 코드베이스 라이선스 (Sunity AI Coach) 와 동일.

COCO-17 keypoint index (RTMPose 표준 출력 — `mmpose/configs/_base_/datasets/coco.py`):
  0: nose          1: left_eye       2: right_eye
  3: left_ear      4: right_ear
  5: left_shoulder 6: right_shoulder
  7: left_elbow    8: right_elbow
  9: left_wrist   10: right_wrist
 11: left_hip     12: right_hip
 13: left_knee    14: right_knee
 15: left_ankle   16: right_ankle

H3.6M 17-joint 순서 (Plan 01-08 `pose_lifters/mediapipe_to_h36m17.py` 와 동일):
  0: hip (root)       1: r_hip          2: r_knee
  3: r_foot           4: l_hip          5: l_knee
  6: l_foot           7: spine          8: thorax
  9: neck_nose       10: head          11: l_shoulder
  12: l_elbow        13: l_wrist       14: r_shoulder
  15: r_elbow        16: r_wrist

매핑 전략 (12개 직접 + 5개 derive):
  직접 매핑 (12개):
    COCO 12 → H36M 1 (r_hip)
    COCO 14 → H36M 2 (r_knee)
    COCO 16 → H36M 3 (r_foot, right ankle)
    COCO 11 → H36M 4 (l_hip)
    COCO 13 → H36M 5 (l_knee)
    COCO 15 → H36M 6 (l_foot, left ankle)
    COCO  5 → H36M 11 (l_shoulder)
    COCO  7 → H36M 12 (l_elbow)
    COCO  9 → H36M 13 (l_wrist)
    COCO  6 → H36M 14 (r_shoulder)
    COCO  8 → H36M 15 (r_elbow)
    COCO 10 → H36M 16 (r_wrist)
  파생 (5개):
    H36M  0 hip       = mean(COCO 11 + COCO 12)
    H36M  8 thorax    = mean(COCO  5 + COCO  6)
    H36M  7 spine     = mean(H36M 0 + H36M 8)
    H36M  9 neck_nose = mean(H36M 8 + COCO 0 nose)
    H36M 10 head      = COCO 0 (nose proxy)

입력 좌표계:
  RTMPose 는 absolute pixel 좌표 (x, y) 와 keypoint별 score 를 출력한다.
  본 어댑터는 image (W, H) 로 [0, 1] 정규화한 출력을 반환해, Plan 01-08
  `pose_lifters/mediapipe_to_h36m17.py` 의 출력 형식 (normalized 0~1) 과
  맞춘다. MotionBERT 가 기대하는 입력은 이 정규화 좌표.

confidence 처리:
  RTMPose 의 keypoint score < `score_threshold` 인 키포인트는 NaN 으로 마킹.
  MotionBERT lift 단계 이전에 temporal_fill 보간이 NaN 을 메꾸도록 한다
  (Plan 01-07 spike 패턴 동일).

본 어댑터는 mmpose 의존 없이 순수 numpy 로 작성됨 — 단위 테스트 로컬 실행 가능.
"""

from __future__ import annotations

import numpy as np

# H3.6M 17-joint 이름 (인덱스 순서와 일치) — Plan 01-08 production 어댑터와 동일
H36M_JOINT_NAMES = (
    "hip",        # 0 — derive: mean(l_hip, r_hip)
    "r_hip",      # 1 — COCO 12
    "r_knee",     # 2 — COCO 14
    "r_foot",     # 3 — COCO 16 (right ankle)
    "l_hip",      # 4 — COCO 11
    "l_knee",     # 5 — COCO 13
    "l_foot",     # 6 — COCO 15 (left ankle)
    "spine",      # 7 — derive: mean(hip[H36M 0], thorax[H36M 8])
    "thorax",     # 8 — derive: mean(l_shoulder, r_shoulder)
    "neck_nose",  # 9 — derive: mean(thorax[H36M 8], nose)
    "head",       # 10 — COCO 0 (nose proxy)
    "l_shoulder",  # 11 — COCO 5
    "l_elbow",    # 12 — COCO 7
    "l_wrist",    # 13 — COCO 9
    "r_shoulder",  # 14 — COCO 6
    "r_elbow",    # 15 — COCO 8
    "r_wrist",    # 16 — COCO 10
)

NUM_H36M_JOINTS = len(H36M_JOINT_NAMES)  # 17

# H3.6M 인덱스 조회 편의
H36M_IDX = {name: i for i, name in enumerate(H36M_JOINT_NAMES)}

# COCO-17 인덱스 상수
_COCO_NOSE = 0
_COCO_L_SHOULDER = 5
_COCO_R_SHOULDER = 6
_COCO_L_ELBOW = 7
_COCO_R_ELBOW = 8
_COCO_L_WRIST = 9
_COCO_R_WRIST = 10
_COCO_L_HIP = 11
_COCO_R_HIP = 12
_COCO_L_KNEE = 13
_COCO_R_KNEE = 14
_COCO_L_ANKLE = 15
_COCO_R_ANKLE = 16

# H3.6M 인덱스 상수 (가독성)
_H36M_HIP = 0
_H36M_R_HIP = 1
_H36M_R_KNEE = 2
_H36M_R_FOOT = 3
_H36M_L_HIP = 4
_H36M_L_KNEE = 5
_H36M_L_FOOT = 6
_H36M_SPINE = 7
_H36M_THORAX = 8
_H36M_NECK_NOSE = 9
_H36M_HEAD = 10
_H36M_L_SHOULDER = 11
_H36M_L_ELBOW = 12
_H36M_L_WRIST = 13
_H36M_R_SHOULDER = 14
_H36M_R_ELBOW = 15
_H36M_R_WRIST = 16

# 기본 score threshold — RTMPose 출력 keypoint score < 0.3 이면 NaN 처리
DEFAULT_SCORE_THRESHOLD: float = 0.3


def convert_rtmpose_coco17_to_h36m17(
    rtmpose_kp: np.ndarray,
    image_size: tuple[int, int] | None = None,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    use_score_as_conf: bool = False,
) -> np.ndarray:
    """RTMPose COCO-17 출력 → H3.6M 17-joint 정규화 좌표.

    Args:
        rtmpose_kp: shape (T, 17, 3) — RTMPose 출력 (x_pixel, y_pixel, score).
                    또는 (T, 17, 2) — score 없는 경우 (모든 keypoint 신뢰).
                    또는 (17, 2) | (17, 3) — 단일 프레임 (T=1 로 확장).
        image_size: (width, height) — 입력 영상 픽셀 크기. None 이면 좌표를
                    정규화하지 않고 그대로 사용 (이미 정규화된 입력 가정).
                    Pod 실행 시 image_size 명시 권장.
        score_threshold: RTMPose keypoint score 가 이 값 미만이면 해당 좌표를
                         NaN 처리 (downstream temporal_fill 이 보간).
        use_score_as_conf: True 면 출력에 세 번째 채널 (confidence) 추가 →
                           (T, 17, 3). False 면 (T, 17, 2).
                           파생 joint 의 confidence 는 구성 joint 의 최솟값.

    Returns:
        shape (T, 17, 2) 또는 (T, 17, 3) — H3.6M 17-joint 정규화 좌표.
        파생 joint (hip, spine, thorax, neck_nose) 는 구성 joint 좌표 평균.
        구성 joint 가 NaN 인 경우 파생 joint 도 NaN 으로 전파됨.

    Raises:
        ValueError: 입력 형상이 COCO-17 기준 (17 keypoints) 에 맞지 않을 때.
    """
    kp = np.asarray(rtmpose_kp, dtype=float)

    # 단일 프레임 → 배치 형태로 확장
    if kp.ndim == 2:
        kp = kp[np.newaxis, ...]  # (1, 17, C)

    if kp.ndim != 3 or kp.shape[1] != 17 or kp.shape[2] < 2:
        raise ValueError(
            "rtmpose_kp 형상은 (T, 17, 2|3) 또는 (17, 2|3) 이어야 합니다. "
            f"받은 형상: {kp.shape}"
        )

    T = kp.shape[0]
    has_score = kp.shape[2] >= 3
    C_out = 3 if use_score_as_conf else 2

    # score threshold NaN 처리 — 원본 입력의 사본을 만들어서 수정
    kp_proc = kp.copy()
    if has_score:
        low_score_mask = kp_proc[:, :, 2] < score_threshold  # (T, 17)
        # 저신뢰 keypoint 의 x, y 를 NaN 처리 (downstream temporal_fill 이 보간)
        for c in range(2):
            kp_proc[:, :, c] = np.where(low_score_mask, np.nan, kp_proc[:, :, c])

    # image_size 정규화 — pixel 좌표를 [0, 1] 로 변환
    if image_size is not None:
        width, height = image_size
        if width <= 0 or height <= 0:
            raise ValueError(
                f"image_size 의 width/height 는 양수여야 합니다: {image_size}"
            )
        kp_proc[:, :, 0] = kp_proc[:, :, 0] / float(width)
        kp_proc[:, :, 1] = kp_proc[:, :, 1] / float(height)

    out = np.full((T, NUM_H36M_JOINTS, C_out), np.nan, dtype=float)

    # -- 직접 대응 (COCO idx → H36M idx) --
    direct_map = [
        (_COCO_R_HIP,      _H36M_R_HIP),
        (_COCO_R_KNEE,     _H36M_R_KNEE),
        (_COCO_R_ANKLE,    _H36M_R_FOOT),
        (_COCO_L_HIP,      _H36M_L_HIP),
        (_COCO_L_KNEE,     _H36M_L_KNEE),
        (_COCO_L_ANKLE,    _H36M_L_FOOT),
        (_COCO_NOSE,       _H36M_HEAD),
        (_COCO_L_SHOULDER, _H36M_L_SHOULDER),
        (_COCO_L_ELBOW,    _H36M_L_ELBOW),
        (_COCO_L_WRIST,    _H36M_L_WRIST),
        (_COCO_R_SHOULDER, _H36M_R_SHOULDER),
        (_COCO_R_ELBOW,    _H36M_R_ELBOW),
        (_COCO_R_WRIST,    _H36M_R_WRIST),
    ]

    for coco_idx, h36m_idx in direct_map:
        out[:, h36m_idx, 0] = kp_proc[:, coco_idx, 0]  # x
        out[:, h36m_idx, 1] = kp_proc[:, coco_idx, 1]  # y
        if use_score_as_conf and has_score:
            out[:, h36m_idx, 2] = kp_proc[:, coco_idx, 2]  # raw score

    # -- 파생 joint --
    # H36M 8: thorax = mean(L/R shoulder)
    l_sh_xy = kp_proc[:, _COCO_L_SHOULDER, :2]
    r_sh_xy = kp_proc[:, _COCO_R_SHOULDER, :2]
    thorax_xy = (l_sh_xy + r_sh_xy) / 2.0
    out[:, _H36M_THORAX, 0] = thorax_xy[:, 0]
    out[:, _H36M_THORAX, 1] = thorax_xy[:, 1]
    if use_score_as_conf and has_score:
        out[:, _H36M_THORAX, 2] = np.minimum(
            kp_proc[:, _COCO_L_SHOULDER, 2], kp_proc[:, _COCO_R_SHOULDER, 2]
        )

    # H36M 0: hip = mean(L/R hip)
    l_hip_xy = kp_proc[:, _COCO_L_HIP, :2]
    r_hip_xy = kp_proc[:, _COCO_R_HIP, :2]
    hip_xy = (l_hip_xy + r_hip_xy) / 2.0
    out[:, _H36M_HIP, 0] = hip_xy[:, 0]
    out[:, _H36M_HIP, 1] = hip_xy[:, 1]
    if use_score_as_conf and has_score:
        out[:, _H36M_HIP, 2] = np.minimum(
            kp_proc[:, _COCO_L_HIP, 2], kp_proc[:, _COCO_R_HIP, 2]
        )

    # H36M 7: spine = mean(hip[H36M 0], thorax[H36M 8])
    spine_xy = (out[:, _H36M_HIP, :2] + out[:, _H36M_THORAX, :2]) / 2.0
    out[:, _H36M_SPINE, 0] = spine_xy[:, 0]
    out[:, _H36M_SPINE, 1] = spine_xy[:, 1]
    if use_score_as_conf and has_score:
        out[:, _H36M_SPINE, 2] = np.minimum(
            out[:, _H36M_HIP, 2], out[:, _H36M_THORAX, 2]
        )

    # H36M 9: neck_nose = mean(thorax[H36M 8], nose[COCO 0])
    nose_xy = kp_proc[:, _COCO_NOSE, :2]
    neck_nose_xy = (out[:, _H36M_THORAX, :2] + nose_xy) / 2.0
    out[:, _H36M_NECK_NOSE, 0] = neck_nose_xy[:, 0]
    out[:, _H36M_NECK_NOSE, 1] = neck_nose_xy[:, 1]
    if use_score_as_conf and has_score:
        out[:, _H36M_NECK_NOSE, 2] = np.minimum(
            out[:, _H36M_THORAX, 2], kp_proc[:, _COCO_NOSE, 2]
        )

    return out
