// 결과 화면 첫 진입 코치마크 2종 (32-07 D-07). AccuracyLimitBadge.tsx(렌더 전형)
// + onboarding.ts(1회 플래그) 아날로그. 1회 플래그 기록은 호출부가 coachmark.ts
// helper 로 수행 — 이 컴포넌트는 표시/닫기만 담당한다 (관심사 분리).
//
// 라이트 테마 유지 (CLAUDE.md §4 / design.md §10 — 다크 배경 금지): 어두운 스크림
// 대신 brandTint(연한 브랜드 워시)로 배경을 부드럽게 덮고 탭 캡처만 한다.
// 정확한 앵커 위치(어느 요소 위에 붙일지)는 결과 화면 배선(32-11) 소관 — 여기서는
// 자기완결 오버레이로 두 팁을 세로 스택으로 제시한다.
//
// 토큰만 사용 (하드코딩 금지, SP-5). 이모지 0.

import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, radius, spacing, typography, layout } from '../theme';

// 카피 상수 — 변경 시 32-07 D-07 취지(오늘 고칠 것 1개 강조 + 펼침 안내) 유지.
const COACHMARK_TODAY = '오늘 고칠 건 하나만 보여드려요';
const COACHMARK_EXPAND = '자세한 내용은 펼쳐서 볼 수 있어요';
const DISMISS_HINT = '화면을 탭하면 닫혀요';

interface ResultCoachmarksProps {
  // caller 파생 boolean — hasSeenResultCoachmark() 결과의 반대(아직 안 봤으면 표시).
  visible: boolean;
  // 탭 시 호출. 호출부가 markResultCoachmarkSeen() 기록 + visible=false 전환.
  onDismiss: () => void;
}

export function ResultCoachmarks({ visible, onDismiss }: ResultCoachmarksProps) {
  if (!visible) return null;
  return (
    <Pressable
      style={styles.backdrop}
      onPress={onDismiss}
      accessibilityRole="button"
      accessibilityLabel={`${COACHMARK_TODAY}. ${COACHMARK_EXPAND}. ${DISMISS_HINT}`}
      accessibilityHint="탭하면 코치마크가 닫혀요"
    >
      <View style={styles.bubble}>
        <Ionicons name="flag-outline" size={20} color={colors.brand} />
        <Text style={styles.tipText}>{COACHMARK_TODAY}</Text>
      </View>
      <View style={styles.bubble}>
        <Ionicons name="chevron-down-circle-outline" size={20} color={colors.brand} />
        <Text style={styles.tipText}>{COACHMARK_EXPAND}</Text>
      </View>
      <Text style={styles.dismissHint}>{DISMISS_HINT}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.brandTint, // 연한 브랜드 워시 (다크 스크림 금지 — 라이트 테마)
    justifyContent: 'center',
    paddingHorizontal: spacing.screenX,
    gap: 16,
  },
  bubble: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.cardBg,
    borderRadius: radius.card,
    borderWidth: layout.cardBorderWidth,
    borderColor: colors.brand,
    paddingVertical: 16,
    paddingHorizontal: spacing.cardPadding,
  },
  tipText: {
    ...typography.bodyMd,
    color: colors.textPrimary,
    flex: 1,
  },
  dismissHint: {
    ...typography.bodySm,
    color: colors.textSecondary,
    textAlign: 'center',
  },
});
