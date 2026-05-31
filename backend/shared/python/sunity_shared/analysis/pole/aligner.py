"""폴 축 좌표계 정렬 — scipy Rotation.align_vectors (D-12).

Phase 1 결정 박제:
  D-12: raw + pole-aligned 둘 다 PoseFrame 에 저장.
        PoleAxisAligner 가 폴 축 → Z 축 회전행렬 산출.
  REVIEWS H-2: scipy module-level import 금지.
               compute_alignment_matrix 함수 내부에서만 lazy import.
               Lambda module import 는 scipy 부재 환경에서도 성공해야 함.

scipy.spatial.transform.Rotation.align_vectors edge case 처리:
  - pole_axis ≈ [0,0,1]: 회전 무필요 → identity
  - pole_axis ≈ [0,0,-1]: 180° 회전 → scipy 가 안전하게 처리
  RESEARCH §Pattern 5 + Code Example 3 참조.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..pose_frame import Keypoint3D, Keypoint3DAligned  # noqa: F401

# 수직 = Z+ 방향 (PoleAxisAligner target axis)
TARGET_AXIS = np.array([0.0, 0.0, 1.0])


def compute_alignment_matrix(
    pole_axis_direction: tuple[float, float, float] | np.ndarray,
) -> np.ndarray:
    """폴 축 방향 → Z 축 정렬 회전행렬 (3×3).

    H-2 박제: scipy 는 이 함수 내부에서만 lazy import.
    zero vector 입력 시 ValueError.
    scipy.spatial.transform.Rotation.align_vectors 사용 (edge case 처리됨).

    Args:
        pole_axis_direction: 폴 축 단위 벡터 (또는 정규화 전 벡터).
            zero vector 는 ValueError.

    Returns:
        (3, 3) float64 ndarray — 회전행렬 R.
        R @ pole_axis_direction ≈ [0, 0, 1].
        det(R) ≈ ±1.
    """
    # H-2 박제: scipy module-level import 금지 — 함수 내부 lazy import
    from scipy.spatial.transform import Rotation  # noqa: PLC0415

    pole = np.array(pole_axis_direction, dtype=np.float64)

    norm = float(np.linalg.norm(pole))
    if norm < 1e-9:
        raise ValueError(
            f"pole_axis_direction 은 zero vector 가 될 수 없음 — norm={norm:.2e}"
        )
    pole = pole / norm

    rot, _rssd = Rotation.align_vectors([TARGET_AXIS], [pole])
    return rot.as_matrix()  # (3, 3)


def apply_alignment(
    keypoints: dict,
    R: np.ndarray,
) -> dict:
    """모든 키포인트에 회전행렬 R 적용 → pole-aligned 좌표 dict.

    scipy 의존 없음 — numpy 행렬 곱만 사용.
    keypoints 는 dict[str, Keypoint3D] 또는 dict[str, dict] 모두 허용 (duck-typed).
    Keypoint3DAligned import 는 함수 내부에서 lazy.

    입력 key set = 출력 key set.

    Args:
        keypoints: {joint_name: obj_with_x_y_z_attrs} 또는 {joint_name: {'x':..., 'y':..., 'z':...}}.
        R: (3, 3) 회전행렬.

    Returns:
        {joint_name: Keypoint3DAligned(x, y, z)} — 회전 적용된 좌표.
    """
    # H-2 박제: Keypoint3DAligned import 도 함수 내부에서 lazy
    from ..pose_frame import Keypoint3DAligned  # noqa: PLC0415

    aligned: dict = {}
    for name, kp in keypoints.items():
        # duck-typed: Keypoint3D 데이터클래스 또는 dict 모두 허용
        if isinstance(kp, dict):
            v = np.array([kp["x"], kp["y"], kp["z"]], dtype=np.float64)
        else:
            v = np.array([kp.x, kp.y, kp.z], dtype=np.float64)

        v_aligned = R @ v
        aligned[name] = Keypoint3DAligned(
            x=float(v_aligned[0]),
            y=float(v_aligned[1]),
            z=float(v_aligned[2]),
        )

    return aligned
