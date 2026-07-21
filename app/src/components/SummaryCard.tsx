// 요약 카드 1장 (32-07 Task 3 — 32-CONTEXT D-01 골격 + D-09 수치 규칙).
// 결과 화면 첫인상 본체: 잘한 점 1 + 오늘 고칠 것 1 + 다음 행동 1 + 점수 소형 보조.
// 카드 구조 아날로그 = ScoreBreakdownSection.tsx(카드 스타일 정본) + result.tsx 강사
// 섹션(:2009-2028). props 는 summarySource.deriveSummaryContent 반환 형상 + score +
// 점프 콜백 — doc 결합/데이터소스 배선은 32-11 소관(interface-first, result.tsx 무접촉).
//
// ★수치 1곳 규칙 (32-PLAN-REVIEW HIGH + D-01/D-09 동시 충족):
//   요약 카드에서 수치를 렌더하는 곳은 **점수 소형 보조 배지 단 1곳**뿐이다.
//   praise 의 evidenceValue/evidenceUnit 은 props 로 통과만 하고 이 카드에서 Text 로
//   렌더하지 않는다 — 근거 수치는 상세 감점 카드의 게이지/배지(32-10)가 담당한다.
//   이렇게 해야 D-01 '점수 소형 보조 확정'과 D-09 '카드당 수치 한 곳·헤드라인 수치
//   금지'가 동시에 성립한다. mode3 헤드라인=발전 델타 invariant 는 praise.headline
//   (사람 말, 수치 0)이 담당한다.
//
// 게임 프레임 요소(목표 게이지·미션 배지 등)는 D-10 확정 범위(안 B = 감점 카드 + 성장
// 탭)에 요약 카드가 포함되지 않으므로 여기서는 미포함.
// 토큰만 사용 (하드코딩 금지, SP-5). 이모지 0. 라이트 전용.

import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, layout, radius, spacing, typography } from '../theme';
import type {
  SummaryNextAction,
  SummaryPraiseResult,
  SummaryTodayFix,
} from '../lib/summarySource';

// 카피 상수 — praise 근거 부재 시 정직 고지(D-06: 근거 없는 칭찬 금지, 응원 톤 후
// 바로 오늘 고칠 것으로 시선 유도). 변경 시 D-06 취지 유지.
const HONEST_NO_PRAISE = '측정된 잘한 점을 아직 찾지 못했어요';
const HONEST_NO_PRAISE_SUB = '오늘 고칠 것 하나에 집중해봐요';
const TODAY_NONE = '오늘 크게 고칠 점은 없어요';

export function SummaryCard({
  praise,
  todayFix,
  nextAction,
  score,
  onPressTodayFix,
  onPressExpand,
}: {
  praise: SummaryPraiseResult | null;
  todayFix: SummaryTodayFix | null;
  nextAction: SummaryNextAction | null;
  score: number;
  /** 오늘 고칠 것 탭 → 해당 상세 감점 카드로 점프 (동선은 32-11 배선). */
  onPressTodayFix: () => void;
  /** 펼침 상세 보기 진입. */
  onPressExpand: () => void;
}) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const todayHeadline = todayFix?.headline ?? TODAY_NONE;
  return (
    <View style={styles.card}>
      {/* 상단 — 잘한 점(몸 말 헤드라인) + 점수 소형 보조 배지(수치 1곳, 헤드라인 아님) */}
      <View style={styles.headerRow}>
        <View style={styles.praiseWrap}>
          <Text style={styles.praiseHeadline}>
            {praise ? praise.headline : HONEST_NO_PRAISE}
          </Text>
          {praise ? null : (
            <Text style={styles.honestSub}>{HONEST_NO_PRAISE_SUB}</Text>
          )}
        </View>
        <View
          style={styles.scoreBadge}
          accessibilityLabel={`종합 점수 ${clamped}점`}
        >
          <Text style={styles.scoreBadgeText}>{clamped}점</Text>
        </View>
      </View>

      {/* 오늘 고칠 것 — 탭하면 상세 감점 카드로 점프 */}
      <Pressable
        style={styles.todaySection}
        onPress={onPressTodayFix}
        accessibilityRole="button"
        accessibilityLabel={`오늘 고칠 것: ${todayHeadline}. 자세히 보려면 탭하세요`}
        hitSlop={8}
      >
        <Text style={styles.sectionLabel}>오늘 고칠 것</Text>
        <View style={styles.todayRow}>
          <Text style={styles.todayHeadline}>{todayHeadline}</Text>
          <Ionicons name="chevron-forward" size={18} color={colors.textSecondary} />
        </View>
      </Pressable>

      {/* 다음 행동 — 행동 큐(외부 초점). 브랜드색은 '행동'에만 (emphasis 규칙). */}
      {nextAction ? (
        <View style={styles.nextActionWrap}>
          <Text style={styles.sectionLabel}>다음 행동</Text>
          <View style={styles.cuePill}>
            <Text style={styles.cueText}>{nextAction.text}</Text>
          </View>
        </View>
      ) : null}

      {/* 펼침 상세 진입 (채점 표면 재배치는 32-11) */}
      <Pressable
        style={styles.expandRow}
        onPress={onPressExpand}
        accessibilityRole="button"
        accessibilityLabel="분석 상세 펼쳐 보기"
        hitSlop={8}
      >
        <Text style={styles.expandText}>자세히 보기</Text>
        <Ionicons name="chevron-down" size={16} color={colors.brand} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  // 카드 스타일 정본 복제 (ScoreBreakdownSection.tsx:169-176).
  card: {
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.divider,
    padding: spacing.cardPadding,
    gap: 14,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
  },
  praiseWrap: { flex: 1, gap: 4 },
  // 몸 말 헤드라인 — 가장 큼, 수치 금지 (D-09). bodyLg 24/700.
  praiseHeadline: { ...typography.bodyLg, color: colors.textPrimary },
  honestSub: { ...typography.bodySm, color: colors.textSecondary },
  // 점수 소형 보조 배지 — 중립 회색, 헤드라인 아님 (수치 1곳).
  scoreBadge: {
    backgroundColor: colors.softBg,
    borderRadius: radius.listItem,
    paddingVertical: 4,
    paddingHorizontal: 10,
    alignSelf: 'flex-start',
  },
  scoreBadgeText: { ...typography.badge, color: colors.textMid },
  sectionLabel: { ...typography.badge, color: colors.textSecondary },
  todaySection: { gap: 6 },
  todayRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  todayHeadline: { ...typography.bodyMd, color: colors.textPrimary, flex: 1 },
  nextActionWrap: { gap: 6 },
  // 행동 큐 pill — tint 배경 + 브랜드색 (외부 초점 강조).
  cuePill: {
    backgroundColor: colors.brandTint,
    borderRadius: radius.button,
    paddingVertical: 10,
    paddingHorizontal: 12,
    alignSelf: 'flex-start',
  },
  cueText: { ...typography.bodyMdBold, color: colors.brand },
  expandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    borderTopWidth: 1,
    borderTopColor: colors.divider,
    paddingTop: 12,
  },
  expandText: { ...typography.bodySm, color: colors.brand },
});
