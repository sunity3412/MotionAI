// Phase 13 (Plan 13-A, PERS-03) — 전체 보완 운동 라이브러리 (browse data source).
//
// HIGH-2 (13-REVIEW-FIXES.md §5): app mirror = backend/data/corrective_exercises.json
// 의 byte-for-byte 복사(./corrective_exercises.json) + 본 typed wrapper. manual TS
// object 금지 — backend JSON 이 canonical, app JSON 은 그 복사. drift 는
// backend/tests/phase13/test_corrective_exercises_app_lockstep.py 가 full-content
// deep-equal 로 방어한다.
//
// 이 모듈은 "다른 운동 보기" 모달(RecommendedExerciseModal)이 읽는 전체 라이브러리
// source — Firestore result.recommendedExercises(개인화 subset)이 아니다. 모달은
// 이 전체 목록에서 **이 분석에 해당하는 그룹만** 골라 그린다 (quick-260910-pbs,
// 선택 규칙 = lib/exerciseSections.ts).

import data from './corrective_exercises.json';
import type { ExerciseKind, RecommendedExercise } from '../types/analysis';

// corrective_exercises.json 의 운동 항목 모양 (RecommendedExercise 호환 — sourceRef
// 와 kind 는 fixture 에서 항상 채워지나 계약상 옵셔널).
export interface CorrectiveExercise extends RecommendedExercise {
  sourceRef: string;
  kind: ExerciseKind;
}

// 운동 성격의 한글 표시명 — **여기 한 곳**에만 둔다 (quick-260910-vwh Task 2).
// belle 이 문구를 바꿀 때 이 3줄만 고치면 되고 백엔드 재배포가 필요 없다.
// ★ 이 값으로 운동 개수를 배분하지 않는다 (belle 2026-09-10 "근력이 충분한데
// 뭐하러 헬스를 하겠어" — 강제 혼합 기각). 표시만 한다.
export const EXERCISE_KIND_LABELS: Record<ExerciseKind, string> = {
  strength: '근력',
  flexibility: '유연성',
  warmup: '준비운동',
};

/** 성격 표시명. 옛 doc(2026-09-10 이전 분석)은 kind 가 없어 null → 표시 생략. */
export function exerciseKindLabel(kind?: string | null): string | null {
  if (typeof kind !== 'string') return null;
  return EXERCISE_KIND_LABELS[kind as ExerciseKind] ?? null;
}

export interface CorrectiveDefect {
  triggers: { sourceSignals: string[]; jointHints: string[] };
  exercises: CorrectiveExercise[];
}

export interface CorrectivePainArea {
  avoid: string;
  exercises: CorrectiveExercise[];
}

export interface CorrectiveLibrary {
  schemaVersion: string;
  lastUpdated: string;
  sourceNotebook: string;
  sourceNotebookName: string;
  defects: Record<string, CorrectiveDefect>;
  painAreas: Record<string, CorrectivePainArea>;
}

export const CORRECTIVE_EXERCISES = data as CorrectiveLibrary;
export const CORRECTIVE_SCHEMA_VERSION = (data as CorrectiveLibrary).schemaVersion;

// 모달이 browse 할 수 있게 결함 + 통증부위 운동을 그룹 단위로 펼친 목록.
// 결함 그룹 먼저, 통증부위 그룹 다음.
//
// name 중복 제거는 **여기서 하지 않는다** (quick-260910-pbs — 종전 주석은 제거를
// 약속했으나 구현이 없었고, 여기서 제거하면 안 된다는 것이 그 사이 밝혀졌다):
// 라이브러리는 같은 운동을 여러 그룹이 공유하므로(스쿼트 = 다리 펴기 + 둔근 안정화
// + 무릎 통증), 전체 목록에서 먼저 잘라내면 **표시되지 않는 그룹이 이름을 가져가**
// 정작 보여줄 그룹에서 그 운동이 사라진다. 그래서 중복 제거는 분석별 선택 이후에
// buildExerciseSections(lib/exerciseSections.ts)가 수행한다 — 사용자가 보는 목록에
// 중복이 없다는 약속은 거기서 지켜지고, node --test 로 검증된다.
export interface CorrectiveSection {
  key: string; // 그룹 키 (defect key 또는 painArea key)
  kind: 'defect' | 'painArea';
  title: string; // 사용자 표시 그룹 제목 (한국어)
  note?: string; // painArea avoid 안전 라인 (있으면)
  exercises: CorrectiveExercise[];
}

const DEFECT_TITLES: Record<string, string> = {
  grip_weak: '그립·악력 강화',
  shoulder_unstable: '어깨 안정화',
  core_weak: '코어 강화',
  legs_not_extended: '다리 펴기 강화',
  hip_hamstring_tight: '고관절·유연성',
  glute_hip_unstable: '둔근·골반 안정화',
};

const PAIN_AREA_TITLES: Record<string, string> = {
  shoulder: '어깨 통증 보강',
  wrist: '손목 통증 보강',
  lower_back: '허리 통증 보강',
  knee: '무릎 통증 보강',
  ankle: '발목 통증 보강',
  neck: '목 통증 보강',
  hip: '고관절 통증 보강',
  elbow: '팔꿈치 통증 보강',
};

export const CORRECTIVE_SECTIONS: CorrectiveSection[] = [
  ...Object.entries(CORRECTIVE_EXERCISES.defects).map(([key, d]) => ({
    key,
    kind: 'defect' as const,
    title: DEFECT_TITLES[key] ?? key,
    exercises: d.exercises,
  })),
  ...Object.entries(CORRECTIVE_EXERCISES.painAreas).map(([key, p]) => ({
    key,
    kind: 'painArea' as const,
    title: PAIN_AREA_TITLES[key] ?? key,
    note: p.avoid,
    exercises: p.exercises,
  })),
];

export const CORRECTIVE_LIBRARY_HAS_ITEMS = CORRECTIVE_SECTIONS.some(
  (s) => s.exercises.length > 0
);
