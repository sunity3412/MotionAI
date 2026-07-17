// growthSelectors 시맨틱 테스트 (HIGH-2) — 신규 테스트 프레임워크·devDependency 0.
// 앱에 JS 테스트 러너가 없어(typecheck 만이 정적 게이트) selector 핵심 규칙을 실행
// 가능한 fixture 로 잠근다: 주간 bucket·모드 비혼합·폴백 3분기·scoreSuppressed 제외
// (HIGH-1)·그룹핑·point 델타·NaN 방어.
//
// 실행 (Node 24 내장 타입 스트리핑 — growthSelectors.ts 는 `import type` 만 쓰는
// 순수 모듈이라 런타임 의존 0 → 그대로 로드됨):
//   cd app && node --experimental-strip-types scripts/assert-growth-selectors.mjs
// verify-firebase.mjs 관례(순수 Node 실행, node: 내장만)와 정합.

import assert from 'node:assert/strict';
import {
  weekStartOf,
  weeklyAverages,
  defaultGrowthMode,
  motionDeltas,
  hasUsableGrowthScore,
} from '../src/lib/growthSelectors.ts';

// 로컬 자정 기준 주(월요일 시작). 2026-01-05 = 월, 01-07 = 수(같은 주),
// 01-12 = 다음 주 월, 01-19 = 그 다음 주 월.
const monA = new Date(2026, 0, 5).getTime();
const wedA = new Date(2026, 0, 7).getTime();
const monB = new Date(2026, 0, 12).getTime();
const monC = new Date(2026, 0, 19).getTime();

function mkDoc({
  id,
  mode,
  createdAt,
  overallScore,
  scoreSuppressed = false,
  refId,
  refName,
  status = 'done',
}) {
  const comparison =
    mode === 'mode1'
      ? {
          mode: 'mode1',
          referenceMotionId: refId,
          referenceMotionName: refName,
          athleteName: '정은지',
          similarity: 0,
        }
      : { mode: 'mode3', isFirst: false };
  const result = {
    overallScore,
    dimensionScores: {},
    joints: [],
    tips: [],
    comparison,
    myVideoUrl: '',
    ...(scoreSuppressed
      ? { scoreSuppressed: true, scoreSuppressedReason: 'unheld' }
      : {}),
  };
  return {
    analysisId: id,
    mode,
    status,
    fileName: '',
    createdAt,
    updatedAt: createdAt,
    result,
  };
}

// ── 1. weekStartOf: 수요일 millis → 그 주 월요일 00:00 로컬 millis ──────────
assert.equal(weekStartOf(wedA), monA, 'weekStartOf 수요일→월요일 경계');
assert.equal(weekStartOf(monA), monA, 'weekStartOf 월요일=자기 자신');

// ── 2. weeklyAverages 모드 비혼합 (D-02) ──────────────────────────────────
// 같은 주에 mode1(80) + mode3(40) 섞여 있어도 서로의 점수를 평균에 넣지 않는다.
const mixed = [
  mkDoc({ id: 'm1', mode: 'mode1', createdAt: monA, overallScore: 80, refId: 'ref-a', refName: '사이드스핀' }),
  mkDoc({ id: 'm3', mode: 'mode3', createdAt: monA, overallScore: 40 }),
];
const wa1 = weeklyAverages(mixed, 'mode1');
const wa3 = weeklyAverages(mixed, 'mode3');
assert.equal(wa1.length, 1, 'mode1 주별 점 1개');
assert.equal(wa1[0].avg, 80, 'mode1 평균에 mode3 점수 미유입');
assert.equal(wa3.length, 1, 'mode3 주별 점 1개');
assert.equal(wa3[0].avg, 40, 'mode3 평균에 mode1 점수 미유입');

// ── 3. defaultGrowthMode 3분기 (D-03) ─────────────────────────────────────
// (a) 최신 모드(mode3) 주별 점 ≥2 → 그 모드. 배열은 최신순(newest-first).
const dgA = [
  mkDoc({ id: 'a2', mode: 'mode3', createdAt: monB, overallScore: 60 }),
  mkDoc({ id: 'a1', mode: 'mode3', createdAt: monA, overallScore: 50 }),
];
assert.equal(defaultGrowthMode(dgA), 'mode3', 'D-03(a) 최신 모드 ≥2주');

// (b) 최신 모드(mode1) 1주뿐, 다른 모드(mode3) ≥2주 → 폴백.
const dgB = [
  mkDoc({ id: 'b3', mode: 'mode1', createdAt: monC, overallScore: 70, refId: 'ref-a', refName: '사이드스핀' }),
  mkDoc({ id: 'b2', mode: 'mode3', createdAt: monB, overallScore: 60 }),
  mkDoc({ id: 'b1', mode: 'mode3', createdAt: monA, overallScore: 50 }),
];
assert.equal(defaultGrowthMode(dgB), 'mode3', 'D-03(b) 타 모드 폴백');

// (c) 양쪽 다 <2주 → null.
const dgC = [
  mkDoc({ id: 'c2', mode: 'mode1', createdAt: monB, overallScore: 70, refId: 'ref-a', refName: '사이드스핀' }),
  mkDoc({ id: 'c1', mode: 'mode3', createdAt: monA, overallScore: 50 }),
];
assert.equal(defaultGrowthMode(dgC), null, 'D-03(c) 양쪽 부족 null');

// ── 4. hasUsableGrowthScore / HIGH-1: scoreSuppressed 제외 (평균·델타·기본모드) ──
// scoreSuppressed:true 이고 overallScore 가 있는 mode3 문서가 모든 후보에서 빠진다.
const suppressed = mkDoc({ id: 's1', mode: 'mode3', createdAt: monC, overallScore: 90, scoreSuppressed: true });
assert.equal(hasUsableGrowthScore(suppressed, 'mode3'), false, 'HIGH-1 predicate 억제 제외');
const withSuppressed = [
  suppressed,
  mkDoc({ id: 's0', mode: 'mode3', createdAt: monA, overallScore: 50 }),
];
const waS = weeklyAverages(withSuppressed, 'mode3');
assert.equal(waS.length, 1, 'HIGH-1 weeklyAverages 억제 주 미포함');
assert.equal(waS[0].avg, 50, 'HIGH-1 억제 점수(90) 평균 미반영');
assert.equal(defaultGrowthMode(withSuppressed), null, 'HIGH-1 억제 제외로 <2주 → null');
const mdS = motionDeltas(withSuppressed);
const selfRowS = mdS.find((r) => r.key === 'self');
assert.equal(selfRowS.latestAvg, 50, 'HIGH-1 motionDeltas 억제 점수 미반영');

// ── 5. motionDeltas 그룹핑 (D-04 화면층) ──────────────────────────────────
// mode1 은 referenceMotionId 별 행, mode3 는 '내 기록' 단일 행.
const grouping = [
  mkDoc({ id: 'g1', mode: 'mode1', createdAt: monA, overallScore: 70, refId: 'ref-a', refName: '사이드스핀' }),
  mkDoc({ id: 'g2', mode: 'mode1', createdAt: monB, overallScore: 76, refId: 'ref-a', refName: '사이드스핀' }),
  mkDoc({ id: 'g3', mode: 'mode1', createdAt: monA, overallScore: 55, refId: 'ref-b', refName: '폭스탑' }),
  mkDoc({ id: 'g4', mode: 'mode3', createdAt: monA, overallScore: 40 }),
  mkDoc({ id: 'g5', mode: 'mode3', createdAt: monB, overallScore: 48 }),
];
const md = motionDeltas(grouping);
const rowA = md.find((r) => r.key === 'ref-a');
const rowB = md.find((r) => r.key === 'ref-b');
const selfRow = md.find((r) => r.key === 'self');
assert.ok(rowA && rowA.badge === '프로 비교', 'mode1 referenceMotionId 그룹 + 프로 배지');
assert.equal(rowA.label, '사이드스핀', 'mode1 label=referenceMotionName');
assert.ok(rowB, 'mode1 두 번째 refId 별도 행');
assert.ok(selfRow && selfRow.label === '내 기록', 'mode3 단일 내 기록 행');
// mode1 refId 는 2개 → self 는 mode3 전부 1행 = 총 3행.
assert.equal(md.length, 3, 'motionDeltas 그룹 수 = ref-a + ref-b + self');

// ── 6. motionDeltas 델타: 정수 point 차이, 활동 주 1개면 null (D-05) ────────
assert.equal(rowA.delta, 6, 'ref-a 델타 = 76 − 70 = +6 point');
assert.ok(Number.isInteger(rowA.delta), '델타는 정수 point (퍼센트 아님)');
assert.equal(rowB.delta, null, 'ref-b 활동 주 1개 → 첫 기록 null');
assert.equal(selfRow.delta, 8, '내 기록 델타 = 48 − 40 = +8 point');

// ── 7. NaN 방어: overallScore NaN 문서가 평균/델타에 미반영 ──────────────────
const withNaN = [
  mkDoc({ id: 'n2', mode: 'mode3', createdAt: monB, overallScore: Number.NaN }),
  mkDoc({ id: 'n1', mode: 'mode3', createdAt: monA, overallScore: 50 }),
];
const waN = weeklyAverages(withNaN, 'mode3');
assert.equal(waN.length, 1, 'NaN 문서의 주는 집계 제외');
assert.equal(waN[0].avg, 50, 'NaN 미반영 평균');
assert.equal(hasUsableGrowthScore(withNaN[0], 'mode3'), false, 'NaN predicate 제외');

console.log('growth-selectors semantic checks passed');
