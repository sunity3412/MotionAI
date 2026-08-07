// 재생 상태 불변식 판정 순수 로직 검증 (260806-usc — V-1 / quick-260807-fpw —
// belle 08-07 #2 백오프 개정).
//
// 실행: node --test app/src/lib/__tests__/playbackInvariant.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행된다 — 테스트 러너/트랜스파일러
// 등 **신규 npm 의존성 0** (belle: 1,120개 의존성 이유로 테스트 러너 승인 철회).
// 그래서 node:test / node:assert 표준 모듈만 쓰고 `.ts` 확장자 import 를 명시한다.
// tsconfig 의 allowImportingTsExtensions=true 라 tsc(typecheck)도 이 import 를 허용한다.
//
// 검증 축 — 보존 축(개입 0 계열: R1 단일 패널 / R2 scrubbing / R3 voicePaused /
// R4 창 밖 / 양쪽 재생 / R6 startHold)은 그대로 두고, 재시도 페이싱 축을 belle
// 08-07 #2 백오프 스케줄(RESUME_RETRY_AT_TICKS = 0.5/1/2/3초 간격) 의미로
// 재작성했다. 신설 핵심 경로: **양쪽 정지도 재시도 대상** (종전 R5 는 대칭이면
// 전부 무개입이라 양쪽 play() 실효 실패가 사각 — belle 랜덤 스톨). 개입 0 축이
// 여전히 다수인 이유: 이 판정의 위험은 못 잡는 것보다 **정상 주행을 건드리는
// 것**이다(T-usc-01/T-usc-03).

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  decidePlaybackInvariant,
  RESUME_CONVERGE_GRACE_TICKS,
  RESUME_RETRY_AT_TICKS,
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

// ── R5': 양쪽 재생 = 회복. 양쪽 정지는 스케줄 대기 (belle 08-07 #2 개정) ────

test('8. 관찰창 안 + 양쪽 재생 → none / 양쪽 정지(스케줄 전) → none (스케줄 대기)', () => {
  const bothPlaying = decidePlaybackInvariant(
    input({ resumeWatchTicks: 0, leftPlaying: true, rightPlaying: true }),
  );
  assert.equal(bothPlaying.action, 'none');
  // 개정 사유 (belle 08-07 #2): 종전에는 "양쪽 정지 = 무조건 정상"이었다. 이제
  // 양쪽 정지는 재시도 **대상**이되, 첫 재시도 시각(RESUME_RETRY_AT_TICKS[0])
  // 전에는 개입 0 — spin-up 중 false/false 오판 방지를 스케줄 지연이 대신한다.
  const bothStopped = decidePlaybackInvariant(
    input({ resumeWatchTicks: 0, leftPlaying: false, rightPlaying: false }),
  );
  assert.equal(bothStopped.action, 'none');
});

// ── R7'/R8': 백오프 스케줄 재시도 → 수렴 (belle 08-07 #2) ───────────────────

test('9. 편측 + 재시도 여유 → 스케줄 시각에 안 도는 쪽만 play (재시도 소비)', () => {
  // 개정 사유 (belle 08-07 #2): 종전 매 tick 재시도 → 스케줄 시각에만 재시도.
  const at = RESUME_RETRY_AT_TICKS[0];
  const leftStopped = decidePlaybackInvariant(
    input({ resumeWatchTicks: at, leftPlaying: false, rightPlaying: true }),
  );
  assert.equal(leftStopped.action, 'retry-play');
  assert.equal(leftStopped.left, 'play');
  assert.equal(leftStopped.right, 'leave');
  assert.equal(leftStopped.consumeRetry, true);
  assert.equal(leftStopped.closeWatch, false);
  // 방향은 하드코딩이 아니라 "안 도는 쪽" 선택이어야 한다 (역방향도 동일 규칙).
  const rightStopped = decidePlaybackInvariant(
    input({ resumeWatchTicks: at, leftPlaying: true, rightPlaying: false }),
  );
  assert.equal(rightStopped.action, 'retry-play');
  assert.equal(rightStopped.left, 'leave');
  assert.equal(rightStopped.right, 'play');
});

test('10. 재시도 소진 + RESUME_WATCH_TICKS 도달 → converge-pause(도는 쪽만) + 관찰창 닫기', () => {
  // 개정 사유 (belle 08-07 #2): 종전 "소진 즉시 양쪽 pause" → 마지막 재시도 후
  // 유예(RESUME_CONVERGE_GRACE_TICKS)를 기다렸다 관찰창 끝에서 수렴. pause 는
  // 재생 중인 쪽에만 보낸다 (이미 멈춘 쪽에 불필요한 호출 0).
  const d = decidePlaybackInvariant(
    input({
      resumeWatchTicks: RESUME_WATCH_TICKS,
      leftPlaying: false,
      rightPlaying: true,
      resumeRetriesUsed: RESUME_PLAY_RETRIES,
    }),
  );
  assert.equal(d.action, 'converge-pause');
  assert.equal(d.left, 'leave');
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

test('12. 시작 홀드여도 역방향(left 정지·right 재생)은 면제 아님 → 스케줄 시각에 retry-play', () => {
  // 개정 사유 (belle 08-07 #2): 재시도 시각이 스케줄로 이동 (규칙 자체는 보존).
  const d = decidePlaybackInvariant(
    input({
      resumeWatchTicks: RESUME_RETRY_AT_TICKS[0],
      startHold: true,
      leftPlaying: false,
      rightPlaying: true,
    }),
  );
  assert.equal(d.action, 'retry-play');
  assert.equal(d.left, 'play');
  assert.equal(d.right, 'leave');
});

// ── 신설 (belle 08-07 #2): 양쪽 정지 재시도 + 스케줄 페이싱 + 유예 수렴 ──────

test('13. 양쪽 정지 + 스케줄 시각 → 양쪽 play retry (belle 랜덤 스톨 회복 신설 경로)', () => {
  const first = decidePlaybackInvariant(
    input({
      resumeWatchTicks: RESUME_RETRY_AT_TICKS[0],
      leftPlaying: false,
      rightPlaying: false,
    }),
  );
  assert.equal(first.action, 'retry-play');
  assert.equal(first.left, 'play');
  assert.equal(first.right, 'play');
  assert.equal(first.consumeRetry, true);
  // 2번째 재시도 시각(재시도 1 소비 후)에도 같은 규칙.
  const second = decidePlaybackInvariant(
    input({
      resumeWatchTicks: RESUME_RETRY_AT_TICKS[1],
      leftPlaying: false,
      rightPlaying: false,
      resumeRetriesUsed: 1,
    }),
  );
  assert.equal(second.action, 'retry-play');
  assert.equal(second.left, 'play');
  assert.equal(second.right, 'play');
});

test('14. 스케줄 시각 전: 편측 → enforce-pause(도는 쪽) / 양쪽 정지 → none', () => {
  const before = RESUME_RETRY_AT_TICKS[0] - 1;
  // 편측 — 재시도 대기 중에도 도는 쪽을 멈춰 드리프트 차단 (불변식 정신).
  const oneSided = decidePlaybackInvariant(
    input({ resumeWatchTicks: before, leftPlaying: false, rightPlaying: true }),
  );
  assert.equal(oneSided.action, 'enforce-pause');
  assert.equal(oneSided.left, 'leave');
  assert.equal(oneSided.right, 'pause');
  assert.equal(oneSided.consumeRetry, false);
  // 양쪽 정지 — 재시도 시각까지 대기 (개입 0).
  const bothStopped = decidePlaybackInvariant(
    input({ resumeWatchTicks: before, leftPlaying: false, rightPlaying: false }),
  );
  assert.equal(bothStopped.action, 'none');
});

test('15. 마지막 재시도 후 유예 중 none → RESUME_WATCH_TICKS 도달 시 converge-pause', () => {
  // 유예 중 (양쪽 정지) — 마지막 play() 의 실효 대기, 개입 0.
  const grace = decidePlaybackInvariant(
    input({
      resumeWatchTicks: RESUME_WATCH_TICKS - 1,
      leftPlaying: false,
      rightPlaying: false,
      resumeRetriesUsed: RESUME_PLAY_RETRIES,
    }),
  );
  assert.equal(grace.action, 'none');
  // 관찰창 끝 (양쪽 정지) — 호출 0 의 대칭 정지 종결 + 관찰창 닫기. 호출부는 이
  // 액션에서 '일시정지됨 — 탭하여 계속' 배지를 세운다 (정직 표면화).
  const final = decidePlaybackInvariant(
    input({
      resumeWatchTicks: RESUME_WATCH_TICKS,
      leftPlaying: false,
      rightPlaying: false,
      resumeRetriesUsed: RESUME_PLAY_RETRIES,
    }),
  );
  assert.equal(final.action, 'converge-pause');
  assert.equal(final.left, 'leave');
  assert.equal(final.right, 'leave');
  assert.equal(final.closeWatch, true);
  // 유예 중 편측이면 도는 쪽만 enforce-pause (드리프트 차단, 수렴은 창 끝에서).
  const graceOneSided = decidePlaybackInvariant(
    input({
      resumeWatchTicks: RESUME_WATCH_TICKS - 1,
      leftPlaying: true,
      rightPlaying: false,
      resumeRetriesUsed: RESUME_PLAY_RETRIES,
    }),
  );
  assert.equal(graceOneSided.action, 'enforce-pause');
  assert.equal(graceOneSided.left, 'pause');
  assert.equal(graceOneSided.right, 'leave');
});

test('16. 양쪽 정지 재시도가 startHold 중 right 에 play 를 쏘지 않는다 (R6 의도 보존)', () => {
  const d = decidePlaybackInvariant(
    input({
      resumeWatchTicks: RESUME_RETRY_AT_TICKS[0],
      leftPlaying: false,
      rightPlaying: false,
      startHold: true,
    }),
  );
  assert.equal(d.action, 'retry-play');
  assert.equal(d.left, 'play');
  assert.equal(d.right, 'leave');
});

test('17. 스케줄 sanity: 오름차순 + 개수 = 재시도 한도 + 마지막 + 유예 = 관찰창', () => {
  for (let i = 1; i < RESUME_RETRY_AT_TICKS.length; i += 1) {
    assert.ok(RESUME_RETRY_AT_TICKS[i] > RESUME_RETRY_AT_TICKS[i - 1]);
  }
  assert.equal(RESUME_RETRY_AT_TICKS.length, RESUME_PLAY_RETRIES);
  assert.equal(
    RESUME_RETRY_AT_TICKS[RESUME_RETRY_AT_TICKS.length - 1] +
      RESUME_CONVERGE_GRACE_TICKS,
    RESUME_WATCH_TICKS,
  );
});
