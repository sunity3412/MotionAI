// 요약 카드 1장 (32-07 Task 3 — 32-CONTEXT D-01 골격) → quick-260831-lcc 다이어트
// (belle 2026-08-31 결과 화면 재구성 승인 "요약 우선" — 구 D-01/D-09 배치 결정을
// 대체, 수치 규율 자체는 유지).
//
// 구조: 잘한 점(사람 말 헤드라인) + 오늘 고칠 것(topFix 점프 CTA) + 자세히 보기 토글.
// 카드 구조 아날로그 = ScoreBreakdownSection.tsx(카드 스타일 정본).
//
// ★quick-260831-lcc 제거 2건 (복제 제거 — 정보 손실 0):
//   - 점수 소형 배지: 옥타곤 점수 카드가 바로 위(header 직후)에서 점수를 표시하므로
//     중복. 이 카드는 이제 수치를 렌더하지 않는다 (D-09 헤드라인 수치 금지 자동 충족).
//   - '다음 행동' cuePill: DeductionCard cueBox 와 verbatim 동일 텍스트였다
//     (before-screens/07 "목표는 한쪽 무릎은…" 2회 실증) — cueBox 가 유일본.
//     조립(summarySource.selectNextAction)은 무접촉 — 렌더만 제거.
//
// praise 의 evidenceValue/evidenceUnit 은 props 로 통과만 하고 이 카드에서 Text 로
// 렌더하지 않는다 — 근거 수치는 상세 감점 카드의 게이지/배지(32-10)가 담당한다.
// mode3 헤드라인=발전 델타 invariant 는 praise.headline(사람 말, 수치 0)이 담당.
//
// 게임 프레임 요소(목표 게이지·미션 배지 등)는 D-10 확정 범위(안 B = 감점 카드 + 성장
// 탭)에 요약 카드가 포함되지 않으므로 여기서는 미포함.
// 토큰만 사용 (하드코딩 금지, SP-5). 이모지 0. 라이트 전용.

import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, layout, radius, spacing, typography } from '../theme';
import type {
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
  onPressTodayFix,
  onPressExpand,
  expanded,
}: {
  praise: SummaryPraiseResult | null;
  todayFix: SummaryTodayFix | null;
  /** 오늘 고칠 것 탭 → 해당 상세 감점 카드로 점프 (동선은 32-11 배선). */
  onPressTodayFix: () => void;
  /** 펼침 상세 보기 진입. 33-15 (D-17): 재탭 = 접기 (caller 토글). */
  onPressExpand: () => void;
  /**
   * 33-15 (D-17) — 펼침 상태. true 면 라벨 '접기' + chevron-up (재탭 안 접힘
   * 해소 — 토글 상태가 라벨로 드러난다). 미전달(다른 소비처) 시 기존 렌더 유지.
   */
  expanded?: boolean;
}) {
  const todayHeadline = todayFix?.headline ?? TODAY_NONE;
  return (
    <View style={styles.card}>
      {/* 잘한 점(몸 말 헤드라인) — 수치 금지 (D-09). */}
      <View style={styles.praiseWrap}>
        {/* F-4 (33-G) — 상자 이탈 방어 2겹째. 1겹은 summarySource 의 길이·조립
            게이트(승인 상수로 강등)이고, 이건 그마저 뚫렸을 때의 하드 스톱이다.
            승인 카피는 전부 20자 이하라 bodyLg 2줄 안에서 절대 잘리지 않는다. */}
        {/* quick-260831-lcc — hangul-word 줄바꿈: 큰 제목이 "기본 기준/은
            지켰어요"처럼 조사에서 분리되던 것 수리 (RN 0.81 iOS 지원). */}
        <Text
          style={styles.praiseHeadline}
          numberOfLines={2}
          lineBreakStrategyIOS="hangul-word"
        >
          {praise ? praise.headline : HONEST_NO_PRAISE}
        </Text>
        {praise ? null : (
          <Text style={styles.honestSub}>{HONEST_NO_PRAISE_SUB}</Text>
        )}
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
          <Text style={styles.todayHeadline} lineBreakStrategyIOS="hangul-word">
            {todayHeadline}
          </Text>
          <Ionicons name="chevron-forward" size={18} color={colors.textSecondary} />
        </View>
      </Pressable>

      {/* 펼침 상세 진입 (채점 표면 재배치는 32-11). 33-15 (D-17): expanded 시
          '접기' + chevron-up — 재탭이 접기 동작임이 라벨로 드러난다. */}
      <Pressable
        style={styles.expandRow}
        onPress={onPressExpand}
        accessibilityRole="button"
        accessibilityLabel={
          expanded === true ? '분석 상세 접기' : '분석 상세 펼쳐 보기'
        }
        hitSlop={8}
      >
        <Text style={styles.expandText}>
          {expanded === true ? '접기' : '자세히 보기'}
        </Text>
        <Ionicons
          name={expanded === true ? 'chevron-up' : 'chevron-down'}
          size={16}
          color={colors.brand}
        />
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
  praiseWrap: { gap: 4 },
  // 몸 말 헤드라인 — 가장 큼, 수치 금지 (D-09). bodyLg 24/700.
  praiseHeadline: { ...typography.bodyLg, color: colors.textPrimary },
  honestSub: { ...typography.bodySm, color: colors.textSecondary },
  sectionLabel: { ...typography.badge, color: colors.textSecondary },
  todaySection: { gap: 6 },
  todayRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  todayHeadline: { ...typography.bodyMd, color: colors.textPrimary, flex: 1 },
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
