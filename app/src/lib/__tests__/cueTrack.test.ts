// 재생 중 큐(D-18 자막) 순수 로직 검증 (32-08).
//
// 실행: node --test app/src/lib/__tests__/cueTrack.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행된다 — 테스트 러너/트랜스파일러
// 등 **신규 npm 의존성 0** (belle: 1,120개 의존성 이유로 테스트 러너 승인 철회,
// manualOffset.test.ts 선례). node:test / node:assert 표준 모듈 + `.ts` import 만.
//
// 검증 축 5개 (D-18 자막 큐 + D-17 확정 밀도 + belle 08-07 #3 체이닝):
//   1) buildCueWindows — startSec = userFrameIdx/userFps − windowSec/2 (0 클램프),
//      recordId 입력 승계, fps 는 인자로만(9/18 하드코딩 금지).
//   2) activeCue — 해당 구간 큐 1개 또는 null, 겹침 시 시작 늦은 큐 우선(더 정확).
//   3) 밀도 제한 — maxCues 초과 시 감점(|points|) 큰 순 상위 N개.
//   4) fps 0/NaN·프레임 인덱스 부재·빈 텍스트 → 빈 배열 (크래시 0).
//   5) nextChainedCue — 음성 자연 종료 시 +horizon 이내 미발화 큐 체이닝
//      (quick-260807-fpw, 파워스핀 0.11초 간격 끊김 해소).

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildCueWindows,
  activeCue,
  nextChainedCue,
  CUE_CHAIN_HORIZON_SEC,
} from '../cueTrack.ts';

// ── Test 1: buildCueWindows (startSec 산식 + 0 클램프 + recordId 승계) ────────

test('buildCueWindows: startSec = userFrameIdx/userFps − windowSec/2, recordId 승계', () => {
  // fps=9, windowSec=1.0. idx=18 → center=2.0, start=1.5, end=2.5.
  const out = buildCueWindows(
    [{ userFrameIdx: 18, text: '다리를 쭉 뻗어보세요', recordId: 'r00:leg_extension' }],
    9,
    1.0,
  );
  assert.equal(out.length, 1);
  assert.equal(out[0].startSec, 1.5);
  assert.equal(out[0].endSec, 2.5);
  assert.equal(out[0].text, '다리를 쭉 뻗어보세요');
  assert.equal(out[0].recordId, 'r00:leg_extension'); // 입력에서 그대로 승계

  // 0 클램프: idx=0 → center=0, start=max(0,−0.5)=0, end=0.5. recordId 부재 유지.
  const clamped = buildCueWindows([{ userFrameIdx: 0, text: 'x' }], 9, 1.0);
  assert.equal(clamped[0].startSec, 0);
  assert.equal(clamped[0].endSec, 0.5);
  assert.equal(clamped[0].recordId, undefined);
});

test('buildCueWindows: centerSec(인증 순간, atVideoSec) 우선 — fps 환산 없이 중심', () => {
  // belle 08-07 — 큐 앵커는 record 의 인증된 측정 순간(초). userFrameIdx 보다 우선.
  const out = buildCueWindows(
    [{ centerSec: 3.5, userFrameIdx: 18, text: 'x', recordId: 'r02' }],
    9,
    1.0,
  );
  assert.equal(out[0].startSec, 3.0);
  assert.equal(out[0].endSec, 4.0);
  assert.equal(out[0].recordId, 'r02');
  // 비유한/음수 centerSec 은 legacy userFrameIdx 폴백.
  const nan = buildCueWindows(
    [{ centerSec: Number.NaN, userFrameIdx: 18, text: 'x' }],
    9,
    1.0,
  );
  assert.equal(nan[0].startSec, 1.5);
  const neg = buildCueWindows([{ centerSec: -1, userFrameIdx: 18, text: 'x' }], 9, 1.0);
  assert.equal(neg[0].startSec, 1.5);
  // 둘 다 부재 → 개별 스킵 (순간을 지어내지 않는다).
  assert.equal(buildCueWindows([{ text: 'x' }], 9, 1.0).length, 0);
});

test('buildCueWindows: fps 는 인자로만 (9/18 하드코딩 금지 — 같은 인덱스라도 결과 달라짐)', () => {
  const a = buildCueWindows([{ userFrameIdx: 18, text: 'x' }], 9, 1.0);
  const b = buildCueWindows([{ userFrameIdx: 18, text: 'x' }], 18, 1.0);
  assert.equal(a[0].startSec, 1.5); // center 2.0
  assert.equal(b[0].startSec, 0.5); // center 1.0 (fps 를 인자에서 읽는다는 증거)
});

// ── Test 2: activeCue (구간 큐 1개 또는 null, 겹침 시 시작 늦은 큐 우선) ───────

test('activeCue: 해당 구간 큐 1개 또는 null, 겹침 시 시작이 늦은(더 정확한) 큐 우선', () => {
  const windows = [
    { startSec: 0, endSec: 2, text: 'A' },
    { startSec: 1, endSec: 3, text: 'B' }, // [1,2) 에서 A 와 겹침
  ];
  assert.equal(activeCue(windows, 0.5)?.text, 'A'); // A 단독
  assert.equal(activeCue(windows, 1.5)?.text, 'B'); // 겹침 → 시작 늦은 B
  assert.equal(activeCue(windows, 2.5)?.text, 'B'); // B 단독
  assert.equal(activeCue(windows, 2)?.text, 'B'); // endSec 배타 [start,end): A(0..2) 제외, B(1..3) 포함
  assert.equal(activeCue(windows, 5), null); // 구간 밖 → null
  assert.equal(activeCue(windows, NaN), null); // 비유한 → null
  assert.equal(activeCue([], 1), null); // 빈 배열 → null
});

// ── Test 3: 밀도 제한 (maxCues 초과 시 감점 큰 순 상위 N개 — D-17) ────────────

test('밀도 제한: maxCues 초과 입력 시 감점(|points|) 큰 순 상위 N개만', () => {
  const out = buildCueWindows(
    [
      { userFrameIdx: 9, text: 'small', points: -1 },
      { userFrameIdx: 18, text: 'big', points: -10 },
      { userFrameIdx: 27, text: 'mid', points: -5 },
    ],
    9,
    1.0,
    2,
  );
  assert.equal(out.length, 2);
  // small(−1) 탈락, big·mid 만 남음 (텍스트만 비교, 정렬 무관)
  assert.deepEqual(
    out.map((w) => w.text).sort(),
    ['big', 'mid'],
  );

  // maxCues 미지정 → 전부 유지
  const all = buildCueWindows(
    [
      { userFrameIdx: 9, text: 'a', points: -1 },
      { userFrameIdx: 18, text: 'b', points: -2 },
    ],
    9,
    1.0,
  );
  assert.equal(all.length, 2);

  // points 부재 = 0 우선순위 최저 (있는 쪽이 선택됨)
  const noPts = buildCueWindows(
    [
      { userFrameIdx: 9, text: 'hasPts', points: -3 },
      { userFrameIdx: 18, text: 'noPts' },
    ],
    9,
    1.0,
    1,
  );
  assert.equal(noPts.length, 1);
  assert.equal(noPts[0].text, 'hasPts');
});

// ── Test 4: 크래시 0 (fps 0/NaN·프레임 인덱스 부재·빈 텍스트·빈 입력 → []) ─────

test('buildCueWindows: fps 0/NaN/음수 → 빈 배열 (크래시 0)', () => {
  const one = [{ userFrameIdx: 9, text: 'a' }];
  assert.deepEqual(buildCueWindows(one, 0, 1.0), []);
  assert.deepEqual(buildCueWindows(one, NaN, 1.0), []);
  assert.deepEqual(buildCueWindows(one, -9, 1.0), []);
});

test('buildCueWindows: windowSec 0/NaN/음수 → 빈 배열 (크래시 0)', () => {
  const one = [{ userFrameIdx: 9, text: 'a' }];
  assert.deepEqual(buildCueWindows(one, 9, 0), []);
  assert.deepEqual(buildCueWindows(one, 9, NaN), []);
  assert.deepEqual(buildCueWindows(one, 9, -1), []);
});

test('buildCueWindows: 프레임 인덱스 부재·비정수·음수·빈 텍스트·빈 입력 → 빈 배열', () => {
  assert.deepEqual(buildCueWindows([{ userFrameIdx: -1, text: 'a' }], 9, 1.0), []);
  assert.deepEqual(buildCueWindows([{ userFrameIdx: 1.5, text: 'a' }], 9, 1.0), []);
  assert.deepEqual(buildCueWindows([{ text: 'a' } as never], 9, 1.0), []);
  assert.deepEqual(buildCueWindows([{ userFrameIdx: 9, text: '' }], 9, 1.0), []);
  assert.deepEqual(buildCueWindows([], 9, 1.0), []);
  assert.deepEqual(buildCueWindows(null, 9, 1.0), []);
  assert.deepEqual(buildCueWindows(undefined, 9, 1.0), []);
});

// ── Test 5: nextChainedCue (belle 08-07 #3 — 인접 큐 체이닝) ─────────────────

test('nextChainedCue: 파워스핀 재현 — 0.11초 간격 겹침 윈도우 2개, 첫 큐 발화 후 둘째가 체인 후보', () => {
  // CUE_WINDOW_SEC=1.6 기준 half=0.8. 큐1 center 5.00 → [4.2, 5.8),
  // 큐2 center 5.11 → [4.31, 5.91) — 윈도우가 크게 겹친다 (planner_findings 7).
  const windows = [
    { startSec: 4.2, endSec: 5.8, text: '큐1', recordId: 'r1' },
    { startSec: 4.31, endSec: 5.91, text: '큐2', recordId: 'r2' },
  ];
  // 큐1 발화 종료 시점: 멈춘 cL = 5.0 (큐1 중심 부근에서 멈춤).
  const out = nextChainedCue(windows, 5.0, new Set(['r1']), CUE_CHAIN_HORIZON_SEC);
  assert.equal(out?.recordId, 'r2'); // 같은 멈춤에서 이어 발화할 후보
});

test('nextChainedCue: horizon 밖 시작 큐는 null', () => {
  const windows = [
    { startSec: 6.5, endSec: 8.1, text: '먼 큐', recordId: 'r9' },
  ];
  // currentSec 5.0 + horizon 1.0 = 6.0 < startSec 6.5 → 후보 아님.
  assert.equal(nextChainedCue(windows, 5.0, new Set(), 1.0), null);
  // 경계: startSec == currentSec + horizon 은 포함 (<=).
  const edge = [{ startSec: 6.0, endSec: 7.6, text: '경계', recordId: 'r8' }];
  assert.equal(nextChainedCue(edge, 5.0, new Set(), 1.0)?.recordId, 'r8');
});

test('nextChainedCue: 이미 발화한 recordId 는 제외', () => {
  const windows = [
    { startSec: 4.31, endSec: 5.91, text: '큐2', recordId: 'r2' },
  ];
  assert.equal(nextChainedCue(windows, 5.0, new Set(['r2']), 1.0), null);
});

test('nextChainedCue: recordId 없는 윈도우는 제외 (조인 키 부재 = 체인 불가)', () => {
  const windows = [{ startSec: 4.31, endSec: 5.91, text: '고아 큐' }];
  assert.equal(nextChainedCue(windows, 5.0, new Set(), 1.0), null);
});

test('nextChainedCue: 후보 다수면 startSec 최소(가장 이른 것) 선택, 동률은 입력 순', () => {
  const windows = [
    { startSec: 5.4, endSec: 7.0, text: '늦은 큐', recordId: 'late' },
    { startSec: 5.2, endSec: 6.8, text: '이른 큐', recordId: 'early' },
  ];
  assert.equal(nextChainedCue(windows, 5.0, new Set(), 1.0)?.recordId, 'early');
  const tied = [
    { startSec: 5.2, endSec: 6.8, text: '동률1', recordId: 't1' },
    { startSec: 5.2, endSec: 7.0, text: '동률2', recordId: 't2' },
  ];
  assert.equal(nextChainedCue(tied, 5.0, new Set(), 1.0)?.recordId, 't1');
});

test('nextChainedCue: endSec 지난 윈도우는 제외 (이미 지나간 큐 재생 금지)', () => {
  const windows = [
    { startSec: 2.0, endSec: 4.9, text: '지난 큐', recordId: 'past' },
  ];
  // endSec 4.9 <= currentSec 5.0 → 제외.
  assert.equal(nextChainedCue(windows, 5.0, new Set(), 1.0), null);
  // 경계: endSec == currentSec 도 제외 (반개구간과 정합).
  const edge = [{ startSec: 2.0, endSec: 5.0, text: '경계', recordId: 'e' }];
  assert.equal(nextChainedCue(edge, 5.0, new Set(), 1.0), null);
});

test('nextChainedCue: 비유한 currentSec/빈 windows → null (크래시 0)', () => {
  const windows = [
    { startSec: 4.31, endSec: 5.91, text: '큐', recordId: 'r' },
  ];
  assert.equal(nextChainedCue(windows, NaN, new Set(), 1.0), null);
  assert.equal(nextChainedCue([], 5.0, new Set(), 1.0), null);
  assert.equal(nextChainedCue(null, 5.0, new Set(), 1.0), null);
  assert.equal(nextChainedCue(undefined, 5.0, new Set(), 1.0), null);
  assert.equal(nextChainedCue(windows, 5.0, new Set(), NaN), null);
});
