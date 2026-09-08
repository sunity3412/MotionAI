// 요약 탭 카드 — "분석에서 N개 교정할 점이 보여요" + 감점 칩 + 경고 박스 + CTA.
// 피그마 `분석 디자인 업데이트` 시안 1 (belle 09-08).
//
// 치수는 전부 시안 벡터 바운딩 박스 실측이다 (px → pt, k = 390/467.206 = 0.83474).
// 카드 좌표는 **화면**이 아니라 카드 좌상단 기준으로 환산해 두었다 — 카드의 세로
// 위치는 탭 컨테이너(RESULT_TAB_TOP)가 정하고, 여기는 내부 조판만 안다.
//
//   카드      43.7, 498.5, 379.9 × 362.1px  → 36.5, 416.2, 317.1 × 302.3pt
//   헤드라인  카드 top +36.5px → +30.5pt
//   서브      +69.8px → +58.3pt
//   칩 행     +104.1px → +86.9pt   칩 147.8 × 36.0px → 123.4 × 30.1pt, 간격 8.4/9.3px
//   경고 박스 +210.0px → +175.3pt, 334.0 × 130.1px → 278.8 × 108.6pt
//   CTA       화면 top +884.8px → +738.6pt, 379.9 × 71.3px → 317.1 × 59.5pt
//
// 카드 폭 317.1 − 경고 박스 폭 278.8 = 좌우 안쪽 여백 19.2pt.
//
// 색: 브랜드는 #FF4B33 (시안의 #E94D37 기각 — belle 09-08). 나머지는 시안 실측
// 토큰(resultChipBg / resultWarnBg). 하드코딩 색 0.
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius, typography } from '../../theme';
import type { SummaryChip } from '../../lib/resultSummary';

const K = 390 / 467.206;

const D = {
  cardRadius: radius.resultCard,
  cardPadX: 19.2,
  headlineTop: 36.5 * K, // 30.5
  subTop: 69.8 * K, // 58.3 (카드 top 기준)
  chipsTop: 104.1 * K, // 86.9
  chipH: 36.0 * K, // 30.1
  chipMinW: 147.8 * K, // 123.4
  chipGapX: 8.4 * K, // 7.0
  chipGapY: 9.3 * K, // 7.8
  chipPadX: 12,
  warnTop: 210.0 * K, // 175.3
  warnPad: 12,
  cardBottom: 20,
  ctaH: 71.3 * K, // 59.5
  ctaGap: 24, // 카드 아랫변 ~ CTA 윗변 (시안: 884.8 − 860.6px = 24.2px → 20.2pt + 카드 하단 여백)
} as const;

export interface ResultSummaryWarning {
  title: string;
  /** 본문 — 줄바꿈은 배열로 준다(시안은 3줄). 빈 배열이면 제목만. */
  lines: readonly string[];
}

export interface ResultSummaryCardProps {
  /** 교정할 점 개수 — 헤드라인과 CTA 가 같은 수를 쓴다. */
  total: number;
  chips: readonly SummaryChip[];
  /** 칩으로 못 보여준 나머지. 0 이면 '+N' 칩을 그리지 않는다. */
  overflow: number;
  /** 헤드라인 아래 한 줄. */
  subline: string;
  /** 노란 경고 박스. 없으면 렌더하지 않는다 — 없는 경고를 지어내지 않는다. */
  warning?: ResultSummaryWarning | null;
  /** CTA. 미전달 시 버튼을 그리지 않는다. */
  onSeePoints?: () => void;
  /** 칩 탭 — 그 항목의 상세로. 미전달 시 칩은 표시 전용. */
  onChipPress?: (recordId: string) => void;
}

export function ResultSummaryCard({
  total,
  chips,
  overflow,
  subline,
  warning,
  onSeePoints,
  onChipPress,
}: ResultSummaryCardProps) {
  return (
    <View style={styles.wrap}>
      <View style={styles.card}>
        {/* 헤드라인 — 숫자만 브랜드색. 시안이 '5개' 를 빨강으로 띄운다. */}
        <Text style={styles.headline}>
          분석에서 <Text style={styles.headlineNum}>{total}개</Text> 교정할 점이 보여요
        </Text>
        <Text style={styles.sub}>{subline}</Text>

        <View style={styles.chips}>
          {chips.map((c, i) => {
            const body = (
              <Text style={styles.chipText} numberOfLines={1}>
                {c.label} {c.pointsText}
              </Text>
            );
            const key = c.recordId ?? `chip-${i}`;
            return c.recordId && onChipPress ? (
              <Pressable
                key={key}
                onPress={() => onChipPress(c.recordId as string)}
                accessibilityRole="button"
                accessibilityLabel={`${c.label} ${c.pointsText}점 상세 보기`}
                style={styles.chip}
              >
                {body}
              </Pressable>
            ) : (
              <View key={key} style={styles.chip}>
                {body}
              </View>
            );
          })}
          {overflow > 0 ? (
            <View style={[styles.chip, styles.chipMore]}>
              <Text style={[styles.chipText, styles.chipMoreText]}>+{overflow}</Text>
            </View>
          ) : null}
        </View>

        {warning ? (
          <View style={styles.warn}>
            <Text style={styles.warnTitle}>{warning.title}</Text>
            {warning.lines.map((l, i) => (
              <Text key={`warn-${i}`} style={styles.warnBody}>
                {l}
              </Text>
            ))}
          </View>
        ) : null}
      </View>

      {onSeePoints ? (
        <Pressable
          onPress={onSeePoints}
          accessibilityRole="button"
          accessibilityLabel={`교정 포인트 ${total}개 보기`}
          style={({ pressed }) => [styles.cta, pressed && styles.ctaPressed]}
        >
          <Text style={styles.ctaText}>교정 포인트 {total}개 보기 &gt;</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: D.ctaGap },
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: D.cardRadius,
    borderWidth: StyleSheet.hairlineWidth,
    // 시안 벡터는 stroke #19191B 0.48px 다. 그 굵기로는 렌더에서 #C6C6C6 로 읽히고
    // (실측), 앱 카드 관례(design.md §5-4)도 같은 톤의 divider 다 — 토큰을 쓴다.
    borderColor: colors.divider,
    paddingHorizontal: D.cardPadX,
    paddingTop: D.headlineTop,
    paddingBottom: D.cardBottom,
  },
  headline: {
    ...typography.resultHeadline,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  headlineNum: { color: colors.brand },
  sub: {
    ...typography.resultSub,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: D.subTop - D.headlineTop - typography.resultHeadline.fontSize,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: D.chipGapX,
    rowGap: D.chipGapY,
    marginTop: D.chipsTop - D.subTop - typography.resultSub.fontSize,
  },
  chip: {
    minWidth: D.chipMinW,
    height: D.chipH,
    borderRadius: D.chipH / 2, // 시안은 알약 모양
    backgroundColor: colors.resultChipBg,
    paddingHorizontal: D.chipPadX,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipText: {
    ...typography.resultChip,
    color: colors.brand,
  },
  // '+N' 은 감점이 아니라 개수라 회색 (시안 실측 #F4F4F6 ≈ softBg).
  chipMore: { minWidth: 0, backgroundColor: colors.softBg },
  chipMoreText: { color: colors.textMid },
  warn: {
    backgroundColor: colors.resultWarnBg,
    borderRadius: radius.resultBox,
    padding: D.warnPad,
    marginTop: D.warnTop - D.chipsTop - D.chipH * 2 - D.chipGapY,
    alignItems: 'center',
  },
  warnTitle: {
    ...typography.resultWarnTitle,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  warnBody: {
    ...typography.resultWarnBody,
    color: colors.textHi,
    textAlign: 'center',
    marginTop: 4,
  },
  cta: {
    height: D.ctaH,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ctaPressed: { opacity: 0.85 },
  ctaText: {
    ...typography.resultCta,
    color: colors.textWhite,
  },
});
