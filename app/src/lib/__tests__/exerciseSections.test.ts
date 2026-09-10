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
//   2) 이름 중복이 실제로 사라진다 (first-wins)
//   3) 중복 제거는 **선택 이후**에 돈다 — 안 보이는 섹션이 이름을 가져가지 않는다
//   4) 볼 것이 없으면 빈 목록 (모달은 빈 상태 문구를 그린다)

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  buildExerciseSections,
  countExerciseRows,
  type ExerciseSectionLike,
} from '../exerciseSections.ts';

const ex = (name: string) => ({ name });

const SECTIONS: ExerciseSectionLike[] = [
  { key: 'grip_weak', kind: 'defect', title: '그립·악력 강화', exercises: [ex("Farmer's Walk"), ex('Hand Grippers'), ex('Deadlift')] },
  { key: 'shoulder_unstable', kind: 'defect', title: '어깨 안정화', exercises: [ex('Push-ups'), ex('Overhead Press')] },
  { key: 'legs_not_extended', kind: 'defect', title: '다리 펴기 강화', exercises: [ex('Squats'), ex('Lunges')] },
  { key: 'wrist', kind: 'painArea', title: '손목 통증 보강', note: '손목 과신전 회피', exercises: [ex("Farmer's Walk"), ex('Hand Grippers')] },
  { key: 'knee', kind: 'painArea', title: '무릎 통증 보강', note: '깊은 굴곡 회피', exercises: [ex('Squats'), ex('Lunges')] },
];

const keys = (s: ExerciseSectionLike[]) => s.map((x) => x.key);
const names = (s: ExerciseSectionLike[]) => s.flatMap((x) => x.exercises.map((e) => e.name));

test('이 분석의 감점 그룹만 남는다 — 나머지 라이브러리는 안 나온다', () => {
  const got = buildExerciseSections(SECTIONS, {
    exerciseNames: ['Push-ups'],
    painAreas: [],
  });
  assert.deepEqual(keys(got), ['shoulder_unstable']);
  assert.deepEqual(names(got), ['Push-ups', 'Overhead Press']);
});

test('분석마다 다른 섹션이 나온다', () => {
  const a = buildExerciseSections(SECTIONS, { exerciseNames: ['Push-ups'], painAreas: [] });
  const b = buildExerciseSections(SECTIONS, { exerciseNames: ['Squats'], painAreas: [] });
  assert.deepEqual(keys(a), ['shoulder_unstable']);
  assert.deepEqual(keys(b), ['legs_not_extended']);
  assert.notDeepEqual(keys(a), keys(b));
});

test('통증부위 그룹은 이름이 아니라 사용자가 고른 부위 키로 들어온다', () => {
  const got = buildExerciseSections(SECTIONS, {
    exerciseNames: ['Push-ups'],
    painAreas: ['wrist'],
  });
  assert.deepEqual(keys(got), ['shoulder_unstable', 'wrist']);
});

test('이름 중복이 실제로 사라진다 (first-wins)', () => {
  const got = buildExerciseSections(SECTIONS, {
    exerciseNames: ["Farmer's Walk"],
    painAreas: ['wrist'],
  });
  const all = names(got);
  assert.equal(all.length, new Set(all).size, '중복 name 잔존');
  // grip_weak 이 먼저라 이름을 가진다.
  assert.deepEqual(all, ["Farmer's Walk", 'Hand Grippers', 'Deadlift']);
});

test('중복 제거로 비어도 회피 안내가 있으면 섹션은 남는다 (안전 정보)', () => {
  const got = buildExerciseSections(SECTIONS, {
    exerciseNames: ["Farmer's Walk"],
    painAreas: ['wrist'],
  });
  const wrist = got.find((s) => s.key === 'wrist');
  assert.ok(wrist, '통증부위 섹션이 사라짐');
  assert.equal(wrist.exercises.length, 0);
  assert.equal(wrist.note, '손목 과신전 회피');
});

test('중복 제거는 선택 이후 — 안 보이는 섹션이 이름을 가져가지 않는다', () => {
  // 통증부위 wrist 를 고르지 않았으므로 grip_weak 은 Farmer's Walk 를 온전히 갖는다.
  const got = buildExerciseSections(SECTIONS, {
    exerciseNames: ["Farmer's Walk"],
    painAreas: [],
  });
  assert.deepEqual(names(got), ["Farmer's Walk", 'Hand Grippers', 'Deadlift']);
});

test('그룹 대표가 아닌 항목만 겹치면 그 그룹은 안 나온다 (공유 운동 딸림 방지)', () => {
  // Deadlift 는 grip_weak 의 3번째 항목 — 대표가 아니므로 그룹이 따라 나오지 않는다.
  // 실측: 이 가드가 없으면 Squats 하나 때문에 둔근 그룹이 4개 doc 전부에 딸려 나왔다.
  assert.deepEqual(
    keys(buildExerciseSections(SECTIONS, { exerciseNames: ['Deadlift'], painAreas: [] })),
    [],
  );
  assert.deepEqual(
    keys(buildExerciseSections(SECTIONS, { exerciseNames: ['Lunges'], painAreas: [] })),
    [],
  );
});

test('처방된 운동은 모달 어딘가에 반드시 보인다 (앞면 카드와 모달이 어긋나지 않음)', () => {
  // 백엔드가 내리는 이름은 (a) 결함 그룹의 대표이거나 (b) 통증부위 그룹 항목이다.
  // 둘 다 이 규칙으로 반드시 선택되므로, 앞면에 보이는 운동이 모달에서 사라질 수 없다.
  const prescribed = ['Push-ups', 'Squats', "Farmer's Walk"];
  const got = buildExerciseSections(SECTIONS, {
    exerciseNames: prescribed,
    painAreas: ['wrist'],
  });
  const shown = new Set(names(got));
  for (const name of prescribed) {
    assert.ok(shown.has(name), `처방된 ${name} 이 모달에서 누락`);
  }
});

test('해당 그룹이 하나도 없으면 빈 목록 (모달 빈 상태)', () => {
  assert.deepEqual(buildExerciseSections(SECTIONS, { exerciseNames: [], painAreas: [] }), []);
  assert.deepEqual(
    buildExerciseSections(SECTIONS, { exerciseNames: ['Unknown Move'], painAreas: [] }),
    [],
  );
});

test('빈/누락 입력에 크래시 0', () => {
  assert.deepEqual(buildExerciseSections([], { exerciseNames: ['Squats'], painAreas: ['knee'] }), []);
  assert.equal(countExerciseRows([]), 0);
});

test('countExerciseRows 는 그려질 카드 수를 센다', () => {
  const got = buildExerciseSections(SECTIONS, {
    exerciseNames: ['Squats'],
    painAreas: ['knee'],
  });
  // legs_not_extended(Squats, Lunges) + knee(둘 다 중복 → 0, note 로 잔존)
  assert.equal(countExerciseRows(got), 2);
  assert.deepEqual(keys(got), ['legs_not_extended', 'knee']);
});

test('원본 섹션 배열을 변형하지 않는다', () => {
  const before = JSON.stringify(SECTIONS);
  buildExerciseSections(SECTIONS, { exerciseNames: ["Farmer's Walk"], painAreas: ['wrist'] });
  assert.equal(JSON.stringify(SECTIONS), before);
});
