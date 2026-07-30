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

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildRegionSheetView,
  formatVideoSecKo,
  regionPartKeyForRecord,
  type RegionSheetInput,
} from '../deductionSheet.ts';

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
    ['고칠 것 1 — 다리 스플릿 각도 (−12점)', '고칠 것 2 — 다리 신전(펴짐) (−20점)'],
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
  const withSec = buildRegionSheetView({
    records: [rec({ criterion: 'angle_vs_reference__left_shoulder' })],
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
