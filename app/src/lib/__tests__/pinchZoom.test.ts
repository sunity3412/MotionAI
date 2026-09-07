// 손가락 확대(핀치 줌) 순수 기하 검증 (belle 09-07 — "손가락으로 영상을 멈추고 확대할 수 있게").
//
// 실행: node --test app/src/lib/__tests__/pinchZoom.test.ts
// Node 의 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (gaugeGeometry.test.ts / manualOffset.test.ts 선례). node:test / node:assert 표준
// 모듈만 쓰고 `.ts` 확장자 import 를 명시한다(tsconfig allowImportingTsExtensions).
//
// 검증 축:
//   1) 회귀 잠금 — scale=DEFAULT_ZOOM, 팬 0 이면 오늘 VideoCompare.tsx:1941-1944 인라인
//      수식과 픽셀 단위로 동일. belle 이 실기기에서 승인한 프레이밍이라 한 톨도 못 움직인다.
//   2) 배율 클램프 [MIN_ZOOM, MAX_ZOOM]
//   3) 배율 1.0 에서 팬 강제 0 (밀어낼 여백이 없다)
//   4) 고배율 팬 경계 — 확대 박스가 항상 클리핑 박스를 덮는다(가장자리 노출 0)
//   5) applyPinch 초점 보존 — 손가락 아래 픽셀이 그 자리에 머문다
//   6) pinchDistance — 손가락 2개 미만은 0("핀치 아님")

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_ZOOM,
  MIN_ZOOM,
  MAX_ZOOM,
  pinchDistance,
  applyPinch,
  clampZoom,
} from '../pinchZoom.ts';

// ── Test 1: 회귀 잠금 (가장 중요) ─────────────────────────────────────────

test('Test 1 (회귀 잠금): DEFAULT_ZOOM·팬 0 = 오늘 인라인 수식 그대로', () => {
  // 승인된 프레이밍 상수 자체.
  assert.equal(DEFAULT_ZOOM, 1.35, 'DEFAULT_ZOOM 은 오늘의 FULLSCREEN_ZOOM 과 같아야 한다');

  // 박제 수치 — node 로 오늘 수식을 직접 돌려 얻은 값 (테스트가 구현을 그대로 베끼는
  // 동어반복이 되지 않도록 리터럴로 못 박는다).
  //   zoomW = Math.round(boxW * 1.35),  zoomLeft = -Math.round((zoomW - boxW) / 2)
  const frozen = [
    // [boxW, boxH, zoomW, zoomH, zoomLeft, zoomTop]
    [393, 699, 531, 944, -69, -123],
    [375, 667, 506, 900, -66, -117],
    // 310×551 은 "폭을 먼저 반올림하고 그 차의 절반을 다시 반올림" 을 지키지 않으면
    // 두 축 모두 어긋나는 케이스다 (-Math.round(boxW*0.35/2) 로 쓰면 -54/-96 이 나온다).
    [310, 551, 419, 744, -55, -97],
  ] as const;

  for (const [boxW, boxH, zoomW, zoomH, zoomLeft, zoomTop] of frozen) {
    const g = clampZoom({ scale: DEFAULT_ZOOM, tx: 0, ty: 0 }, boxW, boxH);
    assert.equal(g.zoomW, zoomW, `zoomW ${boxW}x${boxH}`);
    assert.equal(g.zoomH, zoomH, `zoomH ${boxW}x${boxH}`);
    assert.equal(g.zoomLeft, zoomLeft, `zoomLeft ${boxW}x${boxH}`);
    assert.equal(g.zoomTop, zoomTop, `zoomTop ${boxW}x${boxH}`);
    // 팬 0 요청은 그대로 0 (DEFAULT_ZOOM 에서는 경계 안쪽이라 잘리지 않는다).
    assert.equal(g.tx, 0, 'tx');
    assert.equal(g.ty, 0, 'ty');
    assert.equal(g.scale, DEFAULT_ZOOM, 'scale');
  }
});

test('Test 1b (회귀 잠금 스윕): 폭 300~450 전 구간에서 오늘 수식과 일치', () => {
  for (let boxW = 300; boxW <= 450; boxW += 1) {
    const boxH = Math.round((boxW * 16) / 9); // 세로 9:16 슬롯
    const g = clampZoom({ scale: DEFAULT_ZOOM, tx: 0, ty: 0 }, boxW, boxH);
    // 오늘 renderFullscreenSlot 인라인 수식 (VideoCompare.tsx:1941-1944).
    const zoomW = Math.round(boxW * 1.35);
    const zoomH = Math.round(boxH * 1.35);
    assert.equal(g.zoomW, zoomW, `zoomW boxW=${boxW}`);
    assert.equal(g.zoomH, zoomH, `zoomH boxW=${boxW}`);
    assert.equal(g.zoomLeft, -Math.round((zoomW - boxW) / 2), `zoomLeft boxW=${boxW}`);
    assert.equal(g.zoomTop, -Math.round((zoomH - boxH) / 2), `zoomTop boxW=${boxW}`);
  }
});

// ── Test 2: 배율 클램프 ───────────────────────────────────────────────────

test('Test 2 (배율 클램프): [MIN_ZOOM, MAX_ZOOM] 밖은 경계값으로', () => {
  assert.equal(MIN_ZOOM, 1.0);
  assert.equal(MAX_ZOOM, 4.0);

  const boxW = 393;
  const boxH = 699;

  const under = clampZoom({ scale: 0.4, tx: 0, ty: 0 }, boxW, boxH);
  assert.equal(under.scale, MIN_ZOOM, '축소 요청은 1.0 에서 멈춘다');
  assert.equal(under.zoomW, boxW, '1.0 이면 확대 박스 = 클리핑 박스');
  assert.equal(under.zoomH, boxH);

  const over = clampZoom({ scale: 12, tx: 0, ty: 0 }, boxW, boxH);
  assert.equal(over.scale, MAX_ZOOM, '확대 요청은 4.0 에서 멈춘다');
  assert.equal(over.zoomW, Math.round(boxW * MAX_ZOOM));

  // 비유한 배율은 승인된 프레이밍으로 되돌린다 (NaN 이 레이아웃에 새지 않는다).
  const broken = clampZoom({ scale: Number.NaN, tx: 0, ty: 0 }, boxW, boxH);
  assert.equal(broken.scale, DEFAULT_ZOOM);
  assert.ok(Number.isFinite(broken.zoomLeft) && Number.isFinite(broken.zoomTop));
});

// ── Test 3: 배율 1.0 에서 팬 강제 0 ───────────────────────────────────────

test('Test 3 (팬 경계 @1.0): 밀어낼 여백이 없으므로 팬은 0 으로 강제된다', () => {
  const boxW = 393;
  const boxH = 699;
  for (const req of [
    { tx: 500, ty: 500 },
    { tx: -500, ty: -500 },
    { tx: 1, ty: -1 },
  ]) {
    const g = clampZoom({ scale: MIN_ZOOM, ...req }, boxW, boxH);
    assert.equal(g.tx, 0, `tx 강제 0 (요청 ${req.tx})`);
    assert.equal(g.ty, 0, `ty 강제 0 (요청 ${req.ty})`);
    assert.equal(g.zoomLeft, 0, 'zoomLeft 0');
    assert.equal(g.zoomTop, 0, 'zoomTop 0');
  }
});

// ── Test 4: 고배율 팬 경계 ────────────────────────────────────────────────

test('Test 4 (팬 경계 @고배율): 확대 박스가 항상 클리핑 박스를 덮는다', () => {
  const boxW = 393;
  const boxH = 699;

  for (const scale of [1.35, 2, 3, MAX_ZOOM]) {
    // 오른쪽 끝까지 밀어도 왼쪽 가장자리가 드러나지 않는다 (zoomLeft <= 0).
    const right = clampZoom({ scale, tx: 99999, ty: 99999 }, boxW, boxH);
    assert.equal(right.zoomLeft, 0, `scale=${scale}: 왼쪽 가장자리 밀착(0)`);
    assert.equal(right.zoomTop, 0, `scale=${scale}: 위쪽 가장자리 밀착(0)`);

    // 반대쪽 끝까지 밀어도 오른쪽/아래 가장자리가 드러나지 않는다.
    const left = clampZoom({ scale, tx: -99999, ty: -99999 }, boxW, boxH);
    assert.equal(left.zoomLeft + left.zoomW, boxW, `scale=${scale}: 오른쪽 가장자리 밀착`);
    assert.equal(left.zoomTop + left.zoomH, boxH, `scale=${scale}: 아래쪽 가장자리 밀착`);

    // 중간값도 항상 덮는다.
    for (const tx of [-140, -37, 0, 12, 200]) {
      const g = clampZoom({ scale, tx, ty: tx }, boxW, boxH);
      assert.ok(g.zoomLeft <= 0, `scale=${scale} tx=${tx}: zoomLeft ${g.zoomLeft} > 0`);
      assert.ok(
        g.zoomLeft + g.zoomW >= boxW,
        `scale=${scale} tx=${tx}: 오른쪽 노출 ${g.zoomLeft + g.zoomW} < ${boxW}`,
      );
      assert.ok(g.zoomTop <= 0, `scale=${scale} ty=${tx}: zoomTop ${g.zoomTop} > 0`);
      assert.ok(g.zoomTop + g.zoomH >= boxH, `scale=${scale} ty=${tx}: 아래 노출`);
      // zoomLeft 는 항상 중앙정렬 오프셋 + 클램프된 tx (호출측이 되먹일 수 있어야 한다).
      assert.ok(Number.isInteger(g.tx) && Number.isInteger(g.zoomLeft), '레이아웃 수치는 정수');
    }
  }
});

// ── Test 5: applyPinch 초점 보존 ──────────────────────────────────────────

const BOX_W = 393;
const BOX_H = 699;

/**
 * 모듈 문서에 명시된 연속 좌표 모델을 테스트에서 독립적으로 다시 세운다.
 * 확대 박스 내 정규화 위치 u 의 화면 좌표.
 */
function screenX(scale: number, tx: number, u: number): number {
  return (BOX_W * (1 - scale)) / 2 + tx + u * BOX_W * scale;
}
function screenY(scale: number, ty: number, v: number): number {
  return (BOX_H * (1 - scale)) / 2 + ty + v * BOX_H * scale;
}

test('Test 5 (초점 보존): 손가락 아래 픽셀이 배율 변경 후에도 그 자리에 머문다', () => {
  const cases = [
    { start: { scale: DEFAULT_ZOOM, tx: 0, ty: 0 }, ratio: 2, focalX: 120, focalY: 300 },
    { start: { scale: DEFAULT_ZOOM, tx: 0, ty: 0 }, ratio: 0.5, focalX: 300, focalY: 90 },
    { start: { scale: 2.4, tx: -40, ty: 55 }, ratio: 1.3, focalX: 196, focalY: 350 },
    // 상한에 붙는 경우 — 실제 적용된 배율(4.0) 기준으로 초점이 보존돼야 한다.
    { start: { scale: 3.5, tx: 10, ty: -20 }, ratio: 3, focalX: 60, focalY: 620 },
  ];

  for (const c of cases) {
    const startDist = 100;
    const curDist = startDist * c.ratio;
    // 초점 아래의 정규화 위치 = 배율 전후 불변량.
    const left0 = (BOX_W * (1 - c.start.scale)) / 2 + c.start.tx;
    const top0 = (BOX_H * (1 - c.start.scale)) / 2 + c.start.ty;
    const u0 = (c.focalX - left0) / (BOX_W * c.start.scale);
    const v0 = (c.focalY - top0) / (BOX_H * c.start.scale);

    const next = applyPinch({
      startState: c.start,
      startDist,
      curDist,
      focalX: c.focalX,
      focalY: c.focalY,
      boxW: BOX_W,
      boxH: BOX_H,
    });

    // 배율은 비율만큼, 단 [MIN, MAX] 안에서.
    const expectedScale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, c.start.scale * c.ratio));
    assert.ok(
      Math.abs(next.scale - expectedScale) < 1e-9,
      `scale ${next.scale} != ${expectedScale}`,
    );

    // 같은 콘텐츠 점이 같은 화면 좌표에 남는다.
    assert.ok(
      Math.abs(screenX(next.scale, next.tx, u0) - c.focalX) < 1e-9,
      `focalX 이동: ${screenX(next.scale, next.tx, u0)} != ${c.focalX}`,
    );
    assert.ok(
      Math.abs(screenY(next.scale, next.ty, v0) - c.focalY) < 1e-9,
      `focalY 이동: ${screenY(next.scale, next.ty, v0)} != ${c.focalY}`,
    );

    // 실제 렌더 수치(반올림·클램프 후)로도 초점이 1px 안에 머문다.
    // 팬 경계에 붙은 경우는 제외 — 가장자리 노출 금지가 초점 보존보다 우선한다.
    const g = clampZoom(next, BOX_W, BOX_H);
    const panUnclamped = g.tx === Math.round(next.tx) && g.ty === Math.round(next.ty);
    if (panUnclamped) {
      const renderedX = g.zoomLeft + u0 * g.zoomW;
      const renderedY = g.zoomTop + v0 * g.zoomH;
      assert.ok(Math.abs(renderedX - c.focalX) <= 1.5, `렌더 초점 X 흔들림 ${renderedX}`);
      assert.ok(Math.abs(renderedY - c.focalY) <= 1.5, `렌더 초점 Y 흔들림 ${renderedY}`);
    }
  }
});

test('Test 5b (핀치 아님): startDist 0/음수·박스 0 이면 상태 불변', () => {
  const start = { scale: 2, tx: -30, ty: 12 };
  const args = { startState: start, focalX: 100, focalY: 200, boxW: BOX_W, boxH: BOX_H };

  assert.deepEqual(applyPinch({ ...args, startDist: 0, curDist: 120 }), start);
  assert.deepEqual(applyPinch({ ...args, startDist: -5, curDist: 120 }), start);
  assert.deepEqual(applyPinch({ ...args, startDist: 100, curDist: 0 }), start);
  assert.deepEqual(
    applyPinch({ ...args, boxW: 0, startDist: 100, curDist: 200 }),
    start,
    '박스 폭 0 (레이아웃 전) 이면 배율을 건드리지 않는다',
  );
  assert.deepEqual(
    applyPinch({ ...args, focalX: Number.NaN, startDist: 100, curDist: 200 }),
    start,
    'NaN 초점은 무시',
  );
});

// ── Test 6: pinchDistance ─────────────────────────────────────────────────

test('Test 6 (핀치 거리): 손가락 2개 미만은 0, 2개면 두 점 사이 거리', () => {
  assert.equal(pinchDistance([]), 0, '손가락 0');
  assert.equal(pinchDistance([{ pageX: 10, pageY: 10 }]), 0, '손가락 1 = 핀치 아님(드래그)');
  assert.equal(
    pinchDistance([
      { pageX: 0, pageY: 0 },
      { pageX: 3, pageY: 4 },
    ]),
    5,
    '3-4-5 삼각형',
  );
  // 손가락 3개 이상이면 앞의 두 개만 (핀치 도중 세 번째 손가락이 닿아도 배율이 튀지 않는다).
  assert.equal(
    pinchDistance([
      { pageX: 0, pageY: 0 },
      { pageX: 0, pageY: 10 },
      { pageX: 999, pageY: 999 },
    ]),
    10,
    '앞의 두 손가락만 사용',
  );
  assert.equal(
    pinchDistance([
      { pageX: Number.NaN, pageY: 0 },
      { pageX: 3, pageY: 4 },
    ]),
    0,
    'NaN 좌표는 0(핀치 아님)',
  );
});
