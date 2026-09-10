// 동결된 옛 이름 표 ↔ 라이브러리 id 집합 게이트 (quick-260910-woq Task 3).
//
// 실행: node --test app/src/data/__tests__/legacyExerciseNames.test.ts
//
// 이 표는 09-10 개명 이전 doc 을 되짚는 **유일한** 수단이다. 라이브러리에 운동이
// 추가/삭제되면 표와 어긋나고, 어긋난 항목은 옛 doc 에서 조용히 사라진다(빈 모달).
// 여기서 양방향으로 막는다 — 누락도 fail, 고아도 fail.
//
// JSON 은 import 하지 않고 fs 로 읽는다 (Node ESM 의 import assertion 이 Metro 와
// 갈리는 함정 회피 — lib/resultSummary.ts 머리주석과 같은 이유).

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';

import {
  EXERCISE_ID_BY_LEGACY_NAME,
  LEGACY_EXERCISE_NAMES,
  resolveExerciseId,
} from '../legacyExerciseNames.ts';

const LIB = JSON.parse(
  readFileSync(path.join(import.meta.dirname, '..', 'corrective_exercises.json'), 'utf8'),
) as {
  defects: Record<string, { exercises: { id: string; name: string }[] }>;
  painAreas: Record<string, { exercises: { id: string; name: string }[] }>;
};

const ALL_ROWS: { group: string; id: string; name: string }[] = [
  ...Object.entries(LIB.defects).flatMap(([k, d]) =>
    d.exercises.map((e) => ({ group: `defects.${k}`, id: e.id, name: e.name })),
  ),
  ...Object.entries(LIB.painAreas).flatMap(([k, p]) =>
    p.exercises.map((e) => ({ group: `painAreas.${k}`, id: e.id, name: e.name })),
  ),
];
const UNIQUE_IDS = new Set(ALL_ROWS.map((r) => r.id));

test('라이브러리 전 항목이 id 를 갖는다 (실측 43행 / 유니크 28)', () => {
  assert.equal(ALL_ROWS.length, 43, '라이브러리 행 수가 바뀌었다 — 표도 함께 봐야 한다');
  for (const r of ALL_ROWS) {
    assert.equal(typeof r.id, 'string', `${r.group} / ${r.name} 에 id 없음`);
    assert.ok(r.id.length > 0, `${r.group} / ${r.name} id 가 빈 문자열`);
  }
  assert.equal(UNIQUE_IDS.size, 28);
});

test('축4 id 유니크성 — 서로 다른 운동이 같은 id 를 쓰면 fail', () => {
  const namesById = new Map<string, Set<string>>();
  for (const r of ALL_ROWS) {
    if (!namesById.has(r.id)) namesById.set(r.id, new Set());
    namesById.get(r.id)!.add(r.name);
  }
  const collided = [...namesById].filter(([, names]) => names.size > 1);
  assert.deepEqual(collided, [], '같은 id 인데 이름이 다르다 — 다른 운동이 id 를 공유');
});

test('축5 같은 운동은 어느 그룹에 있든 같은 id (스쿼트 3그룹 · 옆으로 다리 들기 2그룹)', () => {
  const idsByName = new Map<string, Set<string>>();
  for (const r of ALL_ROWS) {
    if (!idsByName.has(r.name)) idsByName.set(r.name, new Set());
    idsByName.get(r.name)!.add(r.id);
  }
  const split = [...idsByName].filter(([, ids]) => ids.size > 1);
  assert.deepEqual(split, [], '같은 이름인데 그룹마다 id 가 다르다');

  // 여러 그룹에 실린 운동이 실제로 있다는 것도 확인한다 — 없으면 이 축이 사문이 된다.
  const groupsFor = (name: string) => ALL_ROWS.filter((r) => r.name === name).map((r) => r.group);
  assert.ok(groupsFor('스쿼트').length >= 3, '스쿼트가 3그룹에 없다 — 축5 전제가 깨졌다');
  assert.ok(groupsFor('옆으로 다리 들기').length >= 2);
});

test('id 는 스네이크 케이스 — 표시명(한글) 파생이 아니다', () => {
  for (const id of UNIQUE_IDS) {
    assert.match(id, /^[a-z0-9]+(_[a-z0-9]+)*$/, `id 형식 위반: ${id}`);
  }
});

test('옛 이름 표가 라이브러리 id 를 빠짐없이 덮는다 (누락 = 옛 doc 이 조용히 사라짐)', () => {
  const missing = [...UNIQUE_IDS].filter((id) => !(id in LEGACY_EXERCISE_NAMES));
  assert.deepEqual(missing, [], '옛 이름이 없는 id — 개명 이전 doc 이 이 운동을 못 찾는다');
});

test('옛 이름 표에 고아가 없다 (라이브러리에서 사라진 id 는 표에서도 빠져야 한다)', () => {
  const orphans = Object.keys(LEGACY_EXERCISE_NAMES).filter((id) => !UNIQUE_IDS.has(id));
  assert.deepEqual(orphans, [], '라이브러리에 없는 id 가 표에 남아 있다');
});

test('옛 이름도 유니크 — 한 이름이 두 id 를 가리키면 옛 doc 이 오매칭된다', () => {
  const names = Object.values(LEGACY_EXERCISE_NAMES);
  assert.equal(names.length, new Set(names).size);
  assert.equal(Object.keys(EXERCISE_ID_BY_LEGACY_NAME).length, names.length);
});

test('resolveExerciseId: id 우선 → 옛 이름 → 없으면 null (지어내지 않는다)', () => {
  assert.equal(resolveExerciseId({ id: 'squats', name: '아무거나' }), 'squats');
  assert.equal(resolveExerciseId({ name: 'Push-ups' }), 'push_ups');
  assert.equal(resolveExerciseId({ name: '팔굽혀펴기' }), null, '지금 이름은 이 표의 소관이 아니다');
  assert.equal(resolveExerciseId({ name: 'Bicep/Tricep Balance' }), null, '라이브러리에서 사라진 운동');
  for (const bad of [{}, { id: '' }, { id: null, name: null }, null, undefined]) {
    assert.equal(resolveExerciseId(bad as never), null, JSON.stringify(bad));
  }
});
