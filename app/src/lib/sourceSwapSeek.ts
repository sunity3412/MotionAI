// 소스 교체 후 재생위치 복원 판정 — 순수 판정 + 상수 단일 출처 (quick-260910-euz).
//
// 순수 함수만 (player/react/expo-video/타이머 의존 0 — `tsc --noEmit` +
// `node --test` 로 검증). playbackInvariant.ts / replaySettle.ts /
// driftHysteresis.ts 관례와 동일: 상수·판정을 순수 모듈이 소유하고
// RenderedComparePlayer 는 import 해 호출만 한다. 여기서는 "지금 기다릴지, seek
// 할지, 끝낼지, 포기할지"만 정하고 실제 replaceAsync/currentTime 대입/play 는
// 컴포넌트가 한다.
//
// 실행: node --test app/src/lib/__tests__/sourceSwapSeek.test.ts
//
// **왜 이 파일이 있는가 (belle 2026-09-10 실기기 반려, TestFlight/LTE)**
//
// 합성 비교 플레이어의 '관절선' 칩은 표시 있는 판 ↔ 없는 판 두 mp4 를 갈아끼운다.
// 그런데 기기에서 칩을 누르면 영상이 **처음부터** 재생됐다. 같은 조작이 가끔은
// 정상이었고(belle: "처음부터 안돌아가기도 하는거 같고"), 맥 시뮬레이터에서는
// 2026-09-09 에 정상으로만 관측됐다. expo-video 3.0.16 네이티브 소스를 읽어 확정한
// 원인은 두 축이다.
//
//   축 1 — ready 아닌 아이템에 exact seek 을 쏜다.
//     `replaceAsync`(ios/VideoModule.swift:330-333)가 부르는 async
//     `replaceCurrentItem`(ios/VideoPlayer.swift:236-268)은 main 큐 블록을 **예약만
//     하고 반환**한다. `DangerousPropertiesStore`(ios/VideoPlayer/
//     DangerousPropertiesStore.swift:1-2, 7-14)는 주석 그대로 "아이템이 아직 안
//     꽂혔다"만 막지 "아직 안 익었다"는 안 막는다 — `applyProperties` 가
//     `ref.replaceCurrentItem` 바로 다음 줄(:264-266)에서 같은 블록 안에 돌기
//     때문이다. 결국 status `.unknown` 인 새 AVPlayerItem 에
//     `ref.seek(to:, toleranceBefore: .zero, toleranceAfter: .zero)`
//     (ios/VideoPlayer.swift:55)가 날아간다. 새 아이템은 아무것도 프리로드하지
//     않으므로(ios/VideoPlayerItem.swift:27 `automaticallyLoadedAssetKeys: nil`)
//     소스가 원격 S3 presigned mp4 인 지금, moov + t≈at 부근 샘플이 도착하기까지의
//     창이 맥에서는 ~0, LTE 폰에서는 초 단위다. **sim/device 차이가 기계적으로
//     나오는 축.**
//
//   축 2 — 교체 전에 멈추지 않아 재생 의사가 살아남는다.
//     `replaceCurrentItem` 어디에도 pause 가 없고 `rate` 는 AVPlayer 레벨
//     (ios/VideoPlayer.swift:32-35)이라 아이템 교체를 넘어 유지된다. 재생 중에
//     토글하면 새 아이템이 ready 되는 즉시 0초부터 돈다.
//
// 그래서 채택한 순서가 **교체 전 pause → ready 대기 → seek → 되읽어 검증 →
// 재시도 → 그 다음에만 play** 이고, 이 모듈은 그 순서의 판정부다.
//
// 계기는 `sourceLoad` 가 정본, `statusChange` 가 보조다 — iOS 는
// `statusChange('readyToPlay')` 를 직접 emit 하는 자리가 없고
// `isPlaybackLikelyToKeepUp`/`timeControlStatus` KVO 부수효과로만 낸다
// (ios/VideoPlayerObserver.swift:449-450, 475-481). **pause 상태로 기다리면
// `timeControlStatus` 가 안 변하므로** statusChange 단독으로는 못 쓴다.
//
// **이 모듈이 증명하지 못하는 것 (감추지 않고 적어 둔다)**
//   "readyToPlay 에서 `player.currentTime = x` 가 iOS 실기기에서 실제로 먹는가"는
//   AVFoundation 런타임 사실이라 순수 테스트가 닿지 못한다. 같은 저장소에 이미
//   배포되어 도는 선례(PoseCompareFrames.tsx:39-64 `useSeekPaused`)가 있을 뿐
//   증명은 아니다. 최종 판정은 belle 실기기.

/** 교체 절차의 진행 단계. 소유자는 RenderedComparePlayer 의 ref. */
export type SwapPhase = 'idle' | 'awaitingReady' | 'seeking' | 'done';

/** expo-video `VideoPlayer.status` 와 같은 집합 (VideoPlayer.types.d.ts:278). */
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

// 검증 허용 오차(초). seek 은 exact tolerance 로 나가지만 되읽는 값은 프레임
// 경계로 스냅되고, 소스가 9fps 계열 합성본이라 한 프레임이 ~0.11s 다. 0.35s 는
// 그 몇 배 여유 — 이보다 좁히면 성공한 seek 을 실패로 읽어 헛재시도가 늘고,
// 넓히면 "처음으로 돌아갔다"(=0 부근)를 성공으로 오판할 여지가 생긴다.
export const SWAP_VERIFY_TOLERANCE_S = 0.35;

// seek 시도 상한. 소진하면 포기하되 **정지로 두지 않는다** (아래 규칙 참조).
export const SWAP_SEEK_ATTEMPTS = 3;

// ready 신호 대기 상한(ms). LTE 에서 원격 mp4 의 moov 도착이 초 단위인 것이 이
// 결함의 축 1 이라 넉넉히 잡는다. 상한에 닿으면 마지막으로 한 번 seek 을 쏘고
// 절차를 진행시킨다 — 영원히 기다려 칩이 잠긴 채 남는 것이 더 나쁘다.
export const SWAP_READY_TIMEOUT_MS = 6000;

/**
 * 목표 시각을 실제로 쏠 수 있는 값으로 정리한다.
 *
 * - NaN/±Infinity/음수 → 0 (**NaN 이 `player.currentTime` 으로 새면 안 된다**).
 * - `durationSec > 0` → `duration - 0.05` 를 넘지 않는다 (끝 임계 — replaySettle.ts
 *   의 같은 0.05 관례). 결과는 항상 0 이상.
 * - `durationSec <= 0`/NaN → 아직 duration 을 모르는 것이므로 클램프하지 않는다
 *   (모르는 값으로 목표를 깎지 않는다).
 */
export function clampSeekTarget(targetSec: number, durationSec: number): number {
  if (!Number.isFinite(targetSec) || targetSec < 0) return 0;
  if (!(durationSec > 0)) return targetSec;
  return Math.max(0, Math.min(targetSec, durationSec - 0.05));
}

/**
 * 교체 절차의 한 걸음을 정한다.
 *
 * 분기 순서가 곧 우선순위다 (위에서 걸리면 아래는 보지 않는다).
 *
 *  1) `done`/`idle` — 절차 밖. 아무 행동도 하지 않는다. `done` 뒤에 늦은 ready
 *     신호가 또 와도 되감기지 않게 하는 것이 이 가드의 목적이다.
 *  2) `error` — abort. seek 도 play 도 하지 않는다. 로드 실패를 조용한 0초
 *     재생으로 강등하지 않는다 (호출부는 칩을 되돌린다).
 *  3) `awaitingReady` — ready 이거나 대기 상한이면 seek, 아니면 wait.
 *  4) `seeking` — 되읽은 값이 없으면 wait, 오차 안이면 finish, 아니면 시도
 *     상한까지 재 seek. 상한을 소진해도 `finish` 다 — **재생 중에 토글했는데
 *     멈춰 있는 것도 고장**이라 정지로 두지 않는다.
 */
export function decideSwapSeek(input: SwapDecisionInput): SwapDecision {
  const { phase, status, targetSec, durationSec, wasPlaying, observedSec } =
    input;

  // 1) 절차 밖 — 재발화 금지.
  if (phase === 'done' || phase === 'idle') return { action: 'wait' };

  // 2) 로드 실패.
  if (status === 'error') return { action: 'abort' };

  const seekSec = clampSeekTarget(targetSec, durationSec);

  // 3) ready 대기. **전이가 아니라 상태**를 본다 — 구독 시점에 이미
  //    readyToPlay 인 경우(캐시/맥 시뮬)가 지금 정상 동작하는 경로다.
  if (phase === 'awaitingReady') {
    if (status === 'readyToPlay') return { action: 'seek', seekSec };
    if (input.waitedMs >= SWAP_READY_TIMEOUT_MS) {
      return { action: 'seek', seekSec };
    }
    return { action: 'wait' };
  }

  // 4) seek 검증.
  if (observedSec === null) return { action: 'wait' };
  if (Math.abs(observedSec - seekSec) <= SWAP_VERIFY_TOLERANCE_S) {
    return { action: 'finish', play: wasPlaying };
  }
  if (input.attempts < SWAP_SEEK_ATTEMPTS) return { action: 'seek', seekSec };
  return { action: 'finish', play: wasPlaying };
}
