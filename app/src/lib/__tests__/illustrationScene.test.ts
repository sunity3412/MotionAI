// 일러스트 장면일치 판정 검증 (quick-260731-2jt Task 1 — 33-G S13/S25).
//
// 실행: node --test app/src/lib/__tests__/illustrationScene.test.ts
// Node 24 의 type stripping 으로 트랜스파일 없이 실행 — 신규 npm 의존성 0
// (deductionSheet.test.ts / resultSections.test.ts 선례). node:test / node:assert
// 표준 모듈 + `.ts` 확장자 import 만.
//
// 왜 이 테스트가 존재하나: 이 판정의 실패 모드는 **조용하다**. 잘못 붙으면 화면에
// 어깨 항목 아래 다리 그림이 그냥 앉아 있고(belle 확인 ② #8·#9·#11), 반대로 규칙이
// 과하면 아무 데도 안 붙는데 에러 하나 없다. typecheck 는 둘 다 통과한다. 특히
// **토큰 공집합에서 부분집합 판정이 vacuously 참**이 되는 갈래는 fail-closed 를
// 정반대로 뒤집으면서 타입·렌더 어느 쪽에서도 티가 나지 않는다 (T-33G4-02).
//
// 검증 축 (플랜 behavior 9축 + 위협 T-33G4-01/02):
//   1) 장면 토큰이 항목 토큰을 전부 덮으면 motionId 반환
//   2) 못 덮으면 null — 어깨 항목에 다리 그림 차단 (M-5 직접 해소)
//   3) 부분 겹침(항목 shoulder+arm × 장면 arm) → null (P-2)
//   4) 토큰 공집합 partKey(criterion:...) → 항상 null (P-3 vacuous 차단)
//   5) motionId null/undefined/미등재/에셋 미보유 4동작 → null (mode3 회귀 0)
//   6) partKey null/빈 문자열/공백 → null
//   7) hasIllustrationFor 가 illustrationMotionForPart 와 항상 일치 (규칙 사본 0)
//   8) ILLUSTRATION_SCENES 전 항목이 비어있지 않은 parts + provenance (T-33G4-01)
//   9) parts 토큰이 전부 BODY_PART_OF_KEYPOINT 치역 (오타 토큰 조용한 미매칭 차단)

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ILLUSTRATION_SCENES,
  hasIllustrationFor,
  illustrationMotionForPart,
  sceneCoversParts,
} from '../illustrationScene.ts';
import { BODY_PART_OF_KEYPOINT } from '../deductionLabels.ts';
import { regionPartKeyForRecord } from '../deductionSheet.ts';

// ── 픽스처 ────────────────────────────────────────────────────────────────

const REGISTERED = Object.keys(ILLUSTRATION_SCENES);
/** 33-14 에서 검수 상한 3회를 소진한 미완 4동작 (의도된 fail-closed hidden). */
const ASSET_MISSING_MOTIONS = [
  'ref-peter-pan',
  'ref-elbow-twist-sister',
  'ref-pdshape',
  'ref-sideway-spin',
];
/** 부위 키 전건 — deductionSheet.regionPartKeyForRecord 가 낼 수 있는 형태. */
const PART_KEYS = ['leg', 'shoulder', 'arm', 'shoulder+arm'];

// ── 1) 덮으면 부착 ────────────────────────────────────────────────────────

test('1: 장면 토큰이 항목 토큰을 전부 덮으면 그 motionId 를 돌려준다', () => {
  let attached = 0;
  for (const motionId of REGISTERED) {
    const scene = ILLUSTRATION_SCENES[motionId];
    for (const token of scene.parts) {
      assert.equal(
        illustrationMotionForPart(motionId, token),
        motionId,
        `${motionId} × ${token} 이 자기 장면 토큰인데 미부착`,
      );
      attached += 1;
    }
  }
  // 부착 갈래가 하나도 없으면 배선이 죽은 코드다 (스위프 INV-6 과 같은 하한).
  assert.ok(attached >= 1, '부착 케이스 0건 — 규칙이 전멸시켰다');
});

// ── 2) 못 덮으면 미부착 ───────────────────────────────────────────────────

test('2: 항목 부위가 장면에 없으면 null — 어깨 항목에 다리 그림 차단 (M-5)', () => {
  for (const motionId of REGISTERED) {
    const scene = new Set(ILLUSTRATION_SCENES[motionId].parts);
    for (const partKey of PART_KEYS) {
      const covered = partKey.split('+').every((t) => scene.has(t));
      if (covered) continue;
      assert.equal(
        illustrationMotionForPart(motionId, partKey),
        null,
        `${motionId} × ${partKey} 가 장면과 어긋나는데 부착됐다`,
      );
    }
  }
  // 현 등재본 전건이 다리 장면이므로 어깨 항목은 전 동작에서 미부착이어야 한다.
  for (const motionId of REGISTERED) {
    assert.equal(illustrationMotionForPart(motionId, 'shoulder'), null);
  }
});

// ── 3) 부분 겹침 = 불일치 (P-2) ───────────────────────────────────────────

test('3: 부분 겹침은 불일치 — 항목 shoulder+arm × 장면 arm 은 null', () => {
  // 등재 6장이 전부 다리 계열이라 실맵으로는 이 분기를 밟을 수 없다 → 규칙을
  // 합성 토큰으로 직접 고정한다 (P-13).
  assert.equal(sceneCoversParts(['shoulder', 'arm'], ['arm']), false);
  assert.equal(sceneCoversParts(['shoulder', 'arm'], ['shoulder']), false);
  assert.equal(sceneCoversParts(['shoulder', 'arm'], ['shoulder', 'arm']), true);
  assert.equal(sceneCoversParts(['arm'], ['shoulder', 'arm']), true);
  assert.equal(sceneCoversParts(['leg'], ['shoulder', 'arm']), false);
});

test('3b: 유효 범위 밖 토큰은 장면에 같은 문자가 있어도 불일치 (오타 fail-closed)', () => {
  assert.equal(sceneCoversParts(['legs'], ['legs']), false);
  assert.equal(sceneCoversParts(['LEG'], ['LEG']), false);
  assert.equal(sceneCoversParts(['leg'], ['leg']), true);
});

// ── 4) 토큰 공집합 (P-3) ──────────────────────────────────────────────────

test('4: 투영 공집합 항목(criterion:...)은 어떤 에셋과도 매칭되지 않는다', () => {
  const emptyKeys = [
    'criterion:line',
    'criterion:dimension_overall_fallback',
    'criterion:split_angle',
    'criterion:',
  ];
  for (const motionId of REGISTERED) {
    for (const key of emptyKeys) {
      assert.equal(
        illustrationMotionForPart(motionId, key),
        null,
        `${motionId} × ${key} — 공집합이 vacuous 매칭됐다 (fail-closed 역전)`,
      );
    }
  }
  // 규칙 자체도 공집합에서 false (호출자 우회 방지).
  assert.equal(sceneCoversParts([], ['leg']), false);
  assert.equal(sceneCoversParts(['leg'], []), false);
  assert.equal(sceneCoversParts([], []), false);
});

// ── 5) motionId 갈래 (mode3 / 미등재 / 에셋 미보유) ───────────────────────

test('5: motionId 부재·미등재·에셋 미보유 4동작은 전 부위 미부착', () => {
  for (const partKey of PART_KEYS) {
    assert.equal(illustrationMotionForPart(null, partKey), null); // mode3
    assert.equal(illustrationMotionForPart(undefined, partKey), null);
    assert.equal(illustrationMotionForPart('', partKey), null);
    assert.equal(illustrationMotionForPart('ref-unknown-move', partKey), null);
    for (const motionId of ASSET_MISSING_MOTIONS) {
      assert.equal(
        illustrationMotionForPart(motionId, partKey),
        null,
        `${motionId} 은 33-14 미완 4동작 — 부착되면 안 된다`,
      );
    }
  }
  // 프로토타입 키로 표를 우회할 수 없다.
  for (const key of ['__proto__', 'constructor', 'toString']) {
    assert.equal(illustrationMotionForPart(key, 'leg'), null, key);
  }
});

// ── 6) partKey 갈래 ───────────────────────────────────────────────────────

test('6: partKey 부재·빈 문자열·공백은 미부착', () => {
  for (const motionId of REGISTERED) {
    assert.equal(illustrationMotionForPart(motionId, null), null);
    assert.equal(illustrationMotionForPart(motionId, undefined), null);
    assert.equal(illustrationMotionForPart(motionId, ''), null);
    assert.equal(illustrationMotionForPart(motionId, '   '), null);
    assert.equal(illustrationMotionForPart(motionId, '+'), null);
    assert.equal(illustrationMotionForPart(motionId, '++'), null);
  }
});

// ── 7) 두 공개 함수 일치 ──────────────────────────────────────────────────

test('7: hasIllustrationFor 는 illustrationMotionForPart 와 항상 일치', () => {
  const motions = [
    ...REGISTERED,
    ...ASSET_MISSING_MOTIONS,
    'ref-unknown-move',
    '',
  ];
  const keys = [...PART_KEYS, 'criterion:line', '', '   ', 'legs'];
  for (const motionId of [...motions, null, undefined]) {
    for (const partKey of [...keys, null, undefined]) {
      assert.equal(
        hasIllustrationFor(motionId, partKey),
        illustrationMotionForPart(motionId, partKey) !== null,
        `${String(motionId)} × ${String(partKey)}`,
      );
    }
  }
});

// ── 8) 데이터 무결성 (T-33G4-01 — 근거 없는 등재 차단) ────────────────────

test('8: 전 등재 항목이 비어있지 않은 parts 와 provenance 를 갖는다', () => {
  assert.ok(REGISTERED.length > 0, '등재 0건');
  for (const motionId of REGISTERED) {
    const scene = ILLUSTRATION_SCENES[motionId];
    assert.ok(Array.isArray(scene.parts), `${motionId} parts 배열 아님`);
    assert.ok(scene.parts.length > 0, `${motionId} parts 공집합 — 등재 금지`);
    assert.equal(
      new Set(scene.parts).size,
      scene.parts.length,
      `${motionId} parts 중복 토큰`,
    );
    assert.equal(
      typeof scene.provenance,
      'string',
      `${motionId} provenance 없음`,
    );
    assert.ok(
      scene.provenance.trim().length >= 20,
      `${motionId} provenance 가 근거로 읽히지 않는다`,
    );
    // 문서만 보고 정한 토큰은 등재하지 않는다 (P-4 / D-40).
    assert.ok(
      scene.provenance.includes('실물 열람'),
      `${motionId} provenance 에 실물 열람 근거가 없다`,
    );
  }
});

// ── 9) 토큰 어휘 (오타 조용한 미매칭 차단) ────────────────────────────────

test('9: parts 토큰은 전부 BODY_PART_OF_KEYPOINT 치역에 속한다', () => {
  const valid = new Set<string>(Object.values(BODY_PART_OF_KEYPOINT));
  assert.ok(valid.size > 0, '부위 사전이 비었다');
  for (const motionId of REGISTERED) {
    for (const token of ILLUSTRATION_SCENES[motionId].parts) {
      assert.ok(
        valid.has(token),
        `${motionId} 의 토큰 ${token} 이 부위 사전 밖 — 조용히 영원히 미매칭된다`,
      );
    }
  }
});

// ── 10) 부위 키 단일 출처 (P-1 — 두 번째 그룹핑 규칙 금지) ────────────────

test('10: 판정 입력은 regionPartKeyForRecord 가 실제로 내는 키를 그대로 먹는다', () => {
  type Rec = Parameters<typeof regionPartKeyForRecord>[0];
  const mk = (criterion: string, over: Partial<Rec> = {}): Rec =>
    ({
      criterion,
      measuredValue: 141,
      baselineValue: 180,
      baselineKind: null,
      deviation: 19,
      ruleId: 'illu-1',
      points: -12,
      unit: 'deg',
      ipsfAnchor: 'x',
      source: 'geometry',
      deviationSource: 'ipsf_absolute',
      statusLine: null,
      whyLine: null,
      cueLine: null,
      ...over,
    }) as Rec;

  const legKey = regionPartKeyForRecord(mk('leg_extension'), undefined);
  const shoulderKey = regionPartKeyForRecord(
    mk('angle_vs_reference__left_shoulder', {
      deviationSource: 'reference_relative',
    }),
    undefined,
  );
  const emptyKey = regionPartKeyForRecord(mk('line'), undefined);

  assert.equal(legKey, 'leg');
  assert.equal(shoulderKey, 'shoulder');
  assert.ok(emptyKey.startsWith('criterion:'));

  const motionId = REGISTERED[0];
  assert.equal(illustrationMotionForPart(motionId, legKey), motionId);
  assert.equal(illustrationMotionForPart(motionId, shoulderKey), null);
  assert.equal(illustrationMotionForPart(motionId, emptyKey), null);
});
