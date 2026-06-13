// Phase 4 (04-02 D-08) — 정확도 제한 배지.
//
// 트리거 (canonical, BLOCKER-3 4차 게이트 리뷰):
//   합성 경고 public enum 의 첫 코드를 hasSynthesisWarning helper 로 파생해
//   visible prop 으로 내려보낸다. top-level doc.warnings / result.warnings 에서
//   파생 금지 — 단일 source 는 aiSynthesisMeta.warnings 배열 (analysis.ts
//   SynthesisWarningCode public enum) 만.
//
// 블랙박스 카피 (D-05 R7 4차 게이트 리뷰):
//   내부 코드명 / 기술 용어는 사용자에게 노출 금지. 본 컴포넌트가 화면에
//   렌더하는 문자열은 아래 LINE_OCCLUSION + LINE_SIDE 두 줄만 — 변경 시
//   04-UI-SPEC Copywriting Contract 와 함께 갱신.
//
// Phase 12.5 "추정" 카피와 공존 — DimensionDetailModal / 코칭 팁의 기존
// 추정 표기 (estimateGray + ⓘ Alert) 와 동시 노출 가능, 서로 대체하지 않음.

import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing, typography } from '../theme';

// 카피 상수 — 블랙박스 R7 박제. 변경 시 04-UI-SPEC Copywriting Contract 동시 갱신.
const LINE_OCCLUSION = '가림 구간 정확도가 제한적이에요';
const LINE_SIDE = '측면 관절 추정 오차가 포함될 수 있어요.';

interface AccuracyLimitBadgeProps {
  // canonical: hasSynthesisWarning(result, code) 결과 (caller 파생).
  visible: boolean;
}

export function AccuracyLimitBadge({ visible }: AccuracyLimitBadgeProps) {
  if (!visible) return null;
  return (
    <View
      style={styles.container}
      accessibilityRole="alert"
      accessibilityLabel={`${LINE_OCCLUSION}. ${LINE_SIDE}`}
    >
      <View style={styles.row}>
        <Ionicons name="warning" size={14} color={colors.warnAmber} />
        <Text style={styles.title}>{LINE_OCCLUSION}</Text>
      </View>
      <Text style={styles.description}>{LINE_SIDE}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.accuracyLimitBg, // softBg alias (#F5F5F5)
    borderWidth: 1,
    borderColor: colors.warnAmber, // #E6A300
    borderRadius: radius.card, // 15pt
    paddingVertical: 12,
    paddingHorizontal: spacing.screenX, // 16pt
    marginTop: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    ...typography.boxLabel, // 15pt 700
    color: colors.accuracyLimitText, // warnAmber alias (#E6A300)
  },
  description: {
    ...typography.caption, // 12pt 400
    color: colors.textSecondary,
    marginTop: 4,
  },
});
