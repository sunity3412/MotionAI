---
phase: quick-260806-usc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/src/lib/playbackInvariant.ts
  - app/src/lib/__tests__/playbackInvariant.test.ts
  - app/src/components/VideoCompare.tsx
autonomous: true
requirements: [V-1, D-13]
must_haves:
  truths:
    - "음성 큐 정지 중에는 두 영상 중 어느 쪽도 혼자 진행하지 않는다 (한쪽이 playing 이면 그 tick 에 pause)"
    - "음성 종료 재개 직후 관찰창 안에서 한쪽만 도는 상태가 지속되면, 안 도는 쪽에 play() 를 재시도한다"
    - "재시도 한도를 넘겨도 편측이면 양쪽을 함께 멈춘다 (어긋난 채 진행 금지 — 정렬 보존, 사용자가 재생 버튼으로 재개)"
    - "시작 홀드(rawComposedRef<0, right 의도적 정지)는 편측으로 오판되지 않는다"
    - "scrubbing 중 / 관찰창 밖 정상 주행 중에는 개입이 0 이다"
    - "사용자 제스처(재생·정지·seek·오프셋 조작)는 관찰창을 닫아 감시가 사용자와 싸우지 않는다"
  artifacts:
    - path: "app/src/lib/playbackInvariant.ts"
      provides: "tick 개입 판정 순수 함수 + 관찰창/재시도 상수"
      exports: ["decidePlaybackInvariant", "RESUME_WATCH_TICKS", "RESUME_PLAY_RETRIES"]
    - path: "app/src/lib/__tests__/playbackInvariant.test.ts"
      provides: "불변식 판정 12축 검증 (node --test, 신규 의존성 0)"
    - path: "app/src/components/VideoCompare.tsx"
      provides: "tick 안 집행 블록 + 관찰창 ref 2개 + 제스처 4곳 창 닫기"
      contains: "decidePlaybackInvariant"
  key_links:
    - from: "app/src/components/VideoCompare.tsx (tick)"
      to: "decidePlaybackInvariant"
      via: "followTick 산출 직후 · follow/drift 블록 직전 호출"
      pattern: "decidePlaybackInvariant\\("
    - from: "tick F-1 재개 블록 (voicePauseRef=false 전이)"
      to: "resumeWatchTicksRef / resumeRetriesRef"
      via: "재개 순간 관찰창 개시(0) + 재시도 카운터 리셋"
      pattern: "resumeWatchTicksRef\\.current = 0"
---

<objective>
동작비교(VideoCompare)의 재생 상태가 **편측으로 갈라지는 것을 tick 마다 차단**한다.

33-13 **D-13** 승인 설계의 불변식 = "음성 중엔 두 영상이 함께 멈추고, 끝나면 함께 돈다".
현재 코드는 이 불변식을 **전이 순간에 한 번만** 집행한다(pause 2줄 / play 2줄). 그 호출이
실기기에서 한쪽만 실효하면 되돌릴 주체가 없어 그대로 갈라진 채 남는다 — belle 실기기 V-1
(엘보 doc: 내 영상 4.9s 동결, 정은지만 10초대까지 진행, 음성 종료 후에도 미재개).

Purpose: 원인을 추측해 고치는 것이 아니라(시뮬 iOS 26.5 개발빌드 #29 에서 재현 안 됨 —
큐1 4.1/4.2 동시 정지, 종료 후 양쪽 재개, 큐2 6.7/6.7 동시 정지, 최종 13.3/13.5 동기 주행 =
**상태머신은 이상 조건에서 옳다**), 불변식을 **상시 감시·집행**해 원인이 무엇이든(재버퍼 스톨,
mid-tick 레이스, play() 무실효) 편측 상태가 100ms 이상 지속되지 못하게 한다.

Output: 순수 판정 함수 1개(+테스트) + VideoCompare tick 안 집행 블록 1개.
</objective>

<source_audit>

| 출처 | 항목 | 상태 | 담는 곳 |
|---|---|---|---|
| GOAL | V-1 편측 정지/미재개 차단 | COVERED | Task 2 (tick 집행 블록) |
| REQ | V-1 (CONTINUE-2026-08-01 §08-06 밤) | COVERED | Task 1 판정 + Task 2 집행 |
| CONTEXT | **D-13** 불변식 "함께 멈추고 함께 돈다" | COVERED | Task 1 `decidePlaybackInvariant` 규칙 전체 |
| CONTEXT | 기존 F-1/F-2 조기 return 보존 | COVERED | Task 2 (무접촉 + 게이트) |
| CONTEXT | 시작 홀드·right 소유권 충돌 금지 | COVERED | Task 1 `startHold` 예외 + Task 2 배치 순서 |
| CONTEXT | scrubbing 중 개입 금지 | COVERED | Task 1 최우선 가드 |

**범위 밖(고의)**: V-2(시작 직후 발화)·V-3(목록 미확보)·EAS OTA·실기기 실효 확인.
V-1 원인 규명은 하지 않는다 — 원인 불명 상태에서 **결과 상태를 불변식으로 수렴**시키는 수리다.
</source_audit>

<execution_context>
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/workflows/execute-plan.md
@/Users/kimtaesung/Dev/SunityMotion/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/CLAUDE.md
@.planning/CONTINUE-2026-08-01.md
@app/src/components/VideoCompare.tsx
@app/src/lib/manualOffset.ts
@app/src/lib/__tests__/manualOffset.test.ts
</context>

<interface_contract>
읽고 시작할 것 — 실행자가 코드베이스를 뒤지지 않게 여기에 계약을 박는다.

**기존 tick 좌표 (app/src/components/VideoCompare.tsx, 현 HEAD 기준)**

| 위치 | 내용 |
|---|---|
| 313 | `const CUE_PAUSE_MAX_MS = 15000;` (안전 상한) |
| 411 | `const scrubbingRef = useRef(false);` |
| 554-555 | `voicePauseRef` / `voicePauseStartRef` 선언 |
| 649-878 | tick `useEffect` 전체 (`setInterval(tick, TICK_INTERVAL_MS=100)`) |
| 668-670 | `leftPlaying` / `bothPlaying` 캡처, `setPlaying(!!ref?.playing)` |
| 689-713 | 큐 발화 → `leftPlayer?.pause(); rightPlayer?.pause();` + `voicePauseRef=true` + **F-2 조기 return** |
| 720-737 | 음성 종료/overMax → `voicePauseRef=false` + `leftPlayer?.play(); rightPlayer?.play();` + **F-1 조기 return** |
| 752-757 | `aTick` / `activeTick` / `followTick` 산출 |
| 758-819 | follow/drift 블록 (right 소유권). 779-783 = 시작 홀드 `rawComposedRef < 0` → `rightPlayer.pause()` |
| 856-859 | `shouldPauseAtEnd` → 양쪽 pause |

**사용자 제스처가 `voicePauseRef.current = false` 를 놓는 4곳** (전부 관찰창도 닫아야 함):
906 `togglePlay`(정지) · 910 `togglePlay`(재생) · 1013 `seekBoth` · 1132 `markOffsetApplying`.
(724 는 tick 재개 블록 — 여기는 창을 **연다**.)

**신규 순수 함수 계약 (Task 1 이 정의, Task 2 가 소비)**

```
decidePlaybackInvariant(input: PlaybackInvariantInput): PlaybackInvariantDecision

PlaybackInvariantInput = {
  hasLeft: boolean; hasRight: boolean;
  scrubbing: boolean; voicePaused: boolean;
  leftPlaying: boolean; rightPlaying: boolean;
  resumeWatchTicks: number | null;   // null = 관찰창 밖, 0.. = 재개 후 경과 tick
  resumeRetriesUsed: number;
  startHold: boolean;                // rawComposedRef<0 — right 가 의도적 정지
}

PlaybackSideCommand = 'play' | 'pause' | 'leave'
PlaybackInvariantDecision = {
  action: 'none' | 'enforce-pause' | 'retry-play' | 'converge-pause';
  left: PlaybackSideCommand; right: PlaybackSideCommand;
  consumeRetry: boolean;   // true → 컴포넌트가 재시도 카운터 +1
  closeWatch: boolean;     // true → 컴포넌트가 관찰창을 닫음(null)
}

RESUME_WATCH_TICKS = 10    // 100ms tick × 10 = 재개 후 1초만 감시
RESUME_PLAY_RETRIES = 3    // play() 재시도 3회(≈300ms) 후 대칭 정지로 수렴
```
</interface_contract>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 불변식 판정 순수 함수 + 테스트</name>
  <files>app/src/lib/playbackInvariant.ts, app/src/lib/__tests__/playbackInvariant.test.ts</files>
  <behavior>
    판정 규칙 (우선순위 순 — 위에서 걸리면 아래는 보지 않는다):
    - R1: `!hasLeft || !hasRight` → `none`. 한쪽 패널만 있는 화면엔 대칭 개념이 없다.
    - R2: `scrubbing` → `none`. 사용자 제스처 우선(기존 tick 규율과 동일).
    - R3: `voicePaused` → 도는 쪽만 `pause`. 둘 다 정지면 `none`.
          action=`enforce-pause`, consumeRetry=false, closeWatch=false.
    - R4: `resumeWatchTicks === null || resumeWatchTicks > RESUME_WATCH_TICKS` → `none`.
          **관찰창 밖 정상 주행에는 절대 개입하지 않는다** (D-13 두 국면에만 개입).
    - R5: `leftPlaying === rightPlaying` → `none`. 양쪽 재생/양쪽 정지 = 대칭 = 정상.
          (양쪽이 아직 spin-up 중인 false/false 를 위반으로 오판하지 않기 위한 축.)
    - R6: `startHold && leftPlaying && !rightPlaying` → `none`. 시작 홀드는 **의도된** 편측.
          역방향(left 정지 / right 재생)은 면제 대상이 아니다.
    - R7: `resumeRetriesUsed < RESUME_PLAY_RETRIES` → action=`retry-play`,
          안 도는 쪽 `play` / 도는 쪽 `leave`, consumeRetry=true.
    - R8: 그 외(재시도 소진 + 여전히 편측) → action=`converge-pause`,
          left=`pause`, right=`pause`, closeWatch=true.

    테스트 축 (node:test + node:assert/strict, `.ts` 확장자 import — manualOffset.test.ts 관례):
    1. voicePaused + right 만 재생 → enforce-pause, left='leave', right='pause'
    2. voicePaused + 양쪽 재생 → 양쪽 'pause'
    3. voicePaused + 양쪽 정지 → none (불필요한 pause 호출 0)
    4. scrubbing 이면 voicePaused + 편측이어도 none (R2 가 R3 를 이긴다)
    5. hasRight=false → none
    6. resumeWatchTicks=null + 편측 → none (관찰창 밖 무개입)
    7. resumeWatchTicks=RESUME_WATCH_TICKS+1 + 편측 → none (창 만료)
    8. 창 안 + 양쪽 재생 → none / 창 안 + 양쪽 정지 → none
    9. 창 안 + left 정지·right 재생 + retries=0 → retry-play, left='play', right='leave', consumeRetry
    10. 창 안 + 같은 상태 + retries=RESUME_PLAY_RETRIES → converge-pause, 양쪽 'pause', closeWatch
    11. startHold + left 재생·right 정지 → none (시작 홀드 면제)
    12. startHold + left 정지·right 재생 → retry-play (면제는 단방향)
  </behavior>
  <action>
    `app/src/lib/playbackInvariant.ts` 신설. 위 계약대로 타입 3개 + 상수 2개 + 순수 함수 1개만
    export 한다. React·expo-video·타이머 import 0 (순수 로직 — manualOffset.ts 와 동일 성격).
    분기는 위 R1~R8 순서를 코드 순서로 그대로 옮긴다(읽는 사람이 우선순위를 코드에서 본다).

    파일 상단 주석에 **왜**를 적는다 — 출처 인용 필수, 이모지 금지:
    `260806-usc — V-1: belle 실기기 편측 정지/미재개, 시뮬 미재현 → 불변식 집행`.
    이어서 (a) 33-13 D-13 불변식 원문, (b) 시뮬에서 재현되지 않았다는 사실과 그래서
    원인 수리가 아니라 결과 수렴 수리라는 것, (c) R5 가 "양쪽 정지"를 정상으로 보는 이유
    (play() 직후 양쪽이 아직 spin-up 중일 수 있음 — 대칭이면 건드리지 않는다),
    (d) R6 시작 홀드 면제 근거(32-08 실기기 피드백 #1, follow 블록이 right 를 소유)를 적는다.
    상수 2개에는 산출 근거를 적는다: tick 100ms × 10 = 재개 후 1초만 감시(그 밖은 사용자
    영역), 재시도 3회 ≈ 300ms 안에 못 돌면 갈라진 채 진행하는 것보다 대칭 정지가 낫다.

    테스트 파일은 `manualOffset.test.ts` 헤더 형식을 그대로 따른다(실행법 주석 + 신규
    npm 의존성 0 명시 + `../playbackInvariant.ts` 확장자 import).
  </action>
  <verify>
    <automated>node --test app/src/lib/__tests__/playbackInvariant.test.ts</automated>
    <automated>npm --prefix app run typecheck</automated>
    <automated>cd app &amp;&amp; grep -v '^\s*//' src/lib/playbackInvariant.ts | grep -c "from 'react'\|expo-video\|setTimeout\|setInterval" | grep -qx 0</automated>
  </verify>
  <done>
    12축 전부 pass. typecheck GREEN(무출력). 순수성 게이트 0건.
    기존 테스트 무회귀: `node --test app/src/lib/__tests__/manualOffset.test.ts` 6 pass,
    `node --test app/src/lib/__tests__/cueTrack.test.ts` 7 pass (실측 기준선).
    ※ `node --test <디렉터리>` 는 이 트리에서 pre-existing 실패(MODULE_NOT_FOUND) —
    게이트로 쓰지 말 것. 파일 단위 호출이 이 레포 관례다.
  </done>
</task>

<task type="auto">
  <name>Task 2: tick 집행 블록 배선 + 관찰창 생명주기</name>
  <files>app/src/components/VideoCompare.tsx</files>
  <action>
    (1) **ref 2개 신설** — `voicePauseStartRef`(555) 바로 아래:
    `const resumeWatchTicksRef = useRef&lt;number | null&gt;(null);`(null = 관찰창 밖)
    `const resumeRetriesRef = useRef(0);`

    (2) **관찰창 개시** — tick 의 F-1 재개 블록(720-737) 안, `return` **직전**에
    `resumeWatchTicksRef.current = 0; resumeRetriesRef.current = 0;` 를 넣는다.
    `voicePauseRef.current = false` 전이와 같은 지점이어야 한다(overMax 강제 재개도 동일 경로라
    자동 포함). **F-1/F-2 기존 문장과 조기 return 은 한 줄도 건드리지 않는다.**

    (3) **집행 블록** — `const followTick = ...`(757) 다음 줄, follow/drift `if`(758) **앞**에
    삽입한다. 이 위치인 이유를 주석으로 남긴다: `startHold` 판정에 `followTick` 이 필요하고,
    집행 후 조기 return 이 stale `leftPlaying` 으로 도는 follow/drift 블록보다 앞서야
    F-2 와 같은 mid-tick 레이스를 다시 만들지 않는다.

    블록이 하는 일:
    - 관찰창 진행: `resumeWatchTicksRef.current` 가 null 이 아니면 +1, `RESUME_WATCH_TICKS`
      초과 시 null 로 닫는다.
    - `const startHoldActive = followTick &amp;&amp; targetRefTime(cL) &lt; 0;`
      (779행 `rawComposedRef` 와 **같은 식** — 시작 홀드 판정 규칙을 두 벌 만들지 않는다.)
    - `decidePlaybackInvariant({ hasLeft, hasRight, scrubbing: scrubbingRef.current,
      voicePaused: voicePauseRef.current, leftPlaying, rightPlaying: !!rightPlayer?.playing,
      resumeWatchTicks: resumeWatchTicksRef.current, resumeRetriesUsed: resumeRetriesRef.current,
      startHold: startHoldActive })` 호출.
      ※ `rightPlaying` 은 tick 시작 시점 캡처가 없으므로 이 자리에서 새로 읽는다.
      `leftPlaying` 은 668행 캡처값을 쓴다(같은 tick 안 F-2 규율 유지).
    - `decision.action === 'none'` 이면 아무 것도 하지 않고 통과(기존 흐름 그대로).
    - 아니면 `left`/`right` 커맨드를 그대로 적용(`'pause'` → `pause()`, `'play'` → `play()`,
      `'leave'` → 무동작), `consumeRetry` 면 `resumeRetriesRef.current += 1`,
      `closeWatch` 면 `resumeWatchTicksRef.current = null`,
      action 이 `enforce-pause`/`converge-pause` 면 `setPlaying(false)`,
      그리고 **`return`** 으로 tick 을 조기 종료한다(F-1/F-2 와 동일 규율 — 다음 tick 이
      신선한 상태로 판정).

    (4) **사용자 제스처가 관찰창을 닫는다** — `voicePauseRef.current = false;` 가 놓인
    제스처 4곳(906 togglePlay 정지 / 910 togglePlay 재생 / 1013 seekBoth / 1132
    markOffsetApplying) 각각에 `resumeWatchTicksRef.current = null;` 를 짝으로 붙인다.
    사용자가 개입한 뒤에는 감시가 사용자와 싸우면 안 된다(기존 "제스처 우선" 규율의 연장).
    724(tick 재개)에는 붙이지 않는다 — 거기는 창을 여는 자리다.

    (5) 신규 타이머/인터벌/폴링 **0**. 판정은 전부 기존 100ms tick 위에서만.
    주석은 왜-주석 + 출처 인용(`260806-usc — V-1 …`), 이모지 금지, 테마/카피 변경 0.
  </action>
  <verify>
    <automated>npm --prefix app run typecheck</automated>
    <automated>cd app &amp;&amp; test $(grep -n 'decidePlaybackInvariant({' src/components/VideoCompare.tsx | head -1 | cut -d: -f1) -lt $(grep -n 'const rawComposedRef = targetRefTime(cL)' src/components/VideoCompare.tsx | cut -d: -f1)</automated>
    <automated>cd app &amp;&amp; test $(grep -v '^\s*//' src/components/VideoCompare.tsx | grep -c 'setInterval(') -eq 1</automated>
    <automated>cd app &amp;&amp; test $(grep -v '^\s*//' src/components/VideoCompare.tsx | grep -c 'resumeWatchTicksRef.current = null') -ge 4</automated>
    <automated>cd app &amp;&amp; test $(grep -v '^\s*//' src/components/VideoCompare.tsx | grep -c 'resumeWatchTicksRef.current = 0') -eq 1</automated>
    <automated>node --test app/src/lib/__tests__/playbackInvariant.test.ts</automated>
    <human-check>
    **오케스트레이터 시뮬 회귀 확인** (실행자 아님 — 개발 빌드 + Metro 가동 중):
    엘보 doc 재생 → 큐1·큐2 발화 지점에서 (a) 양쪽이 함께 멈추는가 (b) 음성 종료 후 양쪽이
    함께 재개되는가 (c) 최종까지 두 시각이 동기 주행하는가 — 08-06 실측(4.1/4.2 → 6.7/6.7 →
    13.3/13.5)과 **같은 궤적**이면 회귀 0. 추가로 (d) 재생 버튼 정지/재개, (e) 타임라인 scrub,
    (f) 오프셋 슬라이더 조작 후 영상이 멈춰 버리지 않는가(관찰창 닫기 실효).
    ※ 시뮬은 원 결함(V-1)을 재현하지 못한다 — 여기서 증명되는 것은 **회귀 없음**뿐이다.
    </human-check>
  </verify>
  <done>
    typecheck GREEN. 게이트 5종 통과(집행 블록이 follow/drift 앞 · 타이머 1개 유지 ·
    제스처 4곳 창 닫기 · 창 개시 1곳). 오케스트레이터 시뮬 (a)~(f) 확인.
    F-1/F-2 조기 return·follow/drift 블록·시작 홀드 로직 diff 0(추가만, 기존 줄 수정 0).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (없음) | 신규 입력·네트워크·저장소 경계 0. 로컬 플레이어 상태만 읽고 play/pause 를 부른다. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-usc-01 | Denial of Service | tick 집행 블록 ↔ follow/drift 블록 | mitigate | 집행 후 조기 `return` + 관찰창 `RESUME_WATCH_TICKS` 상한 + 재시도 `RESUME_PLAY_RETRIES` 상한 → play/pause 무한 왕복(배터리·stutter) 구조적 차단. 게이트로 배치 순서 검사. |
| T-usc-02 | Denial of Service | converge-pause | accept | 재버퍼가 300ms 를 넘으면 양쪽이 멈춘다(사용자가 재생 버튼으로 재개, 정렬 보존). 편측 5초 이탈보다 낫다는 판단 — D-13 불변식 우선. |
| T-usc-03 | Tampering | 사용자 제스처 vs 자동 집행 | mitigate | `scrubbing` 최우선 가드(R2) + 제스처 4곳 관찰창 닫기 → 자동 로직이 사용자 조작을 덮어쓰지 않는다. |
| T-usc-SC | Tampering | npm/pip/cargo installs | mitigate | **신규 의존성 0** (설치 태스크 없음 — node:test/node:assert 표준 모듈만). |
</threat_model>

<verification>
1. `node --test app/src/lib/__tests__/playbackInvariant.test.ts` — 12축 pass
2. `npm --prefix app run typecheck` — GREEN(무출력, 실측 기준선과 동일)
3. 기존 테스트 무회귀 — manualOffset 6 pass / cueTrack 7 pass
4. 배치·타이머·생명주기 grep 게이트 5종
5. 오케스트레이터 시뮬 (a)~(f)
</verification>

<success_criteria>
- 음성 정지 중 편측 진행이 100ms(1 tick) 이상 지속될 수 없다 — 판정 함수로 증명.
- 재개 후 1초 관찰창 안에서 편측이면 play() 재시도 3회, 그래도 편측이면 양쪽 대칭 정지.
- 관찰창 밖·scrubbing 중·시작 홀드에는 개입 0 (기존 right 소유권 로직과 충돌 0).
- 신규 타이머 0, 신규 npm 의존성 0, 채점·계약·테마·카피 변경 0.
- 커밋 1개 (fix).
</success_criteria>

<honesty_gate>
SUMMARY 에 **반드시** 다음을 그대로 박제한다:

- **실기기 실효 = UNVERIFIED.** 시뮬(iOS 26.5, 개발빌드 #29)에서 원 결함 V-1 이 재현되지
  않으므로, 시뮬 확인으로 증명되는 것은 **회귀 없음**뿐이다. "V-1 이 고쳐졌다"고 쓰지 말 것.
  belle 실기기 확인 전까지 상태는 "불변식 감시를 넣었다 / 실효 미확인".
- **원인 미규명.** 이 수리는 원인(재버퍼 스톨 / mid-tick 레이스 / play() 무실효)을 가리지
  않는다. 결과 상태를 수렴시킬 뿐이다. 원인 후보를 확정된 것처럼 쓰지 말 것(F-6 원칙).
- **converge-pause 는 트레이드오프다.** 느린 네트워크에서 재개가 300ms 를 넘으면 양쪽이
  멈춘 채로 사용자 조작을 기다린다 — 의도된 동작이며, belle 이 "음성 끝나면 자꾸 멈춘다"고
  보고하면 `RESUME_PLAY_RETRIES` / `RESUME_WATCH_TICKS` 상향이 조정 지점임을 명시.
- belle 실기기 확인 항목(단서 포함): V-1 재현 doc(엘보)에서 ① 음성 종료 후 내 영상이 도는가
  ② 안 돌면 **양쪽이 같이 멈춰 있는가**(=집행 성공, 정렬 보존) ③ 재생 버튼으로 다시 도는가.
</honesty_gate>

<output>
Create `.planning/quick/260806-usc-v-1/260806-usc-SUMMARY.md` when done.
EAS OTA 는 이 계획 범위 밖 — 오케스트레이터가 시뮬 확인 후 수행한다.
</output>
