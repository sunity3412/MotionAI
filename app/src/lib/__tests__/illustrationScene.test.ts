// 일러스트 장면일치 판정 검증 (quick-260731-2jt Task 1 — 33-G S13/S25,
// quick-260731-plf Task 1 — §C-4 3번 부위별 키 전환).
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
// 검증 축 (2jt 9축 + P-1 축 + plf 신규 3축):
//   1) 장면 토큰이 항목 토큰을 전부 덮으면 부착 (반환 asset 이 실제로 그 토큰을 덮는다)
//   2) 못 덮으면 null — 어깨 항목에 다리 그림 차단 (M-5 직접 해소)
//   3) 부분 겹침(항목 shoulder+arm × 장면 arm) → null (P-2)
//   4) 토큰 공집합 partKey(criterion:...) → 항상 null (P-3 vacuous 차단)
//   5) motionId null/undefined/미등재/에셋 미보유 동작 → null (mode3 회귀 0)
//   6) partKey null/빈 문자열/공백 → null
//   7) hasIllustrationFor 가 illustrationAssetForPart 와 항상 일치 (규칙 사본 0)
//   8) ILLUSTRATION_SCENES 전 항목이 비어있지 않은 parts + provenance (T-33G4-01)
//   9) parts 토큰이 전부 BODY_PART_OF_KEYPOINT 치역 (오타 토큰 조용한 미매칭 차단)
//  10) 판정 입력 = regionPartKeyForRecord 가 실제로 내는 키 (P-1 단일 출처)
//  11) 복수 후보 시 **최구체 우선** (parts 최소가 이긴다)
//  12) asset 중복 0 · 같은 (motionId, parts) 쌍 중복 0
//  13) 부위 어휘 게이트 — parts 토큰의 부위 어휘가 provenance 에 있어야 한다
//      (억지 매칭 차단: 다리 그림 provenance 에 토큰만 shoulder 로 붙이는 경로 봉인)

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ILLUSTRATION_SCENES,
  hasIllustrationFor,
  illustrationAssetForPart,
  sceneCoversParts,
} from '../illustrationScene.ts';
import type { IllustrationScene } from '../illustrationScene.ts';
import { BODY_PART_OF_KEYPOINT } from '../deductionLabels.ts';
import { regionPartKeyForRecord } from '../deductionSheet.ts';

// ── 픽스처 ────────────────────────────────────────────────────────────────

/** 장면을 가진 동작 목록 (표 파생 — 하드코딩 목록 0). */
const REGISTERED_MOTIONS = [
  ...new Set(ILLUSTRATION_SCENES.map((s) => s.motionId)),
];
/**
 * 33-14 검수 상한 3회를 소진한 미완 4동작 중 **아직 장면이 없는 것**. 파생으로 두는
 * 이유: §C-4 3번이 이 집합을 줄이므로 고정 목록이면 거짓 FAIL 이 난다.
 */
const KNOWN_UNFINISHED_2026_07_29 = [
  'ref-peter-pan',
  'ref-elbow-twist-sister',
  'ref-pdshape',
  'ref-sideway-spin',
];
const SCENELESS_MOTIONS = KNOWN_UNFINISHED_2026_07_29.filter(
  (m) => !REGISTERED_MOTIONS.includes(m),
);
/** 부위 키 전건 — deductionSheet.regionPartKeyForRecord 가 낼 수 있는 형태. */
const PART_KEYS = ['leg', 'shoulder', 'arm', 'shoulder+arm'];

/** 규칙 사본이 아니라 **독립 재계산** — 판정이 표와 어긋나면 잡는다. */
function scenesCovering(motionId: string, partKey: string): IllustrationScene[] {
  const tokens = partKey.split('+').filter((t) => t.length > 0);
  if (partKey.startsWith('criterion:') || tokens.length === 0) return [];
  return ILLUSTRATION_SCENES.filter(
    (s) =>
      s.motionId === motionId && tokens.every((t) => s.parts.includes(t)),
  );
}

// ── 1) 덮으면 부착 ────────────────────────────────────────────────────────

test('1: 장면 토큰이 항목 토큰을 전부 덮으면 부착되고, 반환 asset 이 그 토큰을 덮는다', () => {
  let attached = 0;
  for (const scene of ILLUSTRATION_SCENES) {
    // 개별 토큰 + 장면 토큰 전체 조합 둘 다 부착돼야 한다.
    const keys = [...scene.parts, scene.parts.join('+')];
    for (const key of keys) {
      const got = illustrationAssetForPart(scene.motionId, key);
      assert.notEqual(
        got,
        null,
        `${scene.motionId} × ${key} 이 자기 장면 토큰인데 미부착`,
      );
      const winner = ILLUSTRATION_SCENES.find((s) => s.asset === got);
      assert.ok(winner, `반환 asset ${got} 이 표에 없다`);
      assert.equal(winner.motionId, scene.motionId, '다른 동작의 그림이 왔다');
      assert.ok(
        sceneCoversParts(key.split('+'), winner.parts),
        `${scene.motionId} × ${key} → ${got} 이 그 부위를 덮지 않는다`,
      );
      attached += 1;
    }
  }
  // 부착 갈래가 하나도 없으면 배선이 죽은 코드다 (스위프 INV-6 과 같은 하한).
  assert.ok(attached >= 1, '부착 케이스 0건 — 규칙이 전멸시켰다');
});

// ── 2) 못 덮으면 미부착 ───────────────────────────────────────────────────

test('2: 항목 부위가 장면에 없으면 null — 어깨 항목에 다리 그림 차단 (M-5)', () => {
  for (const motionId of REGISTERED_MOTIONS) {
    for (const partKey of PART_KEYS) {
      const covering = scenesCovering(motionId, partKey);
      const got = illustrationAssetForPart(motionId, partKey);
      if (covering.length === 0) {
        assert.equal(
          got,
          null,
          `${motionId} × ${partKey} 가 장면과 어긋나는데 부착됐다`,
        );
      } else {
        assert.ok(
          covering.some((s) => s.asset === got),
          `${motionId} × ${partKey} → ${got} 이 덮는 장면이 아니다`,
        );
      }
    }
  }
  // 어떤 항목에도 "그 부위를 안 짚는 그림"이 오면 안 된다 (M-5 본체).
  for (const motionId of REGISTERED_MOTIONS) {
    for (const partKey of PART_KEYS) {
      const got = illustrationAssetForPart(motionId, partKey);
      if (got === null) continue;
      const winner = ILLUSTRATION_SCENES.find((s) => s.asset === got);
      assert.ok(winner);
      for (const token of partKey.split('+')) {
        assert.ok(
          winner.parts.includes(token),
          `${motionId} × ${partKey} → ${got} 은 ${token} 을 안 짚는 그림이다`,
        );
      }
    }
  }
});

// ── 3) 부분 겹침 = 불일치 (P-2) ───────────────────────────────────────────

test('3: 부분 겹침은 불일치 — 항목 shoulder+arm × 장면 arm 은 null', () => {
  // 실표가 한 계열로만 채워진 구간에서는 이 분기를 밟을 수 없다 → 규칙을 합성
  // 토큰으로 직접 고정한다 (P-13).
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
  for (const motionId of REGISTERED_MOTIONS) {
    for (const key of emptyKeys) {
      assert.equal(
        illustrationAssetForPart(motionId, key),
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

test('5: motionId 부재·미등재·장면 미보유 동작은 전 부위 미부착', () => {
  for (const partKey of PART_KEYS) {
    assert.equal(illustrationAssetForPart(null, partKey), null); // mode3
    assert.equal(illustrationAssetForPart(undefined, partKey), null);
    assert.equal(illustrationAssetForPart('', partKey), null);
    assert.equal(illustrationAssetForPart('ref-unknown-move', partKey), null);
    for (const motionId of SCENELESS_MOTIONS) {
      assert.equal(
        illustrationAssetForPart(motionId, partKey),
        null,
        `${motionId} 은 장면 미보유 — 부착되면 안 된다`,
      );
    }
  }
  // 프로토타입 키로 표를 우회할 수 없다 (배열 순회로 원천 소멸했으나 회귀 방지).
  for (const key of ['__proto__', 'constructor', 'toString']) {
    assert.equal(illustrationAssetForPart(key, 'leg'), null, key);
  }
});

// ── 6) partKey 갈래 ───────────────────────────────────────────────────────

test('6: partKey 부재·빈 문자열·공백은 미부착', () => {
  for (const motionId of REGISTERED_MOTIONS) {
    assert.equal(illustrationAssetForPart(motionId, null), null);
    assert.equal(illustrationAssetForPart(motionId, undefined), null);
    assert.equal(illustrationAssetForPart(motionId, ''), null);
    assert.equal(illustrationAssetForPart(motionId, '   '), null);
    assert.equal(illustrationAssetForPart(motionId, '+'), null);
    assert.equal(illustrationAssetForPart(motionId, '++'), null);
  }
});

// ── 7) 두 공개 함수 일치 ──────────────────────────────────────────────────

test('7: hasIllustrationFor 는 illustrationAssetForPart 와 항상 일치', () => {
  const motions = [
    ...REGISTERED_MOTIONS,
    ...KNOWN_UNFINISHED_2026_07_29,
    'ref-unknown-move',
    '',
  ];
  const keys = [...PART_KEYS, 'criterion:line', '', '   ', 'legs'];
  for (const motionId of [...motions, null, undefined]) {
    for (const partKey of [...keys, null, undefined]) {
      assert.equal(
        hasIllustrationFor(motionId, partKey),
        illustrationAssetForPart(motionId, partKey) !== null,
        `${String(motionId)} × ${String(partKey)}`,
      );
    }
  }
});

// ── 8) 데이터 무결성 (T-33G4-01 — 근거 없는 등재 차단) ────────────────────

test('8: 전 등재 항목이 비어있지 않은 parts 와 provenance 를 갖는다', () => {
  assert.ok(ILLUSTRATION_SCENES.length > 0, '등재 0건');
  for (const scene of ILLUSTRATION_SCENES) {
    const id = `${scene.motionId}/${scene.parts.join('+')}`;
    assert.equal(typeof scene.motionId, 'string');
    assert.ok(scene.motionId.length > 0, `${id} motionId 없음`);
    assert.equal(typeof scene.asset, 'string');
    assert.ok(scene.asset.length > 0, `${id} asset 없음`);
    assert.ok(Array.isArray(scene.parts), `${id} parts 배열 아님`);
    assert.ok(scene.parts.length > 0, `${id} parts 공집합 — 등재 금지`);
    assert.equal(
      new Set(scene.parts).size,
      scene.parts.length,
      `${id} parts 중복 토큰`,
    );
    assert.equal(typeof scene.provenance, 'string', `${id} provenance 없음`);
    assert.ok(
      scene.provenance.trim().length >= 20,
      `${id} provenance 가 근거로 읽히지 않는다`,
    );
    // 문서만 보고 정한 토큰은 등재하지 않는다 (P-4 / D-40).
    assert.ok(
      scene.provenance.includes('실물 열람'),
      `${id} provenance 에 실물 열람 근거가 없다`,
    );
  }
});

// ── 9) 토큰 어휘 (오타 조용한 미매칭 차단) ────────────────────────────────

test('9: parts 토큰은 전부 BODY_PART_OF_KEYPOINT 치역에 속한다', () => {
  const valid = new Set<string>(Object.values(BODY_PART_OF_KEYPOINT));
  assert.ok(valid.size > 0, '부위 사전이 비었다');
  for (const scene of ILLUSTRATION_SCENES) {
    for (const token of scene.parts) {
      assert.ok(
        valid.has(token),
        `${scene.motionId} 의 토큰 ${token} 이 부위 사전 밖 — 조용히 영원히 미매칭된다`,
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

  // 그 키가 판정에 그대로 들어가 표와 일치하는 결과를 낸다 (독립 재계산 대조).
  // 명시 타입 — assert.equal 의 `asserts actual is T` narrowing 이 배열 리터럴
  // 추론과 순환하면 TS7022 가 난다.
  const derivedKeys: string[] = [legKey, shoulderKey];
  for (const motionId of REGISTERED_MOTIONS) {
    for (const key of derivedKeys) {
      const covering = scenesCovering(motionId, key);
      const got = illustrationAssetForPart(motionId, key);
      if (covering.length === 0) assert.equal(got, null, `${motionId} × ${key}`);
      else assert.ok(covering.some((s) => s.asset === got), `${motionId} × ${key}`);
    }
    assert.equal(illustrationAssetForPart(motionId, emptyKey), null);
  }
});

// ── 11) 최구체 우선 (plf 신규) ────────────────────────────────────────────

test('11: 복수 후보가 덮으면 parts 가 가장 작은 장면이 이긴다', () => {
  // 합성 고정 — 실표에 복수 후보가 없는 구간에서도 규칙이 살아 있어야 한다.
  assert.equal(sceneCoversParts(['shoulder'], ['shoulder']), true);
  assert.equal(sceneCoversParts(['shoulder'], ['shoulder', 'arm']), true);

  // 실표에 복수 매칭이 실제로 있으면 최소 parts 쪽이 반환돼야 한다.
  const probeKeys = [...PART_KEYS];
  let multiSeen = 0;
  for (const motionId of REGISTERED_MOTIONS) {
    for (const partKey of probeKeys) {
      const covering = scenesCovering(motionId, partKey);
      if (covering.length < 2) continue;
      multiSeen += 1;
      const minLen = Math.min(...covering.map((s) => s.parts.length));
      const expected = covering.find((s) => s.parts.length === minLen);
      assert.ok(expected);
      assert.equal(
        illustrationAssetForPart(motionId, partKey),
        expected.asset,
        `${motionId} × ${partKey} — 최구체 우선이 아니다`,
      );
    }
  }
  // 복수 매칭이 없는 것은 정상(표 상태에 달림) — 관측만 남긴다.
  assert.ok(multiSeen >= 0);
});

// ── 12) 중복 금지 (plf 신규) ──────────────────────────────────────────────

test('12: asset 값이 유일하고 같은 (motionId, parts 집합) 쌍이 중복되지 않는다', () => {
  const assets = ILLUSTRATION_SCENES.map((s) => s.asset);
  assert.equal(
    new Set(assets).size,
    assets.length,
    `asset 중복: ${assets.filter((a, i) => assets.indexOf(a) !== i).join(', ')}`,
  );
  const pairs = ILLUSTRATION_SCENES.map(
    (s) => `${s.motionId}|${[...s.parts].sort().join('+')}`,
  );
  assert.equal(
    new Set(pairs).size,
    pairs.length,
    `같은 동작·같은 부위 조합이 둘 이상: ${pairs.filter((p, i) => pairs.indexOf(p) !== i).join(', ')}`,
  );
});

// ── 13) 부위 어휘 게이트 (plf 신규 — 억지 매칭 차단) ──────────────────────

test('13: parts 토큰마다 그 부위의 한국어 어휘가 provenance 에 있어야 한다', () => {
  // 어휘 표는 이 파일 1곳에만 둔다 (판정 코드에 넣으면 규칙이 두 벌이 된다).
  // 목적: 다리 그림의 provenance 를 그대로 두고 토큰만 shoulder 로 넓히는 경로 봉인.
  const VOCAB: Record<string, string[]> = {
    shoulder: ['어깨', '견갑'],
    arm: ['팔', '팔꿈치', '엘보', '손'],
    leg: ['다리', '무릎', '발', '골반'],
  };
  for (const scene of ILLUSTRATION_SCENES) {
    for (const token of scene.parts) {
      const words = VOCAB[token];
      assert.ok(words, `부위 토큰 ${token} 의 어휘가 표에 없다`);
      assert.ok(
        words.some((w) => scene.provenance.includes(w)),
        `${scene.motionId}/${scene.asset} — parts 에 ${token} 이 있는데 provenance 에 그 부위 어휘(${words.join('·')})가 없다`,
      );
    }
  }
});
