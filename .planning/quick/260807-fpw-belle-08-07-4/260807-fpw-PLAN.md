---
phase: quick-260807-fpw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/src/lib/deductionLabels.ts
  - app/src/lib/__tests__/deductionLabels.test.ts
  - app/src/app/analysis/result.tsx
  - app/src/lib/playbackInvariant.ts
  - app/src/lib/__tests__/playbackInvariant.test.ts
  - app/src/lib/cueTrack.ts
  - app/src/lib/__tests__/cueTrack.test.ts
  - app/src/components/VideoCompare.tsx
autonomous: true
requirements: [BELLE-0807-1, BELLE-0807-2, BELLE-0807-3, BELLE-0807-4]
user_setup: []

must_haves:
  truths:
    - "감점 번호(영상 마커·재생바 틱·점수 계산 내역 행)가 측정 순간(atVideoSec) 오름차순으로 1부터 매겨진다. atVideoSec 없는 record 는 시간 보유분 뒤에 원순서로 온다 (BELLE-0807-1)"
    - "'오늘 고칠 것' 요약 히어로는 정렬과 무관하게 여전히 최대 |points| record 다 (BELLE-0807-1 주의 a)"
    - "음성 후 재개 실패 시 0.5/1/2/3초 간격 백오프로 재시도하고, 최종 실패 시 대칭 정지 + '일시정지됨 — 탭하여 계속' 배지가 보이며, 배지 탭으로 재생이 재개된다 (BELLE-0807-2)"
    - "음성 종료 시점에 현재 재생시각 +1초 이내에 시작하는 미발화 큐가 있으면 재개 없이 같은 멈춤에서 이어 발화 후 재개한다 — 파워스핀 0.11초 간격 케이스가 끊김 없이 연달아 나온다 (BELLE-0807-3)"
    - "재생 중에는 관절 점이 기본 흰색이고 활성 음성 큐의 해당 record 투영 부위만 빨강(brand)이다. 정지 상태의 번호 마커·범례·그룹 경계는 현행 그대로다 (BELLE-0807-4)"
    - "저신뢰(IN-01) doc 도 음성 표면(재생 중 큐 빨간 점·음성 중 강조)에서는 해당 부위가 표시된다 — 정지 상태 마커 억제는 유지 (BELLE-0807-4)"
    - "채점·doc 무접촉: overallScore/final/records 값과 백엔드는 byte 불변, 표시 전용 변경"
  artifacts:
    - path: "app/src/lib/deductionLabels.ts"
      provides: "sortDeductionRecordsByMoment 순수 정렬 함수 (시간순 번호의 단일 출처 입력)"
    - path: "app/src/lib/playbackInvariant.ts"
      provides: "RESUME_RETRY_AT_TICKS 백오프 스케줄 + 개정 R5~R8 판정"
    - path: "app/src/lib/cueTrack.ts"
      provides: "nextChainedCue 순수 체이닝 판정 + CUE_CHAIN_HORIZON_SEC"
    - path: "app/src/components/VideoCompare.tsx"
      provides: "재개 실패 배지(탭하여 계속) + 큐 체이닝 배선 + isPlaying/activeCueRecordId 오버레이 opts"
    - path: "app/src/app/analysis/result.tsx"
      provides: "정렬 records 단일 출처 + 재생 중 마커 색 반전 오버레이 분기"
  key_links:
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/lib/deductionLabels.ts"
      via: "records memo 가 sortDeductionRecordsByMoment 를 1곳에서만 호출"
      pattern: "sortDeductionRecordsByMoment"
    - from: "app/src/app/analysis/result.tsx"
      to: "components/ScoreBreakdownSection"
      via: "정렬 records 로 재조립한 breakdown 객체 전달 (recordNumbers 와 평행 유지)"
      pattern: "records:\\s*records|sortedBreakdown"
    - from: "app/src/components/VideoCompare.tsx"
      to: "app/src/lib/cueTrack.ts"
      via: "음성 자연 종료 분기에서 nextChainedCue 호출"
      pattern: "nextChainedCue"
    - from: "app/src/components/VideoCompare.tsx"
      to: "app/src/lib/playbackInvariant.ts"
      via: "converge-pause 판정 → resumeNotice 배지 state"
      pattern: "converge-pause"
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/components/VideoCompare.tsx"
      via: "leftOverlay opts.isPlaying/activeCueRecordId → 색 반전 분기 → focusKeypointsForRecordId"
      pattern: "isPlaying"
---

<objective>
belle 08-07 실기기 피드백 4건 수리 — 재생 표시·신뢰성. 전부 앱 전용(채점·doc·백엔드 무접촉), 오늘 오전 V-A 2차 수리(35eb03d3·ae398c51: record 별 atFrameIdx 틱 분리 + centerSec 큐)가 반영된 현 트리 기준.

1. (BELLE-0807-1) 감점 번호를 측정 순간(atVideoSec) 시간순으로 재번호 — 번호 단일 출처(마커·틱·내역 행) 유지한 채 입력 배열만 정렬.
2. (BELLE-0807-2) 음성 후 재개 실패 랜덤 스톨 — 재기동 재시도를 백오프(0.5/1/2/3초 간격)로 확장 + 최종 실패 시 '일시정지됨 — 탭하여 계속' 정직 표면화. 원인 추측 수리 금지.
3. (BELLE-0807-3) 인접 큐 체이닝 — 파워스핀 큐 2개 0.11초 간격의 "음성1 종료 → 0.1초 재생 → 음성2 정지" 끊김을 같은 멈춤에서 이어 발화로 해소.
4. (BELLE-0807-4) 재생 중 마커 색 반전 — 재생 중 기본 관절 점 흰색, 활성 큐 record 투영 부위만 빨강. 정지 상태 승인 설계(번호 마커·범례) 보존.

Purpose: belle 실기기 신뢰 회복 — 번호가 시간을 따라가고, 멈춤이 정직하게 안내되고, 연속 감점이 끊기지 않고, 재생 중 화면이 지금 말하는 부위만 가리킨다.
Output: 위 4건이 반영된 앱 코드 + node --test 신규 케이스(정렬 번호·백오프·체이닝) + 전 스위트/typecheck GREEN. 시뮬·OTA 는 오케스트레이터가 사이클 후 수행 (계획 범위 밖).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@app/src/lib/deductionLabels.ts
@app/src/lib/cueTrack.ts
@app/src/lib/playbackInvariant.ts
@app/src/app/analysis/result.tsx
@app/src/components/VideoCompare.tsx
@app/src/lib/__tests__/playbackInvariant.test.ts
@app/src/lib/__tests__/cueTrack.test.ts
@app/src/lib/__tests__/deductionLabels.test.ts
</context>

<planner_findings>
플래너가 실측·전수 grep 으로 확정한 사실 (실행자는 재조사 불요, 인용해 사용):

1. **번호 파이프라인**: `buildDeductionMarkers(records, faultJoints)` 가 입력 순회 순서대로 번호를 부여하고, `recordNumbers`(내역 행)·`keypointNumbers`/`groupMarkers`(영상 마커)·`buildDeductionTicks`(재생바 틱)·`fullscreenLegend`·`partGroups`/`partChips` 전부 이 결과에 평행하다. 입력 배열만 정렬하면 셋이 함께 시간순이 된다.
2. **records 직접 접근 전수 (result.tsx)**: `result.deductionBreakdown?.records ?? []` 직접 접근 11곳 — line 1045(confirmedKeypoints), 1103(estimatedAreaKeypoints), 1139(estimatedAreaRecordIndex), 1162(markers), 1176(partGroups), 1187(partChips), 1204(breakdownBasisLine), 1291(fullscreenLegend), 1311(timelineTicks), 1456(sheetZooms), 1471(sheetView) + 1325(`hasBreakdownRecords` length 접근) + 1792(기존 `records` memo — 위치가 첫 사용보다 늦다).
3. **순서 민감 외부 소비자 1곳**: `ScoreBreakdownSection`(result.tsx:2828)이 `breakdown={result.deductionBreakdown}` 원본 객체를 받아 내부에서 `breakdown.records` 를 순회하며 `recordNumbers={markers.recordNumbers}` 와 index 평행 조인한다. 정렬 배열을 함께 주지 않으면 행↔번호 어긋남. **컴포넌트 무수정으로 해결**: 정렬 records 로 재조립한 breakdown 객체를 전달.
4. **히어로는 이미 순서 무관 (주의 a 확인 완료)**: result.tsx:1819 `topFixIndex` 는 mission recordId 우선 + `points` 최소(최대 감점) 명시 루프. summarySource.ts:240 `selectTodayFix` 도 `[...records].sort((a,b)=>a.points-b.points)[0]` 명시 정렬. **둘 다 수정 불요** — 회귀 가드 주석만.
5. **순서 무관 확인 (주의 b 전수 grep 완료)**: recordId 조인(mission/spotCheck hiddenRecordIds/audioCue cueId/zoom criterion 키/recordMaps)·`cleanPass`·`judgeFinal`(.final)·`coverageGaps`·`detailRecordIndex`+`openRecordByNumber`(recordNumbers.indexOf)·collapsed 목록(`records.map`+`recordKeyForIndex`) 전부 같은 단일 배열 index 이거나 recordId 조인 — 단일 출처로 바꾸면 내부 정합 자동.
6. **재개 불변식 현황**: playbackInvariant.ts — `RESUME_WATCH_TICKS=10`(1초 창), `RESUME_PLAY_RETRIES=3`, R7 이 편측이면 매 tick(100ms) 재시도 → 3회 소진 후 R8 converge-pause(무표시). R5 는 "대칭이면 개입 0" — **양쪽 다 play() 실효 실패(대칭 정지)면 재시도 자체가 없다**. VideoCompare:837 nudge 는 `resumeRetriesRef.current === RESUME_PLAY_RETRIES - 1` (마지막 재시도 직전 제자리 seek). togglePlay(1002)는 양 분기에서 이미 `resumeWatchTicksRef.current = null`(사용자 제스처가 감시를 끈다 — 창 안 "양쪽 정지 = 재개 실패" 판정의 전제).
7. **큐 발화 트리거**: VideoCompare tick(663~)에서 `activeCue(cueWindowsRef.current, cL)` → text 변경 시에만 speakCue → started 면 양쪽 pause + `voicePauseRef=true`. 음성 종료 분기(734~)는 `!isCueSpeaking() || overMax` 면 양쪽 play + 관찰창 개시(755~756 `resumeWatchTicksRef=0, resumeRetriesRef=0`). `CUE_PAUSE_MAX_MS=15000`(318). CUE_WINDOW_SEC=1.6(result.tsx:172) — 파워스핀 0.11초 간격 큐 2개의 윈도우가 크게 겹친다.
8. **재발화 함정 2개 (체이닝 설계 근거)**: (a) 체인 발화 때 자막을 다음 큐로 바꾸면, 멈춘 cL 에서 activeCue 가 여전히 이전 큐라 다음 tick 에 text 역전·재발화가 난다 → 음성 멈춤 중에는 감지/발화 블록을 건너뛴다(voicePauseRef 게이트). (b) 재개 후 체인으로 이미 말한 큐 윈도우에 진입하면 text 변경으로 재발화한다 → 발화 이력 Set(chainSpokenRef) 으로 speak 만 차단(자막 갱신은 유지). Set 은 활성 큐 윈도우를 완전히 벗어날 때(activeCue null) 비운다 — 사용자가 되감아 재진입하면 다시 발화(기존 replay 의미 보존).
9. **오버레이 색 체계 (KeypointOverlay 무수정 가능)**: 관절 점 fill 은 저신뢰→estimateGray / isHi(highlightKeypoints)→`colors.brand`(빨강) / attention→advisoryOrange / 기본→`colors.textWhite`(흰). 즉 재생 중 색 반전은 result.tsx 의 prop 조립 분기만으로 성립: highlightKeypoints=큐 투영, attention/group/number/폴백=비움. 흰 기본 점은 `skeletonVisible`(토글 ON)일 때 렌더 — 토글 OFF 재생 중엔 큐 빨간 점만 뜬다(33-13 D-42 기본 숨김 보존, 의도된 상호작용). `markersVisible` 게이트(2526)는 재생 중 큐 활성 시에도 열려야 한다.
10. **저신뢰 우회 지점**: result.tsx:1867 `focusKeypointsForRecordId` 의 `if (attributionUnreliable) return [];` 조기 반환. 이 함수의 소비처는 음성/큐 표면 2곳뿐(음성 중 focusKeypoints + 신규 재생 중 빨간 점) — 정지 상태 마커 억제(overlayHighlightKeypoints/overlayMarkerNumbers/overlayGroupMarkers/estimatedArea 강등)는 별도 파생이라 무접촉.
11. **배지 스타일 승계원**: VideoCompare styles `voicePausePill`/`voicePauseText`(2060·2070, '음성 중 — 잠시 멈춤' pill) — Ionicons + colors 토큰. 이모지 없음.
12. **테스트 기준선**: 13파일 전부 개별 PASS, 총 179 tests (cueTrack 8 / deductionLabels 4 / deductionSheet 66 / focusShape 12 / gaugeGeometry 4 / illustrationScene 14 / manualOffset 6 / playbackInvariant 12 / resultSections 6 / screenVocabulary 5 / summarySource 14 / visualCards 21 / pickerFailure 7). 러너: Node 24 type stripping, `node --test <파일>` 개별 실행(디렉터리 일괄 실행은 깨짐 — 파일 단위 루프 사용), node:test/node:assert 만, `.ts` 확장자 import.
</planner_findings>

<tasks>

<task type="auto">
  <name>Task 1: 감점 번호 시간순 재번호 — 정렬 단일 출처 (BELLE-0807-1)</name>
  <files>app/src/lib/deductionLabels.ts, app/src/lib/__tests__/deductionLabels.test.ts, app/src/app/analysis/result.tsx</files>
  <action>
belle 08-07 확정 결정 #1: records 를 측정 순간(atVideoSec) 오름차순으로 정렬한 순서로 번호가 매겨지게 한다. 번호 단일 출처(buildDeductionMarkers)는 무수정 — 입력 배열을 정렬해 마커·틱·내역 행이 함께 시간순이 된다.

1. deductionLabels.ts 에 순수 함수 `sortDeductionRecordsByMoment(records: DeductionRecord[]): DeductionRecord[]` 를 export 추가. 규칙: (a) `atVideoSec` 이 유한 number 인 record 는 그 값 오름차순, (b) 없거나 비유한이면 전부 뒤로 보내되 원순서 유지(정렬 키 +Infinity), (c) 동률도 원순서 유지 — V8 stable sort 를 복제본 `[...records].sort(...)` 에 적용, 입력 배열 비변형. 주석 한국어로 belle 08-07 결정 + quick-260807-fpw 출처 명기. 같은 파일 buildDeductionMarkers 헤더의 "record 순회는 저장 순서 그대로 — 재정렬 금지" 주석을 갱신: 이 함수 자체는 여전히 입력 순서대로 번호를 부여하며, 시간순 정렬은 호출부(result.tsx)가 sortDeductionRecordsByMoment 로 선행한다(belle 08-07 — 표시 순서 결정은 표시 계층 소관, 엔진 저장 순서 재해석 아님).

2. result.tsx 단일 출처화: 기존 line 1792 부근의 `records` useMemo 를 첫 사용(confirmedKeypoints, ~line 1042) 앞으로 이동하고 `sortDeductionRecordsByMoment(result.deductionBreakdown?.records ?? [])` 을 적용한다. planner_findings 2 의 직접 접근 11곳(1045/1103/1139/1162/1176/1187/1204/1291/1311/1456/1471)을 전부 `records` 로 교체, `hasBreakdownRecords`(1325)는 `records.length > 0` 으로. 기존 1792 memo 는 제거(중복 선언 금지).

3. ScoreBreakdownSection 정합(planner_findings 3): `records` memo 근처에 `sortedBreakdown` useMemo 를 추가 — breakdown 존재 시 `{ ...result.deductionBreakdown, records }` 로 재조립, 부재 시 그대로. result.tsx:2828 의 `breakdown` prop 을 이 값으로 교체한다. ScoreBreakdownSection 컴포넌트 자체는 무수정. cleanPass/judgeFinal/coverageGaps 등 순서 무관 소비자(planner_findings 5)는 원본 유지 — 값 byte 동일.

4. 히어로 회귀 가드(주의 a): topFixIndex(1819)와 summarySource selectTodayFix 는 이미 최대 |points| 명시 선택이라 수정 불요 — topFixIndex 주석에 "정렬 무관: 히어로 = mission 우선 + 최대 감점 명시 선택 (belle 08-07 #1 주의 a 확인)" 1줄만 추가.

5. deductionLabels.test.ts 신규 케이스 (node:test/node:assert, .ts import 관례 유지): (a) atVideoSec 혼재 입력이 오름차순으로 정렬된다, (b) atVideoSec 없는 record 들은 뒤에 원순서로 온다, (c) 동률 시 원순서 유지(stable), (d) 입력 배열 비변형, (e) 정렬 결과를 buildDeductionMarkers 에 넣으면 recordNumbers 가 시간 순서대로 1부터 증가한다(번호·마커·틱 시간순의 실체 검증).

금지: 엔진/백엔드/doc 접촉 0, buildDeductionMarkers 내부 재정렬 0(번호 규칙 사본 금지), 정렬 지점 2곳 이상 금지(단일 출처).
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && node --test app/src/lib/__tests__/deductionLabels.test.ts && [ "$(grep -c 'deductionBreakdown?.records' app/src/app/analysis/result.tsx)" = "1" ] && (cd app && npm run typecheck)</automated>
  </verify>
  <done>sortDeductionRecordsByMoment 신설 + result.tsx 의 `deductionBreakdown?.records` 직접 접근이 records memo 1곳뿐. deductionLabels 테스트(기존 4 + 신규 5) PASS. ScoreBreakdownSection 은 정렬 records 로 재조립된 breakdown 을 받아 recordNumbers 와 평행. topFixIndex/selectTodayFix 무수정(주석 가드만). typecheck GREEN.</done>
</task>

<task type="auto">
  <name>Task 2: 음성 후 재개 백오프 + '탭하여 계속' + 인접 큐 체이닝 (BELLE-0807-2·3)</name>
  <files>app/src/lib/playbackInvariant.ts, app/src/lib/__tests__/playbackInvariant.test.ts, app/src/lib/cueTrack.ts, app/src/lib/__tests__/cueTrack.test.ts, app/src/components/VideoCompare.tsx</files>
  <action>
음성 전후 재생 수명주기 2건. 원인 추측 수리 금지(F-6 원칙 — 기기 실패 기제 미규명 유지): 회복력 강화 + 정직한 표면화 + 끊김 제거만.

**A. 재개 백오프 (playbackInvariant.ts — 순수 판정 개정, belle 08-07 #2):**

상수 개정: `RESUME_RETRY_AT_TICKS = [5, 15, 35, 65]`(tick=100ms — 재개 후 0.5/1.5/3.5/6.5초 시점 = 간격 0.5/1/2/3초, belle 예시 그대로), `RESUME_PLAY_RETRIES = RESUME_RETRY_AT_TICKS.length`(4 — VideoCompare nudge 조건 `RESUME_PLAY_RETRIES - 1` 은 무수정 승계되어 마지막 재시도 직전 제자리 seek 유지), `RESUME_CONVERGE_GRACE_TICKS = 10`(마지막 재시도 후 1초 유예), `RESUME_WATCH_TICKS = 75`(= 65 + 10, 관찰창 7.5초).

판정 개정 (R1~R4·R6 유지, R5·R7·R8 개정 — 헤더 주석에 belle 08-07 #2 근거 갱신):
- R5': 양쪽 재생 중이면 NONE(회복 — 개입 0). **관찰창 안에서 "양쪽 정지"는 더 이상 무조건 정상이 아니다** — togglePlay 양 분기가 이미 관찰창을 닫으므로(planner_findings 6) 창 안의 양쪽 정지는 사용자 정지가 아니라 재개 실패다. 종전 spin-up 유예는 첫 재시도가 0.5초 뒤로 밀리며 스케줄이 자연 제공(구 R5 헤더 (c) 주석 갱신).
- R7'(재시도 잔여): `resumeWatchTicks >= RESUME_RETRY_AT_TICKS[resumeRetriesUsed]` 면 retry-play — 정지된 쪽에 play(양쪽 정지면 양쪽), 단 startHold 중 right 는 leave(R6 의도 편측 보존), consumeRetry. 아직 시각 전이면: 편측(한쪽만 재생)은 enforce-pause 로 도는 쪽을 멈춰 드리프트 차단(불변식 정신 — 대기 중 편측 진행 금지), 양쪽 정지면 NONE(재시도 시각까지 대기).
- R8'(재시도 소진): `resumeWatchTicks >= RESUME_WATCH_TICKS` 면 converge-pause(재생 중인 쪽만 pause, closeWatch) — 최종 대칭 정지. 그 전엔 편측이면 enforce-pause(도는 쪽), 양쪽 정지면 NONE(마지막 재시도 유예 대기).

**B. '일시정지됨 — 탭하여 계속' 배지 (VideoCompare.tsx):**

state `resumeNotice: boolean` 신설. 세팅: decision 처리부에서 `action === 'converge-pause'` 일 때 setPlaying(false)와 함께 true. 해제: (a) togglePlay 양 분기(사용자 제스처), (b) tick 에서 notice 인데 어느 쪽이든 재생 관측되면(자연 회복), (c) 배지 탭. 렌더: `resumeNotice && !playing` 일 때 row 컨테이너 안 하단 중앙(기존 cueSubtitleWrap 위치 계열, 자막 유무와 독립인 별도 wrap)에 Pressable pill — voicePausePill/voicePauseText 스타일 승계(신규 스타일 resumeNoticePill 류로 복제·조정, colors 토큰만, 이모지 금지, Ionicons 'play' 아이콘 허용), 문구 '일시정지됨 — 탭하여 계속'. accessibilityRole="button" + accessibilityLabel + hitSlop. onPress: notice 해제 → togglePlay()(재생) → 관찰창 재무장(`resumeWatchTicksRef.current = 0; resumeRetriesRef.current = 0` — togglePlay 가 null 로 닫은 뒤 재무장이므로 호출 순서 준수, 탭 재개도 백오프 보호를 받는다). 주석에 belle 08-07 #2(엘보 랜덤 스톨) + quick-260807-fpw 출처.

**C. 인접 큐 체이닝 (cueTrack.ts 순수 함수 + VideoCompare 배선, belle 08-07 #3):**

cueTrack.ts 에 `CUE_CHAIN_HORIZON_SEC = 1.0` 과 순수 함수 `nextChainedCue(windows, currentSec, spokenRecordIds: ReadonlySet<string>, horizonSec): CueWindow | null` export 추가. 후보 조건: recordId 보유 ∧ spokenRecordIds 에 없음 ∧ `endSec > currentSec`(이미 지나간 윈도우 제외) ∧ `startSec <= currentSec + horizonSec`(이미 열려 있는 미발화 윈도우 포함 — 파워스핀 겹침 윈도우가 정확히 이 모양, planner_findings 7). 선택: startSec 최소(가장 이른 것), 동률은 입력 순. currentSec 비유한/windows 부재 → null. 주석에 belle 08-07 #3(파워스핀 '돌다가 끊김') 출처.

VideoCompare 배선 (planner_findings 8 의 재발화 함정 2개 해소 포함):
- `chainSpokenRef = useRef<Set<string>>(new Set())` 신설. 최초 발화 성공 시(started) `chainSpokenRef.current.add(cue.recordId)`.
- tick 재구성: `const cue = activeCue(...)` 계산과 활성 윈도우 추적은 항상 수행하되, **text 갱신·발화 블록 전체를 `!voicePauseRef.current` 게이트로 감싼다**(함정 a — 음성 멈춤 중 자막은 체인 핸들러가 소유, 발화 중 자막이 오디오와 일치 유지). cue 가 null 이면 chainSpokenRef 를 비운다(윈도우 군집을 완전히 벗어남 — 되감기 재진입 시 재발화되는 기존 replay 의미 보존).
- 발화 트리거에 이력 가드 추가: `cue.recordId` 가 chainSpokenRef 에 있으면 speakCue 를 건너뛴다(자막 갱신은 수행 — 함정 b).
- 음성 종료 분기(734~) 개정: `!isCueSpeaking()` 이고 `!overMax`(자연 종료만 — 상한 강제 재개는 체인 금지)이고 audioEnabledRef 켜짐이면 `nextChainedCue(cueWindowsRef.current, cL, chainSpokenRef.current, CUE_CHAIN_HORIZON_SEC)` 를 시도. 후보가 있고 speakCue started 면: chainSpokenRef 에 추가, setVoiceCueRecordId(다음 recordId), activeCueTextRef/현재 자막을 다음 큐 text 로 갱신, `voicePauseStartRef.current = Date.now()`(큐당 CUE_PAUSE_MAX_MS 재무장), voicePauseRef 는 true 유지한 채 조기 return(같은 멈춤에서 이어 발화). 후보 없음/발화 실패면 기존 재개 경로 그대로(관찰창 개시 포함 — A 의 백오프가 이어받는다).
- 알려진 무해 엣지(주석 박제): 체인 재개 직후 자막이 한 tick 이전 큐로 되돌았다 다음 윈도우에서 복귀할 수 있음 — 발화는 이력 가드로 차단되므로 표시 순간 전환만.

**D. 테스트:**

playbackInvariant.test.ts 갱신: 보존 축(개입 0 계열 — R1 단일 패널/R2 scrubbing/R3 voicePaused enforce/R4 창 밖 NONE/R6 startHold 면제/양쪽 재생 NONE)은 유지하고, 재시도 페이싱 축을 스케줄 의미로 재작성. 신규 축: (a) 양쪽 정지 상태에서 스케줄 시각에 retry-play 가 양쪽 play 로 발화(belle 랜덤 스톨 회복의 핵심 신설 경로), (b) 스케줄 시각 전 편측이면 enforce-pause(도는 쪽), (c) 스케줄 시각 전 양쪽 정지면 NONE, (d) 마지막 재시도 후 유예 중 NONE·`RESUME_WATCH_TICKS` 도달 시 converge-pause + closeWatch, (e) startHold 중 재시도가 right 에 play 를 쏘지 않는다, (f) 스케줄 sanity(오름차순, 마지막 + 유예 = RESUME_WATCH_TICKS). 기존 12 테스트 중 페이싱 의미가 바뀐 것만 개정 — 개정 사유를 각 테스트 주석에 belle 08-07 #2 로 명기.

cueTrack.test.ts 신규: (a) 파워스핀 재현 — 0.11초 간격 겹침 윈도우 2개, 첫 큐 발화 후 둘째가 체인 후보로 선택, (b) horizon(1초) 밖 시작 큐는 null, (c) 이미 발화한 recordId 제외, (d) recordId 없는 윈도우 제외, (e) 후보 다수면 startSec 최소 선택, (f) endSec 지난 윈도우 제외, (g) 비유한 currentSec/빈 windows → null.

금지: cueTrack 기존 buildCueWindows/activeCue 시그니처 변경 0, epsilon seek 등 신규 회복 지렛대 추가 0(승인 범위 밖), 원인 확정 서술 주석 0.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && node --test app/src/lib/__tests__/playbackInvariant.test.ts && node --test app/src/lib/__tests__/cueTrack.test.ts && (cd app && npm run typecheck)</automated>
  </verify>
  <done>백오프 스케줄(0.5/1/2/3초 간격, 관찰창 7.5초)이 순수 판정에 박제되고 양쪽-정지 재개 실패도 재시도 대상이 된다. 최종 실패 시 대칭 정지 + '일시정지됨 — 탭하여 계속' Pressable 배지(토큰·스타일 승계·이모지 0), 탭으로 재생+관찰창 재무장. nextChainedCue 가 +1초 이내 미발화 큐를 같은 멈춤에서 이어 발화시키고 재발화 함정 2개가 가드된다. playbackInvariant·cueTrack 테스트 PASS, typecheck GREEN.</done>
</task>

<task type="auto">
  <name>Task 3: 재생 중 마커 색 반전 — 흰 기본 + 활성 큐 부위만 빨강 (BELLE-0807-4)</name>
  <files>app/src/components/VideoCompare.tsx, app/src/app/analysis/result.tsx</files>
  <action>
belle 08-07 지시 #4 그대로: 재생 중에는 기본 관절 점 흰색, 활성 음성 큐의 해당 record 투영 부위만 빨강. 정지 상태의 번호 마커·범례·그룹 경계는 현행 유지(isPlaying 조건 분기 — 승인 설계 보존). KeypointOverlay 는 무수정 — planner_findings 9 대로 색 반전은 prop 조립 분기만으로 성립(빨강 = colors.brand 경유 기존 isHi 렌더, 흰 = colors.textWhite 기존 기본 렌더 — 신규 색상 리터럴 0).

1. VideoCompare 활성 윈도우 추적: state `activeCueWindowRecordId: string | null` + ref 신설. tick 에서 `cue = activeCue(...)` 계산 직후(Task 2 의 voicePauseRef 게이트 **바깥** — 항상 추적) `cue?.recordId ?? null` 을 ref 비교로 변경 시에만 setState(렌더 churn 0). 이것은 발화 여부와 무관한 윈도우 도메인 신호다 — 오디오 OFF 자막-만 재생에서도 성립.

2. 오버레이 opts 확장: OverlayRenderProp opts 를 `{ sizeScale?, voiceCueRecordId?, isPlaying?: boolean, activeCueRecordId?: string | null }` 로 확장. VideoSlot(세로)과 renderFullscreenSlot(전체화면) 의 **학생(left) 슬롯** overlay 호출 2곳에 `isPlaying: playing` 과 `activeCueRecordId: activeCueWindowRecordId` 를 전달(음성 큐 강조가 학생 측만인 33-13 관례 승계 — right 슬롯 미전달). 주석에 belle 08-07 #4 + quick-260807-fpw 출처.

3. result.tsx leftOverlay 색 반전 분기: render prop 안에서 `const playingInversion = opts?.isPlaying === true;` 와 `const playingCueKeypoints = playingInversion && opts?.activeCueRecordId ? focusKeypointsForRecordId(opts.activeCueRecordId) : null;` 을 파생하고 KeypointOverlay props 를 분기한다 — playingInversion 이면: highlightKeypoints = playingCueKeypoints ?? [](활성 큐 투영 부위만 빨강), attentionKeypoints = [], groupMarkers = [], markerNumbers = {}, forceHighlightWorstCount = 0, jointAngles = undefined(legacy doc 편차 폴백 빨강도 재생 중 억제 — 규칙 일관). 아니면 기존 overlay* 파생값 그대로(정지 상태 승인 설계 byte 보존). markersVisible 게이트를 `overlayVisible || opts?.voiceCueRecordId != null || (opts?.isPlaying === true && opts?.activeCueRecordId != null)` 로 확장 — 토글 OFF 재생 중에도 큐 부위 빨간 점이 뜬다(그 외엔 D-42 기본 숨김 유지). focusKeypoints prop 은 무변경(voiceCueRecordId 는 음성 멈춤 중에만 non-null → 재생 중 dim/펄스 미발동 자동 보장).

4. IN-01 저신뢰 우회(planner_findings 10): focusKeypointsForRecordId 의 `if (attributionUnreliable) return [];` 조기 반환을 제거한다. 주석에 명기: belle 08-07 #4 — 이 함수의 소비처는 음성/큐 표면 2곳뿐(음성 중 강조 + 재생 중 큐 빨간 점)이고, 음성이 이미 그 관절명을 말하므로 음성 표면에는 부위 표시를 허용한다(quick-260807-fpw). 정지 상태 마커 억제(overlayHighlightKeypoints/overlayMarkerNumbers/overlayGroupMarkers/estimatedArea 강등·집계 문장 강등)는 별도 파생이라 그대로 유지 — IN-01 승인 설계의 정지 표면은 무접촉.

5. 자체 점검(코드 리뷰 수준, 주석/구현으로 반영): (a) 재생 중 + 큐 없음 = 빨강 0(highlightKeypoints 빈 배열) — 토글 ON 이면 흰 스켈레톤만, (b) 음성 멈춤 중(playing=false) = 기존 승인 설계(dim + focusShapes + 번호 마커), (c) 사용자 정지 = 기존 번호 마커·그룹 경계 그대로, (d) 전체화면 뷰어도 동일 분기(같은 render prop 재사용이라 자동).

금지: KeypointOverlay.tsx 수정 0, 색상 hex 하드코딩 0(토큰 경유 기존 렌더 재사용), 정지 상태 마커 파생값(overlay* 계열) 수정 0.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && (cd app && npm run typecheck) && for f in app/src/lib/__tests__/*.test.ts app/src/lib/__tests__/*.test.mjs app/src/lib/pickerFailure.test.ts; do node --test "$f" || exit 1; done && [ "$(grep -c "attributionUnreliable) return \[\]" app/src/app/analysis/result.tsx)" = "0" ]</automated>
  </verify>
  <done>재생 중 학생 오버레이가 색 반전 분기를 탄다: 기본 점 흰색(토글 ON 시), 활성 큐 record 투영 부위만 brand 빨강, 번호/그룹/주황/폴백 억제. 정지·음성 멈춤 상태는 기존 승인 렌더 byte 보존. 저신뢰 doc 도 음성 표면에서 부위 표시(조기 반환 제거 + belle 08-07 출처 주석). 전 테스트 스위트(13파일) PASS + typecheck GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Firestore doc → 앱 렌더 | 저장된 record 필드(atVideoSec/recordId)를 표시 로직이 소비 — 이미 normalize 계층 존재 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-fpw-01 | Tampering | sortDeductionRecordsByMoment 입력 | mitigate | 비유한/부재 atVideoSec 방어 처리(뒤로 정렬·크래시 0), 입력 비변형 — 테스트로 고정 |
| T-fpw-02 | DoS | 재개 재시도 루프 | mitigate | 스케줄 상한 4회 + 관찰창 75 tick 상한 + converge-pause 종결 — 무한 play/pause 왕복 구조 차단(기존 원칙 승계) |
| T-fpw-03 | DoS | 큐 체이닝 재발화 | mitigate | chainSpokenRef 이력 가드 + 자연 종료 한정 + 큐당 CUE_PAUSE_MAX_MS 재무장 — 무한 체인/재발화 차단 |
| T-fpw-04 | Info Disclosure | IN-01 저신뢰 부위 표시 | accept | belle 08-07 명시 승인 — 음성이 이미 관절명을 발화하는 표면에 한정, 정지 상태 억제 유지 |
| T-fpw-SC | Tampering | 패키지 설치 | accept | 신규 의존성 0 (node:test/기존 라이브러리만) — 설치 태스크 부재로 legitimacy 게이트 해당 없음 |
</threat_model>

<verification>
전 태스크 공통 게이트 (계획 범위 = 코드 + node 테스트 + typecheck. 시뮬 렌더·OTA 는 오케스트레이터가 사이클 후 수행):

1. 전체 스위트: `for f in app/src/lib/__tests__/*.test.ts app/src/lib/__tests__/*.test.mjs app/src/lib/pickerFailure.test.ts; do node --test "$f" || exit 1; done` — 13파일 전부 PASS (기준선 179 tests + 신규. playbackInvariant 페이싱 축 개정은 belle 08-07 #2 승인 의미 변경 — 개정 사유 주석 필수).
2. `cd app && npm run typecheck` GREEN.
3. 단일 출처: result.tsx 의 `deductionBreakdown?.records` 직접 접근 == 1 (records memo 만).
4. 채점 무접촉: 백엔드/`app/src/types/analysis.ts` 계약 diff 0 — `git diff --stat backend/ app/src/types/` 빈 출력.
5. 관례: 주석 한국어 + 출처 인용(belle 08-07, quick-260807-fpw), 이모지 0, 신규 색상 hex 리터럴 0(colors 토큰만 — brand/textWhite 기존 렌더 재사용).
</verification>

<success_criteria>
- belle 4건 전부 반영: 번호 시간순(마커·틱·내역 동시), 재개 백오프+정직 배지, 인접 큐 체이닝, 재생 중 색 반전.
- 히어로(오늘 고칠 것)는 여전히 최대 |points| — 정렬의 부수 회귀 0.
- ScoreBreakdownSection 행 번호 ↔ 영상 마커 번호 ↔ 재생바 틱 번호 일치 유지(단일 출처 보존).
- 정지 상태 승인 설계(번호 마커·범례·IN-01 정지 억제) byte 보존.
- 전 스위트 + typecheck GREEN, 채점·doc·계약 무접촉.
</success_criteria>

<output>
완료 시 `.planning/quick/260807-fpw-belle-08-07-4/260807-fpw-SUMMARY.md` 작성 — 4건별 구현 내역, 테스트 증분(기준선 179 → 신규 포함 수), 미검증 항목(실기기·시뮬 확인 대기)을 이유와 함께 표로 박제.
</output>
