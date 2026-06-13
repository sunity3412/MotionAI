"""Cylindrical humanoid mesh → 12 virtual camera render.

License-clear stack: pyrender (MIT) + trimesh (MIT) + numpy (BSD).

12 virtual camera = 360° / 12 = 30° 간격 yaw rotation, fixed pitch.
RTMW 재추론 입력으로 사용할 silhouette / colorize image 출력.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import trimesh

# pyrender는 OpenGL 의존이라 RunPod GPU 환경 권장.
# spike skeleton 단계에서는 headless EGL backend 박제.
try:
    import os as _os
    _os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
    import pyrender
    PYRENDER_AVAILABLE = True
except (ImportError, OSError) as e:
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
    forward /= np.linalg.norm(forward)
    up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    pose = np.eye(4)
    pose[:3, 0] = right
    pose[:3, 1] = up
    pose[:3, 2] = -forward    # pyrender = -z forward
    pose[:3, 3] = eye
    return pose


def render_12_views(
    mesh: trimesh.Trimesh,
    width: int = 256,
    height: int = 256,
) -> list[np.ndarray]:
    """
    Returns: 12 view 의 RGB image list. shape (H, W, 3) uint8.
    """
    if not PYRENDER_AVAILABLE:
        # RunPod GPU 환경 필요 박제 — local skeleton 단계에서는 dummy 반환
        return [
            np.full((height, width, 3), fill_value=128 + i * 10, dtype=np.uint8)
            for i in range(12)
        ]

    py_mesh = pyrender.Mesh.from_trimesh(mesh, smooth=False)
    scene = pyrender.Scene(ambient_light=[0.3, 0.3, 0.3])
    scene.add(py_mesh)

    target = mesh.centroid
    cameras = make_12_camera_set(distance=3.0)
    images = []

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
