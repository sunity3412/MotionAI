"""RTMW 133 wholebody keypoints → COCO-17 + 폴 확장 (toe/heel/grip) 변환 어댑터.

Plan 01-21 Task 1. D-20/D-22/H-3/H-4/D-21 박제.

D-20: RTMW 133 원본 보존 (raw_keypoints_133) + COCO-17 분석 계약 (keypoints_3d) + 폴 확장.
D-22: RTMW 단일 keypoint score → Keypoint3D.confidence 직접 매핑.
      uncertainty_proxy = 1 - confidence (D-22).
H-3: pole_axis 인자를 PoseFrame.pole_axis 에 그대로 보존.
H-4: frame-level reliability = compute_frame_reliability(mean_score).
D-21: PoseFrame.body_shape = None (RTMW path 는 SMPL-X β 없음).

어댑터 본체는 rtmlib/mmpose/onnxruntime 완전 무관 (backend-agnostic).
rtmlib 의존은 RTMWPoseEngine(Task 2) 에서만 lazy import.
"""

from __future__ import annotations

import numpy as np

from ..pose_frame import (
    PoseFrame,
    Keypoint2D,
    Keypoint3D,
    Keypoint3DAligned,
    PoseExtensionLandmark,
    PoleAxis,
    compute_frame_reliability,
)
from ..skeleton import KEYPOINT_NAMES
from ..pose_engines.rtmw.wholebody_keypoints import RTMW_KEYPOINT_INDICES


# ── RTMW 133 → COCO-17 매핑 ──────────────────────────────────────────────
#
# RTMW body 17 인덱스 = COCO-17 표준 (0~16) — 1:1 매핑.
# [CITED: COCO-WholeBody + rtmlib README]
#
RTMW_133_TO_COCO17: dict[str, int] = {name: RTMW_KEYPOINT_INDICES[name] for name in KEYPOINT_NAMES}
assert len(RTMW_133_TO_COCO17) == 17


# ── grip derived source 인덱스 ─────────────────────────────────────────────
#
# A2 grip derivation: left_hand_root + index_finger_mcp + middle_finger_mcp 평균
# [CITED: mediapipe_to_coco17.py A2 패턴 — wrist/finger 평균 grip point]
# RTMW 의 좌손: left_hand_root(91), left_index_finger_mcp(96), left_middle_finger_mcp(100)
# RTMW 의 우손: right_hand_root(112), right_index_finger_mcp(117), right_middle_finger_mcp(121)
#
GRIP_LEFT_SOURCE_INDICES: tuple[int, ...] = (91, 96, 100)   # left hand root + index/middle MCP
GRIP_RIGHT_SOURCE_INDICES: tuple[int, ...] = (112, 117, 121) # right hand root + index/middle MCP


# ── 폴 확장 landmark 맵 ──────────────────────────────────────────────────
#
# D-04/D-20 박제: toe / heel / grip 확장.
#   int 값: RTMW 133 배열 인덱스에서 직접 추출.
#   tuple 값: derived — source 인덱스들의 좌표 평균 (grip).
#
# left_foot_index  = left_big_toe  (RTMW 인덱스 17)
# right_foot_index = right_big_toe (RTMW 인덱스 20)
# left_heel        = RTMW 인덱스 19
# right_heel       = RTMW 인덱스 22
#
POLE_EXTENSION_MAP: dict[str, int | tuple[int, ...]] = {
    "left_heel":        19,                       # raw RTMW 인덱스
    "right_heel":       22,                       # raw RTMW 인덱스
    "left_foot_index":  17,                       # left_big_toe (RTMW 인덱스 17)
    "right_foot_index": 20,                       # right_big_toe (RTMW 인덱스 20)
    "pole_grip_left":   GRIP_LEFT_SOURCE_INDICES,  # derived
    "pole_grip_right":  GRIP_RIGHT_SOURCE_INDICES, # derived
}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

def _build_keypoint3d_from_score(
    x: float,
    y: float,
    z: float,
    score: float,
) -> Keypoint3D:
    """RTMW score → Keypoint3D.

    D-22: confidence = score (단일 score 직접 매핑).
    uncertainty_proxy = 1 - confidence.
    """
    confidence = float(np.clip(score, 0.0, 1.0))
    uncertainty_proxy = 1.0 - confidence
    return Keypoint3D(
        x=x,
        y=y,
        z=z,
        confidence=confidence,
        uncertainty_proxy=uncertainty_proxy,
    )


def _build_keypoints_2d_from_rtmw(
    keypoints_133: np.ndarray,
    scores_133: np.ndarray,
    img_w: int,
    img_h: int,
) -> dict[str, Keypoint2D]:
    """RTMW 133 keypoints + scores → COCO-17 2D normalized [0, 1].

    Phase 12 Wave 0A R1 fix + B1 iter-4 fix (Codex 직접 리뷰 2026-06-10):
      - 기존 None 반환 폐기 → 실 COCO-17 2D 좌표 박제.
      - confidence source = scores_133 (별도 1D array, shape (133,)). keypoints_133[i][2]
        는 3D path 에서 z 좌표 — visibility 로 쓰면 z 가 누설됨.
      - 좌표 normalization: image native px → 0..1 normalized (RESEARCH §Pattern 1 정합).
      - visibility = float(np.clip(score, 0.0, 1.0)).
      - Keypoint2D 는 x/y/visibility 3 필드만 (R6 정합 — raw_visibility/raw_presence 는
        Landmark2D/Landmark3D 영역, Keypoint2D 와 혼동 X).
      - Phase 12 KeypointOverlay (Wave 1/2) 의 데이터 source.

    Args:
        keypoints_133: (133, 3) float array — (x, y, z) px.
        scores_133: (133,) float array — per-keypoint confidence score [0~1].
        img_w: 원본 프레임 폭 (px). <= 0 → 빈 dict + log warning.
        img_h: 원본 프레임 높이 (px). <= 0 → 빈 dict + log warning.

    Returns:
        dict[COCO joint name -> Keypoint2D]. img dim 부적합 시 빈 dict.
    """
    if img_w <= 0 or img_h <= 0:
        # 좌표 normalization 실패 — keypoint_2d_unavailable warning 박제 (R1 fallback).
        # log import 회피 — 호출 빈도 낮고, 빈 dict 반환만으로 caller 가 fallback 가능.
        return {}
    result: dict[str, Keypoint2D] = {}
    for coco_name, rtmw_idx in RTMW_133_TO_COCO17.items():
        kp = keypoints_133[rtmw_idx]  # shape (3,) = (x, y, z) — z 무시
        score = float(np.clip(scores_133[rtmw_idx], 0.0, 1.0))
        result[coco_name] = Keypoint2D(
            x=float(kp[0]) / float(img_w),
            y=float(kp[1]) / float(img_h),
            visibility=score,
        )
    return result


def _build_pole_extension_from_rtmw(
    keypoints_133: np.ndarray,
    scores_133: np.ndarray,
    rtmw_idx: int,
) -> PoseExtensionLandmark:
    """raw RTMW 인덱스에서 PoseExtensionLandmark 생성."""
    kp = keypoints_133[rtmw_idx]
    score = float(np.clip(scores_133[rtmw_idx], 0.0, 1.0))
    return PoseExtensionLandmark(
        x=float(kp[0]),
        y=float(kp[1]),
        z=float(kp[2]),
        confidence=score,
    )


def _build_pole_grip_from_rtmw(
    keypoints_133: np.ndarray,
    scores_133: np.ndarray,
    source_indices: tuple[int, ...],
) -> PoseExtensionLandmark:
    """source 인덱스 좌표/score 평균으로 grip derived landmark 생성."""
    xs = [float(keypoints_133[i][0]) for i in source_indices]
    ys = [float(keypoints_133[i][1]) for i in source_indices]
    zs = [float(keypoints_133[i][2]) for i in source_indices]
    n = len(source_indices)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    mean_z = sum(zs) / n
    mean_conf = float(np.mean([np.clip(scores_133[i], 0.0, 1.0) for i in source_indices]))
    return PoseExtensionLandmark(
        x=mean_x,
        y=mean_y,
        z=mean_z,
        confidence=mean_conf,
    )


# ── 메인 변환 함수 ────────────────────────────────────────────────────────

def convert_rtmw_keypoints_to_coco17_and_pole_ext(
    keypoints_133: np.ndarray,
    scores_133: np.ndarray,
    image_width: int,
    image_height: int,
    frame_index: int,
    timestamp_ms: int,
    pole_axis: PoleAxis,
) -> PoseFrame:
    """RTMW 133 wholebody keypoints → PoseFrame (COCO-17 + 폴 확장 + reliability + pole_axis).

    D-20: 133 원본 전체 raw_keypoints_133 에 보존. COCO-17 derived 스코어링 계약.
    D-22: confidence = score (단일 score 직접 매핑). uncertainty_proxy = 1 - confidence.
    H-3: pole_axis 인자 → PoseFrame.pole_axis 그대로 보존.
    H-4: reliability = compute_frame_reliability(mean_scores).
    D-21: body_shape = None (RTMW path).

    Args:
        keypoints_133: (133, 3) float array — (x, y, z) 또는 (x, y, score) 형태.
                       z=0 인 경우 2D 추론 결과.
        scores_133: (133,) float array — per-keypoint confidence score (0~1).
        image_width: 원본 프레임 폭 (px) — 2D normalized 변환용.
        image_height: 원본 프레임 높이 (px).
        frame_index: 영상 프레임 인덱스.
        timestamp_ms: 영상 타임스탬프 (ms).
        pole_axis: PoleDetector 산출 PoleAxis (D-10/H-3).

    Returns:
        PoseFrame — COCO-17 + 폴 확장 + 133 원본 보존.
    """
    # 1) raw_keypoints_133: 133개 전체 Keypoint3D (D-20 원본 저장)
    raw_keypoints_133: dict[str, Keypoint3D] = {}
    for name, idx in RTMW_KEYPOINT_INDICES.items():
        kp = keypoints_133[idx]
        score = scores_133[idx]
        raw_keypoints_133[name] = _build_keypoint3d_from_score(
            x=float(kp[0]),
            y=float(kp[1]),
            z=float(kp[2]),
            score=float(score),
        )

    # 2) keypoints_3d: RTMW_133_TO_COCO17 매핑으로 17개 Keypoint3D 추출
    keypoints_3d: dict[str, Keypoint3D] = {}
    for coco_name, rtmw_idx in RTMW_133_TO_COCO17.items():
        kp = keypoints_133[rtmw_idx]
        score = scores_133[rtmw_idx]
        keypoints_3d[coco_name] = _build_keypoint3d_from_score(
            x=float(kp[0]),
            y=float(kp[1]),
            z=float(kp[2]),
            score=float(score),
        )

    # 3) pole_extension_landmarks: POLE_EXTENSION_MAP iteration
    pole_extension_landmarks: dict[str, PoseExtensionLandmark] = {}
    for ext_name, source in POLE_EXTENSION_MAP.items():
        if isinstance(source, int):
            pole_extension_landmarks[ext_name] = _build_pole_extension_from_rtmw(
                keypoints_133, scores_133, source
            )
        else:
            pole_extension_landmarks[ext_name] = _build_pole_grip_from_rtmw(
                keypoints_133, scores_133, source
            )

    # 4) keypoints_3d_pole_aligned: pole aligner 사용 (Plan 03 산출)
    keypoints_3d_pole_aligned: dict[str, Keypoint3DAligned] = {}
    try:
        from ..pole.aligner import compute_alignment_matrix, apply_alignment  # noqa: PLC0415
        R = compute_alignment_matrix(pole_axis.axis_vector)
        keypoints_3d_pole_aligned = apply_alignment(keypoints_3d, R)
    except ImportError:
        # Plan 03 (PoleAxisAligner) 미완성 폴백: raw xyz → Keypoint3DAligned 직접 변환
        for name, kp in keypoints_3d.items():
            keypoints_3d_pole_aligned[name] = Keypoint3DAligned(x=kp.x, y=kp.y, z=kp.z)

    # 5) reliability: H-4 — compute_frame_reliability(mean_scores)
    #    RTMW 에서는 scores_133 mean 사용 (visibility 대신 score — D-22)
    mean_score = float(np.clip(np.mean(scores_133), 0.0, 1.0))
    reliability = compute_frame_reliability(mean_score)

    # 6) PoseFrame 반환 — D-21: body_shape=None, H-3: pole_axis 인자 그대로
    return PoseFrame(
        frame_index=frame_index,
        timestamp_ms=timestamp_ms,
        raw_landmarks_33={},        # RTMW path: 빈 dict (raw_keypoints_133 사용)
        keypoints_3d=keypoints_3d,
        keypoints_3d_pole_aligned=keypoints_3d_pole_aligned,
        # Phase 12 Wave 0A R1 fix (2026-06-10 Codex 직접 리뷰) — 기존 None 폐기.
        # COCO-17 keypoint name → Keypoint2D(x, y, visibility) normalized [0,1].
        # scores_133 별도 인자 (B1 iter-4 — kp[2] 는 z, visibility 와 무관).
        keypoints_2d=_build_keypoints_2d_from_rtmw(
            keypoints_133, scores_133, image_width, image_height
        ),
        pole_extension_landmarks=pole_extension_landmarks,
        pole_axis=pole_axis,        # H-3 박제
        reliability=reliability,    # H-4 박제
        body_shape=None,            # D-21 박제 — RTMW path = None
        raw_keypoints_133=raw_keypoints_133,  # D-20 박제 — 133 원본 보존
    )
