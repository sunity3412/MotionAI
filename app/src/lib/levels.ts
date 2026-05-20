// 레벨별 기대 점수 — 파일럿 픽스처. 데이터 누적되면 실 평균치로 교체.
//
// KISMAM 점수(0~100)는 폴스포츠 정상 범위(skeleton tolerance) 대비 Z-score
// 가우시안 평가라 이미 절대값으로 의미가 있다. 다만 사용자가 "76점이 어디쯤?"
// 즉답하려면 레벨대를 함께 보여야 함 → 이 상수.

import type { SkillLevel } from '../types/analysis';

export const LEVEL_EXPECTED_SCORE: Record<SkillLevel, number> = {
  basic: 65,
  intermediate: 78,
  advanced: 88,
};

export const LEVEL_LABEL_KO: Record<SkillLevel, string> = {
  basic: '입문',
  intermediate: '중급',
  advanced: '고급',
};

export type ScoreBand = 'sub_basic' | SkillLevel;

export interface LevelStanding {
  band: ScoreBand; // 현재 점수가 속한 구간
  nextTargetLevel: SkillLevel | null; // 다음 도전 레벨 (고급 달성이면 null)
  nextTargetScore: number | null;
  // 사용자에게 보여줄 한 줄 요약 — 점수의 위치를 즉각 인지하도록
  summary: string;
}

export function levelStanding(score: number): LevelStanding {
  const b = LEVEL_EXPECTED_SCORE.basic;
  const i = LEVEL_EXPECTED_SCORE.intermediate;
  const a = LEVEL_EXPECTED_SCORE.advanced;

  if (score >= a) {
    return {
      band: 'advanced',
      nextTargetLevel: null,
      nextTargetScore: null,
      summary: `고급 평균(${a}) 도달 — 정말 잘하고 있어요`,
    };
  }
  if (score >= i) {
    return {
      band: 'intermediate',
      nextTargetLevel: 'advanced',
      nextTargetScore: a,
      summary: `중급 평균(${i}) 이상 · 고급(${a})까지 ${a - score}점`,
    };
  }
  if (score >= b) {
    return {
      band: 'basic',
      nextTargetLevel: 'intermediate',
      nextTargetScore: i,
      summary: `입문 평균(${b}) 이상 · 중급(${i})까지 ${i - score}점`,
    };
  }
  return {
    band: 'sub_basic',
    nextTargetLevel: 'basic',
    nextTargetScore: b,
    summary: `입문 평균(${b})까지 ${b - score}점`,
  };
}
