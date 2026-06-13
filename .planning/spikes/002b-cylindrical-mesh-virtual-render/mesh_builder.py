"""RTMW 3D keypoint → cylindrical humanoid mesh (commercial-friendly path).

Spike 002b 의 핵심 — SMPL-X 의존 제거 박제.

License-clear stack: trimesh (MIT) + numpy (BSD) + RTMW (Apache-2.0).
SMPL-X (Max-Planck research-only) / MagicMan weight (transitive 비상업) / Higgsfield
ToS §5.1(iii) 충돌 모두 회피.

Approach:
  - RTMW 33 wholebody / COCO-17 keypoint → 13 body segment 박제
  - 각 segment = trimesh.creation.cylinder (radius/height 인체 비율 박제)
  - segment 위치/회전 = 인접 joint vector 로 계산
  - 합쳐서 single trimesh 출력
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import trimesh


# ── RTMW COCO-17 joint index ─────────────────────────────────────────────────
NOSE = 0
EYE_L, EYE_R = 1, 2
EAR_L, EAR_R = 3, 4
SHO_L, SHO_R = 5, 6
ELB_L, ELB_R = 7, 8
WRI_L, WRI_R = 9, 10
HIP_L, HIP_R = 11, 12
KNE_L, KNE_R = 13, 14
ANK_L, ANK_R = 15, 16


# ── Segment 박제 (13 body part) ──────────────────────────────────────────────
@dataclass(frozen=True)
class Segment:
    name: str
    joint_a: int                  # 시작 joint
    joint_b: int                  # 끝 joint
    radius: float                 # cylinder radius (m, 평균 성인 기준)


SEGMENTS: list[Segment] = [
    # head : ear_center → nose 방향 박제 (간단화)
    Segment("head", EYE_L, NOSE, radius=0.10),
    # torso : 어깨 중심 → 골반 중심 (별도 처리)
    Segment("torso", SHO_L, HIP_L, radius=0.15),  # placeholder, _add_torso 에서 실제 처리
    # arms
    Segment("upper_arm_l", SHO_L, ELB_L, radius=0.05),
    Segment("lower_arm_l", ELB_L, WRI_L, radius=0.04),
    Segment("upper_arm_r", SHO_R, ELB_R, radius=0.05),
    Segment("lower_arm_r", ELB_R, WRI_R, radius=0.04),
    # legs
    Segment("upper_leg_l", HIP_L, KNE_L, radius=0.08),
    Segment("lower_leg_l", KNE_L, ANK_L, radius=0.06),
    Segment("upper_leg_r", HIP_R, KNE_R, radius=0.08),
    Segment("lower_leg_r", KNE_R, ANK_R, radius=0.06),
]


def _cylinder_between(
    a: np.ndarray,
    b: np.ndarray,
    radius: float,
    segments_circle: int = 12,
) -> trimesh.Trimesh:
    """두 점 사이를 잇는 cylinder mesh 생성."""
    direction = b - a
    length = float(np.linalg.norm(direction))
    if length < 1e-6:
        return trimesh.Trimesh()
    midpoint = (a + b) / 2
    # default cylinder는 z 축 정렬
    cyl = trimesh.creation.cylinder(radius=radius, height=length, sections=segments_circle)
    # z 축 → direction 으로 회전
    z = np.array([0.0, 0.0, 1.0])
    direction_n = direction / length
    axis = np.cross(z, direction_n)
    axis_norm = np.linalg.norm(axis)
    if axis_norm > 1e-6:
        axis = axis / axis_norm
        angle = float(np.arccos(np.clip(np.dot(z, direction_n), -1.0, 1.0)))
        rot = trimesh.transformations.rotation_matrix(angle, axis)
        cyl.apply_transform(rot)
    cyl.apply_translation(midpoint)
    return cyl


def build_humanoid_mesh(joints: np.ndarray) -> trimesh.Trimesh:
    """
    (17, 3) RTMW COCO-17 3D joint → cylindrical humanoid mesh 박제.

    Returns:
        trimesh.Trimesh: 합쳐진 single mesh
    """
    if joints.shape != (17, 3):
        raise ValueError(f"joints shape (17,3) 필요, got {joints.shape}")

    parts: list[trimesh.Trimesh] = []

    # head — ear center 기준 sphere 박제 (cylinder 보다 자연스러움)
    ear_center = (joints[EAR_L] + joints[EAR_R]) / 2
    head_top = ear_center + np.array([0.0, 0.18, 0.0])
    parts.append(_cylinder_between(ear_center, head_top, radius=0.10))

    # torso — 어깨 중심 → 골반 중심 (대형 cylinder)
    sho_center = (joints[SHO_L] + joints[SHO_R]) / 2
    hip_center = (joints[HIP_L] + joints[HIP_R]) / 2
    parts.append(_cylinder_between(sho_center, hip_center, radius=0.15))

    # 나머지 segment
    for seg in SEGMENTS:
        if seg.name in ("head", "torso"):
            continue  # 위에서 박제 완료
        cyl = _cylinder_between(joints[seg.joint_a], joints[seg.joint_b], radius=seg.radius)
        parts.append(cyl)

    # joint sphere — 어깨/팔꿈치 등 joint marker (시각화 도움)
    for j in [SHO_L, SHO_R, ELB_L, ELB_R, HIP_L, HIP_R, KNE_L, KNE_R]:
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=0.06)
        sphere.apply_translation(joints[j])
        parts.append(sphere)

    combined = trimesh.util.concatenate(parts)
    return combined
