// 발전 캡션 판정 검증 (quick-260822-oe1 — belle 08-22 갱신 문구 "저번보다 나아졌어요").
//
// 실행: node --test app/src/lib/__tests__/progressCaption.test.ts
// Node 24 type stripping — node:test + node:assert/strict + `.ts` import
// (illustrationHow.test.ts 선례). 신규 npm 의존성 0.
//
// 검증 축 (PLAN behavior 블록만 — 수치 채우기 금지):
//   1) findPreviousComparable — 직전 done mode1 + 같은 referenceMotionId 중 최신.
//      자기 자신/미래/같은 시각/mode3/타 동작/미완료 제외. 없으면 null.
//   2) extractCriterionMeasure — criterion 정확 일치 첫 record 의
//      { measured, target, unit }. records 없음/불일치 → null.
//   3) buildProgressCaption 개선 판정 — 개선 = prevDelta − curDelta ≥ 문턱이고
//      두 쪽 다 deg + 유한값 + 앵커 progressSentence 있으면 그 문장 (단일 소스).
//      차이형(target 0)·절대각형 두 record 모양 다 성립. 경계(= 문턱) 포함.
//   4) fail-closed 전 축 — 문턱 null / prev null / unit 불일치 / non-finite /
//      개선 < 문턱 / 악화 / 미등록 asset / progressSentence 없는 앵커 /
//      rotate 앵커 → null.
//   5) 앵커 원문 — HOW_ANCHORS['ref-kip-up--leg'].progressSentence 가 belle
//      08-22 갱신 화법 원문 그대로 (BELLE-0821-P2 — 변형·수치 삽입 금지).

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  PROGRESS_NOISE_THRESHOLD_DEG,
  findPreviousComparable,
  extractCriterionMeasure,
  buildProgressCaption,
} from '../progressCaption.ts';
import { HOW_ANCHORS, type HowAnchors } from '../illustrationHow.ts';
import type { AnalysisDoc } from '../../types/analysis.ts';

/** belle 08-22 갱신 화법 원문 (검증 리터럴 — 프로덕션 사본 아님, 단일 소스는 앵커). */
const BELLE_SENTENCE = '저번보다 나아졌어요';

/** 최소 mode1 done doc 픽스처 — 판정에 쓰이는 필드만 (cast 는 런타임 소거). */
function mode1Doc(
  analysisId: string,
  createdAt: number,
  referenceMotionId: string,
  opts?: {
    status?: string;
    records?: Record<string, unknown>[];
    mode3?: boolean;
  },
): AnalysisDoc {
  return {
    analysisId,
    mode: opts?.mode3 ? 'mode3' : 'mode1',
    status: opts?.status ?? 'done',
    fileName: 'f.mp4',
    createdAt,
    updatedAt: createdAt,
    result: {
      comparison: opts?.mode3
        ? { mode: 'mode3', isFirst: false }
        : { mode: 'mode1', referenceMotionId },
      ...(opts?.records ? { deductionBreakdown: { records: opts.records } } : {}),
    },
  } as unknown as AnalysisDoc;
}

const CURRENT = { analysisId: 'cur', createdAt: 1000, referenceMotionId: 'ref-kip-up' };

// ── 1) findPreviousComparable ────────────────────────────────────────────

test('1a: 같은 동작 직전 done mode1 중 최신을 고른다 (더 오래된 것·잡음 doc 무시)', () => {
  const analyses = [
    mode1Doc('future', 1100, 'ref-kip-up'), // 미래 — 제외
    mode1Doc('same-ts', 1000, 'ref-kip-up'), // 같은 시각 — "현재보다 작은 것"만
    mode1Doc('cur', 1000, 'ref-kip-up'), // 자기 자신 — 제외
    mode1Doc('not-done', 970, 'ref-kip-up', { status: 'processing' }), // 미완료
    mode1Doc('other-ref', 960, 'ref-power-spin'), // 타 동작
    mode1Doc('m3', 950, 'ref-kip-up', { mode3: true }), // mode3
    mode1Doc('a', 900, 'ref-kip-up'), // ← 정답 (직전 최신)
    mode1Doc('b', 800, 'ref-kip-up'), // 더 오래됨
  ];
  const prev = findPreviousComparable(analyses, CURRENT);
  assert.ok(prev != null);
  assert.equal(prev.analysisId, 'a');
});

test('1b: 후보 없음 → null (정렬 순서 무관 — 배열 순서에 의존하지 않는다)', () => {
  assert.equal(findPreviousComparable([], CURRENT), null);
  assert.equal(
    findPreviousComparable([mode1Doc('x', 900, 'ref-power-spin')], CURRENT),
    null,
  );
  // 오름차순으로 줘도 최신(900)을 고른다
  const asc = [mode1Doc('b', 800, 'ref-kip-up'), mode1Doc('a', 900, 'ref-kip-up')];
  assert.equal(findPreviousComparable(asc, CURRENT)?.analysisId, 'a');
});

// ── 2) extractCriterionMeasure ───────────────────────────────────────────

const SPLIT_50 = { criterion: 'split_angle', measuredValue: 50, baselineValue: 0, unit: 'deg' };

test('2a: criterion 정확 일치 첫 record 의 { measured, target, unit }', () => {
  const doc = mode1Doc('p', 900, 'ref-kip-up', {
    records: [
      { criterion: 'other', measuredValue: 1, baselineValue: 2, unit: 'deg' },
      SPLIT_50,
      { criterion: 'split_angle', measuredValue: 99, baselineValue: 0, unit: 'deg' }, // 둘째 무시
    ],
  });
  assert.deepEqual(extractCriterionMeasure(doc, 'split_angle'), {
    measured: 50,
    target: 0,
    unit: 'deg',
  });
});

test('2b: records 없음 / 불일치 / doc null → null', () => {
  assert.equal(extractCriterionMeasure(mode1Doc('p', 900, 'ref-kip-up'), 'split_angle'), null);
  assert.equal(
    extractCriterionMeasure(
      mode1Doc('p', 900, 'ref-kip-up', { records: [] }),
      'split_angle',
    ),
    null,
  );
  assert.equal(
    extractCriterionMeasure(
      mode1Doc('p', 900, 'ref-kip-up', {
        records: [{ criterion: 'other', measuredValue: 1, baselineValue: 2, unit: 'deg' }],
      }),
      'split_angle',
    ),
    null,
  );
  assert.equal(extractCriterionMeasure(null, 'split_angle'), null);
  assert.equal(extractCriterionMeasure(undefined, 'split_angle'), null);
});

// ── 3) buildProgressCaption — 개선 판정 (문턱 주입, 상수 직접 비의존) ────

const ASSET = 'ref-kip-up--leg';
const deg = (measured: number, target: number) => ({ measured, target, unit: 'deg' });

test('3a: 차이형(50→20, 개선 30 ≥ 문턱 12) → belle 원문 (앵커 단일 소스와 동일 참조)', () => {
  const caption = buildProgressCaption(ASSET, deg(20, 0), deg(50, 0), 12);
  assert.equal(caption, BELLE_SENTENCE);
  const anchor = HOW_ANCHORS[ASSET];
  assert.ok(anchor.kind === 'baked');
  assert.equal(caption, anchor.progressSentence); // 문장 사본 금지 — 단일 소스
});

test('3b: 절대각형(130/180 → 165/180, 개선 35) → 문장 · 경계(개선 == 문턱)도 문장', () => {
  assert.equal(buildProgressCaption(ASSET, deg(165, 180), deg(130, 180), 12), BELLE_SENTENCE);
  // prevDelta 32 − curDelta 20 = 12 == 문턱 → 개선 ≥ 문턱이므로 문장
  assert.equal(buildProgressCaption(ASSET, deg(20, 0), deg(32, 0), 12), BELLE_SENTENCE);
});

test('3c: 기본 인자 = 상수 (null 이면 전면 비활성, 수치면 그 문턱)', () => {
  // 개선 폭을 비상식적으로 크게 줘 상수의 구체값에 비의존 — null/수치 분기만 본다.
  const got = buildProgressCaption(ASSET, deg(0, 0), deg(9999, 0));
  assert.equal(got, PROGRESS_NOISE_THRESHOLD_DEG == null ? null : BELLE_SENTENCE);
});

// ── 4) fail-closed 전 축 ─────────────────────────────────────────────────

test('4: 문턱 null / prev 없음 / unit 불일치 / non-finite / 미달 / 악화 / 앵커 부적격 → null', () => {
  const good = { cur: deg(20, 0), prev: deg(50, 0) };
  // 문턱 null (측정 불충분 = 캡션 전면 비활성, BELLE-0821-P3)
  assert.equal(buildProgressCaption(ASSET, good.cur, good.prev, null), null);
  // prev 없음 (직전 분석 없음 / record 없음)
  assert.equal(buildProgressCaption(ASSET, good.cur, null, 12), null);
  assert.equal(buildProgressCaption(ASSET, good.cur, undefined, 12), null);
  // current 없음 (수치 문장 없는 곳에 캡션만 뜨는 일 없음)
  assert.equal(buildProgressCaption(ASSET, null, good.prev, 12), null);
  // unit 불일치 (한쪽이라도 deg 아님)
  assert.equal(
    buildProgressCaption(ASSET, { measured: 20, target: 0, unit: 'notch' }, good.prev, 12),
    null,
  );
  assert.equal(
    buildProgressCaption(ASSET, good.cur, { measured: 50, target: 0, unit: 'cm' }, 12),
    null,
  );
  // 값 없음 / non-finite
  assert.equal(buildProgressCaption(ASSET, { measured: null, target: 0, unit: 'deg' }, good.prev, 12), null);
  assert.equal(buildProgressCaption(ASSET, deg(Number.NaN, 0), good.prev, 12), null);
  assert.equal(buildProgressCaption(ASSET, good.cur, deg(Number.POSITIVE_INFINITY, 0), 12), null);
  // 개선 < 문턱 (prev 30 → cur 20, 개선 10 < 12)
  assert.equal(buildProgressCaption(ASSET, deg(20, 0), deg(30, 0), 12), null);
  // 악화 (개선 음수 — 악화 문구 발명 금지, 침묵)
  assert.equal(buildProgressCaption(ASSET, deg(40, 0), deg(20, 0), 12), null);
  // 미등록 asset
  assert.equal(buildProgressCaption('ref-kip-up', good.cur, good.prev, 12), null);
  assert.equal(buildProgressCaption(null, good.cur, good.prev, 12), null);
  assert.equal(buildProgressCaption(undefined, good.cur, good.prev, 12), null);
});

test('4b: progressSentence 없는 baked 앵커 / rotate 앵커 → null (데이터 opt-in)', () => {
  const anchors: Readonly<Record<string, HowAnchors>> = {
    'baked-no-progress': {
      kind: 'baked',
      arrows: [{ from: [0, 0], to: [1, 1], ctrlOffset: [0, 0] }],
      directionSentence: '{n}°',
      // progressSentence 없음 — 이 에셋은 캡션 미대상
    },
    'rotate-any': {
      kind: 'rotate',
      limbs: [],
      shares: [],
      directionSentence: '{n}°',
      nowLabelOffsetY: 0,
    },
  };
  assert.equal(
    buildProgressCaption('baked-no-progress', deg(20, 0), deg(50, 0), 12, anchors),
    null,
  );
  assert.equal(buildProgressCaption('rotate-any', deg(20, 0), deg(50, 0), 12, anchors), null);
});

// ── 5) 앵커 원문 박제 (BELLE-0821-P2) ────────────────────────────────────

test('5: HOW_ANCHORS ref-kip-up--leg 의 progressSentence = belle 08-21 원문 그대로', () => {
  const anchor = HOW_ANCHORS['ref-kip-up--leg'];
  assert.ok(anchor.kind === 'baked');
  assert.equal(anchor.progressSentence, BELLE_SENTENCE);
});
