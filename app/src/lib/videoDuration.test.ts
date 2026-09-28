// videoDuration 순수 분기 검증 (Phase 38 D-14, 리뷰 R15c).
//
// 실행: node --test app/src/lib/videoDuration.test.ts
// pickerFailure.test.ts 와 같은 어법 — Node 24 type stripping 으로 트랜스파일 없이
// 실행된다. node:test / node:assert 표준 모듈만 쓰고 `.ts` 확장자 import 를 명시한다
// (신규 npm 의존성 0).
//
// 검증 축 3개:
//   1) fail-open — duration 이 없거나 0 이면 판정하지 않는다(null). 값 없음은 "짧다"가
//      아니라 "모른다"다. 이 분기가 뒤집히면 duration 을 안 주는 갤러리 픽이 통째로
//      막힌다(리뷰 R15c: 보장 범위 = 클라이언트 검사뿐, 이 fail-open 은 의도된 수용).
//   2) 경계 — 3초·90초는 통과(경계 포함), 그 바깥만 실패.
//   3) 상수 — analyze.tsx 가 리터럴을 두지 않고 이 이름만 쓰므로 값이 여기서 잠긴다.

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  classifyDurationMs,
  MAX_DURATION_MS,
  MIN_DURATION_MS,
} from './videoDuration.ts';

test('duration 부재(undefined/null)는 판정하지 않는다 — fail-open', () => {
  assert.equal(classifyDurationMs(undefined), null);
  assert.equal(classifyDurationMs(null), null);
});

test('duration 0 은 판정 불가 — fail-open (0 은 "짧다"가 아니라 "값 없음")', () => {
  assert.equal(classifyDurationMs(0), null);
});

test('3초 미만은 tooShort', () => {
  assert.equal(classifyDurationMs(2000), 'tooShort');
});

test('3초 정각은 통과 — 하한 경계 포함', () => {
  assert.equal(classifyDurationMs(3000), null);
});

test('90초 정각은 통과 — 상한 경계 포함', () => {
  assert.equal(classifyDurationMs(90000), null);
});

test('90초 초과는 tooLong', () => {
  assert.equal(classifyDurationMs(91000), 'tooLong');
});

test('상수는 3초·90초 (ms) — analyze.tsx 는 이 이름만 쓴다', () => {
  assert.equal(MIN_DURATION_MS, 3000);
  assert.equal(MAX_DURATION_MS, 90000);
});
