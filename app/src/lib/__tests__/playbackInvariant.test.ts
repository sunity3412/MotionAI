// 재생 상태 불변식 판정 순수 로직 검증 (260806-usc — V-1).
//
// 실행: node --test app/src/lib/__tests__/playbackInvariant.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행된다 — 테스트 러너/트랜스파일러
// 등 **신규 npm 의존성 0** (belle: 1,120개 의존성 이유로 테스트 러너 승인 철회).
// 그래서 node:test / node:assert 표준 모듈만 쓰고 `.ts` 확장자 import 를 명시한다.
// tsconfig 의 allowImportingTsExtensions=true 라 tsc(typecheck)도 이 import 를 허용한다.
//
// 검증 축 12개 — R1~R8 우선순위가 코드에서 실제로 그 순서로 걸리는지, 그리고
// "개입하지 않아야 하는 자리"(관찰창 밖·대칭·시작 홀드·scrubbing)에서 개입이
// 0 인지를 양방향으로 잡는다. 개입 0 축이 절반인 이유: 이 판정의 위험은 못 잡는
// 것보다 **정상 주행을 건드리는 것**이다(T-usc-01/T-usc-03).

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  decidePlaybackInvariant,
  RESUME_WATCH_TICKS,
  RESUME_PLAY_RETRIES,
} from '../playbackInvariant.ts';
import type { PlaybackInvariantInput } from '../playbackInvariant.ts';

// 정상 주행(창 밖·대칭·개입 0) 기준 입력. 각 축은 필요한 필드만 덮어쓴다.
function input(over: Partial<PlaybackInvariantInput> = {}): PlaybackInvariantInput {
  return {
    hasLeft: true,
    hasRight: true,
    scrubbing: false,
    voicePaused: false,
    leftPlaying: true,
    rightPlaying: true,
    resumeWatchTicks: null,
    resumeRetriesUsed: 0,
    startHold: false,
    ...over,
  };
}

// ── R3: 음성 정지 중 편측 진행 차단 ────────────────────────────────────────

test('1. 음성 정지 중 right 만 재생 → 도는 쪽만 pause (left 는 건드리지 않음)', () => {
  const d = decidePlaybackInvariant(
    input({ voicePaused: true, leftPlaying: false, rightPlaying: true }),
  );
  assert.equal(d.action, 'enforce-pause');
  assert.equal(d.left, 'leave');
  assert.equal(d.right, 'pause');
  assert.equal(d.consumeRetry, false);
  assert.equal(d.closeWatch, false);
});

test('2. 음성 정지 중 양쪽 재생 → 양쪽 pause', () => {
  const d = decidePlaybackInvariant(
    input({ voicePaused: true, leftPlaying: true, rightPlaying: true }),
  );
  assert.equal(d.action, 'enforce-pause');
  assert.equal(d.left, 'pause');
  assert.equal(d.right, 'pause');
});

test('3. 음성 정지 중 양쪽 정지 → none (불필요한 pause 호출 0)', () => {
  const d = decidePlaybackInvariant(
    input({ voicePaused: true, leftPlaying: false, rightPlaying: false }),
  );
  assert.equal(d.action, 'none');
  assert.equal(d.left, 'leave');
  assert.equal(d.right, 'leave');
});

// ── R2/R1: 사용자 제스처·단일 패널 면제 ────────────────────────────────────

test('4. scrubbing 중이면 음성 정지 + 편측이어도 none (R2 가 R3 를 이긴다)', () => {
  const d = decidePlaybackInvariant(
    input({
      scrubbing: true,
      voicePaused: true,
      leftPlaying: false,
      rightPlaying: true,
    }),
  );
  assert.equal(d.action, 'none');
});

test('5. 한쪽 패널만 있는 화면(hasRight=false) → none (대칭 개념 없음)', () => {
  const d = decidePlaybackInvariant(
    input({ hasRight: false, voicePaused: true, leftPlaying: true, rightPlaying: false }),
  );
  assert.equal(d.action, 'none');
});

// ── R4: 관찰창 밖 무개입 ───────────────────────────────────────────────────

test('6. 관찰창 밖(resumeWatchTicks=null) + 편측 → none (정상 주행 무개입)', () => {
  const d = decidePlaybackInvariant(
    input({ resumeWatchTicks: null, leftPlaying: false, rightPlaying: true }),
  );
  assert.equal(d.action, 'none');
});

test('7. 관찰창 만료(RESUME_WATCH_TICKS 초과) + 편측 → none', () => {
  const d = decidePlaybackInvariant(
    input({
      resumeWatchTicks: RESUME_WATCH_TICKS + 1,
      leftPlaying: false,
      rightPlaying: true,
    }),
  );
  assert.equal(d.action, 'none');
});

// ── R5: 대칭은 정상 ────────────────────────────────────────────────────────

test('8. 관찰창 안 + 대칭(양쪽 재생 / 양쪽 정지) → none (spin-up 오판 방지)', () => {
  const bothPlaying = decidePlaybackInvariant(
    input({ resumeWatchTicks: 0, leftPlaying: true, rightPlaying: true }),
  );
  assert.equal(bothPlaying.action, 'none');
  // play() 직후 양쪽이 아직 spin-up 중인 false/false 를 위반으로 세면
  // 재개 순간마다 converge-pause 로 수렴해 버린다.
  const bothStopped = decidePlaybackInvariant(
    input({ resumeWatchTicks: 0, leftPlaying: false, rightPlaying: false }),
  );
  assert.equal(bothStopped.action, 'none');
});

// ── R7/R8: 재시도 → 수렴 ───────────────────────────────────────────────────

test('9. 관찰창 안 + 편측 + 재시도 여유 → 안 도는 쪽만 play (재시도 소비)', () => {
  const leftStopped = decidePlaybackInvariant(
    input({ resumeWatchTicks: 0, leftPlaying: false, rightPlaying: true }),
  );
  assert.equal(leftStopped.action, 'retry-play');
  assert.equal(leftStopped.left, 'play');
  assert.equal(leftStopped.right, 'leave');
  assert.equal(leftStopped.consumeRetry, true);
  assert.equal(leftStopped.closeWatch, false);
  // 방향은 하드코딩이 아니라 "안 도는 쪽" 선택이어야 한다 (역방향도 동일 규칙).
  const rightStopped = decidePlaybackInvariant(
    input({ resumeWatchTicks: 0, leftPlaying: true, rightPlaying: false }),
  );
  assert.equal(rightStopped.action, 'retry-play');
  assert.equal(rightStopped.left, 'leave');
  assert.equal(rightStopped.right, 'play');
});

test('10. 재시도 소진 + 여전히 편측 → 양쪽 pause 로 수렴 + 관찰창 닫기', () => {
  const d = decidePlaybackInvariant(
    input({
      resumeWatchTicks: 3,
      leftPlaying: false,
      rightPlaying: true,
      resumeRetriesUsed: RESUME_PLAY_RETRIES,
    }),
  );
  assert.equal(d.action, 'converge-pause');
  assert.equal(d.left, 'pause');
  assert.equal(d.right, 'pause');
  assert.equal(d.closeWatch, true);
  assert.equal(d.consumeRetry, false);
});

// ── R6: 시작 홀드 면제는 단방향 ────────────────────────────────────────────

test('11. 시작 홀드(left 재생·right 정지) → none (의도된 편측)', () => {
  const d = decidePlaybackInvariant(
    input({
      resumeWatchTicks: 0,
      startHold: true,
      leftPlaying: true,
      rightPlaying: false,
    }),
  );
  assert.equal(d.action, 'none');
});

test('12. 시작 홀드여도 역방향(left 정지·right 재생)은 면제 아님 → retry-play', () => {
  const d = decidePlaybackInvariant(
    input({
      resumeWatchTicks: 0,
      startHold: true,
      leftPlaying: false,
      rightPlaying: true,
    }),
  );
  assert.equal(d.action, 'retry-play');
  assert.equal(d.left, 'play');
  assert.equal(d.right, 'leave');
});
