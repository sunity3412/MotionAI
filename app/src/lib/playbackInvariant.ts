// 동작비교 재생 상태 불변식 판정 (260806-usc — V-1).
//
// 순수 함수만 (player/react/타이머 의존 0 — `tsc --noEmit` + `node --test` 로 검증).
// manualOffset.ts 헤더 관례와 동일: 판정을 순수 함수로 격리해 재생 제어(play/pause/
// seek)의 부작용과 분리한다. 여기서는 "무엇을 해야 하는가"만 정하고, 실제 호출은
// VideoCompare 의 tick 이 한다.
//
// **왜 이 파일이 있는가**
//
// (a) 33-13 D-13 승인 설계의 불변식 = "음성 큐가 말하는 동안 두 영상은 함께 멈추고,
//     음성이 끝나면 함께 돈다". 지금 코드는 이 불변식을 **전이 순간에 한 번만**
//     집행한다(발화 시 pause 2줄 / 종료 시 play 2줄). 그 호출 중 한쪽이 실효하지
//     않으면 되돌릴 주체가 없어 편측 상태가 그대로 남는다 — belle 실기기 V-1
//     (엘보 doc: 내 영상 4.9s 동결, 정은지만 10초대까지 진행, 음성 종료 후에도 미재개).
//
// (b) **시뮬(iOS 26.5, 개발빌드 #29)에서 V-1 은 재현되지 않았다** — 큐1 4.1/4.2 동시
//     정지, 종료 후 양쪽 재개, 큐2 6.7/6.7 동시 정지, 최종 13.3/13.5 동기 주행.
//     즉 상태머신은 이상 조건에서 옳다. 그래서 이 모듈은 **원인 수리가 아니라 결과
//     수렴 수리**다. 재버퍼 스톨인지 mid-tick 레이스인지 play() 무실효인지 가리지
//     않고, 편측 상태가 100ms(1 tick) 이상 지속되지 못하게 상시 감시·집행한다.
//     원인 후보를 확정된 것처럼 쓰지 말 것(F-6 원칙).
//
// (c) R5 가 "양쪽 정지"를 정상으로 보는 이유: play() 직후 두 플레이어가 아직 spin-up
//     중이면 leftPlaying=rightPlaying=false 가 한두 tick 관측된다. 이걸 위반으로 세면
//     재개할 때마다 재시도를 소진하고 converge-pause 로 수렴해 버린다. **대칭이면
//     건드리지 않는다** — 위반은 "갈라진 것"이지 "안 도는 것"이 아니다.
//
// (d) R6 시작 홀드 면제 근거: 32-08 실기기 피드백 #1 로 도입된 follow 블록이 정은지
//     (right)의 재생/정지를 소유한다. 목표시각(warp+offset)이 음수인 구간에서는 right
//     를 0 프레임에 세워 두는 것이 **의도된** 편측이다. 이 자리에서 right 에 play() 를
//     쏘면 두 로직이 매 tick 서로 싸운다. 단 면제는 단방향 — left 가 멈추고 right 만
//     도는 상태는 시작 홀드로 설명되지 않으므로 면제하지 않는다.

/** 한쪽 플레이어에 내릴 명령. 'leave' = 무동작(호출 자체를 하지 않는다). */
export type PlaybackSideCommand = 'play' | 'pause' | 'leave';

export type PlaybackInvariantInput = {
  hasLeft: boolean;
  hasRight: boolean;
  /** 타임라인 드래그 중 — 사용자 제스처 우선(기존 tick 규율과 동일). */
  scrubbing: boolean;
  /** 음성 큐 때문에 멈춰 있는 상태(사용자 정지와 구분). */
  voicePaused: boolean;
  leftPlaying: boolean;
  rightPlaying: boolean;
  /** null = 관찰창 밖, 0.. = 음성 종료 재개 후 경과 tick 수. */
  resumeWatchTicks: number | null;
  resumeRetriesUsed: number;
  /** follow 블록의 시작 홀드(목표시각 < 0 — right 가 의도적으로 정지). */
  startHold: boolean;
};

export type PlaybackInvariantDecision = {
  action: 'none' | 'enforce-pause' | 'retry-play' | 'converge-pause';
  left: PlaybackSideCommand;
  right: PlaybackSideCommand;
  /** true → 호출부가 재시도 카운터 +1. */
  consumeRetry: boolean;
  /** true → 호출부가 관찰창을 닫는다(null). */
  closeWatch: boolean;
};

// 관찰창 길이(tick 수). tick 100ms × 10 = 재개 후 **1초만** 감시한다. 재개가 실효
// 했는지는 1초면 판가름 나고, 그 뒤의 재생 상태는 사용자 영역이다 — 상시 감시로
// 늘리면 정상 주행에까지 개입할 여지가 생긴다(T-usc-01).
export const RESUME_WATCH_TICKS = 10;

// play() 재시도 한도. 3회 ≈ 300ms 안에 못 돌면 재시도를 더 쌓지 않고 양쪽을 함께
// 멈춘다 — 어긋난 채 계속 진행하는 것보다 대칭 정지가 낫다(정렬이 보존되고 사용자가
// 재생 버튼으로 재개할 수 있다). 무한 play/pause 왕복(배터리·stutter)도 이 상한이
// 구조적으로 막는다.
export const RESUME_PLAY_RETRIES = 3;

const NONE: PlaybackInvariantDecision = {
  action: 'none',
  left: 'leave',
  right: 'leave',
  consumeRetry: false,
  closeWatch: false,
};

/**
 * 한 tick 의 재생 상태를 보고 개입 여부/내용을 정한다.
 *
 * 분기 순서 = 우선순위 R1~R8 (위에서 걸리면 아래는 보지 않는다). 코드 순서를 규칙
 * 순서와 일치시켜 읽는 사람이 우선순위를 코드에서 그대로 보게 한다.
 */
export function decidePlaybackInvariant(
  input: PlaybackInvariantInput,
): PlaybackInvariantDecision {
  const {
    hasLeft,
    hasRight,
    scrubbing,
    voicePaused,
    leftPlaying,
    rightPlaying,
    resumeWatchTicks,
    resumeRetriesUsed,
    startHold,
  } = input;

  // R1 — 한쪽 패널만 있는 화면엔 대칭 개념이 없다.
  if (!hasLeft || !hasRight) return NONE;

  // R2 — 사용자 제스처 우선. 드래그 중 자동 개입은 stutter 를 만든다.
  if (scrubbing) return NONE;

  // R3 — 음성 정지 중에는 어느 쪽도 혼자 진행하지 않는다. 도는 쪽만 멈추고,
  // 둘 다 정지면 개입 0(불필요한 pause 호출을 만들지 않는다).
  if (voicePaused) {
    if (!leftPlaying && !rightPlaying) return NONE;
    return {
      action: 'enforce-pause',
      left: leftPlaying ? 'pause' : 'leave',
      right: rightPlaying ? 'pause' : 'leave',
      consumeRetry: false,
      closeWatch: false,
    };
  }

  // R4 — 관찰창 밖 정상 주행에는 절대 개입하지 않는다(D-13 두 국면에만 개입).
  if (resumeWatchTicks === null || resumeWatchTicks > RESUME_WATCH_TICKS) {
    return NONE;
  }

  // R5 — 대칭(양쪽 재생 / 양쪽 정지)은 정상. 헤더 (c) 참조.
  if (leftPlaying === rightPlaying) return NONE;

  // R6 — 시작 홀드는 의도된 편측(헤더 (d)). 면제는 단방향.
  if (startHold && leftPlaying && !rightPlaying) return NONE;

  // R7 — 재시도 여유가 있으면 안 도는 쪽에 play() 를 재시도한다.
  if (resumeRetriesUsed < RESUME_PLAY_RETRIES) {
    return {
      action: 'retry-play',
      left: leftPlaying ? 'leave' : 'play',
      right: rightPlaying ? 'leave' : 'play',
      consumeRetry: true,
      closeWatch: false,
    };
  }

  // R8 — 재시도를 소진하고도 편측이면 양쪽을 함께 멈춰 정렬을 보존한다.
  return {
    action: 'converge-pause',
    left: 'pause',
    right: 'pause',
    consumeRetry: false,
    closeWatch: true,
  };
}
