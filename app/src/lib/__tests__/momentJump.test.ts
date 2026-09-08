// 손가락 확대 뷰어 순간 목록(buildMomentTargets) 순수 로직 검증 (belle 09-07).
//
// 실행: node --test app/src/lib/__tests__/momentJump.test.ts
// voiceSnap.test.ts / cueTrack.test.ts 관례 — node:test / node:assert + `.ts` import,
// 신규 npm 의존성 0 (Node 의 type stripping 으로 트랜스파일 없이 실행).
//
// 검증 축:
//   1) 실 doc fixture(엘보) — 저장된 atVideoSec/refVideoSec 을 그대로 싣는다.
//      초 재계산 0 (rep↔video fps 축 혼동 = §11.8 F-3 근본원인, 엘보에서 3.78초 오차).
//   2) refVideoSec 부재 → refSec null · certified false (짝 없는 순간을 인증하지 않음).
//   3) 진입점 일치 — refSec 이 음성 큐 경로(buildRefSnapSecs)와 항상 같다
//      (mode 게이트 금지 회귀 잠금 — belle 09-07 감사 수리).
//   4) atVideoSec 부재/비유한 → 목록에서 제외 (순간 날조 0).
//   5) 중복 recordId → first-wins (결정성, buildRefSnapSecs 와 동일 규칙).
//   6) 번호가 buildDeductionTicks 와 같은 축 — 뷰어와 재생바 틱이 같은 것을 가리킨다.

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { buildMomentTargets } from '../momentJump.ts';
import {
  buildDeductionMarkers,
  buildDeductionTicks,
  matchZoomForDeductionRecord,
  sortDeductionRecordsByMoment,
} from '../deductionLabels.ts';
import { buildRefSnapSecs } from '../voiceSnap.ts';
import type {
  DeductionRecord,
  FaultZoomComparison,
} from '../../types/analysis.ts';

const HERE = import.meta.dirname; // <repo>/app/src/lib/__tests__
const REPO_ROOT = path.join(HERE, '..', '..', '..', '..'); // <repo>
// 실 분석 doc — 엘보(감점 4 · 확대카드 6). 지어낸 shape 대신 실제 계약을 검증한다.
const ELBOW_DOC = path.join(
  REPO_ROOT,
  '.planning',
  'phases',
  '35-server-rendered-comparison-video',
  'data',
  'elbow',
  'doc.json',
);

type ElbowFixture = {
  records: DeductionRecord[];
  zooms: FaultZoomComparison[];
};

// fixture 로딩 — records 는 화면(result.tsx)과 같은 순서 규약으로 시간순 정렬해 넘긴다.
function loadElbow(): ElbowFixture {
  const doc = JSON.parse(fs.readFileSync(ELBOW_DOC, 'utf8'));
  const result = doc.result;
  return {
    records: sortDeductionRecordsByMoment(
      result.deductionBreakdown.records as DeductionRecord[],
    ),
    zooms: result.faultZoomComparisons as FaultZoomComparison[],
  };
}

const rec = (fields: Partial<DeductionRecord>): DeductionRecord =>
  ({ criterion: 'angle_vs_reference__right_elbow', ...fields }) as DeductionRecord;

const zoom = (fields: Partial<FaultZoomComparison>): FaultZoomComparison =>
  ({ tier: 'confirmed', joint: 'right_elbow', ...fields }) as FaultZoomComparison;

// ── Test 1: 실 fixture — 저장값 그대로 (초 재계산 0) ─────────────────────────

test('실 doc(엘보): 저장된 atVideoSec/refVideoSec 을 그대로 싣는다 — 초 재계산 0', () => {
  const { records, zooms } = loadElbow();
  const out = buildMomentTargets(records, zooms);

  assert.equal(out.length, 4);
  assert.deepEqual(
    out.map((m) => m.recordId),
    [
      'r02:angle_vs_reference__left_hip',
      'r01:angle_vs_reference__right_shoulder',
      'r03:angle_vs_reference__right_knee',
      'r00:angle_vs_reference__right_elbow',
    ],
  );
  // userSec = record.atVideoSec, refSec = 매칭 카드의 refVideoSec — 둘 다 doc 원본값.
  assert.deepEqual(
    out.map((m) => m.userSec),
    records.map((r) => r.atVideoSec),
  );
  assert.deepEqual(
    out.map((m) => m.refSec),
    [7.0, 8.666666666666666, 16.333333333333332, 14.88888888888889],
  );
  assert.ok(out.every((m) => m.certified));

  // 두 축의 차이가 실재한다는 증거 — 엘보 record 는 user 11.111 ↔ ref 14.889.
  // 앱이 rep 인덱스로 초를 추정했다면 이 3.78초를 그대로 틀렸다 (contract.md §11.8).
  const elbow = out[3];
  assert.equal(elbow.recordId, 'r00:angle_vs_reference__right_elbow');
  assert.ok(Math.abs((elbow.refSec as number) - elbow.userSec - 3.7778) < 0.001);
});

// ── Test 2: refVideoSec 부재 → 인증하지 않는다 ──────────────────────────────

test('refVideoSec 부재(refMatched=false·legacy doc): refSec null · certified false', () => {
  const out = buildMomentTargets(
    [rec({ recordId: 'r00:angle_vs_reference__right_elbow', atVideoSec: 3.5 })],
    [zoom({ criterion: 'angle_vs_reference__right_elbow' })], // refVideoSec 없음
  );
  assert.equal(out.length, 1);
  assert.equal(out[0].userSec, 3.5); // 학생 순간은 살아있다 (카드와 무관)
  assert.equal(out[0].refSec, null);
  assert.equal(out[0].certified, false);
});

test('매칭 카드 자체가 없으면(zooms 빈 배열·null): refSec null · certified false', () => {
  const records = [
    rec({ recordId: 'r00:angle_vs_reference__right_elbow', atVideoSec: 3.5 }),
  ];
  for (const zooms of [[], null, undefined]) {
    const out = buildMomentTargets(records, zooms);
    assert.equal(out.length, 1);
    assert.equal(out[0].refSec, null);
    assert.equal(out[0].certified, false);
  }
});

// ── Test 3: 진입점 일치 — 시트와 음성 큐가 같은 오른쪽 프레임을 가리킨다 ──────
//
// belle 09-07 감사 수리의 회귀 잠금. 종전에는 여기에 "mode3 면 refSec 을 버린다"는
// 게이트가 있었고 그 게이트가 잠겨 있었다. 그런데 같은 화면의 음성 큐 경로
// (result.tsx cueRefSnapSecs → VideoCompare snapRightToCuePair)에는 mode 분기가
// 없어서, 같은 감점을 시트로 여느냐 pill 로 여느냐에 따라 오른쪽 프레임이 갈렸다.
// 이제 두 진입점이 **같은 함수(buildRefSnapSecs)의 같은 입력**을 쓴다 — 그 동형성을
// 잠근다. 누가 다시 mode 게이트를 넣으면 이 테스트가 깨진다.

test('refSec 은 음성 큐 경로(buildRefSnapSecs)와 항상 같은 값이다 — 진입점 분기 0', () => {
  const { records, zooms } = loadElbow();
  const out = buildMomentTargets(records, zooms);

  // result.tsx cueRefSnapSecs 와 **같은 방식**으로 만든 기준 초 맵 (사본이 아니라
  // 같은 함수를 같은 입력으로 부른 것).
  const cueMap = buildRefSnapSecs(
    records.map((rec) => ({
      recordId: rec.recordId,
      refVideoSec: matchZoomForDeductionRecord(rec, undefined, zooms)
        ?.refVideoSec,
    })),
  );

  assert.ok(out.length > 0, '엘보 fixture 가 순간을 하나도 안 냈다');
  for (const m of out) {
    const cueSec = Object.prototype.hasOwnProperty.call(cueMap, m.recordId)
      ? cueMap[m.recordId]
      : null;
    assert.equal(
      m.refSec,
      cueSec,
      `${m.recordId}: 시트 경로 refSec 과 음성 큐 경로가 갈라졌다`,
    );
    assert.equal(m.certified, cueSec != null);
  }
});

test('카드가 refVideoSec 을 들고 있으면 인증한다 — mode 로 버리지 않는다', () => {
  const records = [
    rec({ recordId: 'r00:angle_vs_reference__right_elbow', atVideoSec: 3.5 }),
  ];
  const zooms = [
    zoom({ criterion: 'angle_vs_reference__right_elbow', refVideoSec: 9.25 }),
  ];
  const out = buildMomentTargets(records, zooms);
  assert.equal(out.length, 1);
  assert.equal(out[0].userSec, 3.5);
  assert.deepEqual(
    [out[0].refSec, out[0].certified],
    [9.25, true],
    'mode3(본인 영상 2개) 도 오른쪽 패널이 지난 영상이라 짝이 실재한다',
  );
});

// ── Test 4: atVideoSec 없는 record 제외 (fabricate 0) ───────────────────────

test('atVideoSec 부재/비유한/음수 record 는 목록에서 제외한다 (순간 날조 0)', () => {
  const out = buildMomentTargets(
    [
      rec({ recordId: 'r00:angle_vs_reference__right_elbow' }), // 부재 — reach·fallback·legacy
      rec({
        recordId: 'r01:angle_vs_reference__right_shoulder',
        atVideoSec: Number.NaN,
      }),
      rec({
        recordId: 'r02:angle_vs_reference__left_hip',
        atVideoSec: Number.POSITIVE_INFINITY,
      }),
      rec({
        recordId: 'r03:angle_vs_reference__right_knee',
        atVideoSec: -1,
      }),
      rec({
        recordId: 'r04:angle_vs_reference__left_knee',
        criterion: 'angle_vs_reference__left_knee',
        atVideoSec: 0, // 0초(영상 시작)는 유효
      }),
    ],
    [],
  );
  assert.deepEqual(
    out.map((m) => m.recordId),
    ['r04:angle_vs_reference__left_knee'],
  );
  assert.equal(out[0].userSec, 0);
});

test('recordId 부재/빈 문자열 record 는 제외한다 (조인 키 없는 순간 금지)', () => {
  const out = buildMomentTargets(
    [
      rec({ atVideoSec: 1.0 }), // recordId 부재 (legacy doc)
      rec({
        recordId: '',
        criterion: 'angle_vs_reference__right_shoulder',
        atVideoSec: 2.0,
      }),
      rec({
        recordId: 'r02:angle_vs_reference__left_hip',
        criterion: 'angle_vs_reference__left_hip',
        atVideoSec: 3.0,
      }),
    ],
    [],
  );
  assert.deepEqual(
    out.map((m) => m.recordId),
    ['r02:angle_vs_reference__left_hip'],
  );
});

// ── Test 5: 중복 recordId first-wins ────────────────────────────────────────

test('중복 recordId 는 first-wins (결정성)', () => {
  const out = buildMomentTargets(
    [
      rec({ recordId: 'dup', atVideoSec: 1.5 }),
      rec({
        recordId: 'dup',
        criterion: 'angle_vs_reference__left_hip',
        atVideoSec: 8.5,
      }),
    ],
    [],
  );
  assert.equal(out.length, 1);
  assert.equal(out[0].userSec, 1.5);
});

// ── Test 6: 번호 축 일치 — 뷰어와 재생바 틱이 같은 것을 가리킨다 ────────────

test('번호가 buildDeductionTicks 와 일치한다 (실 doc 엘보, 같은 입력 배열)', () => {
  const { records, zooms } = loadElbow();
  const { recordNumbers } = buildDeductionMarkers([...records], undefined);
  const ticks = buildDeductionTicks(records, recordNumbers, null);
  const out = buildMomentTargets(records, zooms);

  // 번호 → 그 번호를 실은 틱의 frameIndex.
  const frameOfNumber = new Map<number, number>();
  for (const t of ticks) {
    for (const n of t.numbers) frameOfNumber.set(n, t.frameIndex);
  }
  assert.equal(frameOfNumber.size, out.length);

  const recordById = new Map(records.map((r) => [r.recordId as string, r]));
  for (const m of out) {
    // 같은 번호의 틱이 존재하고, 그 틱의 frame 이 이 record 의 측정 프레임이다.
    assert.equal(
      frameOfNumber.get(m.number),
      recordById.get(m.recordId)?.atFrameIdx,
      `번호 ${m.number} 의 틱 frame 이 record 측정 프레임과 달라졌다`,
    );
  }
  // 시간순 정렬 입력 → 번호도 1..N 시간순 (belle 08-07 #1 규약 유지 확인).
  assert.deepEqual(
    out.map((m) => m.number),
    [1, 2, 3, 4],
  );
});

// ── Test 7: 방어 입력 ───────────────────────────────────────────────────────

test('records null/undefined/빈 배열 — 빈 목록 (크래시 0)', () => {
  assert.deepEqual(buildMomentTargets(null, []), []);
  assert.deepEqual(buildMomentTargets(undefined, []), []);
  assert.deepEqual(buildMomentTargets([], []), []);
});
