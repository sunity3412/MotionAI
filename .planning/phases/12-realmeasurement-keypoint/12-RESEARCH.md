# Phase 12: 실측 각도 표시 + 키포인트 오버레이 + UIUX 한번에 — Research

**Researched:** 2026-06-10
**Domain:** Frontend (React Native / expo-video / react-native-svg overlay) + Backend wiring (assemble.py 실측 각도 채움 + KeypointFrame schema 신설 + Firestore flat 저장)
**Confidence:** HIGH (모든 stack 의 정확한 버전 + API + 기존 코드 wiring 상태 직접 inspect 완료)

## Summary

Phase 12 는 **frontend-heavy + backend wiring 일부** 통합 phase 다. 패턴 신설은 거의 없다 — Phase 12.5 (UI) + Phase 9 (backend 3-way contract lockstep) 의 verified-PASS 패턴을 1:1 mirror 하고, 신영역 3 component (`KeypointOverlay` / `ForcePatternCard` / `ForcePatternDetailModal`) + 1 신설 schema (`KeypointFrame`/`KeypointReport`) 를 박제한다.

핵심 발견 4 가지:
1. **`currentAngle`/`targetAngle` 은 production 에서 절대 채워지지 않음.** `kismam.assess()` 시그니처 는 `user_angles` + `reference_angles` kwarg 를 받지만, pipeline `_process` 의 3 call site (`pipeline/app.py:768, 772, 940`) 모두 kwarg 누락. result.tsx 79번째 줄 주석 "시뮬 픽스처" + `enrichJoints` 의 `targetAngle` reference fallback 이 production 의 실측 누락을 가린다. → **Wave 0 의 핵심 task = `kismam.assess()` 의 3 call site 에 user/reference mean angle dict 전달**.
2. **expo-video SDK 54 의 `timeUpdate` event 는 `useEvent` / `useEventListener` hook 으로 폴링 없이 구독 가능** — 기존 `VideoCompare.tsx` 의 250ms `setInterval` 폴링은 SDK 54 의 `useEventListener(player, 'timeUpdate', ...)` + `player.timeUpdateEventInterval = 0.033` (~30fps) 로 교체 권장. 단 기존 VideoCompare 동기-재생 동작과 회귀 위험 — Wave 1 은 기존 폴링 유지 + KeypointOverlay 만 `useEvent` 추가가 안전.
3. **`PoseFrame.keypoints_2d: dict[str, Keypoint2D]` 가 이미 정의돼 있으나 `keypoints_2d=None` 으로 통과** (`pose_frame.py:233, 267` empty sentinel). RTMW path 가 `keypoints_2d` 를 채우는지 grep 검증 미완료 — Wave 0 grep audit task. 채우지 않으면 1 sample fixture 로 `keypoints_3d` projection 도 가능 (NLF/RTMW 의 image-space 2D 좌표 별도 제공 여부 확인 후 결정).
4. **Firestore 1 MiB 제한 안 안전** — 60s × 30fps × 9 keypoint × 2 axis × 4 byte (float32) = 129,600 byte ≈ 0.124 MiB (안전 마진 8배). 실제 분석 영상 길이 분포는 3-15s 가 일반 — 진짜 worst case 도 < 0.5 MiB. **flat 저장 가능, 별도 Storage upload 불필요**.

**Primary recommendation:**
- Wave 0 = (a) `kismam.assess()` 3 call site wiring fix (user/reference mean angle dict) + (b) 3-way schema lockstep atomic commit (KeypointFrame TS interface + Python frozen dataclass + docs §9.12 신설 + Firestore scoped validator + frontend null-guard) + (c) `pipeline._process` 의 `keypoints_2d` flat 저장 wiring + (d) Phase 9 패턴 정합 단위 test 7건.
- Wave 1 = 신영역 component 3개 (`KeypointOverlay` 신설 / `ForcePatternCard` 신설 / `ForcePatternDetailModal` 신설) + `result.tsx` 6 영역 layout 재정비 (component 분리 X, 기존 779줄 안 끼워넣기 per D-12-A2) + `enrichJoints` 의 "시뮬 픽스처" 주석 제거 + `VideoCompare` 의 slot prop 추가 (`children?: React.ReactNode`).
- Wave 2 = `KeypointOverlay` 와 `expo-video` 의 `timeUpdate` event sync (useEventListener pattern) + delta 강조 룰 + confidence/occlusion 표기 + `typecheck` clean + 신영역 단위 test (frontend test infra 신설 X — manual UAT + typecheck 만, deferred to v2).
- 모든 패키지 install 없음 (`react-native-svg` 15.12.1 + `expo-video` ~3.0.16 기존 의존만 사용) — slopcheck 무관 + Package Legitimacy Audit 섹션 omit.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Keypoint frame 좌표 (x, y, confidence) 산출 | Backend / `pose_estimator.py` (RTMW) → `pose_frames[].keypoints_2d` | — | NLF/RTMW 가 image-space 정규화 좌표 출력. 신설 아님 (이미 schema 존재) |
| Keypoint frame Firestore 저장 (flat) | Backend / `pipeline._process` + `firestore_admin.complete_analysis(..., keypoints=...)` 신설 kwarg | — | Phase 8 `force_signals_report` kwarg + scoped validator 패턴 mirror (D-12-E3) |
| Frame index → (x, y) lookup | Browser (App) / `KeypointOverlay.tsx` | — | UI 시각 layer — backend 가 좌표만 제공, 동기화는 UI 책임 |
| 비디오 currentTime → frame index 매핑 | Browser (App) / `useEventListener(player, 'timeUpdate', ...)` | — | expo-video SDK 54 timeUpdate event 가 currentTime 제공 (verified) |
| 실측 각도 (`currentAngle` / `targetAngle`) 채움 | Backend / `kismam.assess(..., user_angles=, reference_angles=)` | — | 이미 시그니처 존재, **call site wiring 미완** (Wave 0 task) |
| 3-way schema lockstep (KeypointFrame) | TS `analysis.ts` ↔ Python `keypoint_frame.py` 신설 ↔ docs §9.12 신설 | — | 단일 atomic commit (D-12-E2, Phase 9 D-09-U1 패턴 mirror) |
| delta ≥ 10° UI 강조 | Browser (App) / `KeypointOverlay` 가 직접 계산 | — | `KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0` module const + Phase 9 IPSF 20° 와 분리 |
| Phase 9 finding 카드 렌더 | Browser (App) / `ForcePatternCard` 신설 + `ForcePatternDetailModal` 신설 | — | `forcePatternInference.findings` 그대로 소비 — backend 신설 X |
| 자연어 풍부화 (LLM) | — | Phase 11 (Gemini 자연어 번역) | Phase 12 = canned KO 직접 표시 + raw 수치 노출 책임 (D-09-D5) |
| 발끝 (toe) keypoint | — | v2 | ROADMAP Phase 12 SC #4 명시 deferred |

## User Constraints (from CONTEXT.md)

### Locked Decisions (must research THESE, no alternatives)

**(A) 결과 화면 layout 통합**

- **D-12-A1**: 영역 배치 순서 = 점수 게이지 → 영상+오버레이 → Phase 9 원인 카드 Top-3 → 차원 카드 → 각도 가이드 상세 → (mode3 only) 성장 차트 → footer. `[CITED: 12-CONTEXT.md]`
- **D-12-A2**: 기존 779줄 `result.tsx` 구조 유지 + 신영역 끼워넣기. component 분리는 신영역 3 개만.
- **D-12-A3**: feature flag X — 단일 main 브랜치 직접 진행 (Phase 9 atomic commit 패턴 mirror).
- **D-12-A4**: 신영역 component 분리 3 개 = `KeypointOverlay` / `ForcePatternCard` / `ForcePatternDetailModal`. `VideoCompare` 는 slot prop 만 확장.

**(B) Phase 9 finding 카드 UI**

- D-12-B1: layout = finding[0] 큰 카드 + finding[1..2] 작은 가로 카드 × 2.
- D-12-B2: 본문 출처 = Phase 9 canned KO 직접 표시 (`forcePatternInference.findings[].interpretation` 그대로). Phase 11 통합 시 동일 필드 LLM 풍부화 자동 교체.
- D-12-B3: tap → 자세히 모달 (Phase 12.5 `DimensionDetailModal.tsx` 패턴 mirror).
- D-12-B4: mode 분기 자동 (UI 분기 코드 X, backend 의 `modeContext` + interpretation prefix 이미 박제).

**(C) 키포인트 오버레이**

- D-12-C1: mode1 = 정은지+사용자 둘 다, mode3 = 사용자만.
- D-12-C2: joint 범위 = 어깨/골반/무릎/손 좌우 4×2 + 중심축 (axis = 어깨 중심 ↔ 골반 중심). 발끝 (toe) v2.
- D-12-C3: delta ≥ 10° → #FF4B33 강조 + 흰색 default. `KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0` module const.
- D-12-C4: 토글 디폴트 ON, AsyncStorage persist (`force_pattern_overlay_enabled` key — UI-SPEC §8).
- D-12-C5: `react-native-svg` + `expo-video` 의 currentTime → keypoint frame index lookup.

**(D) Confidence + occlusion 표기**

- D-12-D1: confidence < 0.5 또는 frame reliability=='low' → "추정 N°" + 회색 + ⓘ tooltip.
- D-12-D2: 차원 카드 단위 ⚠ 배지 (해당 차원 frame 중 occlusion ≥ 20%).
- D-12-D3: Phase 9 finding card 안 confidence 바 (≥0.7 brand "높음" / 0.5-0.7 "보통" / <0.5 textLo "낮음").

**(E) 데이터 흐름 정합**

- D-12-E1: `assemble.py` 의 angleGuide wiring 전수 확인 (5 joint × 2 = 8 joint + 중심축 모두 mode1/mode3_first/mode3_progress 채움).
- D-12-E2: 3-way contract lockstep (`analysis.ts` ↔ `models.py` ↔ `assemble.py` ↔ `docs/contract.md §9.12 신설`).
- D-12-E3: Firestore nested-array 금지 정합 — keypoint (x, y) flat 저장 + 읽는 쪽 reshape (Phase 9 `forcePatternInference` 패턴 mirror).

**(U) Universal**

- D-12-U1: Phase 12.5 시각 언어 1:1 mirror.
- D-12-U2: 신영역 단위 test (snapshot 회피, props → 렌더 elements + 핵심 텍스트 assertion). **단 frontend test infra 부재 (research §16) — Wave 0 install plan 또는 typecheck-only 박제 결정 planner 책임**.
- D-12-U3: mode 분기 자동화 (UI 단 분기 코드 최소화).
- D-12-U4: light theme only — 비디오 카드 배경만 native black 예외.
- D-12-U5: 브랜드 컬러 #FF4B33 — delta 강조 / confidence high 색 / 토글 활성 색.
- D-12-U6: keypoint 데이터 미가용 fallback (오버레이 미표시 + "키포인트 데이터 미가용" placeholder).

### Claude's Discretion (research options, recommend)

- **expo-video currentTime hook 정확한 API** → §Pitfall 1, §Code Examples §1. `useEventListener(player, 'timeUpdate', ...)` 권장 (`player.timeUpdateEventInterval = 0.033` 권장).
- **react-native-svg overlay 위 비디오 동기화 fps drift 처리** → §Pitfall 2 + §Code Examples §2. `useState` 가 아닌 `useRef` + `requestAnimationFrame` 패턴 또는 `useEvent` (이벤트 기반 자동 re-render) 권장.
- **`KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0` 임계** → research §Open Q 1 + Phase 8.1 sweep evidence 활용. 정은지 elite axis tilt 10-53° 분포 (joint angle 은 별개) — 10° 는 첫 default 합리적. 실증 테스트 시점 검수 deferred.
- **`keypoints` Firestore vs Storage 저장 위치** → §Open Q 2. **Firestore flat 저장 결정** (60s × 30fps × 9 × 2 × 4 byte ≈ 0.12 MiB, 1 MiB 한계 안 안전 8배 마진). 비디오는 별도 S3 (기존 그대로).
- **신영역 component 위치** → `app/src/components/` 직접 (Phase 12.5 `DimensionDetailModal.tsx` 와 같은 레벨, 서브폴더 신설 X).
- **mode3 성장 차트 위치 (영역 7)** → D-12-A1 박제대로 footer 직전. 실증 테스트 시점 belle 검수 deferred.

### Deferred Ideas (OUT OF SCOPE)

- 발끝 (toe) keypoint → v2 (ROADMAP Phase 12 SC #4 명시).
- LLM 풍부화 interpretation → Phase 11 (CoachCommentHook + Gemini 자연어 번역).
- AI 카메라 앵글 합성 / 다각도 시점 → Phase 4 redesign.
- 보완 운동 매핑 → Phase 13.
- TestFlight + 종합 검증 → Phase 15.
- `KEYPOINT_DELTA_HIGHLIGHT_DEG` 정밀화 → 실증 테스트 점검 리스트 (12-deferred-items.md 박제).
- Figma design 작성 후 재진입 → Figma 작성 시점.
- 성장 차트 위치 미세 조정 → 실증 테스트 점검 리스트.
- **Frontend 단위 test 인프라 (jest + @testing-library/react-native)** → research §16 발견 = 부재. v2 (별도 plan 또는 Phase 15 통합 시점)로 deferred 권장 — Wave 0/1/2 verify gate 는 typecheck + manual UAT (실 비디오 1건 정은지 reference 위 오버레이 정합 확인) 로 박제.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FEED-01 | 결과 화면에 관절 각도 수치가 "현재 87° → 기준 110°" 형태로 명확히 표시 + 영상 위에 어깨·골반·무릎·손 키포인트와 중심축 오버레이 | §Code Examples §3 (Wave 0 `kismam.assess` wiring fix) + §Code Examples §1-2 (Wave 2 `KeypointOverlay` + `useEventListener`) + §Architecture Patterns §3 (KeypointFrame schema) |
| VIS-01 | 결과 화면 시각화 (확장 keyword) | §Architecture Patterns §1 (6 영역 layout 재정비) + §Code Examples §4 (`ForcePatternCard` 렌더 패턴) |

## Standard Stack

### Core (기존 의존만 사용 — 신설 install 0)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `expo` | ~54.0.33 | App framework + EAS Build | CLAUDE.md §3 결정 박제 (변경 금지) `[CITED: app/package.json]` |
| `expo-video` | ~3.0.16 | 비디오 재생 (VideoView + useVideoPlayer hook + timeUpdate event) | SDK 54 권장, expo-av 대체 (`[CITED: app/package.json]` + `[CITED: docs.expo.dev/versions/v54.0.0/sdk/video/]`) |
| `react-native-svg` | 15.12.1 | KeypointOverlay 의 Circle / Line / G / Rect / Text SVG layer | OctagonScore + GrowthChart 이미 사용 중 — 동일 기술 `[CITED: app/package.json]` |
| `react-native` | 0.81.5 | Modal (bottom sheet) + ScrollView + Pressable | Phase 12.5 패턴 정합 `[CITED: app/package.json]` |
| `@react-native-async-storage/async-storage` | 2.2.0 | 토글 ON/OFF 상태 persist (`force_pattern_overlay_enabled`) | UI-SPEC §8 박제, 이미 Firebase Auth backing store 로 사용 중 `[CITED: app/package.json]` |
| `react` | 19.1.0 | useState / useEffect / useMemo / useRef | New Architecture enabled `[CITED: app/app.json]` |

### Backend (기존 의존만 사용)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `numpy` | >=1.26,<3 | 좌표 평균/reshape (mean angles per joint) | Phase 9 패턴 정합 `[VERIFIED: backend/requirements-dev.txt]` |
| `firebase-admin` | >=6,<7 | Firestore Admin write (top-level + result.keypointReport flat) | Phase 8/9 패턴 정합 `[VERIFIED: backend/functions/*/requirements.txt]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `react-native-svg` Circle + Line | `react-native-skia` | Skia 가 GPU 가속으로 더 빠르나 신설 install + 학습 비용 + Phase 12.5 패턴 정합 X. 60fps 폴 영상 9 keypoint 는 SVG 로 충분 `[ASSUMED]` |
| `useEventListener(player, 'timeUpdate', ...)` | `useEvent(player, 'timeUpdate', ...)` | `useEvent` 는 re-render 자동 (state hook 처럼), `useEventListener` 는 callback (ref/state 박제 책임 caller). KeypointOverlay 는 매 frame re-render 가 필요하므로 **`useEvent` 권장** `[CITED: docs.expo.dev/versions/v54.0.0/sdk/video/]` |
| `expo-video` timeUpdate event | 기존 250ms `setInterval` 폴링 | 폴링은 정확도 ↓ + 배터리 ↑. timeUpdate event 는 native side emit 으로 더 정확. **단 기존 `VideoCompare` 회귀 위험 → 기존 폴링 유지 + KeypointOverlay 내부만 `useEvent` 추가** |
| Frontend 단위 test (`@testing-library/react-native`) | typecheck-only + manual UAT | infra 부재 + Wave 0 install 비용 + Phase 12 scope 확대 우려 → **manual UAT + typecheck 권장 (v2 deferred)** |

**Installation:** 신규 package 없음 — `npm install` 불필요.

**Version verification:**

```bash
cd /Users/kimtaesung/Dev/SunityMotion/app && cat package.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('expo-video:', d['dependencies']['expo-video']); print('react-native-svg:', d['dependencies']['react-native-svg']); print('expo:', d['dependencies']['expo'])"
# expo-video: ~3.0.16
# react-native-svg: 15.12.1
# expo: ~54.0.33
```

`[VERIFIED: app/package.json + docs.expo.dev/versions/v54.0.0/sdk/video/]`

## Architecture Patterns

### System Architecture Diagram

```text
[비디오 영상] (S3 presigned URL)
       │
       ▼
[expo-video VideoView] ─────┐
       │                    │
       │ player.timeUpdate  │
       │ event (currentTime)│
       ▼                    │
[KeypointOverlay (SVG)] ◀───┘
       │
       │ frame index = floor(currentTime × fps)
       ▼
[normalize 된 KeypointFrame[] ]  ◀── [Firestore subscription (onSnapshot)]
       │                                       │
       │                                       │ flat data reshape
       │                                       ▼
       │                              `analysisDoc.keypoints` (flat)
       │
       ▼
[react-native-svg Circle/Line/G/Rect/Text 렌더]
       │
       └─ delta ≥ 10° → brand #FF4B33 강조 + floating angle label

─────────────────────────────────────────────────────────────────

[Pipeline _process (backend)]
       │
       ├─ frame_extractor → pose_estimator (RTMW)
       │                          │
       │                          ▼
       │                   pose_frames[].keypoints_2d  (D-03 UI 오버레이)
       │
       ├─ features.compute_joint_angles → angles (T, J)
       │
       ├─ mean per joint (user + reference) ─┐
       │                                     ▼
       ├─ kismam.assess(deviation,           ← Wave 0 wiring fix
       │                user_angles=mean_u,
       │                reference_angles=mean_r)
       │       │
       │       ▼
       │   JointAssessment.current_angle / target_angle 채움
       │       │
       │       ▼
       ├─ assemble.build_joints → result.joints[].currentAngle / targetAngle
       │
       ├─ infer_force_direction_pattern → forcePatternInference (Phase 9)
       │
       └─ firestore_admin.complete_analysis(
             result=...,
             angles=...,
             keypoint_report=KeypointReport(...),  ← Wave 0 신설 kwarg
             force_pattern_inference=...)
```

### Recommended Project Structure (신설 파일)

```text
app/src/
├── components/
│   ├── KeypointOverlay.tsx          # 신설 (D-12-A4 + UI-SPEC §5)
│   ├── ForcePatternCard.tsx         # 신설 (D-12-A4 + UI-SPEC §4)
│   ├── ForcePatternDetailModal.tsx  # 신설 (D-12-A4 + UI-SPEC §7)
│   ├── VideoCompare.tsx             # 수정 (children?: ReactNode slot prop)
│   ├── OctagonScore.tsx             # 변경 X (재사용)
│   ├── DimensionDetailModal.tsx     # 변경 X (재사용)
│   ├── GrowthChart.tsx              # 변경 X (재사용)
│   └── CoachingTipDetailModal.tsx   # 변경 X (재사용)
├── app/analysis/
│   └── result.tsx                   # 수정 (6 영역 layout 재정비 + enrichJoints 시뮬 주석 제거)
├── lib/
│   ├── userAnalyses.ts              # 수정 (KeypointReport null-guard 추가)
│   └── keypointSync.ts              # 신설 (optional helper — currentTime → frame index lookup)
├── types/
│   └── analysis.ts                  # 수정 (KeypointFrame + KeypointReport interface 신설)
└── theme/
    └── colors.ts                    # 수정 (estimateGray / progressGreen / progressRed / warnAmber / videoBg / brandSoft / brandBg 토큰 신설)

backend/shared/python/sunity_shared/
├── analysis/
│   ├── keypoint_frame.py            # 신설 (KeypointFrame + KeypointReport frozen dataclass)
│   ├── kismam.py                    # 변경 X (assess 시그니처 이미 user_angles/reference_angles 지원)
│   └── assemble.py                  # 수정 (build_keypoint_report 신설 + build_joints 의 5 joint cover 검증)
├── firestore_admin.py               # 수정 (complete_analysis 의 keypoint_report kwarg + _validate_keypoint_report scoped validator 신설)
└── models.py                        # 변경 X (re-export 만)

backend/functions/pipeline/
└── app.py                           # 수정 (kismam.assess 3 call site 에 user_angles/reference_angles 전달 + keypoint_report 산출 + complete_analysis kwarg)

docs/
└── contract.md                      # 수정 (§9.12 신설 — KeypointFrame + KeypointReport spec)
```

### Pattern 1: 3-way contract lockstep (Phase 9 D-09-U1 mirror)

**What:** TS `analysis.ts` + Python `keypoint_frame.py` (frozen dataclass) + `docs/contract.md §9.12` 세 파일 단일 atomic commit. 변경 시 세 곳 모두 같이 수정.

**When to use:** Wave 0 = KeypointFrame / KeypointReport schema 신설 시 반드시.

**Example:**

```python
# Source: backend/shared/python/sunity_shared/analysis/force_pattern.py 패턴 정합
# 신설: backend/shared/python/sunity_shared/analysis/keypoint_frame.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

# 5 joint × 좌우 2 + 중심축 1 = 9 keypoint (D-12-C2)
KeypointName = Literal[
    "left_shoulder", "right_shoulder",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_hand", "right_hand",
    "axis",  # 어깨 중심 ↔ 골반 중심
]

_KEYPOINT_NAMES: tuple[KeypointName, ...] = (
    "left_shoulder", "right_shoulder",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_hand", "right_hand",
    "axis",
)
NUM_KEYPOINTS_PHASE12 = len(_KEYPOINT_NAMES)  # 9


@dataclass(frozen=True)
class KeypointReport:
    """Phase 12 신설 — KeypointOverlay 가 소비하는 flat frame-by-frame 좌표.

    TS lockstep: app/src/types/analysis.ts KeypointReport interface.
    docs lockstep: docs/contract.md §9.12.

    Firestore [[firestore-nested-array-flat]] 정합:
      data = flat list[float], length = frames × len(joints) × 2 (x, y)
      reshape 책임 = userAnalyses.ts::normalize 또는 KeypointOverlay 내부.

    confidence = flat list[float], length = frames × len(joints).
    reliability = frame 단위 "high" | "medium" | "low" (frame_reliability gate, D-12-D1).
    """

    version: str
    joints: list[str] = field(default_factory=lambda: list(_KEYPOINT_NAMES))
    frames: int = 0
    fps: int = 30
    data: list[float] = field(default_factory=list)          # flat (T × J × 2)
    confidence: list[float] = field(default_factory=list)    # flat (T × J)
    reliability: list[str] = field(default_factory=list)     # len = T
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # length 정합 검증 (Wave 0 R2 strict gate, Phase 9 패턴 mirror)
        T = self.frames
        J = len(self.joints)
        if T < 0 or J < 1:
            raise ValueError(f"frames={T}, joints={J} invalid")
        if len(self.data) != T * J * 2:
            raise ValueError(
                f"data length {len(self.data)} != frames({T}) × joints({J}) × 2"
            )
        if len(self.confidence) != T * J:
            raise ValueError(
                f"confidence length {len(self.confidence)} != frames({T}) × joints({J})"
            )
        if len(self.reliability) != T:
            raise ValueError(
                f"reliability length {len(self.reliability)} != frames({T})"
            )
        for r in self.reliability:
            if r not in ("high", "medium", "low"):
                raise ValueError(f"reliability item invalid: {r!r}")
```

```typescript
// Source: app/src/types/analysis.ts ForcePatternInference 패턴 정합 (line 700-712)
// 신설:

export type KeypointName =
  | 'left_shoulder' | 'right_shoulder'
  | 'left_hip' | 'right_hip'
  | 'left_knee' | 'right_knee'
  | 'left_hand' | 'right_hand'
  | 'axis';

/**
 * Phase 12 신설 — KeypointOverlay 가 소비하는 flat frame-by-frame 좌표.
 *
 * Python lockstep: backend/shared/python/sunity_shared/analysis/keypoint_frame.py
 *   KeypointReport (frozen dataclass + __post_init__ validator).
 * docs lockstep: docs/contract.md §9.12.
 *
 * Firestore [[firestore-nested-array-flat]] 정합:
 *   data = flat number[], length = frames × joints.length × 2 (x, y).
 *   reshape 책임 = userAnalyses.ts::normalize 또는 KeypointOverlay 내부 useMemo.
 */
export interface KeypointReport {
  version: string;
  joints: KeypointName[];   // length J = 9
  frames: number;           // T
  fps: number;              // default 30
  /** flat (T × J × 2). [x_0_0, y_0_0, x_0_1, y_0_1, ..., x_T-1_J-1, y_T-1_J-1] */
  data: number[];
  /** flat (T × J). 0~1. */
  confidence: number[];
  /** length = T. 'high' | 'medium' | 'low' frame reliability gate (D-12-D1). */
  reliability: ('high' | 'medium' | 'low')[];
  warnings: string[];
}
```

### Pattern 2: Firestore scoped validator (Phase 9 D-09-U5 mirror)

**What:** `firestore_admin._validate_keypoint_report` 신설 — 화이트리스트 schema, nested list[number] 만 허용 (flat `data` / `confidence` / `reliability` / `warnings` / `joints`).

**When to use:** Wave 0 `complete_analysis(..., keypoint_report=...)` kwarg 추가 시.

**Example:** Phase 9 `_validate_force_pattern_inference` (firestore_admin.py:343-404) 와 1:1 mirror. 신설 함수 = `_validate_keypoint_report`.

### Pattern 3: 신영역 component slot pattern (D-12-A4)

**What:** `VideoCompare.tsx` 가 `children?: React.ReactNode` prop 만 받고, `KeypointOverlay` 를 child 로 받아 `<View style={absoluteOverlay}>` 안에 렌더.

**When to use:** Wave 1 `VideoCompare.tsx` 확장 시.

**Example:**

```typescript
// Source: app/src/components/VideoCompare.tsx 확장 (Wave 1)
type VideoCompareProps = {
  leftLabel: string;
  rightLabel: string;
  leftUrl?: string;
  rightUrl?: string;
  // Phase 12 신설 — 영상 위 absolute layer (KeypointOverlay 등)
  leftOverlay?: React.ReactNode;
  rightOverlay?: React.ReactNode;
};

// slotFrame 안에 absolute overlay 자식 박제
<View style={styles.slotFrame}>
  {url && player ? (
    <>
      <VideoView player={player} style={styles.video} contentFit="contain" ... />
      {overlay && <View style={styles.overlayContainer}>{overlay}</View>}
    </>
  ) : (
    <View style={styles.slotEmpty}>...</View>
  )}
</View>

// styles
overlayContainer: {
  position: 'absolute',
  top: 0, left: 0, right: 0, bottom: 0,
  pointerEvents: 'none',  // tap 통과 (영상 컨트롤이 받아야 함)
},
```

### Pattern 4: `useEvent` for currentTime auto re-render (expo-video SDK 54)

**What:** `useEvent(player, 'timeUpdate', { currentTime: player.currentTime })` 가 timeUpdate emit 시마다 컴포넌트 re-render 자동 트리거. KeypointOverlay 가 매 frame 위치 lookup 가능.

**When to use:** Wave 2 KeypointOverlay 안 currentTime 구독.

**Example:**

```typescript
// Source: docs.expo.dev/versions/v54.0.0/sdk/video/ (verified)
import { useEvent } from 'expo';
import { useVideoPlayer } from 'expo-video';

function KeypointOverlay({ player, keypointReport, ... }) {
  // player.timeUpdateEventInterval 은 player setup 콜백에서 설정해야 함
  // (useVideoPlayer 의 두번째 인자, 또는 useEffect 안에서 1회).
  const { currentTime } = useEvent(player, 'timeUpdate', {
    currentTime: player.currentTime,
  });

  const frameIndex = useMemo(() => {
    if (!keypointReport) return 0;
    const idx = Math.floor(currentTime * keypointReport.fps);
    return Math.min(idx, keypointReport.frames - 1);
  }, [currentTime, keypointReport]);

  // 매 frame re-render — useMemo 가 reshape 캐시
  const positions = useMemo(() => {
    if (!keypointReport) return null;
    const J = keypointReport.joints.length;
    const stride = J * 2;
    const offset = frameIndex * stride;
    const out: Record<string, { x: number; y: number }> = {};
    for (let j = 0; j < J; j++) {
      out[keypointReport.joints[j]] = {
        x: keypointReport.data[offset + j * 2],
        y: keypointReport.data[offset + j * 2 + 1],
      };
    }
    return out;
  }, [keypointReport, frameIndex]);

  if (!positions) return null;

  return (
    <Svg viewBox={`0 0 ${videoSize.width} ${videoSize.height}`}>
      {/* 9 Circle + 8 Line (bone) + delta 강조 색 + floating angle label */}
    </Svg>
  );
}
```

### Anti-Patterns to Avoid

- **`useState(currentTime)` + 250ms `setInterval` 폴링** — 기존 `VideoCompare.tsx` 의 폴링 패턴은 timeline label 용 (250ms 충분). KeypointOverlay 의 frame-by-frame 동기에는 부족 (30fps = 33ms 간격). `useEvent(player, 'timeUpdate', ...)` 사용.
- **각도 자체 계산 (UI 단)** — D-12 안티 패턴 §12 — `keypoints_2d` 좌표 → 각도 변환은 backend 책임. UI 는 `joints[].currentAngle` / `joints[].targetAngle` 그대로 표시 + `floating angle label` 도 backend 산출 (joint mean angle) 만 사용. UI 단에서 좌표로 angle 계산 X.
- **시뮬 픽스처 잔존** — `app/src/app/analysis/result.tsx:78-110` 의 `enrichJoints` 주석 ("currentAngle 은 백엔드 NLF 가 아직 채우지 못해(시뮬 픽스처) 그대로 둔다") 제거 + 함수 자체 단순화. Wave 0 의 wiring fix 후 enrichJoints 는 reference fallback 만 담당.
- **Firestore 60s × 30fps × 9 × 2 × 8 byte = 0.25 MiB 가정** — 실제 float 은 JSON serialization 시 float64 가 아니라 string ("1.234") 이므로 base size 가 추정과 다름. **Wave 0 의 실측 fixture 1건 (예: 5s × 30fps) 로 byte size 측정 후 안전 확인** (대략 5000~10000 byte 이내 예상).
- **`useEvent` vs `useEventListener` 혼동** — `useEvent` = state-like (re-render 자동 + initial value 필수). `useEventListener` = effect-like (callback ref/state caller 책임). KeypointOverlay 는 매 frame re-render 필요 → `useEvent` 권장.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 비디오 currentTime 구독 | `setInterval` 폴링 + `setState` (기존 VideoCompare 패턴) | `useEvent(player, 'timeUpdate', ...)` from `expo` package | SDK 54 native side timeUpdate emit 이 더 정확 + 배터리 효율적 `[CITED: docs.expo.dev/versions/v54.0.0/sdk/video/]` |
| Frame-by-frame keypoint lookup 캐시 | `useState` + 매 frame `setState` | `useMemo([currentTime, keypointReport])` reshape | useState 는 매 frame 강제 re-render, useMemo 는 dependency 변화 시만 |
| SVG Circle 좌표 변환 (image-space → viewBox) | 매 frame `Math` 계산 후 inline 박제 | `viewBox = "0 0 ${videoSize.width} ${videoSize.height}"` + 좌표 그대로 (image-space 정규화) | SVG 가 viewBox transform 자동 처리 — JS 계산 0 |
| 토글 상태 persist | 전역 Redux/Context | `@react-native-async-storage/async-storage` | 이미 Firebase Auth backing store 로 사용 중 |
| Modal bottom sheet | 신설 sheet library (react-native-bottom-sheet 등) | RN 기본 `Modal` + `transparent={true}` + handle gesture | Phase 12.5 `DimensionDetailModal.tsx` 패턴 정합 |
| Keypoint frame Firestore 저장 | 별도 Storage upload + presigned URL | Firestore flat 저장 (`anglesFrames` 패턴 mirror) | 1 MiB 한계 안 안전 (60s × 30fps × 9 × 2 × 4 byte ≈ 0.12 MiB) `[VERIFIED: firebase.google.com/docs/firestore/quotas]` |
| 9 keypoint × 30fps × 60s flat reshape | 모든 frame 의 reshape 미리 계산 후 state 박제 | `useMemo([currentTime])` 안 단일 frame 만 reshape | 메모리 효율 — 단일 frame = 18 floats only |
| frontend test infra | jest + @testing-library/react-native 신설 install | typecheck (`tsc --noEmit`) + manual UAT (실 분석 1건 belle 검수) | Phase 12 scope 확대 우려, infra 신설 = 별도 plan (v2) |

**Key insight:** Phase 12 는 **거의 모든 패턴이 기존 verified-PASS 박제와 1:1 mirror**. 신설 코드는 (a) 3 신영역 component + (b) KeypointFrame schema + (c) `kismam.assess` 3 call site wiring fix + (d) result.tsx 영역 순서 재정비. 새 라이브러리 / 새 아키텍처 / 새 패턴 0. Phase 9 (backend) + Phase 12.5 (frontend) 의 atomic-commit + scoped-validator + null-guard + 3-way lockstep + slot pattern 을 그대로 적용한다.

## Runtime State Inventory

> Phase 12 = component 신설 + backend wiring fix + schema 신설. **stored data migration X** (신설만, 기존 doc 호환 = null-guard 로 처리). 단, 기존 `enrichJoints` 의 "시뮬 픽스처" 주석 + `simulatedResult.ts` fallback 의 상태 정합 점검 필요.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | (a) 기존 Firestore `users/{uid}/analyses/{id}` doc 중 `keypoints` 필드 부재 — 신설 필드, **migration X** (신규 분석부터 채움 + 기존 doc 은 null-guard 로 `keypoints=undefined` → fallback placeholder 표시). (b) 기존 doc 의 `result.joints[].currentAngle` 부재 — `enrichJoints` reference fallback 이 가렸음, 신규 분석부터 실측 채움. | code edit (Wave 0 wiring fix + Wave 1 null-guard) |
| Live service config | None — verified by grep (`grep "keypoints\|KeypointReport" backend/` 결과 0). Lambda env var / Parameter Store 영향 X. | none |
| OS-registered state | None — Phase 12 는 RunPod / Lambda 배포 영향 X (assemble.py + pipeline/app.py + firestore_admin.py 만 수정 + RunPod 자체 코드 미수정). | none |
| Secrets / env vars | None — 신설 secret X, 기존 Firebase / AWS / Cerebras 키 그대로 사용. | none |
| Build artifacts / installed packages | None — 신설 package 0 (`expo-video` ~3.0.16 + `react-native-svg` 15.12.1 기존). egg-info / node_modules 무관. EAS Build 빌드 12 (Phase 12 ship target) 는 신설 package 없이 동일 lockfile 빌드. | none |

**The canonical question:** *After every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?* — Phase 12 는 신설 / 확장만 — 기존 string rename / refactor X. Firestore 의 기존 분석 doc 은 `keypoints` 부재 시 fallback placeholder 표시 (D-12-U6) — migration 불필요.

## Common Pitfalls

### Pitfall 1: expo-video 2.1.7+ 의 currentTime seek 버그 (iOS only)

**What goes wrong:** `player.currentTime = 0` 으로 seek 후 `timeUpdate` event 가 currentTime=0 을 잘못 emit (실제 위치와 다름) — KeypointOverlay 가 1번째 frame 으로 깜빡임.
**Why it happens:** PR #36308 (expo-video 2.1.7) 이 seek tolerance 를 ~5s 로 너무 크게 설정. PR #37672 (2025-07-08 merge) 이 fix (tolerances=0).
**How to avoid:** Wave 2 의 verify gate 에 "iOS 실 비디오 1건 seek 후 KeypointOverlay 1번째 frame 깜빡임 X" 추가. expo-video ~3.0.16 (SDK 54) 가 fix 포함됐는지 확인 — Open Q 1. 만약 SDK 54 까지 fix 미포함이면 `currentTime` 직접 read (event payload 가 아니라 `player.currentTime` 직접) 로 우회.
**Warning signs:** TestFlight 빌드 12 에서 belle 가 "오버레이가 영상 첫 frame 으로 튄다" 보고.
**Source:** `[CITED: github.com/expo/expo/issues/37299 + github.com/expo/expo/pull/37672]`

### Pitfall 2: react-native-svg + state-driven re-render 60fps 미달

**What goes wrong:** `setState(currentTime)` 매 frame 호출 시 React reconciler 가 9 Circle + 8 Line + Floating Label 을 매번 diff — 60fps 환경에서 jank 발생.
**Why it happens:** SVG element 가 child component (Reanimated worklet 아님) 라 main JS thread reconciliation 필요.
**How to avoid:** (a) `useEvent` 사용 시 re-render 횟수 = native timeUpdate emit 횟수 (timeUpdateEventInterval=0.033 → ~30fps). (b) Floating Label 의 위치/텍스트 변경은 frame index 가 바뀔 때만 (`useMemo([frameIndex])`). (c) **현실 검증:** 9 keypoint × 30fps 는 일반 폰에서 SVG 로 충분 — Phase 12.5 의 GrowthChart (수십 path) 가 이미 잘 작동.
**Warning signs:** "iOS Pixel-Capture / Android Profile GPU rendering" 으로 60fps 미달 검출. iOS Simulator 가 아닌 실 디바이스 검증.
**Source:** `[CITED: blog.swmansion.com/you-might-not-need-react-native-svg-b5c65646d01f]` (Skia 대안 언급) + `[CITED: docs.expo.dev/versions/v54.0.0/sdk/video/]` (timeUpdateEventInterval)

### Pitfall 3: `kismam.assess()` 의 user_angles / reference_angles kwarg 누락

**What goes wrong:** 현재 `pipeline/app.py` 의 3 call site (line 768, 772, 940) 모두 `kismam.assess(deviation)` 만 호출 — `user_angles` / `reference_angles` kwarg 없음. 결과: `JointAssessment.current_angle = None` + `target_angle = None` → `build_joints()` 가 `currentAngle` / `targetAngle` 필드 안 박제 → result.tsx 의 `angleGuide()` 가 null 반환 → "현재 N° → 기준 M°" 표시 0.
**Why it happens:** `kismam.assess()` 시그니처 는 user/reference 각도 kwarg 를 받지만, pipeline 박제 시 kwarg 전달 누락. `enrichJoints()` (result.tsx) 의 reference fallback 이 가렸음.
**How to avoid:** Wave 0 의 첫 task = 3 call site 에 `user_angles=` + `reference_angles=` kwarg 추가. user_angles = `{joint_key: float(angles[:, j].mean())}` for j in JOINT_KEYS (DTW match 구간 평균). reference_angles = mode1 = `ref.get("meanAngles")` 또는 reference 평균 / mode3_first = IPSF baseline dict (예: `{"left_knee": 175.0, ...}`) / mode3_progress = prev_angles 평균.
**Warning signs:** Wave 0 verify gate = `pytest -k "test_build_joints_with_real_angles" -v` PASS 후 prod 결과 doc 의 `result.joints[0].currentAngle != null` 검증.

### Pitfall 4: KeypointFrame 좌표 정규화 좌표계 혼동

**What goes wrong:** `PoseFrame.keypoints_2d` 는 "image normalized 0~1 좌표" 라 박제됨 (`pose_frame.py:137`) — 그러나 RTMW pipeline 의 `keypoints_2d` 실제 채움 여부 + 정규화 단위 (0~1 vs pixel) 검증 미완료. KeypointOverlay 가 잘못된 좌표계 가정하면 9 keypoint 가 영상 모서리에 몰리거나 화면 밖.
**Why it happens:** RTMW backbone 은 pixel 좌표 출력 (RTMPose 표준) — adapter layer 가 0~1 정규화 박제 여부 확인 필요.
**How to avoid:** Wave 0 의 grep audit = `grep -rn "keypoints_2d" backend/shared/python/sunity_shared/analysis/pose_engines/` + 실 분석 1건 fixture 의 `keypoints_2d` 값 inspect. 0~1 범위면 normalized, 100+ 면 pixel. KeypointOverlay 의 viewBox 박제 = pixel 인 경우 `videoSize.width × videoSize.height`, normalized 인 경우 `1 × 1` + `<G transform="scale(${w}, ${h})">`.
**Warning signs:** Wave 1 신영역 component 단위 test (실시 fixture 없이) 박제 + Wave 2 실 비디오 1건 검수에서 keypoint 가 영상 영역 안 그려지는지.

### Pitfall 5: `useEvent` 의 initial value 누락 시 첫 frame 미렌더

**What goes wrong:** `useEvent(player, 'timeUpdate', undefined)` — initial value 없으면 첫 timeUpdate emit 전까지 `currentTime = undefined`. KeypointOverlay 가 `frameIndex = NaN` 으로 빈 좌표 박제.
**Why it happens:** `useEvent` API 는 initial value 필수 (state-like).
**How to avoid:** `useEvent(player, 'timeUpdate', { currentTime: player.currentTime })` — initial = `player.currentTime` (대부분 0).
**Source:** `[CITED: docs.expo.dev/versions/v54.0.0/sdk/video/]`

### Pitfall 6: AsyncStorage 토글 상태 비동기 race (첫 렌더 시 OFF 깜빡임)

**What goes wrong:** AsyncStorage read 는 async — 토글 디폴트 = ON 이지만 첫 렌더 시 `useState(true)` → AsyncStorage read → `setState(false)` (사용자가 OFF 저장한 경우) 가 한 박자 늦음. UI 깜빡임.
**Why it happens:** Render → useEffect → read → re-render 순서.
**How to avoid:** (a) `useState(true)` + AsyncStorage read 가 `false` 면 즉시 `setState(false)`. 깜빡임 무시. (b) 또는 `useState(undefined)` + read 완료 전 KeypointOverlay 렌더 X (placeholder). Phase 12 권장 = (a) — 첫 진입 사용자 대다수가 ON 사용.
**Warning signs:** TestFlight 12 belle 검수에서 "결과 화면 진입 시 오버레이 한 번 꺼졌다가 켜진다" 보고.

### Pitfall 7: Firestore 1 MiB 초과 — 1 분 이상 영상

**What goes wrong:** 영상 길이 90s+ × 30fps × 9 keypoint × 2 axis × 4 byte = 194,400 byte (≈ 0.19 MiB). + `confidence` flat 81,000 byte + `reliability` 90 string + `forcePatternInference` + `dimensionScores` + `joints[]` + `forceSignalsReport` + `bodyComparisonReport` 모두 합치면 1 MiB 가까이 접근.
**Why it happens:** 한 doc 안 모든 영역 단일 write — keypoint 가 큰 비중.
**How to avoid:** (a) **결정:** 영상 60s cap 권고 (이미 design.md / MAX_VIDEO_BYTES 100MB 제약). 60s 안 = 0.12 MiB 안전. (b) **실제 영상 길이 분포:** 정은지 reference 5 sample 모두 30s 이내 (`[CITED: 08.1-SWEEP-EVIDENCE.md 25 axisMetric 표 — 5 영상]`) — Phase 12 production worst case 안전. (c) **fallback:** keypoint flat data 만 별도 Storage upload (analysisId 별 JSON file) + Firestore 에는 metadata 만 — v2 deferred (현재 불필요).
**Warning signs:** Wave 2 실 5s 비디오 1건 + 30s 비디오 1건 doc size 측정 → `firestore.write_size > 0.5 MiB` 면 알림.

### Pitfall 8: `enrichJoints` 의 reference fallback 잔존 → 실측 wiring 검증 누락

**What goes wrong:** Wave 0 의 `kismam.assess` wiring fix 후에도 `result.tsx::enrichJoints` 가 reference fallback (refMotion.meanAngles 로 targetAngle 덮어쓰기) 을 그대로 유지하면, backend 실측 채움 미동작 시에도 화면이 정상으로 보임 — 회귀 검증 누락.
**Why it happens:** enrichJoints 가 원래 시뮬 픽스처 보완 목적. wiring 완료 후 더 이상 필요 X.
**How to avoke:** Wave 1 에서 `enrichJoints` 단순화 — `targetAngle` 채워진 경우 (backend wiring 완료 후) reference fallback skip. 또는 함수 자체 제거 + result.tsx 내부 inline 박제.
**Warning signs:** Wave 0 verify gate 에 "result.tsx::enrichJoints 사용 회수 0 또는 reference fallback path 제거" assertion 추가.

### Pitfall 9: VideoCompare 의 폴링 vs KeypointOverlay 의 useEvent 동기 misalignment

**What goes wrong:** 기존 VideoCompare 는 `setInterval(250ms)` 폴링으로 `current` state 박제 (timeline label). KeypointOverlay 는 `useEvent(timeUpdate)` 로 native event 기반. **두 시간 source 가 다름** — 사용자가 timeline scrub 시 timeline label 은 250ms 후 update, KeypointOverlay 는 즉시. UX 미일관성.
**Why it happens:** 패턴 통합 미완료.
**How to avoid:** Wave 2 에서 VideoCompare 의 폴링도 `useEvent` 로 교체 (기존 250ms 단위 → ~33ms 단위로 더 부드러운 timeline). 단 회귀 우려 — Wave 2 의 task 박제 시점 belle 검수 후 결정. **권장 = 통합 (한 source of truth)**.
**Warning signs:** belle UAT 에서 "timeline label 과 keypoint 가 다른 시점 가리킨다" 보고.

## Code Examples

### 1. KeypointOverlay 기본 구조 (Wave 2 핵심)

```typescript
// Source: docs.expo.dev/versions/v54.0.0/sdk/video/ (timeUpdate event + useEvent)
//         + app/src/components/OctagonScore.tsx (react-native-svg 패턴 정합)
// 신설: app/src/components/KeypointOverlay.tsx

import React, { useMemo } from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Circle, Line, G, Rect, Text as SvgText } from 'react-native-svg';
import { useEvent } from 'expo';
import type { VideoPlayer } from 'expo-video';
import { colors } from '../theme';
import type { KeypointReport, KeypointName } from '../types/analysis';

export const KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0;  // D-12-C3 module const

type KeypointOverlayProps = {
  player: VideoPlayer | null;
  keypointReport: KeypointReport | null;
  referenceKeypointReport?: KeypointReport | null;  // mode1 only
  /** 영상 native size (pixel). VideoView onFirstFrameRender 시점 측정 또는 metadata. */
  videoSize: { width: number; height: number };
  /** mode1 = 두 keypoint 모두 비교, mode3 = 사용자만 */
  mode: 'mode1' | 'mode3';
  /** Joint 별 currentAngle / targetAngle (delta 강조 룰 입력). */
  jointAngles: Record<string, { current: number | null; target: number | null }>;
  visible: boolean;
};

const BONES: [KeypointName, KeypointName][] = [
  ['left_shoulder', 'right_shoulder'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip'],
  ['left_hip', 'right_hip'],
  ['left_hip', 'left_knee'],
  ['right_hip', 'right_knee'],
  ['left_shoulder', 'left_hand'],
  ['right_shoulder', 'right_hand'],
];

// joint key → 영상 angle joint key (Phase 12 9 keypoint vs 8 angle key 매핑).
// 어깨 좌우 = left_shoulder/right_shoulder, 무릎 = left_knee/right_knee, 등.
const JOINT_KEY_TO_ANGLE_KEY: Record<KeypointName, string | null> = {
  left_shoulder: 'left_shoulder',
  right_shoulder: 'right_shoulder',
  left_hip: 'left_hip',
  right_hip: 'right_hip',
  left_knee: 'left_knee',
  right_knee: 'right_knee',
  left_hand: 'left_elbow',   // 손 = elbow joint angle reuse (v1, v2 wrist 신설)
  right_hand: 'right_elbow',
  axis: null,                 // 중심축은 두 hip 중심 직접 그림 (각도 X)
};

export function KeypointOverlay(props: KeypointOverlayProps) {
  const { player, keypointReport, videoSize, jointAngles, visible } = props;

  // expo-video SDK 54 — timeUpdate event 로 currentTime 자동 re-render.
  // initial value 필수 (useEvent state-like).
  const { currentTime } = useEvent(
    player as any,
    'timeUpdate',
    { currentTime: player?.currentTime ?? 0 },
  );

  // 매 frame frame index lookup
  const frameIndex = useMemo(() => {
    if (!keypointReport || keypointReport.frames < 1) return 0;
    const idx = Math.floor(currentTime * keypointReport.fps);
    return Math.min(Math.max(idx, 0), keypointReport.frames - 1);
  }, [currentTime, keypointReport]);

  // 단일 frame reshape (전체 flat array reshape 회피 — 메모리 효율)
  const positions = useMemo(() => {
    if (!keypointReport) return null;
    const J = keypointReport.joints.length;
    const stride = J * 2;
    const offset = frameIndex * stride;
    const out: Partial<Record<KeypointName, { x: number; y: number }>> = {};
    for (let j = 0; j < J; j++) {
      const key = keypointReport.joints[j] as KeypointName;
      out[key] = {
        x: keypointReport.data[offset + j * 2],
        y: keypointReport.data[offset + j * 2 + 1],
      };
    }
    return out;
  }, [keypointReport, frameIndex]);

  // delta 강조 룰 (D-12-C3) — 각도 차이 ≥ 10° 인 joint 만 brand 색
  const highlightedJoints = useMemo(() => {
    const set = new Set<KeypointName>();
    for (const [kpName, angleKey] of Object.entries(JOINT_KEY_TO_ANGLE_KEY)) {
      if (!angleKey) continue;
      const a = jointAngles[angleKey];
      if (!a || a.current == null || a.target == null) continue;
      if (Math.abs(a.current - a.target) >= KEYPOINT_DELTA_HIGHLIGHT_DEG) {
        set.add(kpName as KeypointName);
      }
    }
    return set;
  }, [jointAngles]);

  if (!visible || !positions || !keypointReport) {
    return null;  // D-12-U6 fallback (caller 가 placeholder 렌더)
  }

  const W = videoSize.width;
  const H = videoSize.height;

  return (
    <View
      style={StyleSheet.absoluteFillObject}
      pointerEvents="none"
      accessibilityElementsHidden={!visible}
    >
      <Svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%">
        {/* Bones */}
        {BONES.map(([a, b], i) => {
          const pa = positions[a];
          const pb = positions[b];
          if (!pa || !pb) return null;
          const isHi = highlightedJoints.has(a) || highlightedJoints.has(b);
          return (
            <Line
              key={i}
              x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y}
              stroke={isHi ? colors.brand : '#FFFFFF'}
              strokeWidth={isHi ? 3 : 1.8}
              opacity={0.95}
            />
          );
        })}
        {/* Joints + floating angle labels */}
        {(Object.entries(positions) as [KeypointName, { x: number; y: number }][])
          .map(([key, p]) => {
            const isHi = highlightedJoints.has(key);
            const angleKey = JOINT_KEY_TO_ANGLE_KEY[key];
            const angle = angleKey ? jointAngles[angleKey]?.current : null;
            return (
              <G key={key}>
                <Circle
                  cx={p.x} cy={p.y} r={10}
                  fill={isHi ? colors.brand : '#FFFFFF'}
                  stroke={isHi ? colors.brand : 'rgba(0,0,0,0.6)'}
                  strokeWidth={1.5}
                />
                {isHi && angle != null && (
                  <G transform={`translate(${p.x + 12}, ${p.y - 9})`}>
                    <Rect x={0} y={0} width={48} height={18} rx={9}
                      fill={colors.brand} />
                    <SvgText x={24} y={13} fontSize={10}
                      fontWeight="600" fill="#FFFFFF" textAnchor="middle">
                      {`${Math.round(angle)}°`}
                    </SvgText>
                  </G>
                )}
              </G>
            );
          })}
      </Svg>
    </View>
  );
}
```

### 2. `useVideoPlayer` setup callback 에서 timeUpdate 활성화

```typescript
// Source: docs.expo.dev/versions/v54.0.0/sdk/video/ + GitHub issue 37299
// 박제 위치: VideoCompare.tsx 의 useVideoPlayer 호출

const leftPlayer = useVideoPlayer(leftUrl ?? null, (p) => {
  p.muted = true;
  p.loop = false;
  p.timeUpdateEventInterval = 0.033;  // ~30fps (default 0 = disabled)
  // Phase 12 신설 — KeypointOverlay 가 timeUpdate event 구독
});
```

### 3. `kismam.assess` 의 user_angles / reference_angles wiring fix (Wave 0)

```python
# Source: backend/shared/python/sunity_shared/analysis/kismam.py:97-137 (시그니처 이미 지원)
# 수정: backend/functions/pipeline/app.py:768, 772, 940

# Helper — DTW match 구간 angles → joint mean dict (skeleton.JOINT_KEYS 순서)
def _angles_to_mean_dict(angles: "np.ndarray") -> dict[str, float]:
    """(T, J) angles matrix → {joint_key: float} mean dict.

    JOINT_KEYS = ('left_elbow', 'right_elbow', ..., 'right_knee')  per skeleton.py.
    NaN 무시 (nanmean) — temporal.py 가 보간 후라 NaN 잔존 가능성 낮음.
    """
    import numpy as np
    from sunity_shared.analysis.skeleton import JOINT_KEYS
    out: dict[str, float] = {}
    for j, key in enumerate(JOINT_KEYS):
        col = angles[:, j]
        valid = col[~np.isnan(col)]
        if len(valid) > 0:
            out[key] = float(valid.mean())
    return out


# Wave 0 fix — pipeline/app.py:768 (mode3 first)
# Before:
#   assessments = kismam.assess(dimensions.extension_deviation(angles, profile))
# After:
user_mean = _angles_to_mean_dict(angles)
ipsf_baseline = dimensions.ipsf_baseline_angles(profile)  # 신설 helper or const dict
assessments = kismam.assess(
    dimensions.extension_deviation(angles, profile),
    user_angles=user_mean,
    reference_angles=ipsf_baseline,
)

# Wave 0 fix — pipeline/app.py:772 (mode3 progress)
user_mean = _angles_to_mean_dict(user_seg)  # DTW match segment 만 평균
prev_user_seg_mean = _angles_to_mean_dict(prev_user_seg)
assessments = kismam.assess(
    deviation,
    user_angles=user_mean,
    reference_angles=prev_user_seg_mean,
)

# Wave 0 fix — pipeline/app.py:940 (mode1)
user_mean = _angles_to_mean_dict(user_seg)
ref_mean = _angles_to_mean_dict(a_ref)  # reference (정은지) angles
assessments = kismam.assess(
    deviation,
    user_angles=user_mean,
    reference_angles=ref_mean,
)
```

**Verification:** Wave 0 단위 test = `test_build_joints_with_real_angles` — `assess()` 에 mock user/reference dict 전달 후 `JointAssessment.current_angle != None` + `assemble.build_joints()` 결과 `joint['currentAngle'] != None` 확인. 기존 pytest 408 PASS regression 0 검증.

### 4. ForcePatternCard variant='big' 렌더

```typescript
// Source: app/src/components/DimensionDetailModal.tsx (Phase 12.5 모달 패턴)
//         + Phase 9 forcePatternInference.findings 직접 소비
// 신설: app/src/components/ForcePatternCard.tsx

import React from 'react';
import { Pressable, View, Text, StyleSheet } from 'react-native';
import { colors, radius, spacing, typography } from '../theme';
import type { ForcePatternFinding } from '../types/analysis';

type ForcePatternCardProps = {
  finding: ForcePatternFinding;
  rank: 0 | 1 | 2;
  variant: 'big' | 'small';
  onTap: () => void;
};

const PATTERN_LABEL_KO: Record<string, string> = {
  release: 'RELEASE',
  pull: 'PULL',
  push: 'PUSH',
  brace: 'BRACE',
  rotate: 'ROTATE',
  unknown: '정보',
};

function confidenceLabel(c: number): { text: string; color: string } {
  if (c >= 0.7) return { text: '신뢰도 높음', color: colors.brand };
  if (c >= 0.5) return { text: '신뢰도 보통', color: colors.textSecondary };
  return { text: '신뢰도 낮음', color: colors.textDisabled };
}

export function ForcePatternCard({ finding, rank, variant, onTap }: ForcePatternCardProps) {
  const conf = confidenceLabel(finding.confidence);
  const patternLabel = PATTERN_LABEL_KO[finding.pattern] ?? '정보';
  if (variant === 'big') {
    return (
      <Pressable
        onPress={onTap}
        accessibilityRole="button"
        accessibilityLabel={`실패 원인 ${rank + 1}, ${patternLabel}, ${finding.jointHint ?? '정보'}, 자세히 보려면 탭`}
        hitSlop={8}
        style={styles.bigCard}
      >
        <View style={styles.bigHead}>
          <Text style={styles.rank}>{`#${rank + 1}`}</Text>
          <View style={[styles.patternChip, styles.patternChipBrand]}>
            <Text style={styles.patternChipText}>{patternLabel}</Text>
          </View>
          {finding.jointHint && (
            <View style={styles.jointChip}>
              <Text style={styles.jointChipText}>{finding.jointHint}</Text>
            </View>
          )}
          <Text style={[styles.confLabel, { color: conf.color }]}>{conf.text}</Text>
        </View>
        <Text style={styles.bigBody}>{finding.interpretation}</Text>
        <Text style={styles.tapHint}>탭하여 자세히 보기 ›</Text>
      </Pressable>
    );
  }
  // small variant — 174×110, 본문 2-line clamp
  return (
    <Pressable
      onPress={onTap}
      accessibilityRole="button"
      accessibilityLabel={`실패 원인 ${rank + 1}, ${patternLabel}, ${finding.jointHint ?? '정보'}, 자세히 보려면 탭`}
      hitSlop={8}
      style={styles.smallCard}
    >
      <View style={styles.smallHead}>
        <Text style={styles.rank}>{`#${rank + 1}`}</Text>
        <View style={[styles.patternChip, styles.patternChipSoft]}>
          <Text style={[styles.patternChipText, { color: colors.brand }]}>{patternLabel}</Text>
        </View>
      </View>
      {finding.jointHint && (
        <Text style={styles.smallJointHint}>{finding.jointHint}</Text>
      )}
      <Text style={styles.smallBody} numberOfLines={2} ellipsizeMode="tail">
        {finding.interpretation}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  bigCard: {
    width: '100%',
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: 1,
    borderColor: colors.divider,
    padding: 20,
    gap: 10,
  },
  smallCard: {
    flex: 1,
    backgroundColor: colors.cardBg,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.divider,
    padding: 12,
    gap: 6,
  },
  bigHead: { flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' },
  smallHead: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  rank: { ...typography.captionSmall, color: colors.textDisabled, fontWeight: '600' },
  patternChip: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 11 },
  patternChipBrand: { backgroundColor: colors.brand },
  patternChipSoft: { backgroundColor: colors.brandSoft ?? '#FFD9D2' },
  patternChipText: { fontSize: 9, fontWeight: '600', color: '#FFFFFF', letterSpacing: 0.5 },
  jointChip: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 11, backgroundColor: colors.softBg ?? '#F5F5F5' },
  jointChipText: { fontSize: 11, fontWeight: '500', color: colors.textPrimary },
  confLabel: { fontSize: 10, fontWeight: '500', marginLeft: 'auto' },
  bigBody: { fontSize: 14, fontWeight: '600', color: colors.textPrimary, lineHeight: 22 },
  smallJointHint: { fontSize: 10, color: colors.textSecondary, fontWeight: '500' },
  smallBody: { fontSize: 11, color: colors.textPrimary, lineHeight: 17 },
  tapHint: { fontSize: 11, color: colors.textDisabled, textAlign: 'right' },
});
```

### 5. result.tsx 6 영역 layout 재정비 (Wave 1)

```typescript
// Source: app/src/app/analysis/result.tsx 기존 779줄 안 끼워넣기 (D-12-A2)
// 변경 site = 현재 line 396-548 의 영역 순서 + 신영역 3 카드 추가
//
// 신영역 끼워넣기 (현재 line 472 → 차원 카드 직전):

{/* 점수 게이지 (영역 1) - 기존 그대로 */}
<View style={styles.card}>
  <OctagonScore score={result.overallScore} size={168} />
  ...
</View>

{/* 영역 2 신설: 영상 + 키포인트 오버레이 */}
<View style={[styles.card, styles.videoCard]}>
  <Text style={styles.sectionLabel}>
    {cmp.mode === 'mode1' ? '정은지 선수 vs 내 자세 (키포인트 오버레이)' : '내 영상 (키포인트 오버레이)'}
  </Text>
  <KeypointOverlayToggle ... />  {/* AsyncStorage persist */}
  <VideoCompare
    leftLabel="내 영상"
    rightLabel={cmp.mode === 'mode1' ? `${cmp.athleteName} 선수` : '지난 분석'}
    leftUrl={result.myVideoUrl}
    rightUrl={...}
    leftOverlay={
      overlayVisible && result.keypointReport ? (
        <KeypointOverlay
          player={leftPlayer}
          keypointReport={result.keypointReport}
          videoSize={leftVideoSize}
          mode={cmp.mode}
          jointAngles={jointAnglesByKey}
          visible
        />
      ) : null
    }
    rightOverlay={
      cmp.mode === 'mode1' && overlayVisible && referenceKeypointReport ? (
        <KeypointOverlay
          player={rightPlayer}
          keypointReport={referenceKeypointReport}
          videoSize={rightVideoSize}
          mode="mode1"
          jointAngles={refJointAnglesByKey}
          visible
        />
      ) : null
    }
  />
</View>

{/* 영역 3 신설: Phase 9 원인 카드 Top-3 */}
{result.forcePatternInference && (
  <View style={styles.findingsSection}>
    <Text style={styles.sectionTitle}>실패 원인 후보</Text>
    {result.forcePatternInference.findings.length === 0 ? (
      <ForcePatternCard
        finding={{
          pattern: 'unknown', phase: 'hold', sourceSignal: 'high_jitter',
          reason: '', interpretation: '이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다. 강사와 함께 확인하는 것을 권장해요.',
          confidence: 0, jointHint: null, warnings: [],
        }}
        rank={0} variant="big" onTap={() => { /* no-op */ }}
      />
    ) : (
      <>
        <ForcePatternCard
          finding={result.forcePatternInference.findings[0]}
          rank={0} variant="big"
          onTap={() => setDetailFinding(result.forcePatternInference!.findings[0])}
        />
        {result.forcePatternInference.findings.length > 1 && (
          <View style={styles.findingsSmallRow}>
            <ForcePatternCard
              finding={result.forcePatternInference.findings[1]}
              rank={1} variant="small"
              onTap={() => setDetailFinding(result.forcePatternInference!.findings[1])}
            />
            {result.forcePatternInference.findings.length > 2 && (
              <ForcePatternCard
                finding={result.forcePatternInference.findings[2]}
                rank={2} variant="small"
                onTap={() => setDetailFinding(result.forcePatternInference!.findings[2])}
              />
            )}
          </View>
        )}
      </>
    )}
  </View>
)}

{/* 영역 4: 차원 카드 (기존 그대로) */}
{/* 영역 5: 각도 가이드 (기존 코칭팁 → 6 영역 spec 박제 시 분리) */}
{/* 영역 6: 성장 차트 (mode3 only, 기존 그대로 — 단 위치 footer 직전) */}

{/* Phase 9 finding 모달 — 신설 */}
<ForcePatternDetailModal
  visible={detailFinding != null}
  finding={detailFinding}
  onClose={() => setDetailFinding(null)}
/>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `expo-av` (Video component) | `expo-video` (VideoView + useVideoPlayer hook) | Expo SDK 53 (2025) | 더 모던 API, separation of concerns (player ↔ view), event-based subscription | `[CITED: swmansion.com/blog/the-future-of-video-in-react-native-moving-from-expo-av-to-expo-video]` |
| `setInterval` 폴링 (currentTime) | `useEvent(player, 'timeUpdate', ...)` + `timeUpdateEventInterval` | expo-video 2.0+ | native side event emission, 정확도 + 배터리 효율 | `[CITED: docs.expo.dev/versions/v54.0.0/sdk/video/]` |
| `useState` 매 frame re-render | `useEvent` (state-like hook with event source) | expo SDK 53+ | re-render 횟수 = event emission 횟수 (자동) | `[CITED: docs.expo.dev/versions/v54.0.0/sdk/video/]` |
| react-native-svg + setState animation | Reanimated 3 worklets OR Skia | 2024-2025 | Reanimated/Skia 가 UI thread 에서 직접 동작 — 60fps 보장 | `[CITED: blog.swmansion.com/you-might-not-need-react-native-svg]` |

**Deprecated/outdated:**
- `expo-av` (Video component): SDK 53+ 에서 expo-video 권장. Phase 12 는 이미 expo-video 사용 — 영향 X.
- `react-native-video`: 별도 community package — Phase 12 무관.

**Note on Reanimated/Skia:** Phase 12 의 9 keypoint × 30fps 는 SVG + useEvent 로 충분 — Skia 도입은 Phase 12 scope OUT (별도 plan, v2).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | RTMW path 가 `PoseFrame.keypoints_2d` 를 실제로 채운다 (image-space 0~1 normalized 좌표) | §Pitfall 4 + §Code Examples §1 | 채우지 않으면 Wave 0 의 추가 task = `keypoints_3d` projection or RTMW adapter 확장 (대략 +1 일) `[ASSUMED]` |
| A2 | KEYPOINT_DELTA_HIGHLIGHT_DEG = 10° 는 정은지 vs 일반 사용자 joint angle 차이 분포에서 적절한 임계 | §Open Q 1 | 너무 빈번하면 사용자 피로 (한 영상에 9 keypoint 모두 red), 너무 드물면 의미 없음 → 실증 테스트 시점 belle 검수 박제 `[ASSUMED]` |
| A3 | 분석 영상 길이는 60s 이내가 일반 분포 (정은지 reference 5 sample 모두 30s 이내 verified) | §Pitfall 7 | 90s+ 영상이 흔하면 Firestore 1 MiB 접근, 별도 Storage upload 필요 — fallback path 신설 plan v2 `[VERIFIED: 08.1-SWEEP-EVIDENCE.md 5 영상 확인 + ASSUMED: 일반 사용자 영상 분포]` |
| A4 | expo-video ~3.0.16 (SDK 54) 는 PR #37672 의 seek tolerance fix 를 포함 | §Pitfall 1 | 포함 안 됐으면 iOS seek 후 KeypointOverlay 첫 frame 깜빡임 — workaround = `player.currentTime` 직접 read `[ASSUMED]` |
| A5 | Frontend 단위 test infra 부재 — manual UAT + typecheck 만으로 Phase 12 verify 가능 | §Open Q 3 + Deferred | 회귀 위험 (Phase 12.5 의 component 가 우연히 깨져도 typecheck 통과) — Phase 15 통합 sweep 에서 발견 `[ASSUMED]` |
| A6 | `forcePatternInference.modeContext` 가 mode1 / mode3_first / mode3_progress 모두 backend 가 자동 채움 (Phase 9 verified PASS) | UI 단 mode 분기 코드 X | 채워지지 않으면 UI 가 잘못된 interpretation 표시 — Wave 1 verify gate 에 mode 별 fixture 1 건 assertion 추가 `[VERIFIED: 09-VERIFICATION.md 4/4 SC PASS]` |
| A7 | KeypointName enum 의 'axis' 는 backend 가 어깨 중심 + 골반 중심을 한 keypoint 로 합쳐 좌표 emit (또는 두 hip 중심을 산출) | §Code Examples §1 | backend 가 axis 좌표 별도 emit X 시 UI 가 (left_shoulder + right_shoulder) / 2 + (left_hip + right_hip) / 2 자체 계산 — 안티 패턴 (D-12 §12 좌표 직접 계산 금지) → Wave 0 의 backend `build_keypoint_report` 에서 axis 좌표 명시 산출 박제 권장 `[ASSUMED]` |
| A8 | 9 keypoint × 30fps × 60s 의 react-native-svg 매 frame re-render 는 일반 iOS/Android 디바이스에서 60fps jank 없이 동작 | §Pitfall 2 | jank 발생 시 Skia 전환 plan v2 — TestFlight 12 belle UAT 시점 검증 `[ASSUMED]` |

**If this table is empty:** N/A — 8 가정 모두 명시. 우선순위 = A1 (RTMW keypoints_2d 가용성) > A4 (seek bug fix 적용) > A2 (delta 임계) > 나머지.

## Open Questions

1. **KEYPOINT_DELTA_HIGHLIGHT_DEG = 10° 의 sensitivity 적절성**
   - What we know: 정은지 elite axis tilt 분포 = 10-53° (Phase 8.1 sweep, joint angle 별개). IPSF tolerance = 20°. Phase 9 의 IPSF tolerance 20° 와 분리 (UX 시각 강조 임계).
   - What's unclear: 일반 사용자가 정은지 대비 joint angle 평균 deviation 분포 — production sweep evidence 부재.
   - Recommendation: **10° default 박제 + 실증 테스트 시점 belle 검수 follow-up 박제 (12-deferred-items.md)**. 일단 10° 가 너무 빈번하면 15° 로, 너무 드물면 7° 로 조정 가능 — module const 1 줄 수정.

2. **`PoseFrame.keypoints_2d` 의 RTMW path 실제 채움 + 좌표계 정합**
   - What we know: `pose_frame.py:137` 는 "image normalized 0~1 좌표" 박제. RTMW adapter 가 실제 채우는지 grep 미완료.
   - What's unclear: RTMW backbone 의 pixel 좌표 → normalized 변환 위치 (adapter level).
   - Recommendation: **Wave 0 첫 task = `grep -rn "keypoints_2d" backend/shared/python/sunity_shared/analysis/pose_engines/` + 실 분석 1건 fixture 의 keypoints_2d 값 inspect**. 채워지지 않으면 Wave 0 의 task 박제 = `keypoints_3d` 의 (x, y) projection + image 좌표계 변환 신설.

3. **Frontend 단위 test infra 신설 vs deferred**
   - What we know: `app/__tests__/` 부재, jest config 부재, `@testing-library/react-native` 미설치.
   - What's unclear: belle 가 Phase 12 안 infra 신설 vs Phase 15/v2 deferred 선호.
   - Recommendation: **deferred (v2 또는 별도 plan)** — Phase 12 scope = backend wiring + 신영역 component + layout 재정비. Test infra 신설은 별도 작업 (config + setup file + mocking RN/expo modules). Wave 2 verify gate = typecheck (`tsc --noEmit`) + manual UAT (실 비디오 1건 belle 검수).

4. **`axis` keypoint 좌표 backend 산출 방법**
   - What we know: D-12-C2 = 중심축 = 어깨 중심 ↔ 골반 중심. UI 가 직접 계산 시 안티 패턴 (D-12 §12).
   - What's unclear: backend `assemble.build_keypoint_report` 가 axis 좌표를 명시 emit 하는지.
   - Recommendation: **Wave 0 의 backend `build_keypoint_report` 에서 axis 좌표 명시 산출** — `axis = midpoint(left_shoulder, right_shoulder)` 와 `midpoint(left_hip, right_hip)` 두 점만 emit, UI 가 line 그림. 또는 single point (전체 중심) + axis_top / axis_bottom 두 keypoint 로 분할 — planner 박제.

5. **expo-video seek tolerance fix 가 SDK 54 ~3.0.16 에 포함됐는지**
   - What we know: PR #37672 (2025-07-08 merge) 가 seek tolerance=0 으로 fix. SDK 54 release 2025년 가을. ~3.0.16 의 release date 미확인.
   - What's unclear: 본 fix 가 ~3.0.16 에 포함됐는지.
   - Recommendation: **Wave 2 verify gate iOS 실 디바이스 1건 검수 — seek 후 KeypointOverlay 정확한 frame 표시 확인**. 미포함 시 workaround = `useState(currentTime)` 직접 update via `useEventListener` (event payload currentTime 무시 + `player.currentTime` 직접 read).

## Environment Availability

> Phase 12 = frontend + backend wiring + schema 신설. **외부 tool/service 의존 X**.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node + npm | App typecheck (`tsc --noEmit`) | ✓ | (기존) | — |
| Python 3.12 + pytest | Backend regression (`pytest tests/`) | ✓ | (기존) | — |
| iOS Simulator | Wave 2 verify (KeypointOverlay 시각 검증) | (가정) | — | Android Simulator + 실 iPhone TestFlight 빌드 |
| RTMW Pod | Wave 0 의 keypoints_2d 가용성 검증 | (활성, Phase 1 박제) | — | mock fixture 1건 (Phase 9 verify gate fixture 재사용) |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

> `workflow.nyquist_validation = true` (`[VERIFIED: .planning/config.json:20]`) — 본 섹션 박제 필수.

### Test Framework

| Property | Value |
|----------|-------|
| Backend Framework | pytest >=8,<9 (`[VERIFIED: backend/requirements-dev.txt]`) |
| Backend config | `backend/conftest.py` (기존, Phase 9 패턴 정합) |
| Backend quick run | `pytest backend/tests/phase09/ -x -q` (회귀 49 PASS 기준) |
| Backend full suite | `pytest backend/tests/` (550 PASS regression 검증) |
| Frontend Framework | **부재** (`[VERIFIED: app/package.json + grep app/__tests__ -d]`) |
| Frontend type-check | `cd app && npm run typecheck` (== `tsc --noEmit`, 단일 static gate) |
| Frontend manual UAT | TestFlight 빌드 12 belle 검수 (실 비디오 1건 위 KeypointOverlay 정합) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FEED-01 | `assemble.build_joints()` 가 `currentAngle` + `targetAngle` 필드 채움 (5 joint × 8 angle key 모두) | unit (backend) | `pytest backend/tests/phase12/test_build_joints_with_real_angles.py -x` | Wave 0 |
| FEED-01 | `kismam.assess()` user_angles / reference_angles kwarg 전달 시 `JointAssessment.current_angle != None` | unit (backend) | `pytest backend/tests/phase12/test_kismam_assess_with_angles.py -x` | Wave 0 |
| FEED-01 | `pipeline._process` 의 3 call site 가 `_angles_to_mean_dict` helper 사용 + mode 별 reference_angles 정합 | integration (backend) | `pytest backend/tests/phase12/test_pipeline_phase12_wiring.py -x` | Wave 0 |
| FEED-01 | `KeypointReport.__post_init__` validator (data length = T × J × 2) PASS / 위반 시 ValueError | unit (backend) | `pytest backend/tests/phase12/test_keypoint_report_validator.py -x` | Wave 0 |
| FEED-01 | `firestore_admin._validate_keypoint_report` scoped validator 박제 + `complete_analysis(..., keypoint_report=...)` kwarg | unit (backend) | `pytest backend/tests/phase12/test_firestore_keypoint_validator.py -x` | Wave 0 |
| VIS-01 | `userAnalyses.ts::normalize` 가 `result.keypointReport` 신설 필드 null-guard 통과 (구 doc / 신 doc 둘 다) | type-check (frontend) | `cd app && npm run typecheck` | Wave 0 (existing) |
| VIS-01 | `ForcePatternCard` 의 0/1/2/3 finding edge case 정확한 카드 수 렌더 | manual UAT | belle 검수 (실 분석 1건 mode1/mode3 각 1건) | Wave 1 |
| VIS-01 | `KeypointOverlay` 가 비디오 currentTime 진행에 따라 9 keypoint 좌표 정확히 이동 | manual UAT | belle 검수 (iOS 실 디바이스 TestFlight 12) | Wave 2 |
| VIS-01 | delta ≥ 10° 인 joint 의 brand 색 강조 + floating label "N°" 표시 | manual UAT | belle 검수 (mode1 fixture) | Wave 2 |
| VIS-01 | confidence < 0.5 frame 의 "추정 N°" + 회색 + ⓘ 표기 | manual UAT | belle 검수 (occlusion 영상 fixture) | Wave 2 |

### Sampling Rate

- **Per task commit:** `cd app && npm run typecheck && pytest backend/tests/phase12/ -x -q`
- **Per wave merge:** `pytest backend/tests/ -x -q` (전 phase regression 0)
- **Phase gate:** 전 backend pytest green + `cd app && npm run typecheck` clean + belle UAT (1 mode1 + 1 mode3_first + 1 mode3_progress 영상)

### Wave 0 Gaps

- [ ] `backend/tests/phase12/test_build_joints_with_real_angles.py` — FEED-01 (5 joint × 8 angle key cover)
- [ ] `backend/tests/phase12/test_kismam_assess_with_angles.py` — FEED-01 (kwarg path)
- [ ] `backend/tests/phase12/test_pipeline_phase12_wiring.py` — FEED-01 (3 call site 통합)
- [ ] `backend/tests/phase12/test_keypoint_report_validator.py` — FEED-01 (`__post_init__` strict validator)
- [ ] `backend/tests/phase12/test_firestore_keypoint_validator.py` — FEED-01 (Firestore scoped validator)
- [ ] `backend/tests/phase12/__init__.py` + `conftest.py` — 디렉터리 박제
- [ ] `backend/shared/python/sunity_shared/analysis/keypoint_frame.py` — 신설 (KeypointFrame + KeypointReport frozen dataclass)
- [ ] `backend/shared/python/sunity_shared/analysis/assemble.py::build_keypoint_report` — 신설 helper (pose_frames + axis 좌표 산출)
- [ ] `backend/shared/python/sunity_shared/firestore_admin.py::_validate_keypoint_report` — Phase 9 패턴 mirror scoped validator
- [ ] `docs/contract.md §9.12` — 신설 (KeypointFrame + KeypointReport spec)
- [ ] `app/src/types/analysis.ts` — KeypointName + KeypointReport interface 신설
- [ ] `app/src/lib/userAnalyses.ts::normalize` — KeypointReport null-guard 추가
- [ ] Frontend test infra: **deferred (v2)** — Wave 0 책임 X.

*(Wave 0 의 7 신설 + 6 수정 = Phase 9 의 atomic commit 패턴 정합 — 단일 commit 박제 권장 per D-09-U1 mirror.)*

## Security Domain

> `workflow.security_enforcement = true` (`[VERIFIED: .planning/config.json:42]`) + `security_asvs_level = 1`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (기존) | Firebase Anonymous Auth (변경 X) |
| V3 Session Management | no (기존) | Firebase ID Token (변경 X) |
| V4 Access Control | yes (기존) | Firestore Security Rules `users/{uid}/{**}` (변경 X) |
| V5 Input Validation | **yes (신설)** | `KeypointReport.__post_init__` validator + `_validate_keypoint_report` Firestore scoped validator (Phase 9 패턴 mirror) |
| V6 Cryptography | no | 신설 X — 기존 SOPS / Parameter Store / Firebase keys 그대로 사용 |
| V11 Business Logic | yes (기존) | `_validate_force_pattern_inference` + 신설 `_validate_keypoint_report` 의 nested-array reject |

### Known Threat Patterns for Frontend / Backend wiring

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Firestore doc 1 MiB 초과 (DoS) | Denial of Service | `KeypointReport.__post_init__` 가 `frames × joints × 2 == len(data)` 강제 + 영상 길이 60s cap (기존 MAX_VIDEO_BYTES 100 MB 가 간접 차단) |
| KeypointReport 의 nested list[list[float]] 주입 (corrupted doc) | Tampering | `_validate_keypoint_report` scoped validator (Phase 9 패턴 mirror) — nested list 발견 시 ValueError |
| AsyncStorage 토글 상태 위변조 (사용자 임의 수정) | Tampering | Low risk — UI 시각 토글 상태만 영향. 점수 / 카피 변경 X. mitigation X. |
| KeypointOverlay 가 비디오 위 잘못된 좌표 표시 → 사용자 오해 (예: 정은지 영상에 사용자 keypoint 박힘) | Spoofing | (a) `props.keypointReport` 와 `player` 의 동일 source binding 보장 (slot prop 패턴), (b) Wave 2 verify gate 에 mode1 split 영상 fixture belle 검수 |
| Firestore 신설 keypointReport 필드의 PII (예: 좌표가 사용자 식별 가능) | Information Disclosure | Low risk — 좌표는 개인 식별 정보 아님. 단 mode1 의 정은지 reference keypoint 는 정은지 동의 (이미 보유) 정합. |
| `force_pattern_overlay_enabled` AsyncStorage key 의 namespace collision | Tampering | 신설 key 1 개 — Firebase Auth 의 AsyncStorage 와 prefix 충돌 X (확인 후 `'@sunity:overlay_enabled'` 같은 namespace 권장) |

**No new authentication or session changes** — Phase 12 는 frontend UI + backend wiring 만 신설, auth/session/network endpoints 신설 X.

## Sources

### Primary (HIGH confidence)

- `[VERIFIED: app/package.json]` — expo-video ~3.0.16 + react-native-svg 15.12.1 + react 19.1.0 + react-native 0.81.5 (line 17-34)
- `[VERIFIED: docs.expo.dev/versions/v54.0.0/sdk/video/]` — useVideoPlayer + VideoPlayer + timeUpdate event + useEvent / useEventListener hook + timeUpdateEventInterval + onFirstFrameRender
- `[VERIFIED: github.com/expo/expo/issues/37299]` — expo-video 2.1.7+ iOS seek currentTime bug
- `[VERIFIED: github.com/expo/expo/pull/37672]` — seek tolerance=0 fix (2025-07-08 merge)
- `[VERIFIED: firebase.google.com/docs/firestore/quotas]` — 1 MiB doc size limit + nested array contribution
- `[VERIFIED: backend/shared/python/sunity_shared/analysis/kismam.py:82-137]` — `JointAssessment` dataclass + `assess()` 시그니처 (user_angles / reference_angles kwarg 이미 지원)
- `[VERIFIED: backend/functions/pipeline/app.py:768, 772, 940]` — `kismam.assess()` 3 call site 모두 kwarg 누락 (Wave 0 fix 대상)
- `[VERIFIED: backend/shared/python/sunity_shared/analysis/assemble.py:161-177]` — `build_joints()` 가 currentAngle/targetAngle 조건부 박제 (`a.current_angle is not None`)
- `[VERIFIED: backend/shared/python/sunity_shared/firestore_admin.py:343-404 + 407-472]` — Phase 9 `_validate_force_pattern_inference` + `complete_analysis(force_pattern_inference=)` 패턴 (Phase 12 mirror source)
- `[VERIFIED: backend/shared/python/sunity_shared/analysis/pose_frame.py:135-146 + 233]` — `Keypoint2D` dataclass + `PoseFrame.keypoints_2d: dict[str, Keypoint2D] | None`
- `[VERIFIED: app/src/types/analysis.ts:678-712]` — Phase 9 `ForcePatternFinding` + `ForcePatternInference` interface (Phase 12 KeypointReport mirror source)
- `[VERIFIED: app/src/lib/userAnalyses.ts:89-110]` — Phase 9 null-guard 패턴 (Phase 12 mirror source)
- `[VERIFIED: docs/contract.md §9.11 line 987-1042]` — Phase 9 contract 패턴 (Phase 12 §9.12 mirror source)
- `[VERIFIED: .planning/phases/08.1-axis-metric-redesign/08.1-SWEEP-EVIDENCE.md §2 25 axisMetric 표]` — 정은지 5 영상 × 5 phase tilt 분포 (모두 30s 이내 영상)
- `[VERIFIED: .planning/phases/09-forcedirectionpattern-3/09-RESEARCH.md]` — Phase 9 패턴 mirror source

### Secondary (MEDIUM confidence)

- `[CITED: docs.expo.dev/versions/v54.0.0/sdk/video/ — timeUpdate event payload]` — `{ currentTime, bufferedPosition, currentLiveTimestamp, currentOffsetFromLive }` shape
- `[CITED: docs.expo.dev/versions/v54.0.0/sdk/video/ — useEvent vs useEventListener]` — state-like vs effect-like pattern (Pattern 4)
- `[CITED: nrodrig1.medium.com/react-native-expo-video-and-using-timeupdate-af8a9812b3e1]` — useEvent currentTime extraction pattern
- `[CITED: blog.swmansion.com/you-might-not-need-react-native-svg]` — Skia 대안 권장 (Phase 12 scope 외)
- `[CITED: swmansion.com/blog/the-future-of-video-in-react-native-moving-from-expo-av-to-expo-video]` — expo-av → expo-video 마이그레이션 배경

### Tertiary (LOW confidence — flagged for validation)

- `[ASSUMED: A1 RTMW path 가 keypoints_2d 실제 채움]` — Wave 0 grep audit 로 검증 필요
- `[ASSUMED: A2 10° delta 임계 적절성]` — 실증 테스트 시점 검수
- `[ASSUMED: A4 expo-video ~3.0.16 이 seek fix 포함]` — Wave 2 iOS 실 디바이스 검증
- `[ASSUMED: A5 frontend test infra deferred]` — belle 결정 사항
- `[ASSUMED: A7 axis 좌표 backend 산출 방법]` — Wave 0 planner 결정
- `[ASSUMED: A8 react-native-svg 9 keypoint × 30fps 성능 충분]` — TestFlight 12 belle UAT 검증

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — 모든 의존 버전 `app/package.json` 직접 inspect + expo-video docs SDK 54 검증 + Firestore quota docs 검증.
- Architecture (Patterns 1-4 + Anti-patterns): HIGH — Phase 9 / Phase 12.5 verified-PASS 박제 1:1 mirror.
- Backend wiring (kismam.assess + assemble.build_joints + firestore_admin): HIGH — 코드 직접 inspect + 시그니처 + call site 확인.
- Schema design (KeypointFrame): HIGH — Phase 9 ForcePatternInference 패턴 mirror + Firestore nested-array 정합 검증 + size budget 계산.
- Pitfalls (1-9): MEDIUM-HIGH — 각 pitfall 의 root cause + warning sign + mitigation 모두 검증된 source 박제 (5 verified + 4 reasoned).
- frame data 가용성 (keypoints_2d): MEDIUM — `PoseFrame.keypoints_2d` 필드 존재 확인 (`[VERIFIED: pose_frame.py:233]`), 실제 RTMW path 채움 여부 미검증 (`[ASSUMED: A1]`).
- delta threshold sensitivity: MEDIUM — Phase 8.1 sweep evidence axis tilt 분포 활용 (joint angle 별개라 직접 비교 X). 실증 테스트 시점 검수 필요.
- Frontend test infra: HIGH — 부재 verified (`grep app/__tests__` 결과 0 + jest config 0 + @testing-library 미설치).

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (30 일 — expo-video SDK 54 안정, react-native-svg 15.x 안정). expo-video patch release (~3.0.20+) 시 Pitfall 1 seek bug 재검증 필요.

---

*Phase 12 추가: 2026-06-10 — KeypointReport schema 신설 + assemble.py 의 5 joint × 8 angle key 실측 wiring fix + react-native-svg / expo-video SDK 54 / Firestore flat 저장 패턴 박제. Phase 9 (D-09-U1 atomic commit) + Phase 12.5 (DimensionDetailModal slot pattern) 의 verified-PASS 박제 1:1 mirror.*

Sources:
- [Expo Video SDK 54 docs](https://docs.expo.dev/versions/v54.0.0/sdk/video/)
- [expo/expo issue #37299 (iOS currentTime bug)](https://github.com/expo/expo/issues/37299)
- [expo/expo PR #37672 (seek tolerance fix)](https://github.com/expo/expo/pull/37672)
- [Firestore quotas (Firebase docs)](https://firebase.google.com/docs/firestore/quotas)
- [The Future of Video in React Native (Software Mansion)](https://swmansion.com/blog/the-future-of-video-in-react-native-moving-from-expo-av-to-expo-video-6f4f78e51196/)
- [You Might Not Need react-native-svg (Software Mansion)](https://blog.swmansion.com/you-might-not-need-react-native-svg-b5c65646d01f)
- [expo-video timeUpdate pattern (Nick Rodriguez, Medium)](https://nrodrig1.medium.com/react-native-expo-video-and-using-timeupdate-af8a9812b3e1)
