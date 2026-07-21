// manualOffset 순수 로직 검증 (32-02 D-16).
//
// 실행: node --test app/src/lib/__tests__/manualOffset.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행된다 — 테스트 러너/트랜스파일러
// 등 **신규 npm 의존성 0** (belle: 1,120개 의존성 이유로 테스트 러너 승인 철회).
// 그래서 node:test / node:assert 표준 모듈만 쓰고 `.ts` 확장자 import 를 명시한다.
// tsconfig 의 allowImportingTsExtensions=true 라 tsc(typecheck)도 이 import 를 허용한다.
//
// 검증 축 2개 (D-16 수동 오프셋 합성 + legacy median 폴백):
//   1) composeRefTarget — raw+offset 합성 후 [0, dR] 클램프, dR 0/음수/NaN 안전(크래시 0).
//   2) legacyOffsetFromCompareFrames — 유효 쌍의 오프셋 median(이상치 견고), 유효 쌍 0 → null,
//      fps 는 인자로만(9/18 하드코딩 금지).

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  composeRefTarget,
  legacyOffsetFromCompareFrames,
} from '../manualOffset.ts';

// ── composeRefTarget ──────────────────────────────────────────────────────

test('composeRefTarget: raw+offset 합성 후 [0, dR] 클램프 (경계 초과 시 경계값)', () => {
  // 오프셋 0 = raw 그대로 (dR 범위 내)
  assert.equal(composeRefTarget(5, 0, 10), 5);
  // 양의 오프셋 합성
  assert.equal(composeRefTarget(5, 3, 10), 8);
  // 음의 오프셋 합성
  assert.equal(composeRefTarget(5, -2, 10), 3);
  // 상한 초과 → dR 로 클램프
  assert.equal(composeRefTarget(5, 10, 10), 10);
  // 하한 미만 → 0 으로 클램프
  assert.equal(composeRefTarget(5, -10, 10), 0);
});

test('composeRefTarget: durationRef 0/음수/NaN 안전 (max(0, composed) 폴백, 크래시 0)', () => {
  // dR=0 → 클램프 상한 없음, max(0, composed)
  assert.equal(composeRefTarget(5, 0, 0), 5);
  assert.equal(composeRefTarget(5, 2, 0), 7);
  // dR 음수
  assert.equal(composeRefTarget(5, 0, -1), 5);
  // dR NaN
  assert.equal(composeRefTarget(5, 0, NaN), 5);
  assert.equal(composeRefTarget(5, 2, NaN), 7);
  // composed 가 음수여도 max(0, ·) 로 0 (dR 무효 경로)
  assert.equal(composeRefTarget(-5, 0, NaN), 0);
  // raw/offset NaN 입력도 NaN 을 방출하지 않는다 (0 폴백)
  assert.equal(composeRefTarget(NaN, 0, 10), 0);
  assert.equal(composeRefTarget(5, NaN, 10), 5);
});

// ── legacyOffsetFromCompareFrames ─────────────────────────────────────────

test('legacyOffsetFromCompareFrames: 유효 쌍 오프셋 median (refFrameIdx/refFps − userFrameIdx/userFps)', () => {
  // 단일 쌍: 36/18 − 9/9 = 2 − 1 = 1
  assert.equal(
    legacyOffsetFromCompareFrames([{ userFrameIdx: 9, refFrameIdx: 36 }], 9, 18),
    1,
  );
  // 홀수 개(3) → 가운데 값
  assert.equal(
    legacyOffsetFromCompareFrames(
      [
        { userFrameIdx: 9, refFrameIdx: 36 }, // 1
        { userFrameIdx: 18, refFrameIdx: 54 }, // 3−2 = 1
        { userFrameIdx: 9, refFrameIdx: 54, refMatched: true }, // 3−1 = 2
      ],
      9,
      18,
    ),
    1,
  );
  // 짝수 개(2) → 두 가운데 평균 ((1+3)/2 = 2)
  assert.equal(
    legacyOffsetFromCompareFrames(
      [
        { userFrameIdx: 9, refFrameIdx: 36 }, // 1
        { userFrameIdx: 9, refFrameIdx: 72 }, // 4−1 = 3
      ],
      9,
      18,
    ),
    2,
  );
});

test('legacyOffsetFromCompareFrames: fps 는 인자로만 사용 (9/18 하드코딩 금지)', () => {
  // 같은 인덱스라도 fps 인자에 따라 결과가 달라져야 함 (하드코딩이면 불변)
  const pair = [{ userFrameIdx: 10, refFrameIdx: 20 }];
  // 20/10 − 10/10 = 2 − 1 = 1
  assert.equal(legacyOffsetFromCompareFrames(pair, 10, 10), 1);
  // 20/5 − 10/5 = 4 − 2 = 2  (fps 를 인자에서 읽는다는 증거)
  assert.equal(legacyOffsetFromCompareFrames(pair, 5, 5), 2);
  // 유효하지 않은 fps(0/음수/NaN) → null (나눗셈 불가)
  assert.equal(legacyOffsetFromCompareFrames(pair, 0, 18), null);
  assert.equal(legacyOffsetFromCompareFrames(pair, 9, -1), null);
  assert.equal(legacyOffsetFromCompareFrames(pair, NaN, 18), null);
});

test('legacyOffsetFromCompareFrames: 유효 쌍 0개 → null (폴백 불가 — 슬라이더만)', () => {
  // 전부 refMatched=false
  assert.equal(
    legacyOffsetFromCompareFrames(
      [
        { userFrameIdx: 1, refFrameIdx: 2, refMatched: false },
        { userFrameIdx: 3, refFrameIdx: 4, refMatched: false },
      ],
      9,
      18,
    ),
    null,
  );
  // 비정수 인덱스
  assert.equal(
    legacyOffsetFromCompareFrames([{ userFrameIdx: 1.5, refFrameIdx: 2 }], 9, 18),
    null,
  );
  // 음수 인덱스
  assert.equal(
    legacyOffsetFromCompareFrames([{ userFrameIdx: -1, refFrameIdx: 2 }], 9, 18),
    null,
  );
  // 인덱스 부재
  assert.equal(
    legacyOffsetFromCompareFrames([{ refMatched: true }], 9, 18),
    null,
  );
  // 빈 배열
  assert.equal(legacyOffsetFromCompareFrames([], 9, 18), null);
  // null 입력
  assert.equal(legacyOffsetFromCompareFrames(null, 9, 18), null);
});

test('legacyOffsetFromCompareFrames: 단일 이상치에 좌우되지 않는다 (median 견고성 — 리뷰 반영)', () => {
  // 오프셋 [1, 1, 11] — 마지막 쌍이 극단값(나머지 대비 10초 이탈).
  // median([1,1,11]) = 1 → 다수 쌍의 오프셋 반환 (mean 이면 4.33 로 오염).
  const result = legacyOffsetFromCompareFrames(
    [
      { userFrameIdx: 9, refFrameIdx: 36 }, // 2−1 = 1
      { userFrameIdx: 18, refFrameIdx: 54 }, // 3−2 = 1
      { userFrameIdx: 9, refFrameIdx: 216, refMatched: true }, // 12−1 = 11 (이상치)
    ],
    9,
    18,
  );
  assert.equal(result, 1);
});
