// 재생바 결함 틱(buildDeductionTicks) + 시간순 정렬(sortDeductionRecordsByMoment)
// 순수 로직 검증.
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
//
// belle 08-07 #1 (quick-260807-fpw) — 감점 번호 시간순 정렬 검증:
//   4) atVideoSec 오름차순 / 부재·비유한 뒤로 원순서 / 동률 stable / 입력 비변형.
//   5) 정렬 결과 → buildDeductionMarkers 로 번호가 시간순 1부터 증가 (번호·마커·
//      틱 시간순의 실체).

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildDeductionMarkers,
  buildDeductionTicks,
  sortDeductionRecordsByMoment,
} from '../deductionLabels.ts';
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

// ── belle 08-07 #1 (quick-260807-fpw) — 시간순 정렬 ──────────────────────────

test('sort: atVideoSec 혼재 입력이 오름차순으로 정렬된다', () => {
  const out = sortDeductionRecordsByMoment([
    rec({ recordId: 'a', atVideoSec: 5.5 }),
    rec({ recordId: 'b', atVideoSec: 1.2 }),
    rec({ recordId: 'c' }),
    rec({ recordId: 'd', atVideoSec: 3.3 }),
  ]);
  assert.deepEqual(
    out.map((r) => r.recordId),
    ['b', 'd', 'a', 'c'],
  );
});

test('sort: atVideoSec 없는/비유한 record 들은 뒤에 원순서로 온다', () => {
  // NaN·Infinity 도 "없음" 취급 (순간을 지어내지 않는다 — fabricate 0).
  const out = sortDeductionRecordsByMoment([
    rec({ recordId: 'x' }),
    rec({ recordId: 'y', atVideoSec: Number.NaN }),
    rec({ recordId: 'z', atVideoSec: 0.5 }),
    rec({ recordId: 'w', atVideoSec: Number.POSITIVE_INFINITY }),
  ]);
  assert.deepEqual(
    out.map((r) => r.recordId),
    ['z', 'x', 'y', 'w'],
  );
});

test('sort: 동률은 원순서 유지 (stable)', () => {
  const out = sortDeductionRecordsByMoment([
    rec({ recordId: 'p', atVideoSec: 2 }),
    rec({ recordId: 'q', atVideoSec: 2 }),
    rec({ recordId: 'r', atVideoSec: 1 }),
  ]);
  assert.deepEqual(
    out.map((r) => r.recordId),
    ['r', 'p', 'q'],
  );
});

test('sort: 입력 배열 비변형 (복제본 반환)', () => {
  const input = [
    rec({ recordId: 'a', atVideoSec: 9 }),
    rec({ recordId: 'b', atVideoSec: 1 }),
  ];
  const snapshot = input.map((r) => r.recordId);
  const out = sortDeductionRecordsByMoment(input);
  assert.notEqual(out, input); // 새 배열
  assert.deepEqual(input.map((r) => r.recordId), snapshot); // 원본 순서 그대로
  assert.deepEqual(
    out.map((r) => r.recordId),
    ['b', 'a'],
  );
});

test('sort → buildDeductionMarkers: 번호가 측정 순간 시간순으로 1부터 증가', () => {
  // 저장 순서는 뒤죽박죽, atVideoSec 는 r01(2.1) < r02(5.0) < r00(9.2).
  // angle_vs_reference criterion 이라 각 record 가 단일 keypoint 로 투영돼
  // 전건 번호를 받는다 — 정렬 결과에 번호를 매기면 시간순 1,2,3.
  const sorted = sortDeductionRecordsByMoment([
    rec({
      recordId: 'r00',
      criterion: 'angle_vs_reference__left_knee',
      atVideoSec: 9.2,
    }),
    rec({
      recordId: 'r01',
      criterion: 'angle_vs_reference__left_elbow',
      atVideoSec: 2.1,
    }),
    rec({
      recordId: 'r02',
      criterion: 'angle_vs_reference__left_hip',
      atVideoSec: 5.0,
    }),
  ]);
  assert.deepEqual(
    sorted.map((r) => r.recordId),
    ['r01', 'r02', 'r00'],
  );
  const { recordNumbers, keypointNumbers } = buildDeductionMarkers(
    sorted,
    undefined,
  );
  // 정렬 배열과 평행한 번호 = 시간순 1,2,3 (마커·틱·내역 행이 이 결과를 공유).
  assert.deepEqual(recordNumbers, [1, 2, 3]);
  assert.equal(keypointNumbers.left_elbow, 1); // 가장 이른 순간(2.1s) = ①
  assert.equal(keypointNumbers.left_hip, 2);
  assert.equal(keypointNumbers.left_knee, 3); // 가장 늦은 순간(9.2s) = ③
});
