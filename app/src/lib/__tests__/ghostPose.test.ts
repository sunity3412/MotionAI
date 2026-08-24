// 잔상 데이터 렌더 판정 검증 (quick-260824-jw4 — belle 08-24 "뭐가 됐든 기능 완료").
//
// 실행: node --test app/src/lib/__tests__/ghostPose.test.ts
// Node 24 type stripping — node:test + node:assert/strict + `.ts` import
// (progressCaption.test.ts 선례). 신규 npm 의존성 0.
//
// 검증 축:
//   1) pickGhostMomentSec — 순간 있는 첫 record. 없음/비유한/음수 → null.
//   2) extractGhostPose — 순간 프레임 슬라이스 + 정규화(골반 원점·몸통 1) +
//      신뢰도 게이트. 형상 불일치/힙·어깨 미달/몸통 0/관절 수 미달 → null.
//   3) alignGhostToTorso — 몸통 방향 회전 정렬 + flipX.
//   4) buildGhostPoseForAsset — 메타 없는 에셋/재료 부재 fail-closed.

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  GHOST_ALIGN,
  GHOST_CONF_MIN,
  GHOST_MIN_POINTS,
  alignGhostToTorso,
  buildGhostPoseForAsset,
  extractGhostPose,
  pickGhostMomentSec,
} from '../ghostPose.ts';

// ── 합성 report — 2프레임, 8관절 (테스트 전용, 값은 손계산 가능하게 정수) ──
const JOINTS = [
  'left_shoulder',
  'right_shoulder',
  'left_hip',
  'right_hip',
  'left_knee',
  'right_knee',
  'left_ankle',
  'right_ankle',
];

function makeReport(overrides?: {
  confAt?: (frame: number, j: number) => number;
  frame1Shift?: number;
}) {
  const J = JOINTS.length;
  const frames = 2;
  const data: number[] = [];
  const confidence: number[] = [];
  for (let t = 0; t < frames; t += 1) {
    const shift = t === 1 ? (overrides?.frame1Shift ?? 100) : 0;
    // 직립 자세: 어깨 y=0, 힙 y=100 (몸통 100px), 무릎 y=160, 발목 y=200.
    const pose: Record<string, [number, number]> = {
      left_shoulder: [90 + shift, 0],
      right_shoulder: [110 + shift, 0],
      left_hip: [95 + shift, 100],
      right_hip: [105 + shift, 100],
      left_knee: [90 + shift, 160],
      right_knee: [110 + shift, 160],
      left_ankle: [90 + shift, 200],
      right_ankle: [110 + shift, 200],
    };
    for (let j = 0; j < J; j += 1) {
      const [x, y] = pose[JOINTS[j]];
      data.push(x, y);
      confidence.push(overrides?.confAt ? overrides.confAt(t, j) : 0.9);
    }
  }
  return { fps: 10, frames, joints: [...JOINTS], data, confidence };
}

function pt(pose: { points: readonly { key: string; x: number; y: number }[] }, key: string) {
  const p = pose.points.find((q) => q.key === key);
  assert.ok(p, `point ${key} missing`);
  return p!;
}

// ── 1) pickGhostMomentSec ────────────────────────────────────────────────
test('pickGhostMomentSec: 순간 있는 첫 record 를 고른다', () => {
  assert.equal(
    pickGhostMomentSec([
      { atVideoSec: undefined },
      null,
      { atVideoSec: 3.3 },
      { atVideoSec: 1.0 },
    ]),
    3.3,
  );
});

test('pickGhostMomentSec: 순간 없는 record 뿐이면 null (split_angle 류)', () => {
  assert.equal(pickGhostMomentSec([{ atVideoSec: undefined }, {}]), null);
  assert.equal(pickGhostMomentSec([{ atVideoSec: Number.NaN }]), null);
  assert.equal(pickGhostMomentSec([{ atVideoSec: -1 }]), null);
  assert.equal(pickGhostMomentSec([]), null);
});

// ── 2) extractGhostPose ──────────────────────────────────────────────────
test('extractGhostPose: 정규화 — 골반 원점, 몸통 길이 1, y-down', () => {
  const got = extractGhostPose(makeReport(), 0);
  assert.ok(got);
  // 골반 = (100,100), 어깨중점 = (100,0) → 몸통 100px. 발목 y=200 → (200-100)/100 = 1.
  assert.equal(Math.round(pt(got!, 'left_ankle').y * 100) / 100, 1);
  assert.equal(Math.round(pt(got!, 'left_ankle').x * 100) / 100, -0.1);
  // 몸통 방향: 골반→어깨 = 위 = -90도.
  assert.equal(Math.round(got!.torsoAngleDeg), -90);
});

test('extractGhostPose: atVideoSec 로 프레임을 고른다 (fps 곱 반올림·클램프)', () => {
  const rep = makeReport({ frame1Shift: 100 });
  // 0.1s * 10fps = frame 1 — x 가 +100 이동한 프레임이지만 정규화라 좌표는 동일.
  const f1 = extractGhostPose(rep, 0.1);
  const f0 = extractGhostPose(rep, 0);
  assert.ok(f1 && f0);
  assert.equal(pt(f1!, 'left_ankle').x, pt(f0!, 'left_ankle').x);
  // 범위 밖 초는 마지막 프레임으로 클램프 — null 이 아니다.
  assert.ok(extractGhostPose(rep, 99));
});

test('extractGhostPose: 신뢰도 게이트 — 힙·어깨 미달이면 null', () => {
  const rep = makeReport({
    confAt: (_t, j) => (JOINTS[j] === 'left_hip' ? GHOST_CONF_MIN - 0.01 : 0.9),
  });
  assert.equal(extractGhostPose(rep, 0), null);
});

test('extractGhostPose: 통과 관절 수 미달이면 null', () => {
  // 힙·어깨 4점만 통과 — GHOST_MIN_POINTS(6) 미달.
  const core = new Set(['left_hip', 'right_hip', 'left_shoulder', 'right_shoulder']);
  const rep = makeReport({ confAt: (_t, j) => (core.has(JOINTS[j]) ? 0.9 : 0.1) });
  assert.equal(extractGhostPose(rep, 0), null);
  assert.ok(GHOST_MIN_POINTS > 4);
});

test('extractGhostPose: 형상 불일치·재료 부재 fail-closed', () => {
  assert.equal(extractGhostPose(null, 0), null);
  assert.equal(extractGhostPose(undefined, 0), null);
  const rep = makeReport();
  assert.equal(extractGhostPose({ ...rep, data: rep.data.slice(1) }, 0), null);
  assert.equal(
    extractGhostPose({ ...rep, confidence: rep.confidence.slice(1) }, 0),
    null,
  );
  assert.equal(extractGhostPose({ ...rep, fps: 0 }, 0), null);
  assert.equal(extractGhostPose(rep, Number.NaN), null);
});

// ── 3) alignGhostToTorso ─────────────────────────────────────────────────
test('alignGhostToTorso: 몸통 방향을 목표 각도로 회전한다', () => {
  const raw = extractGhostPose(makeReport(), 0)!;
  // 직립(-90도)을 도립 그림(+90도)에 정렬 → 180도 회전: 발목이 위(-1)로 간다.
  const aligned = alignGhostToTorso(raw, 90);
  assert.equal(Math.round(pt(aligned, 'left_ankle').y * 100) / 100, -1);
});

test('alignGhostToTorso: flipX 는 좌우를 뒤집는다 (몸통 정렬 유지)', () => {
  const raw = extractGhostPose(makeReport(), 0)!;
  const plain = alignGhostToTorso(raw, -90);
  const flipped = alignGhostToTorso(raw, -90, true);
  assert.ok(
    Math.abs(pt(plain, 'left_ankle').x + pt(flipped, 'left_ankle').x) < 1e-9,
  );
  // flip 후에도 몸통(어깨중점)은 같은 방향 — y 부호 동일.
  assert.equal(
    Math.sign(pt(plain, 'left_shoulder').y),
    Math.sign(pt(flipped, 'left_shoulder').y),
  );
});

// ── 4) buildGhostPoseForAsset ────────────────────────────────────────────
test('buildGhostPoseForAsset: 메타 등재 에셋 + 순간 record + report → 잔상', () => {
  const got = buildGhostPoseForAsset(
    'asset-x',
    makeReport(),
    [{ atVideoSec: 0 }],
    { 'asset-x': { pelvisFx: 0.5, pelvisFy: 0.5, torsoF: 0.1, torsoAngleDeg: 90 } },
  );
  assert.ok(got);
  assert.equal(Math.round(pt(got!, 'left_ankle').y * 100) / 100, -1);
});

test('buildGhostPoseForAsset: fail-closed 전 축 — null', () => {
  const rep = makeReport();
  const align = {
    'asset-x': { pelvisFx: 0.5, pelvisFy: 0.5, torsoF: 0.1, torsoAngleDeg: 90 },
  } as const;
  assert.equal(buildGhostPoseForAsset(null, rep, [{ atVideoSec: 0 }], align), null);
  assert.equal(
    buildGhostPoseForAsset('unregistered', rep, [{ atVideoSec: 0 }], align),
    null,
  );
  assert.equal(buildGhostPoseForAsset('asset-x', rep, [{}], align), null);
  assert.equal(buildGhostPoseForAsset('asset-x', null, [{ atVideoSec: 0 }], align), null);
});

test('GHOST_ALIGN: 등재 에셋 메타는 유한값 (실측 좌표 검증)', () => {
  for (const [asset, meta] of Object.entries(GHOST_ALIGN)) {
    for (const v of [meta.pelvisFx, meta.pelvisFy, meta.torsoF, meta.torsoAngleDeg]) {
      assert.ok(Number.isFinite(v), `${asset} meta must be finite`);
    }
    assert.ok(meta.torsoF > 0 && meta.torsoF < 1, `${asset} torsoF range`);
  }
});
