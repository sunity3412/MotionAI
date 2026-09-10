// 소스 교체 후 재생위치 복원 판정 검증 (quick-260910-euz).
//
// 실행: node --test app/src/lib/__tests__/sourceSwapSeek.test.ts
// Node type stripping — 신규 npm 의존성 0 (replaySettle.test.ts 선례).
// node:test / node:assert 표준 모듈 + `.ts` import 만.
//
// 검증 축 (belle 2026-09-10 실기기 "관절선 누르면 처음부터 재생된다", 8개.
// 각 축이 실제 결함 하나를 막는다):
//   1) status 가 계속 'loading' → 매번 wait, seek 0회. ← **기기 결함 그 자체**
//      (아직 안 익은 AVPlayerItem 에 exact seek 을 쏘던 경로를 여기서 끊는다).
//   2) 'loading' → 'readyToPlay' → seek 정확히 1회 (중복 seek 금지).
//   3) 구독 시점에 이미 'readyToPlay' → 즉시 seek. ← 이 축이 없으면 수리가
//      *전이*만 듣게 짜여 지금 정상 동작하는 맥 시뮬 경로를 깬다.
//   4) 'error' → abort (seek·play 둘 다 없음 — 조용한 0초 재생 강등 금지).
//   5) 검증 성공(오차 ≤ SWAP_VERIFY_TOLERANCE_S) → finish{play: wasPlaying}.
//   6) 검증 실패 + attempts < 3 → 재 seek. attempts === 3 → finish (포기해도
//      정지로 두지 않는다).
//   7) targetSec 이 NaN/음수/duration 초과 → 클램프. **NaN 이 seekSec 으로
//      새지 않음** (player.currentTime = NaN 은 네이티브 크래시 위험).
//   8) phase === 'done' 에서는 아무 행동도 안 함 (늦게 도착한 ready 신호로
//      되감기지 않는다).

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SWAP_READY_TIMEOUT_MS,
  SWAP_SEEK_ATTEMPTS,
  SWAP_VERIFY_TOLERANCE_S,
  clampSeekTarget,
  decideSwapSeek,
} from '../sourceSwapSeek.ts';

// 기본 입력 — 재생 중 12.4초 지점에서 칩을 눌러 교체를 막 시작한 상태.
const base = {
  phase: 'awaitingReady' as const,
  status: 'loading' as const,
  targetSec: 12.4,
  durationSec: 30,
  wasPlaying: true,
  observedSec: null as number | null,
  attempts: 0,
  waitedMs: 0,
};

// ── Test 1: ready 전에는 절대 seek 하지 않는다 ──────────────────────────────

test('decideSwapSeek: status 가 loading 인 동안에는 매번 wait — seek 0회', () => {
  let seeks = 0;
  // 100ms 폴백 tick 30회 = 3초. 대기 상한(6초) 안이므로 전부 wait 여야 한다.
  for (let tick = 0; tick < 30; tick += 1) {
    const d = decideSwapSeek({ ...base, waitedMs: tick * 100 });
    if (d.action === 'seek') seeks += 1;
    assert.equal(d.action, 'wait');
  }
  assert.equal(seeks, 0);
  // 'idle' 상태(교체 직후 아직 아무것도 모름)도 같다.
  assert.deepEqual(decideSwapSeek({ ...base, status: 'idle' }), {
    action: 'wait',
  });
  // 다만 영원히 기다리지는 않는다 — 상한에 닿으면 마지막 1회 시도.
  assert.equal(SWAP_READY_TIMEOUT_MS, 6000);
  assert.deepEqual(
    decideSwapSeek({ ...base, waitedMs: SWAP_READY_TIMEOUT_MS }),
    { action: 'seek', seekSec: 12.4 },
  );
  // 상한 직전은 여전히 wait.
  assert.deepEqual(
    decideSwapSeek({ ...base, waitedMs: SWAP_READY_TIMEOUT_MS - 1 }),
    { action: 'wait' },
  );
});

// ── Test 2: loading → readyToPlay 전이에서 seek 정확히 1회 ──────────────────

test('decideSwapSeek: loading 뒤 readyToPlay 가 오면 seek 은 정확히 1회', () => {
  // 호출부가 하는 일을 그대로 모사한다: seek 를 쏘면 phase 가 'seeking' 으로
  // 넘어가고, 되읽기 전에는 observedSec 이 null 이다.
  let phase: 'awaitingReady' | 'seeking' | 'done' = 'awaitingReady';
  let seeks = 0;
  const statuses = ['loading', 'loading', 'readyToPlay', 'readyToPlay'] as const;
  for (const status of statuses) {
    const d = decideSwapSeek({ ...base, phase, status });
    if (d.action === 'seek') {
      seeks += 1;
      assert.equal(d.seekSec, 12.4);
      phase = 'seeking';
    }
  }
  assert.equal(seeks, 1);
  // 'seeking' 으로 넘어간 뒤 늦게 온 ready 신호는 되읽기 전이라 wait.
  assert.deepEqual(
    decideSwapSeek({ ...base, phase: 'seeking', status: 'readyToPlay' }),
    { action: 'wait' },
  );
});

// ── Test 3: 구독 시점에 이미 readyToPlay → 즉시 seek ────────────────────────

test('decideSwapSeek: 이미 readyToPlay 면 전이를 기다리지 않고 즉시 seek', () => {
  // 맥 시뮬/캐시된 소스는 리스너를 걸기 전에 이미 ready 다. 전이만 듣게 짜면
  // 지금 정상 동작하는 이 경로가 죽는다.
  assert.deepEqual(
    decideSwapSeek({ ...base, status: 'readyToPlay', waitedMs: 0 }),
    { action: 'seek', seekSec: 12.4 },
  );
});

// ── Test 4: error → abort (seek 도 play 도 없다) ────────────────────────────

test('decideSwapSeek: status error 는 abort — 0초 재생으로 강등하지 않는다', () => {
  assert.deepEqual(decideSwapSeek({ ...base, status: 'error' }), {
    action: 'abort',
  });
  // seek 을 이미 쏜 뒤 로드가 무너져도 마찬가지.
  assert.deepEqual(
    decideSwapSeek({
      ...base,
      phase: 'seeking',
      status: 'error',
      observedSec: 0,
    }),
    { action: 'abort' },
  );
  // 단 절차가 끝난 뒤(done)에 오는 error 는 무동작이다 — 성공한 교체의 칩을
  // 뒤늦게 되돌리지 않는다 (Test 8 의 done 가드가 error 보다 앞선다).
  assert.deepEqual(
    decideSwapSeek({ ...base, phase: 'done', status: 'error' }),
    { action: 'wait' },
  );
});

// ── Test 5: 검증 성공 → finish{play: wasPlaying} ────────────────────────────

test('decideSwapSeek: 되읽은 값이 오차 안이면 finish, play 는 교체 전 상태', () => {
  assert.equal(SWAP_VERIFY_TOLERANCE_S, 0.35);
  const seeking = {
    ...base,
    phase: 'seeking' as const,
    status: 'readyToPlay' as const,
    attempts: 1,
  };
  assert.deepEqual(decideSwapSeek({ ...seeking, observedSec: 12.4 }), {
    action: 'finish',
    play: true,
  });
  // 경계 포함 — 정확히 오차만큼 벗어난 것은 성공.
  assert.deepEqual(
    decideSwapSeek({ ...seeking, observedSec: 12.4 + SWAP_VERIFY_TOLERANCE_S }),
    { action: 'finish', play: true },
  );
  // 멈춰 있었으면 멈춘 채로 끝난다 (교체가 재생을 시작시키지 않는다).
  assert.deepEqual(
    decideSwapSeek({ ...seeking, wasPlaying: false, observedSec: 12.4 }),
    { action: 'finish', play: false },
  );
  // 아직 되읽지 않았으면 판정하지 않는다.
  assert.deepEqual(decideSwapSeek({ ...seeking, observedSec: null }), {
    action: 'wait',
  });
});

// ── Test 6: 검증 실패 → 상한까지 재시도, 소진하면 finish ────────────────────

test('decideSwapSeek: 검증 실패는 상한까지 재 seek, 소진하면 정지가 아니라 finish', () => {
  assert.equal(SWAP_SEEK_ATTEMPTS, 3);
  const failed = {
    ...base,
    phase: 'seeking' as const,
    status: 'readyToPlay' as const,
    // 기기 증상 그 자체 — seek 이 안 먹어 0초에 서 있다.
    observedSec: 0,
  };
  for (let attempts = 1; attempts < SWAP_SEEK_ATTEMPTS; attempts += 1) {
    assert.deepEqual(decideSwapSeek({ ...failed, attempts }), {
      action: 'seek',
      seekSec: 12.4,
    });
  }
  assert.deepEqual(
    decideSwapSeek({ ...failed, attempts: SWAP_SEEK_ATTEMPTS }),
    { action: 'finish', play: true },
  );
  // 되읽은 값이 NaN 이어도 무한 대기에 빠지지 않는다 (오차 비교가 false →
  // 재시도 → 상한 소진 → finish).
  assert.deepEqual(
    decideSwapSeek({ ...failed, observedSec: Number.NaN, attempts: 1 }),
    { action: 'seek', seekSec: 12.4 },
  );
  assert.deepEqual(
    decideSwapSeek({
      ...failed,
      observedSec: Number.NaN,
      attempts: SWAP_SEEK_ATTEMPTS,
    }),
    { action: 'finish', play: true },
  );
});

// ── Test 7: 목표 시각 클램프 — NaN 이 seekSec 으로 새지 않는다 ──────────────

test('clampSeekTarget: NaN/음수/duration 초과를 쏠 수 있는 값으로 정리한다', () => {
  assert.equal(clampSeekTarget(Number.NaN, 30), 0);
  // ±Infinity 도 0 — "끝으로 보내라"가 아니라 "값을 못 읽었다"로 읽는다.
  // player.currentTime 은 해제 직후 비유한 값을 줄 수 있고, 그때 영상 끝으로
  // 뛰는 것보다 처음으로 서는 편이 덜 놀랍다.
  assert.equal(clampSeekTarget(Number.POSITIVE_INFINITY, 30), 0);
  assert.equal(clampSeekTarget(-1, 30), 0);
  assert.equal(clampSeekTarget(12.4, 30), 12.4);
  // duration 초과 → 끝 임계(duration − 0.05).
  assert.equal(clampSeekTarget(999, 30), 29.95);
  // duration 미산정(0/음수/NaN)이면 깎지 않는다 — 모르는 값으로 목표를 줄이지
  // 않는다. 새 소스의 duration 은 sourceLoad 직후에도 0 일 수 있다.
  assert.equal(clampSeekTarget(12.4, 0), 12.4);
  assert.equal(clampSeekTarget(12.4, Number.NaN), 12.4);
  // 아주 짧은 소스에서도 음수가 나오지 않는다.
  assert.equal(clampSeekTarget(1, 0.02), 0);

  // 판정을 거쳐도 NaN 이 새지 않는다 (이 값이 player.currentTime 으로 간다).
  const d = decideSwapSeek({
    ...base,
    status: 'readyToPlay',
    targetSec: Number.NaN,
  });
  assert.equal(d.action, 'seek');
  assert.equal(d.action === 'seek' && Number.isFinite(d.seekSec), true);
  assert.equal(d.action === 'seek' && d.seekSec, 0);
  // duration 을 모르는 채 ready 가 와도 목표는 그대로 간다.
  assert.deepEqual(
    decideSwapSeek({ ...base, status: 'readyToPlay', durationSec: 0 }),
    { action: 'seek', seekSec: 12.4 },
  );
});

// ── Test 8: done 이후 재발화 금지 ───────────────────────────────────────────

test('decideSwapSeek: phase done 에서는 아무 행동도 하지 않는다', () => {
  // 절차가 끝난 뒤 늦게 도착한 ready/sourceLoad 신호로 되감기면 안 된다.
  const done = { ...base, phase: 'done' as const };
  assert.deepEqual(decideSwapSeek({ ...done, status: 'readyToPlay' }), {
    action: 'wait',
  });
  assert.deepEqual(
    decideSwapSeek({ ...done, status: 'readyToPlay', observedSec: 0 }),
    { action: 'wait' },
  );
  assert.deepEqual(
    decideSwapSeek({ ...done, waitedMs: SWAP_READY_TIMEOUT_MS * 10 }),
    { action: 'wait' },
  );
  // 절차 시작 전(idle)도 같다 — 칩을 누르지 않았는데 움직이지 않는다.
  assert.deepEqual(
    decideSwapSeek({ ...base, phase: 'idle', status: 'readyToPlay' }),
    { action: 'wait' },
  );
});
