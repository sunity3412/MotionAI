# Phase 12: 실측 각도 표시 + 키포인트 오버레이 + UIUX 한번에 — Context

**Gathered:** 2026-06-10
**Status:** Ready for research
**Mode:** mvp
**Trigger:** belle chain — Phase 9 ✓ 종료 후 "UIUX는 한번에 잡자" 결정

<domain>
## Phase Boundary

belle chain (Phase 12.5 ✓ → 16 ✓ → 12 = A 항목, "B→C→A 시퀀싱의 마지막") 종료 단계. ROADMAP Phase 12 본체 (실측 각도 + 키포인트 오버레이) 위에 **UIUX 한번에 통합** scope 박제 — Phase 9 finding 카드 노출 + 결과 화면 전체 layout 재정비 동시 진행.

본 phase 가 산출 (output 본체):

- **결과 화면 (app/src/app/analysis/result.tsx) 전체 layout 재정비** — 영역 5개 + (mode3) 성장 차트, 신규 순서 박제
- **실측 angleGuide 데이터 흐름 정합** — 5 joint **그룹** (어깨/골반/무릎/손 좌우 평균 + 중심축; storage = 8 body keypoint + axisData polyline) 전부 백엔드 `currentAngle`/`targetAngle` 실데이터로 표시 (assemble.py 167-168 이미 일부 wired, result.tsx 78-110 의 "시뮬 픽스처" 주석 제거 + 모든 joint cover)
- **VideoCompare.tsx 키포인트 오버레이 layer 신설** — react-native-svg 기반 8 body keypoint + axisData polyline overlay, 비디오 frame 동기화
- **mode1 delta 강조 룰** — 정은지 vs 사용자 joint angle delta ≥ 10° 시 자동 #FF4B33 강조 (둘 다 영상 위)
- **Phase 9 finding 카드 UI 박제** — finding[0] 큰 카드 + finding[1..2] 가로 작은 카드 × 2, tap → 자세히 모달 (Phase 12.5 패턴 정합)
- **occlusion + confidence 표기** — 저신뢰 각도 "추정 N°" + 회색 + ⓘ, 차원 카드 ⚠ 배지 + 모달 설명

본 phase 가 산출 X (downstream / 다른 phase 영역):

- LLM 자연어 풍부화 (Phase 9 finding interpretation 을 Gemini 가 동적 생성) → Phase 11 (CoachCommentHook + Gemini 자연어 번역만)
- 발끝 (toe) keypoint → v2 (ROADMAP Phase 12 scope 박제 정합)
- 다중 시점 / AI 카메라 앵글 합성 → Phase 4 redesign trigger 시점 ([[camera-angle-ai-single-view-synth]])
- 보완 운동 매핑 → Phase 13
- TestFlight + Mode1·Mode3 종합 검증 → Phase 15

</domain>

<decisions>
## Implementation Decisions

### (A) 결과 화면 layout 통합 — Phase 12.5 위에 신영역 끼워넣기

- **D-12-A1**: **결과 화면 영역 배치 순서 박제 (위 → 아래 스크롤)**:
  1. **점수 게이지** (기존 OctagonScore — Phase 12.5 와 동일 위치, 변경 X)
  2. **영상 + 키포인트 오버레이** (확장된 VideoCompare — 신영역. mode1 = 사용자/정은지 둘다 + delta 강조, mode3 = 사용자만)
  3. **Phase 9 원인 카드 Top-3** (신영역. finding[0] 큰 카드 + finding[1..2] 가로 작은 카드 × 2)
  4. **차원 카드** (기존 angle/line/stability — Phase 12.5 그대로)
  5. **각도 가이드 상세** (기존 angleGuide 출력 — 모든 joint cover + 실데이터 wiring 확인)
  6. **(mode3 only) 성장 차트** (기존 GrowthChart 그대로)
  - **Why 원인 카드를 차원 카드 앞으로**: 사용자 멘탈 모델 = "점수 → 영상 확인 → 왜? (원인) → 어떻게 (차원/각도 evidence)". Phase 9 finding 이 가장 actionable insight 이므로 evidence 보다 먼저 노출. 점수만 보고 닫는 사용자도 1번 finding 은 본다.

- **D-12-A2**: **기존 779줄 result.tsx 구조 유지 + 신영역 끼워넣기** (component 분리 / branch 분리 X). MVP 단순 ([[mvp-simple-pilot-quality]]). 단 신규 영역 (영상 오버레이 + 원인 카드) 은 별도 component 로 추출 — 향후 component 재사용 + 단위 test 단순화.

- **D-12-A3**: **feature flag X** (ROADMAP 박제 "feature flag + git branch" 권고는 빌드 11 stable 유지 가드. 본 phase 는 단일 main 브랜치에서 직접 진행 — Phase 9 처럼 atomic commit + per-task 단위로 검증). 단 EAS preview 채널에서 belle 가 빌드 11 별도 보유 (운영 안전망).

- **D-12-A4**: **신영역 component 분리** (D-12-A2 보강):
  - `app/src/components/KeypointOverlay.tsx` 신설 — VideoCompare 안 children 으로 absolute positioning + svg layer
  - `app/src/components/ForcePatternCard.tsx` 신설 — finding[0] / finding[1..2] 두 size variant + tap 시 모달
  - 기존 `VideoCompare.tsx` 는 KeypointOverlay child 받는 prop 만 확장 (slot pattern)

### (B) Phase 9 finding 카드 UI — finding[0] 강조 + finding[1..2] 보조

- **D-12-B1**: **카드 layout 박제**:
  - finding[0] = 큰 카드 (전체 너비 / 상단 패턴 chip (release / brace 등) + jointHint chip (몸 중심 / 엉덩이 관절 등) + interpretation 본문 큰 텍스트 + confidence 바)
  - finding[1..2] = 작은 카드 2개 가로 나란히 (각 너비 = 50% - gap. patternChip + jointHint chip 작게 + interpretation 본문 단축)
  - findings 길이 = 0 → 큰 카드 1개 (fallback body "이 영상에서는 분명한 힘 흐름 이슈 신호가 보이지 않습니다. 강사와 함께 확인하는 것을 권장해요.")
  - findings 길이 = 1 → finding[0] 만 큰 카드, 2/3 슬롯 비움
  - findings 길이 = 2 → finding[0] 큰 카드 + finding[1] 작은 카드 1개 (왼쪽), 오른쪽 슬롯 비움

- **D-12-B2**: **본문 출처 = Phase 9 canned KO 직접 표시** (현재). `forcePatternInference.findings[].interpretation` 그대로 렌더. Phase 11 (CoachCommentHook + Gemini 자연어 풍부화) 통합 시 동일 interpretation 필드를 LLM 풍부화 산출로 자동 교체 — 본 phase 인터페이스 변경 X.

- **D-12-B3**: **tap → 자세히 모달** (Phase 12.5 `DimensionDetailModal.tsx` 패턴 정합):
  - 모달 헤더 = pattern chip + jointHint chip + confidence 큰 표기
  - 본문 = interpretation 본문 (확장 — Phase 11 통합 시 LLM 자연어 출력)
  - 하단 = "이 원인은 어떻게 측정됐나" 한 줄 설명 (예: "lock 단계에서 어깨 각도가 25° 기울어진 신호 — IPSF 기준 20°")
  - "AI = 강사 보조 도구" footer (Phase 12.5 일관 — `[[feedback-no-echo-confirm]]`)

- **D-12-B4**: **mode 분기 자동** — `forcePatternInference.modeContext` 이미 mode1/mode3_first/mode3_progress 박제됐고 interpretation 본문에 prefix 포함 ("정은지 선수 기준 패턴과 비교했을 때, …" / "이번 첫 분석에서, …" / "지난 영상 대비, …"). 본 UI 는 분기 X — 본문 그대로 렌더.

### (C) 키포인트 오버레이 — 둘 다 + delta 강조

- **D-12-C1**: **오버레이 노출 영상 mode 별 분기**:
  - mode1 = 정은지 영상 + 사용자 영상 둘 다 오버레이 (비교 의미 살림)
  - mode3 = 사용자 영상만 오버레이 (mode3 = 자기 비교, 정은지 없음)

- **D-12-C2**: **joint 범위 박제** (ROADMAP Phase 12 SC #4 정합):
  - 어깨 (shoulder), 골반 (hip), 무릎 (knee), 손 (hand) — 좌우 양쪽 = 4 × 2 = 8 keypoint
  - 중심축 (axis) = 어깨 중심 ↔ 골반 중심 ↔ 무릎 중심 선
  - 발끝 (toe) = v2 deferred (SC #4 명시)

- **D-12-C3**: **delta 강조 룰 (감지 UI)** — belle 명시 요구:
  - mode1: 각 joint 의 angle delta = `|user.currentAngle - reference.currentAngle|`. delta ≥ 10° → 해당 joint 양쪽 keypoint + 연결 선 모두 #FF4B33 강조. delta < 10° → 흰색 (#FFFFFF).
  - mode3_first: IPSF 기준 각도 대비 delta. 동일 10° threshold.
  - mode3_progress: 이전 영상 대비 delta. 동일 10° threshold.
  - 10° 는 모듈 const `KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0` 박제 (Phase 9 의 `_IPSF_TOLERANCE_DEG = 20.0` 와 분리 — UX 시각 강조 임계 vs IPSF tolerance 도메인 임계).
  - delta 산출 = 비디오 재생 위치 (현재 frame timestamp) 기준 angle (이미 백엔드 frame-level data 보유 — `analysisDoc.angles` flat array).

- **D-12-C4**: **토글 디폴트 ON + OFF 옵션**:
  - 비디오 우상단 작은 토글 ("오버레이" 아이콘 + ON/OFF state)
  - 토글 상태 AsyncStorage 로 persist (사용자 선호 박제)
  - 디폴트 = ON (Phase 12 핵심 정보)

- **D-12-C5**: **렌더 기술 박제**:
  - `react-native-svg` 위 absolute positioning (이미 OctagonScore / GrowthChart 패턴 정합)
  - 비디오 frame 동기화 = `expo-video` 의 currentTime hook → keypoint frame-level data 에서 해당 timestamp 의 (x, y) 좌표 lookup
  - 영상 native size 와 svg viewport scale 맞춤 (`onReadyForDisplay` event 또는 비디오 dimensions ref)
  - **researcher 책임**: 정확한 expo-video API + react-native-svg overlay 동기화 best practice 확인 (Expo SDK 54 변경 가능성)

### (D) Confidence + occlusion 표기

- **D-12-D1**: **저신뢰 각도 표기 룰**:
  - confidence < 0.5 (또는 백엔드 frame.reliability == 'low') → "현재 N°" 대신 "현재 추정 N°" + 회색 컬러 + ⓘ 아이콘
  - ⓘ tap → 작은 tooltip / 또는 자세히 모달: "이 구간은 가림 또는 측정 불확실로 추정값입니다."
  - confidence 0.5 ~ 0.7 (medium) → 일반 컬러 + ⓘ 없이 표시 (의식적 노출 안 함)
  - confidence ≥ 0.7 (high) → 일반 컬러, 부가 표시 X

- **D-12-D2**: **occlusion 경고** (차원 카드 단위):
  - 차원 카드 (angle/line/stability) 상단 우측 ⚠ 배지 (해당 차원 frame 중 occlusion 추정 frame 비율 ≥ 20% 일 때)
  - 카드 tap → 모달 안 한 줄: "이 분석은 영상 X% 가 가림으로 추정 — 점수 신뢰 ↓" + 자세히 설명
  - 모든 frame high reliability → 배지 안 표시

- **D-12-D3**: **Phase 9 finding confidence 노출** (B 카드 일관):
  - finding 카드 안 confidence 바 = finding.confidence 0~1 값 시각화
  - confidence < 0.5 → 회색 바 + "낮음" 라벨
  - 0.5 ~ 0.7 → 중간 컬러 + "보통"
  - ≥ 0.7 → #FF4B33 + "높음"

### (E) 데이터 흐름 정합 (실측 wiring 검증)

- **D-12-E1** (2026-06-10 Codex 직접 리뷰 R2/R4/R11 반영): **kismam.assess() wiring fix + KeypointReport schema 신설**:
  - **8 body joint** (어깨/골반/무릎/손 좌우 4 × 2) — 백엔드 실측치 + **별도 axisData polyline** (어깨중심 ↔ 골반중심 ↔ 무릎중심 옵션, R2 정합)
  - mode 별 `target_source` enum 분기 (R4 정합):
    - mode1 = `reference_motion` (정은지 measured)
    - mode3_first = `extension_requirement` (extension-required joint 만 180°, 나머지 `unavailable` — IPSF baseline 박제 X)
    - mode3_progress = `previous_analysis` (이전 영상 measured)
  - **Wave 0A** (12-00) — kismam.assess() 3 call site wiring fix + RTMW keypoints_2d 실 채움 + axisData polyline 정의 + TargetSource enum (R1/R2/R4/R6 Codex 리뷰 BLOCKER 해소)
  - **Wave 0B** (12-01) — KeypointReport 3-way schema lockstep (TS + Python + docs §9.12 + Firestore validator) + Wave 0A 데이터 위에 박제
  - result.tsx 78-110 의 "시뮬 픽스처" 주석 제거 + currentAngle null fallback 처리 (Wave 1 책임)

- **D-12-E2**: **3-way contract lockstep** (`analysis.ts` ↔ `models.py` ↔ `assemble.py`):
  - `JointScore` interface 의 `currentAngle` / `targetAngle` 이미 있음 — 변경 X
  - 신설 = `KeypointReport` interface (frame-level keypoint 데이터) — 백엔드 `_dataclass_to_camel_case_dict` 자동 변환
  - 단, **frame-level keypoint 가 Firestore 에 저장되는지 확인 필수** — 이미 `analysisDoc.angles` (flat) 가 있으나 keypoint (x, y) 좌표는 별도 필드 필요할 수 있음. researcher 검증.

- **D-12-E3**: **Firestore nested-array 금지 정합** ([[firestore-nested-array-flat]]):
  - keypoint (x, y) 좌표는 flat 저장 + 읽는 쪽 reshape (Phase 9 정합 — `forcePatternInference.findings` flat list[dict] 패턴)
  - 예: `analysisDoc.keypoints` = `{joints: ["shoulder_left", "shoulder_right", ...], frames: 60, data: [x0_0, y0_0, x1_0, y1_0, ...]}` (flat)

### Universal Principle (Phase 12 전반)

- **D-12-U1**: **Phase 12.5 일관성 유지** — 새 영역 컴포넌트 스타일은 기존 `DimensionDetailModal.tsx` / `OctagonScore.tsx` / `GrowthChart.tsx` 시각 언어 1:1 mirror. 색상 토큰 / spacing / radius 는 모두 `src/theme/` 토큰 (메모리 [[motion-ai-figma-file]] 없으나 `[[ui-figma-first]]` precedent: design.md + Phase 12.5 코드 자체 판단으로 진행, belle 명시 결정).
- **D-12-U2**: **신영역 단위 test** — KeypointOverlay + ForcePatternCard 각각 fixture 기반 단위 test. snapshot test 회피 (시각 회귀는 design 변경으로 자주 깨짐) — 대신 props → 렌더 elements 카운트 + 핵심 텍스트 assertion.
- **D-12-U3**: **mode 분기 자동화** — Phase 9 / Phase 12.5 패턴 정합. UI 단에서 mode1/mode3 분기 코드 최소화 (백엔드 가 modeContext 박제, UI 는 그대로 렌더).
- **D-12-U4**: **light theme only** (CLAUDE.md §4 / design.md §10) — 다크 배경 절대 금지. 비디오 영역만 native black 배경 (영상 자체).
- **D-12-U5**: **브랜드 컬러 #FF4B33** — delta 강조 / confidence high 색 / 토글 활성 색 = `colors.brand`. 절대 변경 금지 (CLAUDE.md §4).
- **D-12-U6**: **frame-by-frame keypoint 데이터 가용성 가드** — `analysisDoc.keypoints` 없거나 빈 frames 데이터일 시 오버레이 그리지 않음 + ⓘ 배지 ("이 영상은 키포인트 데이터 미가용 — 영상만 표시"). MVP 단순 fallback.

### Claude's Discretion (researcher / planner 영역)

- **expo-video currentTime hook 의 정확한 API** — Expo SDK 54 의 useVideoPlayer / VideoPlayer 변경 가능성. researcher 가 docs 확인.
- **react-native-svg overlay 위 비디오 동기화 fps drift 처리** — 비디오 native fps vs JS thread fps mismatch 시 keypoint 가 영상 frame 보다 한 박자 늦거나 빨라질 가능성. researcher 가 베스트 프랙티스 확인.
- **KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0 임계값 정합성** — 도메인 검증 필요 (10° 가 시각적으로 의미있는 강조인지 vs 너무 빈번하게 발동하는지). belle 검수 → 실증 테스트 점검 리스트 박제 가능.
- **frame-level keypoint 가 Firestore 또는 Storage 어디 저장돼야** — 비디오 길이 60s × 9fps × 8 body keypoint × 2 (x,y) + axisData T × 3 × 2 = ~0.12 MiB. Firestore 1 MiB doc 안전 (R5 iter-1 정합). researcher → planner 결정.
- **신영역 component 위치 — `src/components/` 직접 or `src/components/result/` 서브폴더** — planner 결정.
- **mode3 성장 차트 위치 (배치 순서 6번)** — D-12-A1 박제됐으나 디테일 (성장 차트가 차원 카드 / 각도 상세 사이에 들어가는 게 더 자연스러운지) belle 검수 후 조정 가능.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### ROADMAP / REQUIREMENTS

- `.planning/ROADMAP.md` §Phase 12 (line 327-342) — goal + 4 SC + Phase 6/7 의존성 + UI hint:yes
- `.planning/ROADMAP.md` §Phase 12.5 (line 343 이후) — Phase 12.5 SC + 차원 카드 패턴 (B/C 영역 의존 source)
- `.planning/REQUIREMENTS.md` FEED-01 (line 60) — 각도 수치 + 키포인트 오버레이 단일 source
- `.planning/REQUIREMENTS.md` VIS-01 — 시각화 (확장 keyword)

### Phase 9 산출 (B 영역 입력)

- `backend/shared/python/sunity_shared/analysis/force_pattern.py` (Wave 0 + Wave 1 — verified PASS) — `ForcePatternFinding` 8 필드 + `ForcePatternInference` 5 필드 dataclass
- `backend/shared/python/sunity_shared/analysis/force_pattern_copy.py` — 18 canned KO 본문 (sourceSignal × modeContext) + jointHint 매핑 (몸 중심 / 엉덩이 관절 / 허벅지 안쪽 / 등 근육)
- `app/src/types/analysis.ts:653-712` — TS `ForcePatternFinding` + `ForcePatternInference` interface
- `app/src/lib/userAnalyses.ts:89-100` — Phase 9 null-guard (B 영역 데이터 흐름 정합)
- `docs/contract.md §9.11` (line 987-1054) — Phase 9 contract 명세

### Phase 12.5 산출 (A/B/D 패턴 source)

- `app/src/app/analysis/result.tsx` (line 1-779) — 현재 결과 화면 (Phase 12.5 까지 박제)
- `app/src/components/DimensionDetailModal.tsx` — 자세히 모달 패턴 (B3 / D2 source)
- `app/src/components/OctagonScore.tsx` — 점수 게이지 (A1 #1)
- `app/src/components/GrowthChart.tsx` — 성장 차트 (A1 #6)
- `app/src/components/VideoCompare.tsx` — 영상 비교 (A1 #2 — KeypointOverlay child 추가 대상)
- `app/src/components/CoachingTipDetailModal.tsx` — 코칭팁 모달 (D 영역 패턴 참조)
- `backend/shared/python/sunity_shared/analysis/assemble.py` (line 167-168) — currentAngle / targetAngle wiring (E1)

### Phase 6/7 (의존 — 정규화 각도 source)

- `backend/shared/python/sunity_shared/analysis/dimensions.py` — IPSF 기준 차원별 점수 + targetAngle source
- `backend/shared/python/sunity_shared/analysis/features.py` — angles_tj (T, J) matrix → JointScore 변환

### Phase 8 / 8.1 산출 (오버레이 frame-level 데이터)

- `backend/shared/python/sunity_shared/analysis/force_signals.py` (PhaseBoundary / AxisDeviationMetric) — frame-level reliability data (D1 confidence gate source)
- `app/src/types/analysis.ts:541-635` — Phase 8 산출 TS contract

### Theme + Design

- `app/src/theme/colors.ts` — `colors.brand = #FF4B33` (CLAUDE.md §4 / D-12-U5)
- `app/src/theme/typography.ts` — Pretendard
- `app/src/theme/index.ts` — radius / spacing / layout 토큰
- `design.md` (root) — UI 규칙 단일 source (Figma 없음 / `[[ui-figma-first]]` 박제 — belle 명시: "아직 design 안 그렸다, 자체 판단으로 진행")

### 박제 메모리 (정합 필수)

- `[[ui-figma-first]]` — Figma 없음 확인됨, design.md + Phase 12.5 코드 기반 자체 판단 (belle 명시 결정 박제 2026-06-10)
- `[[motion-ai-figma-file]]` — Motion AI Figma fileKey jrdI7kp245HkPfLB0nclsz (현재 frame 15개 + Phase 12.5 section, Phase 12 result 화면 신규 design 미작성)
- `[[mvp-simple-pilot-quality]]` — 기존 779줄 result.tsx 유지 + 신영역 끼워넣기 (D-12-A2 정합)
- `[[sim-scaffold-not-decorate]]` — Phase 9 canned KO 직접 표시, 시뮬 데이터 X (D-12-B2 정합)
- `[[mode3-progress-not-similarity]]` — mode3 = 절대 지표, % 일치 X (Phase 9 interpretation 본문 박제 정합)
- `[[feedback-analysis-first]]` — 분석 정확도 우선, "추정" 정직 (D-12-D1 정합)
- `[[feedback-no-echo-confirm]]` — AI = 강사 보조 도구 tone (D-12-B3 footer 정합)
- `[[firestore-nested-array-flat]]` — keypoint 좌표 flat 저장 (D-12-E3 정합)
- `[[no-baekje-filler]]` — 박제 단어 카피 안 들어감 (Phase 9 카드 본문 = 일반 사용자 어휘)
- `[[plan-vs-pivot-cross-check]]` — execute-phase 진입 전 plan scope vs active pivot 모순 확인
- `[[camera-angle-ai-single-view-synth]]` — Phase 12/13 종료 후 Phase 4 redesign 진입 trigger 박제 (본 phase 영향 X)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`app/src/app/analysis/result.tsx`** (779줄) — 현재 결과 화면. 점수 게이지 + 차원 카드 (Phase 12.5) + angleGuide 함수 (line 124) 보유. 신영역 (Phase 9 카드 + 오버레이) 끼워넣기 대상.
- **`app/src/components/VideoCompare.tsx`** (290줄) — 비디오 재생 비교. KeypointOverlay child slot 추가 대상.
- **`app/src/components/DimensionDetailModal.tsx`** (348줄) — 자세히 모달 패턴 (Phase 12.5). ForcePatternCard 의 tap → 모달 패턴 mirror.
- **`backend/shared/python/sunity_shared/analysis/assemble.py:167-168`** — `currentAngle / targetAngle` 일부 wired. Wave 0 에서 모든 joint cover 확인 + 누락 시 wiring 완성.
- **`backend/shared/python/sunity_shared/analysis/force_pattern_copy.py`** — Phase 9 18 canned KO + jointHint 매핑. ForcePatternCard 가 직접 소비.

### Established Patterns

- **Slot pattern** (VideoCompare children) — KeypointOverlay 를 VideoCompare 의 child 로 절대 위치 박제
- **Modal pattern** (DimensionDetailModal) — tap → BottomSheet 또는 fullScreen modal, 헤더 chip + 본문 + footer
- **mode 분기 자동화** — 백엔드 modeContext 박제, UI 단에서 분기 코드 최소 (Phase 9 / 12.5 정합)
- **3-way contract lockstep** — `analysis.ts` ↔ `models.py` ↔ `docs/contract.md` (Phase 6/7/8/8.1/9 패턴, 신설 KeypointReport interface 시 정합)
- **react-native-svg overlay** — OctagonScore + GrowthChart 박제. KeypointOverlay 동일 기술
- **`_dataclass_to_camel_case_dict` 자동 변환** — Phase 9 까지 박제. KeypointReport dataclass 신설 시 자동 적용

### Integration Points

- **`assemble.py::build_result`** — 결과 dict 생성 site. KeypointReport data 추가 박제 site (D-12-E2)
- **`firestore_admin.complete_analysis`** — Firestore 저장 site. keypoint flat 저장 분기 (D-12-E3)
- **`userAnalyses.ts::normalize`** — Firestore raw → AnalysisDoc null-guard. keypoint 신설 필드 null-guard 추가
- **`pipeline/app.py::_process`** — Phase 9 wiring 박제 site. keypoint frame data 출력 추가 (researcher 가 frame data 어디서 산출되는지 확인)

</code_context>

<specifics>
## Specific Ideas

- **belle 결정 (2026-06-10)**: "8.1 이 아직 더 남아있어? 그럼 숫자 낮은 것 부터" → 확인 결과 8.1 verified PASS @ 2b1b217. **belle chain 따라 12 진입 + UIUX 한번에 잡자** = 결과 화면 전체 (점수 / 영상 / 원인 카드 / 차원 / 각도 / 성장 차트) 동시 재정비. design 미작성 (Figma 안 그림) → 자체 판단으로 진행.
- **A1 의 "원인 카드 앞으로" 결정 근거**: Phase 9 finding = Top-3 actionable insight. 점수만 보고 닫는 사용자도 1번 finding 은 본다는 UX 가정. 차원/각도는 evidence — 원인 본 후 깊이 들어가는 사용자만. Phase 12.5 의 차원 카드 패턴 + Phase 9 카드 추가 = "왜 이 점수 → 그래서 원인 → 어떻게 측정됐는지" 자연 흐름.
- **C3 (오버레이 둘 다 + delta 강조)** belle 명시: "C3처럼 감지 UI는 있어야 사용자가 직관적". delta ≥ 10° 시 #FF4B33 강조 = 사용자가 한눈에 "어디 문제?" 인지 가능. 10° 는 UX 시각 강조 임계 (Phase 9 의 IPSF tolerance 20° 와 분리).
- **`[[ui-figma-first]]` 정합 박제**: 메모리 박제 = "Figma 우선", belle 결정 = "아직 design 안 그렸다" → 메모리 보존 (precedent), 본 phase 만 design.md + Phase 12.5 코드 + 메모리 원칙 자체 판단으로 진행. Figma 작성 후 phase 진입 시점 다시 적용.
- **Phase 11 통합 시점 자연 검증 path** — Phase 9 interpretation 본문 표시 → Phase 11 (CoachCommentHook + Gemini 자연어 번역) 통합 시 동일 interpretation 필드를 LLM 풍부화 산출로 교체. 본 phase UI 인터페이스 변경 X. Phase 11 = backend 변경만, UI 자동 적용.
- **frame-level keypoint 데이터 가용성 검증** = researcher 의 핵심 task. 현재 백엔드 pipeline 이 frame-by-frame keypoint (x, y) 좌표를 출력하는지 + 어디 저장되는지 (Firestore? Storage?) 확인.

</specifics>

<deferred>
## Deferred Ideas

### 발끝 (toe) keypoint
- **Why deferred**: ROADMAP Phase 12 SC #4 명시 "어깨/골반/무릎/손 + 중심축, 발끝은 v2".
- **Target phase**: v2.

### LLM 풍부화 interpretation
- **Why deferred**: Phase 11 (CoachCommentHook + Gemini 자연어 번역) 책임. Phase 12 UI 는 현재 Phase 9 canned 직접 표시, Phase 11 통합 시 동일 필드 LLM 풍부화 자동 교체.
- **Target phase**: Phase 11.

### AI 카메라 앵글 합성 (Higgsfield Change Camera 류)
- **Why deferred**: Phase 4 redesign trigger. 본 phase 와 별개.
- **Target phase**: Phase 4 redesign (Phase 12/13 종료 후).

### 다중 시점 촬영 UX
- **Why deferred**: Phase 4 정식 scope (현재 ROADMAP — belle 의도와 모순. 메모리 박제 후 redesign 예정).
- **Target phase**: Phase 4 redesign.

### TestFlight + Mode1·Mode3 종합 검증
- **Why deferred**: Phase 15 책임.
- **Target phase**: Phase 15.

### 보완 운동 매핑
- **Why deferred**: Phase 13 책임.
- **Target phase**: Phase 13.

### KEYPOINT_DELTA_HIGHLIGHT_DEG 임계값 정밀화
- **Why deferred**: 10° 는 D-12-C3 박제 default. 실증 테스트 시점 (학원 파일럿) 에서 빈도 + UX 적절성 검수. 변경 시 const 값만 수정.
- **Target phase**: 실증 테스트 점검 리스트 (`.planning/phases/09-forcedirectionpattern-3/deferred-items.md` 패턴 정합 — 본 phase 종료 후 `12-deferred-items.md` 박제).

### Figma design 작성 후 재진입
- **Why deferred**: belle 가 향후 Figma 작성 시 (`[[ui-figma-first]]` 정합) 본 phase 또는 후속 phase 에서 UI 재정비 가능. 본 phase 의 component 분리 (KeypointOverlay / ForcePatternCard) 가 향후 Figma 적용 시 단위 교체 path 박제.
- **Target phase**: Figma 작성 시점.

### 성장 차트 위치 미세 조정
- **Why deferred**: D-12-A1 #6 으로 박제됐으나 차원 카드 ↔ 각도 상세 사이로 이동 가능성 (mode3 사용자 입장에서 자연 흐름 검토 필요). belle 검수 시점에 조정.
- **Target phase**: 실증 테스트 점검 리스트.

</deferred>

<follow_ups>
## Follow-ups (Wave-specific signal)

### Wave 0 종료 후 — assemble.py wiring 전수 확인
- **Trigger**: Wave 0 commit + `pytest tests/phase06/ tests/phase07/ -x -q` 회귀 0
- **Action**: 8 body joint (어깨/골반/무릎/손 좌우 4 × 2) + axis polyline 의 currentAngle / targetAngle 이 모든 mode (mode1 / mode3_first / mode3_progress) 에서 채워지는지 데이터 흐름 grep + 실 분석 1건 test fixture 검증

### Wave 1 종료 후 — UI 시각 회귀 + 단위 test
- **Trigger**: Wave 1 commit + `cd app && npm run typecheck` 0 error
- **Action**: 신영역 component (KeypointOverlay / ForcePatternCard) 단위 test PASS + Wave 0 의 wiring 회귀 0 + Phase 9 finding 카드 0/1/2/3 케이스 모두 렌더 확인

### Wave 2 종료 후 — frame-level keypoint 데이터 정합
- **Trigger**: Wave 2 commit + 비디오 + 오버레이 동기화 단위 test PASS
- **Action**: 실 분석 1건의 keypoint 데이터가 비디오 frame 위에 정확히 그려지는지 belle UAT (TestFlight 빌드 12 등). delta 강조 룰 발동 빈도 검증.

### Phase 11 통합 시점 — interpretation LLM 풍부화 자연 검증
- **Trigger**: Phase 11 (CoachCommentHook + Gemini 자연어 번역) 통합
- **Action**: Phase 12 의 ForcePatternCard 가 interpretation 필드 LLM 풍부화 산출 정상 렌더 — UI 변경 X, backend 변경만으로 통합

### Phase 15 통합 시점 — production sweep
- **Trigger**: Phase 15 (Mode1·Mode3 실영상 + 신뢰도 게이트 + TestFlight)
- **Action**: 정은지 + 학생 영상 sweep → Phase 12 결과 화면 (오버레이 + Phase 9 카드 + 각도 가이드) 정상 동작 검증. delta 강조 빈도 + 사용자 인지 검증.

### 실증 테스트 점검 리스트 (학원 파일럿 시점)
- KEYPOINT_DELTA_HIGHLIGHT_DEG = 10.0 적절성
- 성장 차트 위치 자연성
- Phase 9 카드 vs 차원 카드 순서 사용자 흐름
- 토글 (오버레이 ON/OFF) 사용자 선호도

</follow_ups>

## Next Steps

1. `/gsd-ui-phase 12` — UI-SPEC.md 생성 (Figma 없음 → design.md + Phase 12.5 코드 기반 자체 UI-SPEC 박제. KeypointOverlay + ForcePatternCard 신규 component design + 결과 화면 layout 재정비 명세)
2. `/gsd-plan-phase 12` — wave 분할 + plan 박제. 예상 wave 구조:
   - **Wave 0A** (12-00): data contract foundation — RTMW adapter keypoints_2d 실 채움 (R1) + kismam.assess() 3 call site wiring fix (R4 CRITICAL) + axisData polyline 정의 (R2) + targetSource enum (R4) + Keypoint2D.raw_visibility confidence source 명시 (R6). **Codex 리뷰 2026-06-10 4 blocker 해소**.
   - **Wave 0B** (12-01): KeypointReport 3-way schema lockstep (TS + Python + docs §9.12 + Firestore scoped validator + 8 body keypoint + axisData 별도 field + fps required + size budget test). Single atomic commit (D-09-U1 mirror).
   - **Wave 1** (12-02): UI 신영역 3 component (KeypointOverlay + ForcePatternCard + ForcePatternDetailModal) + VideoCompare **render prop** slot (R7) + result.tsx 6 영역 layout 재정비.
   - **Wave 2** (12-03): useEvent(player, 'timeUpdate', ...) 동기화 + delta ≥ 10° 강조 + 토글 AsyncStorage (`@sunity:keypoint_overlay_enabled`, R8) + confidence/occlusion 표기 + iOS TestFlight UAT.
3. plan-review (cross-AI Codex 등 권장) — D-12-C3 delta 강조 룰 + D-12-E2 contract lockstep 검증
4. Wave 0 → 1 → 2 순차 실행 + 각 wave 종료 시 회귀 PASS gate
5. Wave 2 종료 → Phase 12 verifier → ROADMAP Phase 12 entry "completed" 표시
6. Phase 11 / Phase 15 통합 시점 자연 검증 (본 phase scope OUT)
7. 학원 파일럿 시점 실증 테스트 점검 리스트 검수 (12-deferred-items.md 박제)
