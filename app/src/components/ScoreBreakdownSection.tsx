// 점수 계산 내역 섹션 (quick-260702-q8q) — 투명 감점-합산 tally 를 화면에 노출.
//
// belle 실기기 피드백(TestFlight #27, kip-up fault 88점): 점수는 투명 규칙
// (100 − 12 = 88)으로 계산되는데 앱이 내역을 안 보여줘 신뢰가 깎임. 채점 원칙
// ([[scoring-must-be-transparent-deduction-tally]] — "보고서가 −X−Y−Z=50 내역 노출")
// 의 UI 배선. 렌더 가드는 caller(result.tsx: mode1 + deductionBreakdown 존재).
//
// 객관성: 저장된 record 값을 그대로 표기 — 합계 검증(100 + Σpoints ≠ final)이
// 어긋나도 UI 가 숫자를 조작하지 않는다 (있는 그대로 + final 우선).
// 토큰만 사용 (CLAUDE.md §4). 이모지 0. 라이트 전용.

import { StyleSheet, Text, View } from 'react-native';

import { formatDeductionRecord, formatDeductionNumber } from '../lib/deductionLabels';
import { colors, layout, radius, spacing, typography } from '../theme';
import type { DeductionBreakdown } from '../types/analysis';

export function ScoreBreakdownSection({
  breakdown,
}: {
  breakdown: DeductionBreakdown;
}) {
  const gapCount = breakdown.coverageGaps?.length ?? 0;
  return (
    <View style={styles.card}>
      {/* 헤더 행 — baseline (미감점 천장 100, contract.md §10.1) */}
      <View
        style={styles.row}
        accessibilityLabel={`기준 점수 ${breakdown.baseline}점`}
      >
        <Text style={styles.baselineLabel}>기준 점수</Text>
        <Text style={styles.baselineValue}>{breakdown.baseline}</Text>
      </View>

      {/* record 행 목록 — 저장 순서 그대로 (엔진이 결정적 정렬, 재정렬 금지) */}
      {breakdown.records.length === 0 ? (
        <Text style={styles.emptyText}>
          측정 감점 없음 — 기준 점수 그대로예요.
        </Text>
      ) : (
        breakdown.records.map((rec, i) => {
          const row = formatDeductionRecord(rec);
          return (
            <View
              key={`${rec.criterion}-${i}`}
              style={styles.row}
              accessibilityLabel={`${row.label} 감점 ${formatDeductionNumber(Math.abs(rec.points))}점`}
            >
              <View style={styles.recordLeft}>
                <Text style={styles.recordLabel}>{row.label}</Text>
                <Text style={styles.recordDetail}>{row.detailText}</Text>
              </View>
              <Text style={styles.recordPoints}>{row.pointsText}</Text>
            </View>
          );
        })
      )}

      {/* 합계 행 — final = breakdown.final (overallScore 재사용 금지) */}
      <View
        style={[styles.row, styles.finalRow]}
        accessibilityLabel={`종합 ${breakdown.final}점`}
      >
        <Text style={styles.finalLabel}>= 종합</Text>
        <Text style={styles.finalValue}>{breakdown.final}점</Text>
      </View>

      {/* coverage gap 각주 — 정직한 커버리지 노출 (fabricate 금지, ND-06 정신) */}
      {gapCount > 0 && (
        <Text style={styles.footnote}>
          {`측정하지 못해 점수에 반영하지 않은 항목이 ${gapCount}건 있어요.`}
        </Text>
      )}
      {breakdown.fallback === 'quantification_unavailable' && (
        <Text style={styles.footnote}>
          정밀 정량화가 불가해 측정 기하 종합으로 환산했어요.
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  // 기존 result 카드 패턴 mirror (result.tsx styles.card 상당) — 토큰만.
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
    gap: 12,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    width: '100%',
    gap: 12,
  },
  baselineLabel: { ...typography.boxLabel, color: colors.textPrimary },
  baselineValue: { ...typography.boxLabel, color: colors.textPrimary },
  recordLeft: { flex: 1, gap: 2 },
  recordLabel: { ...typography.boxLabel, color: colors.textPrimary },
  // detailText 2줄 허용 — 실측 근거(측정값/허용오차/초과분) 문구.
  recordDetail: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  // 감점 수치 — brand 계열 강조.
  recordPoints: { ...typography.listTitle, color: colors.brand },
  finalRow: {
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    paddingTop: 12,
    alignItems: 'flex-end',
  },
  finalLabel: { ...typography.boxLabel, color: colors.textPrimary },
  finalValue: { ...typography.listTitle, color: colors.brand },
  emptyText: {
    ...typography.caption,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  footnote: {
    ...typography.captionSmall,
    color: colors.textSecondary,
    lineHeight: 16,
  },
});
