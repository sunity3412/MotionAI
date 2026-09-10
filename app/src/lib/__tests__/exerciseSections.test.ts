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

// ── 개명 회귀 (quick-260910-woq) ────────────────────────────────────────────
//
// 이 블록이 막는 사고: 2026-09-10 에 운동 이름이 영문 → 한글로 바뀌자
// (quick-260910-vwh), 이름으로 조인하던 이 함수의 매칭이 0 이 되어 **개명 이전
// 모든 사용자의 모달이 빈 화면**이 됐다. 시뮬레이터에서 눈으로 보고서야 알았다.
// 아래 세 축은 그 사고를 코드로 재현해 두는 것이다 — 다음에 belle 이 문구를
// 다듬을 때 사람이 아니라 테스트가 먼저 막는다.

/** 표시명만 바꾼 라이브러리 (id·legacyName 은 그대로) — 다음 개명을 흉내낸다. */
const RENAMED: ExerciseSectionLike[] = SECTIONS.map((s) => ({
  ...s,
  exercises: s.exercises.map((e) => ({ ...e, name: `개명-${e.name}` })),
}));

test('축1 id 가 그대로면 이름이 바뀌어도 섹션이 유지된다 (이 결함의 직접 재현)', () => {
  // 분석 당시 저장된 doc — id 와 그때의 이름을 함께 들고 있다.
  const doc = [{ id: 'push_ups', name: '팔굽혀펴기' }];

  // 전제 확인: 저장된 이름은 개명 후 라이브러리 어디에도 없다. 이름으로 조인하면
  // 여기서 반드시 0 이 된다 — 그게 종전 구현이 무너진 지점이다.
  const liveNames = new Set(RENAMED.flatMap((s) => s.exercises.map((e) => e.name)));
  assert.equal(liveNames.has('팔굽혀펴기'), false, '전제가 깨졌다 — 개명 흉내가 안 됐다');

  const got = buildExerciseSections(RENAMED, { exercises: doc, painAreas: [] });
  assert.deepEqual(keys(got), ['shoulder_unstable'], '개명만으로 섹션이 사라졌다');
  assert.deepEqual(names(got), ['개명-팔굽혀펴기', '개명-어깨 위로 밀기']);
});

test('축1-b 중복 제거도 id 기준 — 개명해도 같은 운동이 두 번 안 나온다', () => {
  const got = buildExerciseSections(RENAMED, {
    exercises: [{ id: 'farmers_walk' }],
    painAreas: ['wrist'],
  });
  const ids = got.flatMap((s) => s.exercises.map((e) => e.id));
  assert.equal(ids.length, new Set(ids).size, '같은 id 가 두 번 그려진다');
  assert.deepEqual(ids, ['farmers_walk', 'hand_grippers', 'deadlift']);
});

test('축2 id 없는 옛 doc 은 옛 영문명으로 잡힌다 (폴백이 없으면 빈 모달)', () => {
  // 실물 검증본 doc(c64afae6)이 들고 있던 모양 — id 없음, 옛 영문명.
  const legacyDoc = [
    { name: 'Push-ups' },
    { name: 'Overhead Press' },
    { name: 'Scapular Depression Drills' },
  ];
  const got = buildExerciseSections(SECTIONS, { exercises: legacyDoc, painAreas: [] });
  assert.deepEqual(keys(got), ['shoulder_unstable']);
  assert.deepEqual(names(got), ['팔굽혀펴기', '어깨 위로 밀기']);

  // 옛 이름 표(legacyName)가 없으면 같은 doc 이 빈 목록이 된다는 것도 같이 박제한다.
  // 이 대조군이 없으면 "폴백을 지워도 테스트가 안 깨지는" 상태가 되어 축2 가
  // 무의미해진다. 실물 검증본 doc 으로 잰 값과 같다 — 폴백 있음 5행 / 없음 0행.
  const withoutLegacy = SECTIONS.map((sec) => ({
    ...sec,
    exercises: sec.exercises.map(({ id, name }) => ({ id, name })),
  }));
  assert.deepEqual(
    buildExerciseSections(withoutLegacy, { exercises: legacyDoc, painAreas: [] }),
    [],
    '옛 이름 표 없이도 잡힌다면 이 축은 폴백을 검사하지 않는 것이다',
  );
});

test('축2-b 개명과 id 도입 사이에 만들어진 doc 은 지금 이름으로 잡힌다', () => {
  // vwh(한글 개명) ~ woq(id 도입) 사이 doc: id 도 없고 옛 영문명도 아니다.
  const got = buildExerciseSections(SECTIONS, {
    exercises: [{ name: '팔굽혀펴기' }],
    painAreas: [],
  });
  assert.deepEqual(keys(got), ['shoulder_unstable']);
});

test('축3 id 도 이름도 안 맞으면 빈 목록 — 조용한 오매칭 금지', () => {
  assert.deepEqual(
    keys(buildExerciseSections(SECTIONS, {
      exercises: [{ id: 'no_such_id', name: '없는 운동' }],
      painAreas: [],
    })),
    [],
  );
  // 라이브러리에서 사라진 옛 운동(vwh 가 교체한 팔꿈치 항목)도 아무것도 못 끌어온다.
  assert.deepEqual(
    keys(buildExerciseSections(SECTIONS, {
      exercises: [{ name: 'Bicep/Tricep Balance' }],
      painAreas: [],
    })),
    [],
  );
});

test('축3-b id 를 가진 doc 에는 이름 폴백을 열지 않는다 (오매칭 차단)', () => {
  // 개명으로 서로 다른 두 운동이 한 이름을 나눠 갖는 날을 가정한다. doc 은 A 를
  // 가리키는 id 를 들고 있는데, 지금 라이브러리에서 그 이름은 B 가 쓴다.
  // 이름까지 열어 두면 B 그룹이 조용히 딸려 나온다 — 그러면 안 된다.
  const collided: ExerciseSectionLike[] = [
    { key: 'legs_not_extended', kind: 'defect', title: '다리 펴기 강화',
      exercises: [{ id: 'squats', name: '하체 스쿼트', legacyName: 'Squats' }] },
    { key: 'grip_weak', kind: 'defect', title: '그립·악력 강화',
      exercises: [{ id: 'deadlift', name: '스쿼트', legacyName: 'Deadlift' }] },
  ];
  const got = buildExerciseSections(collided, {
    exercises: [{ id: 'squats', name: '스쿼트' }],
    painAreas: [],
  });
  assert.deepEqual(keys(got), ['legs_not_extended'], 'id 를 무시하고 이름으로 끌려갔다');
});

test('축1-c 그룹마다 이름이 어긋나도 같은 운동은 한 번만 그려진다 (dedup 이 id 기준)', () => {
  // 개명이 그룹별로 어긋나게 반영된 상황. 이름 기준 dedup 이었다면 파머스 워크가
  // 두 벌 그려진다 — 사용자에겐 같은 운동이 두 번 나온 것으로 보인다.
  const drifted: ExerciseSectionLike[] = [
    { key: 'grip_weak', kind: 'defect', title: '그립·악력 강화',
      exercises: [ex('farmers_walk', '파머스 워크', "Farmer's Walk")] },
    { key: 'wrist', kind: 'painArea', title: '손목 통증 보강', note: '손목 과신전 회피',
      exercises: [ex('farmers_walk', '가방 들고 걷기', "Farmer's Walk")] },
  ];
  const got = buildExerciseSections(drifted, {
    exercises: byId('farmers_walk'),
    painAreas: ['wrist'],
  });
  const ids = got.flatMap((s) => s.exercises.map((e) => e.id));
  assert.deepEqual(ids, ['farmers_walk'], `같은 운동이 두 벌 그려졌다: ${ids}`);
  assert.deepEqual(names(got), ['파머스 워크']);
});
