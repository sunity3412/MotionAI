---
phase: quick-260831-lcc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/src/app/analysis/result.tsx
  - app/src/components/SummaryCard.tsx
  - app/src/components/DeductionCard.tsx
  - app/src/components/PartChipsRow.tsx
  - app/src/lib/resultSections.ts
  - app/src/lib/__tests__/resultSections.test.ts
  - app/src/app/(tabs)/profile.tsx
  - app/app.json
autonomous: true
requirements: [BELLE-0831-RESULT-RESTRUCTURE]
must_haves:
  truths:
    - "결과 화면 첫 화면(스크롤 0)에 옥타곤 점수+등급+한줄평이 보이고, 바로 아래 '오늘 고칠 것' 요약 카드가 온다"
    - "한 발견(예: 왼쪽 어깨)의 headline·설명 문단이 화면 전체에서 감점 카드 1곳에만 완결 렌더되고, 다른 곳은 짧은 항목명/요약만"
    - "'목표는 한쪽 무릎은…' 목표 문단이 화면에 정확히 1회만 나타난다 (감점 카드 cueBox)"
    - "면책 문구는 상단 1줄 + 심사 카드 하단 1개(+참고코너 '점수에는 들어가지 않아요' 유지)만 남는다"
    - "'없음'이 문장에 삽입된 카피('없음 보완하면…', '먼저 교정할 점: 없음')가 어떤 doc 에서도 나오지 않는다"
    - "내용이 '없음'인 성장/보완 운동 섹션은 렌더되지 않는다"
    - "본문 문단 텍스트에 브랜드색(#FF4B33)이 없다 — 브랜드색은 점수·감점 수치·주 CTA·활성 상태만"
    - "'심사 환산 점수'와 점수가 붙어 보이지 않는다 (라벨 좌 / 값 우)"
    - "정보 손실 0 — 고유 콘텐츠(기준 모션 설명, 원인 가설, 각도 수치, 감점 tally 전 행)는 전부 화면 어딘가에 잔존"
  artifacts:
    - path: "app/src/app/analysis/result.tsx"
      provides: "재배열된 결과 화면 (옥타곤 상단 + 중복 제거 + 빨강 규율)"
    - path: "app/src/components/SummaryCard.tsx"
      provides: "점수 배지·cuePill 제거된 요약 카드 + hangul-word 줄바꿈"
    - path: "app/src/lib/resultSections.ts"
      provides: "growth/exercise 빈 상태 미렌더 가시성 규칙"
    - path: "app/app.json"
      provides: "version 1.2.0 (runtimeVersion policy appVersion — 런타임 가르기)"
  key_links:
    - from: "SummaryCard '오늘 고칠 것' 탭"
      to: "topFix DeductionCard"
      via: "jumpToRecordKey(topFixKey) — 기존 setCardY 앵커 체계 재사용"
      pattern: "jumpToRecordKey"
    - from: "SummaryCard '자세히 보기' 토글"
      to: "점수 계산 내역 (anchor:scoreBreakdown)"
      via: "toggleDetailExpanded 앵커 1순위 교체 (게이지가 상단으로 갔으므로)"
      pattern: "anchor:scoreBreakdown"
    - from: "ScoreBreakdownSection basisLine"
      to: "상단에서 제거된 scoringBasisLabel 정보"
      via: "breakdownBasisLine (기존 조립, 정보 잔존 경로)"
      pattern: "breakdownBasisLine"
---

<objective>
결과 화면(분석 보고서) 재구성 — "한 발견 = 한 곳, 요약 우선, 빨강 규율".
belle 승인: "UIUX 상으로 필요하면 구조 바꾸는거 오케이", 단 **정보 손실 0** 조건.

Purpose: belle 원문 "보고서가 유익한데 너무 보기가 힘들어" — apple-design 진단 5가지
(발견 5곳 반복 / 점수가 4번째 섹션 / 빨강 남용 / 면책 6곳 / 빈 카드 자리 차지)를 수리.
카피 버그 4건('없음' 삽입, 띄어쓰기, 조사 분리 줄바꿈, 마이 탭 스테일) + version 1.2.0 범프 동반.

Output: result.tsx 재배열 + SummaryCard/DeductionCard/PartChipsRow/resultSections 수정,
typecheck + node --test GREEN. 시뮬레이터 눈검증은 오케스트레이터 후속.
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/CLAUDE.md
@app/src/app/analysis/result.tsx
@app/src/components/SummaryCard.tsx
@app/src/lib/resultSections.ts
@.planning/quick/260831-lcc-result-restructure/before-screens/  (07~13 = before 시각 증거)
</context>

<current_structure_map>
result.tsx(4096줄) 실측 렌더 순서 (플래너가 2026-08-31 측정 — 라인은 수정 전 기준):

| # | 블록 | 라인 | 처분 |
|---|------|------|------|
| 1 | header (title+sub+scoringBasis+배지+bodyProfile+coachPositioning) | 2276-2317 | 참고 3줄→1줄 통합 |
| 2 | refCard (mode1 기준 모션 메타, brandTint) | 2319-2339 | **아래로 이동**+중립화, refNote 제거 |
| 3 | SummaryCard (anchor:summaryCard) | 2356-2392 | 유지 — 점수 배지·cuePill 제거 |
| 4 | coverageCard | 2397-2419 | 무접촉 |
| 5 | InjuryRiskSection ('risk') | 2423 | 무접촉 |
| 6 | topFix DeductionCard + 링크 2개 / cleanPassCard | 2433-2495 | 유지(발견 유일 본체) |
| 7 | 동작 비교 (RenderedComparePlayer/VideoCompare+칩+배너) | 2497-2814 | **내부 무접촉** (승인 이력) |
| 8 | mode3-first/IN-01 안내 | 2816-2863 | 무접촉 |
| 9 | 다른 감점 항목 (collapsed, anchor:collapsedList) | 2875-2912 | 유지 |
| 10 | 옥타곤 점수 카드 (anchor:scoreGauge) | 2916-2953 | **맨 위로 이동**, scoreCaption 제거(하단 병합) |
| 11 | mode3 한계 고지 | 2957-2959 | 유지 |
| 12 | 점수 계산 내역 (anchor:scoreBreakdown) | 2964-2996 | 유지 (투명 tally invariant) |
| 13 | 구간별 점수 | 2999-3016 | 유지 |
| 14 | 코칭 팁 ('먼저 교정할 점' veto card + tips) | 3026-3145 | veto card 해체(고유분만 이동) |
| 15 | 성장·지난 미션 | 3151-3208 | 빈 상태 미렌더 |
| 16 | 보완 운동 | 3214-3288 | 빈 상태 미렌더 |
| 17 | 강사에게 확인할 점 | 3293-3339 | generic 중복 제거 |
| 18 | 심사 시뮬레이션 (judgeInfo) | 3349-3391 | headline 재출현 제거+레이아웃 수리 |
| 19 | ReferenceCornerSection (참고하세요) | 3398-3453 | 무접촉 ('점수에는 들어가지 않아요' 유지 — 오해 방지 기능, 플래너 판단) |
| 20 | CTA 완료/다시 분석 | 3461-3474 | 무접촉 |

실측 근거 포인트:
- `styles.card` 에 `alignItems:'center'`(3572) → judgeTotalRow(space-between, 4078)가
  내용 폭으로 수축해 "심사 환산 점수80점" 붙음 발생 (before-screens/12 실증).
- `highlightNumbers`(250) = 본문 수치를 `colors.brand`+600 으로 — 본문 빨강의 기계 원인.
- `correctionPoint`(1451) = `vetoPrimaryFault ?? tips[0].title` — 백엔드가 '없음' 문자열을
  주면 "없음 보완하면 더 올라가요" 조립 (before-screens 실증). `vetoPrimaryFault`(1056)
  단일 지점 소독이 ①ScoreContext ②'먼저 교정할 점' ③'AI 발견한 점' 3면 동시 수리.
- SummaryCard cuePill(nextAction) 텍스트 = DeductionCard cueBox 와 verbatim 동일
  (before-screens/07 "목표는 한쪽 무릎은…" 2회 실증).
- 섹션 순서·가시성 단일 지점 = `resultSections.ts` RESULT_SECTION_ORDER + 테스트
  (`resultSections.test.ts`). 단, 옥타곤 카드·refCard·점수 내역은 ORDER 키 밖의
  positional JSX — 이동은 JSX 재배치로 하고 ORDER 는 건드릴 필요 없음.
  growth/exercise 빈 상태는 resultSections 가시성 규칙 소관.
</current_structure_map>

<constraints_invariant>
- **정보 손실 0** (belle 조건): 지워도 되는 것은 "복제 문장"과 "없음 표시용 빈 카드"뿐.
  각 제거물의 잔존 경로: refNote→상단 면책 1줄과 의미 동일 / scoringBasisLabel→
  breakdownBasisLine / scoreCaption→하단 통합 면책에 병합 / veto headline→DeductionCard
  statusLine / vetoFixTip→코칭 팁 본문 / cuePill→DeductionCard cueBox / 점수 배지→옥타곤 /
  judge whyLine→DeductionCard whyLine+드릴다운 시트 / growth 빈 안내→2820 mode3-first
  안내문과 의미 중복.
- 투명 감점 tally 수치 삭제 금지 (ScoreBreakdownSection 행·수치 무필터 — memory:
  scoring-must-be-transparent-deduction-tally). D-09 수치 규율(% 금지·헤드라인 수치 금지)
  기존 그대로.
- 동작 비교 섹션(7번 블록) **내부 무접촉** — 확대비교 각도 lockstep·듀얼 컨트롤·발전
  캡션 등 승인 표시 문법 전부. 위치도 이번엔 유지.
- 테마 토큰만(하드코딩 금지), 새 색 추가 금지, 이모지 금지, 다크 배경 금지.
- 백엔드/contract(analysis.ts 타입) 무접촉 — app/src 표시 레이어만.
- OTA 발행 금지 (네이티브 모듈 — 새 빌드로만 배포).
- 홈 추천 썸네일 회색 상자 건은 스코프 밖.
- 실행자는 typecheck+node --test 까지. **시뮬레이터 스크린샷 비교는 오케스트레이터가
  후속 수행** (memory: verify-ui-on-simulator-before-ota — typecheck 는 렌더 크래시를 못 잡는다).
</constraints_invariant>

<tasks>

<task type="auto">
  <name>Task 1: 재배열 + 발견 중복 제거 (요약 우선 구조)</name>
  <files>app/src/app/analysis/result.tsx, app/src/components/SummaryCard.tsx</files>
  <action>
result.tsx 를 current_structure_map 의 처분대로 수술한다. 순서:

1. **옥타곤 카드 상단 이동**: 블록 10(옥타곤 점수 카드, 2916-2953)을 header 직후·refCard
   앞 위치로 JSX 이동. isScoreSuppressed 게이트·anchor:scoreGauge onLayout·ScoreContext·
   vetoPrimaryFault 줄 그대로 동반 이동. scoreCaption("100점은 잘 나오지 않아요…") Text 는
   이 카드에서 제거하고 그 의미를 Task 2 의 하단 통합 면책에 병합한다(문구 신설 최소 —
   기존 두 문장 접합 수준). toggleDetailExpanded 의 스크롤 앵커 1순위를
   anchor:scoreGauge → anchor:scoreBreakdown 으로 교체(게이지가 상단으로 갔으므로 '자세히
   보기'의 목적지는 점수 상세 = 계산 내역).

2. **상단 참고 3줄 → 1줄**: header 에서 scoringBasisLabel Text 를 기본 미렌더로 바꾼다 —
   단 isScoreSuppressed(reference-free "기준 동작 없음") 경로에서만 유지 (Phase 19
   TRUST-03 거짓 confident 차단 목적 잔존). 정보 잔존 경로 = 점수 계산 내역
   breakdownBasisLine(이미 조립됨, 1245 부근) — 실행자는 mode1 doc 에서 basisLine 이 같은
   내용을 담는지 실측 확인 후 제거할 것. coachPositioning("이 분석은 강사 지도를 돕는
   참고예요")이 상단 유일 면책 1줄로 남는다. sub·AccuracyLimitBadge·bodyProfileRow 무접촉.

3. **refCard 하향 이동 + 중립화**: 블록 2(refCard)를 '다른 감점 항목'(블록 9) 뒤·옥타곤
   이동 후 빈 자리(점수 계산 내역 앞) 로 이동 — 사용자의 결과보다 앞에 두지 않는다.
   refNote("기준 모션은 하나의 참고일 뿐이에요") 제거(상단 면책과 의미 중복 — 면책 통합).
   스타일 중립화는 Task 2 소관.

4. **SummaryCard 다이어트** (SummaryCard.tsx): score 배지 제거(옥타곤이 바로 위에서 점수
   표시 — 중복. score prop 과 scoreBadge/scoreBadgeText 스타일 삭제, result.tsx 호출부
   동기 수정). nextAction cuePill 블록 제거(DeductionCard cueBox 와 verbatim 복제 —
   cueBox 가 유일본. nextAction prop·nextActionWrap/cuePill/cueText 스타일 삭제,
   summarySource.ts 는 무접촉 — 조립은 남기고 렌더만 제거해도 되나 미사용 prop 은 지울
   것). praise 헤드라인 + '오늘 고칠 것'(jumpToRecordKey CTA) + '자세히 보기' 토글은 유지.
   praiseHeadline·todayHeadline Text 에 lineBreakStrategyIOS="hangul-word" 추가(큰 제목
   "기본 기준/은 지켰어요" 조사 분리 수리 — RN 0.81 iOS 지원 확인됨).

5. **'없음' 삽입 버그 단일 지점 소독**: vetoPrimaryFault 파생(1056 부근)에서 trim 후
   빈 문자열 또는 '없음' 이면 null 로 강등. correctionPoint(1451)는 tips[0].title 에도
   같은 소독 적용. 이것으로 "없음 보완하면 더 올라가요" / "먼저 교정할 점: 없음" /
   "AI 영상 분석에서 발견한 점: 없음" 3면 동시 수리. 소독은 표시 레이어 폴백 강등이며
   백엔드 데이터 무변형.

6. **'먼저 교정할 점' veto 카드 해체** (블록 14 앞부분, 3036-3073): vetoPrimaryFault
   headline 재출현·vetoFixTip 줄(코칭 팁 detail 재출현)·vetoLeadNote(면책류) 제거. 고유
   콘텐츠인 rootCauseHypotheses('가능한 원인' 목록)만 topFix DeductionCard 직하(2485 부근,
   확대비교 링크 아래)의 중립 보조 블록으로 이동 — topFix 카드 미렌더 경로
   (attributionUnreliable·cleanPass)에서는 함께 미렌더. vetoRootCauses 빈 배열이면 블록
   미렌더. 이동 후 코칭 팁 섹션은 displayTips 카드만 남는다.

7. **심사 시뮬레이션 발견 재출현 제거 + 레이아웃 수리** (블록 18): judgeRow 의 fault 를
   rec.statusLine 우선 → criterionLabelKo(rec.criterion) 짧은 항목명 단독으로 교체하고
   whyLine Text 제거(둘 다 DeductionCard·드릴다운 시트에 잔존 — 행 탭 시 시트가 열리므로
   도달 경로 보존). 환산 수치(−N·심사 환산 점수)와 행 탭 onPress 유지.
   judgeTotalRow 에 alignSelf:'stretch' 추가 — styles.card 의 alignItems:'center' 가 행을
   내용 폭으로 수축시켜 "심사 환산 점수80점" 붙음이 생긴 실측 원인(before-screens/12).
   judgeRow 도 같은 증상이면 동일 처치.

8. **강사 질문 generic 중복 축소** (블록 17): combinedCoachQuestions 렌더 전에 dedup —
   같은 recordId 질문은 첫 1개만, recordId 없는 generic 질문은 텍스트 정확 일치 제거 후
   최대 1개. 사용자가 직접 담은 질문(source 'user')은 필터하지 않는다.

기존 주석의 결정 인용(D-01/D-09/D-02 등)과 이번 재배열이 어긋나는 지점에는 이동 블록
주석에 "belle 2026-08-31 결과 화면 재구성 승인(요약 우선) — 구 D-01/D-09 배치 결정을
대체, 수치 규율 자체는 유지" 를 명기해 다음 세션의 오독을 막는다.
  </action>
  <verify>
    <automated>cd app && npm run typecheck && node --test src/lib/__tests__/summarySource.test.ts src/lib/__tests__/resultSections.test.ts</automated>
  </verify>
  <done>
옥타곤 카드가 header 직후 첫 카드. refCard 는 상세 영역. SummaryCard 에 점수 배지·cuePill
없음. veto 카드 해체 완료(rootCauses 는 topFix 아래 잔존). judgeRow 는 짧은 항목명만.
grep 게이트: "grep -c 'scoreCaption' result.tsx" 스타일 정의 외 사용 0,
"grep -c 'nextAction' SummaryCard.tsx" = 0, typecheck 0 에러.
  </done>
</task>

<task type="auto">
  <name>Task 2: 빨강 규율 + 빈 상태 규칙 + 카피/버전</name>
  <files>app/src/app/analysis/result.tsx, app/src/components/DeductionCard.tsx, app/src/components/PartChipsRow.tsx, app/src/lib/resultSections.ts, app/src/lib/__tests__/resultSections.test.ts, app/src/app/(tabs)/profile.tsx, app/app.json</files>
  <action>
**빨강 규율** (본문 텍스트 브랜드색 금지 — 브랜드색 허용처는 점수·감점 수치(-N)·주 CTA·
활성 상태만. 새 색 추가 금지, 기존 토큰 내 치환):

- result.tsx highlightNumbers(250): 본문 수치 span 을 colors.brand → colors.textPrimary
  유지·fontWeight 강조만 남긴다 (본문 빨강의 기계 원인 제거. 감점 수치 -N 은
  judgeDeduction 등 별도 스타일이라 영향 없음).
- refCard 중립화: backgroundColor brandTint → colors.cardBg, borderColor brand →
  colors.divider, refAthlete brand → colors.textPrimary, refLevel 배지 brand 배경 →
  colors.softBg + colors.textMid (기존 토큰 범위).
- vetoLeadCard 스타일(3920)은 Task 1 이후 growth coachCard 가지(3155)만 사용 — 그 사용처를
  중립 카드로 (brandTint 배경·brand 테두리 제거, styles.card 기본). Ionicons brand 색
  아이콘은 유지 가능(포인트 아이콘은 본문 아님).
- detourCard/detourHeadline(4033-4036): 배경 brandTint → colors.softBg, headline brand →
  colors.textPrimary.
- DeductionCard.tsx cueBox(386): backgroundColor brandTint → colors.softBg (대형 분홍
  박스 → 중립 배경. cue 텍스트는 이미 textPrimary — 무접촉. askBtn brand 테두리 = CTA
  라 유지).
- PartChipsRow.tsx 참고 칩(119-127): borderColor·글자 colors.advisoryOrange → 중립
  (colors.divider / colors.textSecondary) — 노란 점선 제3색 제거. 감점 칩 쪽은 무접촉.
- cleanPassCard 는 무접촉 (이번 증거 화면 밖 + 승인 축하 표면 — 과잉 일반화 금지).

**빈 상태 규칙** (내용 '없음' 카드/섹션 미렌더):

- resultSections.ts: growth 가시성 = hasMissionOutcome 참 또는 variant coachCard 일 때만
  (현재 빈 안내문 렌더 경로 차단 — "이어갈 지난 미션이 없어요"/"다음 분석부터 이전
  미션…" 는 2820 mode3-first 안내와 의미 중복이라 제거 허용). exercise 가시성 =
  개인화 전면 운동 존재 시만 (frontExercise 부재 시 섹션 전체 숨김 — "매핑이 없어요"
  문구·전체 보기 링크 포함. hasExercise input 의미를 "개인화 매핑 존재"로 좁히고
  result.tsx 호출부의 hasExercise 전달값을 frontExercise 기준으로 동기 수정).
  resultSections.test.ts 기대값을 새 규칙으로 갱신 — 각 변경 케이스에 정당화 주석
  1줄(belle 2026-08-31 빈 상태 규칙) 필수.
- result.tsx 쪽 '없음' 폴백 문자열 삽입 잔존분 grep 확인: "없음" 을 템플릿 보간에 넣는
  경로가 남아있지 않은지 (Task 1 의 소독이 상류 차단 — 여기선 확인만).

**카피/버전**:

- profile.tsx 150 행: "로그인·결제·알림 설정은 정식 출시 단계에서 열려요." →
  "결제·알림 설정은 정식 출시 단계에서 열려요." (로그인 구현 완료(Phase 36)와 모순
  해소 — 스테일 카피 수리).
- app.json version "1.1.0" → "1.2.0" (runtimeVersion policy=appVersion 이라 이 범프가
  런타임을 가른다 — 구조 변경분이 구 런타임에 OTA 로 새어나가지 않게 하는 안전판.
  CONTINUE-2026-08-31 명시 사항. OTA 발행은 하지 않는다).
- 하단 통합 면책 1개: JUDGE_SIM_DISCLAIMER(181)에 scoreCaption 의미를 병합 — "AI가 추정한
  감점 시뮬레이션이에요. 촬영 노이즈와 측정 허용 범위가 있어 100점은 잘 나오지 않아요
  (90점 이상이면 정상 자세에 가깝습니다). 실제 심사·강사 평가와 함께 확인하면 가장
  정확해요." 수준의 접합 (신규 창작 최소 — 두 승인 문장의 결합).
  </action>
  <verify>
    <automated>cd app && npm run typecheck && node --test src/lib/__tests__/</automated>
  </verify>
  <done>
grep 게이트(주석 제외 실사용 기준): result.tsx 본문 텍스트 스타일에서
"color: colors.brand" 는 수치·CTA·활성 스타일(judgeDeduction, tipMore, expandText,
scoreDelta, cta 계열)에만 잔존. PartChipsRow 에 advisoryOrange 참고 칩 없음.
resultSections growth/exercise 빈 상태 테스트 신규 기대값 PASS. profile.tsx 에 "로그인"
이 MVP 안내 문구에 없음. app.json version=1.2.0. node --test 전량 PASS (기준선 201
pass 계열 — 기대값 변경은 전부 정당화 주석 동반).
  </done>
</task>

<task type="auto">
  <name>Task 3: 전량 게이트 + 정보 손실 0 자가 감사 + 커밋</name>
  <files>app/src/app/analysis/result.tsx</files>
  <action>
1. 전량 게이트: cd app && npm run typecheck (0 에러) + node --test src/lib/__tests__/
   src/components/__tests__/ (있는 경로만 — 실패 0. 기대값 변경분은 Task 2 에서 이미
   정당화 주석 동반).
2. **정보 손실 0 자가 감사**: constraints_invariant 의 잔존 경로 표를 행별로 코드에서
   실측 확인 — 각 제거물(refNote/scoringBasisLabel/scoreCaption/veto headline/vetoFixTip/
   cuePill/점수배지/judge whyLine/빈 안내문)에 대해 "복제였고 잔존 경로가 코드에 실재"를
   grep 결과로 SUMMARY 에 박제한다. 잔존 경로가 실재하지 않는 항목이 발견되면 제거를
   되돌리고 이동으로 전환할 것 (삭제 금지 원칙).
3. 반복 면책 "정확한 자세는 강사와 함께 영상 확인 권고드립니다" 류가 코칭 팁 detail
   마다 붙는 건은 **백엔드 생성 문장**임을 확인했으므로(app 코드에 해당 문자열 없음 —
   플래너 grep 실측), 표시 레이어 처리 범위에서만: displayTips 렌더 시 tip.detail 말미
   문장이 "강사와" + "확인"/"권고" 를 포함한 문장으로 끝나는 팁이 2개 이상이면 각 팁에서
   그 말미 문장을 잘라내고 코칭 팁 섹션 말미에 동일 취지 1줄(colors.textSecondary)로
   통합 표시. 패턴 미매치 doc 은 원문 그대로(무회귀). 백엔드 문장 원문은 무변형 —
   렌더 시 표시만 접는다.
4. 커밋: 논리 단위로 2~3개 (재배열+중복 제거 / 빨강·빈상태·카피 / 필요시 팁 면책 통합).
   메시지에 quick-260831-lcc 표기.
5. SUMMARY.md 에 명기: **시뮬레이터 눈검증 미수행 — 오케스트레이터가 before-screens/
   07~13 과 after 스크린샷 비교로 수행할 것** (typecheck 는 렌더 크래시를 못 잡는다.
   OTA 발행 금지 — version 1.2.0 은 새 빌드 전용).
  </action>
  <verify>
    <automated>cd app && npm run typecheck && node --test src/lib/__tests__/</automated>
  </verify>
  <done>
typecheck 0 에러, node --test 실패 0, 정보 손실 0 감사표가 SUMMARY 에 grep 근거와 함께
박제, 커밋 완료, 시뮬 검증이 오케스트레이터 후속으로 명시됨.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore doc → 화면 렌더 | 백엔드 생성 문자열(statusLine·tips·primaryFault)이 표시 레이어로 들어옴 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-lcc-01 | Tampering | vetoPrimaryFault/tips 문자열 소독 | mitigate | trim+'없음' 강등은 표시 폴백만 — Text 렌더라 injection 표면 없음, 데이터 무변형 |
| T-lcc-02 | Information Disclosure | 면책 문구 축소 | accept | 상단 1줄+하단 1개+참고코너 1개 잔존 — "AI 참고" 포지셔닝 유지, 법적 표면 동등 |
| T-lcc-SC | Tampering | 패키지 설치 | accept | 신규 패키지 0 (기존 RN Text prop 만 사용) |
</threat_model>

<verification>
- cd app && npm run typecheck — 0 에러
- cd app && node --test src/lib/__tests__/ — 실패 0 (기대값 변경은 정당화 주석 동반)
- grep 게이트: 본문 스타일 brand 잔존 없음 / '없음' 보간 없음 / SummaryCard cuePill·배지 없음
- 시뮬레이터 스크린샷 비교(before-screens/07~13 vs after) = **오케스트레이터 후속** (실행자 스코프 밖)
</verification>

<success_criteria>
- must_haves.truths 9개 전부 코드 레벨 성립 (시각 최종 판정은 오케스트레이터 시뮬 비교)
- 정보 손실 0 감사표 박제 (제거물 → 잔존 경로, grep 근거)
- 동작 비교 섹션 내부 diff 0 / ScoreBreakdownSection 수치 행 무필터 / 백엔드·contract 무접촉
- app.json 1.2.0, OTA 미발행
</success_criteria>

<output>
Create `.planning/quick/260831-lcc-result-restructure/260831-lcc-SUMMARY.md` when done
</output>
