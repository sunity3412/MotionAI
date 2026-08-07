// 재생바 결함 틱(buildDeductionTicks) 순수 로직 검증.
//
// 실행: node --test app/src/lib/__tests__/deductionLabels.test.ts
// cueTrack.test.ts 관례 — node:test / node:assert + `.ts` import, 신규 의존성 0.
//
// debug va-subtitle-audio-mismatch (belle 08-07) — record 별 인증 순간(atFrameIdx)
// 틱 분리 검증:
//   1) atFrameIdx 보유 record → record 별 틱 (같은 frame 은 번호 병합).
//   2) atFrameIdx 부재 record → 종전 공유 median 틱 (veto applied 일 때만 —
//      wj3 저신뢰 복원 경로 보존).
//   3) veto 미적용 + atFrameIdx 부재 → 틱 없음 (fabricate 0).

import test from 'node:test';
import assert from 'node:assert/strict';
import { buildDeductionTicks } from '../deductionLabels.ts';
import type { DeductionRecord, VisionVeto } from '../../types/analysis.ts';

const rec = (fields: Partial<DeductionRecord>): DeductionRecord =>
  ({ ...fields }) as DeductionRecord;

const vetoApplied = (userFrames: number[]): VisionVeto =>
  ({
    status: 'applied',
    windowMedianAngleDeltas: { sourceFrameIndices: { user: userFrames } },
  }) as unknown as VisionVeto;

test('ticks: atFrameIdx 보유 record 는 record 별 틱 — 제 순간 분리 (엘보 잔재 해소)', () => {
  const records = [
    rec({ recordId: 'r00', atFrameIdx: 100 }),
    rec({ recordId: 'r01', atFrameIdx: 67 }),
    rec({ recordId: 'r02', atFrameIdx: 44 }),
    rec({ recordId: 'r03', atFrameIdx: 91 }),
  ];
  const out = buildDeductionTicks(records, [1, 2, 3, 4], vetoApplied([16]));
  assert.deepEqual(out, [
    { frameIndex: 44, numbers: [3] },
    { frameIndex: 67, numbers: [2] },
    { frameIndex: 91, numbers: [4] },
    { frameIndex: 100, numbers: [1] },
  ]);
});

test('ticks: 같은 frame 의 record 는 번호 병합, 번호 null record 는 제외', () => {
  const records = [
    rec({ recordId: 'r00', atFrameIdx: 30 }),
    rec({ recordId: 'r01', atFrameIdx: 30 }),
    rec({ recordId: 'r02', atFrameIdx: 12 }),
  ];
  const out = buildDeductionTicks(records, [2, 1, null], null);
  assert.deepEqual(out, [{ frameIndex: 30, numbers: [1, 2] }]);
});

test('ticks: atFrameIdx 부재 record 는 종전 공유 median 틱 (wj3 복원 경로 보존)', () => {
  // 전건 부재 + veto applied → median frame 1개에 전 번호 병합 (종전 동작 그대로).
  const legacy = [rec({ recordId: 'r00' }), rec({ recordId: 'r01' })];
  const out = buildDeductionTicks(legacy, [1, 2], vetoApplied([10, 20, 30]));
  assert.deepEqual(out, [{ frameIndex: 20, numbers: [1, 2] }]);

  // 혼합: 인증 record 는 제 순간, 미인증 record 는 median — 같은 frame 이면 병합.
  const mixed = [
    rec({ recordId: 'r00', atFrameIdx: 30 }),
    rec({ recordId: 'r01' }),
  ];
  const mixedOut = buildDeductionTicks(mixed, [1, 2], vetoApplied([18]));
  assert.deepEqual(mixedOut, [
    { frameIndex: 18, numbers: [2] },
    { frameIndex: 30, numbers: [1] },
  ]);
});

test('ticks: veto 미적용 + atFrameIdx 부재 → 틱 없음 (순간을 지어내지 않는다)', () => {
  assert.deepEqual(
    buildDeductionTicks([rec({ recordId: 'r00' })], [1], null),
    [],
  );
  assert.deepEqual(
    buildDeductionTicks(
      [rec({ recordId: 'r00' })],
      [1],
      { status: 'skipped' } as unknown as VisionVeto,
    ),
    [],
  );
  // 인증 record 는 veto 없이도 제 순간 틱 (측정 순간이 곧 근거).
  assert.deepEqual(
    buildDeductionTicks([rec({ recordId: 'r00', atFrameIdx: 5 })], [1], null),
    [{ frameIndex: 5, numbers: [1] }],
  );
});
