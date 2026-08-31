---
phase: quick-260831-lcc
plan: 01
subsystem: app-result-screen
tags: [result-restructure, red-discipline, empty-state, copy-fix, version-bump]
requires: []
provides:
  - "결과 화면 요약 우선 재배열 (옥타곤 최상단 + 발견 1곳 완결)"
  - "본문 빨강 규율 (highlightNumbers 중립화 + 카드 4종 중립화)"
  - "빈 상태 미렌더 규칙 (growth/exercise — resultSections 단일 지점)"
  - "'없음' 삽입 버그 단일 지점 소독 (sanitizeFinding)"
  - "app version 1.2.0 (runtimeVersion 가르기)"
affects: [app/src/app/analysis/result.tsx 소비 화면 전체]
tech-stack:
  added: []
  patterns: ["표시 레이어 폴백 강등 (백엔드 데이터 무변형)", "렌더 전용 면책 접기"]
key-files:
  created: []
  modified:
    - app/src/app/analysis/result.tsx
    - app/src/components/SummaryCard.tsx
    - app/src/components/DeductionCard.tsx
    - app/src/components/PartChipsRow.tsx
    - app/src/lib/resultSections.ts
    - app/src/lib/__tests__/resultSections.test.ts
    - app/src/app/(tabs)/profile.tsx
    - app/app.json
decisions:
  - "belle 2026-08-31 결과 화면 재구성 승인(요약 우선) — 구 D-01/D-09 배치 결정 대체, 수치 규율 자체는 유지 (코드 주석에 명기)"
  - "scoringBasisLabel 헤더 렌더는 isScoreSuppressed 경로만 (플랜 명시 게이트 — TRUST-03 잔존)"
  - "hasExercise 의미 = 개인화 전면 운동 존재 (라이브러리 OR 제거)"
metrics:
  duration: "약 16분 (06:32Z ~ 06:48Z)"
  completed: "2026-08-31"
  tasks: 3
  commits: 3
  tests: "typecheck 0 에러 / node --test 208 pass 0 fail (신규 Test 7 포함)"
---

# Quick 260831-lcc: 결과 화면 재구성 (요약 우선 · 발견 1곳 · 빨강 규율) Summary

**One-liner:** 옥타곤 점수를 첫 화면으로 올리고 발견(headline·설명·목표 문단)의 복제 4면을 감점 카드 1곳으로 수렴, highlightNumbers 의 본문 빨강 기계 원인을 제거하고 '없음' 삽입 카피를 sanitizeFinding 단일 지점에서 소독 — 정보 손실 0 감사표 동반, v1.2.0 범프 (OTA 미발행).

## Commits

| Task | Commit | 내용 |
|------|--------|------|
| 1 | 643d7fd2 | 재배열 + 발견 중복 제거 (옥타곤 상단·refCard 하향·SummaryCard 다이어트·'없음' 소독·veto 카드 해체·심사 레이아웃 수리·질문 dedup) |
| 2 | 6f584524 | 빨강 규율 + 빈 상태 미렌더 + profile 카피 + v1.2.0 |
| 3 | cbc89ef9 | 코칭 팁 반복 면책 접기 (말미 문장 2건+ 시 통합 1줄) |

## Task 1 — 재배열 + 발견 중복 제거

- 옥타곤 점수 카드(점수+등급+한줄평+ScoreContext+발견 1줄)를 header 직후 첫 카드로 이동. scoreCaption 은 카드에서 제거(Task 2 에서 하단 면책에 병합). `anchor:scoreGauge` onLayout 은 소비처가 사라져 제거 — '자세히 보기' 앵커 1순위 = `anchor:scoreBreakdown` (summaryCard 앵커는 F-7 그대로 1순위 유지).
- 상단 참고 3줄 → 1줄: scoringBasisLabel 은 isScoreSuppressed 경로만 렌더. coachPositioning("이 분석은 강사 지도를 돕는 참고예요")이 상단 유일 면책.
- refCard 를 '다른 감점 항목' 뒤(구 옥타곤 자리)로 하향 + refNote 제거.
- SummaryCard: score 배지·nextAction cuePill 제거 (props·스타일 동기 삭제, summarySource 조립은 무접촉). praiseHeadline·todayHeadline 에 `lineBreakStrategyIOS="hangul-word"`.
- `sanitizeFinding` 헬퍼 신설 — vetoPrimaryFault 파생 + correctionPoint 의 tips[0].title 에 적용. "없음 보완하면 더 올라가요"/"먼저 교정할 점: 없음"/"AI 발견한 점: 없음" 3면 동시 수리.
- '먼저 교정할 점' veto 카드 해체 — 고유분 rootCauseHypotheses('가능한 원인')만 topFix DeductionCard 직하 중립 카드로 이동 (topFix 미렌더 경로에서 함께 미렌더). vetoFixTip memo·vetoLeadNote 제거.
- 심사 시뮬레이션: judgeRow fault = criterionLabelKo 짧은 항목명 단독, whyLine Text 제거 (행 탭 → 시트 도달 경로 보존). judgeRow/judgeTotalRow 에 `alignSelf:'stretch'` — styles.card 의 `alignItems:'center'` 수축이 "심사 환산 점수80점" 붙음의 실측 원인 (before-screens/12).
- 강사 질문 dedup(displayCoachQuestions): 같은 recordId 첫 1개, generic(무 recordId) 텍스트 일치 제거 후 최대 1개, source 'user' 무필터. 수집 원본 무변형.

## Task 2 — 빨강 규율 + 빈 상태 + 카피/버전

- highlightNumbers(본문 수치 스팬): `colors.brand` → `colors.textPrimary` + fontWeight 600 유지 — 본문 빨강의 기계 원인 제거.
- 중립화: refCard(brandTint→cardBg, brand→divider, refAthlete→textPrimary, refLevel→softBg+textMid) / growth coachCard 가지(vetoLeadCard→coachCard, 아이콘 brand 유지) / detourCard(→softBg, headline→textPrimary) / DeductionCard cueBox(brandTint→softBg, askBtn CTA 유지) / PartChipsRow 참고 칩(advisoryOrange→divider 점선+textSecondary).
- **잔존 brand 허용처 (grep 전수 판정):** scoreDelta(활성 상승)·gradeBadge(점수 배지)·partScore/exerciseSets/tipAngle/judgeDeduction(수치)·trackFill(게이지)·tipAngleCue/tipIndex(행동 큐·번호 배지)·tipMore/dimMore/coverageTip/alignUpsellCta/cta/link(CTA)·Ionicons 아이콘 2곳·cleanPassCard 계열(무접촉 지시). 본문 문단 텍스트 brand = 0.
- 빈 상태 규칙(resultSections.ts): growth visible = mode3 && (coach_card || hasMissionOutcome) / exercise visible = hasExercise === true (의미 = frontExercise 존재, result.tsx 호출부 동기 수정 + CORRECTIVE_LIBRARY_HAS_ITEMS 소비 제거). 도달 불가해진 빈 안내문·"매핑이 없어요" 가지 제거. Test 7 신설 (정당화 주석 동반).
- JUDGE_SIM_DISCLAIMER 에 scoreCaption 의미 병합 (두 승인 문장 접합).
- profile.tsx: "로그인·결제·알림 설정은…" → "결제·알림 설정은…" (Phase 36 로그인 구현과 모순 해소).
- app.json version 1.1.0 → 1.2.0 (runtimeVersion policy appVersion — 구 런타임 OTA 유출 방지 안전판). **OTA 미발행.**

## Task 3 — 팁 반복 면책 접기

- tip.detail 말미 문장이 "강사와"+"확인/권고" 패턴인 팁이 2개 이상이면 각 팁 렌더에서 말미 문장을 잘라내고 섹션 말미 통합 1줄("정확한 자세는 강사와 함께 영상으로 확인해보세요." — textSecondary)로 표시. 백엔드 원문(doc) 무변형 — 렌더 접기만. 패턴 미매치/1개뿐/단일 문장 detail 은 원문 그대로 (무회귀). 해당 문장은 백엔드 생성임을 플래너 grep 으로 확인(app 코드에 원문 없음) — 표시 레이어 범위 처리.

## 정보 손실 0 자가 감사표 (제거물 → 잔존 경로, grep 실측)

| # | 제거물 | 성격 | 잔존 경로 (grep 실측 라인) |
|---|--------|------|---------------------------|
| 1 | refNote "기준 모션은 하나의 참고일 뿐이에요" | 면책 복제 | coachPositioning "이 분석은 강사 지도를 돕는 참고예요" (result.tsx:2417) |
| 2 | 헤더 scoringBasisLabel (비억제 doc) | 복제 | breakdownBasisLine=composeScoringBasisKo (result.tsx:1272→3096, "세계챔피언 정은지 선수 시연 대비 편차…" deductionLabels.ts:209-226 실측) + header sub "…기준으로 분석했어요" (result.tsx:2377). 억제 doc 은 헤더 렌더 유지 |
| 3 | scoreCaption "100점은 잘 나오지 않아요…" | 면책 통합 | JUDGE_SIM_DISCLAIMER 병합본 (result.tsx:185) |
| 4 | veto 카드 headline (vetoPrimaryFault 재출현) | 복제 | DeductionCard statusLine (DeductionCard.tsx:41,100) + 옥타곤 카드 "AI 영상 분석에서 발견한 점" 줄 (result.tsx:2452) |
| 5 | vetoFixTip "이렇게 교정해 보세요" 줄 | 복제 (tip.detail verbatim) | 코칭 팁 본문 렌더 (result.tsx:3205) |
| 6 | SummaryCard cuePill (nextAction) | 복제 (cueBox verbatim — before-screens/07 실증) | DeductionCard cueBox record.cueLine (DeductionCard.tsx:253-255) |
| 7 | SummaryCard 점수 배지 | 복제 | 옥타곤 카드 OctagonScore (result.tsx:2430 — 요약 카드 바로 위) |
| 8 | judge whyLine | 복제 | DeductionCard whyLine (DeductionCard.tsx:42,149) + 행 탭 → 드릴다운 시트 (result.tsx:3438 setDetailRecordIndex) |
| 9 | growth 빈 안내문 ("이어갈 지난 미션이 없어요" 등) | '없음' 빈 카드 | mode3-first 안내 "다음 분석부터 이전 영상과 비교해 발전을 확인해 드려요" (result.tsx:2955) |
| 10 | 팁 말미 반복 면책 (2건+ 시) | 복제 (렌더 접기, 원문 무변형) | 통합 1줄 (result.tsx:3227) |

잔존 경로가 실재하지 않는 항목: 0건 (되돌림 불요).

## must_haves 코드 레벨 판정 (9/9)

1. 첫 화면 옥타곤+등급+한줄평 → 바로 아래 요약 카드: JSX 순서 header→옥타곤→SummaryCard 성립
2. 발견 완결 렌더 1곳: veto 카드 해체 + judge 짧은 항목명 (옥타곤 발견 1줄·ScoreContext 교정 포인트는 플랜 지시로 동반 이동 유지 — 요약이지 완결 문단 아님)
3. 목표 문단 1회: cuePill 제거 → cueBox 유일본
4. 면책 = 상단 1줄 + 심사 하단 1개 + 참고코너: refNote·vetoLeadNote·scoreCaption 제거/병합
5. '없음' 삽입 카피 0: sanitizeFinding 3면 소독
6. '없음' 성장/보완 미렌더: resultSections 가시성 규칙 + Test 7
7. 본문 브랜드색 0: highlightNumbers 중립화 + 카드 4종
8. 심사 환산 점수 라벨 좌/값 우: alignSelf stretch (수축 원인 제거)
9. 정보 손실 0: 위 감사표

## Deviations from Plan

### Auto-fixed / 재량 조정

**1. [Rule 1 - 정합] PartChipsRow 헤더 주석 스테일 정정**
- **Found during:** Task 2 (advisoryOrange 제거 후)
- **Issue:** 파일 헤더 주석이 "구분은 advisoryOrange 색이 담당" 등 제거된 동작을 서술 — 다음 세션 오독 위험
- **Fix:** 주석 2곳을 새 중립 톤 서술로 정정
- **Commit:** 6f584524

**2. [재량] anchor:scoreGauge onLayout 제거**
- 플랜은 "onLayout 동반 이동"을 명시했으나 앵커 1순위 교체(scoreBreakdown) 후 소비처 0 — 죽은 기록이라 제거. pickExpandAnchorY 폴백 체인은 summaryCard→scoreBreakdown 으로 유효.

**3. [재량] node --test 디렉터리 인자 형태**
- `node --test src/lib/__tests__/` 디렉터리 인자가 Node 24.15 에서 MODULE_NOT_FOUND — glob(`*.test.ts *.test.mjs`)으로 실행. 결과 동일 범위 (208 tests).

그 외 플랜 그대로 실행.

## 검증 결과

- `cd app && npm run typecheck` — 0 에러
- `node --test src/lib/__tests__/*.test.ts src/lib/__tests__/*.test.mjs` — **208 pass / 0 fail** (기준선 201 계열 + 이후 quick 추가분 + 신규 Test 7. 기대값 변경 아님 — 신규 케이스만 추가, 정당화 주석 동반)
- grep 게이트: scoreCaption 실사용 0 / SummaryCard nextAction 0 / 본문 brand 0 / advisoryOrange 참고 칩 0 / profile "로그인" MVP 문구 0 / version 1.2.0
- 동작 비교 섹션(블록 7) 내부 diff 0 (VideoCompare/RenderedComparePlayer/큐·오버레이 props 변경 0 — git diff 638c1628..HEAD grep 실측)
- ScoreBreakdownSection 수치 행 무필터·백엔드/contract 무접촉·cleanPassCard 무접촉

## Known Stubs

없음 — 이번 변경에 하드코딩 빈 값·placeholder·미배선 컴포넌트 신설 없음. 도달 불가 가지는 렌더에서 제거함.

## Threat Flags

없음 — 신규 네트워크/auth/파일 접근/스키마 표면 0. 신규 패키지 0 (T-lcc-SC 정합).

## ★ 오케스트레이터 후속 (실행자 스코프 밖)

- **시뮬레이터 눈검증 미수행** — before-screens/07~13 vs after 스크린샷 비교를 오케스트레이터가 수행할 것 (memory: verify-ui-on-simulator-before-ota — typecheck 는 렌더 크래시를 못 잡는다).
- **OTA 발행 금지** — version 1.2.0 은 새 빌드 전용 (구 런타임에 구조 변경분 유출 방지가 범프의 목적).
- 잔여 관찰 1건: mode3 `prev_plus_reference_free` 비억제 doc 은 헤더 scoringBasisLabel 이 사라짐 — 플랜 명시 게이트(isScoreSuppressed 만) 준수 결과. 해당 doc 의 한계 정보는 mode3 한계 고지 + breakdown basisLine 경로가 커버하나, 시뮬 비교 시 mode3 화면도 한 번 볼 것.

## Self-Check: PASSED

- 파일 실재 5/5 (SUMMARY, result.tsx, SummaryCard.tsx, resultSections.ts, app.json)
- 커밋 실재 3/3 (643d7fd2, 6f584524, cbc89ef9)
- 최종 게이트: typecheck 0 에러 / node --test 208 pass 0 fail
