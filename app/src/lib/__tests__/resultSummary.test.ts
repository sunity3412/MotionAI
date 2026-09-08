// 요약 칩 조립 순수 로직 검증 (belle 09-08 재디자인 시안 1).
//
// 실행: node --test app/src/lib/__tests__/resultSummary.test.ts
// momentJump.test.ts / voiceSnap.test.ts 관례 — node:test + `.ts` import, 신규 의존성 0.
//
// 검증 축:
//   1) 감점 큰 순 · 동점은 입력 순서 (같은 doc 이 두 번 다르게 보이지 않는다)
//   2) 라벨은 표(deductionLabels)와 **같은 소스** — 칩은 괄호 설명만 덜어낸다
//   3) 감점 아닌 record 제외 (감점 칩에 감점 아닌 것을 넣지 않는다)
//   4) total 은 칩 개수가 아니라 교정할 점의 실제 수 (헤드라인·CTA 의 N)

import test from 'node:test';
import assert from 'node:assert/strict';
import { buildSummaryChips, summaryChipLabel } from '../resultSummary.ts';
import { criterionLabelKo } from '../deductionLabels.ts';
import type { DeductionRecord } from '../../types/analysis.ts';

function rec(over: Partial<DeductionRecord> = {}): DeductionRecord {
  return {
    criterion: 'angle_vs_reference__right_elbow',
    measuredValue: 100,
    baselineValue: 0,
    baselineKind: null,
    deviation: 11.6,
    ruleId: 'r',
    points: -11.6,
    unit: 'deg',
    ipsfAnchor: 'a',
    source: 'geometry',
    deviationSource: 'reference_relative',
    ...over,
  } as DeductionRecord;
}

test('감점이 큰 순으로 고른다 (시안 11.6 / 9.4 / 7.2 순서)', () => {
  const out = buildSummaryChips([
    rec({ recordId: 'a', criterion: 'angle_vs_reference__left_knee', points: -9.4 }),
    rec({ recordId: 'b', criterion: 'angle_vs_reference__right_elbow', points: -11.6 }),
    rec({ recordId: 'c', criterion: 'line', points: -7.2 }),
  ]);
  assert.deepEqual(
    out.chips.map((c) => [c.recordId, c.pointsText]),
    [
      ['b', '−11.6'],
      ['a', '−9.4'],
      ['c', '−7.2'],
    ],
  );
  assert.equal(out.overflow, 0);
  assert.equal(out.total, 3);
});

test('동점은 입력 순서를 지킨다 (결정성)', () => {
  const out = buildSummaryChips([
    rec({ recordId: 'first', points: -5 }),
    rec({ recordId: 'second', points: -5 }),
    rec({ recordId: 'third', points: -5 }),
  ]);
  assert.deepEqual(
    out.chips.map((c) => c.recordId),
    ['first', 'second', 'third'],
  );
});

test('칩 라벨은 표 라벨에서 괄호 설명만 덜어낸 것 — 규칙 사본 0', () => {
  // 표: '오른쪽 팔꿈치(정은지 대비 각도)' / 칩: '오른쪽 팔꿈치'
  const table = criterionLabelKo('angle_vs_reference__right_elbow');
  const chip = summaryChipLabel('angle_vs_reference__right_elbow');
  assert.ok(table.startsWith(chip), `표 라벨이 칩 라벨로 시작해야 한다: ${table} / ${chip}`);
  assert.ok(!chip.includes('('), '칩에는 괄호 설명이 없다');

  // 각도가 아닌 criterion 은 표와 **완전히 같은** 라벨을 쓴다.
  for (const c of ['line', 'split_angle', 'body_relative_reach', '모르는_기준']) {
    assert.equal(summaryChipLabel(c), criterionLabelKo(c), c);
  }
});

test('감점이 아닌 record 는 칩이 되지 않는다', () => {
  const out = buildSummaryChips([
    rec({ recordId: 'ok', points: -3 }),
    rec({ recordId: 'zero', points: 0 }),
    rec({ recordId: 'plus', points: 4 }),
    rec({ recordId: 'nan', points: Number.NaN }),
    rec({ recordId: 'inf', points: Number.NEGATIVE_INFINITY }),
  ]);
  assert.deepEqual(
    out.chips.map((c) => c.recordId),
    ['ok'],
  );
  assert.equal(out.total, 1, 'total 도 감점 record 만 센다');
});

test('칩은 max 개까지, 나머지는 overflow — total 은 전체 수', () => {
  const many = Array.from({ length: 7 }, (_, i) =>
    rec({ recordId: `r${i}`, points: -(10 - i) }),
  );
  const out = buildSummaryChips(many, 3);
  assert.equal(out.chips.length, 3);
  assert.equal(out.overflow, 4, '시안의 "+N" 칩이 쓰는 값');
  assert.equal(out.total, 7, '헤드라인 "분석에서 N개" 와 CTA 가 쓰는 값');
});

test('max 가 이상하면 3개로 되돌린다', () => {
  const many = Array.from({ length: 5 }, (_, i) => rec({ recordId: `r${i}`, points: -1 }));
  for (const bad of [0, -2, Number.NaN, Number.POSITIVE_INFINITY]) {
    assert.equal(buildSummaryChips(many, bad).chips.length, 3, String(bad));
  }
});

test('입력 배열을 변형하지 않는다 (화면의 시간순 정렬 보존)', () => {
  const list = [
    rec({ recordId: 'a', points: -1 }),
    rec({ recordId: 'b', points: -9 }),
  ];
  const before = list.map((r) => r.recordId);
  buildSummaryChips(list);
  assert.deepEqual(
    list.map((r) => r.recordId),
    before,
  );
});

test('빈/없는 입력 — 빈 결과 (크래시 0)', () => {
  for (const input of [null, undefined, []]) {
    const out = buildSummaryChips(input as never);
    assert.deepEqual(out, { chips: [], overflow: 0, total: 0 });
  }
});
