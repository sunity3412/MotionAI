// 음성 멈춤 기준 패널 짝 프레임 스냅 맵 순수 로직 검증 (quick-260807-iwp).
//
// 실행: node --test app/src/lib/__tests__/voiceSnap.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행된다 — 신규 npm 의존성 0
// (cueTrack.test.ts 선례). node:test / node:assert 표준 모듈 + `.ts` import 만.
//
// 검증 축 (belle 08-07 "정은지 선수 영상이 음성이랑 안 맞는다" — BELLE-0807-5):
//   1) buildRefSnapSecs — {recordId, refVideoSec} 유효 쌍만 맵 등재.
//   2) refVideoSec 부재/NaN/Infinity/음수 쌍 드롭 — 순간 날조 0 (refMatched=false
//      실업로드·legacy doc 은 스냅 생략).
//   3) recordId 부재/null/빈 문자열 쌍 드롭 (조인 키 없는 스냅 금지).
//   4) 중복 recordId — first-wins (결정성).
//   5) 입력 null/undefined/빈 배열 — 빈 맵 (크래시 0).

import test from 'node:test';
import assert from 'node:assert/strict';
import { buildRefSnapSecs } from '../voiceSnap.ts';

// ── Test 1: 유효 쌍 등재 ─────────────────────────────────────────────────────

test('buildRefSnapSecs: 유효 {recordId, refVideoSec} 쌍을 맵으로 등재한다', () => {
  const out = buildRefSnapSecs([
    { recordId: 'r01:leg_extension', refVideoSec: 6.44 },
    { recordId: 'r02:split_angle', refVideoSec: 0 }, // 0초(영상 시작)도 유효
  ]);
  assert.deepEqual(out, {
    'r01:leg_extension': 6.44,
    'r02:split_angle': 0,
  });
});

// ── Test 2: refVideoSec 무효 쌍 드롭 (fabricate 0) ──────────────────────────

test('buildRefSnapSecs: refVideoSec 부재/NaN/Infinity/음수 쌍은 드롭한다', () => {
  const out = buildRefSnapSecs([
    { recordId: 'r00' }, // 부재 — refMatched=false / legacy doc
    { recordId: 'r01', refVideoSec: Number.NaN },
    { recordId: 'r02', refVideoSec: Number.POSITIVE_INFINITY },
    { recordId: 'r03', refVideoSec: Number.NEGATIVE_INFINITY },
    { recordId: 'r04', refVideoSec: -0.5 },
    { recordId: 'r05', refVideoSec: 2.5 }, // 유일한 유효 쌍
  ]);
  assert.deepEqual(out, { r05: 2.5 });
});

// ── Test 3: recordId 무효 쌍 드롭 ────────────────────────────────────────────

test('buildRefSnapSecs: recordId 부재/null/빈 문자열 쌍은 드롭한다', () => {
  const out = buildRefSnapSecs([
    { refVideoSec: 1.0 }, // recordId 부재
    { recordId: null, refVideoSec: 1.5 }, // null (DeductionRecord.recordId 계약)
    { recordId: '', refVideoSec: 2.0 }, // 빈 문자열
    { recordId: 'r09', refVideoSec: 3.0 },
  ]);
  assert.deepEqual(out, { r09: 3.0 });
});

// ── Test 4: 중복 recordId first-wins ────────────────────────────────────────

test('buildRefSnapSecs: 중복 recordId 는 first-wins (결정성)', () => {
  const out = buildRefSnapSecs([
    { recordId: 'r01', refVideoSec: 1.1 },
    { recordId: 'r01', refVideoSec: 9.9 }, // 뒤 쌍은 무시
  ]);
  assert.deepEqual(out, { r01: 1.1 });
});

// ── Test 5: 입력 자체가 없거나 비면 빈 맵 (크래시 0) ─────────────────────────

test('buildRefSnapSecs: null/undefined/빈 배열 입력은 빈 맵', () => {
  assert.deepEqual(buildRefSnapSecs(null), {});
  assert.deepEqual(buildRefSnapSecs(undefined), {});
  assert.deepEqual(buildRefSnapSecs([]), {});
  // 배열 원소 자체가 null/undefined 여도 크래시 없이 스킵.
  assert.deepEqual(
    buildRefSnapSecs([
      null as unknown as { recordId?: string; refVideoSec?: number },
      { recordId: 'r01', refVideoSec: 4.2 },
    ]),
    { r01: 4.2 },
  );
});
