// 동작비교 재생 상태 불변식 판정 (260806-usc — V-1 / quick-260807-fpw — belle 08-07 #2).
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
//     않고, 편측 상태가 오래 지속되지 못하게 감시·집행한다.
//     원인 후보를 확정된 것처럼 쓰지 말 것(F-6 원칙).
//
// (c) belle 08-07 #2 개정 — 관찰창 안 "양쪽 정지"는 더 이상 무조건 정상이 아니다.
//     종전 R5 는 대칭이면 전부 무개입이라 **양쪽 다 play() 실효 실패**(대칭 정지)가
//     재시도 대상에서 빠졌다 — belle 실기기 랜덤 스톨(엘보 doc, 음성 후 재개 실패
//     잔존)이 이 사각에 남는다. togglePlay 양 분기가 관찰창을 닫으므로(사용자
//     제스처) 창 안의 양쪽 정지는 사용자 정지가 아니라 재개 실패다. 종전 (c)의
//     spin-up 유예("play() 직후 한두 tick false/false")는 첫 재시도가
//     RESUME_RETRY_AT_TICKS[0](0.5초) 뒤로 밀리며 스케줄이 자연 제공한다.
//
// (d) R6 시작 홀드 면제 근거: 32-08 실기기 피드백 #1 로 도입된 follow 블록이 정은지
//     (right)의 재생/정지를 소유한다. 목표시각(warp+offset)이 음수인 구간에서는 right
//     를 0 프레임에 세워 두는 것이 **의도된** 편측이다. 이 자리에서 right 에 play() 를
//     쏘면 두 로직이 매 tick 서로 싸운다. 단 면제는 단방향 — left 가 멈추고 right 만
//     도는 상태는 시작 홀드로 설명되지 않으므로 면제하지 않는다. 재시도(R7')가
//     양쪽 정지에 play 를 쏠 때도 startHold 중 right 는 leave (같은 의도 보존).

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

// belle 08-07 #2 (quick-260807-fpw) — 재시도 백오프 스케줄 (tick=100ms, belle 예시
// 그대로). 재개 후 0.5/1.5/3.5/6.5초 시점 = 간격 0.5/1/2/3초. 매 tick 즉시 재시도를
// 버린 이유: (1) spin-up 중 false/false 오판을 스케줄 지연이 흡수한다(헤더 (c)),
// (2) 짧은 재버퍼는 첫 재시도 전에 자연 회복된다 — 간격을 넓혀 가며 두드린다.
export const RESUME_RETRY_AT_TICKS: readonly number[] = [5, 15, 35, 65];

// play() 재시도 한도 = 스케줄 길이(4). 소진하고도 못 돌면 converge-pause 로 종결 —
// 어긋난 채 계속 진행하는 것보다 대칭 정지가 낫다(정렬 보존 + 호출부가 '일시정지됨
// — 탭하여 계속' 배지로 정직 표면화). 무한 play/pause 왕복(배터리·stutter)도 이
// 상한이 구조적으로 막는다. VideoCompare 의 제자리 seek nudge 조건
// (`RESUME_PLAY_RETRIES - 1`)은 무수정 승계 — 마지막 재시도 직전 1회 유지.
export const RESUME_PLAY_RETRIES = RESUME_RETRY_AT_TICKS.length;

// 마지막 재시도 후 converge 판정까지의 유예(1초) — 마지막 play() 의 실효를 기다린
// 뒤에만 최종 대칭 정지로 수렴한다.
export const RESUME_CONVERGE_GRACE_TICKS = 10;

// 관찰창 길이 = 마지막 재시도 시각 + 유예 (75 tick = 7.5초). 그 뒤의 재생 상태는
// 사용자 영역이다 — 상시 감시로 늘리면 정상 주행에까지 개입할 여지가 생긴다
// (T-usc-01). 스케줄에서 파생하므로 sanity(마지막+유예=관찰창)가 구조로 성립한다.
export const RESUME_WATCH_TICKS =
  RESUME_RETRY_AT_TICKS[RESUME_RETRY_AT_TICKS.length - 1] +
  RESUME_CONVERGE_GRACE_TICKS;

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

  // R5' — 양쪽 재생 = 회복(개입 0). **관찰창 안 "양쪽 정지"는 더 이상 무조건
  // 정상이 아니다** (belle 08-07 #2, 헤더 (c) 개정) — 아래 R7'/R8' 가 스케줄로
  // 재시도/수렴을 처리한다.
  if (leftPlaying && rightPlaying) return NONE;

  // R6 — 시작 홀드는 의도된 편측(헤더 (d)). 면제는 단방향.
  if (startHold && leftPlaying && !rightPlaying) return NONE;

  // R7' — 재시도 잔여: 스케줄 시각(RESUME_RETRY_AT_TICKS[used])에 도달하면 정지된
  // 쪽에 play (양쪽 정지면 양쪽 — belle 랜덤 스톨 회복의 핵심 신설 경로). 단
  // startHold 중 right 는 leave (R6 의도 편측 보존). 시각 전이면: 편측은
  // enforce-pause 로 도는 쪽을 멈춰 드리프트를 차단하고(대기 중 편측 진행 금지 —
  // 불변식 정신), 양쪽 정지는 NONE (재시도 시각까지 대기).
  if (resumeRetriesUsed < RESUME_PLAY_RETRIES) {
    if (resumeWatchTicks >= RESUME_RETRY_AT_TICKS[resumeRetriesUsed]) {
      return {
        action: 'retry-play',
        left: leftPlaying ? 'leave' : 'play',
        right: rightPlaying ? 'leave' : startHold ? 'leave' : 'play',
        consumeRetry: true,
        closeWatch: false,
      };
    }
    if (leftPlaying !== rightPlaying) {
      return {
        action: 'enforce-pause',
        left: leftPlaying ? 'pause' : 'leave',
        right: rightPlaying ? 'pause' : 'leave',
        consumeRetry: false,
        closeWatch: false,
      };
    }
    return NONE;
  }

  // R8' — 재시도 소진: RESUME_WATCH_TICKS 도달 시 converge-pause (재생 중인 쪽만
  // pause — 이미 양쪽 정지면 호출 0 의 대칭 정지 종결) + closeWatch. 호출부는 이
  // 액션에서 '일시정지됨 — 탭하여 계속' 배지를 세운다 (belle 08-07 #2 정직
  // 표면화). 그 전(마지막 재시도 유예 중)엔 편측만 enforce-pause, 양쪽 정지는
  // NONE (마지막 play() 의 실효 대기).
  if (resumeWatchTicks >= RESUME_WATCH_TICKS) {
    return {
      action: 'converge-pause',
      left: leftPlaying ? 'pause' : 'leave',
      right: rightPlaying ? 'pause' : 'leave',
      consumeRetry: false,
      closeWatch: true,
    };
  }
  if (leftPlaying !== rightPlaying) {
    return {
      action: 'enforce-pause',
      left: leftPlaying ? 'pause' : 'leave',
      right: rightPlaying ? 'pause' : 'leave',
      consumeRetry: false,
      closeWatch: false,
    };
  }
  return NONE;
}
