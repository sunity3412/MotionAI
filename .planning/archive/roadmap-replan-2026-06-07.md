# 로드맵 재정렬 — 2026-06-07

> 목적: 빌드 11 TestFlight 실분석 PASS + Phase 5 close-out 직후, belle 의 의식적 시퀀싱 (A+B+C 우선, Phase 2~11 보류) 을 단일 문서로 정리한다. **외부 AI 검토용** (Codex / gpt-5.5).
>
> 작성: Claude Code, belle 명시 지시.

---

## 0. 한 줄 요약

빌드 11 (실분석 PASS) + Phase 5 12차 sweep (D-01 게이트 통과) + Phase 16 데이터 박제 = "분석은 동작한다" 상태. belle 의 다음 우선순위 = **A (Phase 12 실측 각도 + 키포인트 오버레이) + B (UI transparency, result.tsx 차원 카피) + C (Phase 16 코드 통합)** — 즉 "보이는 신뢰 강화 + 학원 용어 통합" 을 먼저 하고 Phase 2~11 (체형 정규화 / 두 엔진 본체 / CoachCommentHook) 은 파일럿 후 v1.5 로 연기. 파일럿 목표 = 정은지 시연 + 폴스포츠 학원 실증.

---

## 1. 현재 코드 상태 (사실 vs ROADMAP.md outdated)

| Phase | ROADMAP 표기 | 실제 코드 상태 (commit d12cefc 기준) | 격차 |
|---|---|---|---|
| 1 (PoseEngine + RTMW + R&D 격리) | 21/24 In Progress | **사실상 완료** — Plan 01-25 atomic swap NLF→RTMW = commit 2a8aa72. PoseEngine Protocol + MediaPipe + RTMW + MediaPipe+lifter 어댑터 4종 (`backend/shared/python/sunity_shared/analysis/pose_engines/`). production pipeline = RTMW 사용. 미완 = Plan 01-23 sweep (Phase 5 sweep 12차로 대체됨) + Plan 01-24 R&D 격리 명시 (NLF 가 import 차단되어 있지만 .samignore 명시 미확인) | ROADMAP 갱신 누락 |
| 2 (BodyNormalizationProfile) | 0/TBD Not started | **부분 진척** — `body_normalization.py` 모듈 존재 (RTMW segment 기반 spec). Plan 미작성 | scope 명시 미완 |
| 3 (자가입력 BodyProfileInput) | 0/TBD Not started | 미시작 | — |
| 4 (다중 시점 + occlusion) | 0/TBD Not started | 미시작. 메모리 [[single-camera-first-multi-view-last]] = "단일 카메라 우선, 다각도 최후" | — |
| 5 (Gemini 기술 인식기) | 3/6 In Progress | **사실상 완료** — 12차 sweep D-01 PASS (2026-06-05 12:20 UTC). `phase5_ready_to_release_d16_block=True`. 빌드 11 실분석 PASS (mode1 94 + mode3 100). 미완 = ROADMAP close-out 마킹만 | ROADMAP 갱신 누락 |
| 6~11 (두 엔진 본체) | 0/TBD Not started | 미시작 — belle 의식적 보류 | scope 결정 필요 |
| 12 (실측 각도 + 키포인트 오버레이) | 0/TBD Not started | 미시작. `result.tsx` 에 `JointScore.currentAngle/targetAngle` 표시 부분 존재 (FEED-01 부분), 오버레이 미구현 (VIS-01 미시작) | A scope 정의 필요 |
| 13 (보완 운동) | 0/TBD Not started | 미시작 | — |
| 14 (정은지 reference) | 0/TBD Not started | **부분 진척** — 5개 reference motion 등록 완료 (ref-climb / ref-foxtop / ref-foxtop-split / ref-invert / ref-sideway-spin). 다각도 캡처 가이드 미작성 | 후속 plan 결정 필요 |
| 15 (Mode 1·Mode 3 + 신뢰도 게이트 + TestFlight) | 0/TBD Not started | **빌드 11 PASS** — belle 실분석 정합. letterSpacing SIGABRT + presigned playback-url + mode3 first 함정 fix 완료. 미완 = 고수 위양성 없음 검증, 학원 게스트 실기기 완주 검증 (파일럿 실증) | 부분 진척 |
| 16 (Studio Term Foundation v1) | 1/1 Complete | **데이터/스펙/카피 완료** (2026-06-02). 코드 통합 미완 — AKA 매핑 13개 / 5트랙 채점 v1 (a)+(c)+Page 9 / 분기 2 정은지 reference / 분기 3 자동 수집 = 코드 path 미통합 | C scope 정의 필요 |

**핵심 사실**:
- Phase 1 / 5 / 16 = 사실상 완료, ROADMAP 갱신 필요
- Phase 2 / 3 / 4 / 6~11 / 13 / 14 = belle 의식적 보류
- Phase 12 (A) / 16 코드 통합 (C) + B (UI transparency, 신설) = 다음 우선

---

## 2. belle 의 시퀀싱 의도 (A/B/C + 보류 Phase 들)

### 2-1. 채택 — A + B + C (다음 진행)

| 코드 | Phase | scope | 작업량 추정 |
|---|---|---|---|
| **A** | Phase 12 (실측 각도 + 키포인트 오버레이) | (a) `result.tsx` 의 `JointScore.currentAngle` = backend 실측값 (이미 부분 구현) (b) 영상 위 어깨/골반/무릎/손 keypoint + 중심축 오버레이 (`expo-video` 위 SVG overlay), (c) backend `assemble.py` 가 frame-by-frame keypoint timeline 을 `playbackKeypoints` 로 저장 → Firestore → app 소비 | **큰 scope** (5 plan, 2주~) |
| **B** | UI transparency (Phase 12.5 신설 가칭) | `result.tsx` 차원별 (`angle`/`line`/`stability`/`balance`) 카드에 (a) "이게 무슨 기준 (IPSF Code of Points + 정은지 측정값)" 한 줄 카피, (b) 가중치 표시 (예: "각도 40% + 라인 30% + 안정성 30% = overall"), (c) "왜 이 점수인지" 부가 카피 (어디서 깎였는지). 데이터 contract 약간 확장 (`dimensionExplanation` 필드 1~2개). | **작은 scope** (1 plan, 1~3일) |
| **C** | Phase 16 코드 통합 | (a) AKA 매핑 13개 → backend recognizer 가 사용자 입력 동작명 매핑 + Gemini prompt 반영, (b) 5트랙 채점 v1 (a)+(c)+Page 9 = `assemble.py` 가 4트랙 점수 출력 + result.tsx UI 4트랙 카드, (c) 분기 3 자동 수집 = `pending_terms` Firestore 컬렉션 + UX 카피 노출 (분석 시작 시 "이 동작이 처음이라 분류했어요"). | **중간 scope** (2~3 plan, 1주~) |

### 2-2. 보류 — Phase 2 / 3 / 4 / 6~11 / 13 / 14 (파일럿 후 v1.5)

| Phase | 보류 이유 |
|---|---|
| 2 (BodyNormalizationProfile) | 두 엔진 (체형 정규화 + 힘 패턴) 의 인풋. 현 RTMW + IPSF (a)+(c)+Page 9 + 정은지 reference 만으로 5/5 PASS 충족. BodyNormalizationProfile 의 핵심 가치 = "체형이 다른 사용자에게 위양성 감점 방지" — 그러나 파일럿 = 동일 학원 수강생 그룹 → 위양성 위험 작음. 파일럿 후 데이터 보고 결정. |
| 3 (자가입력 BodyProfileInput) | Phase 2 의존. Phase 2 보류 시 자동 보류. |
| 4 (다중 시점 + occlusion 게이트) | 메모리 [[single-camera-first-multi-view-last]] "단일 카메라 우선, 다각도 최후 수단" 정합. 단일 카메라 path 가 RTMW + Gemini 로 동작 검증됨. 다각도는 단일이 막힌 후 도입. |
| 6 (체형 정규화 비교) | Phase 2 의존. |
| 7 (차이 분류) | Phase 6 의존. |
| 8 (중심축·접촉점·jerk) | 힘 패턴 본체. 학원 강사 (도입 결정권자) 가 "각도보다 힘이 핵심" 박제했으니 v1.5 진입 시 가치 큼. 파일럿 후 데이터 검증 후 진입. |
| 9 (ForceDirectionPattern + 실패 후보 3개) | Phase 8 의존. |
| 10 (부상 위험 신호) | Phase 8 의존. SAFE-01 v1 정신 보존, 파일럿 후. |
| 11 (CoachCommentHook + Gemini 자연어 번역만) | 현재 Cerebras path 가 동작 중. CoachCommentHook 데이터 구조 추가는 가치 있으나, 파일럿 사용자 = "강사 보조" 카피만 부분 진행 가능 (B scope 안에서). 본체는 v1.5. |
| 13 (보완 운동 추천) | PERS-03 v1. 파일럿 후 분석 → 행동 매핑 데이터 보고. |
| 14 (정은지 reference 다각도) | 5개 reference 등록됨 (단일 카메라). 다각도 캡처 = Phase 4 의존. Phase 4 보류 = 다각도 reference 보류. 단일 카메라 reference 5개로 파일럿 진입 가능 (빌드 11 검증). |

### 2-3. 보류 reasoning (belle 박제 정신 정합)

- 메모리 [[feedback-analysis-first]] = "분석이 최우선". 현 상태 = RTMW + Gemini 가 5/5 PASS (Phase 5 12차 sweep) + 빌드 11 실분석 mode1 94 + mode3 100. = "분석 정확도" 박제 정신 정합.
- 다음 게이트 = **사용자 신뢰** (B) + **학원 용어 통합** (C) + **실측 시각화** (A).
- 메모리 [[mvp-simple-pilot-quality.md]] = "MVP 단순 + 실증 퀄리티". A+B+C = 시연/파일럿 직전 필요. Phase 2~11 = 파일럿 후 v1.5 진입 (실증 데이터 보고 결정).

---

## 3. A / B / C scope 상세

### 3-1. A = Phase 12 (실측 각도 + 키포인트 오버레이)

**가치**: 사용자가 "현재 87° → 기준 110°" 를 영상 위 keypoint 와 같이 본다. "수치는 보조, 원인이 핵심" 정신 — 오버레이가 원인 시각화.

**Scope** (5 plan 후보):
- Plan 12-01: backend `assemble.py` 가 `playbackKeypoints` (frame-by-frame timeline) 박제 → AnalysisDoc Firestore 저장. 메모리 [[firestore-nested-array-flat]] 정합 (flat 저장).
- Plan 12-02: `result.tsx` 각 JointScore 카드 "현재 87° → 기준 110°" 박제 검증 (기존 부분 구현 정합 검사 + fixture path 제거).
- Plan 12-03: VideoCompare 위 SVG keypoint 오버레이 (어깨/골반/무릎/손) + 중심축 (axis_vector) 그리기.
- Plan 12-04: keypoint 동기화 (영상 currentTime ↔ frame index) 박제.
- Plan 12-05: 실 영상 5종 검증 (정은지 reference 5개) + belle 시연 PASS.

**의존성**: 없음 (Phase 1/5 완료 위에서 진행). Phase 2/6/7 보류와 무관.

**위험**: backend payload 증가 (playbackKeypoints frame-by-frame). Firestore 1MB 제한 검증 필요 — 5초 영상 × 9fps × 8 keypoint × 2D = 약 10KB, 30초 = 60KB, 60s+ 영상은 별도 검증.

### 3-2. B = UI transparency (Phase 12.5 가칭, 작은 scope)

**가치**: 사용자가 "아 이래서 이런 평가구나" 박제. belle 의문 "94 vs 95% 갭" 정합 — 차원별 카피 + 가중치 표시.

**Scope** (1 plan):
- (a) `result.tsx` 차원별 카드 (`angle`/`line`/`stability`/`balance`) 에 한 줄 카피 — "IPSF Code of Points 기준 + 정은지 측정값" / "관절 angle 평균" / "동작 안정도 (frame inter-diff)" 등.
- (b) 가중치 표시 — "각도 40% + 라인 30% + 안정성 30%" (현재 `assemble.py` 의 overall 산식 정합).
- (c) "왜 이 점수인지" 부가 카피 — 차원별 deficit (예: "오른쪽 어깨 22° 더 펴주세요 = -8점").
- (d) data contract 약간 확장: `analysis.ts` ↔ `models.py` 에 `dimensionExplanation: { weight: number; baseline: string; deficitSummary: string }` 추가.

**의존성**: 없음 (현재 contract 위에 확장).

**작업량**: 1 plan, 1~3일. simplify 정신 정합 (작은 단위).

**A 와의 의존**: A = keypoint 오버레이 + 실측 = "어디" 시각화. B = 차원별 카피 + 가중치 = "왜" 텍스트. **독립** — B 가 A 전에 진행 가능 (작은 scope 우선 가치 큼).

### 3-3. C = Phase 16 코드 통합 (학원 용어 + 5트랙)

**가치**: 학원 용어 (분기 1/2/3) 통합 + IPSF 5트랙 채점 v1 (a)+(c)+Page 9 박제.

**Scope** (3 plan 후보):
- Plan 16-02: AKA 매핑 13개 → backend recognizer (`gemini_motion_classifier.py`) 가 사용자 입력 한국 학원 명칭 → IPSF Code 매핑 + Gemini prompt motion_query 반영. 분기 1 정합.
- Plan 16-03: 5트랙 채점 v1 (a)+(c)+Page 9 → `assemble.py` 가 4트랙 점수 별 출력 (현재 통합 overall 만 출력) + `result.tsx` UI 4트랙 카드. 메모리 [[ipsf-5-track-scoring]] 정합.
- Plan 16-04: 분기 3 자동 수집 = `pending_terms` Firestore 컬렉션 (사용자 입력 미등재 키워드) + UX 카피 노출.

**의존성**: Phase 5 (Gemini 인식기) 완료 정합. Phase 14 (정은지 reference) 정합 — 분기 2 (정은지 reference 비등재 폭스탑) 진행 가능.

**위험**: 분기 3 자동 수집 = 사용자 익명 ID. 메모리 [[runpod-gpu-env.md]] 함정 32 = "Firebase 익명 uid IPA 빌드별 다름" — 자동 수집 데이터 정합 영향 검토 필요.

---

## 4. 외부 AI (Codex / gpt-5.5) 검토 질문

메모리 [[cross-ai-plan-review-good]] = "Codex/gpt-5.5 plan-review-convergence 가 narrow gate 잡아냄". 검토 질문:

### 4-1. 시퀀싱 정합성

1. **Q1**: belle 의 시퀀싱 (A+B+C 우선, Phase 2~11 보류) 이 파일럿 목표 (정은지 시연 + 학원 실증) 에 정합하나? 보류된 Phase 들 (특히 Phase 11 CoachCommentHook = "AI 가 강사 보조 도구" 카피) 이 실증 단계 실패 1순위 후보 (강사/운영자 도입 거부) 인 점 정합?
2. **Q2**: A (Phase 12) 의 큰 scope (5 plan, 2주~) 가 파일럿 시연 직전 시간 정합? **B (UI transparency, 작은 scope) 먼저** → 시연 후 A 박제 가치 더 큰가?
3. **Q3**: C (Phase 16 코드 통합) 의 분기 3 자동 수집이 파일럿 단계에서 수집할 데이터 양 정합? "MVP 단순" 정신 → 분기 3 = 데이터 스키마만 + UX 노출 X (v2) ?

### 4-2. 코드 상태 정합

4. **Q4**: ROADMAP.md 갱신 누락 (Phase 1/5/16 사실상 완료, ROADMAP 표기 outdated) — 외부 검토 진행 전 ROADMAP 정합 우선? 또는 본 문서 가 ROADMAP supersede ?
5. **Q5**: Phase 1 Plan 01-24 (NLF/MediaPipe R&D 격리) = .samignore 명시 + import 차단 단위 테스트 미완. belle 입장에서 NLF 사용 안 함, 그러나 R&D 격리 명시는 라이선스 게이트 정합 ([[license-blocklist-pose.md]]). A+B+C 진입 전 Plan 01-24 우선?

### 4-3. 위험 검증

6. **Q6**: A 의 backend payload (playbackKeypoints frame-by-frame) Firestore 1MB 제한 — 5초/30초 영상은 무난, 60s+ 영상 별도 검증 필요.
7. **Q7**: B (UI transparency) 카피 — "왜 이 점수인지" deficit 표시. 현재 코드 path (`assemble.py` line_score / stability_score) 가 차원별 deficit 미완 (관절별 deficit 만). B scope = backend 차원별 deficit 추가 필요?
8. **Q8**: C 의 5트랙 채점 v1 — 현재 `assemble.py` 가 통합 overall, 4트랙 별 미완. 메모리 [[ipsf-5-track-scoring]] 정합, 그러나 mode3 second+ overall 산식 (각도+안정성 평균) 과의 정합 검증 필요.

### 4-4. 박제 정신 검증

9. **Q9**: 메모리 [[feedback-analysis-first]] "분석이 최우선" 정합 — A+B+C 모두 "분석 정확도" 가시화/통합 layer. 보류 Phase 2~11 (체형 정규화 + 두 엔진 본체) 은 "분석 정확도" 차세대 진화. 시퀀싱 정합?
10. **Q10**: 메모리 [[mode3-progress-not-similarity]] = "mode3 = 발전 not 일치". B (UI transparency) 박제 시 mode3 분기 카피 ("지난 분석보다 무릎 신전 8° 개선") 정합 검증.

---

## 5. 진입 결정 후보 (A+B+C 시퀀싱)

| 시퀀싱 | 정신 | 위험 |
|---|---|---|
| **B → C → A** | 작은 scope 먼저 (1~3일), C 학원 통합, A 큰 scope 마지막 | B 후 사용자 신뢰 검증, A 시연 직전 |
| **B → A → C** | 작은 scope 먼저, A 후 시연, C 후속 | C 학원 통합 미완 시 파일럿 실증 부족 |
| **A → B → C** | 큰 scope 먼저, B/C 정합 | A 박제 시간 (2주~) 시연 직전 위험 |
| **C → B → A** | C 학원 용어 먼저 — 학원 사용자 정합 | C+A 합쳐 3주~ 부담 |

**Claude 추천 = B → A → C**:
- B 작은 scope (1~3일) = 가장 빠른 사용자 신뢰 박제
- A 큰 scope (2주~) = 시연 임팩트 (실측 시각화)
- C 중간 scope (1주~) = 학원 실증 (학원 용어 통합)

메모리 [[mvp-simple-pilot-quality.md]] 정합 — 빠른 박제 + 시연 + 실증 순.

belle 최종 결정 = 외부 AI 검토 후.

---

## 6. 후속 작업

1. 외부 AI (Codex / gpt-5.5) 검토 (`gsd:review` 또는 `gsd:plan-review-convergence`)
2. 검토 결과 반영 (HIGH concern 박제)
3. ROADMAP.md 갱신 (Phase 1/5 close-out 마킹, Phase 12.5 신설 (B), Phase 16 코드 통합 Plan 16-02~04 박제)
4. STATE.md 갱신 (Current Position = Phase 12.5 또는 A/B/C 시퀀스)
5. `gsd:plan-phase` 진입 (시퀀스 첫 항목)

---

*작성: 2026-06-07 (Claude Code, belle 명시 지시 — 외부 AI 검토용 단일 문서)*
*검증: belle 의 다음 세션 (Codex 검토 후)*
