"""MediaPipe 33-landmark → H3.6M 17-joint 매핑 어댑터.

Plan 01-08 production 승격: backend/research/spikes/mediapipe_to_h36m17.py 에서 이전.
운영 코드 import 없음 — 순수 numpy.

H3.6M 17-joint 순서 (MotionBERT/H36M 표준 컨벤션):
  0: Hip           (root — L/R hip 중점)
  1: RHip          (right hip)
  2: RKnee         (right knee)
  3: RFoot         (right ankle)
  4: LHip          (left hip)
  5: LKnee         (left knee)
  6: LFoot         (left ankle)
  7: Spine         (Hip~Thorax 중점)
  8: Thorax        (L/R shoulder 중점)
  9: NeckNose      (Thorax~Nose 중점)
  10: Head         (nose proxy)
  11: LShoulder    (left shoulder)
  12: LElbow       (left elbow)
  13: LWrist       (left wrist)
  14: RShoulder    (right shoulder)
  15: RElbow       (right elbow)
  16: RWrist       (right wrist)

MediaPipe 33-landmark 인덱스 (pose_landmarker 표준):
  0: nose         11: l_shoulder    23: l_hip
  1: l_eye_inner  12: r_shoulder    24: r_hip
  2: l_eye        13: l_elbow       25: l_knee
  3: l_eye_outer  14: r_elbow       26: r_knee
  4: r_eye_inner  15: l_wrist       27: l_ankle
  5: r_eye        16: r_wrist       28: r_ankle
  6: r_eye_outer  ...               ...
  7: l_ear        17: l_pinky
  8: r_ear        ...
  9: mouth_left   21: l_index
  10: mouth_right 22: r_index

입력 형식: normalized_landmarks (이미지 좌표, x∈[0,1], y∈[0,1]).
  이유: world_landmarks의 z 추정이 인버트/측면/폴 폐색 자세에서 노이즈가 크기 때문에
  2D 정보만 사용하고 z는 MotionBERT가 별도 학습된 가중치로 재구성한다.
  (Plan 01-06 발견 — D-16 보류 근거).

출력 형식: (T, 17, 2) — x, y 정규화 좌표.
  MotionBERT는 (T, 17, 2|3) 입력을 받는다. confidence가 있으면 (T, 17, 3)도 허용.
"""

from __future__ import annotations

import numpy as np

# H3.6M 17-joint 이름 (인덱스 순서와 일치)
H36M_JOINT_NAMES = (
    "hip",        # 0 — derived: mean(l_hip, r_hip)
    "r_hip",      # 1 — MP 24
    "r_knee",     # 2 — MP 26
    "r_foot",     # 3 — MP 28 (right ankle)
    "l_hip",      # 4 — MP 23
    "l_knee",     # 5 — MP 25
    "l_foot",     # 6 — MP 27 (left ankle)
    "spine",      # 7 — derived: mean(hip[H36M 0], thorax[H36M 8])
    "thorax",     # 8 — derived: mean(l_shoulder, r_shoulder)
    "neck_nose",  # 9 — derived: mean(thorax[H36M 8], nose)
    "head",       # 10 — MP 0 (nose proxy)
    "l_shoulder", # 11 — MP 11
    "l_elbow",    # 12 — MP 13
    "l_wrist",    # 13 — MP 15
    "r_shoulder", # 14 — MP 12
    "r_elbow",    # 15 — MP 14
    "r_wrist",    # 16 — MP 16
)

NUM_H36M_JOINTS = len(H36M_JOINT_NAMES)  # 17

# H3.6M 인덱스 조회 편의
H36M_IDX = {name: i for i, name in enumerate(H36M_JOINT_NAMES)}

# MediaPipe 33-landmark 인덱스 상수 (이름 → 인덱스 직접 매핑)
_MP_NOSE = 0
_MP_L_SHOULDER = 11
_MP_R_SHOULDER = 12
_MP_L_ELBOW = 13
_MP_R_ELBOW = 14
_MP_L_WRIST = 15
_MP_R_WRIST = 16
_MP_L_HIP = 23
_MP_R_HIP = 24
_MP_L_KNEE = 25
_MP_R_KNEE = 26
_MP_L_ANKLE = 27
_MP_R_ANKLE = 28

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

# COCO-17 → H3.6M 12개 직접 대응 관절 (스코어링 체인이 필요한 limb joints)
# (COCO-17 인덱스, H3.6M 인덱스) 쌍
#   skeleton.py KEYPOINT_NAMES 기준 COCO-17 인덱스:
#   5: left_shoulder   6: right_shoulder
#   7: left_elbow      8: right_elbow
#   9: left_wrist     10: right_wrist
#  11: left_hip       12: right_hip
#  13: left_knee      14: right_knee
#  15: left_ankle     16: right_ankle
H36M_TO_COCO17_LIMB_PAIRS: tuple[tuple[int, int], ...] = (
    (_H36M_L_SHOULDER, 5),   # LShoulder → left_shoulder
    (_H36M_R_SHOULDER, 6),   # RShoulder → right_shoulder
    (_H36M_L_ELBOW, 7),      # LElbow    → left_elbow
    (_H36M_R_ELBOW, 8),      # RElbow    → right_elbow
    (_H36M_L_WRIST, 9),      # LWrist    → left_wrist
    (_H36M_R_WRIST, 10),     # RWrist    → right_wrist
    (_H36M_L_HIP, 11),       # LHip      → left_hip
    (_H36M_R_HIP, 12),       # RHip      → right_hip
    (_H36M_L_KNEE, 13),      # LKnee     → left_knee
    (_H36M_R_KNEE, 14),      # RKnee     → right_knee
    (_H36M_L_FOOT, 15),      # LFoot     → left_ankle
    (_H36M_R_FOOT, 16),      # RFoot     → right_ankle
)


def convert_mp33_to_h36m17(
    mp_landmarks: np.ndarray,
    use_visibility_as_conf: bool = False,
) -> np.ndarray:
    """MediaPipe 33 normalized landmarks → H3.6M 17-joint 좌표 배열.

    Args:
        mp_landmarks: shape (T, 33, 2) — x, y normalized [0,1] 이미지 좌표.
                      또는 (T, 33, 3) — x, y, visibility (세 번째 채널이 있을 때).
                      또는 (33, 2) | (33, 3) — 단일 프레임 (T=1로 확장).
        use_visibility_as_conf: True면 출력에 세 번째 채널(confidence)을 추가해
                                (T, 17, 3) 반환. 없으면 (T, 17, 2) 반환.

    Returns:
        shape (T, 17, 2) 또는 (T, 17, 3) — H3.6M 17-joint (x, y[, confidence]).
        파생 관절(hip, spine, thorax, neck_nose)의 confidence는 구성 관절 최솟값.
        NaN은 구성 관절이 NaN인 경우 그대로 전파.

    Raises:
        ValueError: 입력 형상이 33-landmark 기준에 맞지 않을 때.
    """
    lm = np.asarray(mp_landmarks, dtype=float)

    # 단일 프레임 → 배치 형태로 확장
    if lm.ndim == 2:
        lm = lm[np.newaxis, ...]  # (1, 33, C)

    if lm.ndim != 3 or lm.shape[1] != 33 or lm.shape[2] < 2:
        raise ValueError(
            f"mp_landmarks 형상은 (T, 33, 2|3) 또는 (33, 2|3) 이어야 합니다. "
            f"받은 형상: {lm.shape}"
        )

    T = lm.shape[0]
    has_conf = lm.shape[2] >= 3
    C_out = 3 if use_visibility_as_conf else 2

    out = np.full((T, NUM_H36M_JOINTS, C_out), np.nan, dtype=float)

    # -- 직접 대응 (MP 인덱스 → H36M 인덱스) --
    direct_map = [
        (_MP_R_HIP,      _H36M_R_HIP),
        (_MP_R_KNEE,     _H36M_R_KNEE),
        (_MP_R_ANKLE,    _H36M_R_FOOT),
        (_MP_L_HIP,      _H36M_L_HIP),
        (_MP_L_KNEE,     _H36M_L_KNEE),
        (_MP_L_ANKLE,    _H36M_L_FOOT),
        (_MP_NOSE,       _H36M_HEAD),
        (_MP_L_SHOULDER, _H36M_L_SHOULDER),
        (_MP_L_ELBOW,    _H36M_L_ELBOW),
        (_MP_L_WRIST,    _H36M_L_WRIST),
        (_MP_R_SHOULDER, _H36M_R_SHOULDER),
        (_MP_R_ELBOW,    _H36M_R_ELBOW),
        (_MP_R_WRIST,    _H36M_R_WRIST),
    ]

    for mp_idx, h36m_idx in direct_map:
        out[:, h36m_idx, 0] = lm[:, mp_idx, 0]  # x
        out[:, h36m_idx, 1] = lm[:, mp_idx, 1]  # y
        if use_visibility_as_conf and has_conf:
            out[:, h36m_idx, 2] = lm[:, mp_idx, 2]  # visibility

    # -- 파생 관절 --
    # H36M 8: Thorax = mean(L/R shoulder)
    l_sh = lm[:, _MP_L_SHOULDER, :2]
    r_sh = lm[:, _MP_R_SHOULDER, :2]
    thorax_xy = (l_sh + r_sh) / 2.0
    out[:, _H36M_THORAX, 0] = thorax_xy[:, 0]
    out[:, _H36M_THORAX, 1] = thorax_xy[:, 1]
    if use_visibility_as_conf and has_conf:
        out[:, _H36M_THORAX, 2] = np.minimum(
            lm[:, _MP_L_SHOULDER, 2], lm[:, _MP_R_SHOULDER, 2]
        )

    # H36M 0: Hip = mean(L/R hip)
    l_hip = lm[:, _MP_L_HIP, :2]
    r_hip = lm[:, _MP_R_HIP, :2]
    hip_xy = (l_hip + r_hip) / 2.0
    out[:, _H36M_HIP, 0] = hip_xy[:, 0]
    out[:, _H36M_HIP, 1] = hip_xy[:, 1]
    if use_visibility_as_conf and has_conf:
        out[:, _H36M_HIP, 2] = np.minimum(
            lm[:, _MP_L_HIP, 2], lm[:, _MP_R_HIP, 2]
        )

    # H36M 7: Spine = mean(Hip[H36M 0], Thorax[H36M 8])
    spine_xy = (out[:, _H36M_HIP, :2] + out[:, _H36M_THORAX, :2]) / 2.0
    out[:, _H36M_SPINE, 0] = spine_xy[:, 0]
    out[:, _H36M_SPINE, 1] = spine_xy[:, 1]
    if use_visibility_as_conf:
        if has_conf:
            out[:, _H36M_SPINE, 2] = np.minimum(
                out[:, _H36M_HIP, 2], out[:, _H36M_THORAX, 2]
            )

    # H36M 9: NeckNose = mean(Thorax[H36M 8], Nose[MP 0])
    nose_xy = lm[:, _MP_NOSE, :2]
    neck_nose_xy = (out[:, _H36M_THORAX, :2] + nose_xy) / 2.0
    out[:, _H36M_NECK_NOSE, 0] = neck_nose_xy[:, 0]
    out[:, _H36M_NECK_NOSE, 1] = neck_nose_xy[:, 1]
    if use_visibility_as_conf and has_conf:
        out[:, _H36M_NECK_NOSE, 2] = np.minimum(
            out[:, _H36M_THORAX, 2], lm[:, _MP_NOSE, 2]
        )

    return out


def h36m17_to_coco17_subset(
    h36m_xyz: np.ndarray,
) -> np.ndarray:
    """H3.6M 17-joint (T, 17, 3=xyz) → COCO-17 (T, 17, 4=xyz+conf) 부분 매핑.

    12개 limb joint만 대응. face keypoints(nose, eyes, ears)는 NaN으로 채운다.
    features.py compute_joint_angles는 limb joints(어깨/팔꿈치/손목/고관절/무릎/발목)만
    사용하므로 face NaN은 점수 계산에 영향 없다 (skeleton.py JOINT_ANGLES 참조).

    Args:
        h36m_xyz: shape (T, 17, 3) — MotionBERT 출력 (x, y, z metric 좌표).

    Returns:
        shape (T, 17, 4) — COCO-17 순서 (x, y, z, uncertainty_proxy).
        limb joints: uncertainty_proxy = 0.0 (신뢰).
        face joints: NaN + uncertainty_proxy = 1.0 (미감지).

    COCO-17 인덱스 (skeleton.py KEYPOINT_NAMES):
      0: nose   1: l_eye   2: r_eye   3: l_ear   4: r_ear
      5: l_shoulder  6: r_shoulder  7: l_elbow  8: r_elbow
      9: l_wrist  10: r_wrist  11: l_hip  12: r_hip
      13: l_knee  14: r_knee  15: l_ankle  16: r_ankle
    """
    xyz = np.asarray(h36m_xyz, dtype=float)
    if xyz.ndim != 3 or xyz.shape[1] != 17 or xyz.shape[2] < 3:
        raise ValueError(
            f"h36m_xyz 형상은 (T, 17, 3) 이어야 합니다. 받은 형상: {xyz.shape}"
        )

    T = xyz.shape[0]
    # COCO-17, 4채널 (x, y, z, uncertainty_proxy), NaN+1.0으로 초기화
    out = np.full((T, 17, 4), np.nan, dtype=float)
    out[:, :, 3] = 1.0  # uncertainty_proxy default 1.0 (미감지)

    for h36m_idx, coco_idx in H36M_TO_COCO17_LIMB_PAIRS:
        out[:, coco_idx, 0] = xyz[:, h36m_idx, 0]  # x
        out[:, coco_idx, 1] = xyz[:, h36m_idx, 1]  # y
        out[:, coco_idx, 2] = xyz[:, h36m_idx, 2]  # z
        out[:, coco_idx, 3] = 0.0  # uncertainty_proxy = 0 (MotionBERT 출력 신뢰)

    return out
