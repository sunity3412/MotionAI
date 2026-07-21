---
phase: 32-result-readability-3-omni
plan: 11
subsystem: app-result-screen
tags: [result-screen, rewire, viewmodel, summary-card, deduction-card, mission-loop, coach-questions, judge-simulation, cue-track, coachmarks, d-02, d-03, d-13, d-27, d-28]

# Dependency graph
requires:
  - phase: 32-03
    provides: "resultSections 확정 순서의 근거(D-02) + 6동작 doc 스윕 기준선"
  - phase: 32-07
    provides: "SummaryCard/summarySource/ResultCoachmarks/coachmark + E2 강조 토큰"
  - phase: 32-08
    provides: "cueTrack.buildCueWindows + VideoCompare cueWindows/initialOffsetSec/resetKey/적용중"
  - phase: 32-09
    provides: "방출 실측 doc(recordId·3단 문구·mission·missionOutcome·summaryPraise·coachQuestions)"
  - phase: 32-10
    provides: "DeductionCard/GoalGaugeBar/MissionBadge/DeductionDetailSheet/InjuryRiskSection"
provides:
  - "result.tsx 대배선 — D-02 확정 10항 순서로 재편(요약→위험→top-1→비교→접힘→성장→운동→질문→심사→참고코너)"
  - "resultSections 순수 뷰모델(deriveResultSections/buildRecordMaps) — 순서·가시성·legacy 분기·recordId 조인 단일 지점 (node --test)"
  - "개인화 심사 시뮬레이션 코너(D-03) — 내 결함 → IPSF 감점 환산, 지식전달형 폐기"
  - "보완 운동 개편(D-13) + 코치 질문 강화(D-28) + 미션 루프/코치 카드 승격(D-27)"
  - "슬라이더 정렬 지점 시각 표시(실기기 피드백 #2)"
affects: [32-12 (실기기 6 doc 전수 렌더 게이트 — 이 화면 검증 소비측), 32-13 (spotCheck praiseMismatch 소비 지점 배선처)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "결과 화면 섹션 순서·가시성 = resultSections 순수 뷰모델 단일 지점(2,700줄 대배선을 typecheck 아닌 node --test 로 고정)"
    - "카드 상호작용(점프·질문·드릴다운) = recordId 안정 조인(배열 index 금지) + 부재 legacy record는 'idx:N' 폴백"
    - "파생 계산(records/recordMaps/cueWindows/summaryContent/sections) 전부 useMemo — VideoCompare tick 렌더 churn 격리"

key-files:
  created:
    - app/src/lib/resultSections.ts
    - app/src/lib/__tests__/resultSections.test.ts
  modified:
    - app/src/app/analysis/result.tsx
    - app/src/components/VideoCompare.tsx

key-decisions:
  - "result.tsx return 은 단일 블록이라 Task 1(상부)/Task 2(하부) 를 커밋 2개로 분리 — 상부 재편 후 하부는 유효 중간상태로 렌더되게 순차 전환"
  - "DeductionCard 인라인 확대쌍(userUri/refUri 2장)은 미배선 — FaultZoomComparison 이 [학생|기준] 단일 합성 PNG(imageUrl)라 2-URI 계약과 불일치. 확대쌍은 기존 DeductionDetailSheet 드릴다운(D-17 자세 비교 카드)이 담당(배선 완료), top-1 카드에 '확대 비교 자세히 보기' 진입점"
  - "심사 시뮬레이션 근거 = record.whyLine(심사 언어) — raw ipsfAnchor 노출 대신. 수치는 실존 감점(−points)·환산 점수만 (자의적 % 아님, D-09 무충돌)"
  - "구 참고 지표(dims.map)·DimensionScoreRow/DiagnosisRow/DetailModal 제거 — D-03 심사 코너로 대체 + D-12 '안정성' 추상 용어 표면 제거. 차원 수치는 감점 카드 게이지·심사 환산으로만 흐름"
  - "RecommendedExerciseModal 은 미수정 — D-13 '인라인 전환' 옵션 채택(result.tsx 전면 1개+가로 3). 모달은 '전체 보완 운동 보기' 전체 라이브러리 브라우저로 존치"

requirements-completed: [D-01, D-02, D-03, D-08, D-13, D-14, D-17, D-26, D-27, D-28]

# Metrics
duration: ~2h 30m
completed: 2026-07-22
---

# Phase 32 Plan 11: result.tsx 대배선 — 게이트 확정 순서 통합 Summary

**지금까지 만든 컴포넌트(SummaryCard/DeductionCard/게이지/배지/코치마크/cueTrack)와 방출 필드(recordId·3단 문구·미션·summaryPraise·질문)를 D-02 확정 10항 순서로 통합해 belle §10 "어떻게 읽으라는 건지 모르겠다"를 구조적으로 해소하고, 순서·가시성·recordId 조인을 순수 뷰모델(node --test)로 고정한 결과 화면 재편 — 보완 운동 개편(D-13)·코치 질문 강화(D-28)·개인화 심사 시뮬레이션(D-03)·미션 루프/코치 카드 승격(D-27)·슬라이더 정렬 지점 표시 포함**

## Task Commits

| Task | 내용 | 커밋 |
|---|---|---|
| 1 (RED) | resultSections 뷰모델 실패 테스트 5건 | `f6f1c8b` |
| 1 (GREEN) | deriveResultSections + buildRecordMaps 순수 뷰모델 | `85e16f0` |
| 1 | result.tsx 상부 재편 — 요약 카드·위험 승격·top-1·비교+큐·코치마크 | `15ec449` |
| 2 | result.tsx 하부 재편 — 접힘 카드·성장/미션·보완 운동 가로·코치 질문 점프·심사 시뮬레이션 | `776351e` |
| 2+ | VideoCompare 슬라이더 정렬 지점 표시 (실기기 피드백 #2, Rule 3) | `245761f` |

## Accomplishments

### Task 1 — resultSections 뷰모델 + 상부 재배치

- **resultSections.ts (순수 함수, react/expo 의존 0)**: `deriveResultSections` — D-02 10항 순서(`RESULT_SECTION_ORDER` 단일 출처)·가시성·legacy/clean/suppressed variant·mode3 성장(coach_card 우선) 결정. `buildRecordMaps` — recordId 조인 맵(부재 시 `idx:N` 폴백, 중복 recordId 강등으로 충돌 0, 질문 recordId 조인, matchZoom 주입). `node --test` 5건 GREEN.
- **상부 재편**: 요약 카드(`SummaryCard` — `deriveSummaryContent` 조립: summaryPraise/missionOutcome/mission/dimensionScores/coverageGaps/records/safetyFlags)를 첫 콘텐츠로, 큰 점수 게이지(OctagonScore)는 D-01/D-09 로 상세 영역 강등(요약 카드 점수 소형 배지 1곳). 위험(InjuryRiskSection) 요약 직후 승격. top-1(미션 record 우선/최대 감점) `DeductionCard` 완결형. 동작 비교(VideoCompare) #4 상향 + `cueWindows` 배선(record cueLine + 매칭 zoom userFrameIdx + 학생 fps) + initialOffsetSec/resetKey 유지. 첫 진입 코치마크 1회(`hasSeenResultCoachmark`).
- **파생 계산 useMemo**: records/topFixIndex/recordMaps/cueWindows/summaryContent/sections 전부 memo (VideoCompare tick churn 격리).
- **점프**: ScrollView ref + 카드 onLayout y 기록(recordId 안정 키) → 요약 '오늘 고칠 것' 탭·질문 탭이 해당 카드로 scrollTo.

### Task 2 — 하부 재배치

- **나머지 감점 카드(#5)**: 기본 접힘 `DeductionCard` 목록(top-1 제외, 탭 → 드릴다운 시트). 투명 감점 내역(ScoreBreakdownSection)·구간 점수·코칭 팁은 상세 영역 유지(수치 삭제 0).
- **성장·지난 미션(#6, D-26/D-27)**: missionOutcome 정직 표시(개선/미개선, 수치는 소형 배지). `escalation==='coach_card'`(3회 미개선) 시 코치 카드 전면 승격("혼자 안 되는 건 방법 문제일 수 있어요" + 질문 연결).
- **보완 운동(#7, D-13)**: 전면 top-1 연결 1개 + 이유 1줄(record.exerciseReason 우선), '다른 운동 보기' 가로 스크롤 최대 3 — **5개 세로 나열 폐지**. `escalation==='exercise_detour'`(2회차) 시 우회 제안 카피 상단.
- **강사 질문(#8, D-28)**: `result.coachQuestions`(자동) + legacy 폴백(openQuestionsForCoach) + 사용자 담기(`onAskCoach` → source 'user') 통합. 질문 탭 → recordId 로 해당 감점 카드 점프.
- **심사 정보 코너(#9, D-03)**: 개인화 심사 시뮬레이션 — 내 실제 감점 record 를 IPSF 감점(−points)으로 환산 + 환산 점수. 근거는 whyLine(심사 언어). 행 탭 → 드릴다운. 지식전달형 폐기.
- **참고코너(#10)**: ReferenceCornerSection 채점 표면 전부 뒤 유지(31 D-09 invariant 주석 잔존).
- **구 참고 지표 제거(D-12)**: dims.map + DimensionScoreRow/DiagnosisRow/DetailModal + '안정성' 추상 라벨 제거. 관련 dead 임포트·로컬(ScoreDimension/DimensionExplanation/DIMENSION_LABEL_KO/DIMENSION_SUBLABEL_KO/deltaFor/dims/occlusion) 정리.

### Task 2+ — 슬라이더 정렬 지점 표시 (실기기 피드백 #2)

- VideoCompare 오프셋 슬라이더에 자동 추천 오프셋(정렬 활성=0 / legacy=initialOffsetSec) 위치 브랜드 틱 + 스냅 이내 일치 시 "정렬됨" 배지·틱 강조·접근성 라벨. belle "맞춰지는 지점 확인 어려움" 해소.

## Deviations from Plan

### Rule 3 — 블로킹 이슈 자동 처리

**1. [Rule 3] VideoCompare 슬라이더 정렬 지점 표시 (files_modified 밖)**
- **이유**: 32-GATE-DECISIONS 실기기 피드백 #2를 32-11 소관으로 확정. 슬라이더는 VideoCompare 소유라 구현에 VideoCompare.tsx 수정 불가피(플랜 files_modified 밖).
- **처리**: recommendedOffsetSec/recommendedThumpPct/atRecommendedOffset 계산 + 틱/배지/접근성. 토큰만, 기존 슬라이더 로직 무변경(표시 레이어 추가).
- **커밋**: `245761f`

**2. [Rule 3] buildRecordMaps 제네릭 Z 제약 완화**
- **이유**: 실 zoom 계약 `FaultZoomComparison` 이 `recordId` 미보유 → `Z extends ZoomLike`(weak-type)에서 "no properties in common" typecheck 에러.
- **처리**: `Z = ZoomLike` 기본값(제약 제거), 폴백 recordId 조인은 구조적 캐스트. matchZoom 주입 경로가 실 조인 담당이라 무영향. node --test 5건 무회귀.
- **커밋**: `85e16f0`(초기) → `15ec449`(완화)

### 계획된 재량 (deviation 아님 — 플랜 '또는' 선택지)

**3. RecommendedExerciseModal 미수정**
- D-13 "RecommendedExerciseModal 개편 또는 인라인 전환" 중 **인라인 전환** 채택(result.tsx 전면 1개 + 가로 3). 모달은 '전체 보완 운동 보기' 전체 라이브러리 브라우저로 존치 — files_modified 에 있으나 인라인 옵션 선택으로 미변경.

### 미완료 — 블로킹 (SUMMARY 기록, 후속 위임)

**4. [BLOCKED] Pretendard 실제 폰트 로드 (32-07 이월, D-05 남은 절반)**
- **차단 사유 3중**: (a) `expo-font` 미설치 — 패키지 설치는 executor 자동 처리 대상 아님(Rule 3 exclusion), (b) 저장소에 Pretendard 폰트 에셋(.ttf/.otf) 부재 — 바이너리 폰트 파일 생성 불가, (c) expo-font 는 native 모듈 → OTA 불가, **새 EAS build 필요**(이 phase 오디오 native 모듈 제약과 동일).
- **현 상태**: typography.ts 가 `fontFamily`(Pretendard-Regular/Bold) 이름을 정의하나 스타일에 미적용 + 폰트 미로드(시스템 폰트 폴백). 스캐폴딩조차 expo-font import 가 typecheck 실패라 불가.
- **후속**: belle 가 Pretendard 에셋 제공(또는 공식 릴리스 다운로드 승인) + `expo-font` 설치 + **32-12 EAS build**(오디오 native 모듈과 동반)에서 `useFonts` 배선. 이번 worktree 에서 완결 불가.

## Task 3 — 데이터 케이스 렌더 확인 (시뮬레이터) — 32-12 위임

이 worktree(headless git worktree)에서는 RN 시뮬레이터 기동·Firestore 실 doc 접근 불가. 렌더 검증은 **32-12 실기기 6 doc 전수 렌더 게이트**가 담당(오케스트레이터/mcp_tools 지침). 32-12 가 확인할 케이스:

- **신규 계약 실 doc**(32-09 스윕 산출 — recordId·3단 문구·미션·summaryPraise 보유): `users/phase25eval/analyses/{powerspin,peterpan,elbowtwistsister,pdshape,kipup}{Fault,Correct}1784636486`
- **mode3 연쇄**: `users/phase32emit/analyses/{chainfault1,chainfault2,chaincorrect1,chaincorrect2}1784641056`
- **streak-3 (coach_card + coachQuestions 보유)**: `users/phase32emitb/analyses/streak31784642411`
- **데이터 케이스 5종**: (1) 신규 계약 실 doc, (2) 정상 mode1 감점 다수, (3) 감점 0(isCleanPass 축하), (4) legacy doc(3단 문구·미션 부재 폴백 크래시 0), (5) mode3(missionOutcome 표시)
- **6동작 전수 렌더**(D-23 UI 적용, kip-up 편중 금지): 위 6동작 Fault/Correct doc 각 진입·크래시 0·요약 카드 성립.

**이번 플랜의 정적 근거(worktree 내 가능분)**:
- `deriveResultSections` legacy 테스트(hasPhrases=false → 전 섹션 계산, topFix legacy 표식) — 부분 계산 크래시 0 (T-32-25 완화).
- 컴포넌트 폴백: SummaryCard(praise null → 정직 고지), DeductionCard(statusLine/cueLine/zoom 부재 graceful), 심사 시뮬레이션(records 없으면 미렌더).
- `tsc --noEmit` 0 (main-repo node_modules 심볼릭 링크 하니스 — 커밋 안 함).

OTA 발행은 이 플랜에서 하지 않음(32-12 마감에서 오디오·실패 UX·폰트 native build 포함 후 일괄).

## Known Stubs

없음 — 신규 렌더는 전부 실 doc 필드 소비 + 부재 시 정직 폴백(하드코딩 빈 데이터가 UI 로 흐르는 스텁 0). frontExercise 부재 시 neutral 카피는 의도된 graceful(스텁 아님).

## Threat Flags

없음 — 변경은 전부 기존 doc 필드의 UI 렌더 재배치. 신규 네트워크 엔드포인트·인증 경로·파일 접근·스키마 변경 0. 위협 레지스터 T-32-25(legacy 크래시)·T-32-26(요약 헤드라인 신뢰)·T-32-27(31 결정 위반)은 mitigate 반영(resultSections legacy 테스트 + summaryPraise 단일 원천 + 참고코너 뒤 배치·31 D-09 주석 잔존).

## Verification

- `node --test resultSections.test.ts` → 5 GREEN ✓
- 기존 lib 테스트 무회귀(summarySource/cueTrack/manualOffset/gaugeGeometry/visualCards) → 54 pass ✓
- `cd app && tsc --noEmit` → 0 errors ✓
- D-02 섹션 순서 JSX 확인: SummaryCard 첫 콘텐츠 → InjuryRisk → top-1 DeductionCard → 동작 비교(cueWindows) → 다른 감점 → 성장 → 보완 운동 → 강사 질문 → 심사 정보 → 참고코너 ✓
- '안정성' 사용자 문자열 리터럴 제거(주석만 잔존) ✓
- STATE.md/ROADMAP.md 무접촉(orchestrator 소관) ✓

## Self-Check: PASSED

- FOUND: app/src/lib/resultSections.ts
- FOUND: app/src/lib/__tests__/resultSections.test.ts
- FOUND (modified): app/src/app/analysis/result.tsx (3,194줄, min_lines 2000 충족)
- FOUND (modified): app/src/components/VideoCompare.tsx
- FOUND: .planning/phases/32-result-readability-3-omni/32-11-SUMMARY.md
- FOUND commits: f6f1c8b(test RED) / 85e16f0(GREEN) / 15ec449(top) / 776351e(bottom) / 245761f(align)
- TDD gate: test(...) 커밋 f6f1c8b 이 feat(...) 커밋들보다 선행 — RED→GREEN 게이트 준수
- 파일 삭제 0 (전 커밋 add/modify만)

---
*Phase: 32-result-readability-3-omni*
*Completed: 2026-07-22*
