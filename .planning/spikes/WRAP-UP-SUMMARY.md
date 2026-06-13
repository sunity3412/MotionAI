# Spike Wrap-Up Summary — Phase 4 Camera Angle AI

**Date:** 2026-06-13
**Spikes processed:** 6 (001, 002a, 002c, 002b, 002d, 003, 004, 005)
**Phase:** 4 (ux-occlusion-confidence — Camera Angle AI redesign)
**Next:** `/gsd:plan-phase 4`

## belle 명시 종료 박제

> "전달은 여기까지 최종 정리해서 plan 으로 넘어갈 수 있도록 하자" (2026-06-13)

추가 spike 진행 없음. WHAM 운영 도입 제외 (license 함정), 그러나 아키텍처 패턴 학습 참고로 활용. Gemini 2.5 = Vision 영역 일시 허용.

## Processed Spikes

| # | Name | Type | Verdict | Feature Area |
|---|------|------|---------|--------------|
| 001 | dataset-eval-harness | foundation | ✓ VALIDATED | Stage 0 — IPSF metric ground truth |
| 002a | higgsfield-angles-api | comparison | ✗ INVALIDATED | Stage 4 (block) |
| 002c | magicman-zero-shot | comparison | ✗ INVALIDATED | Stage 3' (block) |
| 002b | cylindrical-mesh-virtual-render | comparison | ✓ VALIDATED-SKELETON | Stage 3' — backend 분석 정확도 |
| 002d | rtmw-mirror-baseline | comparison | ✓ VALIDATED-BASELINE | Stage 0 — 비교 baseline |
| 003 | gemini-vision-view-reasoning | standard | ✓ VALIDATED-PROTOTYPE | Stage 1 — 분석 코어 (PRIMARY) |
| 004 | gemini-omni-view-editing | standard | ⏳ VALIDATED-DEFERRED-VERTEX-GA | Stage 4 — 영상 생성 plug-in (Vertex GA 후) |
| 005 | frontend-3d-viewer | standard | ✓ VALIDATED-ARCHITECTURE | Stage 3 — 사용자 UX viewer |

## Decoupling 4-Stage 아키텍처 (belle 결정적 박제)

```
[입력: 스마트폰 영상]
        │
        ▼
┌──────────────────────────────────────────┐
│ Stage 1: 분석 코어 (Gemini 3.x + Vision 2.5 일시) │ ← Spike 003 (PRIMARY 즉시)
│  - 기술 식별 + 타임스탬프 + 핵심 frame slicing    │
└──────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│ Stage 2: 3D pose (RTMW 133 wholebody)            │ ← Phase 1 운영
│  - 폴 + 신체 관절 X/Y/Z 좌표                     │
└──────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│ Stage 3: 시각화 (Decoupling — 두 갈래)            │
│  - 3 사용자 UX: react-three-fiber frontend viewer │ ← Spike 005 (MVP 가능)
│  - 3' 분석 정확도: cylindrical mesh + RunPod      │ ← Spike 002b (SECONDARY)
└──────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│ Stage 4: 영상 생성 plug-in (옵션)                │ ← Spike 004 (Vertex GA 후)
│  - Omni "측면 90도 회전 비디오 생성"             │
│  - Veo 3.1 (즉시 사용 가능 대안 #2)              │
└──────────────────────────────────────────┘
```

## Key Findings (시간순)

### 1. NLM IPSF lookup (Spike 001)
- **IPSF Page 19 "split angle must remain the same from all angles/perspectives"** = Camera Angle AI 의 IPSF 직접 근거
- 7개 GeometricCriterion 박제 (Fully Extended / Hold Time / Spin Rotation / Twist Alignment / Split Angle / Presentation / Start-End Visibility)

### 2. 외부 path 모두 차단
- **Higgsfield** (Spike 002a): Angles 모델 public API 미존재 + ToS §5.1(iii) + user input 학습 사용
- **MagicMan** (Spike 002c): weight transitive 비상업 (THuman2.1 + 2K2K + SMPL-X 의존)
- **WHAM** (belle 추천이나 license 검증): weight = SMPL/AMASS 비상업 의존 → **아키텍처 패턴 학습 reference 로만** 활용

### 3. 자체 path 검증
- **Cylindrical humanoid mesh** (Spike 002b): trimesh MIT + pyrender MIT + numpy BSD, license 100% clear
- **Spike 001 split angle metric 정합** (180° PASS)

### 4. PRIMARY path 발견 (Spike 003)
- **Gemini Vision multimodal reasoning**: $0.12/video (SMPL-X 880만원/yr 대비 100배 우위)
- 픽셀 합성 X, joint 좌표 추정만 (`analysis-objectivity-no-human-scores` 정합)

### 5. belle 박제 정합 — Gemini Omni (Spike 004)
- 영상 직접 편집 + 카메라 앵글 변경 능력 박제 (DeepMind 공식)
- **Vertex AI 플랫폼 자체는 GA** (Sunity Phase 17 운영), **Omni model endpoint 만 미등록**
- mid-late June 2026 윈도우 (이번 주~수 주 내) — Q3 까지 갈 가능성 낮음
- Motion Realism 4/5 → 폴스포츠 motion clean-data gate 필수 (회전 5 / 역수직 3 / spin 2 = 10건)

### 6. belle 결정적 깨달음 (Spike 005)
- **"AI 영상 생성 불필요 — 수학적 가상 카메라 연산으로 사용자 인터랙티브 360° 가능"**
- v2 deferred "구글맵 스트리트뷰 뷰어" = **MVP 가능 박제로 승격**
- react-three-fiber + expo-three (모두 MIT)

## SMPL-X 박제 (belle 명시 박제)

**Primary mission: "SMPL-X 없이 가능하게 해보라."**
- 도입 조건: (1) 모든 license-clear path 99% 미달 + (2) SMPL-X 효과성 입증
- 비용: 1년 880만원 상업 라이선스 (신청서 belle 받음)
- 현 정책: **완전 최후의 보류** — Spike 002b cylindrical mesh + Spike 003 Gemini Vision + Spike 005 R3F viewer 가 99% 미달 시에만 검토

## Gemini 모델 정책 (belle 정정 박제 2026-06-13)

- **일반 영역** (LLM reasoning / 분류 / 코칭): `gemini-3.1-pro-preview` / `gemini-3.5-flash` 유지 — 2.5 영구 금지
- **Vision 영상 입력 영역 일시 예외:** Google Vision 자체가 3.x 미출시 → Phase 17 + Spike 003/004 Vision input 처리 영역만 `gemini-2.5-pro` 일시 허용
- **3.x Vision 출시 시점 모니터링 의무:** Claude 가 발견 즉시 belle 알림 → 즉시 migrate

## Plan-Phase Wave 권고

| Wave | 작업 | Spike 근거 | License |
|---|---|---|---|
| **1** | Stage 1+2 통합 — Gemini Vision reasoning (영상 slicing + 기술 식별 + 핵심 frame 추출) + RTMW 운영 stack 연결 | Spike 003 + Phase 1 | 100% commercial OK |
| **2** | Stage 3 frontend viewer — react-three-fiber + expo-three 통합. 사용자 360° 인터랙션 | Spike 005 | MIT × 4 |
| **3** | Stage 3' backend mesh render — cylindrical humanoid mesh + RunPod 12 virtual camera + RTMW 재추론 (조건부 트리거 — confidence 미달 phase 만) | Spike 002b | trimesh MIT + pyrender MIT |
| **4** | Stage 4 plug-in 인터페이스 — Omni 출시 후 활성화. 현재는 interface stub + Veo 3.1 PoC (옵션) | Spike 004 | Vertex Public Preview |
| **5** | 정은지 5영상 재처리 + 정확도 비교 (Spike 001 evaluate_4way) | Spike 001 | — |
| **6** | UAT + belle 검증 + UI 다듬기 | — | — |

## 메모리 박제 갱신 사항

| 메모리 | 갱신 내용 |
|---|---|
| `camera-angle-ai-single-view-synth` | Phase 4 redesign 확정, Decoupling 4-stage, SMPL-X 정정 (완전 최후의 보류), Omni Vertex GA 후 PRIMARY 후보, R3F viewer MVP 가능 승격 |
| `rtmw-free-stack-pivot` | SMPL-X 박제 정정 (영구 제거 X, 완전 최후의 보류) |
| `gemini-latest-model-versions` | Vision 영역 2.5 일시 허용 박제 + 3.x 출시 모니터링 의무 |

## Phase 4 CONTEXT.md 박제 갱신

D-15 ~ D-32 (총 18개) 추가 박제. Stage 1~4 Decoupling 아키텍처 + spike 결과 + license 정합 모두 박제.

## Files

- `001-dataset-eval-harness/` — Spike 001 (eval harness + IPSF criteria + dataset)
- `002a-higgsfield-angles-api/README.md` — license/약관 차단 박제
- `002b-cylindrical-mesh-virtual-render/` — Spike 002b (mesh + render skeleton)
- `002c-magicman-zero-shot/README.md` — license 차단 박제
- `002d-rtmw-mirror-baseline/` — Spike 002d (운영 stack baseline)
- `003-gemini-vision-view-reasoning/` — Spike 003 (PRIMARY)
- `004-gemini-omni-view-editing/README.md` — Spike 004 (deferred)
- `005-frontend-3d-viewer/README.md` — Spike 005 (R3F architecture)
- `MANIFEST.md` — 박제 종합
- `CONVENTIONS.md` — 박제 패턴
- `WRAP-UP-SUMMARY.md` — 본 문서

## Next Up

```bash
/clear
/gsd:plan-phase 4
```

권장 plan scope:
- Decoupling 4-stage 아키텍처 정합 Wave 1~6
- Spike 001 evaluate_4way 박제를 verification gate 로 활용
- Spike 005 의 Decoupling 패턴 = PoseEngine 추상화 확장
