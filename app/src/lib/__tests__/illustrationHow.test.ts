// "어떻게" 오버레이 계산 검증 (quick-260821-gb7 — belle 08-21 승인 4항목 배선).
//
// 실행: node --test app/src/lib/__tests__/illustrationHow.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (illustrationScene.test.ts 선례). node:test / node:assert 표준 모듈 +
// `.ts` 확장자 import 만.
//
// 검증 축 (PLAN behavior 블록만 — 수치 채우기 금지):
//   1) baked 오버레이 — kind 판별 / 화살표 2개(잔상 발 → 같은 쪽 실선 발) /
//      ctrl = 중점 + offset (compose_b.py 기하) / 문장 "20° 정도 더 벌리세요" / deltaDeg
//   2) 절대각형 입력(94→71)도 deltaDeg 23 — record 두 모양(차이형·절대각형) 다 성립
//   3) fail-closed 5축 — 미등록 asset / unit cm / measured 없음 / delta<3 / NaN → null
//      (오버레이만 안 그려지고 그림 자체는 표시 — 잔상이 구워져 있어 그림만으로 읽힘)
//   4) 장면 표 배선 — ref-kip-up × leg → 'ref-kip-up--leg' (belle 08-21 승인 에셋)

import test from 'node:test';
import assert from 'node:assert/strict';

import { buildHowOverlay } from '../illustrationHow.ts';
import type { HowOverlayBaked } from '../illustrationHow.ts';
import { illustrationAssetForPart } from '../illustrationScene.ts';

/** 승인 에셋 실측 비율 (exq stage20-1 = 896x1200, sips 실측 — PLAN 확정값). */
const ASPECT = 1200 / 896;

/**
 * 승인 실물 발 좌표 — fe9 meta.json 896x1200 절대픽셀의 0~1 환산 (PLAN 확정값,
 * 재계산 금지). ghost = 그림에 구워진 잔상 발, solid = 실선(정은지) 발.
 */
const GHOST_L = [0.2377, 0.8692] as const;
const SOLID_L = [0.1228, 0.8458] as const;
const GHOST_R = [0.7199, 0.8625] as const;
const SOLID_R = [0.8281, 0.825] as const;
/** ctrl offset — compose_b.py 의 (좌 -8px, 우 +8px, 공통 +46px) 비율 환산. */
const CTRL_OFF_L = [-0.0089, 0.0383] as const;
const CTRL_OFF_R = [0.0089, 0.0383] as const;

const EPS = 1e-9;

/** kind 판별 후 baked 로 좁힌다 — 아니면 즉시 실패. */
function asBaked(o: ReturnType<typeof buildHowOverlay>): HowOverlayBaked {
  assert.ok(o !== null, '오버레이가 null — baked 여야 한다');
  if (o.kind !== 'baked') {
    throw new Error(`kind=${String((o as { kind?: unknown }).kind)} — baked 가 아니다`);
  }
  return o;
}

// ── 1) baked 오버레이 산출 ────────────────────────────────────────────────

test('1: 차이형 입력(measured 20, target 0) → baked — 화살표 2개, ctrl=중점+offset, 방향 문장', () => {
  const o = asBaked(buildHowOverlay('ref-kip-up--leg', 20, 0, 'deg', ASPECT));
  assert.equal(o.deltaDeg, 20);
  assert.equal(o.directionText, '20° 정도 더 벌리세요');
  assert.equal(o.arrows.length, 2);

  const [left, right] = o.arrows;
  // 시작 = 잔상 발, 끝 = 같은 쪽 실선 발 (belle D-03 — 폴 가운데 출발 금지).
  assert.deepEqual(left.from, GHOST_L);
  assert.deepEqual(left.to, SOLID_L);
  assert.deepEqual(right.from, GHOST_R);
  assert.deepEqual(right.to, SOLID_R);
  // ctrl = from·to 중점 + offset — lib 이 소유한 계산을 독립 재계산으로 대조.
  for (const [arrow, off] of [
    [left, CTRL_OFF_L],
    [right, CTRL_OFF_R],
  ] as const) {
    const mx = (arrow.from[0] + arrow.to[0]) / 2 + off[0];
    const my = (arrow.from[1] + arrow.to[1]) / 2 + off[1];
    assert.ok(Math.abs(arrow.ctrl[0] - mx) < EPS, `ctrl x ${arrow.ctrl[0]} ≠ ${mx}`);
    assert.ok(Math.abs(arrow.ctrl[1] - my) < EPS, `ctrl y ${arrow.ctrl[1]} ≠ ${my}`);
  }
});

// ── 2) record 두 모양 (차이형·절대각형) ───────────────────────────────────

test('2: 절대각형 입력(measured 94, target 71) → deltaDeg 23', () => {
  const o = asBaked(buildHowOverlay('ref-kip-up--leg', 94, 71, 'deg', ASPECT));
  assert.equal(o.deltaDeg, 23);
  assert.equal(o.directionText, '23° 정도 더 벌리세요');
});

// ── 3) fail-closed — 조건 하나라도 안 맞으면 null (그림만 표시) ───────────

test('3: 미등록 asset / unit 불일치 / 값 없음 / delta<3 / non-finite → null', () => {
  // 미등록 asset (앵커 없는 에셋은 오버레이를 그리지 않는다)
  assert.equal(buildHowOverlay('ref-kip-up', 20, 0, 'deg', ASPECT), null);
  assert.equal(buildHowOverlay(null, 20, 0, 'deg', ASPECT), null);
  assert.equal(buildHowOverlay(undefined, 20, 0, 'deg', ASPECT), null);
  // unit 이 deg 가 아님
  assert.equal(buildHowOverlay('ref-kip-up--leg', 20, 0, 'cm', ASPECT), null);
  assert.equal(buildHowOverlay('ref-kip-up--leg', 20, 0, null, ASPECT), null);
  // measured/target 없음
  assert.equal(buildHowOverlay('ref-kip-up--leg', null, 0, 'deg', ASPECT), null);
  assert.equal(buildHowOverlay('ref-kip-up--leg', 20, undefined, 'deg', ASPECT), null);
  // 차이 3° 미만 — 잔상과 실선이 겹쳐 보이지 않는다
  assert.equal(buildHowOverlay('ref-kip-up--leg', 2.9, 0, 'deg', ASPECT), null);
  // non-finite
  assert.equal(buildHowOverlay('ref-kip-up--leg', Number.NaN, 0, 'deg', ASPECT), null);
  assert.equal(
    buildHowOverlay('ref-kip-up--leg', 20, Number.POSITIVE_INFINITY, 'deg', ASPECT),
    null,
  );
});

// ── 4) 장면 표 배선 ──────────────────────────────────────────────────────

test('4: ref-kip-up × leg 장면이 승인 에셋 ref-kip-up--leg 를 가리킨다', () => {
  assert.equal(illustrationAssetForPart('ref-kip-up', 'leg'), 'ref-kip-up--leg');
});
