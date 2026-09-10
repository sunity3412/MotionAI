// '전체 보완 운동 보기' 모달 선택 뷰모델 검증 (quick-260910-pbs Task 3).
//
// 실행: node --test app/src/lib/__tests__/exerciseSections.test.ts
// Node 의 type stripping 으로 트랜스파일 없이 실행 — 신규 의존성 0
// (resultSections.test.ts / cueTrack.test.ts 선례). node:test / node:assert 만.
//
// 왜 이 테스트가 존재하나: 모달은 종전에 분석을 아예 안 받아서 어느 분석에서
// 열어도 라이브러리 14그룹 43행이 똑같이 나왔다(belle 09-03 "뭘 다 나열해놨어").
// 여기서 고정하는 축 넷:
//   1) 이 분석에 해당하는 섹션만 남는다 (defect=그룹 대표 운동, painArea=통증부위 키)
//   2) 중복이 실제로 사라진다 (first-wins)
//   3) 중복 제거는 **선택 이후**에 돈다 — 안 보이는 섹션이 운동을 가져가지 않는다
//   4) 볼 것이 없으면 빈 목록 (모달은 빈 상태 문구를 그린다)
//
// quick-260910-woq: 조인 키가 이름 → id 로 바뀌었다. 개명 회귀 축은 파일 아래쪽
// '개명 회귀' 블록에 따로 모아 뒀다.

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  buildExerciseSections,
  countExerciseRows,
  type ExerciseSectionLike,
} from '../exerciseSections.ts';

// (id, 지금 이름, 옛 영문명) — 실물 라이브러리 값과 같은 모양.
const ex = (id: string, name: string, legacyName: string) => ({ id, name, legacyName });

/** doc 의 recommendedExercises 를 id 만으로 흉내 (2026-09-10 이후 분석). */
const byId = (...ids: string[]) => ids.map((id) => ({ id }));

const SECTIONS: ExerciseSectionLike[] = [
  { key: 'grip_weak', kind: 'defect', title: '그립·악력 강화', exercises: [ex('farmers_walk', '파머스 워크', "Farmer's Walk"), ex('hand_grippers', '악력기 운동', 'Hand Grippers'), ex('deadlift', '데드리프트', 'Deadlift')] },
  { key: 'shoulder_unstable', kind: 'defect', title: '어깨 안정화', exercises: [ex('push_ups', '팔굽혀펴기', 'Push-ups'), ex('overhead_press', '어깨 위로 밀기', 'Overhead Press')] },
  { key: 'legs_not_extended', kind: 'defect', title: '다리 펴기 강화', exercises: [ex('squats', '스쿼트', 'Squats'), ex('lunges', '런지', 'Lunges')] },
  { key: 'wrist', kind: 'painArea', title: '손목 통증 보강', note: '손목 과신전 회피', exercises: [ex('farmers_walk', '파머스 워크', "Farmer's Walk"), ex('hand_grippers', '악력기 운동', 'Hand Grippers')] },
  { key: 'knee', kind: 'painArea', title: '무릎 통증 보강', note: '깊은 굴곡 회피', exercises: [ex('squats', '스쿼트', 'Squats'), ex('lunges', '런지', 'Lunges')] },
];

const keys = (s: ExerciseSectionLike[]) => s.map((x) => x.key);
const names = (s: ExerciseSectionLike[]) => s.flatMap((x) => x.exercises.map((e) => e.name));

test('이 분석의 감점 그룹만 남는다 — 나머지 라이브러리는 안 나온다', () => {
  const got = buildExerciseSections(SECTIONS, {
    exercises: byId('push_ups'),
    painAreas: [],
  });
  assert.deepEqual(keys(got), ['shoulder_unstable']);
  assert.deepEqual(names(got), ['팔굽혀펴기', '어깨 위로 밀기']);
});

test('분석마다 다른 섹션이 나온다', () => {
  const a = buildExerciseSections(SECTIONS, { exercises: byId('push_ups'), painAreas: [] });
  const b = buildExerciseSections(SECTIONS, { exercises: byId('squats'), painAreas: [] });
  assert.deepEqual(keys(a), ['shoulder_unstable']);
  assert.deepEqual(keys(b), ['legs_not_extended']);
  assert.notDeepEqual(keys(a), keys(b));
});

test('통증부위 그룹은 운동이 아니라 사용자가 고른 부위 키로 들어온다', () => {
  const got = buildExerciseSections(SECTIONS, {
    exercises: byId('push_ups'),
    painAreas: ['wrist'],
  });
  assert.deepEqual(keys(got), ['shoulder_unstable', 'wrist']);
});

test('중복이 실제로 사라진다 (first-wins)', () => {
  const got = buildExerciseSections(SECTIONS, {
    exercises: byId('farmers_walk'),
    painAreas: ['wrist'],
  });
  const all = names(got);
  assert.equal(all.length, new Set(all).size, '중복 잔존');
  // grip_weak 이 먼저라 운동을 가진다.
  assert.deepEqual(all, ['파머스 워크', '악력기 운동', '데드리프트']);
});

test('중복 제거로 비어도 회피 안내가 있으면 섹션은 남는다 (안전 정보)', () => {
  const got = buildExerciseSections(SECTIONS, {
    exercises: byId('farmers_walk'),
    painAreas: ['wrist'],
  });
  const wrist = got.find((s) => s.key === 'wrist');
  assert.ok(wrist, '통증부위 섹션이 사라짐');
  assert.equal(wrist.exercises.length, 0);
  assert.equal(wrist.note, '손목 과신전 회피');
});

test('중복 제거는 선택 이후 — 안 보이는 섹션이 운동을 가져가지 않는다', () => {
  // 통증부위 wrist 를 고르지 않았으므로 grip_weak 은 파머스 워크 를 온전히 갖는다.
  const got = buildExerciseSections(SECTIONS, {
    exercises: byId('farmers_walk'),
    painAreas: [],
  });
  assert.deepEqual(names(got), ['파머스 워크', '악력기 운동', '데드리프트']);
});

test('그룹 대표가 아닌 항목만 겹치면 그 그룹은 안 나온다 (공유 운동 딸림 방지)', () => {
  // 데드리프트 는 grip_weak 의 3번째 항목 — 대표가 아니므로 그룹이 따라 나오지 않는다.
  // 실측: 이 가드가 없으면 스쿼트 하나 때문에 둔근 그룹이 4개 doc 전부에 딸려 나왔다.
  assert.deepEqual(
    keys(buildExerciseSections(SECTIONS, { exercises: byId('deadlift'), painAreas: [] })),
    [],
  );
  assert.deepEqual(
    keys(buildExerciseSections(SECTIONS, { exercises: byId('lunges'), painAreas: [] })),
    [],
  );
});

test('처방된 운동은 모달 어딘가에 반드시 보인다 (앞면 카드와 모달이 어긋나지 않음)', () => {
  // 백엔드가 내리는 운동은 (a) 결함 그룹의 대표이거나 (b) 통증부위 그룹 항목이다.
  // 둘 다 이 규칙으로 반드시 선택되므로, 앞면에 보이는 운동이 모달에서 사라질 수 없다.
  const prescribed = ['push_ups', 'squats', 'farmers_walk'];
  const got = buildExerciseSections(SECTIONS, {
    exercises: byId(...prescribed),
    painAreas: ['wrist'],
  });
  const shown = new Set(got.flatMap((s) => s.exercises.map((e) => e.id)));
  for (const id of prescribed) {
    assert.ok(shown.has(id), `처방된 ${id} 이 모달에서 누락`);
  }
});

test('해당 그룹이 하나도 없으면 빈 목록 (모달 빈 상태)', () => {
  assert.deepEqual(buildExerciseSections(SECTIONS, { exercises: [], painAreas: [] }), []);
  assert.deepEqual(
    buildExerciseSections(SECTIONS, { exercises: byId('unknown_move'), painAreas: [] }),
    [],
  );
});

test('빈/누락 입력에 크래시 0', () => {
  assert.deepEqual(buildExerciseSections([], { exercises: byId('squats'), painAreas: ['knee'] }), []);
  assert.equal(countExerciseRows([]), 0);
});

test('countExerciseRows 는 그려질 카드 수를 센다', () => {
  const got = buildExerciseSections(SECTIONS, {
    exercises: byId('squats'),
    painAreas: ['knee'],
  });
  // legs_not_extended(스쿼트, 런지) + knee(둘 다 중복 → 0, note 로 잔존)
  assert.equal(countExerciseRows(got), 2);
  assert.deepEqual(keys(got), ['legs_not_extended', 'knee']);
});

test('원본 섹션 배열을 변형하지 않는다', () => {
  const before = JSON.stringify(SECTIONS);
  buildExerciseSections(SECTIONS, { exercises: byId('farmers_walk'), painAreas: ['wrist'] });
  assert.equal(JSON.stringify(SECTIONS), before);
});
