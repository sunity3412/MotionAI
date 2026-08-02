// 부위 단위 감점 상세 시트 뷰모델 검증 (quick-260730-py1 Task 1 — 33-G S6/S7).
//
// 실행: node --test app/src/lib/__tests__/deductionSheet.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (resultSections.test.ts / summarySource.test.ts 선례). node:test / node:assert
// 표준 모듈 + `.ts` 확장자 import 만.
//
// 왜 이 테스트가 존재하나: 시트 조판은 "부위에 감점 2건이면 시트 1개·블록 2개"
// 같은 **구조 규칙**과 "데이터 없으면 문구를 만들지 않는다"는 **fail-closed 규칙**의
// 합이다. 둘 다 typecheck 로 보증되지 않고, 컴포넌트에 붙은 채로는 렌더 환경 없이
// 검증할 수 없다. 조판을 순수 함수로 격리해 여기서 고정한다.
//
// 검증 축 (플랜 behavior 12축 + 위협 T-33G2-01/02):
//   1) 부위 그룹핑 — hip+knee → leg 1그룹 2블록 / shoulder 는 별 그룹
//   2) 투영 공집합(line·dimension_overall_fallback) → criterion 단독 그룹
//   3) 번호 헤더 — 2건 그룹은 전역 recordNumbers 값, 1건 그룹은 번호 절 없음
//   4) estimatedArea — 번호 억제 + numNote IN-01 안내
//   5) 블록 순서 — 그룹 크롭을 낳은 record 가 첫 블록
//   6) paircap — 좌 '내 자세 · 실 N초' / 우 라벨 + 초, refVideoSec 부재 시 초 생략
//   7) method — vision / geometry+reference_relative / ipsf_absolute(null)
//   8) basis — 초 보유·부재·{무엇} 미상 3분기
//   9) facing — reference_relative + 두 초 상이일 때만
//  10) onecap — 각도 의미 문구 / advisory 승인 원문 / 마킹 기하 단정 0
//  11) proof 필드 부재 (M-10 fail-closed — 빈 배열조차 두지 않는다)
//  12) 방어 — records 빈 배열·index 범위 밖·zoom 전무에서 null/크래시 0
//  13) T-33G2-01 — 방출 문자열에 HTML 마크업(`<`/`>`) 0
//
// quick-260730-szk 증축 (33-G S1/S2/S3):
//  15) partGroups — 부위 단위 그룹 1개 + 번호 오름차순 병합 배지(N-2) + 투영 누락 0
//  16) buildPartChips — 감점 칩 순서·라벨 동일성, advisory 칩, cleanPass·저신뢰 0
//  17) 참고 문형 상수 2종 단일 소스 (T-33G3-02)

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ADVISORY_CHIP_KO,
  ADVISORY_NOTE_KO,
  buildCauseGroupKeys,
  buildPartChips,
  buildPartGroups,
  buildRegionSheetView,
  composeCueSubtitleKo,
  formatVideoSecKo,
  partLabelKo,
  regionPartKeyForRecord,
  splitGoalClause,
  type RegionSheetInput,
} from '../deductionSheet.ts';
import { projectDeductionRecordKeypoints } from '../deductionLabels.ts';

// ── 픽스처 ────────────────────────────────────────────────────────────────
// 저장값만 사용 (앱 재계산 0). points 는 SIGNED NEGATIVE 계약.

type Rec = RegionSheetInput['records'][number];

function rec(over: Partial<Rec> & { criterion: string }): Rec {
  return {
    criterion: over.criterion,
    measuredValue: over.measuredValue ?? 30,
    baselineValue: over.baselineValue ?? 0,
    baselineKind: null,
    deviation: over.deviation ?? 10,
    ruleId: over.ruleId ?? 'r1',
    points: over.points ?? -12,
    unit: over.unit ?? 'deg',
    ipsfAnchor: 'anchor',
    source: over.source ?? 'geometry',
    deviationSource: over.deviationSource ?? 'reference_relative',
    statusLine: over.statusLine,
    whyLine: over.whyLine,
    cueLine: over.cueLine,
    // quick-260802-mrg — 표시 병합 키 (부재 = legacy doc).
    exerciseId: over.exerciseId,
    // quick-260801-gbk — 이 감점을 잰 순간 (basis 절의 초 출처).
    atFrameIdx: over.atFrameIdx,
    atVideoSec: over.atVideoSec,
  } as Rec;
}

type Zoom = NonNullable<RegionSheetInput['zooms'][number]>;

function zoom(over: Partial<Zoom> & { imageUrl: string }): Zoom {
  return {
    joint: over.joint ?? 'left_hip',
    imageUrl: over.imageUrl,
    criterion: over.criterion,
    tier: over.tier ?? 'confirmed',
    userVideoSec: over.userVideoSec,
    refVideoSec: over.refVideoSec,
    // quick-260801-gbk — 표시 프레임 == 측정 프레임 인증 (백엔드 방출).
    atMatched: over.atMatched,
  } as Zoom;
}

const RIGHT_LABEL = '기준 (정은지)';

// 승인 목업 ② 다리 케이스 재현 — 벌림(vision, 크롭 보유) + 무릎(geometry ipsf).
const LEGS_RECORDS = [
  rec({
    criterion: 'leg_extension',
    source: 'geometry',
    deviationSource: 'ipsf_absolute',
    measuredValue: 141,
    baselineValue: 180,
    deviation: 19,
    points: -20,
    statusLine: '무릎이 기준보다 덜 펴져 있어요',
    whyLine: '줄이 끊겨서 감점돼요',
    cueLine: '두 무릎을 끝까지 편 채 버텨보세요',
  }),
  rec({
    criterion: 'split_angle',
    source: 'vision',
    deviationSource: 'ipsf_absolute',
    measuredValue: 130,
    deviation: 30,
    points: -12,
    statusLine: '다리를 벌린 각도가 기준보다 좁아요',
  }),
];

// 벌림(index 1)이 크롭을 낳았다 — 블록 순서는 벌림 먼저 (M-5).
const LEGS_ZOOMS = [
  null,
  zoom({
    imageUrl: 'https://s3/legs.png',
    criterion: 'split_angle',
    userVideoSec: 1.74,
    refVideoSec: 4.5,
  }),
];

function legsInput(over: Partial<RegionSheetInput> = {}): RegionSheetInput {
  return {
    records: LEGS_RECORDS,
    recordNumbers: [2, 1],
    actionPhrases: [null, null],
    zooms: LEGS_ZOOMS,
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
    faultJoints: ['left_hip', 'right_hip', 'left_knee', 'right_knee'],
    ...over,
  };
}

// ── Test 1: 부위 그룹핑 ───────────────────────────────────────────────────
test('Test 1 (그룹핑): hip+knee record 2건 → leg 그룹 1개·블록 2개, shoulder 는 별 그룹', () => {
  const records = [
    rec({ criterion: 'angle_vs_reference__left_hip' }),
    rec({ criterion: 'angle_vs_reference__left_knee' }),
    rec({ criterion: 'angle_vs_reference__left_shoulder' }),
  ];
  assert.equal(regionPartKeyForRecord(records[0], undefined), 'leg');
  assert.equal(regionPartKeyForRecord(records[1], undefined), 'leg');
  assert.equal(regionPartKeyForRecord(records[2], undefined), 'shoulder');

  const base: RegionSheetInput = {
    records,
    recordNumbers: [1, 2, 3],
    actionPhrases: [null, null, null],
    zooms: [null, null, null],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  };
  const leg = buildRegionSheetView(base);
  assert.ok(leg);
  assert.equal(leg.partKey, 'leg');
  assert.equal(leg.title, '다리');
  assert.equal(leg.blocks.length, 2);
  assert.deepEqual(
    leg.blocks.map((b) => b.recordIndex),
    [0, 1],
  );

  const shoulder = buildRegionSheetView({ ...base, selectedRecordIndex: 2 });
  assert.ok(shoulder);
  assert.equal(shoulder.partKey, 'shoulder');
  assert.equal(shoulder.title, '어깨');
  assert.equal(shoulder.blocks.length, 1);
});

// 좌우 미분할 (승인본 '다리' = hips+knees 통합).
test('Test 1b (그룹핑): 좌우는 같은 부위로 합친다 (승인본 다리 그룹)', () => {
  const records = [
    rec({ criterion: 'angle_vs_reference__left_knee' }),
    rec({ criterion: 'angle_vs_reference__right_knee' }),
  ];
  const view = buildRegionSheetView({
    records,
    recordNumbers: [1, 2],
    actionPhrases: [null, null],
    zooms: [null, null],
    selectedRecordIndex: 1,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(view);
  assert.equal(view.blocks.length, 2);
});

// ── Test 2: 투영 공집합 → criterion 단독 그룹 ─────────────────────────────
test('Test 2 (투영 공집합): line·dimension_overall_fallback → criterion 단독 그룹, 제목 = criterionLabelKo', () => {
  const records = [
    rec({ criterion: 'line' }),
    rec({
      criterion: 'dimension_overall_fallback',
      unit: 'score_delta',
      deviationSource: 'dimension_overall',
    }),
    rec({ criterion: 'angle_vs_reference__left_knee' }),
  ];
  const base: RegionSheetInput = {
    records,
    recordNumbers: [1, 2, 3],
    actionPhrases: [null, null, null],
    zooms: [null, null, null],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  };
  const lineView = buildRegionSheetView(base);
  assert.ok(lineView);
  assert.equal(lineView.partKey, 'criterion:line');
  assert.equal(lineView.title, '바디 라인');
  assert.equal(lineView.blocks.length, 1);

  const fbView = buildRegionSheetView({ ...base, selectedRecordIndex: 1 });
  assert.ok(fbView);
  assert.equal(fbView.partKey, 'criterion:dimension_overall_fallback');
  assert.equal(fbView.blocks.length, 1);
  // 두 criterion 그룹이 서로 섞이지 않는다.
  assert.notEqual(lineView.partKey, fbView.partKey);
});

// ── Test 3: 번호 헤더 ─────────────────────────────────────────────────────
test('Test 3 (번호 헤더): 2건 그룹 = 전역 recordNumbers 값 / 1건 그룹 = 번호 절 없음', () => {
  const view = buildRegionSheetView(legsInput());
  assert.ok(view);
  // 블록 순서 = 크롭 record(index 1, 번호 1) 먼저.
  assert.deepEqual(
    view.blocks.map((b) => b.header),
    ['고칠 것 1 — 다리 스플릿 각도 (−12점)', '고칠 것 2 — 다리 펴기 (−20점)'],
  );

  const solo = buildRegionSheetView({
    records: [rec({ criterion: 'angle_vs_reference__left_shoulder', points: -17.4 })],
    recordNumbers: [3],
    actionPhrases: [null],
    zooms: [null],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(solo);
  assert.equal(
    solo.blocks[0].header,
    '고칠 것 — 왼쪽 어깨(정은지 대비 각도) (−17.4점)',
  );
});

test('Test 3b (번호 헤더): recordNumbers 값이 null 이면 번호 없이 렌더 (fabricate 0)', () => {
  const view = buildRegionSheetView(legsInput({ recordNumbers: [null, null] }));
  assert.ok(view);
  for (const b of view.blocks) {
    assert.ok(b.header.startsWith('고칠 것 — '), b.header);
  }
});

// ── Test 4: estimatedArea (IN-01) ─────────────────────────────────────────
test('Test 4 (estimatedArea): 번호 억제 + numNote = 관절별 수치 대신 IN-01 안내', () => {
  const view = buildRegionSheetView(legsInput({ estimatedArea: true }));
  assert.ok(view);
  for (const b of view.blocks) {
    assert.ok(b.header.startsWith('고칠 것 — '), b.header);
    assert.equal(b.numNote, '이 부위는 추정이라 관절별 감점 수치는 종합 점수로만 반영돼요');
    assert.ok(!/\d+°/.test(b.numNote ?? ''), '수치 노출 금지');
  }
});

// ── Test 5: 블록 순서 (M-5) ───────────────────────────────────────────────
test('Test 5 (블록 순서): 그룹 크롭을 낳은 record 가 첫 블록, 나머지는 저장순', () => {
  const view = buildRegionSheetView(legsInput());
  assert.ok(view);
  assert.equal(view.primaryRecordIndex, 1);
  assert.deepEqual(
    view.blocks.map((b) => b.recordIndex),
    [1, 0],
  );
  // primary 블록은 자기 크롭을 블록 안에 중복 렌더하지 않는다.
  assert.equal(view.blocks[0].blockRecordIndexForCrop, null);
  // 크롭 없는 두 번째 record 도 블록 안 크롭 없음.
  assert.equal(view.blocks[1].blockRecordIndexForCrop, null);
});

test('Test 5b (블록 크롭): 다른 카드를 가진 두 번째 record 는 그 크롭을 블록 안에 렌더', () => {
  const view = buildRegionSheetView(
    legsInput({
      zooms: [
        zoom({ imageUrl: 'https://s3/knee.png', criterion: 'leg_extension' }),
        LEGS_ZOOMS[1],
      ],
    }),
  );
  assert.ok(view);
  // 저장순 첫 매치 = index 0 (크롭 보유) → primary.
  assert.equal(view.primaryRecordIndex, 0);
  assert.deepEqual(
    view.blocks.map((b) => b.recordIndex),
    [0, 1],
  );
  assert.equal(view.blocks[0].blockRecordIndexForCrop, null);
  assert.equal(view.blocks[1].blockRecordIndexForCrop, 1);
});

// ── Test 6: paircap (M-2) ─────────────────────────────────────────────────
test('Test 6 (paircap): 좌 = 내 자세 · 실 N초 / 우 = 라벨 · 실 N초 (toFixed(1))', () => {
  const view = buildRegionSheetView(legsInput());
  assert.ok(view);
  assert.equal(view.pairCapLeft, '내 자세 · 실 1.7초');
  assert.equal(view.pairCapRight, '기준 (정은지) · 실 4.5초');
});

test('Test 6b (paircap): refVideoSec 부재 → 우측 초 절 생략 (라벨만)', () => {
  const view = buildRegionSheetView(
    legsInput({
      zooms: [
        null,
        zoom({ imageUrl: 'https://s3/legs.png', criterion: 'split_angle', userVideoSec: 1.74 }),
      ],
    }),
  );
  assert.ok(view);
  assert.equal(view.pairCapLeft, '내 자세 · 실 1.7초');
  assert.equal(view.pairCapRight, '기준 (정은지)');
});

test('Test 6c (paircap): zoom 전무 → paircap/onecap null (fabricate 0)', () => {
  const view = buildRegionSheetView(legsInput({ zooms: [null, null] }));
  assert.ok(view);
  assert.equal(view.pairCapLeft, null);
  assert.equal(view.pairCapRight, null);
  assert.equal(view.oneCap, null);
  assert.equal(view.facingLine, null);
});

test('Test 6d (formatVideoSecKo): 유한 0 이상만 초 라벨, 그 외 null', () => {
  assert.equal(formatVideoSecKo(1.74), '실 1.7초');
  assert.equal(formatVideoSecKo(3.07), '실 3.1초');
  assert.equal(formatVideoSecKo(0), '실 0.0초');
  assert.equal(formatVideoSecKo(-1), null);
  assert.equal(formatVideoSecKo(Number.NaN), null);
  assert.equal(formatVideoSecKo(Number.POSITIVE_INFINITY), null);
  assert.equal(formatVideoSecKo(undefined), null);
  assert.equal(formatVideoSecKo(null), null);
});

// ── Test 7: method (M-8) ──────────────────────────────────────────────────
test('Test 7 (method): vision → 시각 판단 문형 / geometry+reference_relative → 정렬 문형 / ipsf_absolute → null', () => {
  const records = [
    rec({ criterion: 'split_angle', source: 'vision', deviationSource: 'ipsf_absolute' }),
    rec({
      criterion: 'angle_vs_reference__left_hip',
      source: 'geometry',
      deviationSource: 'reference_relative',
    }),
    rec({
      criterion: 'leg_extension',
      source: 'geometry',
      deviationSource: 'ipsf_absolute',
    }),
  ];
  const view = buildRegionSheetView({
    records,
    recordNumbers: [1, 2, 3],
    actionPhrases: [null, null, null],
    zooms: [
      null,
      zoom({
        imageUrl: 'https://s3/hip.png',
        criterion: 'angle_vs_reference__left_hip',
        userVideoSec: 1.74,
        refVideoSec: 3.07,
      }),
      null,
    ],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
    faultJoints: ['left_hip', 'right_hip', 'left_knee', 'right_knee'],
  });
  assert.ok(view);
  const byIdx = new Map(view.blocks.map((b) => [b.recordIndex, b]));
  assert.equal(
    byIdx.get(0)?.methodLine,
    '측정 방법 — 이 항목은 특정 순간을 잰 프레임 측정이 아니라, 두 영상 전체를 견준 AI 시각 판단이에요.',
  );
  assert.equal(
    byIdx.get(1)?.methodLine,
    '측정 방법 — 이 항목은 한 순간이 아니라 두 영상의 전 구간을 정렬해 견준 값이에요. 기준 사진은 그 정렬이 실제로 짝지은 순간(기준 실 3.1초)이에요.',
  );
  assert.equal(byIdx.get(2)?.methodLine, null);
});

test('Test 7b (method): 정렬 문형 + refVideoSec 부재 → 두 번째 문장 생략', () => {
  const view = buildRegionSheetView({
    records: [
      rec({
        criterion: 'angle_vs_reference__left_hip',
        source: 'geometry',
        deviationSource: 'reference_relative',
      }),
    ],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [zoom({ imageUrl: 'https://s3/hip.png', userVideoSec: 1.74 })],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(view);
  assert.equal(
    view.blocks[0].methodLine,
    '측정 방법 — 이 항목은 한 순간이 아니라 두 영상의 전 구간을 정렬해 견준 값이에요.',
  );
});

// ── Test 8: basis (M-7) ───────────────────────────────────────────────────
test('Test 8 (basis): 초 보유 → 두 문장 / 초 부재 → 뒷문장 생략 / {무엇} 미상 → 항목 지칭', () => {
  // quick-260801-gbk — 초 출처는 rec.atVideoSec, 방출 조건은 zoom.atMatched.
  // 문장 자체는 승인본 그대로 불변이고 출처·조건만 바뀌었다.
  const withSec = buildRegionSheetView({
    records: [
      rec({
        criterion: 'angle_vs_reference__left_shoulder',
        atFrameIdx: 16,
        atVideoSec: 1.74,
      }),
    ],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [
      zoom({
        imageUrl: 'https://s3/sh.png',
        criterion: 'angle_vs_reference__left_shoulder',
        userVideoSec: 1.74,
        refVideoSec: 3.07,
        atMatched: true,
      }),
    ],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(withSec);
  const segs = withSec.blocks[0].basisLine;
  assert.ok(segs);
  assert.equal(segs[0].text, '어디서 재나요:');
  assert.equal(segs[0].bold, true);
  const joined = segs.map((s) => s.text).join('');
  assert.equal(
    joined,
    '어디서 재나요: 이 항목은 겨드랑이 벌림을 재요. 위 사진은 그 값을 잰 순간(실 1.7초)이에요.',
  );

  const noSec = buildRegionSheetView({
    records: [rec({ criterion: 'angle_vs_reference__left_shoulder' })],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [null],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(noSec);
  assert.equal(
    noSec.blocks[0].basisLine?.map((s) => s.text).join(''),
    '어디서 재나요: 이 항목은 겨드랑이 벌림을 재요.',
  );
  // 사진·초를 지칭하는 절이 없어야 한다 (zoom 부재 fail-closed).
  assert.ok(!(noSec.blocks[0].basisLine ?? []).some((s) => s.text.includes('초')));

  // {무엇} 미상 + 초 부재 → basis 자체 생략.
  const unknown = buildRegionSheetView({
    records: [rec({ criterion: 'dimension_overall_fallback', unit: 'score_delta' })],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [null],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(unknown);
  assert.equal(unknown.blocks[0].basisLine, null);
});

// ── Test 9: facing (M-9) ──────────────────────────────────────────────────
test('Test 9 (facing): reference_relative + 두 초 상이 → 문장, ipsf-only → null', () => {
  const refRel = buildRegionSheetView({
    records: [
      rec({
        criterion: 'angle_vs_reference__left_shoulder',
        deviationSource: 'reference_relative',
        points: -17.4,
      }),
    ],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [
      zoom({
        imageUrl: 'https://s3/sh.png',
        criterion: 'angle_vs_reference__left_shoulder',
        userVideoSec: 1.74,
        refVideoSec: 3.07,
      }),
    ],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(refRel);
  assert.equal(
    refRel.facingLine,
    '두 사진이 달라 보이는 이유 — 두 장면은 같은 동작의 서로 다른 순간이에요(내 1.7초 ↔ 기준 3.1초). 분석이 같은 구간으로 짝지은 순간이라, 몸 방향이 달라 보여도 어깨 각도만 견줘 보세요.',
  );

  // 승인본 다리 그룹 = vision + ipsf_absolute → facing 없음.
  const legs = buildRegionSheetView(
    legsInput({
      records: LEGS_RECORDS.map((r) => ({ ...r, deviationSource: 'ipsf_absolute' })) as
        typeof LEGS_RECORDS,
    }),
  );
  assert.ok(legs);
  assert.equal(legs.facingLine, null);
});

test('Test 9b (facing): 두 초가 같은 순간이면 생략', () => {
  const view = buildRegionSheetView({
    records: [rec({ criterion: 'angle_vs_reference__left_shoulder' })],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [
      zoom({
        imageUrl: 'https://s3/sh.png',
        userVideoSec: 1.7,
        refVideoSec: 1.72,
      }),
    ],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(view);
  assert.equal(view.facingLine, null);
});

// ── Test 10: onecap (M-6) ─────────────────────────────────────────────────
test('Test 10 (onecap): 각도 의미 문구 + 마킹 기하 단정 0', () => {
  const view = buildRegionSheetView({
    records: [rec({ criterion: 'angle_vs_reference__left_shoulder' })],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [
      zoom({
        imageUrl: 'https://s3/sh.png',
        criterion: 'angle_vs_reference__left_shoulder',
        userVideoSec: 1.74,
      }),
    ],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(view);
  assert.equal(view.oneCap, '이 사진은 겨드랑이 벌림을 기준 자세와 견줘요');
  // 마킹 기하(빨간 두 줄 / 꼭짓점)를 단정하지 않는다 — 대부분 카드에서 거짓 지칭.
  for (const forbidden of ['빨간', '두 줄', '꼭짓점', '겨드랑이 중심']) {
    assert.ok(!view.oneCap.includes(forbidden), forbidden);
  }
});

test('Test 10b (onecap): split_angle → 두 다리를 벌린 정도', () => {
  const view = buildRegionSheetView(legsInput({ selectedRecordIndex: 1 }));
  assert.ok(view);
  assert.equal(view.oneCap, '이 사진은 두 다리를 벌린 정도를 기준 자세와 견줘요');
});

test('Test 10c (onecap): advisory 카드 → 승인 원문 유지', () => {
  const view = buildRegionSheetView({
    records: [rec({ criterion: 'angle_vs_reference__left_hand' })],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [zoom({ imageUrl: 'https://s3/adv.png', tier: 'advisory', userVideoSec: 1.74 })],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(view);
  assert.equal(view.isAdvisoryOnly, true);
  assert.equal(
    view.oneCap,
    '참고 부위예요 — 점수 감점은 되지 않지만 회전·힘 같은 전체 동작에 영향을 줄 수 있어요. 눈에 띈 차이만 보여드려요',
  );
});

// ── Test 11: proof 부재 (M-10) ────────────────────────────────────────────
test('Test 11 (proof): 뷰모델에 proof 필드가 없다 (빈 배열조차 두지 않는다)', () => {
  const view = buildRegionSheetView(legsInput());
  assert.ok(view);
  for (const b of view.blocks) {
    assert.ok(!('proof' in b), 'proof 자리 금지 — 백엔드 3컷 방출 전까지 fail-closed');
    assert.ok(!('proofRow' in b));
  }
});

// ── Test 12: 방어 ─────────────────────────────────────────────────────────
test('Test 12 (방어): records 빈 배열 / index 범위 밖 / null → null 반환 (크래시 0)', () => {
  const empty: RegionSheetInput = {
    records: [],
    recordNumbers: [],
    actionPhrases: [],
    zooms: [],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  };
  assert.equal(buildRegionSheetView(empty), null);
  assert.equal(buildRegionSheetView(legsInput({ selectedRecordIndex: null })), null);
  assert.equal(buildRegionSheetView(legsInput({ selectedRecordIndex: 99 })), null);
  assert.equal(buildRegionSheetView(legsInput({ selectedRecordIndex: -1 })), null);
  assert.equal(buildRegionSheetView(legsInput({ selectedRecordIndex: 1.5 })), null);
  // 배열 길이 불일치(번호·행동구·zoom 부족)에서도 크래시 0.
  const view = buildRegionSheetView(
    legsInput({ recordNumbers: [], actionPhrases: [], zooms: [] }),
  );
  assert.ok(view);
  assert.equal(view.blocks.length, 2);
});

test('Test 12b (방어): cueLine 부재 시 actionPhrases 폴백', () => {
  const view = buildRegionSheetView(
    legsInput({ actionPhrases: ['무릎 더 펴기', '다리 더 벌리기'] }),
  );
  assert.ok(view);
  const byIdx = new Map(view.blocks.map((b) => [b.recordIndex, b]));
  // index 0 은 record.cueLine 보유 → record 값이 이긴다.
  assert.equal(byIdx.get(0)?.cueLine, '두 무릎을 끝까지 편 채 버텨보세요');
  // index 1 은 cueLine 부재 → actionPhrases 폴백.
  assert.equal(byIdx.get(1)?.cueLine, '다리 더 벌리기');
});

// ── Test 13: T-33G2-01 HTML 마크업 금지 ───────────────────────────────────
test('Test 13 (T-33G2-01): 방출 문자열에 HTML 태그 문자(`<`/`>`) 0', () => {
  const views = [
    buildRegionSheetView(legsInput()),
    buildRegionSheetView(legsInput({ selectedRecordIndex: 1 })),
    buildRegionSheetView(legsInput({ estimatedArea: true })),
  ];
  for (const view of views) {
    assert.ok(view);
    const strings: string[] = [
      view.title,
      view.pairCapLeft ?? '',
      view.pairCapRight ?? '',
      view.oneCap ?? '',
      view.facingLine ?? '',
    ];
    for (const b of view.blocks) {
      strings.push(
        b.header,
        b.statusLine ?? '',
        b.whyLine ?? '',
        b.cueLine ?? '',
        b.methodLine ?? '',
        b.numNote ?? '',
        ...(b.basisLine ?? []).map((s) => s.text),
      );
    }
    for (const s of strings) {
      assert.ok(!s.includes('<'), s);
      assert.ok(!s.includes('>'), s);
    }
  }
});

// ── Test 14: numNote (M-13 수치 강등) ─────────────────────────────────────
test('Test 14 (numNote): 승인 문두 + 저장값 그대로 + 감점 (formatDeductionRecord 재사용)', () => {
  const view = buildRegionSheetView(legsInput());
  assert.ok(view);
  const byIdx = new Map(view.blocks.map((b) => [b.recordIndex, b]));
  assert.equal(
    byIdx.get(0)?.numNote,
    '측정 수치(참고) — 측정 141° (기준 180°, 허용 초과 19°) → −20점',
  );
  assert.equal(
    byIdx.get(1)?.numNote,
    '측정 수치(참고) — 측정 130° (기준 0°, 허용 초과 30°) (영상 비교 측정) → −12점',
  );
});

// ══════════════════════════════════════════════════════════════════════════
// quick-260730-szk (33-G S1/S2/S3) — 부위 그룹 마커 · 부위 칩 · 참고 문형 단일화
// ══════════════════════════════════════════════════════════════════════════

// 승인 목업 ① 어깨 그룹 재현 — 한 부위에 감점 2건(좌·우 어깨). 1라운드가 관절 원
// 2개를 나열했던 것이 2R#1 "동그라미가 7개" 반려의 실체다 → 그룹 1개 + 병합 배지.
const SHOULDER_PAIR = [
  rec({ criterion: 'angle_vs_reference__left_elbow', points: -6 }),
  rec({ criterion: 'angle_vs_reference__left_shoulder', points: -8.9 }),
  rec({ criterion: 'angle_vs_reference__right_shoulder', points: -5.1 }),
];

// ── Test 15: partGroups 병합 배지 (N-2) ───────────────────────────────────
test('Test 15 (partGroups): 어깨 좌+우 2 record → 그룹 1개, numbers 오름차순, badgeLabel 2·3', () => {
  const groups = buildPartGroups(SHOULDER_PAIR, [1, 2, 3], undefined);
  const shoulder = groups.filter((g) => g.partKey === 'shoulder');
  assert.equal(shoulder.length, 1, '어깨 그룹이 1개가 아니다 (관절 원 나열 = 2R#1 위반)');
  assert.deepEqual(shoulder[0].numbers, [2, 3]);
  assert.equal(shoulder[0].badgeLabel, '2·3');
  // 팔(팔꿈치)은 별 그룹 — 부위가 다르면 합치지 않는다.
  const arm = groups.filter((g) => g.partKey === 'arm');
  assert.equal(arm.length, 1);
  assert.equal(arm[0].badgeLabel, '1');
});

test('Test 15b (partGroups): 감점 1건 부위 → badgeLabel 이 단일 숫자', () => {
  const groups = buildPartGroups(
    [rec({ criterion: 'angle_vs_reference__left_knee' })],
    [4],
    undefined,
  );
  assert.equal(groups.length, 1);
  assert.equal(groups[0].partKey, 'leg');
  assert.equal(groups[0].badgeLabel, '4');
  assert.deepEqual(groups[0].numbers, [4]);
});

test('Test 15c (partGroups): keypoints 합집합 == 부위 멤버 record 투영 합집합 (누락 0)', () => {
  const faultJoints = ['left_hip', 'right_hip', 'left_knee', 'right_knee'] as const;
  const records = [...LEGS_RECORDS, ...SHOULDER_PAIR];
  const numbers = records.map((_, i) => i + 1);
  const groups = buildPartGroups(records, numbers, faultJoints);
  for (const g of groups) {
    const expected = new Set<string>();
    records.forEach((r) => {
      if (regionPartKeyForRecord(r, faultJoints) !== g.partKey) return;
      for (const kp of projectDeductionRecordKeypoints(r, faultJoints)) {
        expected.add(kp);
      }
    });
    assert.deepEqual(
      [...g.keypoints].sort(),
      [...expected].sort(),
      `${g.partKey} 투영 누락/여분`,
    );
  }
});

test('Test 15d (partGroups): 번호 없는 부위·투영 0인 부위는 그룹에서 제외 (고아 경계 0)', () => {
  // line = 투영 공집합 → 그릴 자리 없음. numbers null = 번호 없는 경계.
  const groups = buildPartGroups(
    [
      rec({ criterion: 'line' }),
      rec({ criterion: 'angle_vs_reference__left_knee' }),
    ],
    [1, null],
    undefined,
  );
  assert.deepEqual(groups, []);
});

// ── Test 16: buildPartChips (S3 부위 칩) ──────────────────────────────────
test('Test 16 (칩): 감점 칩 순서 = 첫 등장 순, 라벨 = 부위 시트 제목과 문자 동일', () => {
  const chips = buildPartChips({
    records: SHOULDER_PAIR,
    recordNumbers: [1, 2, 3],
    attentionKeypoints: [],
    estimatedArea: false,
  });
  assert.deepEqual(
    chips.map((c) => c.partKey),
    ['arm', 'shoulder'],
  );
  for (const chip of chips) {
    assert.equal(chip.kind, 'deduction');
    assert.equal(chip.label, partLabelKo(chip.partKey));
  }
  // 칩 수 == 그룹 수 (승인본 "화면의 표시 수 = 항목 수").
  const groups = buildPartGroups(SHOULDER_PAIR, [1, 2, 3], undefined);
  assert.equal(chips.length, groups.length);
  // N-3 — 병합 배지 탭 대상 = 그 부위의 최소 번호 record.
  const shoulderChip = chips.find((c) => c.partKey === 'shoulder');
  assert.equal(shoulderChip?.firstRecordIndex, 1);
  assert.deepEqual(shoulderChip?.numbers, [2, 3]);
});

test('Test 16b (칩): attention 관절만 있는 부위 → advisory 칩 `참고: {부위}`', () => {
  const chips = buildPartChips({
    records: [rec({ criterion: 'angle_vs_reference__left_knee' })],
    recordNumbers: [1],
    attentionKeypoints: ['left_hand'],
    estimatedArea: false,
  });
  assert.deepEqual(
    chips.map((c) => [c.partKey, c.label, c.kind]),
    [
      ['leg', '다리', 'deduction'],
      ['arm', '참고: 팔', 'advisory'],
    ],
  );
  assert.equal(chips[1].firstRecordIndex, null);
});

test('Test 16c (칩): 감점 부위와 겹치는 attention 부위는 참고 칩 미생성 (중복 0)', () => {
  const chips = buildPartChips({
    records: [rec({ criterion: 'angle_vs_reference__left_knee' })],
    recordNumbers: [1],
    attentionKeypoints: ['right_knee'],
    estimatedArea: false,
  });
  assert.deepEqual(
    chips.map((c) => c.partKey),
    ['leg'],
  );
});

test('Test 16d (칩): records 0 → 빈 배열 (N-14 cleanPass 칩 행 미렌더)', () => {
  assert.deepEqual(
    buildPartChips({
      records: [],
      recordNumbers: [],
      attentionKeypoints: ['left_hand'],
      estimatedArea: false,
    }),
    [],
  );
});

test('Test 16e (칩): estimatedArea → 빈 배열 (저신뢰에서 부위 단정 금지, S17 보호)', () => {
  assert.deepEqual(
    buildPartChips({
      records: SHOULDER_PAIR,
      recordNumbers: [1, 2, 3],
      attentionKeypoints: [],
      estimatedArea: true,
    }),
    [],
  );
});

// ── Test 17: 참고 문형 단일 소스 (S2 / T-33G3-02) ─────────────────────────
test('Test 17 (참고 문형): 상수 2종이 승인본 원문과 문자 일치', () => {
  // 승인본 `:1091` 짧은 칩형.
  assert.equal(ADVISORY_CHIP_KO, '참고 — 감점은 아니지만 회전·힘에 영향');
  // 승인본 legend 긴 안내형 (기존 advisory onecap 값 그대로 — 값 변경 0).
  assert.equal(
    ADVISORY_NOTE_KO,
    '참고 부위예요 — 점수 감점은 되지 않지만 회전·힘 같은 전체 동작에 영향을 줄 수 있어요. 눈에 띈 차이만 보여드려요',
  );
  // advisory 시트 onecap 이 같은 상수를 소비한다 (사본 0).
  const view = buildRegionSheetView(
    legsInput({
      zooms: [
        null,
        zoom({
          imageUrl: 'https://s3/adv.png',
          criterion: 'split_angle',
          tier: 'advisory',
        }),
      ],
      selectedRecordIndex: 1,
    }),
  );
  assert.ok(view);
  assert.equal(view.oneCap, ADVISORY_NOTE_KO);
});

// ── quick-260801-gbk — basis "잰 순간" 절의 출처·조건 ────────────────────────
// 종전엔 표시 프레임의 초(zoom.userVideoSec)를 인쇄했다. 모든 카드가 worst_seconds
// 한 시각에서 잘리던 시절엔 그 값이 우연히 맞았지만, 카드가 자기 순간을 갖게 되면
// "문장의 초"와 "사진의 순간"이 갈릴 수 있다. 이제 초는 rec.atVideoSec 에서 나오고,
// 절은 사진이 **바로 그 순간임을 백엔드가 인증**했을 때만 나온다.

const GBK_SUBJECT_ONLY = '어디서 재나요: 이 항목은 겨드랑이 벌림을 재요.';

function gbkView(
  recOver: Record<string, unknown>,
  zoomOver: Record<string, unknown> | null,
) {
  return buildRegionSheetView({
    records: [
      rec({ criterion: 'angle_vs_reference__left_shoulder', ...recOver }),
    ],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [
      zoomOver == null
        ? null
        : zoom({ imageUrl: 'https://s3/sh.png', ...zoomOver } as never),
    ],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
}

function gbkBasis(view: ReturnType<typeof buildRegionSheetView>): string {
  return view?.blocks[0].basisLine?.map((s) => s.text).join('') ?? '';
}

test('gbk basis: 사진 없는 record 는 atVideoSec 이 있어도 절이 없다', () => {
  // line·카드 4장 초과분 등 — 인쇄할 사진이 없으므로 "위 사진은…" 이 성립하지 않는다.
  const view = gbkView({ atFrameIdx: 16, atVideoSec: 1.74 }, null);
  assert.ok(view);
  assert.equal(gbkBasis(view), GBK_SUBJECT_ONLY);
});

test('gbk basis: atMatched 부재/false 카드는 atVideoSec 이 있어도 절이 없다', () => {
  // 앵커 창 안에서 다른 프레임이 채택된 카드 — 사진의 순간이 측정 순간이 아니다.
  for (const atMatched of [undefined, false]) {
    const view = gbkView(
      { atFrameIdx: 16, atVideoSec: 1.74 },
      { criterion: 'angle_vs_reference__left_shoulder', userVideoSec: 0.89, atMatched },
    );
    assert.ok(view);
    const joined = gbkBasis(view);
    assert.ok(!joined.includes('잰 순간'), `atMatched=${String(atMatched)}`);
    assert.equal(joined, GBK_SUBJECT_ONLY); // 앞 절은 그대로 남는다.
  }
});

test('gbk basis: 인증돼도 rec.atVideoSec 이 없으면 절이 없다', () => {
  // 표시 프레임의 초(userVideoSec)로 대체하지 않는다 — 그것은 다른 축의 값이다.
  const view = gbkView(
    {},
    { criterion: 'angle_vs_reference__left_shoulder', userVideoSec: 1.74, atMatched: true },
  );
  assert.ok(view);
  assert.equal(gbkBasis(view), GBK_SUBJECT_ONLY);
});

test('gbk basis: 인쇄되는 초는 rec.atVideoSec 이지 표시 프레임 초가 아니다', () => {
  const view = gbkView(
    { atFrameIdx: 16, atVideoSec: 1.74 },
    {
      criterion: 'angle_vs_reference__left_shoulder',
      userVideoSec: 9.99, // 일부러 다른 값 — 이것이 인쇄되면 안 된다.
      atMatched: true,
    },
  );
  assert.ok(view);
  const joined = gbkBasis(view);
  assert.ok(joined.includes('잰 순간(실 1.7초)'));
  assert.ok(!joined.includes('10.0초'));
});

test('gbk basis: 둘 다 불성립이면 basis 행 자체가 null', () => {
  const view = buildRegionSheetView({
    records: [rec({ criterion: 'dimension_overall_fallback', unit: 'score_delta' })],
    recordNumbers: [1],
    actionPhrases: [null],
    zooms: [null],
    selectedRecordIndex: 0,
    rightPairLabel: RIGHT_LABEL,
  });
  assert.ok(view);
  assert.equal(view.blocks[0].basisLine, null);
});

test('gbk basis: 신규 키가 전부 없는 legacy doc 에서 크래시 0', () => {
  // 종전 doc — atFrameIdx/atVideoSec/atMatched 부재. 절만 빠지고 나머지는 그대로.
  const view = gbkView(
    {},
    {
      criterion: 'angle_vs_reference__left_shoulder',
      userVideoSec: 1.74,
      refVideoSec: 3.07,
    },
  );
  assert.ok(view);
  assert.equal(gbkBasis(view), GBK_SUBJECT_ONLY);
  // method 행의 기준 초는 이 변경과 무관하게 종전 출처(refVideoSec)를 유지한다.
  assert.ok(view.blocks[0].methodLine?.includes('실 3.1초'));
});

// ══════════════════════════════════════════════════════════════════════════
// quick-260802-mrg — 원인 병합 (표시 전용) + 목표 절 분리
//
// belle 실기기(2026-08-01) 2건: ① 어깨 항목과 팔꿈치 항목이 한 잘못인데 따로 보인다
// ② 재생 자막이 결함 대신 목표를 말한다.
//
// **채점 무접촉이 이 블록의 전제다.** 병합은 표시 키만 만든다 — points·measuredValue·
// 총점은 이 코드 경로를 지나지 않고, 묶인 시트에서도 각 감점의 −X점이 블록마다
// 그대로 보인다(투명 합산).
//
// 실 fixture 형상은 저장 fixture(backend/evals/realfixture/fixtures) 실측을 옮긴 것:
//   elbow-twist-sister 8건 — elbow=grip_weak(동작 전용) / shoulder=shoulder_unstable
//     / hip=hip_hamstring_tight / knee=legs_not_extended
//   power-spin 3건 — leg_extension=legs_not_extended / split_angle=hip_hamstring_tight
//     / left_shoulder=shoulder_unstable
// ══════════════════════════════════════════════════════════════════════════

// ── T1~T7: buildCauseGroupKeys ────────────────────────────────────────────

test('T1 (병합): exerciseId 를 공유하는 shoulder / arm 이 한 키 shoulder+arm 로 합쳐진다', () => {
  // belle 이 지목한 형태 — 어깨 결함과 팔꿈치 결함이 한 원인(shoulder_unstable).
  const records = [
    rec({
      criterion: 'angle_vs_reference__left_shoulder',
      exerciseId: 'shoulder_unstable',
    }),
    rec({
      criterion: 'angle_vs_reference__left_elbow',
      exerciseId: 'shoulder_unstable',
    }),
  ];
  // 오늘은 갈라져 있다.
  assert.deepEqual(
    records.map((r) => regionPartKeyForRecord(r, undefined)),
    ['shoulder', 'arm'],
  );
  // 병합 후 한 항목.
  assert.deepEqual(buildCauseGroupKeys(records, undefined), [
    'shoulder+arm',
    'shoulder+arm',
  ]);
  // 기존 키 문법 그대로라 라벨이 이미 만들어진다 (신규 어휘 0).
  assert.equal(partLabelKo('shoulder+arm'), '어깨·팔');
});

test('T2 (병합): 같은 부위 안의 서로 다른 exerciseId 는 쪼개지지 않는다', () => {
  // hip=hip_hamstring_tight / knee=legs_not_extended — exerciseId 로 새로 나누면
  // '다리' 칩이 2개가 된다. 병합은 부위 키를 쪼개는 방향으로 가지 않는다.
  const records = [
    rec({
      criterion: 'angle_vs_reference__left_hip',
      exerciseId: 'hip_hamstring_tight',
    }),
    rec({
      criterion: 'angle_vs_reference__left_knee',
      exerciseId: 'legs_not_extended',
    }),
  ];
  assert.deepEqual(buildCauseGroupKeys(records, undefined), ['leg', 'leg']);
});

test('T3 (병합): 단조성 — distinct 키 수가 부위 키 distinct 수를 넘지 않는다 (merge-only)', () => {
  const criteria = [
    'angle_vs_reference__left_shoulder',
    'angle_vs_reference__right_shoulder',
    'angle_vs_reference__left_elbow',
    'angle_vs_reference__left_hip',
    'angle_vs_reference__left_knee',
    'line',
    'dimension_overall_fallback',
  ];
  const exerciseIds = [
    undefined,
    'shoulder_unstable',
    'grip_weak',
    'legs_not_extended',
    'hip_hamstring_tight',
    '',
  ];
  // 결정적 의사난수 — 같은 시드에서 같은 조합 (테스트 재현성).
  let seed = 20260802;
  const nextInt = (n: number): number => {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    return seed % n;
  };
  for (let trial = 0; trial < 400; trial += 1) {
    const size = 1 + nextInt(7);
    const records = [];
    for (let i = 0; i < size; i += 1) {
      records.push(
        rec({
          criterion: criteria[nextInt(criteria.length)],
          exerciseId: exerciseIds[nextInt(exerciseIds.length)],
          unit: 'deg',
        }),
      );
    }
    const base = new Set(
      records.map((r) => regionPartKeyForRecord(r, undefined)),
    );
    const merged = new Set(buildCauseGroupKeys(records, undefined));
    assert.ok(
      merged.size <= base.size,
      `병합이 그룹을 늘렸다 (base ${base.size} → ${merged.size})`,
    );
  }
});

test('T3b (병합): 한 부위 키의 record 는 exerciseId 보유 여부와 무관하게 같은 키를 받는다', () => {
  // 부위 키가 record 단위로 갈리면 '어깨'와 '어깨·팔' 칩이 동시에 서는 분열이
  // 생기고, 그것은 merge-only 위반이다 (오늘 한 그룹인 것이 갈라진다).
  const records = [
    rec({
      criterion: 'angle_vs_reference__left_shoulder',
      exerciseId: 'shoulder_unstable',
    }),
    rec({ criterion: 'angle_vs_reference__right_shoulder' }), // exerciseId 없음
    rec({
      criterion: 'angle_vs_reference__left_elbow',
      exerciseId: 'shoulder_unstable',
    }),
  ];
  assert.deepEqual(buildCauseGroupKeys(records, undefined), [
    'shoulder+arm',
    'shoulder+arm',
    'shoulder+arm',
  ]);
});

test('T4 (병합): exerciseId 전건 부재(legacy doc) → regionPartKeyForRecord 와 완전 동일', () => {
  const records = [
    rec({ criterion: 'angle_vs_reference__left_shoulder' }),
    rec({ criterion: 'angle_vs_reference__left_elbow' }),
    rec({ criterion: 'angle_vs_reference__left_knee' }),
    rec({ criterion: 'line' }),
    rec({ criterion: 'dimension_overall_fallback', unit: 'score_delta' }),
  ];
  assert.deepEqual(
    buildCauseGroupKeys(records, undefined),
    records.map((r) => regionPartKeyForRecord(r, undefined)),
  );
});

test('T5 (병합): 빈 문자열/공백/비문자열 exerciseId 는 간선을 만들지 않는다 (억지 병합 금지)', () => {
  for (const bogus of ['', '   ', null, undefined, 0, {}]) {
    const records = [
      rec({
        criterion: 'angle_vs_reference__left_shoulder',
        exerciseId: bogus as never,
      }),
      rec({
        criterion: 'angle_vs_reference__left_elbow',
        exerciseId: bogus as never,
      }),
    ];
    assert.deepEqual(
      buildCauseGroupKeys(records, undefined),
      ['shoulder', 'arm'],
      `exerciseId=${JSON.stringify(bogus)} 에서 병합이 일어났다`,
    );
  }
});

test('T6 (병합): criterion: 접두 그룹은 병합에 참여하지 않는다 (그릴 부위 없음)', () => {
  const records = [
    rec({ criterion: 'line', exerciseId: 'core_weak' }),
    rec({
      criterion: 'angle_vs_reference__left_shoulder',
      exerciseId: 'core_weak',
    }),
  ];
  assert.deepEqual(buildCauseGroupKeys(records, undefined), [
    'criterion:line',
    'shoulder',
  ]);
});

test('T7 (병합): 결정성 — 같은 입력이면 같은 출력, 키 안의 토큰 순서는 PART_ORDER', () => {
  // 입력 순서를 뒤집어도 키 문자열의 토큰 순서는 머리→발 고정 (shoulder+arm).
  const shoulder = rec({
    criterion: 'angle_vs_reference__left_shoulder',
    exerciseId: 'shoulder_unstable',
  });
  const elbow = rec({
    criterion: 'angle_vs_reference__left_elbow',
    exerciseId: 'shoulder_unstable',
  });
  assert.deepEqual(buildCauseGroupKeys([shoulder, elbow], undefined), [
    'shoulder+arm',
    'shoulder+arm',
  ]);
  assert.deepEqual(buildCauseGroupKeys([elbow, shoulder], undefined), [
    'shoulder+arm',
    'shoulder+arm',
  ]);
  // 반복 호출 동일.
  const once = buildCauseGroupKeys([shoulder, elbow], undefined);
  assert.deepEqual(buildCauseGroupKeys([shoulder, elbow], undefined), once);
});

test('T7b (병합): records 빈 배열 → 빈 배열 (크래시 0)', () => {
  assert.deepEqual(buildCauseGroupKeys([], undefined), []);
});

// ── T8~T12: splitGoalClause ───────────────────────────────────────────────

// 저장 fixture 실측 문자열 (powerspin.angle_vs_reference__left_shoulder) — 33-13
// belle 4R 승인 문형. 앱은 이 문자열을 **고치지 않고** 자리만 옮긴다.
const REAL_GOAL_CUE =
  '목표는 폴을 따라 위아래 한 줄 스플릿이에요. 어깨가 귀 쪽으로 으쓱 올라가지 않게 견갑을 눌러 잡고, 팔과 몸통 사이 각을 기준 자세에 겹쳐 맞춰보세요';
// 저장 fixture 실측 (powerspin.split_angle) — __common__ 문형이라 목표 절이 없다.
const REAL_COMMON_CUE =
  '양 무릎을 각각 반대쪽 벽으로 밀어낸다는 느낌으로 다리를 벌려보세요';

test('T8 (목표절): "목표는 A. B" → goalLine="목표는 A." / actionLine="B"', () => {
  const out = splitGoalClause(REAL_GOAL_CUE);
  assert.equal(out.goalLine, '목표는 폴을 따라 위아래 한 줄 스플릿이에요.');
  assert.equal(
    out.actionLine,
    '어깨가 귀 쪽으로 으쓱 올라가지 않게 견갑을 눌러 잡고, 팔과 몸통 사이 각을 기준 자세에 겹쳐 맞춰보세요',
  );
  // 첫 `". "` 에서 1회만 자른다 — 행동 절 안의 마침표는 건드리지 않는다.
  const twoDots = splitGoalClause('목표는 A. B. C');
  assert.equal(twoDots.goalLine, '목표는 A.');
  assert.equal(twoDots.actionLine, 'B. C');
});

test('T9 (목표절): 목표 접두 없음(__common__ 문형) → 자르지 않고 원문 그대로', () => {
  const out = splitGoalClause(REAL_COMMON_CUE);
  assert.equal(out.goalLine, null);
  assert.equal(out.actionLine, REAL_COMMON_CUE);
});

test('T10 (목표절): 구분자 ". " 없음 → fail-closed (자르지 않는다)', () => {
  for (const cue of ['목표는 폴을 따라 한 줄 스플릿이에요', '목표는 A.', '목표는 A.B']) {
    const out = splitGoalClause(cue);
    assert.equal(out.goalLine, null, cue);
    assert.equal(out.actionLine, cue, cue);
  }
});

test('T11 (목표절): actionLine 은 항상 원 cueLine 의 부분 문자열 (mp3 에 없는 말 금지)', () => {
  for (const cue of [
    REAL_GOAL_CUE,
    REAL_COMMON_CUE,
    '목표는 A. B',
    '목표는 A.',
    '아무 문장',
  ]) {
    const { actionLine } = splitGoalClause(cue);
    assert.ok(cue.includes(actionLine), `actionLine 이 원문에 없다: ${cue}`);
  }
});

test('T12 (목표절): null/undefined/빈 문자열 → { null, "" } 크래시 0', () => {
  for (const bogus of [null, undefined, '']) {
    assert.deepEqual(splitGoalClause(bogus), { goalLine: null, actionLine: '' });
  }
});

// ── T13~T17: composeCueSubtitleKo ─────────────────────────────────────────

// 저장 fixture 실측 (powerspin.angle_vs_reference__left_shoulder).
const REAL_STATUS = '왼쪽 어깨(겨드랑이) 각도가 파워스핀 기준 자세와 차이가 있어요';

test('T13 (자막): statusLine + actionLine → 결함이 먼저', () => {
  const out = composeCueSubtitleKo(
    rec({
      criterion: 'angle_vs_reference__left_shoulder',
      statusLine: REAL_STATUS,
      cueLine: REAL_GOAL_CUE,
    }),
    null,
  );
  assert.equal(
    out,
    `${REAL_STATUS} 어깨가 귀 쪽으로 으쓱 올라가지 않게 견갑을 눌러 잡고, 팔과 몸통 사이 각을 기준 자세에 겹쳐 맞춰보세요`,
  );
  // 자막의 첫머리가 결함이다 (belle 지적의 실체).
  assert.ok(out?.startsWith(REAL_STATUS));
});

test('T14 (자막): statusLine 없으면 actionLine 단독', () => {
  const out = composeCueSubtitleKo(
    rec({ criterion: 'angle_vs_reference__left_shoulder', cueLine: REAL_GOAL_CUE }),
    null,
  );
  assert.equal(
    out,
    '어깨가 귀 쪽으로 으쓱 올라가지 않게 견갑을 눌러 잡고, 팔과 몸통 사이 각을 기준 자세에 겹쳐 맞춰보세요',
  );
});

test('T15 (자막): cueLine 없으면 legacy 폴백 행동구 유지', () => {
  assert.equal(
    composeCueSubtitleKo(
      rec({ criterion: 'angle_vs_reference__left_knee' }),
      '무릎 더 펴기',
    ),
    '무릎 더 펴기',
  );
  // statusLine 이 있으면 폴백에도 결함이 앞선다 (같은 규칙, 분기 0).
  assert.equal(
    composeCueSubtitleKo(
      rec({
        criterion: 'angle_vs_reference__left_knee',
        statusLine: '왼쪽 무릎 각도가 기준 자세와 차이가 있어요',
      }),
      '무릎 더 펴기',
    ),
    '왼쪽 무릎 각도가 기준 자세와 차이가 있어요 무릎 더 펴기',
  );
});

test('T16 (자막): 행동구가 전무하면 null (자막 미렌더 — 오늘의 방출 조건 그대로)', () => {
  assert.equal(
    composeCueSubtitleKo(rec({ criterion: 'angle_vs_reference__left_knee' }), null),
    null,
  );
  // statusLine 만 있어도 자막을 새로 만들지 않는다 — 종전엔 이 record 에 자막이
  // 없었고, 여기서 만들면 cueTrack 의 입력 집합(밀도·타이밍)이 바뀐다.
  assert.equal(
    composeCueSubtitleKo(
      rec({ criterion: 'angle_vs_reference__left_knee', statusLine: REAL_STATUS }),
      null,
    ),
    null,
  );
});

test('T17 (자막): 산출에 `목표는` 리터럴이 0회', () => {
  const cues = [REAL_GOAL_CUE, REAL_COMMON_CUE, '목표는 A. B'];
  for (const cueLine of cues) {
    const out = composeCueSubtitleKo(
      rec({ criterion: 'angle_vs_reference__left_shoulder', statusLine: REAL_STATUS, cueLine }),
      null,
    );
    assert.ok(out != null);
    assert.ok(!out.includes('목표는'), `자막에 목표 절이 남았다: ${out}`);
  }
});
