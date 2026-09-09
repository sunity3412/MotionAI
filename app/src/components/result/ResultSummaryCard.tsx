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
import { Ionicons } from '@expo/vector-icons';

import { colors, layout, radius, typography } from '../../theme';
import type { SummaryChip } from '../../lib/resultSummary';

const K = 390 / 467.206;

const D = {
  cardRadius: radius.resultCard,
  cardPadX: 19.2,
  headlineTop: 36.5 * K, // 30.5 — 잉크 상단 (아래 라인박스 보정 참조)
  subTop: 69.8 * K, // 58.3 (카드 top 기준) — 잉크 상단
  chipsTop: 104.1 * K, // 86.9
  chipH: 36.0 * K, // 30.1
  chipMinW: 147.8 * K, // 123.4
  chipGapX: 8.4 * K, // 7.0
  chipGapY: 9.3 * K, // 7.8
  chipPadX: 18.9, // 260909-ji1 시안 실측 (이전 12)
  warnTop: 210.0 * K, // 175.3
  warnPadTop: 20.9, // 경고 박스 윗변 → 제목 잉크 상단 (260909-ji1 시안 실측, 이전 12)
  warnPad: 12, // 좌우·아래 — 시안 계기가 없어 이전 값 유지
  // 제목 앞 경고 아이콘 — 시안 잉크 폭 ≈13.4pt. Ionicons 삼각형 잉크는 박스의 약 0.88 → 15.
  warnIconBox: 15,
  warnIconGap: 5, // 아이콘 ↔ 제목 — 시안에 계기가 없어 시각 판단 (PLAN 규칙 4)
  cardBottom: 20,
  ctaH: 71.3 * K, // 59.5
  // 카드 아랫변 ~ CTA 윗변 (시안: 884.8 − 860.6px = 24.2px → 20.2pt). 이전 24 는 px 값을
  // pt 로 환산하지 않고 그대로 넣은 것이었다 (260909-ji1).
  ctaGap: 20.2,
} as const;

// ── 라인박스 보정 (260909-ji1) ───────────────────────────────────────────────────
// 위 D 의 세로 값은 벡터 **잉크** 상단인데, 이전 구현은 그 값을 <Text> **라인박스** 상단
// (paddingTop / marginTop)으로 썼다. 게다가 다음 요소의 marginTop 을 "이전 라인박스 높이
// = fontSize" 로 놓고 뺐는데 실제 라인박스는 fontSize 의 약 1.19 배다. 두 오차가 아래로
// 누적돼 헤드라인 +2.9 / 서브 +5.7 / 칩 +6.1 / 경고박스 +6.0pt 씩 밀렸다(09-09 대조).
//
// 번들 Pretendard 실측(em): hhea asc 0.952 / desc 0.241 / lineGap 0 → 자연 라인 1.193.
// 한글 잉크 상단은 어센더 선에서 Bold 0.153 / Regular 0.162em 아래다 → 0.15 로 통일.
//   라인박스 상단 = 잉크 상단 − fontSize × INK_TOP
// 라인박스 높이는 명시한다 — LINE_H 1.2 ≥ 1.193 이라 RN iOS 가 자연 라인을 가운데 놓는
// 경로를 타고, 기본값에 기대면 기기·폰트마다 어긋난다 (ResultScoreDial 선례).
const INK_TOP = 0.15;
const LINE_H = 1.2;
const headlineLH = typography.resultHeadline.fontSize * LINE_H;
const subLH = typography.resultSub.fontSize * LINE_H;
// 각 요소의 라인박스(뷰는 뷰) 상단 — 카드 top 기준 pt. 뷰(칩·경고 박스)는 보정이 없다.
const T = {
  headline: D.headlineTop - typography.resultHeadline.fontSize * INK_TOP, // 27.5
  sub: D.subTop - typography.resultSub.fontSize * INK_TOP, // 56.6
  chips: D.chipsTop, // 86.9
  warn: D.warnTop, // 175.3
  warnTitle: D.warnPadTop - typography.resultWarnTitle.fontSize * INK_TOP, // 18.9 (박스 top 기준)
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
        <Text style={styles.sub} lineBreakStrategyIOS="hangul-word">
          {subline}
        </Text>

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
            {/* 시안은 제목 앞에 경고 삼각형이 있다 — 구현에 없던 것 (260909-ji1). 이모지가
                아니라 벡터 아이콘이고 색은 제목과 같은 앰버. 장식이라 접근성 트리에서 뺀다. */}
            <View style={styles.warnTitleRow}>
              <Ionicons
                name="warning-outline"
                size={D.warnIconBox}
                color={colors.resultWarnTitle}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
              <Text style={styles.warnTitle}>{warning.title}</Text>
            </View>
            {warning.lines.map((l, i) => (
              <Text
                key={`warn-${i}`}
                style={styles.warnBody}
                lineBreakStrategyIOS="hangul-word"
              >
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
    borderWidth: layout.cardBorderWidth, // design.md §5-4 0.858 — 이전 hairline 은 시안보다 얇았다
    // ★ 이전 주석 "시안 stroke 가 렌더에서 #C6C6C6 로 읽힘" 은 **잘못된 실측**이었다 — 벡터
    // 원문은 #8A8A8B / #6C6C6E 다. 시안 #6D6D6E 그대로 쓴다(페이지 배경 위 4.78:1, colors.ts).
    borderColor: colors.resultCardBorder,
    paddingHorizontal: D.cardPadX,
    paddingTop: T.headline,
    paddingBottom: D.cardBottom,
  },
  headline: {
    ...typography.resultHeadline,
    lineHeight: headlineLH,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  headlineNum: { color: colors.brand },
  sub: {
    ...typography.resultSub,
    lineHeight: subLH,
    color: colors.resultTextSub, // 시안 #D6D6D6 은 1.45:1 라 AA 로 낮춘 값 (colors.ts)
    textAlign: 'center',
    marginTop: T.sub - T.headline - headlineLH, // 5.1
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: D.chipGapX,
    rowGap: D.chipGapY,
    marginTop: T.chips - T.sub - subLH, // 16.5
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
  chipMoreText: { color: colors.resultChipMoreText }, // 시안 #79787E 는 3.91:1 라 AA 로 낮춘 값 (colors.ts)
  warn: {
    backgroundColor: colors.resultWarnBg,
    borderRadius: radius.resultBox,
    padding: D.warnPad,
    paddingTop: T.warnTitle,
    // 칩 2행 아래 — 시안(감점 5개)은 칩이 2행이다. 1행이면 그만큼 위로 붙고 간격은 같다.
    marginTop: T.warn - T.chips - D.chipH * 2 - D.chipGapY, // 20.4
    alignItems: 'center',
  },
  warnTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: D.warnIconGap,
  },
  warnTitle: {
    ...typography.resultWarnTitle,
    color: colors.resultWarnTitle, // 시안 #96773F 는 3.81:1 라 AA 로 낮춘 값 (colors.ts)
    textAlign: 'center',
  },
  warnBody: {
    ...typography.resultWarnBody,
    color: colors.resultWarnBody, // 시안 #79787E 는 3.97:1 라 AA 로 낮춘 값 (colors.ts)
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
