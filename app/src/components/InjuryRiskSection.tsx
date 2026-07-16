// Phase 10 (10-02 D-08 / SAFE-01) — 부상 위험 신호 경고 섹션.
//
// 결정론(LLM 무관) SafetyFlag 레이어(safety_flags.py)를 결과 화면의 시각적으로
// 구분되는 amber 경고 섹션으로 렌더한다 (10-UI-SPEC Placement + Copywriting Contract).
//
// 규칙 (10-UI-SPEC):
//   · 브랜드 레드 사용 금지 — amber 주의 시맨틱(warnAmber/warnAmberBg)만.
//     (브랜드 레드는 긍정 강조/CTA 전용, 문제 상태에 쓰지 않음 — colors.ts.)
//   · "부상 확정" 단정 금지 — "위험 가능성 / ~할 수 있어요" + 전문가 확인 권유.
//   · 플래그 없으면 섹션 전체 OMIT — "안전합니다" 류 안심 카피 금지(거짓 안전 주장).
//   · 토큰만 사용 (하드코딩 색/spacing 금지 — app/CLAUDE.md).
//   · flagType 4종 전부 copy-map 보유 → 10-03/10-04 플래그가 UI 변경 0 으로 자동 렌더.
//   · 29-CONTEXT D-14 — 카드마다 "이렇게 해보세요" 권고(recommendation) 행 보유.
//     권고는 완화 행동 안내일 뿐 부상 확정이 아니며, 정확한 진단은 섹션 하단
//     '강사와 점검' 캡션(EXPERT_REFERRAL)에 위임한다.
//
// 변경 시 10-UI-SPEC Copywriting Contract 동시 갱신.

import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { SafetyFlag, SafetyFlagType } from '../types/analysis';
import { colors, radius, spacing, typography } from '../theme';

const SECTION_TITLE = '부상 위험 신호';
const SECTION_DISCLAIMER =
  '부상을 확정하는 신호가 아니라, 측정값에서 보이는 위험 가능성이에요. 전문가 확인을 권해드려요.';
const EXPERT_REFERRAL = '정확한 판단은 강사 또는 전문가와 함께 확인해 주세요.';

// 29-CONTEXT D-14 — 권고 행 도입구. 부상 확정이 아니라 완화 행동 안내임을 명시.
const RECOMMENDATION_INTRO = '이렇게 해보세요';

// flagType → {title, why, recommendation} 카피 맵 (10-UI-SPEC Copywriting Contract, 4종 전부).
// trunk 의 why 는 D-04 rigid-body 한계 괄호를 반드시 포함한다 (CONTEXT D-04).
// recommendation 은 flagType 별로 결이 다른 구체적 완화 행동을 "~해요/~주세요" 체로 제시
// (29-CONTEXT D-14). 부상 확정 단정 금지 + D-05 금지어 규칙 준용.
const FLAG_COPY: Record<
  SafetyFlagType,
  { title: string; why: string; recommendation: string }
> = {
  asymmetry: {
    title: '좌우 비대칭 신호',
    why: '기준보다 좌우 움직임 차이가 크고, 동작이 흔들리는 구간이 있어요. 한쪽에 무리가 갈 가능성이 있어요.',
    recommendation:
      '약한 쪽 근력과 유연성을 보강하는 운동으로 좌우 균형을 맞추고, 동작 전에 몸을 충분히 풀어 주세요.',
  },
  trunk_hyperextension: {
    title: '허리 부담 가능성',
    why: '허리를 깊게 젖히면서 자세가 불안정한 구간이 보여요. 허리에 부담이 갈 수 있어요. (몸통을 한 덩어리로 추정한 값이라 정확하지 않을 수 있어요.)',
    recommendation:
      '허리만 젖히지 말고 코어와 엉덩이 힘으로 몸통을 함께 받치고, 젖히는 범위는 강사와 함께 조금씩 늘려 주세요.',
  },
  joint_hyperextension: {
    title: '무릎·팔꿈치 과신전 가능성',
    why: '무릎 또는 팔꿈치가 반대로 젖혀지는(역꺾임) 자세가 통제가 흔들리는 구간에서 보여요. 관절에 무리가 갈 수 있어요.',
    recommendation:
      '관절을 끝까지 펴서 잠그지 말고 살짝 힘을 준 상태로 지지하고, 그립과 받치는 자세를 다시 점검해 주세요.',
  },
  level_mismatch: {
    title: '레벨 대비 무리한 동작 가능성',
    why: '입력하신 경력 대비 난이도가 높은 동작이고, 반동·흔들림이 함께 보여요. 단계를 낮춰 연습하는 게 안전할 수 있어요.',
    recommendation:
      '한 단계 쉬운 동작으로 기초를 다진 뒤 올라가고, 지금 동작은 강사 지도 아래에서 연습해 주세요.',
  },
};

// 심각도 높은 순 정렬 (high → medium → low).
const SEVERITY_RANK: Record<string, number> = { high: 3, medium: 2, low: 1 };

function InjuryRiskFlagCard({ flag }: { flag: SafetyFlag }) {
  const copy = FLAG_COPY[flag.flagType];
  if (!copy) return null; // 미지의 flagType — graceful skip (계약 외 값 방어).
  return (
    <View
      style={styles.card}
      accessibilityRole="alert"
      accessibilityLabel={`${copy.title}. ${copy.why}. ${RECOMMENDATION_INTRO}. ${copy.recommendation}`}
    >
      <View style={styles.row}>
        <Ionicons name="warning" size={16} color={colors.warnAmber} />
        <Text style={styles.cardTitle}>{copy.title}</Text>
      </View>
      <Text style={styles.cardWhy}>{copy.why}</Text>
      {/* 29-CONTEXT D-14 — "이렇게 해보세요" 권고 행 (완화 행동 안내, 부상 확정 아님). */}
      <Text style={styles.recoIntro}>{RECOMMENDATION_INTRO}</Text>
      <Text style={styles.reco}>{copy.recommendation}</Text>
    </View>
  );
}

interface InjuryRiskSectionProps {
  flags: SafetyFlag[] | null | undefined;
}

export function InjuryRiskSection({ flags }: InjuryRiskSectionProps) {
  // 플래그 없으면 섹션 전체 OMIT — 안심 카피 금지 (D-08).
  if (!flags || flags.length === 0) return null;
  const sorted = [...flags].sort(
    (a, b) => (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0),
  );
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{SECTION_TITLE}</Text>
      <Text style={styles.disclaimer}>{SECTION_DISCLAIMER}</Text>
      {sorted.map((flag, i) => (
        <InjuryRiskFlagCard key={`${flag.flagType}-${i}`} flag={flag} />
      ))}
      <Text style={styles.referral}>{EXPERT_REFERRAL}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  section: {
    gap: 8,
  },
  sectionTitle: {
    ...typography.sectionTitle, // 20 / 700
    color: colors.textPrimary,
  },
  disclaimer: {
    ...typography.caption, // 12 / 400
    color: colors.textSecondary,
    lineHeight: 18,
  },
  card: {
    backgroundColor: colors.warnAmberBg, // #FFF6E5 amber tint (D-08 시각 구분)
    borderWidth: 1,
    borderColor: colors.warnAmber, // #E6A300
    borderRadius: radius.card, // 15pt
    padding: spacing.cardPadding, // 16pt
    gap: 6,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cardTitle: {
    ...typography.boxLabel, // 15 / 700
    color: colors.warnAmber,
    flexShrink: 1,
  },
  cardWhy: {
    ...typography.caption, // 12 / 400
    color: colors.textPrimary,
    lineHeight: 18,
  },
  recoIntro: {
    ...typography.captionSmall, // 10 / 400 (도입구 — 위험 확정 아님, 행동 안내 라벨)
    color: colors.warnAmber, // amber 시맨틱만 (브랜드 레드 금지)
    marginTop: 2,
  },
  reco: {
    ...typography.caption, // 12 / 400
    color: colors.textPrimary,
    lineHeight: 18,
  },
  referral: {
    ...typography.caption, // 12 / 400
    color: colors.textSecondary,
    lineHeight: 18,
  },
});
