// summarySource 순수 함수 검증 (32-07 Task 2 — D-06/D-26 + 리뷰 blocker 5).
//
// 실행: node --test app/src/lib/__tests__/summarySource.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (pickerFailure.test.ts 선례). node:test / node:assert 표준 모듈만 쓰고
// `.ts` 확장자 import 를 명시한다.
//
// 검증 축: 잘한 점 문장의 단일 원천이 백엔드 summaryPraise 이고(Test 1), 스팟체크
// 불일치 시 강등되며(Test 2), legacy 폴백은 측정 근거에서만 선정되고(Test 3~5,
// 미측정·커버리지 갭 차원은 칭찬 부적격), 헤드라인에 수치가 들어가지 않는다(D-09).

import test from 'node:test';
import assert from 'node:assert/strict';
import { deriveSummaryContent, type SummaryInput } from '../summarySource.ts';

// D-09 수치-헤드라인 금지 검사용 정규식 (측정 단위가 헤드라인에 새는지 감지).
const NUMBER_IN_HEADLINE = /\d+(\.\d+)?\s*(도|°|점|%)/;

test('Test 1 (doc 우선 — blocker 5): summaryPraise 있으면 그 headline/source 를 그대로 사용', () => {
  const input: SummaryInput = {
    mode: 'mode3',
    summaryPraise: {
      source: 'mission_improved',
      headline: '무릎이 지난번보다 훨씬 더 접혔어요',
      evidenceValue: 6,
      evidenceUnit: '점',
    },
    // 로컬 폴백을 유발할 재료가 있어도 doc 이 우선이어야 한다.
    missionOutcome: { improved: false },
  };
  const out = deriveSummaryContent(input);
  assert.ok(out.praise, 'praise 가 있어야 함');
  assert.equal(out.praise?.source, 'mission_improved');
  assert.equal(out.praise?.headline, '무릎이 지난번보다 훨씬 더 접혔어요'); // 로컬 재파생 없음
  assert.equal(out.praise?.evidenceValue, 6);
  assert.equal(out.praise?.evidenceUnit, '점');
});

test('Test 2 (praiseMismatch 강등): mismatch=true 면 doc praise 버리고 로컬 폴백으로 강등', () => {
  const input: SummaryInput = {
    mode: 'mode3',
    summaryPraise: {
      source: 'clean_dimension',
      headline: '검증에서 어긋난 doc 문장', // 이 문장이 노출되면 안 됨
    },
    spotCheckPraiseMismatch: true,
    missionOutcome: { improved: true, deltaPoints: 4 },
  };
  const out = deriveSummaryContent(input);
  assert.ok(out.praise, 'praise 가 로컬 폴백으로 있어야 함');
  assert.equal(out.praise?.source, 'mission_improved'); // 로컬 폴백 체인
  assert.notEqual(out.praise?.headline, '검증에서 어긋난 doc 문장'); // 검증 실패 문장 미노출
});

test('Test 3 (legacy 폴백 D-26 1순위): missionOutcome.improved → mission_improved, 헤드라인 수치 미포함', () => {
  const input: SummaryInput = {
    mode: 'mode3',
    missionOutcome: { improved: true, deltaPoints: 5, criterion: 'angle_vs_reference__left_knee' },
  };
  const out = deriveSummaryContent(input);
  assert.equal(out.praise?.source, 'mission_improved');
  assert.ok(
    !NUMBER_IN_HEADLINE.test(out.praise?.headline ?? ''),
    `헤드라인에 수치가 있으면 안 됨: ${out.praise?.headline}`,
  );
  // 수치는 evidence 구조 필드로만 분리 (D-09).
  assert.equal(out.praise?.evidenceValue, 5);
  assert.equal(out.praise?.evidenceUnit, '점');
});

test('Test 4a (clean_dimension): 개선 없음 + 감점 0 차원(측정 존재·갭 없음) → clean_dimension', () => {
  const input: SummaryInput = {
    mode: 'mode1',
    missionOutcome: { improved: false },
    dimensionScores: [{ key: 'line', score: 100, hasDeduction: false }],
    coverageGaps: [],
  };
  const out = deriveSummaryContent(input);
  assert.equal(out.praise?.source, 'clean_dimension');
  assert.ok(!NUMBER_IN_HEADLINE.test(out.praise?.headline ?? ''));
});

test('Test 4b (criteria_met): clean 차원 부재 + 측정값 규칙 충족 차원 → criteria_met', () => {
  const input: SummaryInput = {
    mode: 'mode1',
    dimensionScores: [
      { key: 'angle', score: 88, hasDeduction: true, metCriteria: true },
    ],
    coverageGaps: [],
  };
  const out = deriveSummaryContent(input);
  assert.equal(out.praise?.source, 'criteria_met');
});

test('Test 4c (커버리지 가드): 미측정·커버리지 갭 차원은 칭찬 부적격', () => {
  const input: SummaryInput = {
    mode: 'mode1',
    dimensionScores: [
      { key: 'line', score: 100, hasDeduction: false }, // 갭에 포함 → 부적격
      { key: 'stability', score: null, hasDeduction: false }, // 미측정 → 부적격
    ],
    coverageGaps: ['line'],
  };
  const out = deriveSummaryContent(input);
  assert.equal(out.praise, null, '안 잰 것/갭 차원을 칭찬하면 안 됨');
});

test('Test 5 (근거 없음): 측정 근거 전무 → praise === null', () => {
  const input: SummaryInput = {
    mode: 'mode1',
    missionOutcome: { improved: false },
    dimensionScores: [],
    coverageGaps: [],
  };
  const out = deriveSummaryContent(input);
  assert.equal(out.praise, null);
});

test('Test 6 (오늘 고칠 것): mission 기반 + isSafety=true 면 gameFrame=false (D-14)', () => {
  const base: SummaryInput = {
    mode: 'mode3',
    mission: { criterion: 'shoulder_tilt', recordId: 'r01:shoulder_tilt', isSafety: true },
    deductionRecords: [
      { criterion: 'shoulder_tilt', points: -8, recordId: 'r01:shoulder_tilt', statusLine: '몸 중심이 옆으로 기울어요' },
    ],
  };
  const safe = deriveSummaryContent(base);
  assert.ok(safe.todayFix, 'todayFix 가 있어야 함');
  assert.equal(safe.todayFix?.criterion, 'shoulder_tilt');
  assert.equal(safe.todayFix?.headline, '몸 중심이 옆으로 기울어요'); // 매칭 record statusLine
  assert.equal(safe.todayFix?.gameFrame, false); // 안전 = 게임 프레임 금지

  // 안전이 아니면 gameFrame=true
  const nonSafe = deriveSummaryContent({
    ...base,
    mission: { criterion: 'shoulder_tilt', recordId: 'r01:shoulder_tilt', isSafety: false },
  });
  assert.equal(nonSafe.todayFix?.gameFrame, true);
});

test('Test 7a (다음 행동): cueLine 존재 시 cue 기반', () => {
  const input: SummaryInput = {
    mode: 'mode1',
    deductionRecords: [
      { criterion: 'knee', points: -6, statusLine: '무릎이 덜 접혔어요', cueLine: '무릎을 가슴 쪽으로 더 당겨보세요' },
    ],
  };
  const out = deriveSummaryContent(input);
  assert.equal(out.nextAction?.text, '무릎을 가슴 쪽으로 더 당겨보세요');
});

test('Test 7b (다음 행동): cueLine 부재 시 보완 운동 이유 기반', () => {
  const input: SummaryInput = {
    mode: 'mode1',
    deductionRecords: [
      { criterion: 'knee', points: -6, statusLine: '무릎이 덜 접혔어요', exerciseReason: '햄스트링 유연성이 무릎 접힘을 돕습니다' },
    ],
  };
  const out = deriveSummaryContent(input);
  assert.equal(out.nextAction?.text, '햄스트링 유연성이 무릎 접힘을 돕습니다');
});

test('Test 7c (다음 행동): cue·운동 이유 모두 부재(fail-closed) → 코치 질문 유도 문구', () => {
  const input: SummaryInput = {
    mode: 'mode1',
    deductionRecords: [
      { criterion: 'knee', points: -6, statusLine: '무릎이 덜 접혔어요' },
    ],
  };
  const out = deriveSummaryContent(input);
  assert.ok(out.nextAction, 'nextAction 이 있어야 함');
  assert.ok(
    (out.nextAction?.text ?? '').includes('강사'),
    `코치 질문 유도 문구여야 함: ${out.nextAction?.text}`,
  );
});
