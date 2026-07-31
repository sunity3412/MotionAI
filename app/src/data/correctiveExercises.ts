// Phase 13 (Plan 13-A, PERS-03) — 전체 보완 운동 라이브러리 (browse data source).
//
// HIGH-2 (13-REVIEW-FIXES.md §5): app mirror = backend/data/corrective_exercises.json
// 의 byte-for-byte 복사(./corrective_exercises.json) + 본 typed wrapper. manual TS
// object 금지 — backend JSON 이 canonical, app JSON 은 그 복사. drift 는
// backend/tests/phase13/test_corrective_exercises_app_lockstep.py 가 full-content
// deep-equal 로 방어한다.
//
// 이 모듈은 "다른 운동 보기" 모달(RecommendedExerciseModal)이 읽는 전체 라이브러리
// source — Firestore result.recommendedExercises(3~5 개인화 subset)이 아니다.

import data from './corrective_exercises.json';
import type { RecommendedExercise } from '../types/analysis';

// corrective_exercises.json 의 운동 항목 모양 (RecommendedExercise 호환 — sourceRef
// 는 fixture 에서 항상 채워지나 계약상 옵셔널).
export interface CorrectiveExercise extends RecommendedExercise {
  sourceRef: string;
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

// 모달이 한 평면 목록으로 browse 할 수 있게 결함 + 통증부위 운동을 펼친 헬퍼.
// 결함 그룹 먼저, 통증부위 그룹 다음 — name 중복 제거 (라이브러리 내 같은 운동 공유).
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
