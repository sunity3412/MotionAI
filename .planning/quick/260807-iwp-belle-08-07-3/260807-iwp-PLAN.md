---
phase: quick-260807-iwp
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/src/lib/voiceSnap.ts
  - app/src/lib/__tests__/voiceSnap.test.ts
  - app/src/lib/driftHysteresis.ts
  - app/src/lib/__tests__/driftHysteresis.test.ts
  - app/src/components/VideoCompare.tsx
  - app/src/components/KeypointOverlay.tsx
  - app/src/app/analysis/result.tsx
autonomous: true
requirements: [BELLE-0807-5, BELLE-0807-6, BELLE-0807-7]
user_setup: []

must_haves:
  truths:
    - "음성 큐 발화로 영상이 멈춘 동안 기준(우) 패널이 그 record 의 짝 프레임 시각(FaultZoomComparison.refVideoSec — 백엔드 방출 기준 도메인 초)으로 이동해, 음성이 말하는 결함의 기준 자세를 보여준다 (BELLE-0807-5)"
    - "재개 직전 기준 패널이 멈춤 시점의 원래 currentTime 으로 복원돼 정렬이 보존되고, 복원 후 기존 재개 로직(백오프 관찰창·nudge)이 그대로 이어진다 (BELLE-0807-5)"
    - "체이닝 연속 발화 시 각 큐마다 제 짝 프레임으로 갱신되고, 복원 목표는 최초 멈춤 시각 하나로 유지된다. refVideoSec 없는 record(실업로드 refMatched=false·legacy doc)는 스냅 없이 현행 유지 — 순간 날조 0 (BELLE-0807-5)"
    - "드리프트 보정이 임계 0.3s + 보정 seek 최소 간격 0.8s 히스테리시스로 동작한다 — 간격 내엔 대기, 간격 경과 후 여전히 초과면 보정(수렴 보장). 연속 seek 로 인한 기준 패널 스터터 완화 (BELLE-0807-6)"
    - "재생 중 학생 오버레이의 관절 점(흰 기본·빨강 활성 큐)이 더 크고 진하게 보인다. 정지 상태 번호 마커·그룹 경계·스켈레톤·기준(우) 패널 렌더는 byte 보존 (BELLE-0807-7)"
    - "채점·doc·백엔드·계약 무접촉: backend/ 와 app/src/types/ diff 0, playbackInvariant.ts·cueTrack.ts diff 0, 음성 정지/재개/체이닝 판정 로직 무변형"
  artifacts:
    - path: "app/src/lib/voiceSnap.ts"
      provides: "buildRefSnapSecs 순수 빌더 — recordId→refVideoSec 스냅 맵 (유한·>=0 만, fabricate 0)"
    - path: "app/src/lib/driftHysteresis.ts"
      provides: "shouldCorrectDrift 순수 판정 + DRIFT_CORRECT_THRESHOLD_S(0.3)/DRIFT_SEEK_MIN_INTERVAL_MS(800) 상수 단일 출처"
    - path: "app/src/components/VideoCompare.tsx"
      provides: "cueRefSnapSecs prop + 음성 멈춤 스냅/복원 배선 + 드리프트 히스테리시스 소비"
    - path: "app/src/components/KeypointOverlay.tsx"
      provides: "playbackEmphasis prop — 재생 중 관절 점 배율/외곽선 강화 (기본 false = 기존 렌더 byte 보존)"
    - path: "app/src/app/analysis/result.tsx"
      provides: "cueRefSnapSecs 파생(matchZoomForRecord 재사용) + playbackEmphasis 전달"
  key_links:
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/lib/voiceSnap.ts"
      via: "cueRefSnapSecs useMemo 가 records + matchZoomForRecord 로 buildRefSnapSecs 호출 (신규 조인 규칙 0 — recordId 원자 조인)"
      pattern: "buildRefSnapSecs"
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/components/VideoCompare.tsx"
      via: "cueRefSnapSecs prop 전달"
      pattern: "cueRefSnapSecs"
    - from: "app/src/components/VideoCompare.tsx"
      to: "app/src/lib/driftHysteresis.ts"
      via: "follow/legacy 양 드리프트 보정 지점이 shouldCorrectDrift 를 호출하고 seek 시 lastDriftSeekAtRef 갱신"
      pattern: "shouldCorrectDrift"
    - from: "app/src/app/analysis/result.tsx"
      to: "app/src/components/KeypointOverlay.tsx"
      via: "leftOverlay 에서 playbackEmphasis={playingInversion} 전달 (재생 중에만 true)"
      pattern: "playbackEmphasis"
---

<objective>
belle 08-07 오후 실기기 피드백 3건 수리 (fpw OTA 3827392e 확인 후) — 전부 앱 전용, 채점·doc·백엔드 무접촉.

1. (BELLE-0807-5) 음성 멈춤 동안 기준 패널 짝 프레임 스냅 — belle "정은지 선수 영상이 음성이랑 안 맞는다. 학생 영상은 맞는데". 학생 패널은 잰 순간(atVideoSec)에 정지해 맞는 게 보장되지만, 기준 패널은 시작점 오프셋만 맞춘 시간 동기 위치라 자세 짝이 아니다. 자세 짝 데이터는 이미 있다 — FaultZoomComparison 의 refVideoSec(백엔드 F-3 방출, 기준 도메인 초). 발화 멈춤 동안 우측을 짝 시각으로 seek, 재개 직전 원위치 복원.
2. (BELLE-0807-6) 드리프트 보정 히스테리시스 — belle "정은지 선수 영상이 끊겨 가지구". 현행은 100ms tick 마다 drift>0.2s 면 즉시 seek(Build 16 "stutter 위험 < 동기화 우선" 절충) — 기기에서 잦은 seek = 기준 패널 스터터. belle 관측이 재균형 근거: 임계 0.2→0.3s + 보정 seek 최소 간격 0.8s.
3. (BELLE-0807-7) 재생 중 오버레이 점 진하게 — belle "마커는 좀 더 진하면 좋을 듯". fpw 가 넣은 재생 중 흰 기본 점·빨강 활성 큐 점의 크기·외곽선 강화. 정지 상태 번호 마커는 무접촉.

Purpose: 음성 안내 순간에 기준 패널이 "음성이 말하는 그 자세"를 보여주고, 재생이 덜 끊기고, 재생 중 마커가 읽힌다.
Output: 위 3건이 반영된 앱 코드 + 신규 순수 모듈 2개(voiceSnap/driftHysteresis) + node --test 신규 케이스 + 전 스위트/typecheck GREEN. 시뮬·OTA 는 오케스트레이터가 사이클 후 수행 (계획 범위 밖).
</objective>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@app/src/components/VideoCompare.tsx
@app/src/components/KeypointOverlay.tsx
@app/src/app/analysis/result.tsx
@app/src/types/analysis.ts
@app/src/lib/cueTrack.ts
@app/src/lib/playbackInvariant.ts
@app/src/lib/__tests__/cueTrack.test.ts
</context>

<planner_findings>
플래너가 실측·전수 grep 으로 확정한 사실 (실행자는 재조사 불요, 인용해 사용):

1. **스냅 시각의 유일한 정당 소스 = `FaultZoomComparison.refVideoSec`** (types/analysis.ts:485~518). task_spec 의 "refFrameIdx / ref fps" 는 이 필드로 실현된다 — 백엔드(33-G §C-1 F-3 fix)가 기준 도메인 초를 이미 방출한다. analysis.ts:507 이 명시적으로 경고: "`refFrameIdx / keypointReport.fps` 로 초를 **재계산하지 말 것**" — rep 프레임 공간(18fps)과 영상 초 공간(9fps)의 불일치가 F-3 의 근본원인이었다. `refVideoSec` 부재 = `refMatched=false`(실업로드 대응 실패) 또는 legacy doc → **스냅 생략** (task_spec "없으면 스냅 생략, fabricate 0"과 정합). refFrameIdx 나눗셈을 앱에 재도입하는 것은 금지.
2. **음성 멈춤 중 드리프트 보정은 현재도 미진입 (실측 판독 완료)**: follow 보정 블록(VideoCompare:990~)은 `leftPlaying` 가드, legacy 블록(1026~)은 `bothPlaying` 가드 — 발화 pause 로 양쪽이 멈추면 둘 다 스킵된다. playbackInvariant R3 도 voicePaused 중 양쪽 정지면 NONE. **신규 게이트 코드 불요** — 스냅 배선 주석에 이 판독 근거만 박제 (task_spec "판독 후, 돌면 게이트" 요건의 판독 결과 = 안 돈다).
3. **`voicePauseRef.current = false` 리셋 지점 전수 5곳** — 스냅 상태 정리를 같은 지점에 건다: tick 재개 경로 860(play() 직전 — **복원**), togglePlay pause 분기 1138·play 분기 1146(사용자 제스처 — **복원**), seekBoth 1264·scrub 1385(직후 setRightToStudentTime 재-seek — **클리어만**, 복원 seek 까지 하면 이중 seek 스터터).
4. **복원 직후 play() 의 seek 미적용 스톨 위험은 기존 안전망이 흡수**: Build 15 선례(REPLAY_SEEK_DELAY_MS — seek 직후 play 는 정지 위험)가 있으나, 재개 경로는 fpw 백오프 관찰창(`resumeWatchTicksRef=0` + RESUME_RETRY_AT_TICKS 0.5/1/2/3초 재시도 + 마지막 직전 제자리 seek nudge)이 재개 실효를 감시한다. 별도 지연 불요 — task_spec "복원 후 기존 재개 로직이 그대로 이어진다"가 이 구조를 지칭.
5. **`DRIFT_CORRECT_THRESHOLD_S` 사용 전수**: 정의 304 + follow 보정 1022 + legacy 보정 1042. 정책 서술 주석 293~306(Build 16 블록)·444~450·890~894 도 "매 tick 즉시 보정"을 서술하므로 함께 갱신. `START_SYNC_THRESHOLD_S`(togglePlay 시작 동기)·`START_HOLD_EPS_S`(음수 오프셋 시작 홀드, 1012~1015 의 `currentTime = 0` 은 드리프트 보정 아님) 는 별개 — 무접촉.
6. **KeypointOverlay 점 크기 상수는 정지 마커와 공유 — 전역 상향 금지**: `RADIUS=(10*S)/H`, `RADIUS_HI=(14*S)/H`, `STROKE_CIRCLE_OUTLINE=(1.5*S)/H`, `_HI=(2.4*S)/H` (355~360). 같은 상수를 정지 상태 번호 마커·주황 참고 점이 쓴다. 재생 중만 키우려면 **신규 opt-in prop 게이트 배율**이 유일한 안전 경로 (기본 false = 기존 렌더 byte 보존). 흰 점 어두운 외곽선은 기존 `'rgba(0,0,0,0.6)'`(758) — alpha 계수 조정은 허용, 신규 hex 색 리터럴 0.
7. **재생 중 점 렌더 실태**: 오버레이 토글 OFF 재생 중엔 활성 큐 빨간 점(isHi)만 뜨고(739 게이트), 토글 ON 이면 흰 기본 점+본. belle "마커 진하게"는 이 재생 표면 — result.tsx leftOverlay 의 `playingInversion`(opts.isPlaying===true) 이 이미 재생 판별 신호다. 음성 멈춤 중(isPlaying=false)은 emphasis 미발동 → 음성 중 강조(dim·펄스) 승인 렌더 무접촉.
8. **recordId 원자 조인 유지**: `matchZoomForRecord`(result.tsx:1865, matchZoomForDeductionRecord 단일 출처)를 cueWindows·recordMaps 가 이미 공용한다. 신규 스냅 맵도 같은 매처를 재사용하면 신규 조인 규칙 0.
9. **테스트 러너**: Node 24 type stripping, `node --test <파일>` 파일 단위 루프(디렉터리 일괄 실행 깨짐), node:test/node:assert 만, `.ts` 확장자 import. 기준선 = 13파일 196 tests (fpw 종료 시점).
10. **mode 분기 불요**: mode3 doc 의 refVideoSec 도 우측 패널이 재생하는 바로 그 영상(지난 영상) 도메인 초다 — 맵 파생은 mode 무관, 데이터 부재면 자동 생략.
</planner_findings>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 음성 멈춤 동안 기준 패널 짝 프레임 스냅 + 재개 복원 (BELLE-0807-5)</name>
  <files>app/src/lib/voiceSnap.ts, app/src/lib/__tests__/voiceSnap.test.ts, app/src/app/analysis/result.tsx, app/src/components/VideoCompare.tsx</files>
  <behavior>
    voiceSnap.test.ts (node:test, cueTrack.test.ts 관례):
    - buildRefSnapSecs: {recordId,refVideoSec} 유효 쌍 → 맵 등재 (r01→6.44 등)
    - refVideoSec 부재/NaN/Infinity/음수 쌍 → 드롭 (fabricate 0)
    - recordId 부재/빈 문자열 쌍 → 드롭
    - 중복 recordId → first-wins (결정성)
    - 입력 null/undefined/빈 배열 → 빈 맵 (크래시 0)
  </behavior>
  <action>
    (a) `app/src/lib/voiceSnap.ts` 신규 — 순수 함수만 (react/player 의존 0, cueTrack.ts 헤더 관례). `buildRefSnapSecs(entries: readonly { recordId?: string; refVideoSec?: number }[] | null | undefined): Record<string, number>` — recordId 가 비어있지 않은 문자열이고 refVideoSec 이 유한 ≥0 인 쌍만 등재, 중복 first-wins. 헤더 주석에 출처(belle 08-07 "정은지 영상이 음성이랑 안 맞는다", quick-260807-iwp)와 refVideoSec 만 쓰는 근거(F-3 — refFrameIdx/fps 재계산 금지, planner_findings 1) 명기.

    (b) result.tsx — `cueRefSnapSecs` useMemo 신설: records 를 순회해 `{ recordId: rec.recordId, refVideoSec: matchZoomForRecord(rec)?.refVideoSec }` 배열을 만들고 buildRefSnapSecs 로 맵 산출 (isRecordHidden 필터는 cueWindows 와 동일하게 적용 — 숨김 record 는 발화 자체가 없으니 스냅 대상도 아님). deps 는 cueWindows memo 관례 준수. VideoCompare 에 `cueRefSnapSecs={cueRefSnapSecs}` 전달. **신규 조인 규칙 금지** — matchZoomForRecord 재사용 (planner_findings 8).

    (c) VideoCompare.tsx — 신규 prop `cueRefSnapSecs?: Record<string, number>` (미전달 = 기존 렌더/동작 diff 0, opt-in 관례). ref 미러 `cueRefSnapSecsRef`(alignmentRef 관례 — tick stale 클로저 회피) + `voiceSnapRestoreSecRef = useRef<number | null>(null)`.

    헬퍼 3개 (컴포넌트 내부):
    - `snapRightToCuePair(recordId)`: sec = 맵 조회. 없으면 `unsnapRight()` 호출(체인이 짝 없는 큐로 넘어가면 이전 큐의 스냅 프레임을 새 큐에 오귀속시키지 않게 원위치 복귀). 있으면: restoreRef 가 null 일 때만 `rightPlayer.currentTime` 저장(최초 멈춤 시각 = 복원 목표 단일 유지) 후 `rightPlayer.currentTime = sec`.
    - `unsnapRight()`: restoreRef 비-null 이면 rightPlayer.currentTime 복원 + null 클리어. (멈춤 중 재생은 정지 상태라 복원값 = 원 정렬 위치 그대로.)
    - `clearVoiceSnapOnly()`: restoreRef = null (복원 seek 없이 상태만 정리).

    호출 지점 (planner_findings 3 전수):
    - 발화 시작 pause 분기(795~808, `voicePauseRef.current = true` 직후): `snapRightToCuePair(cue.recordId)`. 정지 상태 중 발화(멈춤 없는 발화) 경로는 무접촉 — 스냅은 "큐 발화로 정지하는 동안"만.
    - 체인 발화 분기(844~856, chainStarted 후): `snapRightToCuePair(chained.recordId)` — 큐마다 제 짝 프레임 갱신.
    - tick 재개 경로(860~864): `leftPlayer?.play()` **직전** `unsnapRight()` — 복원 후 백오프 관찰창이 그대로 이어짐 (planner_findings 4, 별도 지연 금지).
    - togglePlay pause 분기(1138)·play 분기(1146): `unsnapRight()` (사용자 제스처 — 정렬 보존 복원).
    - seekBoth(1264)·scrub 핸들러(1385): `clearVoiceSnapOnly()` (직후 재-seek 가 정렬 재확립 — 이중 seek 금지).

    스냅 배선 주석에 판독 근거 박제: "음성 멈춤 중 follow(leftPlaying)/legacy(bothPlaying) 드리프트 보정은 가드로 미진입 — 신규 게이트 불요" (planner_findings 2). usc 불변식·정지/재개·체이닝 **판정** 로직(playbackInvariant.ts·cueTrack.ts·decidePlaybackInvariant 호출부) byte 무접촉. 주석 한국어 + 출처(belle 08-07, quick-260807-iwp). ⚠ VideoCompare 주석에 `refFrameIdx` 문자열을 쓰지 말 것(아래 grep=0 게이트 자기무효화 방지) — 나눗셈 금지 근거 서술은 voiceSnap.ts 헤더가 담당.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && node --test app/src/lib/__tests__/voiceSnap.test.ts && (cd app && npm run typecheck) && [ "$(grep -c 'refFrameIdx' app/src/components/VideoCompare.tsx)" = "0" ] && [ "$(grep -c 'buildRefSnapSecs(' app/src/app/analysis/result.tsx)" = "1" ] && git diff HEAD --exit-code -- app/src/lib/playbackInvariant.ts app/src/lib/cueTrack.ts</automated>
  </verify>
  <done>발화 멈춤 동안 우측 패널이 record 짝 시각(refVideoSec)으로 seek 되고, 체인마다 갱신되며(짝 없으면 복귀), 재개·사용자 제스처에서 원위치 복원 후 기존 백오프가 이어진다. refVideoSec 부재 record 는 스냅 0. VideoCompare 에 refFrameIdx 나눗셈 미도입. voiceSnap 테스트 PASS + typecheck GREEN + playbackInvariant.ts/cueTrack.ts diff 0 (HEAD 기준 — git add 무력화 방지).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 드리프트 보정 히스테리시스 — 임계 0.3s + seek 최소 간격 0.8s (BELLE-0807-6)</name>
  <files>app/src/lib/driftHysteresis.ts, app/src/lib/__tests__/driftHysteresis.test.ts, app/src/components/VideoCompare.tsx</files>
  <behavior>
    driftHysteresis.test.ts:
    - drift 0.25 (임계 이하) → false — 언제든
    - drift 0.35, 마지막 seek 후 0.2s → false (간격 내 대기)
    - drift 0.35, 마지막 seek 후 0.9s → true (간격 후 여전히 초과면 보정 — 수렴 보장)
    - drift 0.35, lastSeekAt 0 (최초) → true (첫 보정은 즉시 허용)
    - 경계: 간격 정확히 800ms 경과 → true (>= 판정)
    - NaN/비유한 drift → false (크래시 0)
    - 상수 박제: DRIFT_CORRECT_THRESHOLD_S === 0.3, DRIFT_SEEK_MIN_INTERVAL_MS === 800
  </behavior>
  <action>
    (a) `app/src/lib/driftHysteresis.ts` 신규 — 순수 함수만 (playbackInvariant.ts 관례: 상수를 순수 모듈이 소유하고 VideoCompare 가 import). export: `DRIFT_CORRECT_THRESHOLD_S = 0.3`, `DRIFT_SEEK_MIN_INTERVAL_MS = 800`, `shouldCorrectDrift(driftS: number, nowMs: number, lastSeekAtMs: number): boolean` = 유한 drift > 임계 AND (nowMs - lastSeekAtMs) >= 최소 간격. 헤더 주석에 재균형 근거 인용: Build 16(iter-2)이 UAT 5차 drift 1-2s 누적으로 hysteresis 를 제거하고 "stutter 위험 < 동기화 우선" 절충을 택했으나, belle 08-07 실기기 "정은지 선수 영상이 끊겨 가지구" 관측이 재균형 근거 — 임계 0.2→0.3s + 연속 seek 금지(0.8s 간격). 간격 내엔 대기하고 간격 후 여전히 초과면 보정하므로 동기화 수렴은 보장된다(tick 100ms 상시 재판정).

    (b) VideoCompare.tsx — 로컬 `const DRIFT_CORRECT_THRESHOLD_S = 0.2`(304) 삭제, driftHysteresis 에서 import. `lastDriftSeekAtRef = useRef(0)` 신설(follow/legacy 는 한 tick 에 하나만 돌므로 공유 1개). 보정 지점 2곳 치환:
    - follow(1020~1024): `if (shouldCorrectDrift(drift, Date.now(), lastDriftSeekAtRef.current)) { rightPlayer.currentTime = target; lastDriftSeekAtRef.current = Date.now(); }`
    - legacy(1041~1050): 동일 패턴 (양쪽 back-seek 도 보정 seek — 간격 공유).
    START_SYNC_THRESHOLD_S·START_HOLD_EPS_S·시작 홀드 `currentTime = 0`(1015)·togglePlay/replay 경로는 무접촉 (planner_findings 5).

    (c) 정책 서술 주석 갱신 — Build 16 상수 블록(293~306)에 이번 재균형 항목 추가(belle 08-07 출처 + Build 16 이력 유지), "매 tick 즉시 보정" 서술(444~450·890~894)을 새 정책(임계 0.3 + 0.8s 간격 히스테리시스)으로 정정. usc 불변식·정지/재개·체이닝 로직과 playbackInvariant.ts 는 byte 무접촉.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && node --test app/src/lib/__tests__/driftHysteresis.test.ts && node --test app/src/lib/__tests__/playbackInvariant.test.ts && (cd app && npm run typecheck) && [ "$(grep -c 'const DRIFT_CORRECT_THRESHOLD_S' app/src/components/VideoCompare.tsx)" = "0" ] && [ "$(grep -c 'shouldCorrectDrift(drift' app/src/components/VideoCompare.tsx)" = "2" ] && git diff HEAD --exit-code -- app/src/lib/playbackInvariant.ts</automated>
  </verify>
  <done>보정이 임계 0.3s + 최소 간격 0.8s 로만 발사되고(2곳 모두), 간격 후 잔존 drift 는 반드시 보정된다(수렴). 상수는 driftHysteresis.ts 단일 출처, VideoCompare 로컬 정의 0. 주석에 belle 08-07 근거 + Build 16 절충 이력. driftHysteresis/playbackInvariant 테스트 PASS + typecheck GREEN + playbackInvariant.ts diff 0.</done>
</task>

<task type="auto">
  <name>Task 3: 재생 중 오버레이 점 시인성 강화 — playbackEmphasis (BELLE-0807-7)</name>
  <files>app/src/components/KeypointOverlay.tsx, app/src/app/analysis/result.tsx</files>
  <action>
    (a) KeypointOverlay.tsx — 신규 prop `playbackEmphasis?: boolean` (기본 false = 기존 렌더 byte 보존 — 정지 상태 번호 마커·주황 참고 점·그룹 경계·본/스켈레톤 무접촉이 구조로 성립, planner_findings 6). 배율 상수 `PLAYBACK_EMPHASIS_SCALE = 1.3` 신설(FULLSCREEN_OVERLAY_SCALE 관례 — belle 실기기 확인 후 미세조정 가능하게 상수화, 주석에 belle 08-07 "마커는 좀 더 진하면 좋을 듯" 출처). keypoint circles 렌더 루프(728~804)에만 적용:
    - 원 반지름: `RADIUS`/`RADIUS_HI` 에 emphasis 배율 곱 (흰 기본 점·빨강 활성 점 공통).
    - 외곽선 두께: `STROKE_CIRCLE_OUTLINE`/`_HI` 에 동일 배율 곱.
    - 흰 점 어두운 외곽선: 기존 `'rgba(0,0,0,0.6)'` 의 alpha 계수를 emphasis 시 0.8 로 상향 (밝은 배경 대비 확보 — 기존 스타일 계수 조정, **신규 hex/브랜드 색 리터럴 0**, colors 토큰 외 신규 색 금지).
    bones·axis·group/focus 도형·번호 텍스트(재생 중엔 어차피 억제됨)는 무접촉.

    (b) result.tsx — leftOverlay 의 KeypointOverlay 에 `playbackEmphasis={playingInversion}` 전달 (재생 중에만 true — 음성 멈춤 중(isPlaying=false)·정지 상태는 false 라 승인 렌더 보존, planner_findings 7). rightOverlay(기준 패널)는 무접촉 — belle 지적 표면은 fpw 가 넣은 학생 측 재생 점. 주석 한국어 + 출처(belle 08-07, quick-260807-iwp).

    (c) 마감 게이트 겸 전체 회귀: 전 스위트 파일 단위 루프 + typecheck + 무접촉 증명 일괄 실행.
  </action>
  <verify>
    <automated>cd /Users/kimtaesung/Dev/SunityMotion && (cd app && npm run typecheck) && for f in app/src/lib/__tests__/*.test.ts app/src/lib/__tests__/*.test.mjs app/src/lib/pickerFailure.test.ts; do node --test "$f" || exit 1; done && [ "$(grep -c 'playbackEmphasis' app/src/components/KeypointOverlay.tsx)" -ge "2" ] && [ "$(grep -c 'playbackEmphasis={playingInversion}' app/src/app/analysis/result.tsx)" = "1" ] && [ "$(git diff HEAD -- app/src | grep -cE '^\+.*#[0-9a-fA-F]{6}')" = "0" ] && git diff HEAD --stat -- backend/ app/src/types/ | wc -l | grep -q '^ *0$'</automated>
  </verify>
  <done>재생 중 학생 오버레이 점(흰 기본·빨강 활성)이 1.3배 크기 + 두꺼운 외곽선 + 흰 점 어두운 외곽선 alpha 0.8 로 렌더된다. playbackEmphasis 기본 false 라 정지 상태·음성 멈춤·기준 패널·전체화면 정지 렌더는 byte 보존. 전 스위트(기준선 196 + 신규) PASS + typecheck GREEN + 신규 hex 리터럴 0 + backend/·types/ diff 0.</done>
</task>

</tasks>

<verification>
전 태스크 공통 게이트 (계획 범위 = 코드 + node 테스트 + typecheck. 시뮬 렌더·OTA·belle 실기기 확인은 오케스트레이터가 사이클 후 수행):

1. 전체 스위트: `for f in app/src/lib/__tests__/*.test.ts app/src/lib/__tests__/*.test.mjs app/src/lib/pickerFailure.test.ts; do node --test "$f" || exit 1; done` — 전 파일 PASS (기준선 196 tests + voiceSnap/driftHysteresis 신규. 파일 단위 루프 — 디렉터리 일괄 실행 깨짐).
2. `cd app && npm run typecheck` GREEN.
3. 무접촉 증명 (HEAD 기준 — `git add` 무력화 방지): `git diff HEAD --exit-code -- app/src/lib/playbackInvariant.ts app/src/lib/cueTrack.ts` 통과 + `git diff HEAD --stat -- backend/ app/src/types/` 빈 출력.
4. 관례: 주석 한국어 + 출처 인용(belle 08-07, quick-260807-iwp), 이모지 0, 신규 hex 색 리터럴 0 (테마 토큰·기존 rgba 계수 조정만).
</verification>

<success_criteria>
- BELLE-0807-5: 음성 멈춤 동안 기준 패널이 record 의 refVideoSec 짝 시각을 보여주고, 재개 직전 원위치 복원으로 정렬 보존. 짝 없는 record 는 스냅 0 (날조 0). 체인마다 제 짝 갱신.
- BELLE-0807-6: 드리프트 보정 임계 0.3s + seek 최소 간격 0.8s — 간격 내 대기·간격 후 보정(수렴 보장). 상수·판정 순수 모듈 단일 출처 + 재균형 근거 주석.
- BELLE-0807-7: 재생 중 학생 오버레이 점 크기·외곽선 강화 (opt-in prop — 정지 렌더 byte 보존).
- 전 스위트 + typecheck GREEN, 채점·doc·백엔드·계약 무접촉, playbackInvariant.ts·cueTrack.ts diff 0.
</success_criteria>

<output>
완료 시 `.planning/quick/260807-iwp-belle-08-07-3/260807-iwp-SUMMARY.md` 생성 (summary.md 템플릿).
</output>
