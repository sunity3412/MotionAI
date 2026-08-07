// 드리프트 보정 히스테리시스 순수 판정 검증 (quick-260807-iwp).
//
// 실행: node --test app/src/lib/__tests__/driftHysteresis.test.ts
// Node 24 type stripping — 신규 npm 의존성 0 (cueTrack.test.ts 선례).
// node:test / node:assert 표준 모듈 + `.ts` import 만.
//
// 검증 축 (belle 08-07 "정은지 선수 영상이 끊겨 가지구" — BELLE-0807-6):
//   1) 임계 이하 drift → 보정 안 함 (언제든).
//   2) 임계 초과 + 마지막 보정 seek 후 간격 내 → 대기 (연속 seek 스터터 차단).
//   3) 임계 초과 + 간격 경과 → 보정 (간격 후 잔존 drift 는 반드시 보정 — 수렴 보장).
//   4) 최초(lastSeekAt=0) → 즉시 허용.
//   5) 경계 정확히 800ms 경과 → 보정 (>= 판정).
//   6) NaN/비유한 drift → false (크래시 0).
//   7) 상수 박제 — 0.3s / 800ms (driftHysteresis.ts 단일 출처).

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DRIFT_CORRECT_THRESHOLD_S,
  DRIFT_SEEK_MIN_INTERVAL_MS,
  shouldCorrectDrift,
} from '../driftHysteresis.ts';

// ── Test 1: 임계 이하 → false ────────────────────────────────────────────────

test('shouldCorrectDrift: 임계(0.3s) 이하 drift 는 언제든 false', () => {
  assert.equal(shouldCorrectDrift(0.25, 10_000, 0), false);
  assert.equal(shouldCorrectDrift(0.25, 10_000, 9_900), false);
  // 임계 정확히 0.3 은 초과가 아니므로 false (기존 `drift >` 판정 보존).
  assert.equal(shouldCorrectDrift(0.3, 10_000, 0), false);
  assert.equal(shouldCorrectDrift(0, 10_000, 0), false);
});

// ── Test 2: 간격 내 대기 ─────────────────────────────────────────────────────

test('shouldCorrectDrift: 임계 초과여도 마지막 seek 후 0.2s 면 false (간격 내 대기)', () => {
  // lastSeekAt=10000, now=10200 → 경과 200ms < 800ms.
  assert.equal(shouldCorrectDrift(0.35, 10_200, 10_000), false);
});

// ── Test 3: 간격 후 잔존 drift 보정 (수렴 보장) ──────────────────────────────

test('shouldCorrectDrift: 마지막 seek 후 0.9s 경과 + 여전히 초과면 true', () => {
  // 간격 내엔 대기하고 간격 후 여전히 초과면 보정 — tick 100ms 상시 재판정이라
  // 동기화 수렴은 보장된다.
  assert.equal(shouldCorrectDrift(0.35, 10_900, 10_000), true);
});

// ── Test 4: 최초 보정 즉시 허용 ──────────────────────────────────────────────

test('shouldCorrectDrift: lastSeekAt=0(최초)이면 즉시 true', () => {
  // Date.now() 실시각(epoch ms)은 0 대비 항상 간격 초과 — 첫 보정은 즉시.
  assert.equal(shouldCorrectDrift(0.35, Date.now(), 0), true);
});

// ── Test 5: 경계 — 정확히 간격만큼 경과 → true (>= 판정) ────────────────────

test('shouldCorrectDrift: 정확히 800ms 경과는 true (>= 판정)', () => {
  assert.equal(
    shouldCorrectDrift(0.35, 10_000 + DRIFT_SEEK_MIN_INTERVAL_MS, 10_000),
    true,
  );
  // 1ms 모자라면 false.
  assert.equal(
    shouldCorrectDrift(0.35, 10_000 + DRIFT_SEEK_MIN_INTERVAL_MS - 1, 10_000),
    false,
  );
});

// ── Test 6: 비유한 drift → false (크래시 0) ─────────────────────────────────

test('shouldCorrectDrift: NaN/Infinity drift 는 false', () => {
  assert.equal(shouldCorrectDrift(Number.NaN, 10_000, 0), false);
  assert.equal(shouldCorrectDrift(Number.POSITIVE_INFINITY, 10_000, 0), false);
  assert.equal(shouldCorrectDrift(Number.NEGATIVE_INFINITY, 10_000, 0), false);
});

// ── Test 7: 상수 박제 (단일 출처) ────────────────────────────────────────────

test('상수: 임계 0.3s + 보정 seek 최소 간격 800ms', () => {
  assert.equal(DRIFT_CORRECT_THRESHOLD_S, 0.3);
  assert.equal(DRIFT_SEEK_MIN_INTERVAL_MS, 800);
});
