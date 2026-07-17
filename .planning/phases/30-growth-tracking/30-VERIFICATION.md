---
phase: 30-growth-tracking
verified: 2026-07-17T00:00:00Z
status: passed
score: 28/28 must-haves verified
overrides_applied: 0
human_verification_note: >
  실기기 확인 7항목 + Pod 재가동 확인 4항목은 batch-UAT 원칙에 따라
  30-HUMAN-UAT.md 에 기적립됨 (즉시 belle 호출 금지, /gsd-audit-uat 일괄 —
  [[batch-uat-after-phase-31]], Phase 29 verification 선례 동일). 본 검증의
  human_needed 사유가 전부 그 문서에 있으므로 규칙에 따라 status=passed.
---

# Phase 30: 성장 추적 개선 — 평균 기반·동작별 막대 Verification Report

**Phase Goal:** 성장 그래프를 실증 피드백대로 재설계 (시나리오 5). E1: raw 점수 나열 → 평균값 기반. E2: 동작별 상승/하락률 막대(주식창식) — mode3-progress-not-similarity(발전≠일치, %일치 헤드라인 금지) 원칙 정합 확인 필수. 지적 단위 세션간 개선 추적은 이후 단계로 유지.
**Verified:** 2026-07-17
**Status:** passed (실기기·Pod 항목은 30-HUMAN-UAT.md 배치 적립)
**Re-verification:** No — initial verification

## Goal Achievement

E1(raw 나열→주별 평균)과 E2(동작별 ▲▼ 포인트 리스트)가 데이터 계층(30-01 순수 selector) → 백엔드 계약(30-02 recognizedMotionId 적립) → 컴포넌트(30-03) → 홈 카드 배선(30-04)까지 코드 실측으로 관통 확인됨. 스코프 밖 항목(fault_category 세션간 추적)은 goal 원문대로 미착수 유지 — selector·컴포넌트 어디에도 신뢰구간/fault 매칭 코드 없음(스코프 준수 확인).

**invariant 정합 (goal 필수 확인 항목):** 증감은 전부 '점수 포인트 델타'(`+N점`/`−N점`) — `growthSelectors.ts`·`GrowthMotionBars.tsx` 파일 전체 '%' 문자 0건 실측(모듈로 연산자 포함 금지 게이트 통과), 등락률·%일치 헤드라인 코드 경로 부재. overallScore만 소비, angle 유사도·deltaFromPrevious 미소비(`mode3-overall-exclude-angle-similarity` 정합, 파일 헤더 :9-12 박제).

### Observable Truths — 30-01 데이터 계층 (8/8)

| # | Truth | Status | Evidence (코드 실측 — SUMMARY 주장 아님) |
|---|-------|--------|------|
| 1 | weeklyAverages 주별 평균, 빈 주 건너뜀 (D-01) | ✓ VERIFIED | `growthSelectors.ts:88-119` Map 버킷 — 존재하는 주만 요소 생성(0점 채움 없음), weekStart 오름차순. 시맨틱 테스트 실행 exit 0 |
| 2 | mode1/mode3 분리 집계, 혼합 경로 없음 (D-02) | ✓ VERIFIED | `:110-119` mode 인자 + `hasUsableGrowthScore(doc, mode)` 단일 관문(:70 `doc.mode !== mode` 배제). 혼합 평균 함수 자체가 없음 |
| 3 | defaultGrowthMode 마지막 모드 + 폴백 + null (D-03) | ✓ VERIFIED | `:127-138` `analyses[0]?.mode` 우선 → 주별 점 <2면 타 모드 → 양쪽 <2면 null |
| 4 | motionDeltas point 델타, 활동 주 1개=null (D-05) | ✓ VERIFIED | `:176-179` `Math.round(latest.rawAvg - prev.rawAvg)`, prev 없으면 null |
| 5 | scoreSuppressed 제외 — 평균·델타·기본모드 전부 (HIGH-1) | ✓ VERIFIED | `:74` predicate 단일 관문, 세 selector 전부 경유(:114/:148/:135). `assert-growth-selectors.mjs` 28 assert 중 suppressed 제외 케이스 7 매치 — 직접 실행 통과 |
| 6 | legacy 필터 부재 (D-07) | ✓ VERIFIED | property 접근 grep(`phaseId\|milestone\|createdAt<\|scoringBasis비교\|version`) 0건, 헤더 :14-18 D-07 박제 |
| 7 | declineBlue 토큰 + D-06 근거 주석 (D-06) | ✓ VERIFIED | `colors.ts:90` `declineBlue: '#006FFD'`(highlight alias) + :85-88 D-06 주석, brand #FF4B33 무변경 |
| 8 | 시맨틱 테스트가 핵심 규칙 잠금 (HIGH-2) | ✓ VERIFIED | `assert-growth-selectors.mjs` 161줄, assert 28건 — **검증자 직접 실행: "growth-selectors semantic checks passed" exit 0** |

### Observable Truths — 30-02 백엔드 계약 (6/6)

| # | Truth | Status | Evidence |
|---|-------|--------|------|
| 9 | mode3 인식 성공 시 recognizedMotionId/Name 저장, first 포함 (HIGH-3) | ✓ VERIFIED | `assemble.py:695-696` emit이 early return **앞** 배치. `test_assemble.py:120-131` is_first=True emit 테스트 통과 |
| 10 | first·progress 파이프라인 경로 pytest 증명 (HIGH-3) | ✓ VERIFIED | `test_pipeline_mode3.py:99-118` motion_id="ref-foo" 픽스처로 양 경로 assert — **검증자 직접 실행: 53 passed** |
| 11 | motion_id None → 키 미추가, legacy 동형 (backward-compat) | ✓ VERIFIED | `test_pipeline_mode3.py:125-129` negative test + 기존 exact-dict assert 무수정 통과 |
| 12 | 3-way lockstep 동시 갱신 (D-04) | ✓ VERIFIED | `analysis.ts:280` + `models.py:69-77` + `contract.md:438-441` 3곳 전부 매치 |
| 13 | comparison 내부 scalar string — validator 무접촉 | ✓ VERIFIED | `firestore_admin.py` recognizedMotionId 매치 0건 (무변경) |
| 14 | 채점 로직 무접촉 (phase 불변 경계) | ✓ VERIFIED | pipeline diff = `recognized_motion_id=profile.motion_id` kwarg 2곳(grep -c = 2)뿐, 채점 산출 라인 무접촉 (30-REVIEW 전체 diff 검토 교차 확증) |

### Observable Truths — 30-03 컴포넌트 (7/7)

| # | Truth | Status | Evidence |
|---|-------|--------|------|
| 15 | GrowthChart = WeeklyPoint[] 주별 평균 꺾은선 (D-01, E1) | ✓ VERIFIED | `GrowthChart.tsx:30` `{ points: WeeklyPoint[] }`, `scores: number[]` 0건, y소스 = p.avg(:42), 주 시작일 라벨 'M/D주'(:51-54) |
| 16 | GrowthMotionBars 통합 리스트 + 배지 구분 (D-04 i, D-09) | ✓ VERIFIED | `GrowthMotionBars.tsx:71-105` rows 전량 렌더, row.badge('프로 비교'/'내 기록') 배지 |
| 17 | '+N점'/'−N점' 포인트 표기, '%' 0건 (D-05, invariant) | ✓ VERIFIED | `:48` `▲ +${delta}점` / `:58` `▼ −${mag}점`, 파일 전체 % 0건 |
| 18 | 임계 없음, ▲=brand / ▼=declineBlue (D-06) | ✓ VERIFIED | `:36` deltaVisual 부호로만 분기(필터·숨김 없음), :51 colors.brand / :60 colors.declineBlue, progressGreen/Red 0건 |
| 19 | 첫 기록 표시 "첫 기록 N점 (비교 전)" (D-05) | ✓ VERIFIED | `:41` delta===null 분기 정확 카피 |
| 20 | 하드코딩 0 — 테마 토큰만 | ✓ VERIFIED | 두 컴포넌트 hex 0건 (BAR_UNIT 등은 기하 상수 — GrowthChart W/H 선례 동일) |
| 21 | 잠정 배선 TODO(30-04-PLAN.md) 계약 | ✓ VERIFIED (이행 후 소거) | 30-04가 계약대로 교체 — 현재 `TODO(30-04` 0건 (truth 27과 동일 증거) |

### Observable Truths — 30-04 홈 카드 배선 (7/7)

| # | Truth | Status | Evidence |
|---|-------|--------|------|
| 22 | [추이]/[동작별] 탭 + GROWTH_CARD_CONTENT_HEIGHT 단일 상수 공유 (D-08, MEDIUM-1) | ✓ VERIFIED | `index.tsx:326` 상수 정의(=152), :602 growthBody minHeight + :615 growthLocked minHeight 공유 (4 매치) |
| 23 | [추이] 모드 토글 + 선택 모드 주별 평균만 렌더 (D-02) | ✓ VERIFIED | `:398` `view === 'trend' &&` 조건부 모드 토글, `:380` `weeklyAverages(analyses, effectiveMode)` 단일 모드 피드 |
| 24 | 기본값 = defaultGrowthMode + 활성 탭 브랜드색 (D-03) | ✓ VERIFIED | `:377` `modeOverride ?? baseMode` 파생(stale 회피), `:597` toggleTabSelected = brandTint bg + brand border, a11y 세트(:350-353 Role/State/Label+hitSlop) |
| 25 | [동작별] 모드 토글 숨김 + GrowthMotionBars 렌더 (D-09) | ✓ VERIFIED | 모드 토글은 :398 trend 분기 내부에만 존재, `:420` byMotion에서 `<GrowthMotionBars rows={motionRows} />` (slice(0,4) 상한, 재계산 없음) |
| 26 | "이번주 성장 그래프" 라벨 정정 (D-01) | ✓ VERIFIED | 구 라벨 0건, `:390` "주별 평균 성장 그래프" |
| 27 | locked 게이트 = defaultGrowthMode null + 주별 기준 카피 (D-03 null) | ✓ VERIFIED | `:91` growthBaseMode useMemo → `:219` null 분기 렌더 게이트, `:435-437` "서로 다른 주에 분석을 2번 이상 하면" 카피 정정 |
| 28 | 잠정 배선·TODO 완전 소거 | ✓ VERIFIED | `TODO(30-04` 0건, `?? 'mode3'`는 부모 게이트 통과 후 타입 보증용 잔존(:374-377 주석 근거) — 잠정 배선 아님 |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/src/lib/growthSelectors.ts` | 순수 selector 5 export, min 90줄 | ✓ VERIFIED | 188줄, 5 함수 + 2 인터페이스 export, react/firebase import 0 |
| `app/src/theme/colors.ts` | declineBlue | ✓ VERIFIED | :90, D-06 주석 |
| `app/scripts/assert-growth-selectors.mjs` | 시맨틱 테스트, min 60줄 | ✓ VERIFIED | 161줄, assert 28건, 실행 통과 |
| `app/src/components/GrowthChart.tsx` | WeeklyPoint 꺾은선, min 60줄 | ✓ VERIFIED | 116줄 |
| `app/src/components/GrowthMotionBars.tsx` | ▲▼ 델타 리스트, min 60줄 | ✓ VERIFIED | 146줄, named export |
| `app/src/app/(tabs)/index.tsx` | 2층 토글 + 배선 | ✓ VERIFIED | GrowthToggle/GrowthCard/GrowthLockedCard 재작업 |
| `app/src/types/analysis.ts` | recognizedMotionId? optional | ✓ VERIFIED | :280 |
| `backend/.../assemble.py` | recognized kwargs, None→미추가 | ✓ VERIFIED | :648/:675(ValueError)/:695-696 |
| `backend/functions/pipeline/app.py` | 양 분기 배선 | ✓ VERIFIED | grep -c = 2 |
| `docs/contract.md` | 신규 필드 서술 + legacy 폴백 | ✓ VERIFIED | :438-441 |
| `backend/tests/test_assemble.py` | emit/미emit/ValueError | ✓ VERIFIED | :120-140+ 통과 |
| `backend/tests/test_pipeline_mode3.py` | ref-foo first·progress | ✓ VERIFIED | :99-129 통과 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| growthSelectors.ts | analysis.ts | import type | ✓ WIRED | :19 `import type { AnalysisDoc, AnalysisMode }` |
| GrowthChart.tsx | growthSelectors.ts | WeeklyPoint | ✓ WIRED | :11 import type |
| GrowthMotionBars.tsx | growthSelectors.ts | MotionDeltaRow | ✓ WIRED | :2 import type |
| GrowthMotionBars.tsx | theme | declineBlue/brand | ✓ WIRED | :51/:60 사용 |
| index.tsx | GrowthMotionBars | [동작별] 렌더 | ✓ WIRED | :13 import + :420 렌더 (30-03 고아 해소) |
| index.tsx | growthSelectors | 3 selector 호출 | ✓ WIRED | :16-18 import, :91/:376/:380/:384 호출 |
| index.tsx | GrowthChart | points 렌더 | ✓ WIRED | :411 |
| pipeline app.py | assemble.py | recognized kwargs 2곳 | ✓ WIRED | `recognized_motion_id=profile.motion_id` = 2 |
| assemble.py | contract.md | lockstep 상호 인용 | ✓ WIRED | docstring :664 + contract.md :441 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| GrowthCard | analyses | `useMyAnalyses({doneOnly})` Firestore onSnapshot (기존 구독) | Yes | ✓ FLOWING |
| GrowthChart | trendPoints | `weeklyAverages(analyses, effectiveMode)` useMemo :380 | Yes (실집계, 하드코딩 없음) | ✓ FLOWING |
| GrowthMotionBars | motionRows | `motionDeltas(analyses).slice(0,4)` useMemo :384 | Yes | ✓ FLOWING |
| Firestore comparison | recognizedMotionId | `_mode3_comparison` → build_mode3 → complete_analysis 기존 저장 경로 | Yes (Pod 재가동 후 실효 — HUMAN-UAT 항목) | ✓ FLOWING (코드 경로) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 앱 타입 정합 | `cd app && npm run typecheck` | exit 0 | ✓ PASS |
| selector 시맨틱 (28 assert) | `node --experimental-strip-types scripts/assert-growth-selectors.mjs` | "growth-selectors semantic checks passed" exit 0 | ✓ PASS |
| 백엔드 계약 테스트 | `pytest backend/tests/test_assemble.py backend/tests/test_pipeline_mode3.py -q` | 53 passed | ✓ PASS |
| production OTA 발행 (30-04 이월분) | `npx eas-cli update:list --branch production --limit 2` | 최신 = "phase 30: growth card weekly avg + per-motion deltas", Group 9806274f, ios+android | ✓ PASS |

참고: 전체 백엔드 스위트의 41건 실패는 pre-phase base 8d3cd3f와 동일한 선재 실패(Gemini/env 의존) — phase 30 회귀 아님 (오케스트레이터 확증 + 30-REVIEW 교차).

### Probe Execution

프로젝트 관례 probe(`scripts/*/tests/probe-*.sh`) 해당 없음 — 이 phase의 실행 가능 검증은 위 스팟체크 3종(시맨틱 assert + pytest + typecheck)이 본체이며 전부 검증자 프로세스에서 직접 실행함.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| E1 (PILOT-FEEDBACK §E) | 30-01/03/04 | raw 점수 나열 → 평균값 기반 | ✓ SATISFIED | weeklyAverages + GrowthChart points + 홈 [추이] 배선 |
| E2 (PILOT-FEEDBACK §E) | 30-01/02/03/04 | 동작별 상승/하락 막대(주식창식) | ✓ SATISFIED | motionDeltas + GrowthMotionBars + [동작별] 탭 + recognizedMotionId 적립 |

**주:** ROADMAP Phase 30 `Requirements: TBD` — REQUIREMENTS.md에 Phase 30 매핑 ID가 없어 ORPHANED 요구사항 0건. 플랜의 E1/E2는 PILOT-FEEDBACK-2026-07-06 §E 항목 ID(플랜 frontmatter 주석에 명시)로, REQUIREMENTS.md 계보가 아님 — 전 플랜 일관 선언, 누락 없음.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (12개 phase 수정 파일 전수 스캔) | — | TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER 0건 | — | 30-03의 TODO(30-04) 잠정 주석도 30-04가 계약대로 소거 완료 |

### Human Verification Required

전부 **30-HUMAN-UAT.md에 기적립** (batch UAT 원칙 — 즉시 호출 금지, `/gsd-audit-uat` 일괄):

1. **실기기 7항목** (30-04 적립): 탭 전환 높이 불변·활성 탭 브랜드색(D-08/D-03), 모드 토글 기본값 폴백(D-03), 주별 평균 선+주 라벨(D-01), 배지·▲▼색·포인트 표기·첫 기록(D-05/D-06/D-09), [동작별] 모드 토글 미노출(D-09), locked 카피(D-03 null), 명시 선택 모드 데이터 부족 안내
2. **Pod 재가동 후 4항목** (30-02 적립): git pull 반영, mode3 실분석 recognizedMotionId 저장, 인식 실패 시 키 부재, (선택) SAM 재배포 UPDATE_COMPLETE

### Observations (advisory — 차단 아님)

- **SAM 배포 보류 (30-02 Task 3):** `sam deploy`가 CloudFormation EarlyValidation 훅에서 실패(선존 인프라 요인, 코드 무관) — 플랜의 명시된 graceful 분기("배포 불가 시 deviation+UAT 기록, 둘 중 하나 충족")를 정확히 이행. Pod OFF라 production 회귀 0. 재시도 명령 박제됨.
- **30-REVIEW Warning 4건(WR-01~04) + Info 3건(IN-01~03):** Critical 0. WR-01(홈 헤더 NaN/suppressed 유입), WR-02(추이 주 수 무상한 라벨 겹침), WR-03(malformed mode1 → '내 기록' 합산), WR-04(recognized ValueError blast radius)는 must-have 위반이 아닌 개선 후보 — Phase 29 선례대로 quick 후보로 이월 권장.

### Gaps Summary

없음 — 28/28 must-haves 코드 실측 검증. E1/E2가 데이터→계약→컴포넌트→홈 노출까지 관통하고, %일치 invariant 게이트(파일 전체 % 0건)와 스코프 경계(fault_category 추적 미착수, 채점 무접촉)가 전부 준수됨. OTA는 검증자가 EAS에서 독립 확인(Group 9806274f).

---

_Verified: 2026-07-17_
_Verifier: Claude (gsd-verifier)_
