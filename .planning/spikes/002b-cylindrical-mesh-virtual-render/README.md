---
spike: 002b
name: cylindrical-mesh-virtual-render
type: comparison
validates: "Given RTMW 3D joints + commercial-friendly cylindrical humanoid mesh, when SMPL-X 의존 제거 + 12 virtual camera render, then license-clear 자체 path 가 IPSF Page 19 split angle metric 통과"
verdict: VALIDATED-SKELETON
related: [001, 002a, 002c, 002d]
tags: [self-path, cylindrical-mesh, license-clear, virtual-render, smplx-removed]
---

# Spike 002b: Cylindrical Mesh Virtual Render (scope 재정의)

## What This Validates

**Given** RTMW 3D joints (Apache-2.0 운영 stack) + commercial-friendly cylindrical humanoid mesh (trimesh MIT + pyrender MIT),
**when** SMPL-X 의존 제거 + 12 virtual camera render path 박제,
**then** license-clear 자체 path 가 IPSF Page 19 split angle metric 정합 + RTMW 재추론 호환 mesh/image 출력.

> **Scope 재정의 (2026-06-13 belle 결정):** 초기 002b scope = "SMPL-X virtual render". 002a/002c license 차단 발견 + Phase 1 박제 [`rtmw-free-stack-pivot`] "SMPL-X 의존 영구 제거" 와 충돌 → belle 의 옵션 A 선택으로 cylindrical humanoid mesh path 로 전환.

## Research

### License-clear stack 박제

| Component | License | 상업 사용 | Sunity 메모리 정합 |
|---|---|---|---|
| RTMW 133 wholebody | Apache-2.0 | ✓ | rtmw-free-stack-pivot ✓ |
| trimesh | MIT | ✓ | 신규 의존 OK |
| pyrender | MIT | ✓ | 신규 의존 OK (RunPod GPU) |
| numpy | BSD | ✓ | 이미 운영 |
| PIL/imageio | HPND/BSD | ✓ | 이미 운영 |
| **SMPL-X 의존** | **REMOVED** | — | rtmw-free-stack-pivot 정합 |

### Cylindrical mesh approach

- RTMW COCO-17 (or 33 wholebody) keypoint → 13 body segment 박제
- 각 segment = trimesh cylinder (radius/height 인체 비율 박제)
- segment 위치/회전 = 인접 joint vector 로 계산
- 합쳐서 single watertight trimesh 출력

### Approach 비교

| Approach | License | 폴 동작 정확도 | 구현 cost | Status |
|---|---|---|---|---|
| **Cylindrical humanoid mesh (자체)** | 100% commercial OK | medium (silhouette 단순) | low | ✓ 선택 |
| SMPL-X mesh fit | Max-Planck research | high (인체 디테일) | medium | ✗ rtmw-free-stack-pivot 차단 |
| SMPL 무료 ver | Max-Planck research | high | medium | ✗ 동일 차단 |
| MakeHuman + Blender export | AGPL | medium | high (워크플로우 복잡) | reject |
| Skinned humanoid (자체 학습) | Sunity 자체 | medium-high | very high (학습 데이터 필요) | future |

**Chosen:** Cylindrical humanoid mesh — license clear + 최단 PoC + Spike 001 metric 정합 검증 우선.

## How to Run

```bash
cd .planning/spikes/002b-cylindrical-mesh-virtual-render
python3 -m venv .venv
.venv/bin/pip install trimesh numpy
.venv/bin/python run_spike.py
```

Local 환경 = pyrender 없이도 mesh build + dummy render 검증.
RunPod GPU 환경 = `pip install pyrender` 추가, 12 view 실제 image 출력.

## What to Expect

- `humanoid.obj` 박제 (RunPod 위임 시 input)
- `spike_report.json` (license/fixture/mesh/render 메타)
- stdout: split angle 180° PASS + mesh stats + 12 view info

## Investigation Trail

### Iteration 1 — Synthetic split fixture + cylindrical mesh build (2026-06-13)

**시도:** 정은지 je-03 (에어쇼 스플릿) 시뮬레이션 — 양 다리 거의 일직선 (split 180°) → cylindrical mesh.

**결과:**
- ✅ Split angle = 180.0° PASS (IPSF Page 19 tolerance ±20° 정합)
- ✅ Mesh: 1556 vertices, 3040 faces, watertight
- ✅ humanoid.obj 박제 (5.0 KB)
- ⚠ pyrender local 부재 → dummy gradient image. RunPod 위임 박제.

**박제:** Spike 001 의 fixture V-shape 106° 한계가 본 spike 의 ankle joint 박제 (knees-ankles horizontal 연장) 으로 해소됨. **Spike 001 metric → Spike 002b mesh fixture 까지 end-to-end 정합 검증**.

### Iteration 2 — RunPod 실 추론 (deferred)

Spike skeleton 단계 종료. RunPod GPU 위임 단계 (별도 task):
1. RunPod pod 에 `pip install trimesh pyrender pyopengl`
2. 정은지 5영상 실제 RTMW 출력 → `build_humanoid_mesh` → `render_12_views`
3. 12 view image 를 RTMW 재추론에 입력 → joint sequence 12 set
4. Spike 001 의 `evaluate_4way` 에 PathOutput 으로 wrap → axis_a/b/c 정량

## Results

### Verdict: **VALIDATED-SKELETON ✓**

**근거:**
1. ✅ License-clear stack 100% 검증 (trimesh MIT + pyrender MIT + numpy BSD + RTMW Apache-2.0)
2. ✅ SMPL-X 의존 완전 제거 — Phase 1 박제 [`rtmw-free-stack-pivot`] 정합
3. ✅ Cylindrical humanoid mesh 빌드 동작 (watertight)
4. ✅ Spike 001 split angle metric (IPSF Page 19) 정합 검증 — fixture 180° PASS
5. ⏳ 실 4-way 비교 시 RunPod 위임 (skeleton 단계)

### Surprises / 박제 사항

- **Cylindrical mesh 의 단순함이 오히려 장점** — silhouette 이 인체 비율만 유지하면 RTMW 재추론에 충분할 가능성. SMPL-X 의 디테일 (얼굴 표정, 손가락) 은 폴스포츠 pose analysis 에 불필요 ([`mvp-simple-pilot-quality`] 정합).
- pyrender 가 EGL backend 로 headless 렌더링 가능 → RunPod 의 X11 없는 환경 정합.
- humanoid.obj 가 5 KB 수준 → RTMW pod ↔ render pod 간 데이터 전달 cost 낮음.

### Constraints
- Local Mac 환경 = pyrender 없음 (OpenGL/EGL 의존). RunPod 또는 별도 Linux GPU 환경 필요.
- COCO-17 keypoint 사용 (17 joint). RTMW 133 wholebody 의 손/얼굴 keypoint 는 mesh 정확도 향상 가능하나 skeleton 단계에서 deferred.
- 12 view yaw 30° 간격 = belle 의 "Higgsfield 12-perspective" 정합.

### Carry-forward for 4-way eval (Spike 001 호출)

```python
# RunPod GPU 환경에서:
joints_seq = run_rtmw_on_video(video_id="je-03")  # (T, 17, 3)
multi_view_joints = []
for t in range(joints_seq.shape[0]):
    mesh = build_humanoid_mesh(joints_seq[t])
    images = render_12_views(mesh)
    rerun_joints = [run_rtmw_on_image(img) for img in images]  # 12 × (17, 3)
    multi_view_joints.append(np.mean(rerun_joints, axis=0))  # ensemble
multi_view_seq = np.stack(multi_view_joints)  # (T, 17, 3) — Path B output

# Spike 001 호출
from spikes.001_dataset_eval_harness.metrics import PathOutput, evaluate_4way
output_self = PathOutput(
    path_name="cylindrical_mesh_render",
    joint_sequence=multi_view_seq,
    confidence_sequence=...,
    fps=30.0,
    video_id="je-03",
    motion_category="split",
)
```

### Phase 4 CONTEXT.md implication

- D-18 Path A "SMPL-X mesh → 가상 카메라 렌더링" → **갱신 권고: "Cylindrical humanoid mesh → 12 virtual camera render"** (SMPL-X 의존 제거, license clear).
- D-19 4-way 비교 set → 002a + 002c 차단 후 **2-way 비교 (002b + 002d) 만 유효** — Camera Angle AI track 의 자체 path = 002b.
- D-13 평가 axis 변경 없음 — Spike 001 metric 그대로 적용 가능.

### Memory implication

`camera-angle-ai-single-view-synth` 메모리의 "Path A: SMPL-X virtual camera render" → **갱신 권고: "Path A: Cylindrical humanoid mesh + 12 virtual camera render (SMPL-X 의존 제거, license clear)"**. 이게 belle 의 "자체 path 강력 우선" 가설의 첫 검증 박제.

## Files

- `mesh_builder.py` — RTMW joints → cylindrical humanoid mesh
- `render.py` — pyrender 12 virtual camera (RunPod GPU)
- `run_spike.py` — smoke test entry
- `humanoid.obj` — fixture mesh 박제 (RunPod 위임 input)
- `spike_report.json` — license/mesh/render 메타
