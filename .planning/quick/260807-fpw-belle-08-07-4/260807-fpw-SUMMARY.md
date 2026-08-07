---
phase: quick-260807-fpw
plan: 01
subsystem: app-result-playback
tags: [deduction-numbering, playback-invariant, cue-chaining, marker-inversion, belle-feedback]
requires:
  - "260806-usc 재생 불변식 집행 (playbackInvariant R1~R8)"
  - "260806-wj3 record별 atFrameIdx 틱 분리 + centerSec 큐"
  - "33-13 음성 큐 일시정지·부위 강조 (voiceCueRecordId opts)"
provides:
  - "sortDeductionRecordsByMoment — 감점 번호 시간순의 단일 정렬 지점"
  - "RESUME_RETRY_AT_TICKS 백오프 스케줄 + 양쪽-정지 재시도 (R5'/R7'/R8')"
  - "nextChainedCue + CUE_CHAIN_HORIZON_SEC — 인접 큐 같은 멈춤 이어 발화"
  - "overlay opts.isPlaying/activeCueRecordId — 재생 중 색 반전 신호"
affects: [app-result-screen, video-compare, audio-cue]
tech-stack:
  added: []
  patterns:
    - "정렬은 표시 계층 1곳 (엔진 저장 순서 재해석 0)"
    - "백오프 스케줄 순수 판정 + 호출부 배지 표면화"
key-files:
  created: []
  modified:
    - app/src/lib/deductionLabels.ts
    - app/src/lib/__tests__/deductionLabels.test.ts
    - app/src/app/analysis/result.tsx
    - app/src/lib/playbackInvariant.ts
    - app/src/lib/__tests__/playbackInvariant.test.ts
    - app/src/lib/cueTrack.ts
    - app/src/lib/__tests__/cueTrack.test.ts
    - app/src/components/VideoCompare.tsx
decisions:
  - "번호 시간순은 입력 배열 정렬로 성립 — buildDeductionMarkers 번호 규칙 무수정 (단일 출처 보존)"
  - "관찰창 안 양쪽 정지 = 재개 실패 (togglePlay 가 창을 닫으므로 사용자 정지 아님) — R5 개정"
  - "체인은 자연 종료(!overMax) + audio ON 한정, 재발화는 chainSpokenRef 이력으로 차단"
  - "재생 중 빨강 = 활성 큐 record 투영 부위뿐 (legacy 편차 폴백·주황·번호·그룹 전부 억제)"
metrics:
  duration: "24m"
  completed: "2026-08-07"
  tasks: 3
  commits: 3
  tests: "179 → 196 (+17)"
---

# Quick 260807-fpw: belle 08-07 재생 표시·신뢰성 4건 Summary

**One-liner:** 감점 번호 시간순 정렬 단일 출처 + 재개 백오프(0.5/1/2/3초)·'탭하여 계속' 정직 배지 + 인접 큐 같은-멈춤 체이닝 + 재생 중 활성 큐 부위만 빨강 — 전부 표시·재생 전용, 채점·doc·백엔드 byte 무접촉.

## 4건별 구현 내역

### 1. BELLE-0807-1 — 감점 번호 측정 순간 시간순 (commit `d848e469`)

- `deductionLabels.ts` 에 `sortDeductionRecordsByMoment` 신설: atVideoSec 오름차순, 부재·비유한(NaN/Infinity)은 뒤로 원순서, 동률 stable, 입력 비변형(복제본). Infinity−Infinity=NaN comparator 함정을 `===` 동률 조기 반환으로 회피.
- `result.tsx` records memo 를 첫 사용(confirmedKeypoints) 앞으로 이동 + 정렬 적용. 직접 접근 11곳(confirmedKeypoints/estimatedAreaKeypoints/estimatedAreaRecordIndex/markers/partGroups/partChips/breakdownBasisLine/fullscreenLegend/timelineTicks/sheetZooms/sheetView) + hasBreakdownRecords 전부 단일 출처화 — `deductionBreakdown?.records` 직접 접근 잔존 1곳(records memo)뿐 (grep 검증).
- ScoreBreakdownSection 은 `sortedBreakdown`(정렬 records 재조립 spread) 을 받아 내부 행 순회 ↔ recordNumbers 평행 유지 — 컴포넌트 무수정.
- 히어로(오늘 고칠 것)는 무수정 — topFixIndex 가 mission 우선 + points 최소 명시 선택이라 정렬 무관 (회귀 가드 주석만 추가, 주의 a).

### 2. BELLE-0807-2 — 재개 백오프 + '일시정지됨 — 탭하여 계속' (commit `f063b36c`)

- `playbackInvariant.ts`: `RESUME_RETRY_AT_TICKS=[5,15,35,65]`(재개 후 0.5/1.5/3.5/6.5초 = 간격 0.5/1/2/3초, belle 예시 그대로), `RESUME_PLAY_RETRIES=4`(스케줄 길이 파생), `RESUME_CONVERGE_GRACE_TICKS=10`, `RESUME_WATCH_TICKS=75`(스케줄 파생 — sanity 구조 성립).
- R5' 개정: 양쪽 재생만 무개입. **관찰창 안 양쪽 정지는 재시도 대상** (belle 랜덤 스톨의 사각이던 "양쪽 다 play() 실효 실패" 회복 경로 신설). spin-up 유예는 첫 재시도 0.5초 지연이 대체.
- R7': 스케줄 시각 도달 시 정지된 쪽 play (양쪽 정지면 양쪽, startHold 중 right 는 leave), 시각 전엔 편측 enforce-pause / 양쪽 정지 NONE. R8': RESUME_WATCH_TICKS 도달 시 converge-pause(재생 중인 쪽만 pause) + closeWatch.
- VideoCompare: converge-pause 에 `resumeNotice` 배지 세움 — '일시정지됨 — 탭하여 계속' Pressable pill (voicePausePill 스타일 승계, videoBg/textWhite 토큰만, Ionicons 'play', accessibility 완비). 해제 3경로: togglePlay 양 분기 / tick 재생 관측(자연 회복) / 배지 탭. 탭 = 해제 → togglePlay → 관찰창 재무장(togglePlay 가 닫은 **뒤** 0 재무장 — 탭 재개도 백오프 보호).
- 기존 제자리 seek nudge(`RESUME_PLAY_RETRIES - 1`) 무수정 승계 — 마지막(4번째) 재시도 직전 1회 유지. 원인 확정 서술 0 (F-6).

### 3. BELLE-0807-3 — 인접 큐 체이닝 (commit `f063b36c`)

- `cueTrack.ts` 에 `nextChainedCue(windows, currentSec, spokenRecordIds, horizonSec)` + `CUE_CHAIN_HORIZON_SEC=1.0` 신설: recordId 보유 ∧ 미발화 ∧ endSec>currentSec ∧ startSec≤currentSec+1초 후보 중 startSec 최소 (동률 입력 순). 기존 buildCueWindows/activeCue 시그니처 무변경.
- VideoCompare 음성 자연 종료(!overMax) 분기에서 체인 시도: 성공 시 chainSpokenRef 등재 + voiceCueRecordId/자막을 다음 큐로 + CUE_PAUSE_MAX_MS 큐당 재무장 + voicePauseRef true 유지 조기 return — 같은 멈춤에서 이어 발화. 실패/후보 없음 = 기존 재개 경로 그대로 (관찰창 → #2 백오프가 이어받음).
- 재발화 함정 2개 가드: (a) 음성 멈춤 중 자막·발화 블록 전체 `!voicePauseRef` 게이트 (멈춘 cL 의 activeCue 역전 차단 — 멈춤 중 자막은 체인 핸들러 소유), (b) chainSpokenRef 이력으로 speak 만 차단 (자막 갱신 유지). 이력은 activeCue null(윈도우 군집 이탈) 시 clear — 되감기 재발화(replay) 의미 보존.

### 4. BELLE-0807-4 — 재생 중 마커 색 반전 (commit `d1bf271a`)

- VideoCompare: `activeCueWindowRecordId` 상태 신설 — 발화 여부 무관 윈도우 도메인 신호 (voicePause 게이트 **바깥**에서 항상 추적, ref 비교 setState 로 churn 0 — 오디오 OFF 자막-만 재생에서도 성립). overlay opts 를 `isPlaying`/`activeCueRecordId` 로 확장, 학생(left) 슬롯만 전달 (세로 VideoSlot + 전체화면 renderFullscreenSlot 2곳, 33-13 관례 승계).
- result.tsx leftOverlay 분기: `playingInversion`(재생 중)이면 highlightKeypoints=활성 큐 record 투영 부위만(빨강 = 기존 colors.brand isHi 렌더 재사용), attention/group/number/forceHighlight/jointAngles(legacy 편차 폴백) 전부 억제. 아니면 기존 overlay* 파생값 그대로 — 정지·음성 멈춤 상태 승인 렌더 byte 보존. markersVisible 게이트에 `(isPlaying && activeCueRecordId)` 추가 — 토글 OFF 재생 중에도 큐 부위 빨간 점 (그 외 D-42 기본 숨김 유지). KeypointOverlay 무수정, 신규 색상 리터럴 0.
- IN-01 저신뢰 우회: focusKeypointsForRecordId 의 `attributionUnreliable → []` 조기 반환 제거 — 소비처가 음성/큐 표면 2곳뿐이고 음성이 이미 관절명을 발화. 정지 상태 억제(overlay* 강등)는 별도 파생이라 무접촉.

## 테스트 증분

| 파일 | 기준선 | 최종 | 증분 |
|------|--------|------|------|
| deductionLabels.test.ts | 4 | 9 | +5 (정렬 4축 + 정렬→번호 시간순 실체) |
| playbackInvariant.test.ts | 12 | 17 | +5 (양쪽-정지 재시도/스케줄 페이싱/유예 수렴/startHold leave/스케줄 sanity — 페이싱 개정 3건은 개정 사유 주석 명기) |
| cueTrack.test.ts | 8 | 15 | +7 (파워스핀 재현/horizon/이력 제외/recordId 부재/최소 startSec/지난 윈도우/무효 입력) |
| 나머지 10파일 | 155 | 155 | 무변경 전건 PASS |
| **합계** | **179** | **196** | **+17** |

전 스위트 13파일 196 pass / 0 fail + `tsc --noEmit` GREEN + `git diff --stat backend/ app/src/types/` 빈 출력 (채점·계약 무접촉) + 신규 hex 리터럴 0 + 이모지 0.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 3 grep 게이트와 무관 라인 substring 충돌**
- **Found during:** Task 1 (선제 처리) / Task 3 검증 게이트
- **Issue:** 게이트 `grep -c "attributionUnreliable) return \[\]" == 0` 이 **유지 대상**인 estimatedAreaKeypoints 의 `if (!attributionUnreliable) return [];` 까지 substring 매치 — 게이트와 "estimatedArea 강등 유지" 지시가 동시 성립 불가.
- **Fix:** 해당 라인을 brace 형식(`{ return []; }`)으로 재서식 — 의미 byte-동일, 게이트는 제거 대상(focusKeypointsForRecordId 조기 반환)만 검증하게 됨. 추가로 실행자 주석이 게이트 문자열(`deductionBreakdown?.records`)을 포함해 카운트를 2로 만들던 것도 문구 수정.
- **Files modified:** app/src/app/analysis/result.tsx
- **Commit:** d848e469 (재서식) / d1bf271a (조기 반환 제거)

**2. [Rule 3 - Blocking] worktree 에 node_modules 부재 → typecheck 불가**
- **Found during:** Task 1 검증
- **Issue:** 실행 worktree 는 fresh checkout 이라 `app/node_modules`(gitignored) 부재 — `npm run typecheck` 가 `tsc: command not found`.
- **Fix:** 메인 저장소 `/Users/kimtaesung/Dev/SunityMotion/app/node_modules` 를 worktree 에 심링크 (신규 패키지 설치 0, gitignored 라 커밋 무접촉).
- **Files modified:** 없음 (환경 전용)

## 미검증 항목 (실기기·시뮬 확인 대기)

계획 범위 = 코드 + node 테스트 + typecheck. 시뮬 렌더·OTA 는 오케스트레이터가 사이클 후 수행.

| # | 항목 | 안 재본 이유 |
|---|------|-------------|
| 1 | 시간순 번호가 실 doc 의 마커·틱·내역 행에서 일치 렌더 | 시뮬 미기동 — 순수 함수·조립 검증만 (buildDeductionMarkers 시간순 1..N 은 테스트로 실증) |
| 2 | 백오프가 belle 실기기 랜덤 스톨을 실제 회복 | 기기 실패 기제 미규명(F-6) + 재현 조건 없음 — 판정 경로만 테스트로 고정, 실효는 belle 재확인 |
| 3 | '일시정지됨 — 탭하여 계속' 배지 위치·자막 겹침 | 시뮬 미기동 — paddingBottom 96(자막 3줄 zone 위)은 계산 근거만, 렌더 캡처 못 봄 |
| 4 | 파워스핀 큐 2개 연속 발화의 실제 오디오 연속성 | 실 mp3 재생(Polly)·didJustFinish 타이밍은 기기/시뮬에서만 — 체인 선택 로직만 테스트로 고정 |
| 5 | 재생 중 색 반전 시각 결과 (흰 점 + 빨간 큐 부위) | KeypointOverlay 무수정 — prop 조립 분기까지만 검증, 화면 미도달 |
| 6 | 저신뢰(IN-01) doc 의 음성 표면 부위 표시 | 실 저신뢰 doc(엘보 트위스트) 재생 확인 필요 — 조기 반환 제거는 grep + typecheck 로만 확인 |

## Threat Model 처분 결과

| Threat ID | Disposition | 반영 |
|-----------|-------------|------|
| T-fpw-01 | mitigate | 비유한/부재 atVideoSec 방어(+Infinity 후순위)·입력 비변형 — 테스트 4건 고정 |
| T-fpw-02 | mitigate | 스케줄 상한 4회 + 관찰창 75 tick + converge-pause 종결 — 무한 왕복 구조 차단 (sanity 테스트) |
| T-fpw-03 | mitigate | chainSpokenRef 이력 + 자연 종료 한정 + 큐당 CUE_PAUSE_MAX_MS 재무장 — 무한 체인/재발화 차단 |
| T-fpw-04 | accept | belle 08-07 명시 승인 — 음성 표면 한정, 정지 억제 유지 |
| T-fpw-SC | accept | 신규 의존성 0 (node:test/기존 라이브러리만) |

신규 보안 표면(네트워크/auth/스키마) 없음 — Threat Flags 해당 없음.

## Known Stubs

없음 — 4건 전부 데이터 배선 완결 (플레이스홀더·빈 값 스텁 0).

## Commits

| Task | Commit | 제목 |
|------|--------|------|
| 1 | `d848e469` | 감점 번호 측정 순간 시간순 재번호 — 정렬 단일 출처 |
| 2 | `f063b36c` | 재개 백오프 + '탭하여 계속' 배지 + 인접 큐 체이닝 |
| 3 | `d1bf271a` | 재생 중 마커 색 반전 — 활성 큐 부위만 빨강 |

## Self-Check: PASSED

- SUMMARY.md 생성 확인 (ls)
- 수정 8파일 존재 확인 (ls)
- 커밋 3건 존재 확인 (git log: d1bf271a / f063b36c / d848e469)
- 전 스위트 196 pass + typecheck GREEN + 단일 출처 grep == 1 + IN-01 grep == 0
- backend/·app/src/types/ diff 0 (채점·계약 무접촉)
