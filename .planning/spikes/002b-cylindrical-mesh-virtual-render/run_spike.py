"""Spike 002b 실행 entry — synthetic RTMW joint 으로 mesh + 12 view 박제.

local 환경 (GPU 없음): mesh 박제 + render dummy (PYRENDER_AVAILABLE=False) 검증.
RunPod GPU 환경: render 실제 12 view image 저장 → RTMW 재추론 호출 (별도 task).
"""
from __future__ import annotations

import json
import os

import numpy as np

from mesh_builder import build_humanoid_mesh
from render import PYRENDER_AVAILABLE, render_12_views


def make_synthetic_joints() -> np.ndarray:
    """
    정은지 je-03 (에어쇼 스플릿) 시뮬레이션 — 양 다리 거의 일직선 (split 180°).
    Spike 001 의 fixture 한계 (V-shape 106°) 보강 박제.
    """
    joints = np.zeros((17, 3))
    # head
    joints[0] = [0.0, 1.7, 0.0]      # nose
    joints[1] = [-0.04, 1.72, 0.0]   # eye_l
    joints[2] = [+0.04, 1.72, 0.0]   # eye_r
    joints[3] = [-0.08, 1.70, 0.0]   # ear_l
    joints[4] = [+0.08, 1.70, 0.0]   # ear_r
    # shoulders
    joints[5] = [-0.20, 1.50, 0.0]
    joints[6] = [+0.20, 1.50, 0.0]
    # elbows + wrists (옆으로 펼침)
    joints[7] = [-0.45, 1.50, 0.0]
    joints[8] = [+0.45, 1.50, 0.0]
    joints[9] = [-0.70, 1.50, 0.0]
    joints[10] = [+0.70, 1.50, 0.0]
    # hips
    joints[11] = [-0.10, 1.00, 0.0]
    joints[12] = [+0.10, 1.00, 0.0]
    # knees — split 180° 박제 = 양 다리 horizontal 펼침
    joints[13] = [-0.50, 1.00, 0.0]
    joints[14] = [+0.50, 1.00, 0.0]
    # ankles — knees 연장
    joints[15] = [-0.90, 1.00, 0.0]
    joints[16] = [+0.90, 1.00, 0.0]
    return joints


def smoke_test() -> None:
    print("=" * 60)
    print("Spike 002b: cylindrical-mesh-virtual-render smoke test")
    print(f"  pyrender available: {PYRENDER_AVAILABLE}")
    print("=" * 60)

    joints = make_synthetic_joints()

    print("\n[1/3] RTMW COCO-17 joint fixture 박제")
    print(f"  shape={joints.shape}, range=[{joints.min():.2f}, {joints.max():.2f}]")
    # split angle 정합 확인
    hip_l, hip_r = joints[11], joints[12]
    knee_l, knee_r = joints[13], joints[14]
    v_l = knee_l - hip_l
    v_r = knee_r - hip_r
    cos_t = np.dot(v_l, v_r) / (np.linalg.norm(v_l) * np.linalg.norm(v_r) + 1e-9)
    import math
    split_deg = math.degrees(math.acos(np.clip(cos_t, -1.0, 1.0)))
    print(f"  split angle = {split_deg:.1f}° (IPSF target 180°, tolerance ±20°)")
    pass_ipsf = abs(split_deg - 180.0) <= 20.0
    print(f"  IPSF Page 19 Fully Extended Split: {'PASS' if pass_ipsf else 'FAIL'}")

    print("\n[2/3] Cylindrical humanoid mesh 빌드")
    mesh = build_humanoid_mesh(joints)
    print(f"  vertices = {len(mesh.vertices)}")
    print(f"  faces    = {len(mesh.faces)}")
    print(f"  bounds   = {mesh.bounds.tolist()}")
    print(f"  watertight = {mesh.is_watertight}")

    # mesh 저장 (RunPod 위임 시 input)
    mesh.export("humanoid.obj")
    print("  ✓ humanoid.obj 박제")

    print("\n[3/3] 12 virtual camera render")
    images = render_12_views(mesh, width=256, height=256)
    print(f"  views = {len(images)}, shape per view = {images[0].shape}")

    # 박제 metadata
    report = {
        "spike": "002b-cylindrical-mesh-virtual-render",
        "license_stack": {
            "trimesh": "MIT",
            "pyrender": "MIT",
            "numpy": "BSD",
            "rtmw_input": "Apache-2.0 (Sunity 운영)",
            "smpl_x_dependency": "REMOVED ✓",
        },
        "fixture": {
            "split_angle_deg": split_deg,
            "ipsf_page19_pass": bool(pass_ipsf),
        },
        "mesh": {
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "watertight": bool(mesh.is_watertight),
        },
        "render": {
            "pyrender_available": PYRENDER_AVAILABLE,
            "n_views": len(images),
            "view_resolution": list(images[0].shape),
            "note": "PYRENDER_AVAILABLE=False 시 dummy gradient image. RunPod GPU 위임 필요.",
        },
    }
    with open("spike_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\n✓ spike_report.json 박제")


if __name__ == "__main__":
    smoke_test()
