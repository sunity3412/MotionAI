// 재재생 settle 가드 — 순수 판정 + 상수 단일 출처 (quick-260807-k70, BELLE-0807-10).
//
// 순수 함수만 (player/react/타이머 의존 0 — `tsc --noEmit` + `node --test` 검증).
// driftHysteresis.ts 관례와 동일: 상수·판정을 순수 모듈이 소유하고 VideoCompare
// 는 import 해 호출만 한다. "재재생 직후 종료판정을 언제까지 유예하는가"만 정하고,
// 실제 pause 건너뜀은 VideoCompare 의 tick 이 한다.
//
// **판독 근거 (belle 08-07 저녁 "두번째/n번째 재생이 매번 깔끔하다고 보기 힘듦.
// 어떨 땐 잘 나오고 어떨 땐 끊기고")**
//
// 재재생(togglePlay isAtEnd)/처음으로(restart)는 양쪽 seek(0) 후 고정
// REPLAY_SEEK_DELAY_MS(200ms) 뒤 play() 한다. 200ms 는 경험 상수다 — 60→200
// 상향 이력("정은지 S3 buffer reset") 자체가 seek 적용 지연이 실재함의 선행
// 증거다. 적용이 200ms 를 넘기면 tick 의 종료판정이 stale current(=end)로
// either-own-end(followTick 활성 시 한쪽 stale 만으로 참)를 세워 방금 재개한
// 양쪽을 즉시 재-pause 한다. 사용자가 다시 탭하면 그땐 seek 이 적용돼 있어
// 성공한다 — "어떨 땐 잘 나오고 어떨 땐 끊기고"와 부합하는 결정론적 경로다.
// 이 가드는 seek 적용 관측('settled') 또는 상한('expired')까지 **종료판정만**
// 유예한다 — drift 보정·불변식·큐 판정은 무접촉 (최소 개입).

// 유예 상한 (tick 100ms × 20 = 2.0s — REPLAY_SEEK_DELAY_MS 200ms 의 10배).
// seek 적용이 그때까지 관측되지 않으면 정상 종료판정을 복원한다 (가드 영구화
// 금지 — 진짜 끝 상태를 무한정 가리면 자연 종료 pause 가 사라진다).
export const REPLAY_SETTLE_MAX_TICKS = 20;

export type ReplaySettleDecision = 'hold' | 'settled' | 'expired';

export type ReplaySettleInput = {
  /** 무장 후 경과 tick 수 (VideoCompare ref 가 hold 마다 +1). */
  ticksElapsed: number;
  hasLeft: boolean;
  hasRight: boolean;
  /** 각 패널 currentTime (초). */
  cL: number;
  cR: number;
  /** 각 패널 native duration (초). ≤0/NaN = 미산정. */
  dL: number;
  dR: number;
};

// 패널 settled = seek(0) 적용이 관측된 상태.
//   - duration 미산정(≤0/NaN): 그쪽은 tick 종료판정 자체가 안 돌므로 (d > 0
//     가드) 유예 대상이 아니다 — settled 취급.
//   - 유한 current < duration − 0.05: tick 종료판정(`current >= d − 0.05`)과
//     같은 끝 임계의 값 사본 — 끝 임계 미만이면 stale 종료 위치가 아니다.
//   - NaN/비유한 current: 판정 불가 — not settled (expiry 상한이 안전망).
function panelSettled(current: number, duration: number): boolean {
  if (!(duration > 0)) return true;
  if (!Number.isFinite(current)) return false;
  return current < duration - 0.05;
}

/**
 * 재재생 직후 종료판정 유예 여부 판정.
 *
 * 'settled': 존재하는 모든 패널의 seek 적용 관측 — 즉시 정상 종료판정 복원.
 * 'expired': ticksElapsed ≥ REPLAY_SETTLE_MAX_TICKS — stale 지속에도 복원
 *            (settled 가 우선 — 적용이 관측되면 상한 무관 즉시 복원).
 * 'hold':    그 외 — 이번 tick 의 종료판정 pause 실행을 건너뛴다.
 */
export function decideReplaySettle(
  input: ReplaySettleInput,
): ReplaySettleDecision {
  const leftSettled = !input.hasLeft || panelSettled(input.cL, input.dL);
  const rightSettled = !input.hasRight || panelSettled(input.cR, input.dR);
  if (leftSettled && rightSettled) return 'settled';
  if (input.ticksElapsed >= REPLAY_SETTLE_MAX_TICKS) return 'expired';
  return 'hold';
}
