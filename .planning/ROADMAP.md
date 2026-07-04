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
- [x] **Phase 3: 자가입력 BodyProfileInput** - 키·몸무게·경력·통증부위 1회 입력 UX (completed 2026-06-15)
- [x] **Phase 4: Camera Angle AI (single-view 가상 다각도) + occlusion confidence 게이트** - 1영상 업로드 유지, 가림/저신뢰 구간만 AI 보완 + "추정" 표기 (2026-06-13 belle pivot 재정의 — 다중 시점 직접 업로드 영구 제거) (completed 2026-06-14)
- [x] **Phase 5: Gemini 기술 인식기 (분류 한정)** - 동작 분류만, 좌표·판단 출력 금지. **2026-06-05 12차 sweep D-01 PASS** (phase1_ready_to_swap=True, phase5_ready_to_release_d16_block=True). 빌드 11 실분석 mode1 94 + mode3 100 PASS.
- [x] **Phase 6: 체형 정규화 비교 엔진 (coaching 모드)** - 프로 패턴을 수강생 체형 비율로 재계산 (completed 2026-06-08)
- [x] **Phase 7: 차이 분류** - 체형 허용 차이 / 개선 필요 차이 / uncertain 분리 + bodyTypeInterpretation·recommendation 박제 (completed 2026-06-08, 2 plans 108 phase07 PASS + Phase 6 회귀 0)
- [x] **Phase 8: 중심축 이탈 + 접촉점 안정성 + jerk/jitter** - 힘 패턴 추론을 위한 기초 신호. **2026-06-09 close-out** — 4 plans (08-00/01/02/03) 완료. 4 commits Plan 03 (fc3b6b7/ced1d87/c71c75b/f627905). 358 PASS + 1 skipped. 단, 정은지 5/5 영상 axis severity='high' 도메인 정합성 문제 발견 → Phase 8.1 (axis-metric-redesign) 신설 (belle α 결정). tilt 데이터 (rotation-only) 는 유의미 → Phase 9 1차 사용 가능.
- [x] **Phase 8.1: axis-metric-redesign** - 정은지 5/5 영상 axis severity high → low fix. Tilt metric 재설계 (rotation-only, distance 차원 제거) + `_normalize_angle_undirected` (modulo 180°) + `tilt_thresholds.yaml` schema_v2 lazy load + 정은지 5영상 P100+margin calibration + IPSF tolerance 20° / major fault 40°. **2026-06-09 close-out** — 3 plans (08.1-00/01/02) 완료. 413 PASS + 1 skipped. SC 5/5 PASS (정은지 5/5 axis severity 'low'). **Deferred (Codex C-MH1 정합)**: `AxisDeviationMetric` → `BodyLineTiltMetric` rename — 별도 plan.
- [x] **Phase 9: ForceDirectionPattern + 실패 원인 후보 3개** - pull/push/brace/rotate/release + 실패 후보 3카드 (completed 2026-06-10)
- [x] **Phase 10: 부상 위험 신호 플래그** - 좌우 비대칭·요추 과신전·무리 동작 신호 (SAFE-01 v1) (completed 2026-06-30)
- [x] **Phase 11: CoachCommentHook 데이터 구조 + Gemini 자연어 번역만** - AI+코치 비즈니스 모델 + 설명 엔진 한정 (completed 2026-06-16)
- [x] **Phase 12: 실측 각도 표시 + 키포인트 오버레이** - 6 build iteration (B/C/D fix + KeypointOverlay frame index Fix A + drift correction + 1080p 영상 압축) + 6 belle UAT (2026-06-10~12) close-out. **2026-06-12 PASS** — keypoint 사람 따라감 ✓ / 두 영상 동기화 ✓ / stall 해소 (4K → 1080p 압축 결정타) ✓. 잔여: 12-A 좌/우 mirror + ankle keypoint 추가 → Phase 13. Build 16 + OTA bundles ship.
- [x] **Phase 12.5: UI Transparency — 차원별 카피 + 자세히 모달 + LLM-ready coaching** - `result.tsx` 차원별 카드 (각도 정확도 / 팔다리 펴기 / 동작 안정성) + 자세히 모달 (점수 산출 설명, 동작·사용자 동적 카피, "심사평" 자연어) + 코칭 팁 자세히 모달 (LLM 동적 다중 원인 + 부상 경고 + coachNote). backend `assemble.build_dimension_explanation` + `coach_writer` JSON 출력 + Cerebras 시스템 프롬프트 갱신. **2026-06-07 close-out** (commits 1c0d20a T1+T2 / 62fdeed T9 backend / e968074 T8+T9 frontend). belle UX 검증 PASS — 모달 스크롤 정상 동작 + 심사평 톤 (평가+이유+결정 3박자) 적용.
- [x] **Phase 13: 보완 운동 추천 + LLM 분기 카피 + coaching detail 완성** - (a) 분석 결과의 실패 원인 후보·체형 정규화 finding 에 맞는 보완 운동·스트레칭 자동 매핑 (분석 → 행동 → 재구매, PERS-03), (b) 실 LLM 활성화 — Pod 갱신 + Cerebras `tip.detail2` 실 영상 검증, (c) `assemble.build_dimension_explanation` 에 `ipsfCode` 분기로 분기 1 (IPSF 등재 = "세계 심사 기준 + 180°") vs 분기 2 (학원 통용 = "정은지 선수 기준") 카피 분리, (d) `coach_writer` 시스템 프롬프트에 동작 분기 + IPSF 정의 각도 fixture 주입. 메모리 [`studio-term-3branch-system`] 정합. **belle 2026-06-07 결정: Phase 12.5 시뮬 한계 (폭스탑 학원 용어 어색 + angle 차원 180° 명시 X) 의 실 LLM 해결을 보완 운동 추천과 같은 phase 로 통합 — backend coach_writer 단일 phase 작업.** (completed 2026-06-16)
- [x] **Phase 14: 정은지 기준 모션 등록 (다각도 캡처 가이드)** - 비교 정확도 최대화 + 다각도 캡처 프로토콜 (completed 2026-06-15)
- [~] **Phase 15: ~~Mode 1·Mode 3 실영상 + 신뢰도 게이트 + TestFlight~~ — DISSOLVED (belle 2026-06-29)** - 실작업(점수 정확도/고수 위양성 제거)은 Phase 19/20/24로 흡수됨. 최종 실증/TestFlight는 개발 phase가 아니라 **마일스톤 완료 이벤트**(phase 정하든 안 하든 점수 정확해지면 수행). "고수 위양성 없음" 게이트는 **마일스톤 통과 기준**으로 유지(현재 20/24 책임). 번호·하위 참조·artifacts 전부 보존(renumber/삭제 안 함 — 후속 phase가 "Phase 15 실증 발견 출처"로 참조).
- [x] **Phase 16: Studio Terminology Foundation (3-branch + 5-Track v1 평행)** - 학원 용어 3분기 시스템 + IPSF 5트랙 채점 v1 scope 데이터/스펙/카피 박제. v1 평행 진행 (Phase 1~15 의존성 없음). MVP 가볍게 + 실증 단계 검증 후 확장 path. (completed 2026-06-02)
- [x] **Phase 17: Gemini Vision Integration — 4 영역 통합** - Gemini Vision multimodal 을 영역 A(reference 자동 등록)/B(코칭 멘트)/C(finding 인식)/D(keypoint 보강) 4개에 도입 + Phoenix/Promptfoo eval + 객관성 guardrail. 7 plan 코드+배포+v5 e2e 검증. (completed 2026-06-12, roadmap reconciled 2026-06-17)
- [x] **Phase 18: Expert deliberate-fault reference eval set** - 정은지 '일부러-실수' reference 영상을 영구 regression/eval 세트로. **(completed 2026-06-20, verdict-level closed)** **2026-06-19 baseline 박제 완료(pod-free)**: `backend/evals/phase18/`(pairs.yaml 6 페어 + 비전-파생 fault 라벨 D-05 + 확정 serial baseline 스냅샷 + assert_baseline.py self-check PASS) + `.planning/phases/18-.../18-EVAL-SET.md`. EVAL baseline = power-spin 72/100·peter-pan 79/100·elbow-twist 59/100·pdshape 58/100 변별 4/4, kip-up 100/100 위양성(known)·climb not_pole(known). **2026-06-20 live sweep ↔ baseline 대조 완료(Pod 2yz9zre7b4d2sp/5d67d94)**: Mode1 verdict 6/6 baseline 일치(변별 4 + kip-up 위양성 + climb 게이트), fault 점수 +0~2 drift(Gemini 비결정성=Phase 20 동기, 회귀 아님). evidence=`.planning/phases/18-.../18-LIVE-DRIFT-EVIDENCE.md`. verdict-level closed. **잔여 2건 → Phase 20 으로 이관(없어진 게 아님)**: (1) sensitivity 셋(미보유+above-cutoff) = Phase 20 20-04 SEVERITY_CAP 도출 입력(필수 선행), (2) exact-score drift 0 = Phase 20 결정성(temp 0 + 캐싱) 작업 후 재평가. (Phase 15 의존)
- [x] **Phase 19: 분석 점수 신뢰도 재설계 (vision-hybrid 채점)** - 실증에서 드러난 점수 위양성(정은지 실패영상 Mode1 94점/89%) 근본 수정 — 이중 단순평균 집계 → 감점식 IPSF 정합 + 비전-추론 하이브리드(영상+RTMW 수치 → 품질/결함 판단)를 채점 루프에 투입 + 표시값 정합·라벨·골격 좌표 버그 + Mode3 미보유동작 게이트. 절대원칙: 일반화(어떤 영상이든 정확), 보유셋 overfit 금지. (Phase 15 실증 발견 + Phase 18 eval = 검증 일부) (completed 2026-06-18)
- [x] **Phase 20: v2 비전 점수 (Gemini 시각 거부권)** — **CLOSED 2026-06-29 (대상 3 충족)**: (1) kip-up 위양성 = Phase 24-A 에서 해결(99→88, vision-측정 split 감점). (2) 상단 변별/결정성 = 캐시키 충돌 결정성 버그 fix(90d038f); Gemini 비결정 잔존은 [[phase18-live-drift-verdict-stable]] 수용범위. (3) Mode3 미보유 게이트+점수근거 = [[p2-mode3-disclosure-already-done]](Phase19/20-03). 잔여 minor=Phase 24 와 공유(calibration). 원본 scope ▸ Phase 19 v1(감점식)이 남긴 점수 위양성을 Gemini 시각 점수로 해소. belle 스펙 게이트 = 같은 정은지 95~100 / 잘못된 동작 ≤50 / Gemini 시각 점수. Phase 18 EVAL baseline = known-answer gate. 대상 3: (1) kip-up 위양성 100/100 — 비-각도형 실패를 DTW가 흡수하는 angle 맹점에 Gemini 시각 거부권, (2) 상단 변별(within-20°=일률 100) + Gemini 인식기 결정성(temp 0 + reference profile 캐싱), (3) Mode3 미보유동작 유효성 게이트(reference-free라 not_pole 미적용) + 점수근거 화면 표시. climb not_pole = 별도 ref-quality 트랙(코드 아님). 구현/eval은 Pod 필요. (Phase 18·19 의존)
- [ ] **Phase 22: 자체 비전 모델 파인튜닝 (오픈 모델 전환)** - Gemini(닫힌 API라 가중치 파인튜닝 불가) 대신 오픈 비전 모델로 전환해 공개 폴 영상 라벨 데이터로 **실제 가중치 학습**. Phase 20/#4(b)(c)(d)에서 꾸준히 모은 라벨 데이터(정타/fault 버킷 · 미보유 동작 · reference 확장)가 학습셋이 됨. 모델 추상화(PoseEngine/recognizer 인터페이스, [[rtmw-free-stack-pivot]]) 위에서 "꾸준히 쌓다가 됐다 싶을 때 갈아끼기". (Phase 21 이후, belle 2026-06-20 결정)
- [x] **Phase 24: 투명 감점-합산 채점 엔진 (severity 밴드 → 측정편차×명시규칙 감점)** — **CLOSED 2026-06-29 (close-out A)**: 감점 엔진 production 첫 검증(각도형 4페어 robust 변별) + **kip-up 위양성 해결**(99→88, split_angle −12 source=vision, 5/5 페어 변별) + 캐시키 충돌(결정성) 버그 fix. 3-단 체인: full-video vision 전환(044ee5e)+at_seconds=None(eb7d4ad)+캐시키 분리(90d038f)+vision-측정 split 편차 주입(f74011f, belle 결정 A). 잔여 minor(후속, pod 필요): power-spin success=91 fallback calibration(95~100 스펙) / kip-up 마진(88, 단일 criterion) 도메인 검토. 박제: memory `kipup-fp-RESOLVED-phase24A`. ▸ 원본 scope: Phase 20 의 `vision_veto.SEVERITY_CAP`+`apply_downward_cap`(severity→고정천장 밴드) 를 **점수 = baseline(100) − Σ(criterion별 측정편차×명시규칙 감점) 엔진**으로 교체. belle 2026-06-24 채점 철학 결정타([[scoring-must-be-transparent-deduction-tally]]): 영상마다 자의적 밴드(major=50)=사람 판단 주입=AI 존재이유 무효 → 동일 규칙 + 실측 편차 + 보고서가 "−X −Y −Z = 점수" 내역 노출. Gemini 강등 = 점수 X, 측정대상/결함 종류만 짚기. 감점 규칙 = `dimensions.py` 기하 tolerance 확장(전 영상 동일 slope), 구조 = criterion 묶음(상관 관절 1회) + criterion별 IPSF severity 상한(최종점수 밴드 아님)·합산. baseline = 사용자 선택 코치=100 / IPSF 공식동작이면 IPSF 기준(D-07 3분기 일반화). 토대 = Phase 23 정량화(각도편차·몸-상대 칸/층) + dimensions.py IPSF. 케이스별 기대점수 manifest(moderate≤75·major=50, 23-03 흡수분 포함) curve-fit 제거. Phase 20 working parts(`gemini_vision_scorer` 결함 짚기·Mode3 게이트·recall)는 보존·재사용. 신규 eval 게이트 = 추적성 + 단조성 + 결정성 + 일반화(미보유+above-cutoff). (Phase 19·20·23 의존, Pod 필요. Phase 22 파인튜닝보다 먼저. belle 2026-06-24 결정.)

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

**Plans**: 3 plans (Wave 1~3 MVP vertical slices)
Plans:

- [x] 03-01-PLAN.md — Wave 1: thin E2E + 3-way BodyProfile 계약 lockstep (TS↔Python↔contract.md) + bodyProfile.ts hook + loading.tsx snapshot + pipeline coach seam (D-04) + D-05 weightKg grep gate + Wave 0 backend 테스트
- [x] 03-02-PLAN.md — Wave 2: BodyProfileForm (5필드 RN primitive + a11y + 토큰) + profile.tsx BodyProfileCard 상시 편집 진입점 (D-01/D-02/D-03)
- [x] 03-03-PLAN.md — Wave 3: BodyProfilePromptModal dismissible 첫분석 권유 + analyze.tsx 게이트 + once-flag (D-01/D-06) + result.tsx BodyProfile 표기 (D-04)

**UI hint**: yes

### Phase 4: Camera Angle AI (single-view 가상 다각도) + occlusion confidence 게이트

> 2026-06-13 재정의 — belle pivot ([[camera-angle-ai-single-view-synth]] + Spike 001~005 wrap-up). 구 scope "정면+측면 2시점 직접 업로드 UX" 폐기 (구 SC #1/#2 폐기). 상세 박제 = `04-CONTEXT.md` D-01~D-32 + `.planning/spikes/WRAP-UP-SUMMARY.md` (Decoupling 4-stage).

**Goal**: 사용자는 1 영상만 업로드하고, 백엔드가 confidence 미달 구간/가려진 관절만 AI 가상 시점으로 핀포인트 보완(재추론·병합)하며, 가림 프레임은 confidence 게이트로 단정하지 않는다
**Mode:** mvp
**Depends on**: Phase 1, Phase 2 (폴 축·체형 피팅 위에 confidence 적용), Phase 17 (Gemini Vision scene_finder 트리거 재사용)
**Requirements**: POSE-03
**Scope 제약**: 단일 영상 입력 고정 (다중 시점 직접 업로드 영구 제거). 사선/뒤 시점 합성·스피닝 폴·Omni 영상 생성 본검증은 v2/후속 (Stage 4는 인터페이스 stub만).
**Success Criteria** (what must be TRUE):

  1. 사용자 업로드 UX는 1영상 그대로 유지된다 (다중 시점 업로드 UI 미존재)
  2. 1차 RTMW 분석에서 confidence 미달 phase/가려진 관절이 식별되고, 해당 구간만 조건부 AI 보완이 트리거된다 (영상 전체 합성 금지 — 비용 효율)
  3. 키포인트 confidence가 임계값 미만인 프레임은 "추정" 표기 + 후속 단정 게이트
  4. occlusion 경고가 결과 화면에 표시되고 (예: "이 구간은 가림으로 추정") 사용자가 인지할 수 있다
  5. AI 보완 실패/시간초과 시 1차 RTMW 결과로 graceful degrade 하고 결과 화면에 정확도 제한이 표기된다
  6. 사용자가 결과 화면 3D 뷰어로 동작을 360° 회전하며 확인할 수 있다 (Stage 3 — react-three-fiber, Spike 005)
  7. 정은지 reference 5영상이 신규 파이프라인으로 자동 재처리된다 (mode1 비교 양쪽 동일 파이프라인)

**Plans**: 6 plans (Wave 0~5) — 04-00 테스트 인프라 / 04-01 Stage1+2 Gemini Vision backend (SynthesisResult + joints3d 3-way lockstep + non-scoring 하드월) / 04-02 Stage3 3D 뷰어 (R3F + Canvas fallback) / 04-03 Stage3' mesh render (Wave 3a smoke + 3b RunPod accuracy gate) / 04-04 Stage4 plug-in stub / 04-05 정은지 재처리 (behavioral guard + versioned/atomic write). 외부 리뷰 1차: 04-DIRECT-REVIEW.md (Codex, revise-before-execution) → 04-DIRECT-REVIEW-RESPONSE.md (5 blocker 반영 완료, 2차 리뷰 대기).
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

**Plans**: 3 plans (Plan 06-01 = algorithm + contract lockstep, Plan 06-02 = pipeline wiring + Firestore + smoke, Plan 06-03 = 정은지 reference 백필) — 2026-06-08 reviews revision (C1/C2/C3/C5/C6/C7/C8/C9/C12/C14/C15 fix) + **round-2 (R1/R2/R3/R4/R5/R6/R7/R8/R9/R10 fix)**; Plan 06-01 = 5 task (Task 1 6 fixture R5 신규), Plan 06-02 = 5 task (Task 0 C2+R1 retro Phase 5 patch + Task 1 R3 단일 helper / R4 non-null student_profile / R8 extra_warnings / R2 source_pose wiring), Plan 06-03 = 7 task (Task 4 dry-run + R7 ADC-free 검증 + Task 4.5 revert R2 두 필드 + Task 5 수동 + Task 6 deferred sweep)

Plans:
**Wave 1**

- [x] 06-01-PLAN.md — body_normalizer.py (Kinematic Tree Reprojection [C1 fix: target-profile-based L_ref + R10 source_profile 회귀 방지 test] + IPSF deficit [C14 fix: pose_reliability_low rename, IPSF divergence note; R9 fix: 5 IPSF + Sunity pose_reliability_low — poor_transitions deferred] + confidence [R5 fix: spatial_dispersion_penalty 산식 자연화 + R6 fix: to_coco17_array 4채널 보존] + **BodyComparisonSourcePose dataclass R2 신규**) + ScaleProfile/BodyComparisonReport (3 ComparisonType + usedReferenceFallback boolean + **extra_warnings 파라미터 R8 fix**) + 3-way contract lockstep (**docs/contract.md §8 + §8.2 R2**) + 6 fixture (R5 신규 fixture_high_dispersion_arms_sprawled 포함) + 4 algorithm test 파일 + drift lockstep test (Wave 1, PERS-01, 5 task, reviews-revised + round-2) — **complete 2026-06-08, 52/52 tests PASS**

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06-02-PLAN.md — Task 0 (C2 + **R1 fix** retro Phase 5 patch): TechniqueProfile.motion_id (**dataclass 맨 끝 위치 — R1 fix**, default-after-non-default 회피) + Gemini populate (keyword arg) + Task 1: pipeline _process wiring (**R3 fix: 단일 `_extract_video_analysis_inputs` helper** — 기존 `_angles_and_video_path_from_video` 폐기, RTMW 1회 실행 보장 + **R4 fix: student_profile non-null** + **R2 wiring: bodyComparisonSourcePose fetch + `_extract_target_torso_px` + source_keypoints 전달** + **R8 wiring: extra_warnings injection, dataclasses.replace 폐기** + _match_reference_by_motion_id exact-match [C2 fix]) + Task 2: firestore_admin.complete_analysis 확장 + _validate_flat_dict_no_nested_array (W5) + Task 3: _dataclass_to_camel_case_dict 4-case 명세 [C8 fix] + frontend userAnalyses normalize + Task 4: SAM build smoke + artifact 존재 검증 [C15 fix] + C9 + **R2 신규 canary** test (mode1 missing ref_profile / ref_source_pose 둘 다 → warnings + confidence + scale_profile 검증) + C14 grep gate (bad_angle 부재) (Wave 2, PERS-01, 5 task, reviews-revised + round-2) — **complete 2026-06-08, 55/55 new tests PASS, phase06 suite 107/107**

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 06-03-PLAN.md — Task 1: firestore_admin.**`update_reference_body_data` helper (R2 fix: 두 필드 atomic merge — bodyNormalizationProfile + bodyComparisonSourcePose, 구 `update_reference_body_profile` 단일 필드 helper 폐기)** + Task 2: extract_reference_body_profiles.py (Pod GPU 직접 실행 + **R2 fix: BodyComparisonSourcePose 산출 — 대표 hold frame 17 keypoint × 4채널 flat 68 float values + torsoPx** + --dry-run [C5 fix]) + Task 3: seed-reference-body-profile.mjs (Firebase Admin SDK ADC + 두 필드 atomic merge + --dry-run [C5 fix] + **R7 fix: 명시적 ordering — parse → validate → if dry-run: stdout + exit (Firebase init 미접촉) → real-run: init + commit**) + Task 4 (C5 + **R7 fix**): dry-run 통합 검증 unit test (**ADC 미설정 환경 + Firebase 호출 0 검증**) + Task 4.5 (C12 + R2): revert-reference-body-profile.mjs (**두 필드 모두 FieldValue.delete**) + Task 5: 실행 checkpoint (C7 filler 제거, **두 필드 모두 검증 항목** 명시, 구체 expected output) + Task 6 (C6 + R9 deferred): belle Pod sweep 사양 박제 (R9 정합 카피 — 5 IPSF + Sunity pose_reliability_low) (Wave 3, PERS-01, 7 task, reviews-revised + round-2)

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

**Plans**: 2 plans

  - [x] 07-01-PLAN.md — Wave 1: schema 3-way lockstep (BodyComparisonFinding +4 / BodyComparisonReport +2+1 WR-03) + copy_templates.py 신설 모듈 (33 canned CR-02 + 3 mode prefix + 9 grep gate FORBIDDEN + render_finding_copy CR-01 fallback) + Wave 0 test 인프라 (phase07/ 디렉토리 + 6 fixture JSON + factory loader) + drift defense test ✅ 완료 2026-06-08 (3 commits: 3e1fbf7 / fcb4025 / d4d8af4, 226 PASS)
  - [x] 07-02-PLAN.md — Wave 2: classify_findings pure function 본체 (D-07-A1 + D-07-A2 + Decision 1 mode3_first fallback + CR-01 + WR-03) + compare_body_profiles wiring 1줄 + 4 신설 kwarg 주입 (findings/dnoc/rec_focus/recommended_focus_fallback) + integration test 4종 + _dataclass_to_camel_case_dict 자동 변환 test 2 + frontend userAnalyses.normalize() WR-02 retract B1 null-guard ✅ 완료 2026-06-08 (3 commits: 2aedb84 / 4851a43 / 8559c6f, 108 phase07 PASS + 136 phase06 PASS 회귀 0 + tsc clean)

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

**Plans**: 3 plans

  - [x] 08-00-PLAN.md — Wave 0: PoleLine2D + PoleAxisMeasurement + CoordinateSpace + ContactPrimitiveKind contract + median_torso_length helper + Wave 0 test 인프라 + 25-timestamp preflight gate spec (completed 2026-06-09)
  - [x] 08-01-PLAN.md — Wave 1: 3-way contract lockstep (TS 7 type + Python placeholder + docs/contract.md §9) + dimensions.stability_wobble raw helper 분리 (drift defense source) + backend/judging_data/contact_points.yaml 신설 (5 motion + default) + 6 programmatic fixture builders (completed 2026-06-09)
  - [x] 08-02-PLAN.md — Wave 2: force_signals.py 본체 신설 (5 dataclass + 5 type alias + 5 public 함수 + 25 private helper) + models.py import 활성화 (3-way lockstep 완성) + Layer 1 motion-agnostic 휴리스틱 + 4 metric 산출 함수 + compute_force_signals umbrella + _layer1_confidence_from_preflight + _min_confidence ceiling helper (completed 2026-06-09)
  - [x] 08-03-PLAN.md — Wave 3: Layer 2 Gemini 활성 (TechniqueProfile.key_moments reuse, R6) + FORCE_SIGNALS_LAYER2_ENABLED env separation (R7) + GEMINI_MODEL env wiring (R8 carryover) + _preflight_label_gate_passed env helper (Cycle 2 NEW HIGH #1) + Layer 2 except ceiling (Cycle 2 NEW HIGH #2) + Firestore scoped validator `_validate_force_signals_report` (Cycle 2 NEW HIGH #3, firestore-nested-array-flat 보존) + _VideoAnalysisInputs.pole_axis_measurement (R10) + pipeline _process wiring + userAnalyses.normalize null-guard + 23 신설 test + 11 pipeline 통합 test. **In-line sweep-driven fix (4건): A sweep_temp/ prefix / B HoughPoleDetector.detect_with_line / B' compute_axis_deviation pole_aligned 3D fallback / C _map_moments_to_5phase setup/hold/release 단독 boundary.** **Phase 8.5 (axis-metric-redesign) 신설 결정** — 정은지 5/5 axis severity='high' 도메인 정합성 문제 발견. (completed 2026-06-09)

### Phase 08.1: axis-metric-redesign

**Goal**: Phase 8 의 axis distance metric 이 도메인 정합성을 위반 (정은지 5/5 영상 모든 phase severity='high' 출력) — 좌표계 origin 미정의 + threshold 단위 mismatch. IPSF Code of Points 의 axis 채점 항목 + 폴스포츠 도메인 "축 이탈" 정의 research 위에서 axis metric 을 재설계. 정은지 baseline 이 `severity='low'` 로 출력되도록 도메인 정합 metric + threshold calibration.
**Mode:** mvp
**Depends on:** Phase 8
**Requirements**: FORCE-01 (Phase 8 와 공유 — axis 차원 의미 부여)
**Single evidence source**: `.planning/phases/08-jerk-jitter/PHASE8-INHERITED-ISSUES.md` (정은지 5영상 sweep raw distance/severity/tilt 분포 + root cause 분석 + 의사결정 공간 α-1~4 / β-1~3 + 외부 AI reviewer 5 핵심 질문)
**Scope 제약**:

  - tilt 데이터 (shoulder/hip, rotation-only) 는 Phase 8 본체에서 보존 — Phase 9 평행 진입 시 사용 가능, 본 phase 가 손대지 않음
  - schema (`ForceSignalsReport` + `coordinate_space` 필드 enum) 보존 — 새 metric 도 본 contract 내 박제
  - [[analysis-objectivity-no-human-scores]] 정합 — 정은지/belle 점수 라벨링 ground truth 금지. threshold 수치 calibration 만 OK (정은지 sweep 분포 + IPSF deduction 카테고리 매핑)

**Success Criteria** (what must be TRUE):

  1. 정은지 5/5 reference 영상 axis severity 가 `low` 으로 출력 (현재 5/5 `high` → fix 후 5/5 `low`)
  2. 좌표계 origin 정의 또는 metric 자체 변경으로 axis distance 가 카메라 거리/줌/dancer 화면 위치에 invariant
  3. IPSF Code of Points 의 axis 채점 항목 (deduction category) 과 metric severity 가 mapping 박제
  4. threshold 값 + 도출 근거 가 `.planning/phases/08.1-axis-metric-redesign/` 의 plan 산출물 에 기록
  5. Phase 8.1 종료 시 sweep 재실행 + 정은지 분포 확인 + 분포 변경 evidence 박제

**Plans:** 2/6 plans executed

Plans:

- [x] 08.1-00-PLAN.md — Wave 0: Schema migration — AxisDeviationMetric distance hard break (5 필드 제거, D-01) + 3-way lockstep atomic (TS + Python + docs §9.3) + Firestore validator backwards-compat + 신설 phase08_1 test infra. **2026-06-09 close-out** — 2 commits (6a294d5 / 1cb3e6e). 372 PASS + 1 skipped. compute_axis_deviation = transitional stub (severity='low' default + warning 'phase_8_1_wave_0_transitional'). C-B1 fix (axis_metric_transitional top-level warning) + C-H1 fix (Wave 0 단독 production 진입 금지) + C-MH1 박제 (naming caveat docstring) 모두 박제.
- [x] 08.1-01-PLAN.md — Wave 1: Tilt metric 재설계 — compute_axis_deviation tilt-only 재작성 + `_normalize_angle_undirected` (modulo 180°) + AXIS_TILT_THRESHOLDS_DEG → tilt_thresholds.yaml schema_v2 lazy load + calibrate_tilt_thresholds.py (source 분기 firestore/repo-artifact/wave2-explicit + null tilt preflight hard gate) + **정은지 5영상 P100 + margin 5° calibration** (P90 폐기) + IPSF tolerance_deg=20° / major_fault_deg=40° floor + boundary-low strict severity (`>` + 1e-9 eps, unsigned [0, 90]). **2026-06-09 close-out** — 3 commits (30fd7d2 / e08be9c / 80c9a6b). 413 PASS + 1 skipped. 정은지 25 sample P100+margin → shoulder cutoff 63.28°/94.92°, hip 54.62°/81.93°. Codex iteration 1-5 fix (C-H2 + C-H3 + C-M1 + C-MH1) 모두 단일 release 박제 (Wave 0+1 한 boundary).
- [x] 08.1-02-PLAN.md — Wave 2: Pipeline rewire + 정은지 5영상 재sweep + SWEEP-EVIDENCE.md — pipeline caller-side audit + mock E2E test + Pod 재배포 manual checkpoint + ROADMAP SC #1-5 evidence 박제

**Future plan (deferred, Codex C-MH1 정합)**: `AxisDeviationMetric` → `BodyLineTiltMetric` rename — distance 차원 제거 후 의미적 정합. 본 phase 미적용 (docstring caveat 만), 별도 plan 으로 분리 (TS interface + Python dataclass + docs §9.3 + tests + frontend 영향).

### Phase 9: ForceDirectionPattern + 실패 원인 후보 3개

**Goal**: 기초 신호를 종합해 `ForceDirectionPattern`(pull/push/brace/rotate/release)을 추론하고, 동작 실패 원인 후보 3개를 카드 형태로 제시한다 (단정 금지, 모든 항목 "가능성"으로 표기)
**Mode:** mvp
**Depends on**: Phase 8 (Phase 8.1 종료 기다리지 않고 평행 진입 가능 — Phase 8.1 D-05 iteration 2 정합)
**Requirements**: FORCE-01, FEED-02
**Axis raw signal only guard (Codex C-M4 정합, 2026-06-09)**: Phase 9 가 `forceSignalsReport.axisMetrics[*].severity` 직접 trust 금지. raw `shoulder_tilt` + `hip_tilt` + `confidence` + `warnings` 만 사용. severity 는 warnings 가 `axis_metric_transitional` 또는 `tilt_unavailable` 또는 `tilt_thresholds_fallback` 포함 시 무시. Phase 8.1 SWEEP-EVIDENCE §11 sensitivity 통과 후 severity 사용 OK.
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

**Plans**: 4 plans (4 waves)

  - [x] 10-01-PLAN.md — Wave 0: SafetyFlag 계약 3중 미러(analysis.ts↔models.py↔contract.md) + safety_flags.py 스캐폴드(frozen dataclass+enum guard+compute stub) + warnAmberBg 토큰 + phase10 RED 테스트/fixture (SAFE-01)
  - [x] 10-02-PLAN.md — Wave 1: Slice 1 — D-02 AND-게이트 + D-04 트렁크 과신전(reference-anchored) + _process 주입 + _validate_safety_flags + 앰버 InjuryRiskSection UI(4종 카피 맵, 비면 omit). 정은지 위양성 0 헤드라인 게이트 (SC2/SC4)
  - [x] 10-03-PLAN.md — Wave 2: Slice 2 — D-05 관절 과신전 외적 부호 방향 판별(무릎>5°/팔꿈치>10° [CITED], 시상면). belle Mode-3 우선. 자동 렌더 (SAFE-01)
  - [x] 10-04-PLAN.md — Wave 3: Slice 3+4 — D-03 비대칭(reference-anchored, kismam 재사용) + D-06 레벨 대비 무리(Mode 1 전용, spoof fail-safe). 4종 완성 (SC1/SC3)

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
  5. Gemini hook-writer LLM 키 미설정 또는 hook 호출 실패 시에도 canned fallback 카피로 분석이 완료된다 [2026-06-16 review correction: hook fallback 은 Gemini api_key_loader seam 기반 — Cerebras 아님. Cerebras coach fallback 은 Phase 13/17 범위]

**Plans**: 3 plans (Wave 0~2 MVP vertical slices). **LOCKED design fork** [2026-06-16 review correction]: 별도 text-only `GeminiCoachHookWriter` 1회 호출 — 두 리포트 hook 을 한 호출에 bundle, 두 리포트 조립 완료 후 생성. 기존 Vision `GeminiCoachWriter.write()` 미변경 (영상 의존이라 재사용 시 Vision 독립 lock / Phase 11·17 경계 위반). model=Gemini, _build_coach_context 철학 + _enforce_no_reject_patterns 재사용 (D-03 addendum).Plans:
**Wave 1**

- [x] 11-00-PLAN.md — Wave 0: CoachCommentHook 3-way lockstep (TS↔models.py↔contract.md) + coach_hook.py 데이터 구조 + phase11 test scaffold (translation-only / fallback / nested-array RED) (COACH-01)
- [x] 11-01-PLAN.md — Wave 1: 별도 text-only GeminiCoachHookWriter (coach_hook_writer.py, CoachHookBundle 스키마, 두 리포트 1회 bundle 호출) + degree/% 포함 _enforce_no_reject_patterns reject-and-fallback + api_key_loader-seam canned fallback + force_pattern_inference 생성 후·complete_analysis 전 부착 + ForcePatternInference scoped validator 확장 (landmine) (COACH-01/FEED-03)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 11-02-PLAN.md — Wave 2: result.tsx "강사에게 확인할 점" 섹션(openQuestionsForCoach만) + 포지셔닝 카피(상단 1줄+코치 헤더) + Mode 1 기준모션 "하나의 참고일 뿐" + userAnalyses null-guard + belle 시각 checkpoint (FEED-03)

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

**Plans**: 3 plans

- [ ] 12-01-PLAN.md — Wave 0: kismam.assess() wiring fix + KeypointReport 3-way schema lockstep (single atomic commit per D-09-U1 mirror)
- [ ] 12-02-PLAN.md — Wave 1: UI 신영역 3 component 신설 (KeypointOverlay + ForcePatternCard + ForcePatternDetailModal) + result.tsx 6 영역 layout 재정비
- [ ] 12-03-PLAN.md — Wave 2: Frame 동기화 (useEvent timeUpdate) + delta 강조 + confidence/occlusion 표기 + 토글 + iOS belle UAT

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

**Plans**: 3 plans (D-05 분리 — Plan A = criteria 1-4 GPU 불필요, Plan B = criteria 5-8 분기 + 실 Cerebras, Plan C = 섹션형 듀얼 coach 보고서)
Plans:

**Wave 1**

- [x] 13-A-corrective-exercises-PLAN.md — Wave 1: 보완운동 라이브러리 fixture + 순수 map_exercises(findings + painAreas + motion_id) + recommendedExercises 3-way 계약 + result.tsx 보완운동 섹션 + 다른 운동 보기 모달 (PERS-03, D-03/D-04/D-05, criteria 1-4, autonomous). **+ 갭클로저(`glute_hip_unstable` defect — pelvis_drop 6번째 force 신호 커버 + 회귀 테스트).**

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 13-B-llm-branch-copy-PLAN.md — Wave 2 **완료 2026-06-16**: motion_ipsf_map 11-motion curated join(belle 5→11 확장 + unknown→branch2 안전 기본) + registered_move_angles {schemaVersion, angles:{}} + assemble copyBranch 분기 + coach_writer 프롬프트 각도 주입 + pipeline wiring. **criteria 5-8 풀 E2E 검증**: Pod(ref-foxtop) upload→Firestore, 양쪽 coach status=done, 분기2 "정은지 선수 기준" + 금지문구 0, detail2 실 LLM 채움. 파일럿 coach = **Gemini**(belle 선택, Cerebras fallback 유지). 인프라: 신규 Pod 부트스트랩 + Firestore analyses 인덱스 면제 7개 신규 적용. (studio-term-3branch, criteria 5-8)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 13-C-section-dual-coach-PLAN.md — Wave 3 **완료 2026-06-16**: **섹션형 듀얼 coach 보고서** — 두 writer 동시 호출(`_call_coach_writer_with_retry` 재시도 1회) + `assemble.assemble_dual_coach_sections` 섹션 출처 태깅 조립 + 계층형 cross-fill 폴백(빈 섹션 0) + 섹션 출처 audit 로깅 + 자세히 모달 4섹션 세로 스택 렌더. 섹션: 원인(왜)=Gemini / 교정 처방(무엇)=Cerebras / 부상위험=Cerebras / 강사확인=Gemini. detail2 형상 불변(source 필드 미추가, 벤더명 비노출). UI 라벨 = 기능 라벨만. phase13 88 passed + tsc clean. **빌드 = 단위/타입 게이트까지 — 실 dual-LLM E2E + 둘 중 하나 drop 여부 = Phase 15 검증 기준.** (coaching detail 완성 = 본 phase 도메인이라 phase 19 신설 X, 13-C 로 처리)

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

**Plans**: 3 plans (CONTEXT D-01~D-05 정합 — 기존 11개 백필, 신규 촬영 0)

  - [x] 14-01-PLAN.md — Wave-0 foundation: Firestore 필드 audit(A2) + 백필 테스트 하니스(D-01 parity / SC#4 graceful / D-02 verdict) + contract 3-way lockstep(techniqueProfile/forceDirectionPattern/captureViews)
  - [x] 14-02-PLAN.md — 백필 compute(동일 _process 함수, RTMW 1회 재추론) + ADD-only merge seeder + firestore_admin helper + 다각도 캡처 가이드 문서(SC#3)
  - [x] 14-03-PLAN.md — Pod 백필 실행(11개 전체) + dry-run/real-run/verify-read + belle 시각 검수 체크포인트 (active flip 없음)

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

> **DISSOLVED (belle 2026-06-29)**: 활성 phase 아님. 점수 정확도/위양성 작업은 Phase 19/20/24로 흡수, 실증/TestFlight는 마일스톤 완료 이벤트. "고수 위양성 없음"은 마일스톤 통과 기준으로 유지(20/24). 아래 내용·하위 참조는 역사/맥락 보존용(renumber·삭제 안 함).

**Goal**: 사용자가 Mode 1(정은지 기준 비교)과 Mode 3(자기 영상 발전)을 실영상으로 완주하고, 고수 영상에서 위양성 없이 신뢰할 만한 점수를 받고, TestFlight 게스트 모드에서 회원가입 없이 실기기로 완주한다
**Mode:** mvp
**Depends on**: Phase 11, Phase 12, Phase 13, Phase 14 (리포트·표시·보완운동·기준모션 모두 준비됨)
**Requirements**: MODE-01, MODE-02, SCORE-04, DELIV-01
**Scope 제약**: 검증 대상은 초기 3~5개 동작군. 범위 밖 false-reject 허용.
**Success Criteria** (what must be TRUE):

  1. Mode 1: 사용자가 정은지 기준 모션을 선택해 본인 영상을 올리면 실분석 결과와 전문가 기준 점수가 표시된다 (referenceMotionId lockstep)
  2. Mode 3: 사용자가 본인 영상 2개를 올리면 차원 점수의 세션 간 델타가 "지난 분석보다 N점 발전" 형태로 표시된다 (현 계약 `build_mode3`/`result.tsx:192`; 관절 각도 델타 "무릎 신전 8°"는 후속 phase — 2026-06-17 belle 결정, 검증-only Phase 15 범위 밖)
  3. 신뢰도 게이트: 정은지(고수) 영상이 41점 같은 위양성 없이 자세 품질을 반영하는 점수로 산출된다
  4. 다양한 동작/앵글 영상 세트에서 분석이 크래시 없이 일관된 점수를 낸다
  5. TestFlight: 수강생이 익명 게스트로 진입해 회원가입 없이 Mode 1·Mode 3를 실기기에서 완주하고 결과 영상이 재생된다 (presigned URL 만료/Content-Type 이슈 없음, letterSpacing SIGABRT 회귀 없음)

**Plans**: TBD
**UI hint**: yes

### Phase 17: Gemini Vision Integration — 4 영역 통합

> **2026-06-12 close-out 완료 (commit 363b742).** 7 plan 전부 코드+배포+검증 박제. Wave 7-A~E (SAM deploy + Pod reactivate + body backfill + v5 mock e2e): status=done, overallScore 84, 영역 A 6/6 motion isActive=true, 영역 B Gemini gemini-3.1-pro-preview 정상 호출(fallback 없음), 영역 C E6 hard gate PASS, 영역 D opt-in skip. debug 5건 해소. **로드맵 reconcile 2026-06-17** — closeout 직후 Phase 4 Gemini Vision view-reasoning 스파이크(spike 003/002d/002b, commit ef0f6fa)로 전환하면서 체크박스 flip 누락분 정리.

**Goal**: Gemini Vision API (multimodal 영상 이해) 를 4 영역에 도입해서 분석 정확도 + 사용자 가치 본질 강화. 신규 reference 영상 추가 부담 해소 + RTMW 의 자세 인식 약점 보강.
**Depends on**: Phase 9 (ForceDirectionPattern finding 구조), Phase 11 (CoachCommentHook 데이터 구조), Phase 14 (정은지 기준 모션 등록 구조)
**Requirements**: VISION-01, VISION-02, VISION-03, VISION-04 (신규 도입 — REQUIREMENTS.md 박힘 박힘)
**Background**: belle 2026-06-12 결정 (`[[gemini-vision-active-use]]` 메모리). 신규 6 motion 의 NLF↔RTMW 호환 깨짐 finding (UAT 2026-06-12) 후속.
**Success Criteria** (what must be TRUE):

  1. **A. Reference 자동 등록**: 정은지 영상 업로드 → Gemini Vision 이 IPSF 명칭 매칭 + clipRange (prepStartS/execPeakS/landEndS) + checkpoint joint 자동 산출 → Firestore `reference/{motionId}` 박힘. 정성 검증 = 3 path cross-check (claude.ai + Gemini + RTMW) 와 일치.
  2. **B. 코칭 멘트 품질**: 분석 결과의 `tips[]` / `coach` 멘트가 RTMW 수치 + Gemini Vision 의 영상 장면 이해 결합 → 구체성 강화 ("팔꿈치가 더 펴져야" → "왼쪽 팔꿈치 hook 시 폴 접촉면 박힘 박힘 박힘 — 어깨 견갑 안정성 부족"). belle / 강사 1차 검수 통과.
  3. **C. Finding 장면 인식**: `forcePatternInference.findings[]` 가 Gemini Vision 의 장면 정보 (그립 종류 / 백벤드 정도 / occlusion / 카메라 angle) 입력으로 강화. `high_score_finding_gated` warning 감소.
  4. **D. 관절 추출 보강 (D-v1, B2 정합)**: RTMW 가 낮은 confidence (`uncertainty_proxy > 0.5`) 박힘 자세 (inverted / twist / 폐색) 의 keypoint user-visible 시각화 보강. `KeypointReport.confidence` 의 0.5 미만 비율 < 5% (현 신규 6 = 13-35%). **D-v2 deferred** (좌표계 계약 박은 후 후속 plan): 3D coco_array 주입 + DTW/KISMAM 점수 재계산.
  5. **비용/지연 budget (3차 R-W2 갱신, 2026-06-12)**: 1회 분석당 Gemini Vision API 비용 < $0.20 (belle "비용 신경X but 효율 잡기" 박힘). 분석 완료 latency 추가 **≤ p95 40s** (기존 "< 15s" → AI-SPEC E8 정합 완화 — [[feedback-analysis-first]] "분석 정확도 우선" 정합). C/B/D 4 영역 호출 합산 비동기 path 박힘 (`asyncio.gather`), Lambda pipeline 900s timeout 내.

**Plans**: 7 plans

  - [x] 17-01-PLAN.md — 공통 Gemini client + 4 영역 Pydantic schemas + 객관성 guardrail (G1)
  - [x] 17-02-PLAN.md — 영역 C Finding 인식 (Flash) + Pod _process wave 1 + G4 정은지 occlusion FP 가드
  - [x] 17-03-PLAN.md — 영역 D Keypoint 보강 (Pro, RTMW < 0.5 conf frame) + G5 좌표 환각 가드
  - [x] 17-04-PLAN.md — 영역 B 코칭 멘트 (Pro Vision) + Cerebras dual-track + 강사 보조 톤 schema 강제
  - [x] 17-05-PLAN.md — 영역 A Reference 자동 등록 (신규 Lambda + SAM + 분기 1/2/3 라우팅 + G3 화이트리스트 가드)
  - [x] 17-06-PLAN.md — Eval + Guardrail wiring (Phoenix self-host + Promptfoo + LLM judge + smart sampling + 30-example dataset)
  - [x] 17-07-PLAN.md — 신규 6 motion 재활성화 (RTMW engine swap + 영역 A endpoint 자동화 + belle 검수 — UAT 2026-06-12 F4 finding 해소)

**UI hint**: no

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
| 3. 자가입력 BodyProfileInput | 3/3 | Complete   | 2026-06-15 |
| 4. 다중 시점 촬영 + occlusion 게이트 | 6/6 | Complete   | 2026-06-14 |
| 5. Gemini 기술 인식기 (분류 한정) | 6/6 | Complete | 2026-06-05 (12차 sweep D-01 PASS) |
| 6. 체형 정규화 비교 엔진 | 3/3 | Complete   | 2026-06-08 |
| 7. 차이 분류 | 0/TBD | Not started | - |
| 8. 중심축·접촉점·jerk 분석 | 4/4 | Complete (axis-metric Phase 8.5 신설) | 2026-06-09 |
| 9. ForceDirectionPattern + 실패 후보 3개 | 2/2 | Complete   | 2026-06-10 |
| 10. 부상 위험 신호 플래그 | 4/4 | Complete   | 2026-06-30 |
| 11. CoachCommentHook + Gemini 번역 | 3/3 | Complete    | 2026-06-16 |
| 12. 실측 각도 + 키포인트 오버레이 | 0/TBD | Not started (v1 chain #5) | - |
| 12.5. UI Transparency (차원별 카피 + 강사 보조) | 1/1 | Complete | 2026-06-07 |
| 13. 보완 운동·스트레칭 추천 | 3/2 | Complete   | 2026-06-16 |
| 14. 정은지 기준 모션 등록 (다각도) | 3/3 | Complete    | 2026-06-15 |
| 15. Mode 1·Mode 3 + 신뢰도 게이트 + TestFlight | 4/5 | In Progress|  |
| 16. Studio Terminology Foundation (3-branch + 5-Track v1) | 1/1 | Complete   | 2026-06-02 |

### Phase 18: Expert deliberate-fault reference eval set (정은지 일부러-실수 영상 검증 테스트 세트) — 가칭

> **가칭 / 미상세 (belle 2026-06-16 결정).** 정은지가 제공한 '일부러 실수한' reference 영상을 활용한다. Phase 15(Mode 1·3 end-to-end)가 동작한 뒤 진입. 상세 scope·요건은 discuss/plan 단계에서 확정.
>
> **2026-06-19 baseline 박제 완료(pod-free).** eval fixture = `backend/evals/phase18/` (`dataset/pairs.yaml` 6 페어 + 비전-파생 fault 라벨[Phase 19 D-05] + `baseline/eval18_serial_baseline.json` 확정 serial 스냅샷 + `assert_baseline.py` self-check **PASS** + README). 정의/게이트/객관성 = `.planning/phases/18-.../18-EVAL-SET.md`. 러너는 `backend/scripts/sweep_phase15.py`(15-01) 재사용. 데이터 재업로드/재처리 0. **남은 일 = Pod 재개 후 live sweep ↔ baseline 정량 대조 + sensitivity 셋(미보유+above-cutoff) Deferred.**

**Goal:** 정은지가 제공한 '일부러 실수한' reference 영상을 영구 eval/검증 테스트 세트(regression fixture)로 만든다 — 각 실수 영상에 '어떤 fault를 시연하는지' 라벨(영상 입력이지 사람 점수 라벨 아님)을 달아, 분석기가 그 fault를 잡아내고 + 높은 점수를 주지 않는지(고수 위양성 역검증) 자동 assert 한다. 핵심 가치(점수 신뢰)와 Phase 15 '고수 위양성 없음' 게이트에 직결. 같은 자산은 나중에 in-app 대조 교육(정타↔실수)에도 재사용 가능.
**Requirements**: TBD (plan 단계에서 신규 EVAL-* 요건 확정)
**Depends on:** Phase 15 (Mode 1·3 실영상 + 신뢰도 게이트가 동작해야 fault 검증 의미)
**Plans:** 3/2 plans complete

**주의 (plan 시 박제):**

- 임계값 calibration 에 직접 쓰면 사람-라벨 ground-truth 경계 — 신중 ([[analysis-objectivity-no-human-scores]]). v1 은 "fault 가 잡히는지" 검증용으로 한정.
- Phase 14 의 seeder / snapshot / rollback 스크립트(14-REVIEW.md CR-01/CR-02 수정 반영) 재사용.

Plans:

- [x] baseline fixture 박제(pod-free, 2026-06-19) — `backend/evals/phase18/` + `18-EVAL-SET.md` + self-check PASS
- [x] live sweep ↔ baseline 정량 대조 (2026-06-20, Pod 2yz9zre7b4d2sp/5d67d94) — Mode1 verdict 6/6 일치, evidence `18-LIVE-DRIFT-EVIDENCE.md`
- [→] sensitivity 셋(미보유+above-cutoff) + exact-score 재평가 = Phase 20 으로 이관 (20-04 입력 / 결정성 후속)

---

### Phase 19: 분석 점수 신뢰도 재설계 (vision-hybrid 채점)

> **신규 (belle 2026-06-17 결정).** Phase 15 실증 중 belle 실기기 검증에서 점수 신뢰도 붕괴 발견 — 정은지 '실패' 영상이 Mode1 94점/89% "거의 다 왔어요". 3-갈래 심층조사로 근본원인 확정. 상세 근거: `.planning/phases/15-mode-1-mode-3-testflight/deferred-items.md`.

**Goal:** 점수가 실제 자세 품질을 반영하게 한다 — 어떤 영상이든(보유 정은지 셋에 국한 X) 정확. 구체: (1) 이중 단순평균 집계 → 감점식 IPSF 정합 집계(결함이 다수 정상 관절에 희석되지 않게), (2) 비전-추론 하이브리드 — RTMW 정량추출 + Gemini(3.1-pro now / Omni 추후) 영상+수치 추론으로 품질·결함·인과 판단을 채점 루프에 투입(기하학은 측정가능 IPSF 기준에만), (3) 표시 각도값을 점수 산출값과 정합(비정렬 nanmean / matched-window vs full-clip 비대칭 제거) + 어깨 '안정성' 라벨 수정 + 안정성을 종합점수 인플레에서 분리, (4) Mode3 미보유동작 유효성 게이트 + 점수근거 화면 표시(동작분류 분기 IPSF/정은지/미보유), (5) 3D 골격 실기기 미표시 버그(joints3d RTMW 픽셀좌표 → 골반중심·몸통길이 정규화), (6) 촬영 팁(전문가 시작점 정합) UX + 운동명칭 직관화.
**Requirements**: SCORE-06, SCORE-07, TRUST-01, TRUST-02, TRUST-03, TRUST-04, TRUST-05 (신설 2026-06-18 — v1 감점식 + 확정 버그 3건 + Mode3 게이트 + v2 hook 자리. v2 비전 거부권 본체는 deferred)
**Depends on:** Phase 15 (실증 발견의 출처), Phase 18 (deliberate-fault eval set = 일반화 검증 자산)

**절대원칙 (박제):**

- 일반화 우선 — 정은지 데이터는 기준으로 쓰되 결론은 어떤 영상이든 정확. 보유 13영상 overfit/curve-fit/teaching-to-test 금지 ([[scoring-redesign-must-generalize-no-overfit]]).
- 임계값을 보유 sweep 으로 재calibrate 금지 ([[calibration-source-hard-gate]]). 검증은 미보유/above-cutoff 케이스 포함 ([[sensitivity-gate-not-just-elite-low]]).
- 사람 점수 라벨 ground-truth 금지 ([[analysis-objectivity-no-human-scores]]). IPSF = 감점식 baseline ([[judging-baseline-ipsf-code-of-points]]).

**Plans:** 4/4 plans complete

Plans:

- [x] 19-01-PLAN.md — Wave 0 RED 테스트 스텁 (SCORE-06/07 + TRUST-01/02/03/05 케이스 + D-05 6 앵커 GPU-skip)
- [x] 19-02-PLAN.md — **완료 2026-06-18**: 감점식 집계 코어 — kismam.overall_score 가중평균→IPSF 누적감점(_PENALTY_PER_DEG=1.2 [ASSUMED], 단일 major fault 지배) + dimensions.line_score micro-bent <160° 요소무효 0점 [CITED] + overall_from_dimensions min-of-core(stability 종합 분리) + 어깨 COACHING_FOCUS '안정성'→'자세각' + DimensionExplanation.contributesToOverall OPTIONAL 3중 계약. Wave 0 RED 6 케이스 GREEN, 가드 케이스 GREEN, tsc clean, 회귀 0. SCORE-06/07, TRUST-02. (b2d88d3/a856fba)
- [x] 19-03-PLAN.md — 3D 골격 좌표 정규화 (joints.ts reshapePose3dData recenter+normalize) — TRUST-04
- [x] 19-04-PLAN.md — 파이프라인 표시-점수 정합 + Mode3 미보유 게이트 + v2 hook 자리 — TRUST-01/03/05

### Phase 20: v2 비전 점수 (Gemini 시각 거부권)

> **신규 (belle 2026-06-19 결정 — 우선순위 15-05 → 18 → 20).** Phase 19 v1(D-01 감점식)이 angle 채널 결함은 잡았으나(EVAL 변별 4/4), **비-각도형 실패는 여전히 위양성**(kip-up 100/100). belle 가 2026-06-12 이미 정한 해결책 = **Gemini 시각 점수를 채점 path 에 직접 투입**([[score-spec-95-100-elite-vision-fix]]). 새 발명 아님 — v2 비전 거부권 본체. 상세 정의/스펙 = `.planning/phases/20-v2-gemini/20-CONTEXT.md`.

**Goal:** 점수가 자세 품질을 정직하게 반영하게 한다 — Phase 19 v1 이 남긴 **비-각도형 실패 위양성**을 Gemini 시각 점수(per-pose 시각 거부권/교차검증)로 해소하되, **어떤 영상이든 정확**(보유셋 overfit 금지). 구체 3:

  1. **kip-up 위양성 해소** — 타이밍/완성도 등 비-각도형 실패를 DTW band 가 흡수하는 angle 채널 맹점에 Gemini 시각 점수가 거부권을 행사. v1 의 결정론적 수치와 비전 판단을 결합하되 기하학은 측정가능 IPSF 기준에만. **[정정 — belle 2026-06-23 D-14 amended ITERATION6: kip-up 잘못된예시 = moderate, 점수 ≤75 (20-04 evidence 75/moderate 일치, ≤50 억지 격상=curve-fit 금지). still-frame regression subset 은 23-03 이 OWN. 아래 '≤50' 스펙은 진짜 틀린/실패 동작용.]**
  2. **상단 변별 + 인식기 결정성** — within-20°=일률 100 이라 good vs perfect 구분 부재 → 비전이 상단 품질 차이를 변별. Gemini 인식기(line 차원 결정)는 LLM 이라 run 변동 가능 → temperature 0 + reference 별 profile 캐싱으로 결정성 박제.
  3. **Mode3 미보유동작 유효성 게이트 + 점수근거 표시** — not_pole 안전게이트가 MODE_EXPERT 블록에만 있어 reference-free Mode 3 는 미보유 동작도 무비판 97 출력([[mode3-scoring-basis-unknown-move-gate]]). 동작분류 분기(IPSF공식/정은지보유/둘다미보유→불확실 표시) + 점수근거 화면 노출.

**Requirements**: SCORE-08 (비전 하향 거부권 통합), SCORE-09 (curve-fit 금지 일반화 게이트), TRUST-06 (결정론 temp 0 + 캐시), TRUST-07 (Mode3 미보유 3분기 게이트), TRUST-08 (visionVeto audit + 억제 UX + 객관성) — REQUIREMENTS.md 신설 2026-06-19
**Depends on:** Phase 19 (v1 감점식 채점 루프 + vision-hybrid hook), Phase 18 (deliberate-fault EVAL baseline = known-answer gate)

**게이트 (박제 — 변경 금지):**

- **belle 점수 스펙** ([[score-spec-95-100-elite-vision-fix]]): 같은 정은지(고수) **95~100** / 잘못된 동작 **≤50** / **Gemini Vision 을 점수 path 에 직접**. tol 완화·UX 우회 금지(KISMAM tol=20° 유지).
- **EVAL baseline** (`backend/evals/phase18/`): kip-up fault 가 cap 적용돼 내려가고 변별 4쌍(power-spin/peter-pan/elbow-twist/pdshape)은 변별 유지(퇴행 0). 결정론(같은 입력=같은 점수) 유지. **[정정 — D-14 amended ITERATION6: kip-up = moderate ≤75 (≤50 아님). still-frame regression subset = 23-03 OWN (superseded-by-23-03); SCORE-09 일반화/sensitivity 는 별도 pending.]**
- **일반화 hard gate** ([[scoring-redesign-must-generalize-no-overfit]] / [[sensitivity-gate-not-just-elite-low]]): 정은지 보유셋 curve-fit 금지. 미보유 + above-cutoff(고득점이어야 정상) sensitivity 케이스로 위양성↔위음성 양방 검증.
- **객관성** ([[analysis-objectivity-no-human-scores]]): 사람 점수 라벨 ground truth 영구 금지. 비전 출력은 결함 위치/종류/기하 추정 — 임계값 수치 라벨링은 OK.

**Scope 경계:**

- **climb not_pole 게이트는 본 phase 코드 scope 아님** — correct-climb 조차 ref-climb 유사도 <25 는 ref-climb **reference 품질/촬영각** 문제. 별도 reference-fix 트랙(재등록/재촬영)으로 분리. 본 phase 는 채점 path(Gemini 시각 점수)에 집중.
- **구현/eval = Pod 필요.** 현재 Pod 없음 → 본 항목(roadmap + CONTEXT spec)까지 pod-free, 실 구현·sweep·eval 은 Pod 재개 후.

**Success Criteria** (plan 에서 정밀화):

  1. Gemini 시각 점수가 채점 path 에 통합되어 kip-up fault 영상이 cap 적용(**moderate ≤75** — D-14 amended ITERATION6, ≤50 아님; 위양성 해소) + 정은지 정타 95~100 유지. (still-frame 은 23-03 OWN; superseded-by-23-03 regression subset.)
  2. EVAL baseline 변별 4쌍 퇴행 0 + 결정론 유지(같은 입력=같은 점수)
  3. 미보유 동작 + above-cutoff sensitivity 케이스에서 위양성·위음성 양방 정확(일반화 — 보유셋 한정 X)
  4. Gemini 인식기 결정성(temp 0 + reference profile 캐싱)으로 run 간 line 차원 변동 0
  5. Mode 3 미보유동작 유효성 게이트 + 점수근거 화면 표시(동작분류 분기)

**Plans:** 3/4 plans executed

Plans:

- [x] 20-01-PLAN.md — [Wave 1, pod-free] 순수 vision_veto 코어 (apply_downward_cap 하향전용 + SEVERITY_CAP placeholder + worst_pose_timestamp) (SCORE-08)
- [x] 20-02-PLAN.md — [Wave 1, pod-free] Gemini 결함-심각도 어댑터 (no-score 스키마 + _SCORE_PATTERN 가드 + temp 0 + video-hash 캐시, mocked) (SCORE-08/TRUST-06/08)
- [x] 20-03-PLAN.md — [Wave 2, pod-free] _apply_vision_veto 본체 swap + visionVeto audit 3-way 계약 + Mode3 미보유 억제 + result.tsx UX (SCORE-08/TRUST-07/08)
- [~] 20-04-PLAN.md — [Wave 3, POD terminal] SEVERITY_CAP 도출(sensitivity 양방, 6페어 fit 금지) + serial sweep 게이트 (kip-up cap + 퇴행0 + 정타 95~100 + 결정론) (SCORE-08/TRUST-06; SCORE-09 별도 pending) — **REGRESSION SUBSET SUPERSEDED-BY 23-03 (belle 2026-06-23, D-14 amended ITERATION6): still-frame SEVERITY_CAP *regression subset* 만(SCORE-08 cap + TRUST-06 결정론) 23-03 eval 이 still-frame veto 에서 OWN·검증한다 — 정은지 95~100 / kip-up fault = moderate 점수 ≤75(belle ITERATION6 HIGH-3, 20-04 evidence 75/moderate 와 일치, ≤50 억지 격상=curve-fit 금지) / 결정론(cold+warm) / EVAL18 변별 4쌍 퇴행0. 옛 whole-video 로 별도 sweep 하면 still-frame swap 후 23 이 다시 흔드므로 중복 회피. SCORE-09(일반화/sensitivity — 미보유+above-cutoff 양방검증)는 흡수하지 않고 별도 pending 유지(Phase 20/후속) — 23 이 조용히 SCORE-09 를 닫지 않는다.**

---

## Backlog — 15-05 데모 후속 발견 (belle 2026-06-20 TestFlight #21 실기기)

> belle 실기기 실증에서 나온 10건 중, 이미 처리/로드맵된 것을 뺀 **신규 제품 발견**. 정식 phase 승격 전 backlog 보관 ([[demo-15-05-device-findings]] 메모리 = 전체 triage). 우선순위/phase 그룹핑은 belle 결정 대기.
>
> **이미 처리:** #8 Mode3 역전 = quick 260620-0r0 (수정 완료). #2 마커-점수 모순 + #4 보조지표 표시 = quick 260620-18r (수정 완료, 다음 EAS 빌드 반영). **이미 로드맵:** #1 Mode1 위양성 + #6 Mode3 위양성 = Phase 18(eval) + Phase 20(Gemini 시각 실점수 + Mode3 미보유 게이트). belle 방향: Gemini는 "wrong→<50" 무지성 스탬프 금지, 실분석 정확점수 ([[vision-score-must-analyze-not-stamp]]).

- **B-15a (#7) Mode 3 즉석 2영상 직접 비교:** 현재 첫 분석은 1영상만 받고 세션간 델타 전제. 사용자가 이미 가진 과거 영상 + 오늘 영상을 그 자리에서 둘 다 선택해 비교하는 경로가 없음(belle 통찰). Mode 3 진입 UX + 파이프라인 2영상 입력 분기 필요.
- **B-15b (#5) 고득점 유지형 코칭:** 100점에 coach_writer 가 "거의 동일"만 출력. 유지/관리 관점 맞춤 코칭(이 수준 유지하려면 무엇을 관리) 분기 부재. Phase 13 코칭 영역 후속.
- **B-15c (#9) 코칭 상세에 프레임 이미지:** `CoachingTipDetail` 스키마에 이미지 필드 없음 — 상세(원인/처방)가 텍스트만이라 어느 순간/자세인지 알기 어려움. 해당 결함 프레임 캡처/오버레이 첨부.
- **B-15d (#10) 보완 운동을 코칭 팁 상세로 통합:** 현재 `tips[]` 와 `recommendedExercises[]` 가 완전 분리. 각 코칭 팁 "자세히 보기" 안에 관련 보완 운동 + 연관성 설명을 넣어 맥락 강화. Phase 13 코칭 영역 후속.
- **B-15e (#3) 3D 뷰어 저장 안정화 + 카메라앵글:** `joints3d` 미저장 doc 이면 빈 화면(Firestore index-entry 한도 이력 — 저장 안정화 = 버그성). + 정은지 실영상에서 회전 동작하는 단일-뷰 카메라앵글 합성은 미구현 신기술 트랙 ([[camera-angle-ai-single-view-synth]]).

### Phase 21: 전문가 셀프서비스 reference 등록 (angles 자동계산 GPU 연결)

> **신규 (belle 2026-06-20).** CLAUDE.md §2 파일럿 Step 2("정은지 촬영 → 백엔드 업로드 → 기준 모션 자동 등록") 직접 충족. 메모리 [[deferred-selfservice-reference-registration]]. Phase 17-05 에서 메타데이터 자동 등록(reference-auto-register Lambda + Gemini A)은 이미 배포돼 동작하나, **새 영상의 angles(포즈) 가 자동 계산되지 않아** 등록해도 Mode 1 비교가 불가 — 이 phase 가 그 GPU 갭을 메운다.

**Goal:** 전문가(정은지/코치)가 새 reference 영상을 업로드하면 추가 수작업 없이 Mode 1 비교 가능한 기준 모션으로 자동 등록된다. 등록 흐름이 angles((T,J) 포즈) + downstream(meanAngles/techniqueProfile/bodyNormalizationProfile/forceDirectionPattern)을 자동 계산·저장 → 등록 즉시 Mode 1 비교 사용 가능. 잘못된 메타데이터가 baseline 을 오염시키지 않게 검수 게이트 유지.

**이미 구축됨 (재사용):** `backend/functions/reference-auto-register/app.py` (POST /reference/auto-register, 배포됨 — belle 인증+BELLE_UID 화이트리스트 + Gemini A `extract_reference_metadata` 동작명/IPSF/checkpointJoints/routing branch + `set_reference_motion_with_gemini` idempotent upsert). 앱 GET /reference 컬렉션 전체 read + `referenceMotions.ts` onSnapshot → 새 reference 자동 목록 반영. downstream compute 엔진(`backfill_reference_downstream.py::compute_reference_downstream`)은 motion_id 범용.

**핵심 갭 (이 phase 가 메우는 것):** auto-register 가 angles 를 계산·저장하지 않음. 현재 angles 는 Pod GPU 수동 스크립트(`extract_reference_angles.py` + downstream backfill)로만 생성 → 등록 흐름에 GPU angle+downstream 자동 계산 연결이 핵심.

**Requirements**: plan 에서 신설 (REF-xx 계열 — angle 자동계산 연결 / 업로드 진입점 / clipRange·checkpoint 검수 게이트 / 11→N 일반화 / baseline 오염 방지)
**Depends on:** Phase 17 (Gemini A 메타데이터 + auto-register Lambda), Phase 14 (downstream compute 엔진). 구현/검증 = Pod GPU 필요.

**Scope 경계:** end-user(수강생) 아님 — 전문가/관리자(belle/정은지/코치) 셀프서비스. 채점 알고리즘 변경 아님(Phase 18/20 영역). reference 영상→기준 데이터 생성 자동화에 집중.

**Success Criteria** (plan 에서 정밀화):

  1. 새 영상 등록 흐름이 angles + downstream 을 자동 계산·저장 → 등록 즉시 Mode 1 비교 가능 (핵심 갭 해소, GPU 연결)
  2. 업로드 진입점 마련 — belle 가 영상만 올리면 됨 (admin UI 또는 간편 endpoint/CLI; 현재는 S3 key 로 endpoint 직접 호출)
  3. clipRange/checkpoint 자동 제안 + belle 검수 분기 (도메인 오류로 baseline 오염 방지 — Gemini 제안, belle 최종 확인, 미검수는 isActive=false)
  4. 11→N 일반화 확인 (하드코딩 MOTION_IDS/게이트 제거 — 대부분 이미 컬렉션 쿼리, 확인 위주)
  5. 객관성/품질 — 사람 점수 라벨 ground truth 금지 유지([[analysis-objectivity-no-human-scores]]), reference 메타데이터 오류 시 baseline 미반영(G3 guardrail)

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 21 to break down)

---

### Phase 22: 자체 비전 모델 파인튜닝 (오픈 모델 전환)

> **신규 (belle 2026-06-20).** Phase 20 에서 드러난 한계 = Gemini 는 닫힌 API라 **가중치 파인튜닝 불가** — 프롬프트/few-shot/캐싱까지만 가능. belle 결정: Phase 21 까지 끝낸 뒤, 꾸준히 모아온 공개 폴 영상 라벨 데이터로 **오픈 비전 모델을 실제 fine-tune** 해서 Gemini 의존 영역(시각 결함 판정/인식기)을 갈아끼운다. "어차피 해야 할 일 — 모델을 함께 쓰든, 됐다 싶을 때 교체."

**Goal:** Gemini 시각 판정(결함 severity / 동작 인식)을 도메인-특화 오픈 비전 모델로 대체/병행한다. 폴스포츠 공개 영상(대회=정타, 튜토리얼 "흔한 실수"=fault) + 정은지 gold 셋으로 라벨 학습셋을 구성해, 정타를 결함으로 스탬프하지 않고(위양성) 실제 결함을 적정 severity 로 잡는(일반화) 판정기를 확보한다.

**선행으로 꾸준히 쌓을 것 (Phase 20~21 동안 데이터 적재):**

- #4(b) sensitivity/일반화 eval 셋 (미보유 + above-cutoff) — 그대로 학습/검증셋 시드
- #4(c) reference 라이브러리 확장 (대회 elite 영상)
- #4(d) severity threshold 경험 데이터
- 버킷 라벨(정타/fault)만 — 사람 숫자 점수 라벨 금지 ([[analysis-objectivity-no-human-scores]])

**교체 가능성 (이미 깔린 기반):** PoseEngine/recognizer 인터페이스 추상화([[rtmw-free-stack-pivot]]) + Gemini 어댑터 경계(20-02 gemini_vision_scorer) → 판정기를 인터페이스 뒤에서 swap. 라이선스 게이트([[license-blocklist-pose.md]] / [[rtmw-clean-weight-release-gate]]) 준수 — 상업 출시용은 clean-data weight.

**setup/prep belle 알림 대상 (진행하며 그때그때):** 학습 GPU(RunPod 등) / 오픈 모델 선택 / 라벨링 도구 / 데이터 저장. 본격 착수는 Phase 21 완료 후.

**Requirements**: plan 에서 신설 (FT-xx — 모델선정 / 학습셋 / 라벨링 / 학습·평가 / swap 게이트 / 라이선스)
**Depends on:** Phase 20 (Gemini 판정 한계 + few-shot 데이터), Phase 21, 누적 라벨 데이터. 학습/평가 = GPU 필요.

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 22 to break down — Phase 21 완료 후)

---

### Phase 23: Mode 1 결함 recall 복구 — still-frame veto (영상통째→DTW key-frame 부위별) + 기준선 정량화

> **신규 (belle 2026-06-22).** **실행 우선순위 = Phase 22(파인튜닝)보다 먼저** — 리서치의 단기 트랙(현 스택 즉시 구현). 근거 = 2026-06-22 deep-research(소스 23개, 18 confirmed) + B 스파이크. 핵심 발견: 현 Mode 1 veto 의 "영상 통째 Gemini 비교"가 상체 결함(팔-폴 갭/고개젖힘/팔꿈치)을 구조적으로 놓친다(whole-video VLM 한계). B 스파이크 실증: **단일 key-frame 입력 시 좌/우팔+고개 풀 recall, 깨끗 프레임 위양성 0** → 레버는 입력 granularity. [[spike-stillframe-recovers-upperbody-2026-06-22]]

**Goal:** Mode 1 veto/비교의 입력을 "영상 통째 업로드"에서 "DTW worst-pose **단일 key-frame(들)** + 부위별 프롬프트 + 프레임×부위 union + N-sample"으로 교체해 상체 결함 recall 을 복구한다(위양성은 늘리지 않음 — 깨끗 프레임 none 유지). 동시에 결함 출력에 **기준선 정량화 레이어**(각도=직접 측정 / 거리=몸-상대 칸·층+화살표 / 기준선=동작별)와 **증상→root cause(힘/폴밀착) 묶음 코칭**을 더해 "무엇을 고쳐야 하는지"를 직관화한다. **스코프(belle 2026-06-22 cross-AI 리뷰 후 정정): Mode 1 집중 — Mode 3 정량화/정렬은 공식 defer(Backlog B-15a 합류). 정량화·코칭은 백엔드 계산·저장·생성까지, 앱 표시(result.tsx/coach-report 렌더링)는 후속 UI phase. 칸·층은 keypoint/폴/바닥 baseline 에서 결정적 기하 계산(VLM 이 수치를 지어내지 않음, percent 표기 금지 — `_SCORE_PATTERN` 누수 회피). 시각 화살표/오버레이는 v1.1.**

**핵심 설계 (스파이크로 입증):**

- **입력 granularity = 레버.** whole-video=상체 0, 5프레임 배치=팔 1, 단일 프레임=풀 recall. → DTW worst-pose 단일 key-frame 으로 교체.
- **recall 완전성** = key-frame × 부위(상체/하체/라인) union + N-sample(단일 호출 과소열거 보정, Phase 20 N=3 집계 근거).
- **DTW 정렬 신뢰도가 성패** — Mode 1 은 사용자 시작점·템포가 reference 와 다른 게 정상. `motiondtw` 2단계(find_action_segment 시작점 + dtw 워핑)가 담당하나, 단일 프레임 의존이라 **정렬 신뢰도 게이팅(MotionMatch.distance) + worst-pose ±윈도우 + 시작점/템포 상이 케이스 프레임선별 검증** 필수(리서치 "DTW 오정렬→거짓결함" 경고).
- **사이즈 통일은 기확보** — 점수는 관절각(스케일 무관) + BodyNormalizationProfile(상대 스케일). 신규 거리표기는 반드시 몸-상대(절대 cm 금지, 140/150 깨짐). [[output-needs-baselined-quantification-layer]]

**Requirements**: plan 에서 신설 (VETO-xx — still-frame 입력 swap / 부위별·union / 정렬 신뢰도 게이팅 / 정량화 레이어 / 증상→원인 코칭).
**Depends on:** Phase 20 (vision veto 어댑터 경계 `gemini_vision_scorer` + downward-cap), Phase 19 (vision-hybrid 채점 hook). 구현/eval = Pod GPU 필요.

**게이트 (박제 — 변경 금지):**

- **일반화 hard gate** ([[scoring-redesign-must-generalize-no-overfit]]): known-answer 에 맞춘 유도 프롬프트·curve-fit 금지. 프롬프트는 generic 유지, recall 은 자체 라벨셋으로 측정.
- **객관성** ([[analysis-objectivity-no-human-scores]]): 사람 점수 라벨 ground truth 금지. 결함 위치/종류/기하 추정만. 고개젖힘 등은 belle 추정 + VLM 독립판정 수렴으로 다룸(하드 라벨 금지).
- **위양성 비증가** — 깨끗 프레임/정타는 none 유지(스파이크 확인). 위양성 history 재발 금지.
- **Mode 3 = 발전** ([[mode3-progress-not-similarity]]): 절대지표 델타. 코칭은 원인=Gemini/처방=Cerebras 섹션 분리 합류 [[section-dual-coach-report]].

**Success Criteria** (plan 에서 정밀화):

  1. Mode 1 veto 입력이 whole-video → DTW worst-pose 단일 key-frame(들)로 교체되고, kip-up 상체 결함(좌/우팔+고개) recall 이 복구된다(스파이크 effect size 재현).
  2. 깨끗 프레임/정타에서 위양성 0 유지(특이도 보존) + 결정론(같은 입력=같은 verdict) 유지.
  3. DTW 정렬 신뢰도 게이팅 + 시작점/템포 상이 케이스에서 프레임선별이 거짓결함을 만들지 않음(검증 task).
  4. 결함 출력에 기준선 정량화(각도 직접 / 거리 몸-상대 칸·층 — keypoint·폴·바닥 baseline 에서 결정적 계산, percent 표기 금지)가 **계산·저장**된다 (앱 표시는 후속 UI phase).
  5. 코칭 출력이 증상을 root cause(힘/폴밀착)에 묶어 **생성**된다 (백엔드; 앱 표시 후속). 일반 답변·수치 나열 금지.
  6. (cross-AI 리뷰) union 에 precision/support 게이트 — 단발 환각 결함이 살아남지 않음(위양성 비증가 강화). 23-03 eval 은 실제 production 경로(_apply_vision_veto·프레임선별·게이팅·캐시)로 측정 + 동일 모델 baseline 재실행 + cold/warm 결정론 분리 + cost/latency·machine-checkable 게이트.

**Plans:** 2/3 plans executed

Plans:

- [x] 23-01-PLAN.md — still-frame 입력 swap + 부위별 key-frame union + DTW-confidence 게이팅(low_alignment_confidence status) (VETO-01/02/03)
- [x] 23-02-PLAN.md — 기준선 정량화 레이어(각도 직접 + 몸-상대 칸/층 텍스트) + 증상→root cause "~로 보임" 가설 코칭 (VETO-04/05)
- [ ] 23-03-PLAN.md — [POD] still-frame veto eval — kip-up recall 재현 + 위양성 0 + 결정론 + 정렬-약 보류 + non-zero assert 게이트(frozen manifest+lock) + **Phase 20-04 regression subset 흡수 게이트(정은지 95~100 / kip-up fault moderate≤75 / 결정론 cold+warm / EVAL18 변별 4쌍 퇴행0, D-14 amended + D-15 — regression subset 만 supersedes 20-04, SCORE-09 별도 pending)** (VETO-06/SCORE-08/TRUST-06)

> ⚠️ **2026-06-24 belle 채점 철학 결정타 — 23-03 의 "kip-up fault moderate≤75" 같은 케이스별 기대점수 밴드는 curve-fit 으로 Phase 24 가 제거·교체.** 23-03 eval 은 recall/위양성0/결정론 게이트로 유지하되, 기대점수 밴드 assert 는 Phase 24 의 추적성·단조성 게이트로 대체된다.

---

### Phase 24: 투명 감점-합산 채점 엔진 (severity 밴드 → 측정편차×명시규칙 감점)

> **신규 (belle 2026-06-24 — Phase 23 Pod eval 도중 채점 철학 결정타).** Phase 20 이 만든 `vision_veto.SEVERITY_CAP{minor:90,moderate:75,major:50}` + `apply_downward_cap=min(overall,cap)` 가 **금지 대상으로 확정**됐다. belle 원문: "육안 판단 불가/사람마다 다른 걸 객관적으로 재려고 AI 쓰는 건데, 내가/너가 '이건 50 넘기지마' 밴드 박으면 그냥 사람이 판단하지 AI가 왜 있냐." severity→고정천장은 영상마다 자의적 = 사람 판단 주입 = AI 존재이유 무효. [[scoring-must-be-transparent-deduction-tally]]

**Goal:** 채점을 **점수 = baseline(100) − Σ(criterion별 측정편차 × 명시규칙 감점)** 으로 교체하고, 보고서가 **"여기 −X, 여기 −Y, 여기 −Z = 점수"** 감점 내역을 명명백백하게 노출한다. 결과 숫자(50이든 70이든)는 tally 출력일 뿐 범위가 아니다 — 동일 규칙 + 실측 편차 + 계산 노출 → "왜 이 점수?" 항상 추적가능. Phase 20 의 밴드 한 단(`SEVERITY_CAP`/`apply_downward_cap`)만 제거·교체하고, 20 의 working parts(`gemini_vision_scorer` 결함 짚기 = score 0/severity·measured target, Mode3 게이트, score suppression)와 Phase 23 정량화(각도편차·몸-상대 칸/층)·recall 은 보존·재사용한다.

**핵심 설계 (discuss 2026-06-24 박제 — 24-CONTEXT.md ND-01~07):**

- **ND-02 Gemini 강등:** Gemini 는 점수 X. **어디를 측정할지 / 무슨 결함인지**만 짚는다. 점수는 측정값 + 규칙. (`gemini_vision_scorer` severity enum → "측정대상 지목"으로 의미 재해석.)
- **ND-03 감점 규칙 = 기하 tolerance 확장:** `dimensions.py` 의 tolerance + per-unit penalty(`_LINE_TOL_DEG`/`_PENALTY_PER_DEG` 기존)를 전 차원(각도·라인·거리 칸/층)으로 확장. 동일 형태 단일 규칙, 모든 영상 동일 slope (curve-fit 금지).
- **ND-04 감점 구조 = criterion 묶음 + IPSF 상한:** 상관 관절은 IPSF criterion 으로 묶어 1회 측정(양다리=다리 신전 1 criterion → 30°+30° 가 −60 안 됨). 각 criterion 감점 = 편차→tolerance(안=0)→곡선, **상한 = 그 fault 의 IPSF severity 가중치(fault 종류별 규칙, 최종점수 밴드 아님)**. criterion 감점 **합산**(평균 금지 — 희석 방지). → 원 20-D05 "worst-pose 지배"를 합산 구조로 supersede.
- **ND-05 baseline=100:** 사용자가 배우려는 코치(선수) 동작 = 그 사용자에겐 100점(지금 정은지, 흐름상 일반화). IPSF 공식 등재 동작 → IPSF 심사기준이 기준. 기존 20-D07 3분기((1)IPSF공식→IPSF / (2)미등재+코치보유→코치비교 / (3)둘다없음→게이트)와 정합, "reference"를 "사용자 선택 코치"로 일반화. 동작별 기준선([[output-needs-baselined-quantification-layer]]: kip-up=바닥/공중=폴·엉덩이라인)은 측정 토대.
- **ND-06 측정불가 결함:** 설계 목표 = 매핑 강제 — Gemini 가 짚은 모든 결함은 기하 측정항(각도/거리 칸·층/라인 편차)으로 변환되어 감점된다. **"보이는데 0감점"은 출하 금지(coverage gap)**. 규칙 미작성 시 임시로만 감점 0 + coverage gap 로그(자의적 밴드 주입 절대 금지) → 그 결함의 측정규칙 추가.

**Requirements**: plan 에서 신설 (SCORE-09 흡수 + 신규 — 감점 엔진 교체 / criterion 묶음·IPSF 상한 / Gemini 강등 / baseline 분기 / 측정불가 매핑 / 보고서 감점내역 노출(백엔드 계산·저장; 앱 표시는 후속 UI phase)).
**Depends on:** Phase 20 (`gemini_vision_scorer` 어댑터 + Mode3 게이트 — 보존·재사용, `SEVERITY_CAP`/`apply_downward_cap` 제거), Phase 23 (정량화 레이어 = 감점 입력, recall), Phase 19 (감점식 집계 코어 `kismam`/`dimensions`). 구현/eval = Pod GPU 필요.

**게이트 (박제 — 변경 금지):**

- **밴드 금지** ([[scoring-must-be-transparent-deduction-tally]]): 최종점수에 고정 천장/하한 금지. fault 종류별 IPSF 상한만 허용(영상 무관 동일 규칙). 케이스별 기대점수 manifest(moderate≤75·major=50) curve-fit 제거.
- **일반화 hard gate** ([[scoring-redesign-must-generalize-no-overfit]] / [[sensitivity-gate-not-just-elite-low]]): 6페어에 curve-fit 금지. 미보유 + above-cutoff sensitivity 셋으로 위양성↔위음성 양방 검증.
- **객관성** ([[analysis-objectivity-no-human-scores]]): 사람 점수 라벨 ground truth 금지. 감점은 실측 편차 + 명시 규칙에서만.
- **결정성** ([[pipeline-not-concurrency-safe-eval-serial]]): 같은 입력 = 같은 감점 내역. eval/sweep 순차만.

**Success Criteria** (plan 에서 정밀화):

  1. `vision_veto.SEVERITY_CAP` + `apply_downward_cap`(severity→고정천장)이 제거되고, 점수 = baseline(100) − Σ(criterion별 측정편차×명시규칙 감점) 엔진으로 교체된다.
  2. **추적성 (Mode1 scope)** — 모든 −점이 명명된 측정 편차 + 명명된 규칙으로 100% 역산되고, 보고서가 "−X(부위) −Y(부위) = 점수" 내역을 **Mode1(MODE_EXPERT) 경로에서** 백엔드에서 계산·저장한다(앱 표시는 후속 UI phase). **Mode3(MODE_SELF) 는 mode3_held passthrough 로 deductionBreakdown 미산출** — Mode3 절대지표 IPSF/criterion 세션간 델타 감점 내역(ND-05 [[mode3-progress-not-similarity]])은 정직한 후속 phase 후보(이 phase 의 silent gap 아님).
  3. **단조성** — 측정 편차가 커지면 점수가 반드시 낮아진다(역전 0). 상관 결함이 criterion 묶음으로 1회만 감점되어 폭주하지 않는다.
  4. **결정성** — 같은 입력 = 같은 감점 내역(temp 0 + 캐싱). Phase 18 exact-score drift 해소.
  5. **일반화** — 정은지(또는 사용자 선택 코치) 정타는 감점합≈0 → 95~100(타깃 아닌 결과), 미보유·above-cutoff 도 정상 고득점. kip-up 등 결함은 측정→감점으로 잡힌다(밴드 없이).
  6. Gemini 가 짚은 결함이 기하 측정항으로 매핑되지 않는 "보이는데 0감점" 케이스가 출하 경로에 없다(coverage gap 로그로 검출).

**Plans:** 3/4 plans executed

Plans:
**Wave 1**

- [x] 24-01-PLAN.md — deduction_engine.tally (pure, 측정-substrate 입력 + baseline_kind string arg + unavailable→dimension fallback + 추적성 fallback record) + ipsf_criteria (5 측정가능 criterion: leg_extension/arm_extension/split_angle/line[substrate profile-gated: 빈 joint_expectations→정직한 0, 밴드 아님 ND-06] + body_relative_reach[reference_relative, delta_notches 소비 — baseline_kind 가 점수에 영향 ND-05/1급입력] + 5 TRACKED deferred coverage gap = FaultKey 8 set 완전 분할 + per-criterion deviation source) + LINEAR slope(raw=over*slope, gaussian delegate 금지) + OBJECT 계약(records/coverageGaps/fallback) + criterion_for_fault_key (FaultKey vocab 전수+partition) + DEDUCTION_* 3-way 계약 lockstep + 단위 게이트 (Wave 1, SCORE-10/11/12/14/15/16)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 24-02-PLAN.md — vision_veto 밴드 제거(SEVERITY_CAP/apply_downward_cap, to_audit_dict band-free) + gemini_vision_scorer severity docstring → criterion-pointer 재구성 + _process veto seam → tally 교체(측정 overallScore + _build_deduction_measured_deviations named substrate 주입 — 0-100 score 를 편차로 오입력 금지 HIGH-3) + per-move baseline_kind 도출(name/motion_id 문자열 매칭, seam 1회 산출 후 string 으로 apply path 에 thread — engine 은 profile 미수신) + cap_would_apply 보존 band-free 연속성(severity in (moderate,major) → 오늘의 coach-injection trigger 와 동일 발화, minor/none 미발화 — byte-동일 legacy 아님 HIGH-6) + result[deductionBreakdown] OBJECT 저장(to_dict, visionVeto analog, _validate_deduction_breakdown top-level dict 검증·kwarg 없음) + capApplied→tallyFinal 3-way 계약 이관(analysis.ts↔models.py↔contract.md §4) + 깨진 caller 테스트 4개(test_vision_veto/test_pipeline_vision_gate/test_pipeline_mode3/test_gemini_vision_scorer) band-free 이관(repo-wide grep 0) + Mode3/토글/정량화 보존 (Wave 2, SCORE-10/13/15/16/09)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 24-03-PLAN.md — phase24/assert_gates.py 4 게이트(추적성/단조성[fixed-set]/결정성[math+criterion-selection]/일반화) + phase18 verdict·margin assert 제거(밴드 문자열 아님) + Pod-serial 일반화 sweep belle 검증(cold-rerun selection 동일) (Wave 3, SCORE-16/09)

---

### Phase 25: 상체 감점 커버리지 — vision-pointed window 측정 (짚기=Gemini / 측정=worst-window / 감점=규칙)

> **신규 (belle 2026-07-04 — TestFlight 실기기 실증에서 확정된 갭).** kip-up fault 영상에서 어깨 좌우 편차(40°/31°, tol 20° 초과)가 **측정은 되는데 감점 0** — 확대/마커/감점 전부 다리(스플릿)만. 원인 = 감점 seed 의 집계가 전체 DTW path median 이라 국소 결함이 희석됨. quick 260702-o0c 로 "표시용 worst-window median 을 seed 로" 실험 → **kip-up fault 50 으로 상체 감점 메커니즘은 실증**됐으나 **success 위양성 4건(74~92)** 으로 sweep GATE FAIL, revert ([[window-median-silent-seed-fp-reverted]]). 교훈 = worst-window 는 편향 표집이라 Gemini-silent 관절에 쓰면 RTMW jitter/촬영거리 노이즈를 감점으로 증폭 (2026-06-12 full-path median 전환 사유의 재확인). belle 도메인 판정: 88(상체 누락)도 50(과감점)도 아닌 그 사이가 정답 — 특정 점수 맞추기(짜맞추기) 금지, 측정 구조를 고쳐 점수가 자리를 찾게 한다.

**Goal:** 역할 분리 아키텍처로 상체(및 임의 부위) 결함 감점 커버리지를 확보한다 — **짚기(detector) = Gemini vision 이 결함 관절/부위를 faultKey 로 지목, 측정(measurement) = 그 관절만 worst-window median 기하 측정, 감점(scoring) = 기존 명시규칙(tol 20°+slope)**. Gemini-silent 관절은 기존 보수적 full-path median seed 유지(위양성 방어). 전제 작업 = vision 결함 짚기 커버리지를 상체까지 확대(per-move 프롬프트/기준 — kip-up 은 현재 split 특정이라 상체는 primaryFault 텍스트로만 언급되고 faultKey 없음). 프롬프트 특정성이 레버라는 기존 결론([[flash-beats-pro-video-split-judgment]]) 재사용.

**게이트 (Phase 24 게이트 승계 + 이번 실패 교훈):**

- sweep 6페어: fault 변별 유지·개선 AND **success 6/6 == 100** (위양성 0 — 260702-o0c FAIL 재발 금지)
- kip-up fault: 88 미만으로 하락하되 상체 감점이 vision-확인 관절에서만 발생 (50 과감점 재현 금지 — 단 특정 점수 assert 는 curve-fit 이므로 금지, "vision 짚은 관절만 감점" 구조 assert 로)
- 밴드 금지 / 신규 튜닝 상수 금지(tol·slope·window 정책 기존 재사용) / 결정론 / 사람 점수 라벨 금지

**Depends on:** Phase 24 (감점 엔진 + criterion 라우터 — 그대로 소비), Phase 23 (still-frame/moment 추출), quick 260702-o0c 실험 결과. 구현/eval = Pod GPU 필요. F(260704-fz4) advisory 티어가 UI 선행 — 측정 초과 관절이 이미 "참고(주황)"로 노출되므로, 이 phase 가 완성되면 vision-확인분이 참고→확정(빨강)으로 승격되는 구조.

**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 25 to break down)

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
*Roadmap updated: 2026-06-24 (Phase 24 신설 — 투명 감점-합산 채점 엔진. belle 채점 철학 결정타([[scoring-must-be-transparent-deduction-tally]]): Phase 20 의 severity→고정밴드(`SEVERITY_CAP`/`apply_downward_cap`)는 자의적=사람 판단 주입 → 점수=baseline(100)−Σ(측정편차×명시규칙 감점), 보고서가 감점 내역 노출 엔진으로 교체. Gemini 강등(점수X·측정대상만 짚기). Phase 20 은 재설계 아님 — working parts 보존, 밴드 한 단만 신규 phase 가 supersede. 23-03 의 케이스별 기대점수 밴드(moderate≤75) curve-fit → Phase 24 추적성·단조성 게이트로 대체. discuss 결정 = 24-CONTEXT.md ND-01~07. Phase 19·20·23 의존, Pod 필요, Phase 22 보다 먼저.)*
*Roadmap updated: 2026-07-04 (Phase 25 신설 — 상체 감점 커버리지 vision-pointed window 측정. TestFlight 실증에서 어깨 40° 측정-무감점 갭 확정, quick 260702-o0c worst-window 실험 = 메커니즘 실증 but success 위양성으로 revert([[window-median-silent-seed-fp-reverted]]). 아키텍처 = 짚기(Gemini faultKey)/측정(worst-window)/감점(규칙) 역할 분리 + Gemini-silent 는 full-path median 유지. belle 판정: 88도 50도 아닌 사이가 정답, 점수 짜맞추기 금지.)*
