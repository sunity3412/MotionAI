"""Stage 3' 12 virtual camera pyrender EGL headless render — Spike 002b VALIDATED-SKELETON 이관.

PYOPENGL_PLATFORM=egl 는 이 모듈 import 즉시 os.environ.setdefault 로 설정됨 —
반드시 import pyrender 보다 먼저 실행되어야 한다 (RESEARCH Pitfall 3 박제).
Mac local 개발 환경(PYRENDER_AVAILABLE=False)에서는 dummy 128-gray 12장 반환 —
분석 흐름 차단 0 (D-07 graceful degrade 계약).

License-clear stack: pyrender (MIT) + trimesh (MIT) + numpy (BSD).
12 virtual camera = 360° / 12 = 30° 간격 yaw rotation, fixed pitch.

박제 정신:
  · render_12_views_safe(mesh, width=256, height=256) → list[np.ndarray] 12장.
  · renderer.delete() try/finally 명시 (GPU 메모리 관리, RESEARCH Pattern 5).
  · PYRENDER_AVAILABLE False 시 dummy 회색 이미지 반환 — Mac local 개발 차단 0.

Spike 002b 출처: .planning/spikes/002b-cylindrical-mesh-virtual-render/render.py
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass

import numpy as np
import trimesh

# pyrender 는 OpenGL 의존이라 RunPod GPU 환경 권장.
# EGL 초기화 순서 박제 — import pyrender 보다 먼저 (RESEARCH Pitfall 3).
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

try:
    import pyrender  # type: ignore[import-not-found]
    PYRENDER_AVAILABLE = True
    _pyrender_err: Exception | None = None
except (ImportError, OSError) as e:  # noqa: BLE001 — Mac local graceful
    PYRENDER_AVAILABLE = False
    _pyrender_err = e


@dataclass
class VirtualCamera:
    yaw_deg: float
    pitch_deg: float
    distance: float       # mesh center 로부터 거리 (m)


def make_12_camera_set(
    distance: float = 3.0,
    pitch_deg: float = 0.0,
) -> list[VirtualCamera]:
    """yaw 12 등분 (30°). pitch 0° = mesh 와 동일 높이."""
    return [
        VirtualCamera(yaw_deg=i * 30.0, pitch_deg=pitch_deg, distance=distance)
        for i in range(12)
    ]


def _camera_pose(camera: VirtualCamera, target: np.ndarray) -> np.ndarray:
    """pyrender 의 4x4 camera pose (camera-to-world)."""
    yaw = math.radians(camera.yaw_deg)
    pitch = math.radians(camera.pitch_deg)
    eye = target + np.array([
        camera.distance * math.cos(pitch) * math.sin(yaw),
        camera.distance * math.sin(pitch),
        camera.distance * math.cos(pitch) * math.cos(yaw),
    ])
    # look-at
    forward = (target - eye)
    forward = forward / np.linalg.norm(forward)
    up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)
    up = np.cross(right, forward)
    pose = np.eye(4)
    pose[:3, 0] = right
    pose[:3, 1] = up
    pose[:3, 2] = -forward    # pyrender = -z forward
    pose[:3, 3] = eye
    return pose


def render_12_views_safe(
    mesh: trimesh.Trimesh,
    width: int = 256,
    height: int = 256,
) -> list[np.ndarray]:
    """12 yaw view RGB image list 반환.

    PYRENDER_AVAILABLE=False (Mac local 환경) → dummy 회색 이미지 12장 반환
    (분석 흐름 차단 0, D-07 graceful degrade).
    PYRENDER_AVAILABLE=True (RunPod EGL) → pyrender.OffscreenRenderer 로 실제
    12 view 렌더 + renderer.delete() try/finally 명시 (GPU 메모리 관리).

    Returns:
        list[np.ndarray] 길이 12, 각 (H, W, 3) uint8.
    """
    if not PYRENDER_AVAILABLE:
        # RunPod GPU 환경 필요 박제 — Mac local 단계에서는 dummy 반환.
        return [
            np.full((height, width, 3), fill_value=128 + i * 10, dtype=np.uint8)
            for i in range(12)
        ]

    py_mesh = pyrender.Mesh.from_trimesh(mesh, smooth=False)
    scene = pyrender.Scene(ambient_light=[0.3, 0.3, 0.3])
    scene.add(py_mesh)

    target = mesh.centroid
    cameras = make_12_camera_set(distance=3.0)
    images: list[np.ndarray] = []

    renderer = pyrender.OffscreenRenderer(viewport_width=width, viewport_height=height)
    try:
        for cam in cameras:
            pose = _camera_pose(cam, target)
            perspective = pyrender.PerspectiveCamera(yfov=math.radians(50.0))
            cam_node = scene.add(perspective, pose=pose)
            light = pyrender.DirectionalLight(color=np.ones(3), intensity=2.0)
            light_node = scene.add(light, pose=pose)
            color, _ = renderer.render(scene)
            images.append(color.copy())
            scene.remove_node(cam_node)
            scene.remove_node(light_node)
    finally:
        renderer.delete()

    return images


__all__ = [
    "PYRENDER_AVAILABLE",
    "VirtualCamera",
    "make_12_camera_set",
    "render_12_views_safe",
]
