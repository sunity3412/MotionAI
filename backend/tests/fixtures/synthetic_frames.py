"""Hough 폴 검출 + 어댑터 단위 테스트용 합성 프레임 (T, H, W, 3) RGB uint8.

무거운 의존성 없음 — numpy only.

생성 함수:
  synthetic_vertical_pole_frames  : 수직 폴 — Hough 검출 명확 케이스
  synthetic_no_pole_frames        : 균일 흰색 — Hough 검출 실패 케이스
  synthetic_tilted_pole_frames    : 기울어진 폴 — vertical_tolerance 밖 케이스

반환값: (T, H, W, 3) uint8 RGB array.
"""

from __future__ import annotations

import numpy as np


def synthetic_vertical_pole_frames(
    num_frames: int = 3,
    height: int = 128,
    width: int = 64,
    pole_x: int | None = None,
) -> np.ndarray:
    """수직 폴 띠가 있는 합성 프레임. Hough 검출이 명확하게 성공하는 케이스.

    배경: 흰색 (255). 폴: 중앙 x 위치에 ±2 px 그레이 (80) 수직 띠.
    pole_x: 폴 중심 x 좌표 (None 이면 width // 2).
    """
    if pole_x is None:
        pole_x = width // 2

    arr = np.full((num_frames, height, width, 3), fill_value=255, dtype=np.uint8)
    # 폴 띠: pole_x 기준 ±2 px (총 5 px 폭)
    x_start = max(0, pole_x - 2)
    x_end = min(width, pole_x + 3)
    arr[:, :, x_start:x_end, :] = 80

    assert arr.dtype == np.uint8 and arr.ndim == 4 and arr.shape[3] == 3
    return arr


def synthetic_no_pole_frames(
    num_frames: int = 3,
    height: int = 128,
    width: int = 64,
) -> np.ndarray:
    """균일 흰색 프레임. Hough 검출 실패 케이스 (수직 선 없음).

    vertical_fallback 폴백 로직 테스트에 사용.
    """
    arr = np.full((num_frames, height, width, 3), fill_value=255, dtype=np.uint8)
    assert arr.dtype == np.uint8 and arr.ndim == 4 and arr.shape[3] == 3
    return arr


def synthetic_tilted_pole_frames(
    num_frames: int = 3,
    height: int = 128,
    width: int = 64,
    tilt_deg: float = 30.0,
) -> np.ndarray:
    """기울어진 폴 (tilt_deg 도 기울기). vertical_tolerance 5° 밖 케이스.

    폴을 대각선 띠로 그린다. Hough 검출은 성공할 수 있으나 vertical 기준(±5°) 밖.
    tilt_deg: 수직(90°)에서의 이탈 각도. 기본 30° — 명확히 vertical_tolerance 초과.
    """
    import math

    arr = np.full((num_frames, height, width, 3), fill_value=255, dtype=np.uint8)

    # 기울어진 폴: 중심 x 에서 시작, 각 row 마다 x 이동
    tilt_rad = math.radians(tilt_deg)
    slope = math.tan(tilt_rad)  # dx/dy
    center_x = width // 2

    for row in range(height):
        col = int(round(center_x + slope * (row - height // 2)))
        for dc in range(-2, 3):
            c = col + dc
            if 0 <= c < width:
                arr[:, row, c, :] = 80

    assert arr.dtype == np.uint8 and arr.ndim == 4 and arr.shape[3] == 3
    return arr
