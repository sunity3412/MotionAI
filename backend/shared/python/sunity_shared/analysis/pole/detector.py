"""폴 축 자동 검출 — Hough Line Transform + 수직 prior (D-09/D-10/D-11).

Phase 1 결정 박제:
  D-09: Hough Line Transform + 수직 prior 자동 검출.
  D-10: 영상 전체 평균 축 1개 산출 (confidence 가중평균, frame_index=None).
  D-11: 검출 실패 시 수직 가정 폴백 + confidence_level='low'.
  REVIEWS H-2: cv2 module-level import 금지.
               cv2 는 HoughPoleDetector.__init__ 에서 lazy import.
               Lambda module import 는 cv2/scipy 부재 환경에서도 성공해야 함.
  REVIEWS M-2: confidence_level enum — 'high'|'medium'|'low' 문자열.
               numeric 0.3 대신 'low', 0.7+ 대신 'high' literal.
               pose_frame.RELIABILITY_HIGH_THRESHOLD / RELIABILITY_MEDIUM_THRESHOLD 재사용.
  REVIEWS H-4 임계값 재사용:
               numeric confidence >= RELIABILITY_HIGH_THRESHOLD (0.7) → 'high'
               numeric confidence >= RELIABILITY_MEDIUM_THRESHOLD (0.4) → 'medium'
               numeric confidence <  RELIABILITY_MEDIUM_THRESHOLD       → 'low'
  Pitfall 3 주석: world landmarks 원점 = hip midpoint.
               폴 축은 image 2D 좌표계에서 검출 — world 좌표와 원점이 다름.
               axis_vector 는 (x_2d, y_2d, 0.0) image 평면 가정 (카메라 roll=0).
               더 엄밀한 처리: Phase 1 범위 밖. 01-RESEARCH §Pitfall 3 참조.
"""

from __future__ import annotations

import math

import numpy as np

from ..pose_frame import (
    PoleAxis,
    RELIABILITY_HIGH_THRESHOLD,
    RELIABILITY_MEDIUM_THRESHOLD,
)

# ── Hough 파라미터 (RESEARCH §Pattern 4 권장값) ──────────────────────────
# 01-RESEARCH.md §Hough 권장 파라미터 — 정은지 5영상 sweep 후 튜닝 가능.

VERTICAL_TOLERANCE_DEG: float = 5.0      # ±5° 수직성 필터 (D-09)
CANNY_LOW: int = 50                       # Canny 하한 임계값
CANNY_HIGH: int = 200                     # Canny 상한 임계값
CANNY_APERTURE: int = 3                   # Sobel 커널 크기
HOUGH_RHO: int = 1                        # 픽셀 해상도
HOUGH_THETA_DEG: float = 1.0             # 각도 해상도 (도) — detect 내부에서 radian 변환
HOUGH_THRESHOLD: int = 80                 # 교차점 최소 누적 (RESEARCH 권장 80)
HOUGH_MIN_LINE_LENGTH: int = 100          # 폴은 화면 높이 50%+ → 640px 기준 ~100 (RESEARCH 권장)
HOUGH_MAX_LINE_GAP: int = 20             # 폴이 살짝 가려도 잇기


# ── module-level 헬퍼 (cv2 의존 없음) ────────────────────────────────────

def _map_numeric_to_confidence_level(numeric: float) -> str:
    """numeric confidence → ConfidenceLevel 문자열 매핑 (M-2 enum 박제).

    pose_frame.RELIABILITY_*_THRESHOLD 상수 재사용 (H-4 임계값).
      numeric >= RELIABILITY_HIGH_THRESHOLD (0.7) → 'high'
      numeric >= RELIABILITY_MEDIUM_THRESHOLD (0.4) → 'medium'
      else                                          → 'low'
    """
    if numeric >= RELIABILITY_HIGH_THRESHOLD:
        return "high"
    if numeric >= RELIABILITY_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


# ── HoughPoleDetector ─────────────────────────────────────────────────────

class HoughPoleDetector:
    """수직 prior + Hough Line Transform 기반 폴 축 자동 검출.

    D-09: Canny 엣지 + HoughLinesP + 수직 필터(±5°).
    D-10: 영상 전체 confidence 가중평균 → video-level PoleAxis 1개.
    D-11: 수직 선 없으면 수직 가정 폴백 + confidence_level='low'.
    H-2: cv2 는 __init__ 에서 lazy import — module load 는 cv2 부재에도 성공.

    스피닝 폴 (spinning pole) 지원: v1.5 — Phase 1 범위 밖.
    """

    def __init__(
        self,
        vertical_tolerance_deg: float = VERTICAL_TOLERANCE_DEG,
        **hough_overrides: object,
    ) -> None:
        """H-2 박제: cv2 lazy import — __init__ 에서 한 번만 import.

        hough_overrides 로 파라미터 개별 튜닝 가능:
          threshold, min_line_length, max_line_gap, canny_low, canny_high.
        """
        # H-2 박제: module-level import cv2 금지. __init__ 내부에서만.
        try:
            import cv2
            self._cv2 = cv2
        except ImportError as e:
            raise RuntimeError(
                "opencv-python-headless 미설치 — HoughPoleDetector 는 RunPod 또는 "
                "cv2 설치 환경에서만 동작. 'pip install opencv-python-headless' 후 재시도."
            ) from e

        self._vertical_tolerance_deg = vertical_tolerance_deg

        # Hough 파라미터 (module-level 상수가 기본값, hough_overrides 로 override)
        self._canny_low: int = int(hough_overrides.get("canny_low", CANNY_LOW))
        self._canny_high: int = int(hough_overrides.get("canny_high", CANNY_HIGH))
        self._canny_aperture: int = int(hough_overrides.get("canny_aperture", CANNY_APERTURE))
        self._hough_rho: int = int(hough_overrides.get("hough_rho", HOUGH_RHO))
        self._hough_theta: float = math.radians(
            float(hough_overrides.get("hough_theta_deg", HOUGH_THETA_DEG))
        )
        self._hough_threshold: int = int(hough_overrides.get("threshold", HOUGH_THRESHOLD))
        self._hough_min_line_length: int = int(
            hough_overrides.get("min_line_length", HOUGH_MIN_LINE_LENGTH)
        )
        self._hough_max_line_gap: int = int(
            hough_overrides.get("max_line_gap", HOUGH_MAX_LINE_GAP)
        )

    def detect(self, frames: np.ndarray) -> PoleAxis:
        """(T, H, W, 3) RGB uint8 → 단일 video-level PoleAxis.

        D-10: 모든 frame 에 동일 axis 적용 — frame_index=None (video-level).
        D-11: 수직 선 없으면 vertical_fallback + confidence_level='low'.

        Pitfall 3: axis_vector 는 image 2D 평면에서 검출된 방향 (x, y, 0.0).
          world landmarks 원점은 hip midpoint 이므로 axis_vector 와 원점이 다름.
          카메라 roll=0 가정 — 더 엄밀한 처리는 Phase 1 범위 밖.
          (01-RESEARCH §Pitfall 3 참조)
        """
        cv2 = self._cv2

        # 빈 frames (T=0) → vertical_fallback (D-11)
        if frames.shape[0] == 0:
            return PoleAxis(
                axis_vector=(0.0, 1.0, 0.0),
                confidence_level="low",
                source="vertical_fallback",
                frame_index=None,  # D-10 video-level
            )

        directions: list[tuple[float, float]] = []
        confidences: list[float] = []

        for frame_rgb in frames:
            h = frame_rgb.shape[0]

            # 그레이스케일 변환
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)

            # Canny 엣지 검출
            edges = cv2.Canny(
                gray,
                self._canny_low,
                self._canny_high,
                apertureSize=self._canny_aperture,
            )

            # HoughLinesP (확률적 Hough Line Transform)
            lines = cv2.HoughLinesP(
                edges,
                self._hough_rho,
                self._hough_theta,
                self._hough_threshold,
                minLineLength=self._hough_min_line_length,
                maxLineGap=self._hough_max_line_gap,
            )

            if lines is None:
                continue

            # 수직 필터링 + 길이 가중
            for line in lines:
                x1, y1, x2, y2 = line[0]
                dx = x2 - x1
                dy = y2 - y1

                # 각도 계산 — 수직 = 90°
                angle_deg = math.degrees(math.atan2(abs(dy), abs(dx)))

                # 수직 필터: ±vertical_tolerance_deg 범위만 통과 (D-09)
                if abs(angle_deg - 90.0) > self._vertical_tolerance_deg:
                    continue

                length = math.hypot(dx, dy)
                if length < self._hough_min_line_length:
                    continue

                # 2D 방향 벡터 — 항상 y+ (아래) 쪽으로 정규화
                vy = abs(dy)
                vx = math.copysign(abs(dx), dx) if dy != 0 else float(dx)
                norm = math.hypot(vx, vy)
                if norm < 1e-9:
                    continue

                directions.append((vx / norm, vy / norm))

                # 프레임당 confidence: 폴 길이 / 영상 높이 비율 (RESEARCH Pattern 4)
                confidences.append(min(length / h, 1.0))

        # 수직 선 없음 → D-11 vertical_fallback
        if not directions:
            return PoleAxis(
                axis_vector=(0.0, 1.0, 0.0),
                confidence_level="low",
                source="vertical_fallback",
                frame_index=None,
            )

        # confidence 가중평균으로 video-level 방향 벡터 산출 (D-10)
        dirs = np.array(directions, dtype=np.float64)   # (N, 2)
        weights = np.array(confidences, dtype=np.float64)  # (N,)

        avg_dir = (dirs * weights[:, None]).sum(axis=0) / weights.sum()
        norm_val = np.linalg.norm(avg_dir)
        if norm_val < 1e-9:
            # 평균이 0 벡터 — 폴백
            return PoleAxis(
                axis_vector=(0.0, 1.0, 0.0),
                confidence_level="low",
                source="vertical_fallback",
                frame_index=None,
            )
        avg_dir /= norm_val

        # Pitfall 3: 2D image 방향 → 3D 카메라 좌표 변환 가정.
        # z=0.0 (image 평면 가정, 카메라 roll=0 가정).
        axis_3d = (float(avg_dir[0]), float(avg_dir[1]), 0.0)

        # 재정규화 (z=0 추가 후 단위 벡터 보장)
        ax, ay, az = axis_3d
        norm_3d = math.sqrt(ax * ax + ay * ay + az * az)
        if norm_3d < 1e-9:
            axis_3d = (0.0, 1.0, 0.0)
        else:
            axis_3d = (ax / norm_3d, ay / norm_3d, az / norm_3d)

        # numeric confidence → ConfidenceLevel enum (M-2 박제)
        numeric_confidence = float(min(weights.mean(), 1.0))
        confidence_level = _map_numeric_to_confidence_level(numeric_confidence)

        return PoleAxis(
            axis_vector=axis_3d,
            confidence_level=confidence_level,
            source="detected",
            frame_index=None,  # D-10 video-level — frame_index=None
        )
