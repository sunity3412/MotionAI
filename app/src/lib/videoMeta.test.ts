// videoMeta 검증 (Phase 38-10 Task 1).
//
// 실행: node --test app/src/lib/videoMeta.test.ts
// node 에는 `document` 가 없다 — 그 경로(네이티브 · 서버 렌더와 같은 조건)에서
// 길이를 지어내지 않고 null(fail-open)을 돌려주는지만 잠근다. 브라우저 경로
// (`<video preload="metadata">`)는 38-10 Task 4 / 38-13 시뮬레이터 측정 몫.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readVideoDurationSec } from './videoMeta.ts';

test('document 가 없으면 길이를 지어내지 않고 null — fail-open', async () => {
  assert.equal(typeof (globalThis as { document?: unknown }).document, 'undefined');
  assert.equal(await readVideoDurationSec('blob:whatever'), null);
  assert.equal(await readVideoDurationSec(new Blob([new Uint8Array(4)])), null);
});
