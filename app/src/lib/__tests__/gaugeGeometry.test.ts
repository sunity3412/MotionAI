// gaugeGeometry 순수 함수 검증 (32-10 Task 1 — D-10/D-09 + 리뷰 HIGH 게이지 의미 정의).
//
// 실행: node --test app/src/lib/__tests__/gaugeGeometry.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (summarySource.test.ts / cueTrack.test.ts 선례). node:test / node:assert 표준
// 모듈만 쓰고 `.ts` 확장자 import 를 명시한다.
//
// 검증 축 (리뷰 HIGH — 자의적 시각 비율 금지): 게이지 스케일 도메인이
// [min(current,target)−tolerance, max(current,target)+tolerance] 로 고정되고(Test 1),
// 거리 0·규칙상수 부재는 정직하게 처리되며(Test 2/3), 방향(늘리기/줄이기)에 무관하게
// 대칭적으로 유효(Test 4)함을 테스트로 못 박는다. tolerance 는 백엔드가 규칙 상수에서
// 방출한 record.tolerance 만 — 없으면 null(게이지 미표시)로 D-09 자의 수치를 시각
// 비율로도 재생산하지 않는다.

import test from 'node:test';
import assert from 'node:assert/strict';
import { computeGaugeGeometry } from '../gaugeGeometry.ts';

// 부동소수 근사 비교 (도메인 비율은 대개 무한소수 — 43/63 등).
function approx(a: number, b: number, eps = 1e-9): boolean {
  return Math.abs(a - b) < eps;
}

test('Test 1 (스케일 정의): 도메인 = [min−tol, max+tol], 각 비율이 선형 위치와 일치', () => {
  // current/target/tol = 94/71/20 → 도메인 [51, 114], span 63.
  const geo = computeGaugeGeometry(94, 71, 20);
  assert.ok(geo, 'geometry 가 있어야 함');
  if (!geo) return;
  // ratio = (94−51)/63, targetRatio = (71−51)/63.
  assert.ok(approx(geo.ratio, 43 / 63), `ratio=${geo.ratio}`);
  assert.ok(approx(geo.targetRatio, 20 / 63), `targetRatio=${geo.targetRatio}`);
  // 허용 오차 밴드 = [target−tol, target+tol] = [51, 91] → 비율 [0, 40/63].
  assert.ok(approx(geo.tolBandStart, 0), `tolBandStart=${geo.tolBandStart}`);
  assert.ok(approx(geo.tolBandEnd, 40 / 63), `tolBandEnd=${geo.tolBandEnd}`);
  // 모든 비율은 [0,1] 도메인 내부 선형 위치.
  for (const r of [geo.ratio, geo.targetRatio, geo.tolBandStart, geo.tolBandEnd]) {
    assert.ok(r >= 0 && r <= 1, `비율이 [0,1] 밖: ${r}`);
  }
});

test('Test 2 (경계): current==target → ratio==targetRatio(거리 0); tol 0/음수/NaN → null', () => {
  // 거리 0 — 도메인 [51, 91], 현재와 목표가 같은 위치(0.5).
  const same = computeGaugeGeometry(71, 71, 20);
  assert.ok(same, 'tolerance 유효 시 거리 0 도 게이지 가능');
  if (same) {
    assert.ok(approx(same.ratio, same.targetRatio), 'ratio==targetRatio (거리 0)');
    assert.ok(approx(same.ratio, 0.5), `중앙이어야: ${same.ratio}`);
  }
  // tolerance 0/음수/NaN → 게이지 불가 (규칙 상수 없음 = 자의 스케일 금지, D-09).
  assert.equal(computeGaugeGeometry(94, 71, 0), null, 'tol 0 → null');
  assert.equal(computeGaugeGeometry(94, 71, -5), null, 'tol 음수 → null');
  assert.equal(computeGaugeGeometry(94, 71, Number.NaN), null, 'tol NaN → null');
});

test('Test 3 (불가 케이스): current/target 비유한 → null (호출측이 게이지 생략)', () => {
  assert.equal(computeGaugeGeometry(Number.NaN, 71, 20), null, 'current NaN → null');
  assert.equal(computeGaugeGeometry(94, Number.NaN, 20), null, 'target NaN → null');
  assert.equal(computeGaugeGeometry(Number.POSITIVE_INFINITY, 71, 20), null, 'current Inf → null');
  assert.equal(computeGaugeGeometry(94, Number.NEGATIVE_INFINITY, 20), null, 'target -Inf → null');
});

test('Test 4 (방향 무가정): 늘려야/줄여야 양쪽에서 비율 대칭 유효 (방향은 표기만)', () => {
  // 줄여야: current 94 > target 71 (decrease). 늘려야: current 71 < target 94 (increase).
  const decrease = computeGaugeGeometry(94, 71, 20);
  const increase = computeGaugeGeometry(71, 94, 20);
  assert.ok(decrease && increase, '양방향 모두 유효');
  if (!decrease || !increase) return;
  // 같은 도메인 [51,114] — current/target 를 뒤집으면 ratio/targetRatio 가 정확히 교환.
  assert.ok(approx(decrease.ratio, increase.targetRatio), 'decrease.ratio == increase.targetRatio');
  assert.ok(approx(decrease.targetRatio, increase.ratio), 'decrease.targetRatio == increase.ratio');
  for (const geo of [decrease, increase]) {
    for (const r of [geo.ratio, geo.targetRatio, geo.tolBandStart, geo.tolBandEnd]) {
      assert.ok(Number.isFinite(r) && r >= 0 && r <= 1, `비율이 유효 [0,1] 밖: ${r}`);
    }
  }
});
