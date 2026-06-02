"""RTMW 133 wholebody keypoints 테스트 픽스처 (Plan 01-21 Task 1).

make_mock_rtmw_keypoints_133: (133, 3) 좌표 배열 + (133,) score 배열 생성 헬퍼.
단위 테스트에서 rtmlib 없이 어댑터 동작 검증에 사용.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np


def make_mock_rtmw_keypoints_133(
    scores: float | Sequence[float] | None = None,
    visible_indices: Sequence[int] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Mock RTMW 133 wholebody keypoints 생성.

    Returns:
        keypoints: (133, 3) float32 배열 — (x, y, z) 좌표. z=0 (2D 출력 기본).
        score_arr: (133,) float32 배열 — 각 keypoint confidence score.

    Args:
        scores: float 단일값 (전체 동일), 또는 (133,) 배열.
                None 이면 기본값 0.9 사용.
        visible_indices: 해당 인덱스만 score=1.0, 나머지 0.0 설정 (low-confidence 테스트용).
                         scores 와 상호 배제 — visible_indices 가 우선.
    """
    # 기본 좌표: 인덱스 기반 분산 좌표 (0~1 normalized range)
    keypoints = np.zeros((133, 3), dtype=np.float32)
    for i in range(133):
        keypoints[i, 0] = (i % 10) * 0.1        # x
        keypoints[i, 1] = (i // 10) * 0.1       # y
        keypoints[i, 2] = 0.0                   # z (2D path, depth=0)

    # score 초기화
    if visible_indices is not None:
        # visible_indices 모드: 지정 인덱스 score=1.0, 나머지 0.0
        score_arr = np.zeros(133, dtype=np.float32)
        for idx in visible_indices:
            if 0 <= idx < 133:
                score_arr[idx] = 1.0
    elif scores is None:
        score_arr = np.full(133, 0.9, dtype=np.float32)
    elif isinstance(scores, (int, float)):
        score_arr = np.full(133, float(scores), dtype=np.float32)
    else:
        arr = np.asarray(scores, dtype=np.float32)
        if arr.shape != (133,):
            raise ValueError(f"scores 배열 shape 이 (133,) 이어야 함, got {arr.shape}")
        score_arr = arr

    return keypoints, score_arr
