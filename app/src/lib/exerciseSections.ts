// quick-260910-pbs — '전체 보완 운동 보기' 모달이 **이 분석 것만** 그리게 하는 순수 뷰모델.
//
// belle 2026-09-03: "뭐가 이렇게 많아. 뭘 다 나열해놨어. 동작별로 어울리는 거
// 부위별로 한 두개씩만 대표로 나오도록 축소하자 그게 더 신뢰도를 줄 듯."
//
// 착수 전 실측: 모달 props 가 `{visible, onClose}` 뿐이라 어느 분석에서 열어도
// 라이브러리 14그룹 43행이 그대로 나왔다(이름 기준 유니크 29 — 14행이 중복).
//
// 여기서 하는 일 셋 (순서가 중요하다):
//   1) 이 분석에 해당하는 섹션만 고른다
//   2) 그 다음에 이름 중복을 제거한다
//   3) 볼 것이 아무것도 안 남은 섹션을 버린다
//
// 왜 "고르고 나서 중복 제거"인가 — 반대로 하면 표시되지 않는 섹션이 먼저 이름을
// 가져가 버려서, 정작 보여줄 섹션에서 그 운동이 사라진다(백엔드가 대표로 뽑은
// 운동이 모달에선 안 보이는 구멍). 그래서 dedup 은 선택 이후에만 돈다.
//
// 이 모듈은 corrective_exercises.json 을 import 하지 않는다 — 섹션 배열을 인자로
// 받는 순수 함수라 node --test 로 그대로 검증된다.

export interface ExerciseSectionLike {
  key: string;
  kind: 'defect' | 'painArea';
  title: string;
  note?: string;
  exercises: { name: string }[];
}

export interface ExerciseSectionQuery {
  // 이 분석의 result.recommendedExercises 이름들 (백엔드 exercise_map 산출).
  // 감점 부위/통증부위는 백엔드가 이미 결함 그룹으로 접어 **각 그룹의 대표**를
  // 넣어 뒀으므로, 앱은 그 대표가 속한 그룹을 펼치기만 한다 — 부위 어휘를 TS 에
  // 복제하지 않는다 (복제하면 백엔드 vision_veto 어휘와 조용히 어긋난다).
  exerciseNames: readonly string[];
  // 분석 당시 bodyProfile.painAreas snapshot. 통증부위 그룹은 이름이 아니라
  // 이 키로 고른다 — 통증은 분석이 아니라 사용자가 말한 것이기 때문이다.
  painAreas: readonly string[];
}

/**
 * 이 분석에 해당하는 섹션만 골라 중복 없는 목록으로 만든다.
 *
 * - defect 그룹: **그 그룹의 대표 운동**(첫 항목)이 recommendedExercises 에 있으면
 *   포함. 아무 항목이나 매칭하면 안 된다 — 라이브러리는 같은 운동을 여러 그룹이
 *   공유해서(Squats = 다리 펴기 + 둔근 안정화 + 무릎 통증), 무릎 감점 하나에
 *   둔근 그룹까지 딸려 나온다(실측: 4개 doc 전부에서 둔근 그룹이 따라 나왔다).
 *   백엔드 exercise_map 은 그룹당 **앞에서부터** 대표를 뽑으므로(_EXERCISES_PER_DEFECT),
 *   "대표가 처방됐는가"가 곧 "이 그룹이 선택됐는가"다. 그룹당 개수를 2로 올려도
 *   대표는 늘 포함되므로 이 대응은 유지된다.
 * - painArea 그룹: 그 부위를 사용자가 통증부위로 선택했으면 포함.
 * - 이름 중복은 앞선 섹션이 가진다(first-wins, 입력 순서 = 표시 순서).
 * - 운동이 하나도 안 남은 섹션은 버린다. 단 **회피 안내(note)가 있으면 남긴다** —
 *   통증부위의 회피 문구는 운동 목록과 별개로 그 자체가 안전 정보다.
 */
export function buildExerciseSections<T extends ExerciseSectionLike>(
  sections: readonly T[],
  query: ExerciseSectionQuery,
): T[] {
  const wantedNames = new Set(query.exerciseNames ?? []);
  const wantedAreas = new Set(query.painAreas ?? []);

  const selected = (sections ?? []).filter((s) =>
    s.kind === 'painArea'
      ? wantedAreas.has(s.key)
      : s.exercises.length > 0 && wantedNames.has(s.exercises[0].name),
  );

  const seen = new Set<string>();
  const out: T[] = [];
  for (const section of selected) {
    const exercises = section.exercises.filter((ex) => {
      if (seen.has(ex.name)) return false;
      seen.add(ex.name);
      return true;
    });
    if (exercises.length === 0 && !section.note) continue;
    out.push({ ...section, exercises });
  }
  return out;
}

/** 모달에 실제로 그려질 운동 카드 수 (빈 상태 판정 · 검증용). */
export function countExerciseRows(sections: readonly ExerciseSectionLike[]): number {
  return (sections ?? []).reduce((n, s) => n + s.exercises.length, 0);
}
