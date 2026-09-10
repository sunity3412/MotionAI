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
//   2) 그 다음에 중복을 제거한다
//   3) 볼 것이 아무것도 안 남은 섹션을 버린다
//
// 왜 "고르고 나서 중복 제거"인가 — 반대로 하면 표시되지 않는 섹션이 먼저 운동을
// 가져가 버려서, 정작 보여줄 섹션에서 그 운동이 사라진다(백엔드가 대표로 뽑은
// 운동이 모달에선 안 보이는 구멍). 그래서 dedup 은 선택 이후에만 돈다.
//
// ── quick-260910-woq: 조인 키를 이름에서 **id** 로 옮겼다 ──────────────────
// 09-10 개명(quick-260910-vwh, 영문 → 한글) 직후 기존 분석의 모달이 전부
// "이번 분석에서 짚인 보완 부위가 없어요" 빈 상태가 됐다. 원인은 여기가 이름
// 문자열로 조인했기 때문이다 — doc 의 이름은 **분석 당시 스냅샷**이고
// `s.exercises[0].name` 은 **지금 라이브러리**의 이름이라, 이름이 바뀌는 순간
// 매칭이 0 이 된다. 이름은 표시 전용이고 조인은 id 로 한다. 그래야 belle 이
// 문구를 또 다듬어도 과거 분석이 안 끊긴다.
// ★ 옛 doc(id 미보유)은 이름 폴백으로 받는다 — 폴백이 없으면 오늘 이전 분석이
//   전부 빈 모달이다. 규칙은 아래 `_splitQuery` 주석에.
//
// 이 모듈은 corrective_exercises.json 을 import 하지 않는다 — 섹션 배열을 인자로
// 받는 순수 함수라 node --test 로 그대로 검증된다.

/** 라이브러리 운동 1건 중 이 모듈이 보는 부분만. */
export interface ExerciseSectionExerciseLike {
  // 라이브러리 식별자 (corrective_exercises.json 의 id). 표시명이 바뀌어도 안 바뀐다.
  id: string;
  // 표시명 (한글 통용명). **조인에 쓰지 않는다.**
  name: string;
  // 2026-09-10 개명 이전 doc 이 들고 있는 옛 영문명 (data/legacyExerciseNames.ts).
  // 섹션을 만드는 쪽(data/correctiveExercises.ts)이 붙여 준다.
  legacyName?: string;
}

export interface ExerciseSectionLike {
  key: string;
  kind: 'defect' | 'painArea';
  title: string;
  note?: string;
  exercises: ExerciseSectionExerciseLike[];
}

/** doc 의 `result.recommendedExercises` 1건 중 조인에 쓰는 부분만. */
export interface RecommendedExerciseRef {
  // 2026-09-10 이후 분석만 보유. 옛 doc 은 없다.
  id?: string | null;
  name?: string | null;
}

export interface ExerciseSectionQuery {
  // 이 분석의 result.recommendedExercises (백엔드 exercise_map 산출).
  // 감점 부위/통증부위는 백엔드가 이미 결함 그룹으로 접어 **각 그룹의 대표**를
  // 넣어 뒀으므로, 앱은 그 대표가 속한 그룹을 펼치기만 한다 — 부위 어휘를 TS 에
  // 복제하지 않는다 (복제하면 백엔드 vision_veto 어휘와 조용히 어긋난다).
  exercises: readonly RecommendedExerciseRef[];
  // 분석 당시 bodyProfile.painAreas snapshot. 통증부위 그룹은 운동이 아니라
  // 이 키로 고른다 — 통증은 분석이 아니라 사용자가 말한 것이기 때문이다.
  // 그래서 개명은 통증부위 그룹 선택에 영향을 주지 않는다.
  painAreas: readonly string[];
}

/**
 * 질의를 id 집합과 **레거시 이름 집합**으로 가른다.
 *
 * 규칙: id 를 가진 항목은 id 로만 본다. 이름은 **id 가 없는 항목에서만** 걷는다.
 * 왜 신 doc 의 이름까지 열어 두지 않는가 — 개명으로 서로 다른 두 운동이 한 이름을
 * 나눠 갖는 날(A 가 쓰던 이름을 B 가 물려받는 경우) 조용한 오매칭이 생긴다.
 * 폴백은 되짚을 다른 수단이 없는 옛 doc 에만 열어 준다.
 */
function _splitQuery(exercises: readonly RecommendedExerciseRef[] | undefined) {
  const ids = new Set<string>();
  const legacyNames = new Set<string>();
  for (const ex of exercises ?? []) {
    const id = typeof ex?.id === 'string' ? ex.id : '';
    if (id.length > 0) {
      ids.add(id);
      continue;
    }
    const name = typeof ex?.name === 'string' ? ex.name : '';
    if (name.length > 0) legacyNames.add(name);
  }
  return { ids, legacyNames };
}

/**
 * 이 분석에 해당하는 섹션만 골라 중복 없는 목록으로 만든다.
 *
 * - defect 그룹: **그 그룹의 대표 운동**(첫 항목)이 recommendedExercises 에 있으면
 *   포함. 아무 항목이나 매칭하면 안 된다 — 라이브러리는 같은 운동을 여러 그룹이
 *   공유해서(스쿼트 = 다리 펴기 + 둔근 안정화 + 무릎 통증), 무릎 감점 하나에
 *   둔근 그룹까지 딸려 나온다(실측: 4개 doc 전부에서 둔근 그룹이 따라 나왔다).
 *   백엔드 exercise_map 은 그룹당 **앞에서부터** 대표를 뽑으므로(_EXERCISES_PER_DEFECT),
 *   "대표가 처방됐는가"가 곧 "이 그룹이 선택됐는가"다. 그룹당 개수를 2로 올려도
 *   대표는 늘 포함되므로 이 대응은 유지된다.
 * - painArea 그룹: 그 부위를 사용자가 통증부위로 선택했으면 포함.
 * - 중복은 앞선 섹션이 가진다(first-wins, 입력 순서 = 표시 순서). 중복 판정도
 *   **id 기준**이다 — 이름 기준이면 같은 운동이 그룹마다 다른 이름을 갖게 되는 날
 *   같은 것이 두 번 그려진다.
 * - 운동이 하나도 안 남은 섹션은 버린다. 단 **회피 안내(note)가 있으면 남긴다** —
 *   통증부위의 회피 문구는 운동 목록과 별개로 그 자체가 안전 정보다.
 *
 * 매칭 우선순위 (quick-260910-woq):
 *   1) id — 2026-09-10 이후 doc. 개명에 안 흔들리는 정상 경로.
 *   2) 옛 영문명(legacyName) — 개명 이전 doc. **이 폴백이 이 함수의 존재 이유다.**
 *   3) 지금 이름(name) — 개명(vwh)과 id 도입(woq) 사이에 만들어진 doc 은 id 도
 *      없고 옛 영문명도 아니라 지금 이름으로만 잡힌다. (2)와 같은 폴백 경로라
 *      id 를 가진 doc 에는 적용되지 않는다.
 */
export function buildExerciseSections<T extends ExerciseSectionLike>(
  sections: readonly T[],
  query: ExerciseSectionQuery,
): T[] {
  const { ids, legacyNames } = _splitQuery(query.exercises);
  const wantedAreas = new Set(query.painAreas ?? []);

  const wanted = (ex: ExerciseSectionExerciseLike): boolean => {
    if (ids.has(ex.id)) return true;
    if (legacyNames.size === 0) return false;
    if (typeof ex.legacyName === 'string' && legacyNames.has(ex.legacyName)) return true;
    return legacyNames.has(ex.name);
  };

  const selected = (sections ?? []).filter((s) =>
    s.kind === 'painArea'
      ? wantedAreas.has(s.key)
      : s.exercises.length > 0 && wanted(s.exercises[0]),
  );

  const seen = new Set<string>();
  const out: T[] = [];
  for (const section of selected) {
    const exercises = section.exercises.filter((ex) => {
      if (seen.has(ex.id)) return false;
      seen.add(ex.id);
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
