/**
 * visualCards 순수 로직 검증 — plain-node (`node --test`).
 *
 * 리뷰 M-03 은 "typecheck 이상의 검증"을 요구했다. jest-expo 도입이 철회돼
 * (devDependency 1,120개) 컴포넌트 층 검증은 드롭됐고, 순수 로직만 신규 의존성 0 으로
 * 여기서 고정한다. Node 24 의 네이티브 타입 스트리핑으로 .ts 를 그대로 실행한다.
 *
 * 실행: cd app && node --test src/lib/__tests__/visualCards.test.mjs
 *
 * 이 파일은 런타임 의존성이 없어야 한다 — visualCards.ts 가 import 0 인 이유와 동일.
 *
 * 왜 .ts 가 아니라 .mjs 인가: node 로 .ts 를 직접 import 하려면 확장자를 명시해야
 * 하는데(`../visualCards.ts`), tsc 는 allowImportingTsExtensions 없이는 이를 TS5097
 * 로 거부한다. tsconfig.json 은 이 플랜의 소유 범위 밖이라, 검증 대상 모듈은 완전히
 * 타입 검사되는 .ts 로 두고 **테스트 하네스만** .mjs 로 뺐다 (tsc 는 .mjs 를 보지 않음).
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  CORRECTED_POSE_PENDING_TIMEOUT_MS,
  ROTATION_PENDING_TIMEOUT_MS,
  isDailyLimit,
  isFeatureDisabled,
  mapFrameIdx,
  pickCompareFrames,
  visualCardState,
} from '../visualCards.ts';

const NOW = 1_000_000_000_000;
const T = CORRECTED_POSE_PENDING_TIMEOUT_MS;

// --- 상태 전이표 (legacy 부재 / failed / pending 신선 / pending 만료 / done) ---

test('status 부재(legacy doc) → hidden', () => {
  assert.equal(visualCardState(undefined, undefined, NOW, T), 'hidden');
});

test("status 'failed' → hidden (D-08 조용한 폴백 — 부재와 동일 처리)", () => {
  assert.equal(visualCardState('failed', NOW, NOW, T), 'hidden');
});

test("status 'done' → done", () => {
  assert.equal(visualCardState('done', NOW - T * 10, NOW, T), 'done');
});

test('pending + 신선 → pending', () => {
  assert.equal(visualCardState('pending', NOW - 1_000, NOW, T), 'pending');
});

test('pending + 타임아웃 초과 → hidden (고아 방어)', () => {
  assert.equal(visualCardState('pending', NOW - T - 1, NOW, T), 'hidden');
});

test('타임아웃 경계: 정확히 timeout 은 아직 pending (초과분만 hidden)', () => {
  assert.equal(visualCardState('pending', NOW - T, NOW, T), 'pending');
  assert.equal(visualCardState('pending', NOW - T - 1, NOW, T), 'hidden');
});

test('pending + updatedAtMs 부재/비정상 → pending 유지 (판정 포기, 자리표시 보존)', () => {
  assert.equal(visualCardState('pending', undefined, NOW, T), 'pending');
  assert.equal(visualCardState('pending', NaN, NOW, T), 'pending');
});

test('done 은 타임아웃과 무관 (완료 후 오래된 문서도 표시)', () => {
  assert.equal(visualCardState('done', NOW - T * 100, NOW, T), 'done');
});

test('회전 타임아웃이 교정 이미지보다 길다 (worker 폴링 상한 반영)', () => {
  assert.ok(ROTATION_PENDING_TIMEOUT_MS > CORRECTED_POSE_PENDING_TIMEOUT_MS);
});

// --- mapFrameIdx: 비율 매핑 · clamp · 비정상 입력 ---

test('mapFrameIdx: 동일 프레임 공간이면 항등', () => {
  assert.equal(mapFrameIdx(7, 30, 30), 7);
});

test('mapFrameIdx: 비율 환산 (축소/확대)', () => {
  assert.equal(mapFrameIdx(10, 100, 50), 5);
  assert.equal(mapFrameIdx(10, 50, 100), 20);
});

test('mapFrameIdx: 상한 clamp — toFrames-1 을 넘지 않는다', () => {
  const out = mapFrameIdx(99, 100, 10);
  assert.notEqual(out, null);
  assert.ok(out <= 9);
});

test('mapFrameIdx: 비정상 입력은 null (0 폴백 금지 — 엉뚱한 순간 렌더 방지)', () => {
  assert.equal(mapFrameIdx(-1, 10, 10), null);
  assert.equal(mapFrameIdx(1.5, 10, 10), null);
  assert.equal(mapFrameIdx(10, 10, 10), null, 'idx >= fromFrames 는 범위 밖');
  assert.equal(mapFrameIdx(0, 0, 10), null);
  assert.equal(mapFrameIdx(0, 10, 0), null);
});

// --- pickCompareFrames: refMatched 게이트 ---

test('pickCompareFrames: refMatched true + 정수 인덱스 → 쌍 반환', () => {
  assert.deepEqual(
    pickCompareFrames([{ userFrameIdx: 12, refFrameIdx: 34, refMatched: true }]),
    { userIdx: 12, refIdx: 34 },
  );
});

test('pickCompareFrames: refMatched false → null (뷰어 숨김 — 거짓 비교 금지)', () => {
  assert.equal(
    pickCompareFrames([{ userFrameIdx: 12, refFrameIdx: 34, refMatched: false }]),
    null,
  );
});

test('pickCompareFrames: refMatched 부재(legacy doc) → null', () => {
  assert.equal(pickCompareFrames([{ userFrameIdx: 12, refFrameIdx: 34 }]), null);
});

test('pickCompareFrames: 빈 배열/부재 → null', () => {
  assert.equal(pickCompareFrames([]), null);
  assert.equal(pickCompareFrames(undefined), null);
});

test('pickCompareFrames: 인덱스 누락/비정수/음수 → null', () => {
  assert.equal(pickCompareFrames([{ userFrameIdx: 1, refMatched: true }]), null);
  assert.equal(
    pickCompareFrames([{ userFrameIdx: 1.5, refFrameIdx: 2, refMatched: true }]),
    null,
  );
  assert.equal(
    pickCompareFrames([{ userFrameIdx: -1, refFrameIdx: 2, refMatched: true }]),
    null,
  );
});

test('pickCompareFrames: top-1 만 본다 (뒤에 유효 항목이 있어도 무시)', () => {
  assert.equal(
    pickCompareFrames([
      { userFrameIdx: 1, refFrameIdx: 2, refMatched: false },
      { userFrameIdx: 3, refFrameIdx: 4, refMatched: true },
    ]),
    null,
  );
});

// --- 오류 code 분기 ---

test('isDailyLimit / isFeatureDisabled: code 로만 분기 (message 파싱 금지)', () => {
  assert.equal(isDailyLimit({ code: 'daily_limit' }), true);
  assert.equal(isDailyLimit({ code: 'feature_disabled' }), false);
  assert.equal(isFeatureDisabled({ code: 'feature_disabled' }), true);
  assert.equal(isFeatureDisabled({ code: 'daily_limit' }), false);
});

test('오류 판별: 비객체/null/code 부재는 false (throw 하지 않음)', () => {
  for (const bad of [null, undefined, 'daily_limit', 42, {}, { code: 1 }]) {
    assert.equal(isDailyLimit(bad), false);
    assert.equal(isFeatureDisabled(bad), false);
  }
});
