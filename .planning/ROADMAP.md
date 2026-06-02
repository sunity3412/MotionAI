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

- [ ] **Phase 1: PoseEngine 추상화 + MediaPipe 어댑터 + 폴 축 정렬 + NLF R&D 격리** - 상용 제품 코드를 MediaPipe로 마이그레이션, NLF/SMPL-X는 R&D 비교군으로 격리, 폴 축 좌표계 산출 (모든 분석의 기반)
- [ ] **Phase 2: BodyNormalizationProfile 자동 측정 (MediaPipe segment 기반)** - 키·팔/다리/몸통 비율·좌우 비대칭 자동 추출. SMPL-X β는 R&D 비교군에서만 (제품 코드 사용 금지)
- [ ] **Phase 3: 자가입력 BodyProfileInput** - 키·몸무게·경력·통증부위 1회 입력 UX
- [ ] **Phase 4: 다중 시점 촬영 UX + occlusion confidence 게이트** - 가림 완화 + 저신뢰 프레임 "추정" 표기
- [ ] **Phase 5: Gemini 기술 인식기 (분류 한정)** - 동작 분류만, 좌표·판단 출력 금지 (역할 축소)
- [ ] **Phase 6: 체형 정규화 비교 엔진 (coaching 모드)** - 프로 패턴을 수강생 체형 비율로 재계산
- [ ] **Phase 7: 차이 분류** - 체형 허용 차이 / 개선 필요 차이 / 감점 분리
- [ ] **Phase 8: 중심축 이탈 + 접촉점 안정성 + jerk/jitter** - 힘 패턴 추론을 위한 기초 신호
- [ ] **Phase 9: ForceDirectionPattern + 실패 원인 후보 3개** - pull/push/brace/rotate/release + 실패 후보 3카드
- [ ] **Phase 10: 부상 위험 신호 플래그** - 좌우 비대칭·요추 과신전·무리 동작 신호 (SAFE-01 v1)
- [ ] **Phase 11: CoachCommentHook 데이터 구조 + Gemini 자연어 번역만** - AI+코치 비즈니스 모델 + 설명 엔진 한정
- [ ] **Phase 12: 실측 각도 표시 + 키포인트 오버레이** - "현재 87° → 기준 110°" + 어깨/골반/무릎/손/중심축
- [ ] **Phase 13: 보완 운동·스트레칭 추천 라이브러리** - 분석 → 행동 매핑 (PERS-03 v1)
- [ ] **Phase 14: 정은지 기준 모션 등록 (다각도 캡처 가이드)** - 비교 정확도 최대화 + 다각도 캡처 프로토콜
- [ ] **Phase 15: Mode 1·Mode 3 실영상 + 신뢰도 게이트 + TestFlight** - 두 모드 end-to-end + 고수 위양성 없음 + 실기기 게스트 완주
- [ ] **Phase 16: Studio Terminology Foundation (3-branch + 5-Track v1 평행)** - 학원 용어 3분기 시스템 + IPSF 5트랙 채점 v1 scope 데이터/스펙/카피 박제. v1 평행 진행 (Phase 1~15 의존성 없음). MVP 가볍게 + 실증 단계 검증 후 확장 path.

## Phase Details

### Phase 1: PoseEngine 추상화 + MediaPipe 어댑터 + 폴 축 정렬 + NLF R&D 격리
**Goal**: 상용 제품 코드를 NLF → MediaPipe로 마이그레이션하고, `PoseEngine` 인터페이스 + 공통 계약(`PoseFrame` / `BodyNormalizationProfile`)을 도입한다. NLF/SMPL-X는 R&D 비교군 어댑터로 격리(제품 호출 경로에서 제거). 동시에 폴 축 자동 검출 + 기준 좌표계 정렬을 MediaPipe 위에서 산출한다 — 모든 다운스트림의 기반.
**Mode:** mvp
**Depends on**: Nothing (공통 레이어 첫 단계 — 현 NLF 코드 마이그레이션 포함)
**Requirements**: POSE-01, POSE-02
**Scope 제약**: 초기 3~5개 동작군 범위(똑바로 선·가림 적은). 스피닝 폴은 v1.5. NLF/SMPL-X는 R&D 비교군 비공개 평가에만 사용 — 공개 베타·유료 파일럿·고객 영상 처리 금지.
**External dependency**: MediaPipe Pose (Apache 2.0, 라이선스 리스크 0). NLF/SMPL-X R&D 비교군은 PS:License 1.0 (비상업) 사내 평가만.
**Success Criteria** (what must be TRUE):
  1. `PoseEngine` 인터페이스가 정의되고 `MediaPipePoseEngine` 어댑터가 제품 코드 경로(Lambda/RunPod 파이프라인)에서 동작한다
  2. `NlfPoseEngine` 어댑터는 별도 모듈로 격리되어 R&D 평가 스크립트에서만 호출 가능 (제품 파이프라인 import 경로에서 제거)
  3. 영상에서 폴 축이 자동 검출되고 video-level **PoleAxis가 1개 산출되어 모든 frame의 PoseFrame.pole_axis에 적용되고**, 모든 키포인트 좌표가 폴 기준 좌표계로 변환된 결과를 반환한다 (D-10 — 일반 폴 가정, 스피닝 폴은 v1.5)
  4. 키포인트 confidence가 임계값 미만인 프레임은 "추정"으로 표기되고 후속 분석이 단정하지 않는다
  5. R&D 평가 스크립트가 MediaPipe vs NLF 정확도 갭을 동일 영상 세트에서 측정해 보고서로 출력한다 (마이그레이션 ROI 판단 근거)
  6. 데이터 계약(`analysis.ts` ↔ `models.py`)에 `PoseFrame` 타입이 lockstep으로 추가된다
  7. **5영상 sweep 재실행 시 (a) IPSF GeometricCriterion 갭 ≤ tolerance + (b) line/angle 5/5 PASS** — 두 게이트 모두 통과해야 Wave 3 (Plan 04/05) 진입 가능. baseline 은 NLF 갭이 아닌 **IPSF Code of Points 객관 임계값** (Plan 12 (c) strong / belle 결정 2026-06-01). 강등/우회/known limitation 수용 금지. 사람 점수 라벨링 (belle/강사/심사자) 영구 금지.
**Plans**: 15 plans (Wave 순서: Wave 0 → Wave 1 → Wave 2 spike & 검증 → Wave 3 swap)
  - [x] 01-01-PLAN.md — PoseFrame + PoleAxis 데이터 계약 3-way lockstep + reliability 게이트 stub + Wave 0 테스트 픽스처 (Wave 0)
  - [x] 01-02-PLAN.md — PoseEngine Protocol + MediaPipePoseEngine 어댑터 + 33→COCO-17 + grip 확장 매핑 (Wave 1)
  - [x] 01-03-PLAN.md — HoughPoleDetector + PoleAxisAligner — lazy cv2/scipy import (D-09/D-10/D-11/D-12) (Wave 1)
  - [x] 01-06-PLAN.md — compare_engines.py 회귀 검증 + belle 검토 checkpoint (D-13~D-16) — **Wave 3 gate (구)** (Wave 2)
  - [x] 01-07-PLAN.md — MotionBERT-lite lifter spike (2D→3D pose lift) — MIT 라이선스 박제 (Wave 2)
  - [x] 01-08-PLAN.md — MediaPipe + MotionBERT 운영 통합 + 5영상 회귀 — 4/5 PASS, ref-sideway-spin 64 FAIL (Wave 2)
  - [closed] 01-09-PLAN.md — AlphaPose 측면 보강 spike — license_blocked (Noncommercial, 영구 후보 제외) (Wave 2)
  - [x] 01-10-PLAN.md — RTMPose-l (MMPose Apache 2.0) 단일 영상 spike — STRONG_PASS (ref-sideway-spin 72) (Wave 2)
  - [x] 01-11-PLAN.md — RTMPose 5영상 sweep + line/angle root cause + 게이트 룰 검토 — **verdict gap_too_wide_blocked** (D-15① 5/5 PASS / D-14 4/5 FAIL / line·angle 5/5 N/A) (Wave 2)
  - [~] 01-12-PLAN.md — 갭 root cause 디버그 spike — T-1~T-4 완료, T-5 belle Pod live 대기. report-only verdict (c)/(d) strong → NLF baseline 부적합 박제 → Plan 15 신설 (Wave 2, NEW 2026-06-01)
  - [ ] 01-15-PLAN.md — **JUDGE-DATA-01 IPSF GeometricCriterion 데이터 수집** (5영상 × phase별 동작 객관 임계값 표). NLF 갭 baseline 폐기 → IPSF tolerance baseline. 사람 점수 라벨링 영구 금지 원칙 박제 후 첫 객관 데이터 작업 (Wave 2, **NEW** 2026-06-01)
  - [~] 01-13-PLAN.md — Gemini key moment timestamp + criteria extractor (multimodal 2.5 Pro). T-1~T-6 완료. **verdict `measurement_unreliable_blocked`** — Gemini moment 추출 + IPSF criteria 비교 pipeline 통과했으나 측정값 자체 의심 (정은지 invert peak hold right_shoulder 18.2° 같은 인체학적 비정상). Plan 12 (e) "두 엔진 3D 분포 strong" 직접 연결. (Wave 2, NEW 2026-06-01, **Plan 14 차단 → Plan 16 필수**)
  - [x] 01-16-PLAN.md — **측정 신뢰도 trace spike** — T-1~T-6 완료. belle Pod live mode 결과 dominant ['b', 'c', 'd'] — left_elbow swap_ratio 1.00 / cross-engine disagreement 34.57° / 영상 평균 |L-R| 43.14°. (a) frame_idx rejected. (Wave 2, COMPLETE 2026-06-01)
  - [x] 01-17-PLAN.md — **keypoint mapping audit + swap fix** (Codex Cycle 3 PASS) — T-1 audit 결과 `blocked/no-static-mapping-defect`. 5 mapping source 58 row canonical (failed 0). Plan 16 swap_ratio 1.00 root cause = static index defect 가 아니라 lift path 자체의 좌우 신뢰도 약점. T-2/T-3/T-4 hard abort branch 정확히 발동. (Wave 2, COMPLETE 2026-06-01)
  - [ ] 01-18-PLAN.md — **multi-engine averaging spike** (NEW) — Plan 16 가설 (d) cross-engine 34.57° strong + Plan 17 audit 통과 후속. RTMPose+MB + MP+MB voting/평균으로 좌우 noise cancel. ref-invert 단독 시범 → swap_ratio ≤ 0.05 + lifter.overall ≥ 85 게이트. (Wave 2, NEW 2026-06-01, **Plan 14 진입 gate**)
  - [ ] 01-14-PLAN.md — 5영상 재검증 sweep — Plan 13 key moment + Plan 15 IPSF 임계값 적용 후 sweep_rtmpose 재실행. **게이트 = IPSF tolerance 안 + line/angle 5/5 PASS** (Wave 2, NEW 2026-06-01, Wave 3 진입 gate — **Plan 16 통과 후 진입**)
  - [ ] 01-04-PLAN.md — NLF R&D 격리 (backend/research/로 이동 + .samignore) (Wave 3 — **Plan 14 통과 후 진입**)
  - [ ] 01-05-PLAN.md — pipeline/app.py atomic swap + RunPod requirements.txt/setup.sh/README 갱신 (Wave 3 — **Plan 14 통과 후 진입**)

### Phase 2: BodyNormalizationProfile 자동 측정 (MediaPipe segment 기반)
**Goal**: MediaPipe 키포인트로부터 신체 segment 길이(상완·전완·대퇴·하퇴·몸통, 어깨/골반 폭) 및 비율을 산출해 `BodyNormalizationProfile`(estimatedHeightScale, armScale, legScale, torsoScale, shoulderHipRatio, confidence, warnings)을 자동 출력한다 — 두 엔진의 공유 입력. SMPL-X β는 R&D 비교군에서만 정확도 평가용으로 사용.
**Mode:** mvp
**Depends on**: Phase 1 (MediaPipe + 폴 축 정렬된 키포인트 위에 segment 측정)
**Requirements**: BODY-01
**Success Criteria** (what must be TRUE):
  1. MediaPipe 키포인트에서 segment 길이가 시간 평균으로 안정적으로 추출된다 (jitter 스무딩)
  2. `BodyNormalizationProfile`이 키·팔/다리/몸통 스케일·어깨/골반 비율·confidence·warnings로 산출된다
  3. 낮은 confidence(가림·저화질) 시 단정하지 않고 warnings 배열에 사유가 표기된다
  4. R&D 비교군: 동일 영상에서 NLF→SMPL-X β로 추출한 BodyNormalizationProfile과의 갭을 보고서로 출력 (제품 코드 비호출, 평가 전용)
  5. 데이터 계약(`analysis.ts` ↔ `models.py`)에 `BodyNormalizationProfile` 타입이 lockstep으로 추가된다
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

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

### Phase 13: 보완 운동·스트레칭 추천 라이브러리
**Goal**: 분석 결과의 실패 원인 후보·체형 정규화 finding에 따라 보완 운동·스트레칭이 자동 매핑되어 결과 화면에 표시된다 (분석 → 행동 → 재구매)
**Mode:** mvp
**Depends on**: Phase 7, Phase 9 (체형 차이·실패 원인 위에 매핑)
**Requirements**: PERS-03
**Scope 제약**: 초기 3~5개 동작군에 대해 보완 운동 5~10개 큐레이션. 영상 가이드는 v2.
**Success Criteria** (what must be TRUE):
  1. 실패 원인·체형 차이별로 매핑된 보완 운동·스트레칭 라이브러리(JSON/Firestore)가 존재한다
  2. 결과 화면이 사용자별 분석 결과에 맞는 보완 운동 3~5개를 표시한다
  3. 매핑 로직이 동작 인식 결과 + 실패 후보 + 통증부위(BodyProfile)를 함께 고려한다
  4. 사용자가 "다른 운동 보기" 같은 액션으로 라이브러리를 탐색할 수 있다
**Plans**: TBD
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
  7. **실증 검증 게이트** (파일럿 후): (a) 사용자가 입력한 키워드 중 분기 1 매핑률 ≥ X% (b) 분기 3 자동 수집된 신규 키워드 누적 패턴 (둘 이상 사용자 입력 키워드 수) (c) 분기 2 reference 사용률. 게이트 통과 후 한 번에 확장 진행 (분기 2 reference 5~10개 추가 + 분기 3 승격 알고리즘 + 분기 1 NotebookLM batch lookup 자동화). X% threshold 는 16-01-PLAN.md 에서 belle 협의 후 박제
**Plans**:
  - [ ] 16-01-PLAN.md — AKA 매핑 13개 + 5트랙 v1 spec + 분기 2 정은지 reference + 자동 수집 스키마 + UX 카피 박제 위치 + 실증 검증 게이트 threshold belle 협의 (T-1~T-7, code change 0)

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

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15
**Phase 16** is independent (v1 평행 — Phase 1~15 의존성 없음). 데이터/스펙/카피 박제가 코드 진척과 독립적이므로 Phase 1 진행 중 평행 진입 가능. Phase 5 (Gemini 기술 인식기) / Phase 14 (정은지 reference) 가 Phase 16 의 데이터를 소비.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. PoseEngine + MediaPipe + 폴 축 + NLF R&D 격리 | 8/15 | In Progress (Plan 12 (c)/(d) strong → Plan 15 신설, IPSF baseline 도입)|  |
| 2. BodyNormalizationProfile (MediaPipe segment) | 0/TBD | Not started | - |
| 3. 자가입력 BodyProfileInput | 0/TBD | Not started | - |
| 4. 다중 시점 촬영 + occlusion 게이트 | 0/TBD | Not started | - |
| 5. Gemini 기술 인식기 (분류 한정) | 0/TBD | Not started | - |
| 6. 체형 정규화 비교 엔진 | 0/TBD | Not started | - |
| 7. 차이 분류 | 0/TBD | Not started | - |
| 8. 중심축·접촉점·jerk 분석 | 0/TBD | Not started | - |
| 9. ForceDirectionPattern + 실패 후보 3개 | 0/TBD | Not started | - |
| 10. 부상 위험 신호 플래그 | 0/TBD | Not started | - |
| 11. CoachCommentHook + Gemini 번역 | 0/TBD | Not started | - |
| 12. 실측 각도 + 키포인트 오버레이 | 0/TBD | Not started | - |
| 13. 보완 운동·스트레칭 추천 | 0/TBD | Not started | - |
| 14. 정은지 기준 모션 등록 (다각도) | 0/TBD | Not started | - |
| 15. Mode 1·Mode 3 + 신뢰도 게이트 + TestFlight | 0/TBD | Not started | - |
| 16. Studio Terminology Foundation (3-branch + 5-Track v1) | 0/TBD | Not started (NEW 2026-06-02) | - |

---
*Roadmap created: 2026-05-29 (brownfield MVP — vertical slices over existing pipeline)*
*Roadmap restructured: 2026-05-31 (research 3 docs 반영 — 공통 레이어 + 엔진 A·B + 코치 훅 아키텍처, 11→15 phases)*
*Roadmap updated: 2026-05-31 (belle 결정 — 상용/베타 = MediaPipe + Gemini, NLF/SMPL-X = R&D 비교군 격리. Phase 1·2 재정의)*
*Roadmap updated: 2026-05-31 (--reviews replan — Phase 1 wave 순서 정정: Wave 2 belle gate before Wave 3 swap, Success #3 video-level PoleAxis wording 정정 per L-1)*
*Roadmap updated: 2026-06-01 (Plan 11 sweep verdict 적재 — Phase 1 Plans 07~11 박제 누락 보정 + Plan 12/13/14 신설 (갭 root cause + Gemini key moment + 재검증). Success #7 신설 (갭 ≤5 + line/angle PASS). Plan 04/05 진입 조건 = Plan 14 통과로 변경. belle 결정 — D-14 강등 거부, 둘 다 1순위 게이트.)*
*Roadmap updated: 2026-06-01 (Plan 12 report-only (c)(d) strong — NLF baseline 부적합 박제 + belle 분석 객관성 절대 원칙 재확인. Plan 15 신설 (JUDGE-DATA-01 IPSF GeometricCriterion 데이터 수집, v1 평행 진행). Success #7 baseline 변경 — NLF 갭 → IPSF tolerance. 사람 점수 라벨링 영구 금지 원칙 박제 (memory analysis-objectivity-no-human-scores + judging-baseline-ipsf-code-of-points).)*
*Roadmap updated: 2026-06-02 (Phase 16 신설 — Studio Terminology Foundation. belle 결정: 학원 사용자 1차 진입 시 학원 용어 처리 path 가 v1 필수. 3분기 시스템 (AKA / 정은지 reference / 자동 수집) + IPSF 5트랙 채점 v1 scope (a+c+Page9). NotebookLM IPSF CoP 2024-2025 lookup 결과 박제. MVP 가볍게 + 실증 검증 게이트 통과 후 한 번에 확장 path. Phase 16 은 의존성 없음 → v1 평행 진행 가능. 현장 설문 강사 5-1 "기본기 표준화" + 운영자 5-2 "기술 데이터 표준화" + 운영자 5-2 "폭스탑 3회 분석" 예시 직접 충족.)*
