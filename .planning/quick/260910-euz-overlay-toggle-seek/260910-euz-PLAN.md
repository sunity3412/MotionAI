---
id: 260910-euz
title: 관절선 토글 재생위치 유실 수리
date: 2026-09-10
status: planned
---

# 관절선 토글 시 재생 위치 유실 수리

**belle 2026-09-10 실기기 반려(TestFlight, LTE)**: 동작비교 합성 플레이어에서 '관절선'
칩을 누르면 영상이 **처음부터** 재생된다. 같은 조작이 **가끔은 정상**이다(belle:
"뭘 조정했는지 처음부터 안돌아가기도 하는거 같고"). 시뮬레이터에서는 2026-09-09 에
정상으로 관측됐다 — **기기에서만, 그리고 간헐적으로** 난다.

## 확정된 원인 (expo-video 3.0.16 네이티브 소스 실독)

두 축이 겹친다. 둘 다 코드 사실이다.

**축 1 — ready 아닌 아이템에 exact seek 을 쏜다.**
`replaceAsync`(`app/node_modules/expo-video/ios/VideoModule.swift:330-333`)가 호출하는
async `replaceCurrentItem`(`ios/VideoPlayer.swift:236-268`)은 `DispatchQueue.main.async`
블록을 **예약만 하고 반환**한다. 그리고 `DangerousPropertiesStore`
(`ios/VideoPlayer/DangerousPropertiesStore.swift:1-2, 7-14`)는 주석 그대로 *"아이템이
아직 안 꽂혔다"* 만 막지 *"아직 안 익었다"* 는 안 막는다 — `applyProperties` 가
`ref.replaceCurrentItem` 과 **같은 main 큐 블록 안에서 바로 다음 줄**(`:264-266`)에
실행되기 때문이다.

즉 저장 경로(`ownerIsReplacing == true`)로 가든 직행 경로(`false`)로 가든, 결국
**status `.unknown` 인 새 AVPlayerItem** 에 `ref.seek(to:, toleranceBefore: .zero,
toleranceAfter: .zero)`(`ios/VideoPlayer.swift:55`)가 날아간다. 새 아이템은 아무것도
프리로드하지 않는다(`ios/VideoPlayerItem.swift:27` `automaticallyLoadedAssetKeys: nil`).
소스가 **원격 S3 presigned mp4** 이므로 moov + t≈at 부근 샘플이 도착하기까지의 창이
맥에서는 ~0, LTE 폰에서는 초 단위다. **sim/device 차이가 기계적으로 나오는 축.**

**축 2 — 교체 전에 멈추지 않아 재생 의사가 살아남는다.**
`replaceCurrentItem` 어디에도 pause 가 없다. `rate` 는 AVPlayer 레벨
(`ios/VideoPlayer.swift:32-35`)이라 아이템 교체를 넘어 유지된다. **재생 중에
토글하면 새 아이템이 ready 되는 즉시 0초부터 돈다.** 현재 코드의
`if (wasPlaying) player.play()`(`RenderedComparePlayer.tsx:220`)는 rate 가 0 이 된
적이 없어 사실상 무의미하다. → belle 의 "재생 중이면 처음부터 / 가끔 괜찮다" 와 일치.

**부수 확정 — 폴링이 성공한 seek 도 0:00 으로 보이게 만든다.**
100ms 폴링(`RenderedComparePlayer.tsx:239-253`)에 토글 억제 창이 없어, 교체 순간의
`currentTime = 0` / `playing = false` 가 그대로 UI 에 쓰인다. 시간 텍스트·트랙 fill·
`activeRid` 파생 감점 행이 한 tick 깜빡인다. 듀얼 경로(`VideoCompare`)의
`replaySettleTicksRef` 방어가 이 파일에 미이식.

**기각한 가설**: "레이스에서 지면 store 를 건너뛴다"(판별력 0 — 두 분기가 몇 ms
차이로 같은 곳에 도달), useVideoPlayer 재생성/VideoView 재마운트/StrictMode 이중
실행/듀얼 경로 오인(전부 코드로 배제).

## 채택한 수리 — 교체 전 pause → ready 대기 → seek → 검증 → 재시도 → 그 다음 play

버린 대안:
- **statusChange ready 대기만** — pause 가 없으면 축 2 가 그대로 산다. 게다가 iOS 는
  `statusChange('readyToPlay')` 를 직접 emit 하는 자리가 없고
  `isPlaybackLikelyToKeepUp`/`timeControlStatus` KVO 부수효과로만 나온다
  (`ios/VideoPlayerObserver.swift:449-450, 475-481`, 둘 다 `.initial` 없음).
  **pause 상태로 대기하면 `timeControlStatus` 가 안 변한다** → 단독으로 못 쓴다.
- **기존 폴링으로 재시도** — 폴링은 이 증상의 증폭기이지 계기가 아니다. "0 이니까 다시
  seek" 은 사용자가 진짜 0 으로 스크럽한 경우와 구분이 안 된다.
- **플레이어 2개 상시 유지** — 오디오가 코칭 음성 그 자체라 이중 음성/음소거 관리가
  생기고, 이 파일의 존재 이유인 *"오버레이·동기·재개 로직 0"*(파일 헤더 `:4-6`)를 되살린다.
- **SVG 오버레이로 온오프** — 재료가 없다. 이 가지는 합성 mp4 출력 시계만 가지고 있고
  관절 좌표를 출력 시간축으로 매핑할 수단이 없다(파일 헤더 한계 2).

계기는 **`sourceLoad` 가 정본**, `statusChange` 가 보조다. `sourceLoad` 는 새 아이템이
`.readyToPlay`(또는 `.error`)에 닿았을 때만 발화한다.

---

## Task 1 — 판정 로직을 순수 모듈로 분리 + 테스트

**files**: `app/src/lib/sourceSwapSeek.ts` (신설),
`app/src/lib/__tests__/sourceSwapSeek.test.ts` (신설)

**action**:
`app/src/lib/playbackInvariant.ts` / `replaySettle.ts` / `driftHysteresis.ts` 선례를
그대로 따른다 — **react / react-native / expo / expo-video import 0**, 순수 함수만.
파일 헤더 주석에 실행 명령과 검증 축을 적는다(선례 형식).

내보낼 것:

```ts
export type SwapPhase = 'idle' | 'awaitingReady' | 'seeking' | 'done';
export type PlayerStatus = 'idle' | 'loading' | 'readyToPlay' | 'error';

export type SwapDecisionInput = {
  phase: SwapPhase;
  status: PlayerStatus;
  /** 교체 전에 읽어 둔 목표 시각(초). */
  targetSec: number;
  /** 새 소스의 duration. 모르면 0. */
  durationSec: number;
  /** 교체 전에 재생 중이었나. */
  wasPlaying: boolean;
  /** seek 뒤 되읽은 현재 시각. 아직 안 읽었으면 null. */
  observedSec: number | null;
  /** 지금까지의 seek 시도 횟수. */
  attempts: number;
  /** ready 신호를 기다린 시간(ms). */
  waitedMs: number;
};

export type SwapDecision =
  | { action: 'wait' }
  | { action: 'seek'; seekSec: number }
  | { action: 'finish'; play: boolean }
  | { action: 'abort' };

export const SWAP_VERIFY_TOLERANCE_S = 0.35;
export const SWAP_SEEK_ATTEMPTS = 3;
export const SWAP_READY_TIMEOUT_MS = 6000;

export function clampSeekTarget(targetSec: number, durationSec: number): number;
export function decideSwapSeek(input: SwapDecisionInput): SwapDecision;
```

규칙:
- `status === 'error'` → `{action:'abort'}` (seek 도 play 도 하지 않는다. 조용한 0초
  재생으로 강등 금지).
- `phase === 'awaitingReady'`:
  - `status === 'readyToPlay'` → `{action:'seek', seekSec: clampSeekTarget(...)}`
  - `waitedMs >= SWAP_READY_TIMEOUT_MS` → `{action:'seek', ...}` (마지막 1회 시도)
  - 그 외 → `{action:'wait'}`
- `phase === 'seeking'`:
  - `observedSec === null` → `{action:'wait'}`
  - `|observedSec - clampSeekTarget(...)| <= SWAP_VERIFY_TOLERANCE_S` →
    `{action:'finish', play: wasPlaying}`
  - `attempts < SWAP_SEEK_ATTEMPTS` → `{action:'seek', ...}`
  - 그 외 → `{action:'finish', play: wasPlaying}` (포기해도 정지로 두지 않는다 —
    재생 중에 토글했는데 멈춰 있는 것도 고장이다)
- `phase === 'done'` → `{action:'wait'}` (재발화 금지)
- `clampSeekTarget`: 음수/NaN → 0. `durationSec > 0` 이면 `min(target, duration - 0.05)`.
  `durationSec <= 0` 이면 클램프하지 않는다(아직 모름).

**테스트 축 (8개, 각각이 실제 결함 하나를 막는다)**:
1. `status` 가 N tick 동안 `'loading'` → 매번 `wait`, seek 0회. ← **기기 결함 그 자체.**
2. `'loading' → 'readyToPlay'` → `seek` 정확히 1회.
3. **구독 시점에 이미 `'readyToPlay'`** → 즉시 `seek`. ← 이 축이 없으면 수리가
   *전이*만 듣게 짜여 시뮬(=지금 되는 경로)을 깬다.
4. `'error'` → `abort` (seek·play 둘 다 없음).
5. 검증 성공(오차 ≤ 0.35s) → `finish{play:wasPlaying}`.
6. 검증 실패 + `attempts < 3` → 재 `seek`. `attempts === 3` → `finish`.
7. `targetSec` 이 NaN/음수/duration 초과 → 클램프. **NaN 이 seekSec 으로 새지 않음**.
8. `phase === 'done'` 에서는 아무 행동도 안 함(재-ready 되감기 방지).

**verify**:
```bash
cd app && node --test $(find src -path '*__tests__*' -name '*.test.ts')
```
기존 226건 전부 통과 + 신규 축 전부 통과.
**함정**: `node --test src/lib` 처럼 디렉터리를 넘기면 실패한다. 파일 목록/글롭만.
대상 모듈은 `.ts` 확장자 명시 import (`from '../sourceSwapSeek.ts'`) —
`allowImportingTsExtensions=true` 라 `tsc --noEmit` 도 통과한다.

**done**: 위 명령이 통과하고 `npm run typecheck` 에러 0.

---

## Task 2 — RenderedComparePlayer 토글 경로 교체 + 폴링 억제

**files**: `app/src/components/RenderedComparePlayer.tsx`

**action**:

(a) **토글 effect 전면 교체** (현재 `:196-225`). Task 1 의 `decideSwapSeek` 를 써서
배선한다. 순서:

1. `at`, `wasPlaying` 을 **교체 전에** 읽는다 (교체 후 값은 옛 아이템 값이거나 0).
2. **`player.pause()` — 교체 전에.** 축 2 를 닫고, 로드 대기 동안 옛 아이템이 계속
   진행해 `at` 이 낡는 것도 같이 막는다.
3. 세대(epoch) ref 를 증가시켜 **연타/재실행 시 옛 콜백을 전부 무효화**한다.
4. **리스너를 `replaceAsync` 호출 *전에* 건다** — Android 는 `statusChange('loading')`
   이 프로미스 해소보다 먼저 나간다(`android/.../VideoModule.kt:356-374`).
   `sourceLoad` 정본 + `statusChange` 보조, **먼저 오는 쪽이 이긴다**.
   `sourceLoad` 는 `.error` 로도 오므로 `statusChange('error')` 를 반드시 같이 구독.
5. `player.replaceAsync(next)` 호출. `.catch` → 칩 되돌림(아래 (c)).
6. ready 신호(또는 `SWAP_READY_TIMEOUT_MS` 폴백 타이머) → `decideSwapSeek` 판정 →
   `player.currentTime = seekSec`.
7. `SWAP_VERIFY_DELAY_MS`(220ms) 뒤 `player.currentTime` 을 **되읽어 검증** →
   판정에 따라 재시도 또는 종료.
8. 종료 시에만 `if (play) player.play()`.
9. cleanup 에서 리스너·타이머 전부 해제.

(b) **교체 중 폴링 억제** (현재 `:239-253` 콜백 첫 줄):
```ts
if (swappingRef.current) return;
```
성공해도 0:00.0 이 한 tick 스치는 것을 belle 은 "처음으로 돌아갔다"로 읽는다.
(`VideoCompare` 의 `replaySettleTicksRef` 와 같은 취지.)

(c) **실패 시 칩 되돌림**: 교체/로드가 실패하면 `overlayOnRef.current` 를 먼저
되돌린 뒤 `setOverlayOn` 한다 — ref 를 먼저 되돌려야 재실행된 effect 가 맨 위
가드에서 즉시 return 해 **되감기 루프가 생기지 않는다**. 지금 코드는 비동기 작업
**전에** ref 를 갱신하고 catch 가 아무것도 안 되돌려, 실패하면 칩과 실제 소스가
**영구 desync** 된다.

(d) **칩 연타 차단** (현재 `:575-593`): `swapping` state 로 `disabled` + `opacity 0.6`
+ `accessibilityState.disabled`. 잠금이 눈에 보여야 belle 이 "안 눌린다"로 안 읽는다.

**★ 재적용 금지 — `playbackRate` 를 교체 후에 다시 대입하지 말 것.**
iOS `didSet` 이 **값이 같아도 무조건** `ref.rate = playbackRate` 를 쓴다
(`ios/VideoPlayer.swift:26-36`). 재적용하면 정지 상태에서 재생이 시작된다.
`rate`/`muted`/`loop`/`volume` 전부 AVPlayer 레벨이라 아이템 교체를 넘어 유지되므로
**아무것도 재적용하지 않는다**.

기존 주석의 취지(위치·재생 상태를 그대로 이어받는다)는 유지하되, **왜 그냥
`await` 뒤 대입으로는 안 되는지**를 네이티브 파일:줄 인용과 함께 적는다. 이 파일의
기존 주석 밀도·한글 서술체를 따른다. 이모지 금지.

**verify**:
```bash
cd app && npm run typecheck
cd app && node --test $(find src -path '*__tests__*' -name '*.test.ts')
```
`player.addListener('sourceLoad'|'statusChange', cb)` 는 캐스트 없이 통과한다
(`VideoPlayer extends SharedObject<VideoPlayerEvents>`,
`build/VideoPlayer.types.d.ts:7`). `PoseCompareFrames.tsx:50-56` 의 캐스트는
`useEvent` 시그니처 문제이지 `addListener` 문제가 아니므로 **흉내내지 말 것**.

**done**: typecheck 0, 테스트 전건 통과, 토글 경로에 pause→ready대기→seek→검증→play
순서가 코드로 존재하고 폴링 억제가 걸려 있다.

---

## 범위 밖 (건드리지 말 것)

- 듀얼 경로(`VideoCompare.tsx`) — 거기 '관절선' 칩은 순수 SVG 렌더 prop 이라 이 결함이
  구조적으로 없다.
- `:192-194` 의 `playbackRate` effect — 정지 상태에서 '0.5배속' 칩을 누르면 재생이
  시작되는 **별건 잠재 결함**이 있다(위 `didSet` 이유). 이번 범위 밖. SUMMARY 에 기록만.
- 서버/렌더 경로(`compare_render.py`), 계약(`contract.md`) — 변경 없음.

## 검증의 한계 (정직하게 적는다)

이 테스트는 **"`readyToPlay` 에서 `player.currentTime = x` 가 iOS 실기기에서 실제로
먹는가"를 못 잡는다.** 그건 AVFoundation 런타임 사실이라 순수 테스트가 닿지 못한다.
같은 저장소에 이미 배포되어 도는 선례(`PoseCompareFrames.tsx:39-64` `useSeekPaused`
— 주석: *"expo-video 는 소스 로드 전 currentTime 설정이 무시될 수 있어
statusChange(readyToPlay)에 맞춰 적용한다"*)가 있을 뿐 증명은 아니다.
**테스트 통과만으로 "고쳤다"고 보고하지 않는다** — 최종 판정은 belle 실기기.
