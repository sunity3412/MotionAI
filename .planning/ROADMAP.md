# Roadmap: Sunity AI Coach

## Overview

이 로드맵은 그린필드가 아니다. 앱은 2026-05-29에 이미 end-to-end로 동작한다 (RN 앱 → S3 presigned 업로드 → Lambda/SQS 파이프라인 → RunPod NLF 3D 분석 → IPSF 채점 → Firestore → 결과 화면). 인프라 골격(walking skeleton)은 완성되어 있다. 남은 일은 **이 파이프라인을 두 엔진(체형 보정 + 힘 방향 패턴) 아키텍처로 진화시켜 파일럿 MVP를 완성하는 것**이다.

핵심 가치는 분석 정확도다. 점수가 믿을 만하고 첫 분석이 "전문가 수준으로 구체적"이어야 한다. 2026-05-31 belle 결정으로 시스템 아키텍처가 갱신됨 (`docs/research/00_시스템_아키텍처_FINAL.md`, `01_체형차이_보정엔진_FINAL.md`, `02_힘방향_힘조절_엔진_FINAL.md`):

- **포즈 엔진 (상용/베타 제품 코드)** = **MediaPipe + Gemini**. NLF/SMPL-X는 **라이선스 확인 전까지 실제 제품 코드에 넣지 않고, 내부 비상업 R&D 비교군으로만 사용**. 현재 코드는 NLF 기반이므로 Phase 1에서 MediaPipe로 마이그레이션 + NLF/SMPL-X R&D 격리.
- **PoseEngine 추상화**: 모든 다운스트림(폴축·구간·체형·힘·채점·리포트)은 `PoseEngine` 인터페이스 + 공통 계약(`PoseFrame` / `BodyNormalizationProfile`)에만 의존. 어댑터 두 개 — ① `MediaPipePoseEngine` (제품 코드), ② `NlfPoseEngine` (R&D 비교군, 비공개 평가만). 엔진 교체 = 구현체 1개 + config 플래그.
- **NLF/SMPL-X R&D 사용 규칙** (입수처: https://is.mpg.de/ps/code, https://smpl-x.is.tue.mpg.de):
  - 사용 목적 = MediaPipe 결과 검증·정확도 갭 측정·향후 마이그레이션 ROI 판단.
  - 사용 환경 = 사내 R&D 노트북/RunPod, **공개 베타·유료 파일럿·고객 영상 처리에 사용 금지**.
  - 라이선스 = PS:License 1.0 (비상업). 출시 전 사용 시 상업 라이선스(`info@max-planck-innovation.de`) 클리어 필수.
- **데이터셋 (R&D 평가 벤치마크)** = AMASS/BEDLAM2.0/AGORA — 비상업, 파이프라인 테스트·정확도 평가에만.
- **두 엔진 공유 레이어**: 폴 축 정렬, 동작 구간 분할, BodyNormalizationProfile.
- **엔진 A (체형 보정)**: coaching 모드 정규화 비교 + 차이 분류.
- **엔진 B (힘 패턴)**: 중심축/접촉점/jerk → ForceDirectionPattern + 실패 원인 후보 3개. 근육 힘 방향 단정 금지 — **패턴 추론만, 측정 X**.
- **Gemini**: 자연어 번역 전용 (좌표·판단 출력 금지).
- **CoachCommentHook**: 모든 리포트에 부착, AI+코치 비즈니스 모델 기반. **confidence 항상 출력**.
- **모드**: coaching 모드 기본. judging 모드(IPSF Code of Points 기하 점검)는 옵션 — v1.5 분리, 데이터 수집은 v1 동시 평행 진행.
- **다중 시점 촬영**: occlusion 완화 위해 v1 포함. 큐레이션 대상 = 똑바로 선·가림 적은 3~5개 동작.

여정은 **공통 레이어 먼저 → 엔진 A·B → 리포트·코칭 → 전달** 순으로 흐른다. 공통 레이어가 두 엔진의 입력을 만들고, 엔진 출력이 리포트에 묶이고, 리포트가 두 모드(Mode 1·Mode 3)에서 실영상으로 검증된 뒤 TestFlight로 전달된다.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: PoseEngine 추상화 + RTMW 어댑터 + 폴 축 정렬 + NLF R&D 격리** - 상용 제품 코드를 RTMW 133 wholebody (Apache-2.0) 로 마이그레이션 완료 (commit 2a8aa72 atomic swap), NLF/SMPL-X 는 R&D 비교군으로 격리, 폴 축 좌표계 산출. **2026-06-07 close-out 사실상 완료** — Plan 01-25 swap 완료, Plan 01-23 sweep 은 Phase 5 12차 sweep 으로 대체. 미완 = Plan 01-24 (.samignore + import 차단 단위 테스트) — 후속 별도 plan.
- [x] **Phase 2: BodyNormalizationProfile 자동 측정 (RTMW segment 기반)** - 키·팔/다리/몸통 비율·좌우 비대칭 자동 추출. SMPL-X β는 R&D 비교군에서만 (제품 코드 사용 금지). **2026-06-07 belle pivot 정합**: Phase 1 RTMW 백본 swap 완료 (commit 2a8aa72) 후 Phase 2 도 MediaPipe → RTMW segment 산출로 갱신. (completed 2026-06-07)
- [ ] **Phase 3: 자가입력 BodyProfileInput** - 키·몸무게·경력·통증부위 1회 입력 UX
- [ ] **Phase 4: 다중 시점 촬영 UX + occlusion confidence 게이트** - 가림 완화 + 저신뢰 프레임 "추정" 표기
- [x] **Phase 5: Gemini 기술 인식기 (분류 한정)** - 동작 분류만, 좌표·판단 출력 금지. **2026-06-05 12차 sweep D-01 PASS** (phase1_ready_to_swap=True, phase5_ready_to_release_d16_block=True). 빌드 11 실분석 mode1 94 + mode3 100 PASS.
- [ ] **Phase 6: 체형 정규화 비교 엔진 (coaching 모드)** - 프로 패턴을 수강생 체형 비율로 재계산
- [ ] **Phase 7: 차이 분류** - 체형 허용 차이 / 개선 필요 차이 / 감점 분리
- [ ] **Phase 8: 중심축 이탈 + 접촉점 안정성 + jerk/jitter** - 힘 패턴 추론을 위한 기초 신호
- [ ] **Phase 9: ForceDirectionPattern + 실패 원인 후보 3개** - pull/push/brace/rotate/release + 실패 후보 3카드
- [ ] **Phase 10: 부상 위험 신호 플래그** - 좌우 비대칭·요추 과신전·무리 동작 신호 (SAFE-01 v1)
- [ ] **Phase 11: CoachCommentHook 데이터 구조 + Gemini 자연어 번역만** - AI+코치 비즈니스 모델 + 설명 엔진 한정
- [ ] **Phase 12: 실측 각도 표시 + 키포인트 오버레이** - "현재 87° → 기준 110°" + 어깨/골반/무릎/손/중심축. **2026-06-07 belle 결정: A 항목, B → C → A 시퀀싱의 마지막. feature flag + git branch 박제로 빌드 11 stable 유지하며 진행.**
- [x] **Phase 12.5: UI Transparency — 차원별 카피 + 자세히 모달 + LLM-ready coaching** - `result.tsx` 차원별 카드 (각도 정확도 / 팔다리 펴기 / 동작 안정성) + 자세히 모달 (점수 산출 설명, 동작·사용자 동적 카피, "심사평" 자연어) + 코칭 팁 자세히 모달 (LLM 동적 다중 원인 + 부상 경고 + coachNote). backend `assemble.build_dimension_explanation` + `coach_writer` JSON 출력 + Cerebras 시스템 프롬프트 갱신. **2026-06-07 close-out** (commits 1c0d20a T1+T2 / 62fdeed T9 backend / e968074 T8+T9 frontend). belle UX 검증 PASS — 모달 스크롤 정상 동작 + 심사평 톤 (평가+이유+결정 3박자) 적용.
- [ ] **Phase 13: 보완 운동 추천 + LLM 분기 카피 + coaching detail 완성** - (a) 분석 결과의 실패 원인 후보·체형 정규화 finding 에 맞는 보완 운동·스트레칭 자동 매핑 (분석 → 행동 → 재구매, PERS-03), (b) 실 LLM 활성화 — Pod 갱신 + Cerebras `tip.detail2` 실 영상 검증, (c) `assemble.build_dimension_explanation` 에 `ipsfCode` 분기로 분기 1 (IPSF 등재 = "세계 심사 기준 + 180°") vs 분기 2 (학원 통용 = "정은지 선수 기준") 카피 분리, (d) `coach_writer` 시스템 프롬프트에 동작 분기 + IPSF 정의 각도 fixture 주입. 메모리 [`studio-term-3branch-system`] 정합. **belle 2026-06-07 결정: Phase 12.5 시뮬 한계 (폭스탑 학원 용어 어색 + angle 차원 180° 명시 X) 의 실 LLM 해결을 보완 운동 추천과 같은 phase 로 통합 — backend coach_writer 단일 phase 작업.**
- [ ] **Phase 14: 정은지 기준 모션 등록 (다각도 캡처 가이드)** - 비교 정확도 최대화 + 다각도 캡처 프로토콜
- [ ] **Phase 15: Mode 1·Mode 3 실영상 + 신뢰도 게이트 + TestFlight** - 두 모드 end-to-end + 고수 위양성 없음 + 실기기 게스트 완주
- [x] **Phase 16: Studio Terminology Foundation (3-branch + 5-Track v1 평행)** - 학원 용어 3분기 시스템 + IPSF 5트랙 채점 v1 scope 데이터/스펙/카피 박제. v1 평행 진행 (Phase 1~15 의존성 없음). MVP 가볍게 + 실증 단계 검증 후 확장 path. (completed 2026-06-02)

## Phase Details

### Phase 1: PoseEngine 추상화 + ~~MediaPipe~~ RTMW 어댑터 + 폴 축 정렬 + NLF R&D 격리

> **2026-06-02 belle pivot — RTMW 무료 스택:** 운영 백본을 **MediaPipe + MotionBERT → RTMW 133 wholebody (Apache-2.0) 단일 백본** 으로 전환. 3D 는 RTMW3D / monocular 리프팅 (단일 카메라) + Pose2Sim (멀티 카메라). 체형 정규화는 SMPL-X 없이 세그먼트 길이 비율. NLF/SMPL-X 의존 영구 제거 (매출 검증 후 옵션 업그레이드). **PoseEngine 인터페이스 추상화 필수** — 다운스트림 분석 레이어 무수정. 자세 사항: `01-CONTEXT.md` D-17~D-25, `/Users/kimtaesung/Downloads/Sunity_v1_개발지시_RTMW무료스택.md`. Plan 02·03 MediaPipe 코드 결과물 → R&D 격리 또는 폐기 (플래너 판단).

**Goal**: 상용 제품 코드를 **NLF → RTMW 133 wholebody (Apache-2.0)** 로 마이그레이션하고, `PoseEngine` 인터페이스 + 공통 계약(`PoseFrame` / `BodyNormalizationProfile`)을 도입한다. NLF/SMPL-X 는 R&D 비교군 어댑터로 격리(제품 호출 경로에서 제거). 동시에 폴 축 자동 검출 + 기준 좌표계 정렬을 RTMW 위에서 산출한다 — 모든 다운스트림의 기반.
**Mode:** mvp
**Depends on**: Nothing (공통 레이어 첫 단계 — 현 NLF 코드 마이그레이션 포함)
**Requirements**: POSE-01, POSE-02
**Scope 제약**: 초기 3~5개 동작군 범위(똑바로 선·가림 적은). 스피닝 폴은 v1.5. NLF/SMPL-X는 R&D 비교군 비공개 평가에만 사용 — 공개 베타·유료 파일럿·고객 영상 처리 금지. **MediaPipe 운영 백본 도입 안 함** (Plan 02·03 결과물은 R&D 격리 또는 폐기).
**External dependency**: **rtmlib RTMW (Apache-2.0)** 운영 백본 — 모델 가중치별 학습 데이터 상업 사용 가능 여부 확인 필수 (D-25). NLF/SMPL-X R&D 비교군은 PS:License 1.0 (비상업) 사내 평가만.
**Success Criteria** (what must be TRUE):

  1. `PoseEngine` 인터페이스가 정의되고 `MediaPipePoseEngine` 어댑터가 제품 코드 경로(Lambda/RunPod 파이프라인)에서 동작한다
  2. `NlfPoseEngine` 어댑터는 별도 모듈로 격리되어 R&D 평가 스크립트에서만 호출 가능 (제품 파이프라인 import 경로에서 제거)
  3. 영상에서 폴 축이 자동 검출되고 video-level **PoleAxis가 1개 산출되어 모든 frame의 PoseFrame.pole_axis에 적용되고**, 모든 키포인트 좌표가 폴 기준 좌표계로 변환된 결과를 반환한다 (D-10 — 일반 폴 가정, 스피닝 폴은 v1.5)
  4. 키포인트 confidence가 임계값 미만인 프레임은 "추정"으로 표기되고 후속 분석이 단정하지 않는다
  5. R&D 평가 스크립트가 MediaPipe vs NLF 정확도 갭을 동일 영상 세트에서 측정해 보고서로 출력한다 (마이그레이션 ROI 판단 근거)
  6. 데이터 계약(`analysis.ts` ↔ `models.py`)에 `PoseFrame` 타입이 lockstep으로 추가된다
  7. **5영상 sweep 재실행 시 (a) IPSF GeometricCriterion 갭 ≤ tolerance + (b) line/angle 5/5 PASS** — 두 게이트 모두 통과해야 Wave 3 (Plan 04/05) 진입 가능. baseline 은 NLF 갭이 아닌 **IPSF Code of Points 객관 임계값** (Plan 12 (c) strong / belle 결정 2026-06-01). 강등/우회/known limitation 수용 금지. 사람 점수 라벨링 (belle/강사/심사자) 영구 금지.

**Plans**: 22 plans total — 17 existing (Wave 0~2) + 7 new RTMW pivot plans (Wave 1~6). 2026-06-02 RTMW pivot supersedes 01-04/01-05/01-14.

  - [x] 01-01-PLAN.md — PoseFrame + PoleAxis 데이터 계약 3-way lockstep + reliability 게이트 stub + Wave 0 테스트 픽스처 (Wave 0)
  - [x] 01-02-PLAN.md — PoseEngine Protocol + MediaPipePoseEngine 어댑터 + 33→COCO-17 + grip 확장 매핑 (Wave 1) — MediaPipe 산출물 plan 24 에서 R&D 격리 예정
  - [x] 01-03-PLAN.md — HoughPoleDetector + PoleAxisAligner — lazy cv2/scipy import (D-09/D-10/D-11/D-12) (Wave 1)
  - [x] 01-06-PLAN.md — compare_engines.py 회귀 검증 + belle 검토 checkpoint (D-13~D-16) — **Wave 3 gate (구)** (Wave 2)
  - [x] 01-07-PLAN.md — MotionBERT-lite lifter spike (2D→3D pose lift) — MIT 라이선스 박제 (Wave 2) — plan 22 옵션 A 선택 시 R&D 격리 대상
  - [x] 01-08-PLAN.md — MediaPipe + MotionBERT 운영 통합 + 5영상 회귀 — 4/5 PASS, ref-sideway-spin 64 FAIL (Wave 2)
  - [closed] 01-09-PLAN.md — AlphaPose 측면 보강 spike — license_blocked (Noncommercial, 영구 후보 제외) (Wave 2)
  - [x] 01-10-PLAN.md — RTMPose-l (MMPose Apache 2.0) 단일 영상 spike — STRONG_PASS (ref-sideway-spin 72) (Wave 2)
  - [x] 01-11-PLAN.md — RTMPose 5영상 sweep + line/angle root cause + 게이트 룰 검토 — **verdict gap_too_wide_blocked** (D-15① 5/5 PASS / D-14 4/5 FAIL / line·angle 5/5 N/A) (Wave 2)
  - [~] 01-12-PLAN.md — 갭 root cause 디버그 spike — T-1~T-4 완료, T-5 belle Pod live 대기. report-only verdict (c)/(d) strong → NLF baseline 부적합 박제 → Plan 15 신설 (Wave 2, NEW 2026-06-01)
  - [~] 01-13-PLAN.md — Gemini key moment timestamp + criteria extractor (multimodal 2.5 Pro). verdict `measurement_unreliable_blocked` (Wave 2, NEW 2026-06-01)
  - [x] 01-15-PLAN.md — **JUDGE-DATA-01 IPSF GeometricCriterion 데이터 수집** — plan 23 의 baseline (Wave 2, NEW 2026-06-01)
  - [x] 01-16-PLAN.md — **측정 신뢰도 trace spike** (Wave 2, COMPLETE 2026-06-01)
  - [x] 01-17-PLAN.md — **keypoint mapping audit + swap fix** (Codex Cycle 3 PASS) (Wave 2, COMPLETE 2026-06-01)
  - [on hold] 01-18-PLAN.md — **multi-engine averaging spike** — **2026-06-02 RTMW pivot 으로 보류** (abandoned 아님)
  - [SUPERSEDED] 01-14-PLAN.md — 5영상 재검증 sweep (RTMPose+MB+lifter baseline) — **plan 23 가 SUPERSEDE** (RTMW + IPSF baseline). 미실행 상태로 SUPERSEDED 마킹.
  - [SUPERSEDED] 01-04-PLAN.md — NLF R&D 격리 (NLF 만) — **plan 24 가 SUPERSEDE + 확장** (NLF + MediaPipe + 비선택 3D path). 미실행 상태로 SUPERSEDED 마킹.
  - [SUPERSEDED] 01-05-PLAN.md — pipeline/app.py atomic swap (NLF→MediaPipe) — **plan 25 가 SUPERSEDE** (NLF→RTMW). 미실행 상태로 SUPERSEDED 마킹.
  - [x] 01-19-PLAN.md — **NEW (RTMW pivot)** PoseEngine 인터페이스 보강 + BodyNormalizationProfile (D-19 SMPL-X 없이 segment 비율) + PoseFrame.bodyShape nullable (D-21) + TS/Python/contract.md 3-way lockstep + ADR-0001 박제 (Wave 1, gap_closure 2026-06-02)
  - [x] 01-20-PLAN.md — **NEW (RTMW pivot)** rtmlib RTMW 가중치 라이선스 audit (D-25) + weights_manifest.json + belle 검토 checkpoint (Wave 1, gap_closure 2026-06-02) — **완료 (2026-06-02)**: belle 승급, Production=`rtmw-x-384x288` (commercial_ok, validation-pilot scope), Fallback=`rtmw-l-384x288`. 출시 전 clean weight 교체 hard gate (별도 plan 작성·시작 belle 지시).
  - [x] 01-21-PLAN.md — **NEW (RTMW pivot)** rtmlib RTMW 133 wholebody 통합 + RTMW133ToCOCO17Adapter + POSE_ENGINE config (D-17/D-20/D-21/D-22/D-24/D-25) (Wave 2, gap_closure 2026-06-02)
  - [x] 01-22-PLAN.md — **NEW (RTMW pivot)** 단일 카메라 3D path 결정 — 옵션 A (RTMW3D 직접) vs 옵션 B (RTMW + MotionBERT lifter) — belle checkpoint (D-18) (Wave 3, gap_closure 2026-06-02)
  - [ ] 01-23-PLAN.md — **NEW (RTMW pivot)** RTMW vs IPSF GeometricCriterion 5영상 회귀 검증 sweep — Wave 5 진입 게이트 (IPSF tolerance + line/angle 5/5 PASS) — plan 14 supersede (Wave 4, gap_closure 2026-06-02)
  - [ ] 01-24-PLAN.md — **NEW (RTMW pivot)** NLF + MediaPipe + 비선택 3D path R&D 격리 (D-23) + .samignore + import 차단 단위 테스트 — plan 04 supersede + 확장 (Wave 5, gap_closure 2026-06-02)
  - [ ] 01-25-PLAN.md — **NEW (RTMW pivot)** pipeline/app.py + RunPod atomic swap NLF→RTMW (D-08/D-21/D-23/D-24) + belle Pod end-to-end 검증 — plan 05 supersede (Wave 6, gap_closure 2026-06-02)

### Phase 2: BodyNormalizationProfile 자동 측정 (RTMW segment 기반)

> **2026-06-07 RTMW pivot 정합**: Phase 1 백본 swap 후 (NLF → RTMW 133 wholebody Apache-2.0, commit 2a8aa72), Phase 2 segment 산출도 **RTMW 키포인트** 기반으로 갱신. MediaPipe 는 운영 백본에서 폐기. NLF/SMPL-X 는 R&D 비교군으로만.

**Goal**: RTMW 키포인트로부터 신체 segment 길이(상완·전완·대퇴·하퇴·몸통, 어깨/골반 폭) 및 비율을 산출해 `BodyNormalizationProfile`(estimatedHeightScale, armScale, legScale, torsoScale, shoulderHipRatio, confidence, warnings)을 자동 출력한다 — 두 엔진의 공유 입력. SMPL-X β는 R&D 비교군에서만 정확도 평가용으로 사용.
**Mode:** mvp
**Depends on**: Phase 1 (MediaPipe + 폴 축 정렬된 키포인트 위에 segment 측정)
**Requirements**: BODY-01
**Success Criteria** (what must be TRUE):

  1. RTMW 키포인트에서 segment 길이가 시간 평균으로 안정적으로 추출된다 (jitter 스무딩) — v1 acceptance: synthetic + RTMW adapter-path validation; real RTMW network output coverage 는 v1.5 sweep 실행 (belle Pod 5영상 keypoint dump 산출) 으로 deferred (MEDIUM-2 v4 박제)
  2. **Phase 2 v1 closure**: 측정기 함수 `measure_body_profile` + helper `_angles_and_body_profile_from_video` 가 박제되고 단위 테스트가 `BodyNormalizationProfile` 7필드 산출을 검증한다. `_process` / Firestore 통합은 Phase 6 plan 책임 — **Phase 6 closure**: production analysis document (Firestore AnalysisDoc) 가 `bodyNormalizationProfile` 을 포함한다 (Phase 6 plan 이 본 phase 의 helper 호출 site 박제) (MEDIUM-1 v5 박제)
  3. 낮은 confidence(가림·저화질) 시 단정하지 않고 warnings 배열에 사유가 표기된다
  4. RTMW `measure_body_profile` 산출이 §1 v1.5 sweep run 에서 5영상 실 산출로 검증된다 (RTMW-native validation, SMPL-X 비교 폐기 — 2026-06-02 RTMW pivot 정합, 2026-06-08 belle 스코프 정정: SMPL-X 는 paid commercial license 로 R&D 에서도 last-resort 만; β-only pure-math 변환은 fake 이므로 폐기, joints rendering 도 별도 weights 필수라 운영 path 무관). §4 closure 는 §1 v1.5 단일 게이트로 단일화.
  5. 데이터 계약(`analysis.ts` ↔ `models.py`)에 `BodyNormalizationProfile` 타입이 lockstep으로 추가된다

**Plans**: 1 plan
Plans:

- [x] 02-01-PLAN.md — RTMW segment 측정기 + 5종 warnings + R&D 격리 + 3-way lockstep 갱신 (Wave 1, BODY-01)

### Phase 3: 자가입력 BodyProfileInput

**Goal**: 사용자가 키·몸무게·경력·통증부위·우세손을 앱에서 1회 입력하고, 분석에 BodyProfile이 함께 전달된다 (영상으로 단정 불가한 항목 보조)
**Mode:** mvp
**Depends on**: Phase 2 (BodyNormalizationProfile과 결합되는 보조 입력)
**Requirements**: BODY-02
**Scope 제약**: 유연성·근력 자가입력은 받지 않음(부정확). 키·몸무게·경력·통증부위만.
**Success Criteria** (what must be TRUE):

  1. 마이페이지 또는 첫 분석 직전 BodyProfileInput 화면에서 키·몸무게·경력·통증부위·우세손을 입력할 수 있다
  2. 입력값이 Firestore에 저장되고 분석 요청 시 백엔드로 전달된다
  3. weightKg는 보조 정보로만 사용되고 분석 단정 근거로 쓰이지 않는다 (코드 주석 + 사용처 제한)
  4. 미입력 사용자도 분석이 graceful하게 진행된다 (BodyNormalizationProfile만으로)

**Plans**: TBD
**UI hint**: yes

### Phase 4: 다중 시점 촬영 UX + occlusion confidence 게이트

**Goal**: 사용자가 다중 시점(정면+측면 등)으로 영상을 업로드할 수 있고, 가림 프레임은 confidence 게이트로 단정하지 않는다
**Mode:** mvp
**Depends on**: Phase 1, Phase 2 (폴 축·체형 피팅 위에 confidence 적용)
**Requirements**: POSE-03
**Scope 제약**: 정면+측면 2시점 우선. 사선/뒤 시점은 v2.
**Success Criteria** (what must be TRUE):

  1. 업로드 화면에서 단일/다중 영상 선택 가이드(촬영 각도 설명)가 표시된다
  2. 다중 영상 업로드 시 동일 analysisId 아래 시점별로 저장되고 백엔드가 시점 매핑된다
  3. 키포인트 confidence가 임계값 미만인 프레임은 "추정" 표기 + 후속 단정 게이트
  4. occlusion 경고가 결과 화면에 표시되고 (예: "이 구간은 가림으로 추정") 사용자가 인지할 수 있다

**Plans**: TBD
**UI hint**: yes

### Phase 5: Gemini 기술 인식기 (분류 한정)

**Goal**: 영상에서 기술명을 분류한다 (예: 인버트·후굴·기본 포징). 좌표·판단·점수 출력은 금지 — 자연어 번역만이 Gemini 역할
**Mode:** mvp
**Depends on**: Phase 1 (폴 축 정렬 위에서 인식)
**Requirements**: SCORE-01
**Scope 제약**: 인식 범위 3~5개 동작군(후굴·인버트·기본 포징). 범위 밖은 "미지원" 처리.
**External dependency**: belle의 Gemini API 키(Google AI Studio) → Parameter Store / RunPod env. 키 미확보 시 Phase 5 블로킹.
**Success Criteria** (what must be TRUE):

  1. 영상에서 동작 분류 결과가 반환되고 관절별 EXTEND/BENT 프로파일이 산출된다
  2. Gemini 호출 실패 시 `FallbackRecognizer`로 graceful degrade하고 분석이 크래시하지 않는다
  3. Gemini 응답에 좌표·판단 출력 요청이 없다 (프롬프트 설계로 강제)
  4. 인식 범위 밖 동작은 명시적으로 "미지원"으로 처리된다

**Plans**: 6 plans total — Wave 0 yaml source 정정 (선행 필수) + Wave 1~4 Gemini wiring + belle Pod sweep checkpoint. NotebookLM IPSF lookup 2026-06-04 결과 박제 (yaml hold_moment IPSF source 박제 X → 정은지 reference 측정값 분기 2 path 정정).

  - [x] 05-00-PLAN.md — yaml source 정은지 reference 측정값 정정 (Plan 5-00 선행 필수, D-17/D-18 박제) + belle 승인 checkpoint (Wave 0)
  - [x] 05-01-PLAN.md — GeminiTechniqueRecognizer 어댑터 신설 + 3-case fallback + motion_name 정규화 spike + response_schema 작동 spike (Wave 1)
  - [x] 05-02-PLAN.md — TechniqueCache 영상 hash 캡싱 + firestore_admin helper 3종 (D-14 박제) (Wave 1)
  - [ ] 05-03-PLAN.md — pipeline _RECOGNIZER lazy swap + env switch + _process recognize(angles, frames) wiring (Wave 2)
  - [ ] 05-04-PLAN.md — Pod requirements/setup.sh + server.py _warmup fail-loud (D-13/D-15, Common Pitfall 4) (Wave 3)
  - [ ] 05-05-PLAN.md — sweep --recognizer gemini flag + belle Pod sweep checkpoint (Phase 5 게이트 = 정은지 reference 기준 5/5 PASS) (Wave 4)

### Phase 6: 체형 정규화 비교 엔진 (coaching 모드)

**Goal**: 프로의 동작 성공 원리를 수강생의 신체 비율에 맞게 재계산해 비교한다 (`normalizeStudentPoseToProReference` 알고리즘) — 체형 차이로 인한 위양성 감점 제거
**Mode:** mvp
**Depends on**: Phase 2 (BodyNormalizationProfile), Phase 5 (기술 인식 결과)
**Requirements**: PERS-01
**Success Criteria** (what must be TRUE):

  1. 프로/수강생 BodyNormalizationProfile 차이로 scale 프로파일이 산출되고 세그먼트별 상대 좌표가 재계산된다
  2. 단순 확대/축소가 아닌 세그먼트별 정규화 (`normalizeByBodySegments`)가 구현된다
  3. 동일 동작에서 체형이 다른 두 사용자가 각자 체형 비율 기준의 점수를 받는다 (절대 각도 차이만으로 감점 X)
  4. coaching 모드 출력에 `bodyNormalizationConfidence`가 항상 포함된다

**Plans**: 3 plans (Plan 06-01 = algorithm + contract lockstep, Plan 06-02 = pipeline wiring + Firestore + smoke, Plan 06-03 = 정은지 reference 백필) — 2026-06-08 revision (W4 박제 박제 9 task 박제 5 + 4 split)

Plans:
**Wave 1**

- [ ] 06-01-PLAN.md — body_normalizer.py (Kinematic Tree Reprojection + IPSF deficit + confidence) + ScaleProfile/BodyComparisonReport (3 ComparisonType + usedReferenceFallback boolean) + 3-way contract lockstep (TS + Python + docs/contract.md §8) + 5 fixture + 4 algorithm test 파일 + drift lockstep test (Wave 1, PERS-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 06-02-PLAN.md — pipeline _process wiring (`_angles_profile_and_frames_from_video` sibling helper for pose_frames + `_match_reference_by_name` Gemini fallback via profile.name) + firestore_admin.complete_analysis 확장 + `_validate_flat_dict_no_nested_array` validator (list[str] + list[dict-scalar] 허용) + `list_reference_motions_by_name` helper + frontend userAnalyses.normalize defensive validation + SAM build smoke + 4 integration test 파일 (Wave 2, PERS-01)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 06-03-PLAN.md — firestore_admin.update_reference_body_profile helper + extract_reference_body_profiles.py (Pod GPU 직접 실행, `-m` invocation 박제 X) + seed-reference-body-profile.mjs (Firebase Admin SDK ADC) + 실행 checkpoint (Wave 3, PERS-01)

### Phase 7: 차이 분류

**Goal**: 정규화 비교 결과를 "체형 허용 차이 / 개선 필요 차이 / uncertain"으로 자동 분류하고 각 항목에 bodyTypeInterpretation·recommendation을 부착한다
**Mode:** mvp
**Depends on**: Phase 6
**Requirements**: PERS-01
**Success Criteria** (what must be TRUE):

  1. `BodyComparisonFinding[]`이 phase별·category별로 산출된다 (`body_type_allowed` / `needs_adjustment` / `uncertain`)
  2. `doNotOverCorrect`와 `recommendedFocus` 배열이 출력에 포함된다
  3. category 분류가 BodyNormalizationProfile confidence를 반영해 낮으면 `uncertain`으로 처리된다
  4. 결과 화면 카피가 "프로보다 못합니다" 같은 표현 없이 보정 중심으로 작성된다

**Plans**: TBD

### Phase 8: 중심축 이탈 + 접촉점 안정성 + jerk/jitter

**Goal**: 힘 방향 패턴 추론에 필요한 기초 신호(중심축 이탈, 접촉점 안정성, 흔들림, jerk)를 phase별로 산출한다 — 가림 스무딩 필수
**Mode:** mvp
**Depends on**: Phase 1, Phase 4 (폴 축 정렬 + confidence 게이트 위에 측정)
**Requirements**: FORCE-01
**Success Criteria** (what must be TRUE):

  1. `AxisDeviationMetric`(골반/흉곽 폴축 거리, 어깨/골반 tilt, deviation 방향)이 phase별로 산출된다
  2. `StabilityMetric`(jitterScore, jerkScore, holdStabilityScore, unstableBodyParts)이 phase별로 산출된다
  3. `ContactStabilityMetric`(접촉점별 estimatedStable, lostContactAtMs, confidence)이 phase별로 산출된다
  4. 모든 신호에 시간적 스무딩이 적용되고 가림 프레임은 confidence로 가중 처리된다

**Plans**: TBD

### Phase 9: ForceDirectionPattern + 실패 원인 후보 3개

**Goal**: 기초 신호를 종합해 `ForceDirectionPattern`(pull/push/brace/rotate/release)을 추론하고, 동작 실패 원인 후보 3개를 카드 형태로 제시한다 (단정 금지, 모든 항목 "가능성"으로 표기)
**Mode:** mvp
**Depends on**: Phase 8
**Requirements**: FORCE-01, FEED-02
**Success Criteria** (what must be TRUE):

  1. `inferForceDirectionPattern` 함수가 5개 카테고리 중 하나 이상을 phase별로 반환한다
  2. 실패 원인 후보가 정확히 상위 3개로 정렬되어 카드 형태 데이터로 출력된다 (KISMAM Top-3 진화)
  3. 모든 finding이 `confidence`와 `interpretation` 필드를 가지며 "단정"이 아닌 "가능성" 언어로 표현된다
  4. "근육 힘 방향" 단정 표현이 출력에 없다 (코드 + 프롬프트 가드)

**Plans**: TBD

### Phase 10: 부상 위험 신호 플래그

**Goal**: 좌우 비대칭·요추 과신전·레벨 대비 무리한 동작 신호를 위험도 스코어로 플래그하고 결과 화면에 경고로 표시한다
**Mode:** mvp
**Depends on**: Phase 8 (기초 신호)
**Requirements**: SAFE-01
**Scope 제약**: "부상 확정" 단정 금지. "위험 가능성"으로만 표기 + 전문가 확인 권유.
**Success Criteria** (what must be TRUE):

  1. 좌우 비대칭 임계값 초과 시 위험 신호 플래그가 출력에 추가된다
  2. 요추 과신전 패턴이 감지되면 "허리 부담 가능성" 경고가 표시된다
  3. 자가입력 `poleExperienceLevel`과 동작 난이도 매핑으로 "레벨 대비 무리" 경고가 동작한다
  4. 결과 화면에 부상 위험 경고가 시각적으로 구분되고 "전문가 확인 권유" 카피가 함께 표시된다

**Plans**: TBD
**UI hint**: yes

### Phase 11: CoachCommentHook 데이터 구조 + Gemini 자연어 번역만

**Goal**: 모든 리포트에 `CoachCommentHook`이 부착되고, Gemini는 구조화된 finding을 자연어로 번역만 한다 (판단·좌표 출력 금지). 결과 화면 카피가 AI를 "강사 보조 도구"로 포지셔닝한다
**Mode:** mvp
**Depends on**: Phase 7, Phase 9 (두 엔진 출력 위에 코칭·번역 레이어)
**Requirements**: COACH-01, FEED-02, FEED-03
**Success Criteria** (what must be TRUE):

  1. `CoachCommentHook`(autoFindingsSummary, openQuestionsForCoach, suggestedCues, coachComment?, reviewedBy) 타입이 데이터 계약 양쪽에 추가된다
  2. 모든 리포트(BodyComparisonReport, ForcePatternInference)에 coachCommentHook이 부착된다
  3. Gemini 프롬프트가 "자연어 번역만, 좌표·판단·점수 출력 금지"로 설계되고 검증된다
  4. 결과 화면 카피가 AI를 강사 보조 도구로 포지셔닝하고 기준 모션이 "하나의 참고일 뿐"으로 명시된다
  5. Cerebras 키 미설정 시에도 fallback 카피로 분석이 완료된다

**Plans**: TBD
**UI hint**: yes

### Phase 12: 실측 각도 표시 + 키포인트 오버레이

**Goal**: 결과 화면에 관절 각도가 "현재 87° → 기준 110°" 형태로 실데이터로 표시되고, 영상 위에 어깨·골반·무릎·손 키포인트와 중심축이 오버레이로 그려진다
**Mode:** mvp
**Depends on**: Phase 6, Phase 7 (정규화된 각도 위에 표시)
**Requirements**: FEED-01, VIS-01
**Success Criteria** (what must be TRUE):

  1. 결과 화면 angleGuide가 백엔드 실측 currentAngle을 표시한다 (fixture 아님)
  2. 각 관절이 "현재 N° → 기준 M°" 형태로 현재값과 기준값을 나란히 보여준다
  3. 데이터 계약(`analysis.ts` ↔ `models.py` ↔ `assemble.py`)이 lockstep으로 갱신된다
  4. 영상 프레임 위에 어깨·골반·무릎·손 키포인트와 중심축이 오버레이로 표시된다 (발끝 toe는 v2)

**Plans**: TBD
**UI hint**: yes

### Phase 12.5: UI Transparency — 차원별 카피 + 가중치 표시 + 강사 보조 카피

**Goal**: 사용자가 "아 이래서 이런 평가구나" 박제 — `result.tsx` 차원별 (`angle`/`line`/`stability`) 카드에 (a) "이게 무슨 기준 (IPSF 기준 + 정은지 측정값)" 한 줄 카피, (b) 가중치 표시 ("각도 40% + 라인 30% + 안정성 30%"), (c) "왜 이 점수인지" 차원별 deficit, (d) "AI = 강사 보조 도구" 헤더/footer 카피. backend `assemble.py` 가 `dimensionExplanation` 출력.
**Mode:** mvp
**Depends on**: Phase 1 (RTMW), Phase 5 (Gemini), Phase 16 (Studio Term v1) — 모두 close-out
**Requirements**: FEED-02 (피드백 명확성), COACH-01 (강사 보조 카피 부분)
**Scope 제약**: 작은 단위 — backend 약 50 line + frontend 약 30 line + contract 양쪽. mode1 / mode3 first / mode3 second+ 분기 카피 박제. 메모리 [[mode3-progress-not-similarity]] 정합 ("지난 분석보다 +5점" 박제, "%일치" 박제 X).
**Success Criteria** (what must be TRUE):

  1. `result.tsx` 차원별 카드에 "이게 무슨 기준" 한 줄 카피가 표시된다 (각도 = IPSF + 정은지 측정값, 라인 = 신전 완성도, 안정성 = inter-frame diff)
  2. 차원별 가중치 합 = 100% 표시 (현재 `assemble.py` 산식 정합)
  3. 차원별 deficit 카피 — worst 관절 1~2개 박제 ("오른쪽 어깨 22° 더 펴주세요 = -8점" 박제 박제)
  4. 헤더 "이 분석은 강사 수업을 대체하지 않아요" + footer "강사와 함께 보세요" 박제 (메모리 [[field-research-stakeholders]] H4 해소)
  5. backend `assemble.py:build_result` 가 `dimensionExplanation: { weight: float; baseline: string; deficitSummary: string }` 출력 — 차원별 weight + baseline 박제 박제 + deficitSummary 박제 박제
  6. 데이터 contract (`analysis.ts` ↔ `models.py`) 양쪽 lockstep 추가
  7. mode 분기 카피 정합: mode1 ("정은지 측정값 기준"), mode3 first ("이번이 첫 분석"), mode3 second+ ("지난 분석 대비 +5점")
  8. 빌드 12 TestFlight ship 박제 (letterSpacing/Cerebras 회귀 박제 X)

**Plans**: TBD
**UI hint**: yes

### Phase 13: 보완 운동 추천 + LLM 분기 카피 + coaching detail 완성

**Goal**: (a) 분석 결과의 실패 원인 후보·체형 정규화 finding 에 따라 보완 운동·스트레칭이 자동 매핑되어 결과 화면에 표시되고, (b) Cerebras LLM 이 실 영상 분석에서 `tip.detail2` (causes/injuryRisk/coachNote) 동적 생성하며, (c) 동작이 IPSF 등재인지 학원 통용인지에 따라 차원 자세히 모달의 formula/baseline/심사평 카피가 분기되어 출력된다 (분석 → 행동 → 재구매 + 코칭 신뢰도)
**Mode:** mvp
**Depends on**: Phase 7, Phase 9 (체형 차이·실패 원인 위에 매핑), Phase 12.5 (UI transparency layer 완성된 후 backend 채움)
**Requirements**: PERS-03, [`studio-term-3branch-system`] 메모리
**Scope 제약**: 초기 3~5개 동작군에 대해 보완 운동 5~10개 큐레이션. 영상 가이드는 v2. LLM 분기는 분기 1 (IPSF 등재) + 분기 2 (학원 통용 정은지 reference) 만 v1, 분기 3 (자동 수집) 은 v2.
**Success Criteria** (what must be TRUE):

  1. 실패 원인·체형 차이별로 매핑된 보완 운동·스트레칭 라이브러리(JSON/Firestore)가 존재한다
  2. 결과 화면이 사용자별 분석 결과에 맞는 보완 운동 3~5개를 표시한다
  3. 매핑 로직이 동작 인식 결과 + 실패 후보 + 통증부위(BodyProfile)를 함께 고려한다
  4. 사용자가 "다른 운동 보기" 같은 액션으로 라이브러리를 탐색할 수 있다
  5. Pod 갱신 + uvicorn 재시작 후 실 영상 분석에서 Cerebras `tip.detail2` 가 채워져 Firestore doc 에 저장되고, 결과 화면 "코칭 팁 자세히 ›" 가 시뮬 fixture 와 동일 UI 로 실 LLM 응답 표시
  6. `assemble.build_dimension_explanation` 이 `motionId` 의 `ipsfCode` 유무로 분기 1 vs 분기 2 카피 분리 (분기 1 = "세계 심사 기준 (IPSF) + 180°", 분기 2 = "정은지 선수 기준 자세")
  7. `coach_writer` 시스템 프롬프트에 동작 이름 + 분기 정보 + IPSF 정의 각도 fixture (angle 차원, 어깨 90° 등) 가 주입되어 자연어 응답이 정확한 기준 각도를 인용
  8. 학원 용어 (폭스탑) 입력 시 결과 화면이 "세계 심사 기준" 어색 표현 없이 "정은지 선수 기준" 으로 자연 노출

**Plans**: TBD — 보완 운동 라이브러리 plan + LLM 분기 plan 분리 또는 통합 결정은 planner 가
**UI hint**: yes

### Phase 14: 정은지 기준 모션 등록 (다각도 캡처 가이드)

**Goal**: 정은지 기준 모션을 다각도 캡처 프로토콜에 따라 등록할 수 있고, 등록된 모션이 BodyNormalizationProfile·EXTEND 프로파일·ForceDirectionPattern을 포함해 Mode 1 비교에 바로 쓰인다
**Mode:** mvp
**Depends on**: Phase 5 (기술 인식), Phase 6 (정규화), Phase 9 (힘 패턴) — 기준 모션이 두 엔진 출력을 모두 가져야 비교 가능
**Requirements**: REF-01
**Scope 제약**: 기준 모션도 초기 3~5개 동작군 범위.
**Success Criteria** (what must be TRUE):

  1. 정은지 영상(다각도 권장)을 업로드하면 기준 모션으로 등록되어 `reference/{motionId}`에 저장되고 앱 Mode 1 목록에 나타난다
  2. 등록된 기준 모션이 meanAngles·EXTEND 프로파일·BodyNormalizationProfile·ForceDirectionPattern을 포함한다
  3. 다각도 캡처 가이드(촬영 조건·앵글·시점 수)가 문서화되어 등록 정확도가 재현 가능하다
  4. 다각도가 없는 단일 시점 기준 모션도 graceful하게 처리되고 confidence가 낮게 표기된다

**Plans**: TBD

### Phase 16: Studio Terminology Foundation (3-branch + 5-Track v1 평행)

**Goal**: 학원 용어 3분기 시스템 (AKA 매핑 / 정은지 reference / 자동 수집) + IPSF 5트랙 채점 v1 scope (a + c + Page 9 절대 트랙) 의 데이터·스펙·UX 카피를 박제한다. **MVP 가볍게**: 코드 변경 최소, 데이터/스펙/카피 박제 중심. **실증 단계 검증 후 확장**: 폴스포츠 학원 파일럿에서 사용자 입력 패턴 (분기 1/2/3 비율, 자동 수집 키워드 누적) 을 데이터로 본 다음 분기 2 reference / 분기 3 승격 알고리즘 / 분기 1 매핑 확장을 한 번에 진행. **v1 평행 진행**: Phase 1~15 의존성 없음 — 데이터/스펙/카피 박제는 코드 진척과 독립적.
**Mode:** mvp
**Depends on**: Nothing (v1 평행 — 데이터/스펙/카피 박제)
**Requirements**: SCORE-05, TERM-01, TERM-DATA-01, TERM-COPY-01
**Scope 제약**: MVP 가볍게 — (1) AKA 매핑 13개 박제 (NotebookLM lookup 2026-06-02 출처) + 각 IPSF Code + Criteria source_ref (2) 분기 2 정은지 reference 비등재 동작 1~2개 (폭스탑 우선 — 운영자 설문 직접 예시) (3) 분기 3 자동 수집 데이터 스키마 + UX 카피 노출 stub (4) 5트랙 채점 v1 = (a) Compulsory Criteria + (c) Technical Deduction + Page 9 절대 공통 트랙. (b) Tech Bonus 연계 가산 + (d) Artistic 정성 = v2 (SCORE-V2-02/03). 사람 점수 라벨링 영구 금지 ([[analysis-objectivity-no-human-scores]] 정합 — 모든 데이터는 IPSF Code of Points 임계값 + 정은지 영상 측정값 기준만).
**External dependency**: NotebookLM (IPSF lookup 자동화), 정은지 영상 (이미 보유 가정). belle/강사 협업 없이 박제 가능 (사람 점수 라벨링 X).
**Success Criteria** (what must be TRUE):

  1. AKA 매핑 13개가 데이터 파일 (예: `backend/data/aka-mapping.json` 또는 reference-motions 확장) 에 박제되어 있고, 각 entry 가 한국 학원 명칭 + IPSF Code + IPSF 공식 영문명 + source_ref (NotebookLM citation) 을 포함한다
  2. 분기 2 정은지 reference 비등재 동작 (최소 폭스탑) 1개가 reference-motions 에 등록되어 있고, isRegistered=false 플래그로 분기 1 과 구분된다
  3. 분기 3 자동 수집 데이터 스키마 (`pending_terms` 컬렉션 또는 동등 구조) 가 정의되어 있고 입력 키워드 + 사용자 익명 ID + 누적 카운트를 저장한다
  4. 분기 3 UX 카피가 belle 작성 그대로 (변경/요약/재가공 X) 분석 흐름에 노출되는 위치가 박제되어 있다 (코드 통합은 후속 plan, 박제만 v1)
  5. 5트랙 채점 v1 scope = (a) + (c) + Page 9 절대 트랙이 채점 엔진 코드의 architectural decision 으로 박제되어 있다 (PROJECT.md Key Decisions + memory [[ipsf-5-track-scoring]] cross-reference)
  6. JUDGE-DATA-01 (v1.5) 와 데이터 형식 동일 (GeometricCriterion) — v1.5 진입 시 추가 박제만 하면 되는 구조
  7. **실증 검증 게이트** (파일럿 후, belle 2026-06-02 결정 박제 — Plan 16-01 T-6):
     - **(a) 분기 1 매핑률 X% threshold = deferred** — belle 결정: 매핑률 자체가 v1 게이트 아님. 진짜 게이트 = 분석 정확도 (특히 고수 위양성 방지, 정은지 41점 같은 케이스 없음). 매핑률은 실증 데이터 수집 후 belle 와 재결정 ([[feedback-analysis-first]] + Core Value 정합).
     - **(b) 분기 3 신규 키워드 승격 기준 = 둘 이상 anon userId** — MVP 단순. `uniqueUserCount >= 2` 충족 시 `promotionStatus: pending → reviewing` 자동 전환 (16-AUTOCOLLECT-SCHEMA.md). 학원 ID 트래킹 기반 정밀화는 v2.
     - **(c) 분기 2 reference 사용률 = v1 게이트 아님** — belle 결정: 사용률 측정 자체보다 "분기 2 reference 사용 시 분석 정확도 (Page 9 트랙 + 정은지 측정값) 가 작동하는지" 가 진짜 검증 (정성). 운영 metric 으로만 박제, v2 belle 재논의.
     - **확장 path**: 게이트 통과 후 한 번에 진행 — 분기 2 reference 5~10개 추가 + 분기 3 승격 알고리즘 + 분기 1 NotebookLM batch lookup 자동화.

**Plans**:

  - [x] 16-01-PLAN.md — AKA 매핑 13개 + 5트랙 v1 spec + 분기 2 정은지 reference + 자동 수집 스키마 + UX 카피 박제 위치 + 실증 검증 게이트 threshold belle 협의 (T-1~T-7, code change 0)

### Phase 15: Mode 1·Mode 3 실영상 + 신뢰도 게이트 + TestFlight

**Goal**: 사용자가 Mode 1(정은지 기준 비교)과 Mode 3(자기 영상 발전)을 실영상으로 완주하고, 고수 영상에서 위양성 없이 신뢰할 만한 점수를 받고, TestFlight 게스트 모드에서 회원가입 없이 실기기로 완주한다
**Mode:** mvp
**Depends on**: Phase 11, Phase 12, Phase 13, Phase 14 (리포트·표시·보완운동·기준모션 모두 준비됨)
**Requirements**: MODE-01, MODE-02, SCORE-04, DELIV-01
**Scope 제약**: 검증 대상은 초기 3~5개 동작군. 범위 밖 false-reject 허용.
**Success Criteria** (what must be TRUE):

  1. Mode 1: 사용자가 정은지 기준 모션을 선택해 본인 영상을 올리면 실분석 결과와 전문가 기준 점수가 표시된다 (referenceMotionId lockstep)
  2. Mode 3: 사용자가 본인 영상 2개를 올리면 절대 지표의 세션 간 델타가 "지난 분석보다 무릎 신전 8° 개선" 형태로 표시된다
  3. 신뢰도 게이트: 정은지(고수) 영상이 41점 같은 위양성 없이 자세 품질을 반영하는 점수로 산출된다
  4. 다양한 동작/앵글 영상 세트에서 분석이 크래시 없이 일관된 점수를 낸다
  5. TestFlight: 수강생이 익명 게스트로 진입해 회원가입 없이 Mode 1·Mode 3를 실기기에서 완주하고 결과 영상이 재생된다 (presigned URL 만료/Content-Type 이슈 없음, letterSpacing SIGABRT 회귀 없음)

**Plans**: TBD
**UI hint**: yes

## v1.5 (Planned, 별도 마일스톤)

v1 코드 phase 아님. 데이터 수집 작업은 v1 동시 평행 진행 (belle/강사 협업).

- **IPSF Code of Points 임계값 데이터 라벨링** — 3~5개 동작 × phase별 `GeometricCriterion`(targetValue, toleranceFull, deductionPerStep, minimumRequirement)
- **judging 모드 코드 구현** — `JudgingModeReport` 렌더 + 정규화 OFF 분기 + "예술 점수 제외" 디스클레이머
- **RTMW clean weight 경로(B)** — **출시 hard gate** (belle 2026-06-02 지시, `docs/licenses/rtmw-weights-audit.md §4-1`). 정식 상업 출시(공개·과금) 전 현 `rtmw-x-384x288` (Cocktail14 학습, validation-pilot scope 한정) 을 (a) mmpose 공식 commercial-friendly weight 또는 (b) 자체 clean-data fine-tune 으로 교체. 별도 plan 작성·시작 필요. 차단 미해소 시 상업 출시 불가.

## Progress

**Execution Order:**
~~Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15~~

**2026-06-08 belle 갱신 — 분석 정확도 핵심 차원 v1 진행 (이전 보류 결정 무효)**:

- close-out 박제: Phase 1 ✓ / Phase 2 ✓ / Phase 5 ✓ / Phase 12.5 ✓ / Phase 16 ✓
- **belle 박제** (2026-06-08): "분석이 제대로 되는 게 목표. 오버레이, 체형 정규화, 힘 패턴은 필수적이지. 어떻게든 기필코 개발하려고 하는 게 지금."
- **v1 시퀀스 (분석 정확도 chain — ROADMAP dep 그래프 정합)**:
  1. **Phase 6** = 체형 정규화 비교 엔진 (coaching 모드) — dep: 2 ✓, 5 ✓ — **현재 진입 (`06-CONTEXT.md` 2026-06-08 박제, plan-phase 2026-06-09 오전 9시 진입)**
  2. **Phase 7** = 차이 분류 (체형 허용 / 개선 필요 / uncertain) — dep: 6
  3. **Phase 8** = 중심축 이탈 + 접촉점 안정성 + jerk/jitter — dep: 1 ✓, 4 (단일 시점 fallback 박제 검토)
  4. **Phase 9** = ForceDirectionPattern + 실패 원인 후보 3 — dep: 8
  5. **Phase 12** = 실측 각도 + 키포인트 오버레이 — dep: 6, 7 (정규화된 각도 위에 표시)
  6. **Phase 13** = 보완 운동 + LLM 분기 카피 — dep: 7, 9, 12.5 ✓
- **이전 보류 reasoning 무효** — 2026-06-07 결정의 "두 엔진 본체 (체형 정규화 + 힘 패턴 + CoachCommentHook) 는 파일럿 후 v1.5" 박제는 본 갱신으로 무효. 메모리 [[feedback-analysis-first]] (분석이 망하면 다 망함 — 도메인 제대로 우선) + [[plan-vs-pivot-cross-check]] 정합. `.planning/roadmap-replan-2026-06-07.md` 는 이력 보존용.
- **Phase 10 (부상 위험) / Phase 11 (CoachCommentHook + Gemini 자연어 번역)** = Phase 9 close-out 후 belle 박제 (v1 / v1.5 분기). 현 시점 미결정.
- **Phase 14 (정은지 기준 모션 등록 다각도)** = Phase 6 D-06-B2 (reference-motions 컬렉션 BodyProfile 필드 추가) 가 plumbing 박제 후 일회 백필 fixture 로 우회 가능. 정식 Phase 14 진입 시점은 belle 박제.
- **Phase 15 (Mode 1·Mode 3 + 신뢰도 게이트 + TestFlight)** = Phase 11/12/13/14 박제 후. 빌드 N (빌드 12 ship 후) 박제.
- **(이력) 2026-06-07 belle 결정 — A+B+C 우선, Phase 2~11 보류 (파일럿 후 v1.5)**: Phase 12.5 (B) + Phase 16 코드 통합 (C) + Phase 12 (A) 우선 시퀀스. Phase 12.5 ✓ close-out 후 belle 가 분석 정확도 우선으로 보류 결정 무효.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. PoseEngine + RTMW + 폴 축 + NLF R&D 격리 | 21/24 | Sufficient (close-out) | 2026-06-07 (Plan 01-24 후속) |
| 2. BodyNormalizationProfile (MediaPipe segment) | 1/1 | Complete   | 2026-06-07 |
| 3. 자가입력 BodyProfileInput | 0/TBD | Not started | - |
| 4. 다중 시점 촬영 + occlusion 게이트 | 0/TBD | Not started | - |
| 5. Gemini 기술 인식기 (분류 한정) | 6/6 | Complete | 2026-06-05 (12차 sweep D-01 PASS) |
| 6. 체형 정규화 비교 엔진 | 0/2 | Plans created (2026-06-08) | - |
| 7. 차이 분류 | 0/TBD | Not started | - |
| 8. 중심축·접촉점·jerk 분석 | 0/TBD | Not started | - |
| 9. ForceDirectionPattern + 실패 후보 3개 | 0/TBD | Not started | - |
| 10. 부상 위험 신호 플래그 | 0/TBD | Not started | - |
| 11. CoachCommentHook + Gemini 번역 | 0/TBD | Not started | - |
| 12. 실측 각도 + 키포인트 오버레이 | 0/TBD | Not started (v1 chain #5) | - |
| 12.5. UI Transparency (차원별 카피 + 강사 보조) | 1/1 | Complete | 2026-06-07 |
| 13. 보완 운동·스트레칭 추천 | 0/TBD | Not started (v1 chain #6) | - |
| 14. 정은지 기준 모션 등록 (다각도) | 0/TBD | Not started | - |
| 15. Mode 1·Mode 3 + 신뢰도 게이트 + TestFlight | 0/TBD | Not started | - |
| 16. Studio Terminology Foundation (3-branch + 5-Track v1) | 1/1 | Complete   | 2026-06-02 |

---
*Roadmap created: 2026-05-29 (brownfield MVP — vertical slices over existing pipeline)*
*Roadmap restructured: 2026-05-31 (research 3 docs 반영 — 공통 레이어 + 엔진 A·B + 코치 훅 아키텍처, 11→15 phases)*
*Roadmap updated: 2026-05-31 (belle 결정 — 상용/베타 = MediaPipe + Gemini, NLF/SMPL-X = R&D 비교군 격리. Phase 1·2 재정의)*
*Roadmap updated: 2026-05-31 (--reviews replan — Phase 1 wave 순서 정정: Wave 2 belle gate before Wave 3 swap, Success #3 video-level PoleAxis wording 정정 per L-1)*
*Roadmap updated: 2026-06-01 (Plan 11 sweep verdict 적재 — Phase 1 Plans 07~11 박제 누락 보정 + Plan 12/13/14 신설 (갭 root cause + Gemini key moment + 재검증). Success #7 신설 (갭 ≤5 + line/angle PASS). Plan 04/05 진입 조건 = Plan 14 통과로 변경. belle 결정 — D-14 강등 거부, 둘 다 1순위 게이트.)*
*Roadmap updated: 2026-06-01 (Plan 12 report-only (c)(d) strong — NLF baseline 부적합 박제 + belle 분석 객관성 절대 원칙 재확인. Plan 15 신설 (JUDGE-DATA-01 IPSF GeometricCriterion 데이터 수집, v1 평행 진행). Success #7 baseline 변경 — NLF 갭 → IPSF tolerance. 사람 점수 라벨링 영구 금지 원칙 박제 (memory analysis-objectivity-no-human-scores + judging-baseline-ipsf-code-of-points).)*
*Roadmap updated: 2026-06-02 (Phase 16 신설 — Studio Terminology Foundation. belle 결정: 학원 사용자 1차 진입 시 학원 용어 처리 path 가 v1 필수. 3분기 시스템 (AKA / 정은지 reference / 자동 수집) + IPSF 5트랙 채점 v1 scope (a+c+Page9). NotebookLM IPSF CoP 2024-2025 lookup 결과 박제. MVP 가볍게 + 실증 검증 게이트 통과 후 한 번에 확장 path. Phase 16 은 의존성 없음 → v1 평행 진행 가능. 현장 설문 강사 5-1 "기본기 표준화" + 운영자 5-2 "기술 데이터 표준화" + 운영자 5-2 "폭스탑 3회 분석" 예시 직접 충족.)*
*Roadmap updated: 2026-06-02 (RTMW free-stack pivot — Phase 1 신규 plan 7개 추가 (01-19 ~ 01-25, gap_closure). 운영 백본 = MediaPipe + MotionBERT → RTMW 133 wholebody (Apache-2.0) 단일 백본 (D-17~D-25). 01-04/01-05/01-14 SUPERSEDED 마킹. 01-18 on hold 유지. Phase 2 BodyNormalizationProfile = RTMW segment 기반 재정의 (D-19, 추후 Phase 2 plan 에서 반영). 출처 = CONTEXT.md D-17~D-25 + /Users/kimtaesung/Downloads/Sunity_v1_개발지시_RTMW무료스택.md + memory rtmw-free-stack-pivot.)*
*Roadmap updated: 2026-06-02 (Plan 01-20 belle license checkpoint 통과 — Production=rtmw-x-384x288 (commercial_ok, validation-pilot scope), Fallback=rtmw-l-384x288. weights_manifest production_eligible=1. Plan 21 진입 차단 해소. v1.5 에 "RTMW clean weight 경로(B) 출시 hard gate" 박제 — 상업 출시 전 mmpose 공식 commercial-friendly weight 또는 자체 clean-data fine-tune 으로 교체 필요 (belle 지시 별도 plan).)*
