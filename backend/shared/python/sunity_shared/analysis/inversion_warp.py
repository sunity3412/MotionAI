"""PR(PersPose 위상회전) 인버전 보정 — 검출 휴리스틱 + 호모그래피 유틸 (32-15, D-22).

spike 006 실측 근거 (.planning/spikes/004-gemini-omni-view-editing/README.md):
  invert(역수직) boneCV 1.16 → 0.489 (−58%) — 인버전 원근왜곡 정규화가 추적 대폭 개선.
  power-spin 전면 적용 1.03 → 7.0 파괴 — 고속 스핀은 중심이 요동해 워프가 추적을 부순다.
  → 프로덕션 통합은 **거꾸로(인버전) 동작 한정 조건부** (32-RESEARCH §PR).

2-pass 조건부 아키텍처 (32-15-PLAN objective — 리뷰 blocker 6 해소):
  ① 1차 추론 = 기존 경로 그대로 (항상 실행 — 이것이 곧 분석)
  ② 1차 keypoint 시퀀스로 인버전 검출 (본 모듈 detect_inversion — 순수 numpy)
  ③ 참일 때만: 1차 kpts 평활 중심(smooth_centers) → H=K·R·K⁻¹ 워프(build_homography)
     → 워프 프레임 2차 추론 → 예측 좌표를 H⁻¹로 원본 프레임 공간 복원(unwarp_points)
     → 프레임 단위 fail-safe(unwarp_frame_keypoints) 통과분만 교체.
  거짓이면 1차 결과 그대로 (바이트 동일 — 비인버전 무회귀의 구조 보장).
  순환 의존 없음: 검출 입력은 1차 추론 "결과"다 (추론 전 keypoint 검출이 아님).
  좌표는 항상 원본 프레임 공간 — 오버레이·crop·채점 좌표계 불변.

훅 위치: pose_engines/rtmw/rtmw_engine.RTMWPoseEngine (프로덕션 추론 단일 관문).
  플랜 명목 대상 pose_estimator.py(NLF)는 DEPRECATED 미사용 경로 — 32-15-SUMMARY 참조.

순수성: 검출·호모그래피 경로는 numpy 만 (torch/cv2 0 — Rodrigues 를 numpy 로 구현).
  cv2 는 프레임 픽셀 워프(warp_frames — GPU/Pod 경로)에서만 lazy import.

안전 기본 분기 ([[motion-routing-generalize-principle]] — fail-closed 금지):
  미상·모호·저신뢰 입력은 전부 "미검출(False) → 보정 미적용 → 기존 경로" 로 수렴.
  보정은 실측 근거가 있는 지속 인버전에서만 켜진다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# ── 검출 상수 (spike 실데이터 캘리브레이션 — 2026-07-22 로컬 재계측) ──────────
#
# 데이터: .planning/spikes/004 kpts/*.npz (RTMW 9fps, 10 clip).
# 프레임 판정 = (어깨mid_y − 엉덩이mid_y) / torso 길이 > INVERSION_MARGIN
#   (이미지 좌표 y 는 아래로 증가 — 값이 양수면 엉덩이가 어깨 "위" = 역위).
# margin 0.3 기준 실측 (ratio = 역위 프레임 / 유효 프레임, run = 최장 연속 역위):
#   TP측 최소:  invert 0.289/run18 · straddle-invert 0.300/run20 · elbow-twist 1.000/run9
#   FP측 최대:  power-spin 0.042/run2 · sideway-spin 0.025/run1 · 정립 5종 0.000/run0
# → RATIO 0.15 = TP 최소(0.289)의 절반 수준·FP 최대(0.042)의 3.6배 위 (양방 여유).
# → MIN_RUN 5프레임(9fps 기준 ~0.56s) = TP 최소 run(9)의 절반·FP 최대 run(2)의 2.5배.
# 두 조건 AND — 고속 스핀의 순간 역전(점프 프레임)은 run 조건이 차단한다.
INVERSION_MARGIN = 0.3
INVERSION_RATIO = 0.15
INVERSION_MIN_RUN = 5

# keypoint 신뢰 하한 — spike compute_metrics BODY_CONF(0.3) 동일 관례.
MIN_JOINT_CONF = 0.3

# 역변환 좌표 허용 마진 (프레임 각 변의 25%) — 사지가 프레임을 살짝 벗어나는
# 정상 좌표는 통과시키되, 워프/역변환 붕괴로 인한 대탈출 좌표는 프레임 단위
# 폴백(1차 좌표 유지)으로 보낸다 (플랜 behavior 4).
UNWARP_BOUNDS_TOLERANCE = 0.25

# 중심 평활 이동평균 창 — spike pr_warp_pod.per_frame_centers(k=9) 동일 값.
# 9fps 에서 1초 창: 프레임별 중심 요동(워프 wobble)을 눌러 추적 파괴를 막는다.
CENTER_SMOOTH_WINDOW = 9

# COCO body 인덱스 (RTMW 133 의 선두 17 = COCO-17 순서)
_BODY = slice(0, 17)
_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP = 5, 6, 11, 12
_MIN_CENTER_POINTS = 5  # spike per_frame_centers 동일 — 중심 산출 최소 유효 kpt 수


@dataclass(frozen=True)
class InversionDetection:
    """검출 결과 + 로깅/게이트 기록용 근거 수치."""

    is_inverted: bool
    inverted_ratio: float
    longest_run_frames: int
    valid_frames: int
    total_frames: int


def detect_inversion(keypoints_xy: np.ndarray, scores: np.ndarray) -> InversionDetection:
    """1차 추론 keypoint 시퀀스에서 지속 인버전 여부를 판정한다 (순수 numpy).

    Args:
        keypoints_xy: (T, K, 2) — K ≥ 13 (COCO body 인덱스 5/6/11/12 사용,
                      17 또는 133 배열 모두 수용). 픽셀 좌표.
        scores: (T, K) — per-keypoint confidence (0~1).

    Returns:
        InversionDetection. 판정 = (역위 비율 ≥ INVERSION_RATIO) AND
        (최장 연속 역위 ≥ INVERSION_MIN_RUN). 유효 프레임(어깨·엉덩이 4점 전부
        신뢰 + 유한) 0 이면 False — 모호하면 보정 미적용이 기본 (안전 분기).
    """
    kpts = np.asarray(keypoints_xy, dtype=float)
    conf = np.asarray(scores, dtype=float)
    T = len(kpts)
    if T == 0:
        return InversionDetection(False, 0.0, 0, 0, 0)

    idx = [_L_SHOULDER, _R_SHOULDER, _L_HIP, _R_HIP]
    joint_ok = (conf[:, idx] > MIN_JOINT_CONF).all(axis=-1)
    finite_ok = np.isfinite(kpts[:, idx, :]).all(axis=(-2, -1))
    valid = joint_ok & finite_ok

    sh_mid = kpts[:, [_L_SHOULDER, _R_SHOULDER], :].mean(axis=1)  # (T,2)
    hip_mid = kpts[:, [_L_HIP, _R_HIP], :].mean(axis=1)
    torso = np.linalg.norm(sh_mid - hip_mid, axis=-1)
    # margin > 0 = 엉덩이가 어깨 위 (이미지 y 아래 증가) — torso 정규화로 해상도 무관.
    with np.errstate(invalid="ignore", divide="ignore"):
        margin = (sh_mid[:, 1] - hip_mid[:, 1]) / (torso + 1e-9)
    inverted = valid & (margin > INVERSION_MARGIN)

    n_valid = int(valid.sum())
    if n_valid == 0:
        return InversionDetection(False, 0.0, 0, 0, T)

    ratio = float(inverted.sum() / n_valid)
    longest = _longest_true_run(inverted)
    is_inv = bool(ratio >= INVERSION_RATIO and longest >= INVERSION_MIN_RUN)
    return InversionDetection(is_inv, ratio, longest, n_valid, T)


def _longest_true_run(mask: np.ndarray) -> int:
    best = cur = 0
    for m in mask:
        cur = cur + 1 if m else 0
        if cur > best:
            best = cur
    return best


def smooth_centers(keypoints_xy: np.ndarray, scores: np.ndarray) -> np.ndarray | None:
    """1차 kpts 로 프레임별 인체 중심을 산출·보간·평활한다 (spike 방식 그대로).

    spike 는 9fps kpts 를 원본 fps grid 로 보간했지만, 프로덕션 2-pass 는
    추론 대상 프레임 배열과 kpts 가 1:1 (같은 9fps 추출 프레임) — 시간축 보간이
    아닌 "유효 프레임 간" 선형 보간 + 이동평균(창 9)만 수행한다.

    Returns:
        (T, 2) float 중심 좌표. 유효 중심이 프레임 0개면 None (워프 스킵 신호).
    """
    kpts = np.asarray(keypoints_xy, dtype=float)
    conf = np.asarray(scores, dtype=float)
    T = len(kpts)
    if T == 0:
        return None

    centers = np.full((T, 2), np.nan)
    body_conf = conf[:, _BODY] > MIN_JOINT_CONF
    for t in range(T):
        pts = kpts[t, _BODY][body_conf[t]]
        pts = pts[np.isfinite(pts).all(axis=-1)]
        if len(pts) >= _MIN_CENTER_POINTS:
            centers[t] = pts.mean(axis=0)

    valid = np.isfinite(centers[:, 0])
    if not valid.any():
        return None

    grid = np.arange(T, dtype=float)
    cx = np.interp(grid, grid[valid], centers[valid, 0])
    cy = np.interp(grid, grid[valid], centers[valid, 1])

    k = CENTER_SMOOTH_WINDOW
    ker = np.ones(k) / k
    cx = np.convolve(np.pad(cx, k // 2, mode="edge"), ker, mode="valid")[:T]
    cy = np.convolve(np.pad(cy, k // 2, mode="edge"), ker, mode="valid")[:T]
    return np.stack([cx, cy], axis=-1)


# ── 호모그래피 (H = K·R·K⁻¹ — PersPose PR, spike pr_warp_pod 편입) ────────────


def _rodrigues(axis_angle: np.ndarray) -> np.ndarray:
    """축각 벡터 → 회전 행렬 (순수 numpy — cv2.Rodrigues 대체)."""
    theta = float(np.linalg.norm(axis_angle))
    if theta < 1e-12:
        return np.eye(3)
    kx, ky, kz = axis_angle / theta
    K = np.array([[0.0, -kz, ky], [kz, 0.0, -kx], [-ky, kx, 0.0]])
    return np.eye(3) + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)


def build_homography(center_xy: np.ndarray, image_width: int, image_height: int) -> np.ndarray:
    """인체 중심 광선을 z축에 정렬하는 H = K·R·K⁻¹ (spike pr_homography 편입).

    focal = hypot(W, H) — CLIFF 근사 (spike 동일). 중심이 광학 중심과 일치하면
    회전각 0 → H = I (워프 무의미 — spike '중앙 근접 클립 ±0.03 무영향' 정합).
    """
    f = float(np.hypot(image_width, image_height))
    K = np.array([[f, 0.0, image_width / 2.0], [0.0, f, image_height / 2.0], [0.0, 0.0, 1.0]])
    Kinv = np.linalg.inv(K)
    ray = Kinv @ np.array([float(center_xy[0]), float(center_xy[1]), 1.0])
    v = ray / np.linalg.norm(ray)
    z = np.array([0.0, 0.0, 1.0])
    axis = np.cross(v, z)
    s = float(np.linalg.norm(axis))
    if s < 1e-8:
        return np.eye(3)
    phi = float(np.arccos(np.clip(np.dot(v, z), -1.0, 1.0)))
    R = _rodrigues(axis / s * phi)
    return K @ R @ Kinv


def warp_points(H: np.ndarray, points_xy: np.ndarray) -> np.ndarray:
    """(N,2) 좌표에 호모그래피 적용. w≈0 발산은 inf 로 남긴다 (fail-safe 가 거름)."""
    pts = np.asarray(points_xy, dtype=float)
    homo = np.concatenate([pts, np.ones((len(pts), 1))], axis=-1)  # (N,3)
    out = homo @ np.asarray(H, dtype=float).T
    with np.errstate(invalid="ignore", divide="ignore"):
        return out[:, :2] / out[:, 2:3]


def unwarp_points(H: np.ndarray, points_xy: np.ndarray) -> np.ndarray:
    """워프 공간 좌표 → H⁻¹ 로 원본 프레임 공간 복원 (2차 추론 좌표의 핵심 역변환).

    Raises:
        numpy.linalg.LinAlgError: H 특이 — caller(unwarp_frame_keypoints)가
        프레임 폴백으로 흡수한다.
    """
    return warp_points(np.linalg.inv(np.asarray(H, dtype=float)), points_xy)


def unwarp_frame_keypoints(
    H: np.ndarray,
    keypoints_xy: np.ndarray,
    image_width: int,
    image_height: int,
) -> tuple[np.ndarray, bool]:
    """한 프레임의 2차 추론 keypoint 를 원본 공간으로 복원 + 유효성 판정.

    반환 계약 (플랜 behavior 4 — 프레임 단위 폴백, 전체 폐기 아님):
      (unwarped, True)  — 전 keypoint 유한 + 허용 범위 내 → 교체 가능.
      (원본 입력, False) — 비유한/범위 대탈출/특이 H → caller 는 해당 프레임의
                           1차(원본) 좌표를 유지해야 한다.

    범위 판정은 입력 배열 전체(kpts (K,2))에 대해 수행 — 프로덕션 caller 는
    COCO body 17 만 넘겨 채점층 기준으로 판정한다 (손·얼굴 저신뢰 노이즈가
    프레임 전체를 기각시키지 않도록).
    """
    kpts = np.asarray(keypoints_xy, dtype=float)
    try:
        back = unwarp_points(H, kpts)
    except np.linalg.LinAlgError:
        return kpts, False

    if not np.all(np.isfinite(back)):
        return kpts, False

    tol_x = image_width * UNWARP_BOUNDS_TOLERANCE
    tol_y = image_height * UNWARP_BOUNDS_TOLERANCE
    in_x = (back[:, 0] >= -tol_x) & (back[:, 0] <= image_width + tol_x)
    in_y = (back[:, 1] >= -tol_y) & (back[:, 1] <= image_height + tol_y)
    if not bool((in_x & in_y).all()):
        return kpts, False
    return back, True


# ── 프레임 픽셀 워프 (GPU/Pod 경로 — cv2 lazy, 어댑터 관례) ───────────────────


def warp_frames(frames: np.ndarray, homographies: list[np.ndarray]) -> np.ndarray:
    """(T,H,W,3) uint8 프레임을 프레임별 H 로 워프한다 — 2차 추론 입력 생성.

    cv2 는 여기서만 lazy import (H-2 어댑터 관례 — Lambda/CI 순수 경로 무영향).
    """
    import cv2  # noqa: PLC0415 — GPU/Pod 경로 한정 lazy import

    T, h, w, _ = frames.shape
    out = np.empty_like(frames)
    for t in range(T):
        out[t] = cv2.warpPerspective(frames[t], homographies[t], (w, h))
    return out
