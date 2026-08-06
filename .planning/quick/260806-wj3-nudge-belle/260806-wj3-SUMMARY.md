---
phase: quick-260806-wj3
plan: 01
subsystem: ui
tags: [expo-audio, expo-video, react-native, playback-invariant, audio-cue, IN-01]

requires:
  - phase: quick-260806-usc
    provides: playbackInvariant 판정 순수 함수(R7 재시도 → R8 converge-pause) + 관찰창
  - phase: quick-260801-f77
    provides: 발화 세대(seq) 무효화 + 로드 실패 감시(watchdog) + 만료 인지 URL 캐시
  - phase: quick-260724-q6b
    provides: IN-01 저신뢰(attributionReliability.unreliable) 표현 강등 게이트
provides:
  - 큐마다 플레이어 재생성 — 자막과 다른 큐의 음성이 재생될 경로를 구조적으로 제거 (fail-closed)
  - 저신뢰 doc 진행 바 감점 틱 복원 (IN-01 강등 범위에서 틱만 이탈)
  - 재개 마지막 재시도 직전 제자리 seek nudge (converge-pause 폴백 보존)
affects: [belle 실기기 확인, EAS OTA 발행, IN-01 재논의, F-6 음성 무음 조사]

tech-stack:
  added: []
  patterns:
    - "재생 아이템 생명주기 단일 소유자 — createAudioPlayer 호출 지점 1곳(activatePlayer)으로 고정하고 구조 게이트로 박제"
    - "fail-closed 오디오 — 로드 실패의 결과는 무음(자막만)이며 이전 아이템으로 대체되지 않는다"
    - "판정/집행 분리 유지 — 회복력 개선은 집행측(VideoCompare)에만, 판정 순수 함수는 diff 0"

key-files:
  created: []
  modified:
    - app/src/lib/audioCue.ts
    - app/src/app/analysis/result.tsx
    - app/src/components/VideoCompare.tsx

key-decisions:
  - "플레이어 재사용(replace) 전제 철회 — 리소스 절약보다 아이템 정합 우선. '남의 음성'은 replace 단일 벡터로만 들어왔고 그 벡터를 없앴다"
  - "didJustFinish 에서는 release 하지 않는다 — 네이티브 콜백 재진입 회피, 다음 발화/stopCue 가 어차피 회수"
  - "failSpeech 는 pausePlayerSafely 유지 — release 하면 뒤늦은 재발급 콜백이 죽은 참조를 만진다"
  - "IN-01 강등에서 진행 바 틱만 이탈 — 틱은 관절 단정이 아니라 시점 안내. 영상 위 마커/번호/그룹/범례 억제는 유지(의도된 비대칭)"
  - "nudge 는 제자리(같은 시각) seek — 정렬은 converge-pause 가 지키려는 자산이라 시각을 옮기지 않는다"
  - "playbackInvariant.ts 무접촉 — 12축 테스트 동반 갱신 회피 + 불변식 보존"

patterns-established:
  - "구조 게이트로 계약 박제: 호출 지점 개수(replace 0 / createAudioPlayer 1 / player=null 1 / remove 1)를 검증 대상으로 삼아 '경로가 없음'을 증명"
  - "표시 강등 범위를 카운트로 고정: 잔존 강등 6건 카운트 게이트가 과잉 일반화를 차단"

requirements-completed: [belle-①, belle-②, belle-④, D-13, IN-01]

duration: 9min
completed: 2026-08-06
---

# quick-260806-wj3: belle 실기기 관측 3건 수리 Summary

**큐마다 플레이어를 새로 만들어 "자막은 큐2인데 음성은 큐1" 경로를 구조적으로 제거하고(fail-closed 무음), 저신뢰 doc 진행 바 감점 틱을 복원하고, 재개 마지막 재시도 직전 제자리 seek 를 1회 넣었다 — 판정 순수 함수·채점·계약 무접촉.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-06T14:38:00Z (2026-08-06 23:38 KST)
- **Completed:** 2026-08-06T14:47:06Z (2026-08-06 23:47 KST)
- **Tasks:** 3 / 3
- **Files modified:** 3 (+146 / −23)

## Accomplishments

- **belle ①** — `replace()` 를 코드에서 소멸시키고 모든 재생 아이템의 출생지를 `activatePlayer` 안의 `createAudioPlayer(url)` 단 하나로 고정. 로드 실패의 결과가 구조적으로 무음(자막만)이 된다.
- **belle ②** — IN-01 저신뢰 강등이 삼키던 진행 바 감점 틱을 복원(7→6, 이탈은 틱 1건뿐). 영상 위 단정 표면 억제는 그대로.
- **belle ④** — converge-pause 최종 폴백을 유지한 채, 마지막 재시도 직전에만 제자리 seek 1회. 판정 계약 `playbackInvariant.ts` diff 0.

## Task Commits

1. **Task 1: 큐마다 플레이어 재생성 — 스테일 아이템 재재생 차단** — `77edf246` (fix)
2. **Task 2: 저신뢰 doc 에서도 진행 바 감점 틱 표시** — `87932d16` (fix)
3. **Task 3: 재개 마지막 재시도 직전 제자리 seek nudge** — `7b7c8d07` (fix)

**Plan metadata:** 커밋 없음 — 이 작업의 docs 아티팩트는 커밋 금지(오케스트레이터 지시). ROADMAP 무접촉.

브랜치: `worktree-agent-a0931c62475d24a16` (base `25f7727e`)

## Files Created/Modified

- `app/src/lib/audioCue.ts` (+93 / −19) — `releasePlayer()` / `activatePlayer()` 신설, `speakCue`·`onLoadTimeout` 재발급 경로를 `activatePlayer` 단일 경유로 교체, `stopCue` 를 `releasePlayer` 로. 모듈 헤더의 "플레이어 재사용" 전제 철회 명시.
- `app/src/app/analysis/result.tsx` (+20 / −4) — `overlayTimelineTicks` 한 줄 수리(코드 변경은 이 1줄이 전부) + IN-01 주석 정합.
- `app/src/components/VideoCompare.tsx` (+33 / −0) — `RESUME_PLAY_RETRIES` import + 집행 블록 커맨드 적용 직전 nudge. 순수 additive(삭제 0).

## 게이트 결과 (전부 직접 실행)

| 게이트 | 기준 | 실측 | 결과 |
|---|---|---|---|
| `npm --prefix app run typecheck` | GREEN(무출력) | 무출력, exit 0 (task 1·2·3 각각 + 최종) | PASS |
| `node --test` 3파일 | 25 pass / 0 fail | tests 25 / pass 25 / fail 0 | PASS |
| audioCue `player?.replace(` | 2 → **0** | 0 | PASS |
| audioCue `createAudioPlayer(` | 1 → **1** | 1 (activatePlayer 안 단 하나) | PASS |
| audioCue `player = null` | 0 → **1** | 1 (releasePlayer 안 단 하나) | PASS |
| audioCue `.remove()` | 0 → **1** | 1 | PASS |
| result.tsx `overlayX = attributionUnreliable` | 7 → **6** | 6 | PASS |
| result.tsx `overlayTimelineTicks = timelineTicks` | 1 | 1 | PASS |
| result.tsx 범례 억제 `? [] : fullscreenLegend` | 1 | 1 | PASS |
| `deductionLabels.ts` + `VideoCompare.tsx` diff (Task 2 시점) | 0 | 빈 출력 | PASS |
| `playbackInvariant.ts` diff | 0 | 빈 출력 | PASS |
| VideoCompare `RESUME_PLAY_RETRIES - 1` | 0 → **1** | 1 | PASS |
| VideoCompare `RESUME_PLAY_RETRIES` 총계 | ≥ 2 | 2 (import + 사용) | PASS |
| VideoCompare `setInterval(` | 1 불변 | 1 (신규 타이머 0) | PASS |
| 커밋별 파일 삭제 | 0 | 3커밋 전부 빈 출력 | PASS |

기준선(착수 시점)도 직접 재실행해 계획의 `<interface_contract>` 실측표와 전건 일치함을 확인한 뒤 착수했다.

## belle ① 코드 판독 논증 (자동 테스트 대신)

**자동 테스트를 쓰지 않은 이유** (계획 `<done>` 사유를 그대로 옮김): `audioCue.ts` 는
expo-audio/AsyncStorage 를 직접 import 하는 어댑터라 `node --test` 로 로드 불가이고,
이 수리의 본질은 **호출 순서·생명주기**여서 순수 함수로 떼어내면 실제 결함이 아닌
껍데기를 검증하게 된다(수치 채우기 금지).

대신 수리 후 파일에서 호출 지점을 전수 조회해 다음을 확인했다:

- `createAudioPlayer(` = **1곳** (`audioCue.ts:194`, `activatePlayer(url)` 내부, 인자는 그 함수의 `url` 파라미터).
- `.play()` = **2곳** (`:256`, `:507`). 둘 다 바로 앞 문장에서 `const p = activatePlayer(<이 큐의 url>)` 로 묶인 지역 변수 `p` 에 대한 호출이고, 그 사이에 재대입이 없다.
  - `:507` (`speakCue`) — `url` = 이 큐 `id` 의 캐시 엔트리 URL.
  - `:256` (`onLoadTimeout` 재발급) — `entry.url` = 이 큐 `recordId` 의 재발급 URL.
- `.replace(` = **0곳** — 기존 플레이어의 소스를 갈아끼울 수단이 없다.
- 그 외 `player` 참조는 전부 읽기(`playing`/`isLoaded`)·리스너 부착·`null` 대입뿐 (전수 조회로 확인).

따라서 **`play()` 가 닿을 수 있는 아이템은 그 큐의 URL 로 만들어진 것뿐**이고,
생성이 실패하면 아이템이 없으므로 결과는 무음이다.

## Decisions Made

계획에 명시된 결정을 그대로 따랐다(위 frontmatter `key-decisions` 참조). 실행 중 새로 내린 판단은 없다.

## Deviations from Plan

**None — plan executed exactly as written.**

Rule 1~3 자동 수정 0건, Rule 4 아키텍처 판단 0건. 신규 의존성 0(`T-wj3-SC` 유지),
신규 타이머 0, 채점·계약·테마·카피 변경 0.

## Issues Encountered

- 워크트리에 `app/node_modules` 가 없어 typecheck 불가 → 선례대로 본 repo `node_modules` 를 심볼릭 링크한 뒤 작업 종료 시 제거했다. 제거 확인 및 본 repo `node_modules` 무손상 확인 완료. 워크트리 `git status` clean.
- 워크트리 HEAD 가 지정 base(`25f7727e`)보다 뒤(`ba48e3c0`)여서 setup 절차대로 `git reset --hard 25f7727e` 로 맞췄다(사전 `git status` clean 확인 후 실행).

## 정직 박제 (honesty_gate — 문장 완화 금지)

- **① 실기기 실효 = UNVERIFIED, 시뮬로 재현 불가.** 이 결함의 전제가 **기기 네트워크에서의 로드 실패**라 시뮬(정상 네트워크)에서는 애초에 발생하지 않는다. 시뮬로 증명되는 것은 회귀 없음뿐이다. "①을 고쳤다"가 아니라 **"① 이 발생할 수 있는 경로를 없앴다(구조 게이트로 증명) / 실기기 실효 미확인"** 이 정확한 표현이다.
- **① 의 기제는 코드 판독 논증이지 계측이 아니다.** replace 실패 시 이전 아이템이 남는다는 것을 실기기에서 계측한 것이 아니다 — expo-audio API 형태와 belle 관측("큐1이 처음부터 다시")의 정합으로 세운 **가설**이다. 확정된 사실처럼 쓰지 말 것.
- **② 가 belle 화면에서 안 보이면 원인이 둘이다.** 이 게이트(코드) 아니면 **데이터**(`visionVeto.status !== 'applied'` / `windowMedianAngleDeltas.sourceFrameIndices.user` 빔). **이번 실행에서는 어느 쪽인지 확인하지 못했다 — 실행자에게 시뮬 도구가 없다.** 오케스트레이터 시뮬 확인 (a)(b)(c) = **미실시/미확인**. 추측으로 코드를 더 고치지 않았다.
- **② 는 비대칭을 남긴다.** 진행 바에는 번호 틱이 뜨는데 영상 위에는 번호가 없다 — IN-01 승인 설계를 지키기 위한 **의도된** 비대칭이다. belle 이 "영상 위에도 번호를"이라고 하면 그건 IN-01 재논의 건이지 이번 수리의 결함이 아니다.
- **④ nudge 는 효과 미검증 지렛대다.** 제자리 seek 가 실제로 스톨을 푸는지 확인한 바 없다. belle 이 여전히 "음성 끝나고 둘 다 멈춘다"고 하면 다음 후보는 (a) epsilon seek(수십 ms 전진), (b) `RESUME_PLAY_RETRIES` / `RESUME_WATCH_TICKS` 상향이다.
- **③(큐1 후 정상 재개)은 무접촉**이며, 오늘 넣은 불변식이 작동한 증거다.
- **Task 3 시뮬 회귀 확인 (a)(b)(c) 도 미실시** — 실행자에게 시뮬 도구가 없다. nudge 가 정상 재생을 끊지 않는지는 **아직 화면으로 확인되지 않았다**(typecheck·순수 함수 테스트는 렌더/재생 거동을 잡지 못한다).
- **F-6(음성 무음)·V-2(시작 음성)는 이번에 손대지 않았다** — 범위 밖(고의).

## belle 실기기 확인 항목

1. **①** 큐2 에서 자막과 음성이 **같은 부위**를 말하는가 — 아니면 **무음**인가. (무음은 이번 설계상 **정상 실패**다. "다른 부위 음성"이 나오면 이번 수리의 전제가 틀린 것이므로 그대로 알려줄 것.)
2. **②** 진행 바에 감점 표시(틱)가 **보이는가**. 보이면 탭 → 그 시점으로 이동 + 해당 감점 시트가 열리는가.
3. **④** 음성 종료 후 재개가 **되는가**. 안 되면 여전히 **양쪽이 같이** 멈춰 있는가(편측이면 다른 결함).

## User Setup Required

None — 외부 서비스 설정 변경 없음.

## Next Phase Readiness

- **오케스트레이터 잔여 게이트 2건 (필수, 미실시):**
  - 시뮬 Task 2 (a) 저신뢰 doc 진행 바 틱 렌더 / (b) 틱 탭 → seek + 시트 / (c) 영상 위 번호·그룹·범례 여전히 없음. **(a) 실패 시 코드 아니라 데이터일 수 있음 — 위 정직 박제 참조, 추측 수리 금지.**
  - 시뮬 Task 3 (a) 큐 시점 양쪽 동시 정지 / (b) 음성 종료 후 양쪽 동시 재개 / (c) 260806-usc 실측 궤적(4.1/4.2 → 6.7/6.7 → 13.3/13.5) 모양 유지 = **회귀 없음**만 증명.
- 위 2건 통과 후 EAS OTA 발행(이 계획 범위 밖) → belle 실기기 확인 3항목.
- 워크트리 `worktree-agent-a0931c62475d24a16` 커밋 3개, 병합 대기.

## Self-Check: PASSED

- 수정 파일 3개 존재 확인 (`ls -l`): `audioCue.ts` / `result.tsx` / `VideoCompare.tsx`
- 커밋 3개 존재 확인 (`git log --oneline -3`): `7b7c8d07` / `87932d16` / `77edf246`
- 워크트리 `git status` clean, `node_modules` 심볼릭 링크 제거 완료, 본 repo `node_modules` 무손상
- SUMMARY 2부(워크트리 + 본 repo 절대경로) `diff` 결과 IDENTICAL

---
*Phase: quick-260806-wj3-nudge-belle*
*Completed: 2026-08-06*
