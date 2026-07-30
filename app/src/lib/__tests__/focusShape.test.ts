// 음성 큐 강조 형태(선/원) 분기 검증 (quick-260730-szk Task 1 — 33-G S19).
//
// 실행: node --test app/src/lib/__tests__/focusShape.test.ts
// Node 24 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (deductionSheet.test.ts / resultSections.test.ts 선례).
//
// 왜 이 테스트가 존재하나: 승인 목업 ④ 컷 2 는 **한 컷 안에서** 오른다리는 모양 선,
// 왼다리는 부위 원으로 갈린다. 그 분기는 "kp confidence 게이트 + 사지 체인 위 연속
// 구간" 이라는 순수 기하 규칙이고, 렌더 컴포넌트에 붙은 채로는 시뮬 없이 검증할 수
// 없다. 규칙을 순수 함수로 격리해 여기서 고정한다.
//
// 검증 축 (플랜 behavior 8축):
//   1) 고신뢰 다리 focus → 체인 1개·점 3개(선) + insetT 0.65 (승인본 65% 규칙)
//   2) 같은 focus 인데 knee 0.43 · ankle 0.29 → 체인 0 · 원 그룹 1 (7R 컷 2 재현)
//   3) 양다리 focus 에서 한쪽만 고신뢰 → 선 1 + 원 1 동시 (측별 혼재)
//   4) 어깨 단독 focus + elbow/hand 저신뢰 → 체인 0 · 원 그룹 1
//   5) 어깨 단독 focus + elbow/hand 고신뢰 → 팔 체인 선 + insetT 0
//   6) 좌·우 어깨 focus → 어떤 체인에도 좌·우가 함께 들어가지 않는다 (N-12)
//   7) 결측/전부 저신뢰 → 빈 결과 (환각 드로잉 0)
//   8) PULSE_PERIOD_MS === 1400 (승인본 .legfx.pulse 1.4s 단일 선언)

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  LIMB_CHAINS,
  PROXIMAL_INSET_T,
  PULSE_PERIOD_MS,
  buildFocusShapes,
} from '../focusShape.ts';
import type { KeypointName } from '../../types/analysis';

// ── 픽스처 ────────────────────────────────────────────────────────────────
// 게이트 = KeypointOverlay.KEYPOINT_LOW_CONFIDENCE_THRESHOLD (0.5) 와 동일 값.
// 신규 임계 상수를 만들지 않는다 — 호출부가 threshold 를 주입한다.
const THRESHOLD = 0.5;

function shapes(
  focusKeypoints: readonly KeypointName[],
  conf: Partial<Record<KeypointName, number>>,
) {
  return buildFocusShapes({
    focusKeypoints,
    confidenceOf: (kp) => (kp in conf ? (conf[kp] as number) : null),
    threshold: THRESHOLD,
  });
}

/** 승인본 7R 컷 2 오른다리 실측 conf (kp150, f75). */
const RIGHT_LEG_HI: Partial<Record<KeypointName, number>> = {
  right_hip: 0.63,
  right_knee: 0.69,
  right_ankle: 0.79,
};

/** 승인본 7R 컷 2 왼다리 실측 conf — knee/ankle 게이트 미달. */
const LEFT_LEG_LOW: Partial<Record<KeypointName, number>> = {
  left_hip: 0.63,
  left_knee: 0.43,
  left_ankle: 0.29,
};

const LEG_FOCUS_R: readonly KeypointName[] = [
  'right_hip',
  'right_knee',
  'right_ankle',
];
const LEG_FOCUS_L: readonly KeypointName[] = [
  'left_hip',
  'left_knee',
  'left_ankle',
];

// ── 1) 고신뢰 다리 → 모양 선 + 근위 inset ─────────────────────────────────

test('고신뢰 다리 focus → 체인 1개·점 3개(선) + insetT 0.65', () => {
  const out = shapes(LEG_FOCUS_R, RIGHT_LEG_HI);
  assert.equal(out.chains.length, 1);
  assert.equal(out.circleGroups.length, 0);
  assert.deepEqual(out.chains[0].keypoints, [
    'right_hip',
    'right_knee',
    'right_ankle',
  ]);
  // 승인본 `:447-448` — hip 관절이 엉덩이 하단이라 hip→knee 선분의 65% 지점부터.
  assert.equal(out.chains[0].insetT, 0.65);
  assert.equal(PROXIMAL_INSET_T.hip, 0.65);
});

// ── 2) 게이트 미달 측 → 부위 원 (승인본 7R 컷 2) ───────────────────────────

test('knee 0.43 · ankle 0.29 → 그 측은 체인 0 · 원 그룹 1', () => {
  const out = shapes(LEG_FOCUS_L, LEFT_LEG_LOW);
  assert.equal(out.chains.length, 0);
  assert.equal(out.circleGroups.length, 1);
  // 원은 게이트를 통과한 focus 관절만 담는다 (저신뢰 좌표 위 표시 금지).
  assert.deepEqual(out.circleGroups[0], ['left_hip']);
});

// ── 3) 한 컷 안에서 측별 혼재 ──────────────────────────────────────────────

test('양다리 focus 에서 오른쪽만 고신뢰 → 선 1개 + 원 1개 동시', () => {
  const out = shapes([...LEG_FOCUS_L, ...LEG_FOCUS_R], {
    ...LEFT_LEG_LOW,
    ...RIGHT_LEG_HI,
  });
  assert.equal(out.chains.length, 1);
  assert.equal(out.circleGroups.length, 1);
  assert.deepEqual(out.chains[0].keypoints, [
    'right_hip',
    'right_knee',
    'right_ankle',
  ]);
  assert.deepEqual(out.circleGroups[0], ['left_hip']);
});

// ── 4·5) 어깨 focus — 팔 체인 가시성으로 갈린다 ────────────────────────────

test('어깨 단독 focus + elbow/hand 저신뢰 → 체인 0 · 원 그룹 1', () => {
  const out = shapes(['left_shoulder'], {
    left_shoulder: 0.88,
    left_elbow: 0.31,
    left_hand: 0.22,
  });
  assert.equal(out.chains.length, 0);
  assert.deepEqual(out.circleGroups, [['left_shoulder']]);
});

test('어깨 단독 focus + elbow/hand 고신뢰 → 팔 체인 선 + insetT 0', () => {
  const out = shapes(['left_shoulder'], {
    left_shoulder: 0.88,
    left_elbow: 0.71,
    left_hand: 0.64,
  });
  assert.equal(out.chains.length, 1);
  assert.equal(out.circleGroups.length, 0);
  // N-11 — focus 가 짚은 사지의 가시 구간 전체 (jointKeys 에 없는 원위 관절 포함).
  assert.deepEqual(out.chains[0].keypoints, [
    'left_shoulder',
    'left_elbow',
    'left_hand',
  ]);
  // 승인본이 팔 체인 inset 값을 제시하지 않았다 → 0 (날조 금지).
  assert.equal(out.chains[0].insetT, 0);
  assert.equal(PROXIMAL_INSET_T.shoulder, 0);
});

// ── 6) 좌↔우 몸통 가로지르기 구조적 불가 (N-12) ────────────────────────────

test('좌·우 어깨 focus → 어떤 체인·원에도 좌우가 함께 들어가지 않는다', () => {
  const out = shapes(['left_shoulder', 'right_shoulder'], {
    left_shoulder: 0.9,
    left_elbow: 0.9,
    left_hand: 0.9,
    right_shoulder: 0.9,
    right_elbow: 0.9,
    right_hand: 0.9,
  });
  assert.equal(out.chains.length, 2);
  for (const group of [
    ...out.chains.map((c) => c.keypoints),
    ...out.circleGroups,
  ]) {
    const hasLeft = group.some((kp) => kp.startsWith('left_'));
    const hasRight = group.some((kp) => kp.startsWith('right_'));
    assert.ok(
      !(hasLeft && hasRight),
      `좌우 혼합 그룹: ${JSON.stringify(group)}`,
    );
  }
});

test('LIMB_CHAINS 사전 자체에 좌우 혼합 체인이 없다 (조건문 아닌 자료구조 강제)', () => {
  assert.equal(LIMB_CHAINS.length, 4);
  for (const chain of LIMB_CHAINS) {
    const hasLeft = chain.keypoints.some((kp) => kp.startsWith('left_'));
    const hasRight = chain.keypoints.some((kp) => kp.startsWith('right_'));
    assert.ok(!(hasLeft && hasRight), JSON.stringify(chain.keypoints));
    assert.ok(chain.keypoints.length >= 2);
    // 근위 관절이 체인의 첫 원소 (inset 적용 대상 판정의 전제).
    assert.ok(chain.keypoints[0].includes(chain.proximalRole));
  }
});

// ── 7) 환각 드로잉 0 ──────────────────────────────────────────────────────

test('focus 관절이 report 에 없으면 빈 결과', () => {
  const out = shapes(LEG_FOCUS_R, {});
  assert.deepEqual(out, { chains: [], circleGroups: [] });
});

test('focus 관절이 전부 저신뢰면 빈 결과', () => {
  const out = shapes(LEG_FOCUS_R, {
    right_hip: 0.11,
    right_knee: 0.2,
    right_ankle: 0.05,
  });
  assert.deepEqual(out, { chains: [], circleGroups: [] });
});

test('focus 가 빈 배열이면 빈 결과', () => {
  const out = shapes([], RIGHT_LEG_HI);
  assert.deepEqual(out, { chains: [], circleGroups: [] });
});

// ── 8) pulse 주기 단일 선언 ────────────────────────────────────────────────

test('PULSE_PERIOD_MS === 1400 (승인본 .legfx.pulse 1.4s)', () => {
  assert.equal(PULSE_PERIOD_MS, 1400);
});

// ── 보강: 런이 근위 관절에서 시작하지 않으면 inset 0 ───────────────────────

test('hip 저신뢰·knee/ankle 고신뢰 → 선은 knee 부터, insetT 0 (이미 몸통 밖)', () => {
  const out = shapes(LEG_FOCUS_R, {
    right_hip: 0.2,
    right_knee: 0.72,
    right_ankle: 0.8,
  });
  assert.equal(out.chains.length, 1);
  assert.deepEqual(out.chains[0].keypoints, ['right_knee', 'right_ankle']);
  assert.equal(out.chains[0].insetT, 0);
});
