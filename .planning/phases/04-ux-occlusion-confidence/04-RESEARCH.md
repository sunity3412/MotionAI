# Phase 4: Camera Angle AI — Research

**Researched:** 2026-06-13
**Domain:** Occlusion confidence gate + AI virtual view synthesis + 3D frontend viewer
**Confidence:** HIGH (spike 6건 완료, 코드베이스 직접 검증)

> ⚠ SUPERSEDED CONTRACT NOTE (2026-06-13, 2차 리뷰 HIGH-3): 본 문서의 adapter 예시 중 tuple/None 반환 + `reshapeJoints3d(angles...)` 패턴은 **폐기**. 최신 계약 = `SynthesisResult(status=applied|partial|skipped|failed)` (04-01) + `reshapePose3dData(result.joints3d...)` (04-02) + `identify_occlusion_targets` (이름 통일) + joints3d source = `keypoints_4ch[:,:,:3]`. 충돌 시 **04-DIRECT-REVIEW-RESPONSE.md + 04-01 PLAN 이 우선**한다.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Phase 4 = Camera Angle AI redesign. 사용자에게 다중 시점 직접 업로드 요구 영구 제거.
- D-02: 사용자 UX = 1 영상 업로드 → 결과 화면. AI 합성은 백엔드에서 사용자 무관하게 발생.
- D-03: 조건부 + 부분 합성. 영상 전체 AI 합성 X.
- D-04: 트리거 후보 4가지 — (a) RTMW score 임계값 미달 phase (b) `occlusion_high_in_phase` warning phase (c) scene_finder `occlusion_severe` / `camera_angle_problematic` Finding (d) 도메인 후보 (회전/거꾸로 매달림/측면)
- D-05: MVP = 완전 블랙박스. 사용자에게 AI 보완 발생 사실 미노출.
- D-06: "AI 가 보완했어요" 명시 transparency = v2 후속.
- D-07: 합성 실패 → graceful degrade. 1차 RTMW 결과로 계속 진행.
- D-08: 합성 실패 시 결과 화면에 정확도 제한 표기 필수 (`ai_synthesis_failed` 또는 유사 신규 warning code).
- D-09: Phase 4 파이프라인 완성 후 정은지 5영상 자동 재처리.
- D-10: 정은지 5영상 재처리 시 AI 합성으로 Phase 17 G4 occlusion FP + Phase 8.1 axis severity 해결 여부 동시 검증.
- D-17: Higgsfield Angles = production BLOCKED (Spike 002a 확정).
- D-18: Primary = Gemini Vision view reasoning (Spike 003), Secondary = Cylindrical mesh (Spike 002b), Baseline = RTMW mirror.
- D-19: 003/002b/002d 3개 path 유효, 002a/002c 차단.
- D-20: 상업 허용 스택 = Gemini API (Apache-2.0 SDK) + trimesh (MIT) + pyrender (MIT) + RTMW (Apache-2.0). 차단 = SMPL-X/SV3D/DUSt3R/MASt3R/MagicMan/Higgsfield.
- D-21: IPSF Page 19 "split angle must remain the same from all angles/perspectives" = Camera Angle AI 의 직접 IPSF 근거.
- D-22: IPSF Page 10/94/106 occlusion 감점 -0.5pt/회. 현 baseline 시뮬 -7.60pts/video.
- D-24~D-28: Gemini Omni Vertex GA 후 PRIMARY 후보, mid-late June 2026 윈도우. 비용 $2-6/10초로 조건부 트리거 전용.
- D-29~D-32: Decoupling 4-stage 아키텍처. Stage 1 = Gemini Vision reasoning, Stage 2 = RTMW, Stage 3 = R3F frontend viewer (Wave 2), Stage 3' = cylindrical mesh backend (Wave 3), Stage 4 = Omni plug-in stub (Wave 4).

### Claude's Discretion
- 구체 confidence 임계값 (RTMW score cutoff %), 부분 합성 윈도우 길이 (프레임 수), 캐싱 키 전략, 비용 dashboard 구체화.

### Deferred Ideas (OUT OF SCOPE)
- 다중 시점 직접 업로드 UX (영구 제거)
- "AI 가 보완했어요" 명시 transparency (v2)
- 스피닝 폴 핸들링 (Phase 1 D-10, v1.5)
- 사선/뒤 시점 합성 (v2)
- 합성 결과 캐싱 + 재사용 (운영 데이터 확보 후)
- 비용 dashboard / 예산 알람 (별도 운영 phase)
- Phase 4.5 원근 왜곡 보정 (D-16: Phase 4 결과 확정 후 진입 결정)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POSE-03 | 사용자가 다중 시점(정면+측면) 영상 업로드 + 키포인트 confidence 임계값 미만 프레임 "추정" 표기 + occlusion 경고 | 다중 시점 UX 는 Camera Angle AI 로 supersede. Confidence 게이트(D-04), 추정 표기(D-05/D-08), warning code(D-08) 로 등가 충족. |
</phase_requirements>

---

## Summary

Phase 4 는 6개 spike 가 완료된 상태에서 진입하는 plan-phase 다. 사용자는 여전히 1 영상만 올리고, 백엔드가 Decoupling 4-stage 아키텍처로 AI 가상 다각도 보완을 수행한다. "다중 시점 직접 업로드" 는 영구 제거됐으며, 그 역할을 Phase 4 파이프라인이 투명하게 대체한다.

Spike 결과 확정된 두 가지 primary path 는: (1) Gemini Vision multimodal view reasoning (Spike 003, 비용 $0.12/video, 의존성 0 추가, Phase 17 통합 위에 바로 얹힘), (2) Cylindrical humanoid mesh + 12 virtual camera + RTMW 재추론 (Spike 002b, trimesh MIT + pyrender MIT, RunPod GPU 위임). 이 둘을 hybrid 로 쓰는 것이 Phase 4 의 구현 core 다.

Wave 2 의 react-three-fiber frontend viewer (Spike 005) 는 "AI 영상 생성 없이" 사용자가 앱에서 손가락으로 3D 자세를 360° 회전해 볼 수 있는 MVP 기능이다. three 0.184 + @react-three/fiber 9.6.1 + expo-three 8.0.0 + expo-gl 56 + @react-three/drei 10.7.7 조합은 Expo SDK 54 + React 19.1 + RN 0.81 + New Architecture 에서 npm 버전 peer deps 확인 결과 호환 가능하나, **실 기기 빌드 검증이 Wave 2 착수 전 필수**다.

**Primary recommendation:** Wave 1 부터 Gemini Vision reasoning (Stage 1+2) 통합, Wave 2 에 R3F frontend viewer, Wave 3 에 cylindrical mesh backend 로 순차 진행. 모든 실패 경로는 1차 RTMW 결과 graceful degrade + `ai_synthesis_failed` warning 으로 처리.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Confidence 게이트 (RTMW score 미달 감지) | API / Backend (Lambda/RunPod) | — | RTMW score 는 서버사이드 추론 결과. 앱에는 숫자만 전달. |
| Gemini Vision view reasoning (Stage 1) | API / Backend (RunPod) | — | GPU Pod 에서 Gemini API 호출. Lambda timeout 회피. |
| Cylindrical mesh render (Stage 3') | GPU / RunPod | — | pyrender EGL headless = X11 없는 RunPod CUDA 환경 전용. |
| AI 합성 트리거 결정 | API / Backend (RunPod _process) | — | `_process` 내부에서 confidence 미달 시 조건부 호출. |
| 합성 결과 ↔ 1차 결과 병합 | API / Backend (shared/analysis) | — | temporal.py 위에서 confidence 가중 병합. |
| 3D Joint sequence 저장 | Database / Firestore | — | flat 저장 (nested-array 금지), reshape 는 앱에서. |
| R3F frontend 3D viewer (Stage 3) | Browser / Client | — | RN JSC 위에서 Three.js + expo-gl 로 GPU 렌더. |
| Firestore schema 갱신 (synthesis 메타) | Database / Firestore | — | flat 저장 + contract.md / models.py / userAnalyses.ts 3-way 갱신. |
| 정확도 제한 표기 (UI, D-08) | Browser / Client | — | warning code 를 앱이 읽어 카피 렌더. |
| Stage 4 Omni plug-in 슬롯 | API / Backend | — | Protocol 인터페이스만 박제. Vertex GA 후 구현체 교체. |

---

## Standard Stack

### Core (Phase 4 신규 의존성)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| three | 0.184.0 | 3D 씬 + 관절 skeleton | MIT, 10.7M downloads/week. R3F + expo-three 모두 의존. |
| @react-three/fiber | 9.6.1 | Three.js React renderer (RN 지원) | MIT, 3.8M downloads/week. Expo SDK ≥43 / React 19 / RN ≥0.78 peer dep 충족. |
| expo-three | 8.0.0 | Expo → Three.js bridge (expo-gl 위) | MIT, 418K downloads/week. expo/expo-three 공식 repo. |
| @react-three/drei | 10.7.7 | OrbitControls + 유틸리티 (선택적 사용) | MIT, 2.8M downloads/week. R3F ecosystem 표준 헬퍼. |
| trimesh | 4.12.2 | RTMW joints → cylindrical humanoid mesh | MIT, PyPI 공식 등재. Spike 002b 검증됨. |
| pyrender | 0.1.45 | 12 virtual camera offscreen render | MIT, PyPI 공식 등재. EGL headless 박제 (render.py `PYOPENGL_PLATFORM=egl`). |

**설치 (app/)**
```bash
npm install three @react-three/fiber expo-three @react-three/drei
# expo-gl 은 Expo SDK 54 에 이미 포함 (별도 install 불필요, 단 expo install 확인)
expo install expo-gl
```

**설치 (RunPod Pod / backend)**
```bash
pip install trimesh pyrender pyopengl
# PyOpenGL-accelerate 는 EGL 환경에서 선택적
```

### Supporting (기존 운영 스택 재사용)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| temporal.py | (운영) | confidence 가중 시간 보간 | 1차 RTMW ↔ 합성 결과 병합 |
| force_signals.py | (운영) | `occlusion_high_in_phase` warning | 트리거 시그널 (D-04.b) |
| gemini/scene_finder.py | (운영) | `occlusion_severe` / `camera_angle_problematic` | 트리거 시그널 (D-04.c) |
| models.py | (운영) | warning code frozenset 카탈로그 | 신규 `ai_synthesis_failed` 추가 위치 |
| firebase (JS SDK v12) | (운영) | Firestore onSnapshot | 앱 실시간 상태 구독 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| expo-gl + R3F | WebView + Three.js | WebView 는 RN 통합 cost + 성능 손실 — 거부됨 (Spike 005) |
| pyrender EGL | OSMesa offscreen | EGL = GPU 직접 사용 → 더 빠름. OSMesa = CPU-only → RunPod GPU 낭비. |
| Gemini reasoning (좌표 추정) | Higgsfield / Magnific 픽셀 합성 | 픽셀 합성은 distortion 승계 + ToS 차단. Reasoning 만이 현실적 (D-17/D-18). |
| trimesh cylindrical | SMPL-X mesh | SMPL-X = 완전 최후의 보류 (belle 명시, $7,300/yr). Cylindrical 로 충분 (폴스포츠 silhouette). |

---

## Package Legitimacy Audit

> slopcheck 설치 권한이 차단됨 — auto mode classifier 정책. 아래는 npm registry + PyPI 직접 검증 결과.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| three | npm | 2012 (13년) | 10.7M/week | github.com/mrdoob/three.js | [ASSUMED-OK] | Approved |
| @react-three/fiber | npm | 2021 (5년) | 3.8M/week | github.com/pmndrs/react-three-fiber | [ASSUMED-OK] | Approved |
| expo-three | npm | 2017 (9년) | 418K/week | github.com/expo/expo-three | [ASSUMED-OK] | Approved (Expo 공식 repo) |
| @react-three/drei | npm | 2020 (6년) | 2.8M/week | github.com/pmndrs/drei | [ASSUMED-OK] | Approved |
| expo-gl | npm | 2018 (8년) | — | github.com/expo/expo | [ASSUMED-OK] | Approved (Expo 공식) |
| trimesh | PyPI | 2012+ | — | github.com/mikedh/trimesh | [ASSUMED-OK] | Approved |
| pyrender | PyPI | 2019 (7년) | — | github.com/mmatl/pyrender | [ASSUMED-OK] | Approved |

postinstall 스크립트: 모든 npm 패키지 postinstall 없음 (직접 확인 완료).

**Packages removed due to slopcheck verdict:** none
**Packages flagged as suspicious:** none

*slopcheck 미실행 — registry 직접 검증으로 대체. 모두 메이저 오픈소스 (5년+ 이상, 공식 GitHub repo 보유). planner 가 첫 install 시 `npm view <pkg> scripts.postinstall` 재확인 권고.*

---

## Architecture Patterns

### System Architecture Diagram

```
[사용자: 스마트폰 영상 1개 업로드]
              │ S3 PUT (presigned URL)
              ▼
         [S3 bucket]
              │ S3 ObjectCreated → SQS
              ▼
    [Lambda: pipeline/app.py]
              │ _delegate_to_runpod()
              ▼
    [RunPod GPU: server.py BackgroundTask]
              │
    ┌─────────▼──────────────────────────────────┐
    │ Stage 1: Gemini Vision reasoning            │
    │  scene_finder (Phase 17 기존) → occlusion_  │
    │  severe / camera_angle_problematic flag     │
    │  + Phase 4 신규 occluded_joint_reasoning    │
    │  (조건부: RTMW confidence 미달 frame 만)     │
    └──────────────┬──────────────────────────────┘
                   │ 추정 좌표 + confidence 반환
    ┌──────────────▼──────────────────────────────┐
    │ Stage 2: RTMW 133 wholebody (운영)           │
    │  1차 분석 → (T, 17, 3) joint sequence        │
    │  + per-joint confidence (rtmw_score)         │
    └──────────────┬──────────────────────────────┘
                   │ confidence 미달 phase 식별
         ┌─────────▼─────────┐
         │ Confidence Gate   │
         │ (D-04 트리거 정책)│
         └────┬──────────┬───┘
    PASS ←────┘          └──── FAIL (occlusion 감지)
    (1차 결과 사용)              │
                         ┌──────▼──────────────────┐
                         │ Stage 3': Cylindrical    │
                         │ mesh + 12 view render    │
                         │ → RTMW 재추론 → 병합     │
                         │ (temporal.py 가중 보간)  │
                         └──────┬──────────────────┘
                                │ 합성 결과 OR graceful
                                │ degrade + ai_synthesis_
                                │ failed warning
                   ┌────────────▼────────────────────┐
                   │ Firestore: users/{uid}/analyses/ │
                   │  {id}  — flat 저장               │
                   │  + aiSynthesisMeta (flat)         │
                   └────────────┬────────────────────┘
                                │ onSnapshot
              ┌─────────────────▼──────────────────┐
              │ 앱 결과 화면                          │
              │  - OctagonScore + coaching 카드       │
              │  - Stage 3: PoseViewer3D (R3F)        │
              │    사용자 손가락 360° 인터랙티브      │
              │  - warning: 정확도 제한 카피 (D-08)   │
              └────────────────────────────────────┘
```

### Recommended Project Structure

```
backend/
├── shared/python/sunity_shared/
│   ├── analysis/
│   │   ├── synthesis/                  # Wave 1/3 신규
│   │   │   ├── __init__.py
│   │   │   ├── interfaces.py           # SynthesisAdapter Protocol
│   │   │   ├── gemini_view_reasoner.py # Stage 1 Gemini 좌표 추정 (Spike 003)
│   │   │   ├── cylindrical_mesh.py     # Stage 3' mesh build (Spike 002b mesh_builder.py 이관)
│   │   │   └── virtual_renderer.py     # Stage 3' render (Spike 002b render.py 이관)
│   │   └── temporal.py                 # 기존 — 병합 로직 재사용
│   ├── gemini/
│   │   └── scene_finder.py             # 기존 — 트리거 시그널 소스
│   └── models.py                       # 신규 warning code 추가
├── functions/pipeline/app.py           # _process wiring 지점
└── runpod_inference/
    ├── server.py                       # BackgroundTask 패턴 유지
    └── requirements.txt                # trimesh, pyrender, pyopengl 추가

app/
└── src/
    ├── components/
    │   └── PoseViewer3D.tsx            # Wave 2 신규 (Spike 005 통합)
    ├── lib/
    │   └── joints.ts                   # (T, 17, 3) flat → reshape 로더
    ├── app/analysis/
    │   └── result.tsx                  # PoseViewer3D 통합 (Wave 2)
    └── types/
        └── analysis.ts                 # aiSynthesisMeta 신규 필드 추가
```

### Pattern 1: Synthesis Adapter Protocol (Phase 1 PoseEngine 패턴 확장)

**What:** AI 합성 API (Gemini, Cylindrical, 미래 Omni) 를 Protocol 기반 어댑터로 격리.
**When to use:** Stage 1 / Stage 3' / Stage 4 모두 동일 인터페이스 사용. 모델 교체 = 구현체 + config flag 만.

```python
# Source: interfaces.py 패턴 (backend/shared/python/sunity_shared/analysis/interfaces.py 정합)
from __future__ import annotations
from typing import Protocol
import numpy as np

class SynthesisAdapter(Protocol):
    """AI 합성 어댑터 인터페이스 — Gemini / Cylindrical / Omni 동일 계약."""

    def synthesize_occluded_joints(
        self,
        joint_sequence: np.ndarray,        # (T, 17, 3) RTMW output
        confidence_sequence: np.ndarray,    # (T, 17) rtmw_score
        occluded_mask: np.ndarray,         # (T, 17) bool — 합성 대상
        scene_findings: dict,              # scene_finder.FindingFlags
    ) -> tuple[np.ndarray, np.ndarray]:    # (T, 17, 3) synthesized, (T, 17) conf
        ...
```

### Pattern 2: Confidence Gate (조건부 트리거)

**What:** RTMW score 임계값 미달 phase 를 핀포인트 식별해 합성 대상만 추출.
**When to use:** `_process` 내에서 전체 joint sequence 산출 후 gate 적용.

```python
# Source: D-04 + temporal.py occluded_mask 패턴 (confidence 가중 판정)
# Claude's Discretion: cutoff 값은 Spike 001 evaluate_4way RunPod 실행 후 확정
# 초기 권장값 (ASSUMED): RTMW confidence < 0.3 = "low" 판정
# force_signals.py LOW_RELIABILITY_PHASE_THRESHOLD (비율 임계) 정합 재사용

from sunity_shared.analysis.temporal import occluded_mask

def identify_occlusion_targets(
    joint_seq: np.ndarray,      # (T, 17, 3)
    confidence_seq: np.ndarray, # (T, 17)
    occlusion_high_phases: list[str],  # force_signals occlusion_high_in_phase
    scene_flags: dict,          # scene_finder FindingFlags
) -> np.ndarray:                # (T, 17) bool synthesis_needed_mask
    """트리거 D-04 (a)(b)(c)(d) 결합 → 합성 필요 mask."""
    mask_a = occluded_mask(joint_seq[..., :2], confidence_seq)  # D-04.a
    mask_b = _phase_occlusion_to_frame_mask(occlusion_high_phases, ...)  # D-04.b
    mask_c = _scene_flag_to_frame_mask(scene_flags, ...)        # D-04.c
    return mask_a | mask_b | mask_c
```

### Pattern 3: Graceful Degrade + Warning Injection

**What:** 합성 API 실패 시 1차 결과 유지 + `ai_synthesis_failed` warning 추가.
**When to use:** 모든 합성 경로의 except 블록.

```python
# Source: D-07/D-08 + body_normalizer.py extra_warnings 패턴 (R8 fix 정합)
import dataclasses

try:
    synth_joints, synth_conf = adapter.synthesize_occluded_joints(...)
    merged_joints, merged_conf = merge_with_temporal(
        primary_joints, primary_conf,
        synth_joints, synth_conf,
        synthesis_mask,
    )
    extra_warnings = []
except Exception:
    log.exception("synthesis failed — graceful degrade")
    merged_joints, merged_conf = primary_joints, primary_conf
    extra_warnings = ["ai_synthesis_failed"]  # models.py frozenset 에 추가 필수

# extra_warnings 주입 (R8 fix 패턴 정합)
profile = dataclasses.replace(profile, extra_warnings=tuple(extra_warnings))
```

### Pattern 4: R3F PoseViewer3D (Wave 2 frontend)

**What:** RTMW (T, 17, 3) joint sequence → Three.js stick figure + 360° 인터랙션.
**When to use:** 결과 화면 `result.tsx` 내 별도 영역.

```typescript
// Source: Spike 005 architecture + @react-three/fiber/native import 필수
// CRITICAL: /native import 경로 사용 (RN 환경 필수)
import { Canvas } from '@react-three/fiber/native';
import { OrbitControls } from '@react-three/drei/native';  // drei RN 지원 확인 필요
import { GLView } from 'expo-gl';  // expo-gl은 expo install expo-gl 로

interface PoseViewer3DProps {
  jointSequence: number[][][];  // (T, 17, 3) flat → 앱에서 reshape
  currentFrame: number;
  ispsFailFrames?: number[];   // IPSF 위반 frame → red highlight
}

export function PoseViewer3D({ jointSequence, currentFrame, ispsFailFrames }: PoseViewer3DProps) {
  // Canvas 는 expo-gl GLView 위에서 동작 (expo-three bridge)
  return (
    <Canvas gl={{ powerPreference: 'high-performance' }}>
      <ambientLight intensity={0.5} />
      <OrbitControls enablePan={false} />
      <SkeletonMesh joints={jointSequence[currentFrame]} failFrames={ispsFailFrames} />
    </Canvas>
  );
}
```

### Pattern 5: pyrender EGL Headless (RunPod GPU — Stage 3')

**What:** X11 없는 RunPod GPU 환경에서 pyrender offscreen render.
**When to use:** cylindrical mesh → 12 view image 생성.

```python
# Source: Spike 002b render.py (직접 박제) — PYOPENGL_PLATFORM=egl 필수
import os
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
import pyrender

renderer = pyrender.OffscreenRenderer(viewport_width=256, viewport_height=256)
# ... render 12 views ...
renderer.delete()  # 반드시 명시적 해제 (GPU 메모리 관리)
```

**RunPod 설치:**
```bash
pip install pyrender pyopengl
# EGL 런타임 (NVIDIA 드라이버에 포함, 별도 apt 불필요 on PyTorch base image)
# 검증: PYOPENGL_PLATFORM=egl python -c "import pyrender; print('EGL OK')"
```

### Anti-Patterns to Avoid

- **Gemini 에 픽셀 좌표 생성 요청:** Gemini 는 joint 좌표 추정(reasoning)만. 이미지 픽셀 합성 X (D-17/D-18, analysis-objectivity 정합).
- **SMPL-X 직접 도입:** belle 명시 완전 최후의 보류. cylindrical + Gemini 99% 미달 + 효과성 입증 시에만.
- **Lambda CPU 에서 Gemini Vision 동기 호출:** Lambda timeout 15s vs Gemini 응답 가변적 → RunPod BackgroundTask 에서만.
- **Firestore 에 (T, J) 중첩 배열 저장:** nested-array 금지 (CLAUDE.md). flat + reshape 패턴 강제.
- **contract.md 한쪽만 갱신:** `aiSynthesisMeta` 신규 필드는 models.py + analysis.ts + contract.md 3-way 동시 갱신 필수.
- **RTMW 3D scoring 행렬 합성 결과로 mutate:** Phase 17 AI-SPEC §1.b D-v2 정합 — DTW/kismam 은 1차 RTMW 원본 사용. 합성 = 시각화 + KeypointReport 만 영향.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 시간축 occlusion 보간 | 커스텀 선형 보간 | `temporal.py temporal_fill` | 이미 구현됨. MAD 기반 outlier 판정 + 가중 이동평균 스무딩 포함. |
| 3D scene + 카메라 | WebGL 직접 코딩 | Three.js + @react-three/fiber | 카메라 행렬, lighting, OrbitControls 모두 제공. |
| Offscreen render | X11 없이 PIL로 렌더 | pyrender EGL backend | GPU 가속 + headless 환경 지원. EGL 1줄 env 설정으로 동작. |
| Gemini API client | urllib JSON 직접 | `sunity_shared.gemini.client.GeminiVisionCall` | Phase 17 에서 이미 구현됨. 에러 처리 + graceful fallback 포함. |
| Warning code 검증 | 임의 문자열 | `BODY_COMPARISON_WARNING_CODES` frozenset + `§9.8` | R8 fix 로 모든 warning 은 frozenset 통과 필수. |
| Mesh build | Three.js MeshBuilder | `trimesh.creation.cylinder` | Cylindrical 비율 계산 + watertight 보장 이미 Spike 002b 에서 구현. |

**Key insight:** temporal.py, scene_finder.py, GeminiVisionCall 이 이미 운영 중이므로 Phase 4 의 "새 코드" 는 어댑터 인터페이스 + wiring 이 전부다. 나머지는 조합.

---

## Common Pitfalls

### Pitfall 1: expo-gl 버전 불일치 (SDK 53 시대의 R3F expo-gl@15 vs R3F 요구 expo-gl@11)

**What goes wrong:** Expo SDK 53 에서 R3F@8 을 쓸 경우 expo-gl@15 vs R3F 요구 @11 불일치로 실 기기 빌드 crash.
**Why it happens:** R3F peerDependency 가 `expo-gl >=11.0` 을 요구하고 SDK 53 = expo-gl@15 인데, 일부 버전 조합에서 네이티브 모듈 초기화 순서 문제 발생.
**How to avoid:** 현재 확인된 안전 조합 = @react-three/fiber 9.6.1 + expo-gl 56.x (Expo SDK 54 기본) + expo-three 8.0.0. `expo install expo-gl` 명령으로 SDK 54 권장 버전 자동 선택.
**Warning signs:** "Could not create GLView context" 런타임 에러, 실 iOS/Android 기기에서 흰 화면.

### Pitfall 2: R3F `/native` import 경로 미사용

**What goes wrong:** `import { Canvas } from '@react-three/fiber'` (web path) 를 RN 에서 사용하면 DOM 의존 코드가 번들에 포함 → 런타임 오류.
**Why it happens:** R3F 패키지가 web/native dual export 구조. RN 에서는 `/native` 경로 필수.
**How to avoid:** 모든 R3F + drei import 를 `/native` 경로로 고정: `from '@react-three/fiber/native'`, `from '@react-three/drei/native'`.
**Warning signs:** "window is not defined", "document is not defined" 런타임 에러.

### Pitfall 3: pyrender EGL 초기화 순서

**What goes wrong:** `import pyrender` 가 `PYOPENGL_PLATFORM` env 설정보다 먼저 실행되면 X11 (없음) 을 시도해 `OSError: [Errno 2] No such file or directory: 'libGL.so.1'` 발생.
**Why it happens:** PyOpenGL 이 import 시점에 platform 결정.
**How to avoid:** `os.environ["PYOPENGL_PLATFORM"] = "egl"` 를 pyrender import 보다 반드시 먼저. `render.py` 에서 Spike 002b 가 이미 `os.environ.setdefault("PYOPENGL_PLATFORM", "egl")` 패턴 박제함.
**Warning signs:** `OSError: No such file or directory: 'libGL.so.1'` 또는 `osmesa.dll not found`.

### Pitfall 4: Firestore nested-array (합성 메타데이터)

**What goes wrong:** `synthesized_joints: [[frame_0_joints], [frame_1_joints], ...]` 형태로 Firestore 에 저장 시 `FirestoreError: Nested arrays are not supported`.
**Why it happens:** Firestore 규칙 (CLAUDE.md 박제).
**How to avoid:** 합성 메타데이터도 flat 저장:
```python
# 금지
"synthesizedJoints": [[joint1, joint2, ...], [joint1, joint2, ...]]  # nested

# 허용
"synthesizedJoints": [joint1, joint2, ..., joint1, joint2, ...]       # flat
"synthesizedJointsFrames": 30                                         # frame 수
"synthesizedJointsJointKeys": ["lShoulder", "rShoulder", ...]        # joint 순서
```

### Pitfall 5: Gemini Occlusion FP (정은지 영상 G4 가드)

**What goes wrong:** 정은지 reference 영상에서 `occlusion_severe=True` 로 잘못 flag → 합성 트리거 발동 → 멀쩡한 reference 점수 오염.
**Why it happens:** Phase 17 G4 guard 가 `is_reference=True + occlusion_severe=True` 동시 시 4 flag 전체 폐기 로직. Phase 4 의 합성 트리거가 이를 무시하면 G4 guard 가 무력화.
**How to avoid:** 합성 트리거 로직에서 `is_reference=True` 시 합성 호출 0. 정은지 5영상 재처리 시 G4 가드가 항상 먼저 실행되도록 순서 보장.
**Warning signs:** 정은지 영상 재처리 결과 점수가 이전보다 낮아짐.

### Pitfall 6: Gemini Omni 조기 도입 (Vertex endpoint 미등록)

**What goes wrong:** Vertex AI SDK 는 이미 GA 이지만 Gemini Omni model endpoint 는 Model Garden 에 미등록 (2026-06-13 기준). endpoint string 하드코딩 → 404 error.
**Why it happens:** Spike 004 VALIDATED-DEFERRED-VERTEX-GA 결과. "coming weeks" 윈도우 (mid-late June 2026).
**How to avoid:** Wave 4 는 interface stub 만 박제. Omni endpoint 등록 확인 후 belle 승인 받아 활성화. Veo 3.1 (Vertex Public Preview) 은 즉시 사용 가능 대안으로 Wave 4 PoC 옵션.
**Warning signs:** `404 Model not found` from Vertex AI SDK.

### Pitfall 7: RTMW 3D scoring 행렬에 합성 좌표 주입

**What goes wrong:** 합성된 joint 좌표를 `coco_array` (DTW/kismam 입력) 에 mutate 하면 채점 결과가 합성 품질에 직접 의존 → 낮은 Gemini 좌표 정확도가 점수를 오염.
**Why it happens:** Phase 17 AI-SPEC §1.b D-v2 에 명시: "RTMW 3D pole-aligned scoring 행렬은 mutate 0".
**How to avoid:** 합성 결과는 `KeypointReport` (사용자 시각화용) + `aiSynthesisMeta` 에만 저장. DTW/kismam 은 항상 1차 RTMW 원본 사용.

---

## Code Examples

### Stage 1: Gemini View Reasoning prompt 구조 (Spike 003 박제)

```python
# Source: .planning/spikes/003-gemini-vision-view-reasoning/run_spike.py
# 비용: Gemini Flash $0.12/video (5영상 $0.60)
OCCLUDED_JOINT_REASONING_PROMPT = """
폴스포츠 동작 분석 전문가로서 RTMW 포즈 추정기가 신뢰도 미달로 추정하지 못한
관절 좌표를 영상과 주변 맥락으로 추정해 주세요.

분석 맥락:
- 기술: {motion_category}
- occlusion_severe: {occlusion_severe}
- camera_angle: {camera_angle}
- 폴 축 x 픽셀: {pole_axis_pixel_x}
- 고신뢰 anchor joints: {visible_anchors}
- 이전 프레임 포즈: {prev_frame_pose}
- 추정 필요 관절: {occluded_joints}

중요 제약:
- 픽셀 이미지 생성 금지. 좌표만 출력.
- 불확실한 경우 "indeterminate" 출력 (추정 거짓말 금지).
- 사람 점수/판단 라벨링 금지.

출력 형식 (JSON):
{{"joints": [{{"name": "lShoulder", "x": 0.45, "y": 0.23, "z_rel": -0.1, "confidence": 0.65}}, ...], "reasoning": "..."}}
"""
```

### Temporal 병합 인터페이스 (temporal.py 재사용)

```python
# Source: temporal.py (운영 코드) — temporal_fill + occluded_mask 재사용
from sunity_shared.analysis.temporal import occluded_mask, temporal_fill

def merge_with_temporal(
    primary_joints: np.ndarray,    # (T, 17, 3) 1차 RTMW
    primary_conf: np.ndarray,      # (T, 17)
    synth_joints: np.ndarray,      # (T, 17, 3) 합성 결과
    synth_conf: np.ndarray,        # (T, 17) 합성 confidence
    synthesis_mask: np.ndarray,    # (T, 17) bool 합성 적용 대상
) -> tuple[np.ndarray, np.ndarray]:
    """confidence 가중 병합. primary + synth 중 높은 쪽을 frame-by-frame 선택."""
    merged_joints = primary_joints.copy()
    merged_conf = primary_conf.copy()
    # synthesis_mask 가 True 이고 synth_conf 가 primary_conf 보다 높은 곳만 교체
    better = synthesis_mask & (synth_conf > primary_conf)
    merged_joints[better] = synth_joints[better]
    merged_conf[better] = synth_conf[better]
    # temporal smoothing (기존 temporal_fill 재사용)
    angles = compute_joint_angles(merged_joints)  # (T, J)
    uncertainty = 1.0 - merged_conf
    filled = temporal_fill(angles, uncertainty)
    return merged_joints, merged_conf  # 또는 filled 각도 기반 재구성
```

### Warning Code 추가 위치

```python
# Source: docs/contract.md §9.8 + body_normalizer.py BODY_COMPARISON_WARNING_CODES 패턴
# 추가 위치 1: models.py 주석 블록 (§9.8 설명 갱신)
# 추가 위치 2: 실제 validation frozenset
# Phase 8 §9.8 Warning Code Enum 에 추가:
# | Phase 4 신설 | `ai_synthesis_failed` | AI 합성 실패 → graceful degrade 발동 |
# | Phase 4 신설 | `ai_synthesis_partial` | 일부 frame 만 합성 성공 |

# ForceSignalsReport warning 과 별도로 AnalysisResult top-level warnings 에도 추가 필요
# contract.md §3 AnalysisResult.warnings enum 에 mirror 갱신 (3-way lockstep)
```

---

## Runtime State Inventory

> Phase 4 는 신규 파이프라인 추가 (greenfield) + 정은지 5영상 재처리 (migration). 재처리 영역만 적용.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Firestore `referenceMotions/{id}` — 정은지 5영상 분석 결과 (angles, joint sequence, scores 등). 현재 1차 RTMW 결과로 저장됨. | Phase 4 파이프라인 완성 후 재처리 스크립트 (D-09). 기존 문서 덮어쓰기 or 신규 버전 필드 추가 결정 필요. |
| Live service config | Lambda env: `RUNPOD_ANALYZE_URL`, `RUNPOD_AUTH_TOKEN` — Pod URL 변경 시 수동 갱신 필요. Phase 4 신규: Gemini API key (`GEMINI_API_KEY` or SSM path) 확인 필요. | Pod 재생성 시 Lambda env 동기화 (runpod-gpu-env 박제 정합). Gemini key = Phase 17 에서 이미 Parameter Store 주입됨 — 재확인만. |
| OS-registered state | RunPod Pod 에 trimesh + pyrender 추가 설치 필요 (매 Pod 재생성 시). 현 setup script (`setup_pod_rtmw.sh`) 에 미포함. | `setup_pod_rtmw.sh` 에 `pip install trimesh pyrender pyopengl` 추가. |
| Secrets/env vars | `GEMINI_API_KEY` (or `GEMINI_C_MODEL_OVERRIDE`) — Phase 17 scene_finder 에서 이미 사용 중. Phase 4 신규 Gemini 호출도 동일 key 재사용 가능. | None (기존 key 재사용). model string 확인: Vision 영역은 `gemini-2.5-pro` 일시 허용 (WRAP-UP-SUMMARY.md 박제). |
| Build artifacts | `app/package-lock.json` — Wave 2 시 `npm install three @react-three/fiber expo-three @react-three/drei expo-gl` 후 갱신됨. EAS Build 시 `npm ci` 가 lock 파일 기준 설치. | Wave 2 npm install 후 lock 파일 commit 필수 (EAS Build 함정 박제 정합). |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 다중 시점 직접 촬영 UX | Single-view AI 가상 다각도 합성 | 2026-06-10 belle pivot | 사용자 마찰 0, 정확도는 AI 합성 품질에 의존 |
| SMPL-X mesh render | Cylindrical humanoid mesh (trimesh) | Spike 002b (2026-06-13) | MIT license, 구현 단순, IPSF split angle metric 정합 |
| Higgsfield 외부 API | 자체 path + Gemini Vision reasoning | Spike 002a/003 (2026-06-13) | ToS 위험 제거, 비용 100배 절감 ($0.12 vs $880만/yr) |
| NLF 단일 프레임 3D | RTMW 133 wholebody + MotionBERT lifter (option B) | Phase 1 (2026-06-03) | Apache-2.0, occlusion/역수직 swap 위험 회귀 가드 |

**Deprecated/outdated:**
- Higgsfield Angles API: public API 미존재 + ToS §5.1(iii) 차단 (Spike 002a).
- MagicMan: THuman2.1 CC BY-NC + 2K2K research-only transitive (Spike 002c).
- SMPL-X direct path: belle 완전 최후의 보류, $7,300/yr (belle 박제 2026-06-13).
- ViTPose-S: NLF 이전 백본, RTMW 133 wholebody 로 교체됨 (Phase 1).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | RTMW confidence < 0.3 = "low" 트리거 초기 임계값 | Standard Stack / Confidence Gate | 너무 낮으면 합성 과호출 (비용 증가), 너무 높으면 occlusion 미포착. Spike 001 evaluate_4way RunPod 실행으로 조정 필요. |
| A2 | @react-three/drei OrbitControls 가 `/native` 경로로 RN 에서 동작 | Code Examples / Wave 2 | drei 의 OrbitControls 가 일부 WebGL 전용 구현 시 별도 gesture 구현 필요. |
| A3 | 정은지 5영상 재처리 시 기존 Firestore 문서를 덮어쓰는 방식 적합 | Runtime State Inventory | 기존 analyses/{id} 덮어쓰면 mode1 비교 중인 사용자에게 일시적 불일치. 버전 필드 추가 or atomic swap 전략 belle 결정 필요. |
| A4 | Gemini Omni Vertex endpoint 가 mid-late June 2026 중 등록됨 | Standard Stack / Wave 4 | 늦어지면 Wave 4 = stub 유지. Veo 3.1 대안으로 Wave 4 PoC 진행 가능. |
| A5 | Cylindrical mesh silhouette 이 RTMW 재추론에 충분한 입력 품질 제공 | Architecture Patterns | Spike 002b VALIDATED-SKELETON 이지만 실 RunPod 추론 결과는 미측정. evaluate_4way 가 확정 필요. |

---

## Open Questions (RESOLVED — plan-phase 2026-06-13)

> 3개 질문 모두 plan task 로 처리됨. Q1 = 04-01 threshold=0.3 초기값 (CONTEXT Claude's Discretion 영역, Wave 1 후 RunPod sweep 조정). Q2 = 04-05 `pipelineVersion="phase4_v1"` + 원자적 교체 결정. Q3 = 04-02 checkpoint Task 0 실기기 검증 + drei /native 미존재 시 PanResponder 대체 분기. 실행 비차단.

1. **RTMW confidence 임계값 확정**
   - What we know: temporal.py `DEFAULT_OUTLIER_K = 3.0`, force_signals.py `LOW_RELIABILITY_PHASE_THRESHOLD` 존재. Spike 002d baseline: confidence < 0.3 frame 비율 7.5%.
   - What's unclear: 0.3 이 최적 임계값인지. force_signals 의 비율 임계와 어떻게 통합할지.
   - Recommendation: Wave 1 착수 전 Spike 001 evaluate_4way RunPod 실행으로 정량화. 초기 구현은 confidence < 0.3 시작, 0.4/0.2 도 테스트.

2. **정은지 5영상 재처리 전략 (덮어쓰기 vs 버전 필드)**
   - What we know: Firestore `referenceMotions/{id}` 에 기존 분석 결과 저장됨. D-09 = 자동 재처리.
   - What's unclear: 기존 문서 덮어쓰기 시 재처리 중 mode1 비교 사용자 영향.
   - Recommendation: belle 에게 확인 후 plan-phase 에서 결정. 권장: 신규 `pipelineVersion` 필드 추가 + 원자적 교체.

3. **@react-three/drei OrbitControls RN 호환 여부**
   - What we know: drei@10.7.7 은 `@react-three/fiber ^9.0.0` peer dep. `/native` import 경로 존재 확인 필요.
   - What's unclear: OrbitControls 가 drei/native 경로에 실제 export 되는지 (일부 helper 는 web-only).
   - Recommendation: Wave 2 착수 시 `npx expo-doctor` 로 호환성 검사. OrbitControls 미동작 시 `react-native-gesture-handler` + 커스텀 pan/rotate handler 로 대체 (개발 비용 1-2일 추가).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | app npm install | ✓ | 22.22.3 | — |
| Python 3.x | backend pip | ✓ | 3.14.5 | — |
| SAM CLI | backend deploy | ✓ | 1.161.0 | — |
| Docker Desktop | sam build --use-container | ✓ | 29.4.0 | — |
| RunPod Pod (GPU) | Stage 3' cylindrical render | ✗ (offline, 매 세션 재생성) | — | Spike 002b dummy render (local 개발만) |
| pyrender local | Stage 3' local 개발 | ✗ (OpenGL/EGL Mac 미지원) | — | RunPod GPU Pod 에서만 실 render |
| Gemini API key | Stage 1 Gemini reasoning | ✓ (Phase 17 운영 중) | — | graceful degrade (scene_finder 패턴 정합) |
| expo-gl | Wave 2 R3F frontend | ✓ (Expo SDK 54 포함, `expo install` 필요) | 56.0.5 | — |

**Missing dependencies with no fallback:**
- RunPod GPU Pod — Stage 3' 실 render. Wave 3 작업 시 Pod 기동 필요.

**Missing dependencies with fallback:**
- pyrender local (Mac) — local 개발 시 Spike 002b dummy image 반환 패턴 유지.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=8,<9 (`backend/requirements-dev.txt`) |
| Config file | `backend/tests/conftest.py` (기존) |
| Quick run command | `pytest backend/tests/phase04/ -x -q` (Wave 0 에서 생성) |
| Full suite command | `pytest backend/tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POSE-03-a | confidence 미달 frame 식별 → synthesis_needed_mask 정확 | unit | `pytest backend/tests/phase04/test_confidence_gate.py -x` | Wave 0 생성 필요 |
| POSE-03-b | Gemini view reasoning graceful degrade (API 실패 시 1차 결과 반환) | unit | `pytest backend/tests/phase04/test_synthesis_adapter.py::test_gemini_degrade -x` | Wave 0 생성 필요 |
| POSE-03-c | temporal 병합 (primary + synth, higher confidence wins) | unit | `pytest backend/tests/phase04/test_synthesis_merge.py -x` | Wave 0 생성 필요 |
| POSE-03-d | `ai_synthesis_failed` warning = models.py frozenset 통과 | unit | `pytest backend/tests/phase04/test_warning_lockstep.py -x` | Wave 0 생성 필요 |
| POSE-03-e | Firestore synthesis meta flat 저장 (nested-array 0) | unit | `pytest backend/tests/phase04/test_synthesis_firestore_flat.py -x` | Wave 0 생성 필요 |
| POSE-03-f | G4 is_reference=True 시 합성 트리거 발동 안 함 | unit | `pytest backend/tests/phase04/test_synthesis_g4_guard.py -x` | Wave 0 생성 필요 |
| POSE-03-g | Spike 001 evaluate_4way: cylindrical mesh path vs baseline IPSF 감점 비교 | integration | `pytest backend/tests/phase04/test_evaluate_4way.py -x` (RunPod 필요) | Wave 3 생성 (manual-only until RunPod) |
| POSE-03-h | PoseViewer3D 컴포넌트 TypeScript 타입 체크 통과 | static | `npm run typecheck` (app/) | Wave 2 생성 필요 |

### Spike 001 evaluate_4way 를 Verification Gate 로 활용

```python
# .planning/spikes/001-dataset-eval-harness/harness.py 의 evaluate_4way 를 Wave 3 통합 테스트 gate 로 재사용
# IPSF axis_b (occlusion reduction): cylindrical mesh path > baseline RTMW-mirror → PASS 기준
# IPSF axis_a (split angle consistency): 모든 path 에서 IPSF Page 19 tolerance ±20° 내 → PASS 기준
# IPSF axis_c (IPSF criterion satisfaction): Phase 4 path 의 twist_alignment 개선 여부
```

### Sampling Rate

- **Per task commit:** `pytest backend/tests/phase04/ -x -q` (< 15초, 단위 테스트)
- **Per wave merge:** `pytest backend/tests/ -q` (전체 backend 테스트 스위트)
- **Phase gate:** Full suite green + `npm run typecheck` (app/) + belle 5영상 재처리 시각 검증 before `/gsd-verify-work`

### Wave 0 Gaps

- `backend/tests/phase04/` 디렉토리 신설
- `backend/tests/phase04/__init__.py`
- `backend/tests/phase04/test_confidence_gate.py` — covers POSE-03-a
- `backend/tests/phase04/test_synthesis_adapter.py` — covers POSE-03-b (GeminiViewReasoner mock + CylindricalMeshAdapter mock)
- `backend/tests/phase04/test_synthesis_merge.py` — covers POSE-03-c (temporal.py 재사용 검증)
- `backend/tests/phase04/test_warning_lockstep.py` — covers POSE-03-d (models.py frozenset 3-way lockstep)
- `backend/tests/phase04/test_synthesis_firestore_flat.py` — covers POSE-03-e
- `backend/tests/phase04/test_synthesis_g4_guard.py` — covers POSE-03-f
- `backend/tests/phase04/conftest.py` — synthetic joint sequence fixtures (Spike 002d 패턴 재사용)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 기존 Firebase Auth 유지 |
| V3 Session Management | no | 기존 구조 변경 없음 |
| V4 Access Control | yes | `is_reference=True` G4 가드 — reference 영상 합성 차단 (D-10 정합) |
| V5 Input Validation | yes | Gemini 출력 좌표 범위 검증 (0~1 normalized), "indeterminate" 처리 |
| V6 Cryptography | no | — |

### Known Threat Patterns for AI Synthesis Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Gemini 출력 hallucinated coordinates (범위 밖 좌표) | Tampering | 출력 좌표 0~1 clamp + "indeterminate" → skip 처리. `analysis-objectivity-no-human-scores` 정합 |
| Phase 17 G4 guard bypass (합성 트리거 우선 실행) | Elevation of Privilege | `is_reference=True` 체크를 합성 트리거보다 먼저 실행. G4 flag 폐기 후 합성 결정. |
| RunPod endpoint 노출 (Gemini API key 평문 로그) | Information Disclosure | `log.exception()` 에서 Gemini key 마스킹. `GEMINI_API_KEY` = SSM Parameter Store (CLAUDE.md §3 시크릿 정책). |
| Cylindrical mesh malformed OBJ injection | Tampering | mesh = 항상 RTMW joint sequence 에서 코드로 생성 (외부 파일 입력 0). |

---

## Sources

### Primary (HIGH confidence)

- `.planning/spikes/001-dataset-eval-harness/` — IPSF GeometricCriterion ground truth + evaluate_4way 하네스 (코드 직접 확인)
- `.planning/spikes/002b-cylindrical-mesh-virtual-render/` — trimesh + pyrender EGL headless 구현 (코드 직접 확인)
- `.planning/spikes/003-gemini-vision-view-reasoning/` — Gemini multimodal reasoning prompt + 비용 ($0.12/video) (코드 직접 확인)
- `.planning/spikes/005-frontend-3d-viewer/README.md` — R3F + expo-three Decoupling 4-stage 아키텍처 (코드 직접 확인)
- `backend/shared/python/sunity_shared/analysis/temporal.py` — confidence 가중 보간 인터페이스 (코드 직접 확인)
- `backend/shared/python/sunity_shared/analysis/body_normalizer.py:166` — `BODY_COMPARISON_WARNING_CODES` frozenset (코드 직접 확인)
- `backend/shared/python/sunity_shared/analysis/force_signals.py:1274` — `occlusion_high_in_phase` 구현 (코드 직접 확인)
- `backend/shared/python/sunity_shared/gemini/scene_finder.py` — G4 guard 구현 (코드 직접 확인)
- `docs/contract.md §9.8` — warning code 20개 enum (코드 직접 확인)
- npm registry: @react-three/fiber 9.6.1 peerDependencies (expo-gl >=11.0, react >=19, RN >=0.78) — 직접 확인
- npm registry: expo-three 8.0.0 (three ^0.166.0 peer dep), three 0.184.0 (최신) — 직접 확인
- npm registry: three/R3F/expo-three/drei — postinstall 스크립트 없음 직접 확인
- PyPI: trimesh 4.12.2 (MIT), pyrender 0.1.45 (MIT) 직접 확인

### Secondary (MEDIUM confidence)

- `.planning/spikes/WRAP-UP-SUMMARY.md` — Wave 권고 + Gemini 모델 정책 + SMPL-X 박제 (스파이크 종합)
- `.planning/phases/04-ux-occlusion-confidence/04-CONTEXT.md` — D-01~D-32 locked decisions
- `.planning/phases/17-gemini-vision-integration-4/17-AI-SPEC.md` — G4 가드 + 영역 D 설계

### Tertiary (LOW confidence)

- WebSearch: expo-three + R3F + Expo SDK 54 + New Architecture 호환성 — Medium article (SDK 53 기준, SDK 54 미확인). ASSUMED 태그.
- [Medium: current state of R3F in Expo](https://trifonstatkov.medium.com/the-current-state-of-using-react-three-fiber-in-react-native-expo-c65918593eaf) — SDK 50 기준 구 정보. peer dep 검증으로 보완.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — npm/PyPI registry 직접 확인 + spike 코드 직접 검증
- Architecture: HIGH — spike 6건 완료, 운영 코드 패턴 직접 확인
- R3F New Architecture 실 기기 동작: MEDIUM — peer dep 호환 확인, 실 빌드 미검증 (Wave 2 착수 시 검증 필수)
- Confidence 임계값: LOW — Spike 001 evaluate_4way RunPod 실행 전 추정치만 존재
- Gemini Omni Vertex 타임라인: LOW — "mid-late June 2026" 예측이지만 변동 가능

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (30일, R3F/expo 생태계는 fast-moving — New Architecture 관련 변경 모니터링 권고)
