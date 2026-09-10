// quick-260910-woq — **동결된** id → 옛 영문 운동명 표 (2026-09-10 이전 doc 전용).
//
// 왜 필요한가: 저장된 분석 doc 은 분석 당시 운동 **이름**을 스냅샷으로 들고 있다.
// 09-10 에 이름이 영문 → 한글로 바뀌면서(quick-260910-vwh) 그 doc 들의 이름이 지금
// 라이브러리의 어느 항목과도 안 맞아 '전체 보완 운동 보기' 모달이 통째로 빈 상태가
// 됐다. id 도입(woq Task 1) 이후 doc 은 id 를 싣고 오지만, 그 이전 doc 은 이 표로만
// 되짚을 수 있다. 이 표가 없으면 오늘 이전 분석이 전부 빈 모달이다.
//
// ★ 이 표는 **동결이다.** 앞으로 belle 이 이름을 또 바꿔도 여기는 건드리지 마라.
//   여기 값은 "옛 doc 안에 실제로 저장돼 있는 문자열"이지 현재 표시명이 아니다.
//   현재 표시명 = corrective_exercises.json 의 name, 조인 키 = 같은 파일의 id.
//   출처 = git show 9ceca050~1:backend/data/corrective_exercises.json (개명 직전 본).
//
// ★ 라이브러리 JSON 안에 legacyName 필드로 두지 않은 이유 셋:
//   1) 수명이 다르다. JSON 은 살아 있는 표시 데이터고 이건 동결 이력이다. 한 파일에
//      두면 다음 개명 때 "옛 이름도 같이 고쳐야지" 하고 손대게 되고, 그 순간 폴백이
//      죽는다 — 이 작업이 막으려는 바로 그 결함이 재발한다.
//   2) 백엔드는 이 표가 필요 없다. 신 doc 은 항상 id 를 싣는다. Lambda/Pod 레이어로
//      죽은 데이터를 실어 보내지 않는다.
//   3) JSON 은 같은 운동이 여러 그룹에 중복 등재돼 있어(스쿼트 3그룹) legacyName 도
//      43벌로 늘어난다. 여기는 유니크 id 당 1행이라 자체 모순이 생길 수 없다.
//
// 커버 범위 = 라이브러리 유니크 id 28개 전부. 양방향 게이트 =
// app/src/data/__tests__/legacyExerciseNames.test.ts (누락도 고아도 fail).
//
// 참고: 팔꿈치 통증 그룹의 옛 항목이던 'Bicep/Tricep Balance' 는 vwh 가 '어깨 위로
// 밀기'(Overhead Press)로 교체해 라이브러리에서 사라졌다. 그래서 이 표에 없다.
// 통증부위 그룹은 이름이 아니라 **부위 키**로 고르므로(exerciseSections.ts) 옛 doc 이
// 그 이름을 들고 있어도 팔꿈치 섹션은 정상적으로 잡힌다.

/** 라이브러리 id → 2026-09-10 개명 이전에 doc 에 저장되던 영문명. */
export const LEGACY_EXERCISE_NAMES: Readonly<Record<string, string>> = {
  farmers_walk: "Farmer's Walk",
  hand_grippers: 'Hand Grippers',
  assisted_pull_ups: 'Assisted Pull-ups',
  dead_hang: 'Dead Hang',
  deadlift: 'Deadlift',
  push_ups: 'Push-ups',
  overhead_press: 'Overhead Press',
  scapular_depression_drills: 'Scapular Depression Drills',
  arm_circles: 'Arm Circles',
  cross_shoulder_stretch: 'Cross-Shoulder Stretch',
  planks: 'Planks',
  side_planks: 'Side Planks',
  russian_twists: 'Russian Twists',
  hanging_leg_raise: 'Hanging Leg Raise',
  supermans: 'Supermans',
  squats: 'Squats',
  lunges: 'Lunges',
  calf_raises: 'Calf Raises',
  high_kick: 'High Kick',
  lateral_leg_raise: 'Lateral Leg Raise',
  hamstring_stretch: 'Hamstring Stretch',
  hip_flexor_stretch: 'Hip Flexor Stretch',
  quad_stretch: 'Quad Stretch',
  dynamic_leg_swings: 'Dynamic Leg Swings',
  pnf_stretch: 'PNF Stretch',
  plank_with_leg_lift: 'Plank with Leg Lift',
  neck_stretch: 'Neck Stretch',
  pigeon_pose: 'Pigeon Pose',
};

/** 역방향 — 옛 영문명 → id. 옛 doc 의 이름을 라이브러리 id 로 되짚을 때 쓴다. */
export const EXERCISE_ID_BY_LEGACY_NAME: Readonly<Record<string, string>> =
  Object.fromEntries(
    Object.entries(LEGACY_EXERCISE_NAMES).map(([id, name]) => [name, id]),
  );

/**
 * doc 의 운동 1건을 라이브러리 id 로 되짚는다.
 *
 * - 신 doc(2026-09-10 이후): `id` 를 그대로 쓴다.
 * - 옛 doc: 저장된 옛 영문명을 이 표로 되짚는다.
 * - 둘 다 안 되면 null — **지어내지 않는다** (조용한 오매칭 금지).
 */
export function resolveExerciseId(ref: {
  id?: string | null;
  name?: string | null;
}): string | null {
  if (typeof ref?.id === 'string' && ref.id.length > 0) return ref.id;
  const name = typeof ref?.name === 'string' ? ref.name : '';
  return EXERCISE_ID_BY_LEGACY_NAME[name] ?? null;
}
