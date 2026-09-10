---
id: 260910-euz
title: 관절선 토글 재생위치 유실 수리
date: 2026-09-10
status: implemented-unverified-on-device
---

# 관절선 토글 시 재생 위치 유실 수리 — 실행 결과

**한 줄**: 합성 비교 플레이어의 소스 교체를 `교체 전 pause → ready 대기 →
seek → 되읽어 검증 → 재시도 → 그 다음에만 play` 순서로 바꾸고, 판정을 순수 모듈
`sourceSwapSeek.ts` 로 분리해 8축으로 테스트했다. **belle 실기기 판정 전이다.**

---

## 바뀐 파일과 커밋

| 커밋 | 종류 | 파일 | 증감 |
| --- | --- | --- | --- |
| `7891623f` | Task 1 | `app/src/lib/sourceSwapSeek.ts` (신설) | +175 |
| `7891623f` | Task 1 | `app/src/lib/__tests__/sourceSwapSeek.test.ts` (신설) | +236 |
| `1f692bb5` | Task 2 | `app/src/components/RenderedComparePlayer.tsx` | +254 / −13 |

두 커밋 모두 삭제된 추적 파일 0 (`git diff --diff-filter=D --name-only` 빈 출력).

### Task 1 — `sourceSwapSeek.ts` (순수 판정)

`playbackInvariant.ts` / `replaySettle.ts` / `driftHysteresis.ts` 관례 그대로:
react / react-native / expo / expo-video import 0, 순수 함수만.

내보낸 것: `SwapPhase`, `PlayerStatus`, `SwapDecisionInput`, `SwapDecision`,
`SWAP_VERIFY_TOLERANCE_S = 0.35`, `SWAP_SEEK_ATTEMPTS = 3`,
`SWAP_READY_TIMEOUT_MS = 6000`, `clampSeekTarget()`, `decideSwapSeek()`.

### Task 2 — `RenderedComparePlayer.tsx` (배선)

- 토글 effect 전면 교체. `at`/`wasPlaying` 을 교체 **전에** 읽고, **교체 전에
  `player.pause()`**, 세대(`swapEpochRef`)로 옛 콜백 무효화, 리스너를
  `replaceAsync` **전에** 등록, ready 신호 또는 6초 폴백 타이머 → `decideSwapSeek`
  → `currentTime` 대입 → `SWAP_VERIFY_DELAY_MS`(220ms) 뒤 되읽어 검증 → 재시도 또는
  종료, **종료 시에만 `play()`**.
- 교체 중 100ms 폴링 억제 (`if (swappingRef.current) return;`).
- 실패 시 `overlayOnRef.current` 를 **먼저** 되돌린 뒤 `setOverlayOn` — 되감기 루프
  없음, 칩·소스 영구 desync 제거.
- 칩 연타 차단: `disabled={swapping}` + `optionPillBusy { opacity: 0.6 }` +
  `accessibilityState.disabled`.
- **`playbackRate` 재적용 없음** (PLAN ★ 재적용 금지 준수). `muted`/`loop`/`volume`
  도 재적용하지 않는다.

---

## 실제로 돌린 검증

```
$ cd app && npm run typecheck
> tsc --noEmit
exit=0        → 에러 0건 (tsc 출력 0줄)

$ cd app && node --test $(find src -path '*__tests__*' -name '*.test.ts')
ℹ tests 234
ℹ pass 234
ℹ fail 0
ℹ skipped 0
ℹ todo 0
```

착수 전 기준선은 **226건 전건 통과**였다. 신규 8축이 더해져 **234건 / 통과 234 /
실패 0**. 줄어든 건 없다.

`player.addListener('sourceLoad'|'statusChange', cb)` 는 PLAN 예측대로 **캐스트 없이
통과**했다 (`PoseCompareFrames.tsx:50-56` 의 `useEvent` 캐스트는 흉내내지 않았다).

### 신규 8축 (각각이 실제 결함 하나를 막는다)

1. `status` 가 30 tick 동안 `'loading'` → 매번 `wait`, **seek 0회** (기기 결함 그 자체)
2. `'loading' → 'readyToPlay'` → `seek` 정확히 1회
3. 구독 시점에 이미 `'readyToPlay'` → 즉시 `seek` (지금 되는 맥 시뮬 경로 보존)
4. `'error'` → `abort` (seek·play 둘 다 없음)
5. 검증 성공(오차 ≤ 0.35s) → `finish{play: wasPlaying}`
6. 검증 실패 + `attempts < 3` → 재 `seek`, `attempts === 3` → `finish`
7. `targetSec` NaN/±Infinity/음수/duration 초과 → 클램프, **NaN 이 `seekSec` 으로
   새지 않음**
8. `phase === 'done'` → 무동작 (늦게 온 ready 신호로 되감기지 않음)

---

## 검증의 한계 (PLAN §검증의 한계 승계 — 그대로 유효하다)

이 테스트는 **"`readyToPlay` 에서 `player.currentTime = x` 가 iOS 실기기에서 실제로
먹는가"를 못 잡는다.** 그건 AVFoundation 런타임 사실이라 순수 테스트가 닿지 못한다.
같은 저장소에 이미 배포되어 도는 선례(`PoseCompareFrames.tsx:39-64` `useSeekPaused`
— 주석: *"expo-video 는 소스 로드 전 currentTime 설정이 무시될 수 있어
statusChange(readyToPlay)에 맞춰 적용한다"*)가 있을 뿐 증명은 아니다.

**테스트 통과만으로 "고쳤다"고 보고하지 않는다.** 최종 판정은 belle 실기기다.
이번 세션에서 실기기 확인도, 시뮬레이터 렌더 확인도 하지 않았다 — typecheck 는
렌더 크래시를 못 잡는다([[verify-ui-on-simulator-before-ota]]). OTA 발행 전에
시뮬레이터에서 이 카드가 그려지는지부터 봐야 한다.

추가로, 이 배선이 남긴 잔여 레이스 하나를 감추지 않고 적는다: 리스너를
`replaceAsync` **전에** 걸므로(Android 요구), 토글 직전에 옛 아이템이 마침 버퍼링
중이었다면 옛 아이템의 `statusChange('readyToPlay')` 가 몇 ms 창 안에 끼어들 수
있다. 그 경우에도 검증-재시도 루프(220ms × 최대 3회)가 새 아이템 위에서 다시
seek 하므로 최종 위치는 복구되지만, 구조적으로 0 인 것은 아니다.

---

## 범위 밖으로 남긴 별건 (기록만)

**`playbackRate` effect 의 정지 중 재생 시작 잠재 결함**
(`RenderedComparePlayer.tsx` 의 `useEffect(() => { player.playbackRate = slowMotion ? 0.5 : 1 }, ...)`).

iOS `playbackRate` 의 `didSet` 은 `ref.rate = playbackRate` 를 **값이 같아도 무조건**
쓴다 (`node_modules/expo-video/ios/VideoPlayer.swift:26-36` — `if oldValue !=
playbackRate` 안에 있는 것은 이벤트 emit 뿐이고 `ref.rate` 대입은 그 밖이다,
실독 확인). 따라서 **정지 상태에서 '0.5배속' 칩을 누르면 재생이 시작될 수 있다.**
이번 범위 밖이라 손대지 않았다. belle 이 아직 이 증상을 보고한 적은 없다 — 별건
관측으로만 남긴다.

그 밖에 PLAN 이 명시한 범위 밖 항목은 전부 무접촉:
- 듀얼 경로 `VideoCompare.tsx` — 변경 0
- 서버/렌더 경로 `compare_render.py`, 계약 `docs/contract.md` — 변경 0
- `ROADMAP.md` — 변경 0

---

## 계획 대비 이탈

**1. [Rule 2 - 누락된 정확성 요건] `player.status` 직독 금지**

- **발견 시점**: Task 2 배선 중
- **문제**: PLAN 은 "ready 신호 → `decideSwapSeek` 판정"까지만 정하고 `status` 를
  어디서 읽는지는 말하지 않았다. 그런데 iOS 의 `status` 는 didSet 이 **값이 바뀔
  때만** emit 하는 속성이라, 옛 아이템이 `readyToPlay` 였으면 교체 직후에도
  `player.status` 는 여전히 `'readyToPlay'` 를 준다. 핸들러에서 이 값을 직독하면
  익지 않은 새 아이템을 익은 것으로 오독해 **수리가 원래 결함을 그대로 재현한다.**
- **수리**: 지역 변수 `signalStatus` 를 두고 **이벤트가 말한 것만** 믿는다.
  `statusChange` 는 payload 의 `status`, `sourceLoad` 는 `readyToPlay`(단
  `player.status === 'error'` 면 `error` — iOS 는 `.error` 를 sourceLoad 발화보다
  먼저 status 에 반영한다, `ios/VideoPlayerObserver.swift:412-421`).
- **커밋**: `1f692bb5`

**2. [Rule 2] `replaceAsync` 거절 시 재생 복구**

- PLAN (c) 는 실패 시 "칩 되돌림"만 정했다. 그런데 우리가 교체 **전에** pause 했기
  때문에, `replaceAsync` 프로미스가 거절되면(=소스는 옛것 그대로) 칩만 되돌리고 끝내면
  **사용자 조작 없이 영상이 멈춘 채로 남는다.** 그래서 `.catch` 경로에서만
  `wasPlaying` 이면 `play()` 로 되돌린다. 위치는 건드린 적이 없으므로 그대로다.
  판정 함수의 `abort`(status === 'error')는 PLAN 규칙대로 **seek 도 play 도 하지
  않는다** — 로드 실패를 0초 재생으로 강등하지 않기 위해서다.
- **커밋**: `1f692bb5`

**3. [테스트 기대값 정정] `clampSeekTarget(+Infinity, 30)`**

- 처음에 `29.95` 를 기대하도록 썼다가 실패했다. 구현은 `Number.isFinite` 게이트라
  ±Infinity 를 `0` 으로 접는다. **구현이 옳다** — 비유한 값은 "끝으로 보내라"가
  아니라 "값을 못 읽었다"이고, `player.currentTime` 은 해제 직후 비유한 값을 줄 수
  있다. 그때 영상 끝으로 뛰는 것보다 처음에 서는 편이 덜 놀랍다. 테스트 기대값을
  고치고 이유를 주석으로 박았다.
- **커밋**: `7891623f` (커밋 전에 정정)

## 인용 검증

주석에 넣은 네이티브 파일:줄은 전부 `node_modules` 에서 실독해 확인했다 —
`ios/VideoModule.swift:330-333`, `ios/VideoPlayer.swift:26-36 · :55 · :236-268`,
`ios/VideoPlayer/DangerousPropertiesStore.swift:1-14`,
`ios/VideoPlayerItem.swift:27`, `ios/VideoPlayerObserver.swift:412-421`,
`ios/VideoPlayer.swift:387`,
`android/src/main/java/expo/modules/video/VideoModule.kt:356-374`.

## Self-Check: PASSED

- `app/src/lib/sourceSwapSeek.ts` — FOUND
- `app/src/lib/__tests__/sourceSwapSeek.test.ts` — FOUND
- `app/src/components/RenderedComparePlayer.tsx` — FOUND
- 커밋 `7891623f` — FOUND
- 커밋 `1f692bb5` — FOUND
- 작업 트리에 미커밋 변경 없음 (이 SUMMARY 및 기존 미추적 파일 제외)
