"""MediaPipe 33 landmark → COCO-17 + 폴 확장 (toe/heel/grip) 변환.

Phase 1 D-04 + REVIEWS M-3 (grip derived landmark) 박제.

A1: 33→COCO-17 매핑 공식 — belle 확정 보류.
    RESEARCH §Pattern 3 매핑 표 기반 (명칭 추론). Plan 06 회귀 검증(정은지 5영상)에서 갱신.
A2: grip derived 인덱스 (wrist+pinky+thumb 평균) — belle 확정 보류.
    Plan 06 회귀 검증 후 최적 조합으로 갱신.

REVIEWS 박제:
  M-1: MediaPipe visibility → raw_visibility, presence → raw_presence 변환
  M-3: pole_grip_left / pole_grip_right derived landmark 추가
  H-3: pole_axis 인자를 PoseFrame.pole_axis에 그대로 보존
  H-4: frame-level reliability = compute_frame_reliability(mean_visibility)

참조: RESEARCH §Pattern 3, D-04, D-05, D-12, §Code Example 1.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..pose_frame import (
    PoseFrame,
    Landmark3D,
    Keypoint3D,
    Keypoint3DAligned,
    Keypoint2D,
    PoseExtensionLandmark,
    PoleAxis,
    compute_frame_reliability,
)
from ..skeleton import KEYPOINT_NAMES


# ── MediaPipe 33 landmark 명칭 ────────────────────────────────────────────
#
# RESEARCH §Pattern 3 + ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
# A1 belle 확정 권장: 공식 문서 명칭 기반 순서 (인덱스 0~32).
#
MEDIAPIPE_33_LANDMARK_NAMES: tuple[str, ...] = (
    "nose",               # 0
    "left_eye_inner",     # 1
    "left_eye",           # 2
    "left_eye_outer",     # 3
    "right_eye_inner",    # 4
    "right_eye",          # 5
    "right_eye_outer",    # 6
    "left_ear",           # 7
    "right_ear",          # 8
    "mouth_left",         # 9
    "mouth_right",        # 10
    "left_shoulder",      # 11
    "right_shoulder",     # 12
    "left_elbow",         # 13
    "right_elbow",        # 14
    "left_wrist",         # 15
    "right_wrist",        # 16
    "left_pinky",         # 17
    "right_pinky",        # 18
    "left_index",         # 19
    "right_index",        # 20
    "left_thumb",         # 21
    "right_thumb",        # 22
    "left_hip",           # 23
    "right_hip",          # 24
    "left_knee",          # 25
    "right_knee",         # 26
    "left_ankle",         # 27
    "right_ankle",        # 28
    "left_heel",          # 29
    "right_heel",         # 30
    "left_foot_index",    # 31
    "right_foot_index",   # 32
)
assert len(MEDIAPIPE_33_LANDMARK_NAMES) == 33, "반드시 33개여야 함"


# ── COCO-17 매핑 ──────────────────────────────────────────────────────────
#
# MediaPipe 33 → skeleton.KEYPOINT_NAMES(COCO-17) 매핑.
# A1 belle 확정 보류: 명칭 기반 추론 — Plan 06 회귀 검증(정은지 5영상) 후 갱신.
# [CITED: developers.google.com/mediapipe — BlazePose landmark list]
#
MEDIAPIPE_33_TO_COCO17: dict[str, int] = {
    "nose":           0,   # MP 0  nose
    "left_eye":       2,   # MP 2  left eye (center)
    "right_eye":      5,   # MP 5  right eye (center)
    "left_ear":       7,   # MP 7  left ear
    "right_ear":      8,   # MP 8  right ear
    "left_shoulder":  11,  # MP 11 left shoulder
    "right_shoulder": 12,  # MP 12 right shoulder
    "left_elbow":     13,  # MP 13 left elbow
    "right_elbow":    14,  # MP 14 right elbow
    "left_wrist":     15,  # MP 15 left wrist
    "right_wrist":    16,  # MP 16 right wrist
    "left_hip":       23,  # MP 23 left hip
    "right_hip":      24,  # MP 24 right hip
    "left_knee":      25,  # MP 25 left knee
    "right_knee":     26,  # MP 26 right knee
    "left_ankle":     27,  # MP 27 left ankle
    "right_ankle":    28,  # MP 28 right ankle
}
assert len(MEDIAPIPE_33_TO_COCO17) == 17


# ── 폴 확장 grip source 인덱스 ──────────────────────────────────────────
#
# A2 belle confirm grip derivation — 정확한 source 인덱스는 추후 갱신.
# 현재: wrist(15/16) + pinky(17/18) + thumb(21/22) 평균 (M-3 D-04).
#
GRIP_LEFT_SOURCE_INDICES: tuple[int, ...] = (15, 17, 21)   # left_wrist, left_pinky, left_thumb
GRIP_RIGHT_SOURCE_INDICES: tuple[int, ...] = (16, 18, 22)  # right_wrist, right_pinky, right_thumb


# ── 폴 확장 landmark 맵 ──────────────────────────────────────────────────
#
# REVIEWS M-3: pole_grip_left / pole_grip_right 추가.
# D-04: toe/heel/grip 확장.
# int 값: raw MediaPipe 인덱스 직접 추출.
# tuple 값: derived — source 인덱스들의 좌표 평균.
# TODO belle confirm grip derivation — A2 항목, 정확한 source 인덱스는 추후 갱신.
#
POLE_EXTENSION_MAP: dict[str, int | tuple[int, ...]] = {
    "left_heel":        29,                     # raw MP 29
    "right_heel":       30,                     # raw MP 30
    "left_foot_index":  31,                     # raw MP 31 (toe)
    "right_foot_index": 32,                     # raw MP 32 (toe)
    "pole_grip_left":   GRIP_LEFT_SOURCE_INDICES,   # derived
    "pole_grip_right":  GRIP_RIGHT_SOURCE_INDICES,  # derived
}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────


def _landmark_to_dict(lm: Any) -> Landmark3D:
    """MediaPipe NormalizedLandmark/Landmark duck-typed 객체 → Landmark3D.

    M-1 D-05 박제:
      MediaPipe API 필드명: visibility, presence
      PoseFrame Landmark3D 필드명: raw_visibility, raw_presence
      본 어댑터에서 정확히 변환 — 어디서도 bare visibility/presence 명칭 사용 금지.

    presence 부재 시 raw_presence = visibility로 폴백 (D-05).
    """
    x: float = float(lm.x)
    y: float = float(lm.y)
    z: float = float(lm.z)
    # M-1: MediaPipe API.visibility → raw_visibility (명칭 변환 지점)
    raw_visibility: float = float(getattr(lm, "visibility", 0.0))
    # M-1: MediaPipe API.presence → raw_presence (명칭 변환 지점)
    # presence 없는 경우(image landmark 등) visibility로 폴백 (D-05)
    raw_presence_attr = getattr(lm, "presence", None)
    raw_presence: float = float(raw_presence_attr) if raw_presence_attr is not None else raw_visibility
    return Landmark3D(
        x=x,
        y=y,
        z=z,
        raw_visibility=raw_visibility,
        raw_presence=raw_presence,
    )


def _build_keypoint3d(lm: Any) -> Keypoint3D:
    """MediaPipe landmark duck-typed 객체 → Keypoint3D.

    D-05: confidence = raw_visibility × raw_presence.
    uncertainty_proxy = 1 - confidence.
    PoseFrame.compute_confidence 사용.
    """
    raw_visibility = float(getattr(lm, "visibility", 0.0))
    raw_presence_attr = getattr(lm, "presence", None)
    raw_presence: float | None = float(raw_presence_attr) if raw_presence_attr is not None else None
    confidence, uncertainty_proxy = PoseFrame.compute_confidence(raw_visibility, raw_presence)
    return Keypoint3D(
        x=float(lm.x),
        y=float(lm.y),
        z=float(lm.z),
        confidence=confidence,
        uncertainty_proxy=uncertainty_proxy,
    )


def _build_pole_extension_raw(lm: Any) -> PoseExtensionLandmark:
    """raw MediaPipe 인덱스에서 직접 PoseExtensionLandmark 생성."""
    raw_visibility = float(getattr(lm, "visibility", 0.0))
    raw_presence_attr = getattr(lm, "presence", None)
    raw_presence: float | None = float(raw_presence_attr) if raw_presence_attr is not None else None
    confidence, _ = PoseFrame.compute_confidence(raw_visibility, raw_presence)
    return PoseExtensionLandmark(
        x=float(lm.x),
        y=float(lm.y),
        z=float(lm.z),
        confidence=confidence,
    )


def _build_pole_grip(
    landmarks: list,
    source_indices: tuple[int, ...],
) -> PoseExtensionLandmark:
    """source 인덱스 좌표 평균으로 grip derived landmark 생성.

    A2 belle confirm grip derivation — 현재 wrist+pinky+thumb 평균.
    confidence = source confidence들의 평균.
    """
    xs = [float(landmarks[i].x) for i in source_indices]
    ys = [float(landmarks[i].y) for i in source_indices]
    zs = [float(landmarks[i].z) for i in source_indices]
    n = len(source_indices)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    mean_z = sum(zs) / n

    # confidence: source landmark confidence 평균
    confidences = []
    for i in source_indices:
        lm = landmarks[i]
        raw_vis = float(getattr(lm, "visibility", 0.0))
        raw_pres_attr = getattr(lm, "presence", None)
        raw_pres: float | None = float(raw_pres_attr) if raw_pres_attr is not None else None
        conf, _ = PoseFrame.compute_confidence(raw_vis, raw_pres)
        confidences.append(conf)
    mean_confidence = sum(confidences) / len(confidences)

    return PoseExtensionLandmark(
        x=mean_x,
        y=mean_y,
        z=mean_z,
        confidence=mean_confidence,
    )


def _compute_mean_visibility(world_landmarks: list) -> float:
    """33 landmark raw_visibility 평균 산출.

    H-4: frame-level reliability 산출에 사용.
    MediaPipe API.visibility → raw_visibility 명칭이므로 getattr(lm, 'visibility') 사용.
    """
    if not world_landmarks:
        return 0.0
    total = sum(float(getattr(lm, "visibility", 0.0)) for lm in world_landmarks)
    return total / len(world_landmarks)


# ── 메인 변환 함수 ────────────────────────────────────────────────────────


def convert_landmarks_to_coco17_and_pole_ext(
    frame_index: int,
    timestamp_ms: int,
    world_landmarks: list,
    image_landmarks: list | None,
    pole_axis: PoleAxis,
) -> PoseFrame:
    """MediaPipe 33 landmark → PoseFrame (COCO-17 + 폴 확장 + reliability + pole_axis).

    D-04: raw 33 전체 보존 + COCO-17 derived + 폴 확장(toe/heel/grip).
    D-05: confidence = raw_visibility × raw_presence, uncertainty_proxy = 1 - confidence.
    H-3: pole_axis 인자 → PoseFrame.pole_axis 그대로 보존.
    H-4: reliability = compute_frame_reliability(mean_visibility).
    M-1: visibility → raw_visibility, presence → raw_presence 변환.
    M-3: pole_grip_left / pole_grip_right derived landmark.
    RESEARCH §Pattern 1·3.
    """
    # 1) raw_landmarks_33: 33개 전체 Landmark3D (D-04 원본 저장)
    raw_landmarks_33: dict[str, Landmark3D] = {}
    for idx, lm in enumerate(world_landmarks):
        name = MEDIAPIPE_33_LANDMARK_NAMES[idx]
        raw_landmarks_33[name] = _landmark_to_dict(lm)

    # 2) keypoints_3d: MEDIAPIPE_33_TO_COCO17 매핑으로 17개 Keypoint3D 추출
    keypoints_3d: dict[str, Keypoint3D] = {}
    for coco_name, mp_idx in MEDIAPIPE_33_TO_COCO17.items():
        keypoints_3d[coco_name] = _build_keypoint3d(world_landmarks[mp_idx])

    # 3) pole_extension_landmarks: POLE_EXTENSION_MAP iteration
    pole_extension_landmarks: dict[str, PoseExtensionLandmark] = {}
    for ext_name, source in POLE_EXTENSION_MAP.items():
        if isinstance(source, int):
            # raw MediaPipe 인덱스 직접 추출
            pole_extension_landmarks[ext_name] = _build_pole_extension_raw(
                world_landmarks[source]
            )
        else:
            # derived: source indices 좌표 평균 (M-3: grip)
            pole_extension_landmarks[ext_name] = _build_pole_grip(world_landmarks, source)

    # 4) keypoints_2d: image_landmarks 주어졌을 때 17개 Keypoint2D
    keypoints_2d: dict[str, Keypoint2D] | None = None
    if image_landmarks is not None:
        keypoints_2d = {}
        for coco_name, mp_idx in MEDIAPIPE_33_TO_COCO17.items():
            img_lm = image_landmarks[mp_idx]
            keypoints_2d[coco_name] = Keypoint2D(
                x=float(img_lm.x),
                y=float(img_lm.y),
                visibility=float(getattr(img_lm, "visibility", 0.0)),
            )

    # 5) keypoints_3d_pole_aligned: pole.aligner lazy import
    #    Plan 03 완성 전까지는 import 실패 → raw keypoints_3d를 Keypoint3DAligned로 복사 (fallback)
    keypoints_3d_pole_aligned: dict[str, Keypoint3DAligned] = {}
    try:
        from ..pole.aligner import compute_alignment_matrix, apply_alignment  # noqa: PLC0415
        R = compute_alignment_matrix(pole_axis.axis_vector)
        keypoints_3d_pole_aligned = apply_alignment(keypoints_3d, R)
    except ImportError:
        # Plan 03 (PoleAxisAligner) 미완성 단계 폴백: raw xyz → Keypoint3DAligned 직접 변환
        for name, kp in keypoints_3d.items():
            keypoints_3d_pole_aligned[name] = Keypoint3DAligned(x=kp.x, y=kp.y, z=kp.z)

    # 6) reliability: H-4 — compute_frame_reliability(mean_visibility)
    mean_vis = _compute_mean_visibility(world_landmarks)
    reliability = compute_frame_reliability(mean_vis)

    # 7) pole_axis: H-3 — 인자 그대로 PoseFrame에 보존 (D-12)
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        raw_landmarks_33=raw_landmarks_33,
        keypoints_3d=keypoints_3d,
        keypoints_3d_pole_aligned=keypoints_3d_pole_aligned,
        keypoints_2d=keypoints_2d,
        pole_extension_landmarks=pole_extension_landmarks,
        pole_axis=pole_axis,  # H-3 박제
        reliability=reliability,  # H-4 박제
    )
