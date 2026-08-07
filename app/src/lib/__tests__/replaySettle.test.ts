// 재재생 settle 가드 순수 판정 검증 (quick-260807-k70, BELLE-0807-10).
//
// 실행: node --test app/src/lib/__tests__/replaySettle.test.ts
// Node type stripping — 신규 npm 의존성 0 (driftHysteresis.test.ts 선례).
// node:test / node:assert 표준 모듈 + `.ts` import 만.
//
// 검증 축 (belle 08-07 저녁 "두번째/n번째 재생이 매번 깔끔하다고 보기 힘듦"):
//   1) 양쪽 seek 적용 관측(자기 duration 끝 임계 미만) → 'settled'
//      (즉시 정상 종료판정 복원).
//   2) 우측만 stale end(cR ≥ dR−0.05) → 'hold' (followTick 활성 시 한쪽 stale
//      만으로 either-own-end 재-pause 경로가 실재 — 그 경로를 유예).
//   3) 좌측만 stale end → 'hold'.
//   4) ticksElapsed ≥ REPLAY_SETTLE_MAX_TICKS → 'expired' (stale 지속에도
//      종료판정 복원 — 가드 영구화 금지).
//   5) duration 미산정(dR ≤ 0/NaN) 쪽은 settled 취급 (그쪽 종료판정 자체가 안 돎).
//   6) hasRight=false → 좌측만으로 판정 (단일 패널).
//   7) NaN/비유한 current → 그쪽 not settled ('hold' — expiry 가 안전망).
//   8) 상수 박제 — REPLAY_SETTLE_MAX_TICKS = 20 (tick 100ms × 20 = 2.0s).

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  REPLAY_SETTLE_MAX_TICKS,
  decideReplaySettle,
} from '../replaySettle.ts';

// 기본 입력 — 재재생 seek(0) 이 양쪽 다 적용된 직후 상태 (둘 다 0 부근).
const base = {
  ticksElapsed: 0,
  hasLeft: true,
  hasRight: true,
  cL: 0.05,
  cR: 0.05,
  dL: 10,
  dR: 8,
};

// ── Test 1: 양쪽 settled → 'settled' ────────────────────────────────────────

test('decideReplaySettle: 양쪽 현재시각이 끝 임계 미만이면 settled', () => {
  assert.equal(decideReplaySettle({ ...base }), 'settled');
  // 경계: current = duration − 0.05 는 끝 도달 (tick 종료판정 `>= d − 0.05` 와
  // 같은 임계 — 값 사본) → not settled.
  assert.equal(decideReplaySettle({ ...base, cL: 10 - 0.05 }), 'hold');
  // 그보다 작으면 settled.
  assert.equal(decideReplaySettle({ ...base, cL: 10 - 0.06 }), 'settled');
});

// ── Test 2: 우측만 stale end → 'hold' ───────────────────────────────────────

test('decideReplaySettle: 우측만 stale end 면 hold', () => {
  assert.equal(decideReplaySettle({ ...base, cR: 8 }), 'hold');
  // dR − 0.05 = 7.95 이상이면 stale end.
  assert.equal(decideReplaySettle({ ...base, cR: 7.96 }), 'hold');
});

// ── Test 3: 좌측만 stale end → 'hold' ───────────────────────────────────────

test('decideReplaySettle: 좌측만 stale end 면 hold', () => {
  assert.equal(decideReplaySettle({ ...base, cL: 10 }), 'hold');
});

// ── Test 4: 상한 도달 → 'expired' (가드 영구화 금지) ────────────────────────

test('decideReplaySettle: 상한 도달 시 expired — stale 지속에도 종료판정 복원', () => {
  assert.equal(
    decideReplaySettle({
      ...base,
      cR: 8,
      ticksElapsed: REPLAY_SETTLE_MAX_TICKS,
    }),
    'expired',
  );
  // 상한 직전은 여전히 hold.
  assert.equal(
    decideReplaySettle({
      ...base,
      cR: 8,
      ticksElapsed: REPLAY_SETTLE_MAX_TICKS - 1,
    }),
    'hold',
  );
  // settled 가 expired 보다 우선 — seek 적용이 관측되면 상한 무관 즉시 복원.
  assert.equal(
    decideReplaySettle({ ...base, ticksElapsed: REPLAY_SETTLE_MAX_TICKS }),
    'settled',
  );
});

// ── Test 5: duration 미산정 쪽은 settled 취급 ───────────────────────────────

test('decideReplaySettle: duration 미산정(≤0/NaN) 쪽은 settled 취급', () => {
  // 그쪽은 tick 종료판정 자체가 안 돌므로 (dR > 0 가드) 유예 대상이 아니다.
  assert.equal(decideReplaySettle({ ...base, dR: 0, cR: 99 }), 'settled');
  assert.equal(
    decideReplaySettle({ ...base, dR: Number.NaN, cR: 99 }),
    'settled',
  );
});

// ── Test 6: 단일 패널 (hasRight=false) ──────────────────────────────────────

test('decideReplaySettle: hasRight=false 면 좌측만으로 판정', () => {
  // 우측 값이 stale 이어도 무시.
  assert.equal(
    decideReplaySettle({ ...base, hasRight: false, cR: 99 }),
    'settled',
  );
  // 좌측이 stale 이면 hold.
  assert.equal(
    decideReplaySettle({ ...base, hasRight: false, cL: 10 }),
    'hold',
  );
});

// ── Test 7: NaN/비유한 current → 그쪽 not settled ───────────────────────────

test('decideReplaySettle: NaN/비유한 current 는 그쪽 not settled (hold)', () => {
  assert.equal(decideReplaySettle({ ...base, cR: Number.NaN }), 'hold');
  assert.equal(
    decideReplaySettle({ ...base, cL: Number.POSITIVE_INFINITY }),
    'hold',
  );
  // NaN 지속에도 상한이 안전망 — expired 로 탈출.
  assert.equal(
    decideReplaySettle({
      ...base,
      cR: Number.NaN,
      ticksElapsed: REPLAY_SETTLE_MAX_TICKS,
    }),
    'expired',
  );
});

// ── Test 8: 상수 박제 ───────────────────────────────────────────────────────

test('상수: REPLAY_SETTLE_MAX_TICKS = 20 (tick 100ms × 20 = 2.0s 상한)', () => {
  assert.equal(REPLAY_SETTLE_MAX_TICKS, 20);
});
