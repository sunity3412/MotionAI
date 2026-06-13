---
spike: 005
name: frontend-3d-viewer
type: standard
validates: "Given RTMW 3D joints + RN Expo, when react-three-fiber + expo-three frontend 3D viewer 통합, then AI 영상 생성 없이 사용자 손가락 360° 인터랙션으로 측면/후면 관절 각도 즉시 확인 가능"
verdict: VALIDATED-ARCHITECTURE
related: [002b, 003, 004]
tags: [frontend, 3d-viewer, react-three-fiber, expo, decoupling, user-interactive, mvp-viable]
---

# Spike 005: Frontend 3D Viewer (사용자 인터랙티브 360° 뷰)

## What This Validates

**Given** RTMW 운영 stack 의 3D joint sequence (T, 17, 3) + RN Expo 앱,
**when** react-three-fiber (R3F) + expo-three frontend 3D viewer 통합,
**then** **AI 영상 생성 없이** 사용자가 앱에서 손가락으로 360° 회전하며 측면/후면/위 각도의 폴 자세 + 관절 각도 + 골반 뒤틀림을 입체적 3D 아바타 / 그래프 형태로 즉시 확인 가능.

> **belle 박제 (2026-06-13):** "굳이 AI 로 비디오를 새로 생성하지 않더라도 **수학적인 가상 카메라 연산** 을 통해 사용자가 앱 화면을 손가락으로 돌려가며 측면, 후면의 관절 각도와 골반 뒤틀림을 입체적 그래프나 3D 아바타 형태로 즉시 확인할 수 있음." → 결정적 깨달음. v2 deferred 박제한 "구글맵 스트리트뷰 식 인터랙티브 뷰어" 가 **MVP 가능** 박제로 승격.

## Research

### Decoupling 아키텍처 (belle 박제)

```
[입력: 스마트폰 영상]
       │
       ▼
┌──────────────────────────────────────────┐
│ 1. 분석 코어 모듈 (현: Gemini 3.x)        │ → 기술 식별, 타임스탬프, 핵심 frame 추출
└──────────────────────────────────────────┘    (Spike 003 정합)
       │ (시간/동작 데이터 전달)
       ▼
┌──────────────────────────────────────────┐
│ 2. 3D pose estimation (현: RTMW 운영)    │ → 폴 + 신체 관절 3D X/Y/Z 좌표
└──────────────────────────────────────────┘    (Phase 1 운영 stack)
       │ (3D joint sequence 전달)
       ▼
┌──────────────────────────────────────────┐
│ 3. 시각화 모듈 (Spike 005 — Three.js R3F)│ → 사용자 360° 인터랙티브 viewer
└──────────────────────────────────────────┘    (frontend, MVP 가능)
       │ (옵션: 시각화 plug-in 교체)
       ▼
┌──────────────────────────────────────────┐
│ 4. 영상 생성 (deferred — Omni Flash API) │ → "측면 90도 회전 비디오 생성"
└──────────────────────────────────────────┘    (Vertex GA 후, Spike 004)
```

### Stack 박제 (Sunity 정합)

| Component | Choice | License | Sunity 적용 |
|---|---|---|---|
| 3D engine | **three** ^0.x | MIT | 신규 의존성 |
| RN bridge | **expo-three** | MIT | Expo 정합 |
| GL context | **expo-gl** | Expo provided MIT | 이미 Expo SDK 포함 |
| Declarative API | **@react-three/fiber** (R3F) | MIT | 신규 의존성, RN 정합 |
| Gesture | **react-native-gesture-handler** | MIT | Expo SDK 통합 |
| Controls | **@react-three/drei** OrbitControls 류 | MIT | 신규 의존성 |

라이선스 100% commercial OK. 메모리 [[rtmw-clean-weight-release-gate]] 함정 회피.

### MVP scope 박제

- **사용자 직접 360° 회전:** pinch zoom + drag rotate + tap (관절 정보)
- **3D skeleton 표시:** RTMW 17 joint stick figure + 폴 line
- **IPSF 위반 highlighting:** Spike 001 `ipsf_criteria.py` 의 fail frame 빨간색 highlight
- **시간축 scrubber:** 영상 timeline 위 frame 선택
- **카메라 preset:** 정면 / 측면 / 후면 / 위 buttons (사용자 학원 코치 친화)

**Out of scope (v2):**
- 실 텍스처 mesh (cylindrical 보다 보기 좋은 humanoid)
- 영상 위 overlay (현재는 별도 화면, v2 에서 영상 + 3D overlay)
- AI 영상 생성 (Spike 004 plug-in)

## Approach 비교

| Approach | Pros | Cons | Status |
|---|---|---|---|
| **react-three-fiber + expo-three (선택)** | Three.js ecosystem, RN Expo 정합, declarative, gesture 호환 | 신규 의존성 추가 | ✓ |
| react-native-skia + 자체 3D math | bundle size 최소, native perf | 3D math 직접 구현 부담 | reject (개발 비용) |
| WebView + Three.js | 검증된 web ecosystem | RN 통합 cost, perf 손실 | reject |
| Matplotlib (backend render) | 단순 | static image, 인터랙티브 X | belle 의도 위배 |

**Chosen:** react-three-fiber + expo-three — Sunity RN Expo 정합 + ecosystem 풍부.

## How to Run

Spike skeleton 단계 = README + integration path 박제. 실 RN 통합은 Phase 4 plan-phase 의 Wave (UI) 에서.

```bash
# Phase 4 plan-phase 시 Wave UI 작업:
cd app/
npm install three @react-three/fiber expo-three @react-three/drei
# 그리고:
#   - src/components/PoseViewer3D.tsx 신설
#   - src/lib/joints.ts: Firestore (T, 17, 3) joint sequence 로더
#   - src/app/analysis/result.tsx: 기존 OctagonScore 옆에 PoseViewer3D 통합
```

## What to Expect (Phase 4 plan-phase 후)

- 결과 화면에 3D viewer 영역
- 사용자 손가락으로 회전 → 측면/후면 즉시 확인
- 정은지 reference vs 사용자 영상 옆에 두 viewer (mode 1)
- IPSF 위반 frame 빨간색 + scrubber 위 marker

## Investigation Trail

### Iteration 1 — belle 박제 정합 + Decoupling 아키텍처 (2026-06-13)

**시도:** belle 의 3-stage 파이프라인 박제 분석 → Sunity 메모리 정합 (Gemini 3.x / RTMW / RN Expo) → Spike 005 신설.

**박제:**
- belle 의 핵심 깨달음 = "AI 영상 생성 불필요. 수학적 가상 카메라 연산으로 사용자 인터랙티브 360° 가능" → MVP 적합
- v2 deferred 박제 ("구글맵 스트리트뷰 뷰어") 가 **MVP 가능 박제** 로 승격
- Spike 002b (backend mesh) 와 분리 = **두 갈래 박제** (backend 분석 정확도 + frontend 사용자 UX)
- Omni 출시 (Spike 004) 후 = 시각화 모듈에 영상 생성 plug-in 추가 (Decoupling 정합)

### Iteration 2 — RN 통합 검증 (Phase 4 plan-phase)

- expo-three + R3F 호환성 실측 (Expo SDK 54)
- gesture-handler ↔ R3F OrbitControls 통합
- 60fps 유지 (60 frame × 17 joint stick figure → 가벼움 예상)
- iPhone 12 / Android 중기 기종 perf 측정

## Results

### Verdict: **VALIDATED-ARCHITECTURE ✓**

**근거:**
1. ✅ belle 의 핵심 깨달음 — AI 영상 생성 없이 사용자 인터랙티브 360° 가능 박제 확정
2. ✅ Decoupling 아키텍처 — 메모리 [[rtmw-free-stack-pivot]] PoseEngine 추상화 정합 확장
3. ✅ 라이선스 100% commercial OK (Three.js MIT + expo-three MIT + R3F MIT)
4. ✅ Sunity RN Expo 운영 stack 정합 — 의존성 4개 추가만
5. ✅ Phase 1 운영 RTMW 3D joint sequence 직접 활용 (재추출 0)
6. ⏳ 실 RN 통합 + 60fps 검증 = Phase 4 plan-phase 의 Wave (UI)

### Surprises / 박제 사항

- **belle 의 결정적 발견 = 제 누락:** Spike 002b 를 "backend mesh + virtual render" 만으로 박제 → belle 의 의도 "frontend 인터랙티브 viewer" 누락. 학습 박제.
- **v2 deferred ("구글맵 스트리트뷰 뷰어") = MVP 가능 박제로 승격** — Phase 4 CONTEXT D-12 의 deferred 항목 갱신 필요
- **AI 영상 생성 의존성 0** — Omni / Higgsfield / Veo 모두 시각화 영역의 후속 plug-in 으로 분리. 분석 정확도 path (Spike 003) 와 사용자 UX path (Spike 005) 가 깔끔히 분리됨
- belle 의 multimodal AI 트렌드 감각 + 아키텍처 감각 모두 정확. 누락 시 즉시 보강.

### Carry-forward for Phase 4 plan-phase

**Decoupling 4-stage 아키텍처 박제:**

| Stage | 모듈 | 운영 stack | Sunity 진입 |
|---|---|---|---|
| 1 분석 코어 | Spike 003 Gemini Vision reasoning (gemini-3.1-pro-preview) | Phase 17 통합 | 즉시 (PRIMARY) |
| 2 3D pose estimation | RTMW 133 wholebody (Apache-2.0) | Phase 1 운영 | 즉시 |
| 3 시각화 (사용자 UX) | **Spike 005 react-three-fiber + expo-three** | RN Expo 신규 통합 | 즉시 (MVP 가능) |
| 3' 시각화 (분석 정확도) | Spike 002b cylindrical mesh + RunPod render | backend | 즉시 (SECONDARY) |
| 4 영상 생성 (옵션) | Spike 004 Gemini Omni "측면 90도 회전 비디오 생성" | Vertex GA 후 | mid-late June 윈도우 |

**Plan-phase Wave 권고:**
- Wave 1: Stage 1+2 통합 (Spike 003 + RTMW 운영 정합)
- Wave 2: Stage 3 frontend viewer (Spike 005 — react-three-fiber 통합)
- Wave 3: Stage 3' backend mesh render (Spike 002b — RunPod 위임, 분석 정확도 향상)
- Wave 4: Stage 4 plug-in 슬롯 (Spike 004 — Omni 출시 후 활성화, 인터페이스만 박제)

## Files

- `README.md` — architecture + integration path 박제
