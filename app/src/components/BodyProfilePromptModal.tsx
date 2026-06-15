// 첫 분석 직전 자가입력 권유 시트 (Phase 3, Plan 03-03).
//
// "가벼운 권유" — 절대 강제 X (게스트 우선, CLAUDE.md §2). dismiss 는 동등 3-way:
//   1) [건너뛰기] 버튼   2) 백드롭 탭   3) native back (onRequestClose)
// 셋 모두 onSkip 으로 수렴 → caller(analyze.tsx)가 once-flag(promptDismissedAt) 를
// 세팅하고 보류된 영상으로 분석을 재개한다 (D-06 재권유 0, R2).
//
// [입력하기] 와 [건너뛰기] 는 equal-weight — 건너뛰기는 버려진 회색 링크가 아니라
// 정식 secondary CTA (RESEARCH §C non-forcing 요건).
//
// DimensionDetailModal 의 bottom-sheet 골격(Modal + 백드롭 Pressable + sheet) 재사용.
// 토큰만 사용 (하드코딩 색/spacing/fontSize 금지 — app/CLAUDE.md / design.md §5-3).

import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, layout, radius, spacing, typography } from '../theme';

interface Props {
  visible: boolean;
  onInput: () => void; // [입력하기] → 폼 진입
  onSkip: () => void; // [건너뛰기] / 백드롭 / native back 공통 dismiss
}

export function BodyProfilePromptModal({ visible, onInput, onSkip }: Props) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      // native back = dismiss 3-way 중 하나 → onSkip 으로 수렴.
      onRequestClose={onSkip}
    >
      {/* RN bottom-sheet 정석: 백드롭 위 빈 영역만 Pressable(dismiss), sheet 자체는
          순수 View. 백드롭 탭 = dismiss 3-way 중 하나. */}
      <View style={styles.backdrop}>
        <Pressable
          style={styles.backdropTop}
          onPress={onSkip}
          accessibilityRole="button"
          accessibilityLabel="닫기"
        />
        <View style={styles.sheet} accessibilityViewIsModal>
          <View style={styles.handle} />
          <Text style={styles.title}>더 정확한 코칭을 위해 (선택)</Text>
          <Text style={styles.subtitle}>
            키·경력·통증부위를 알려주면 분석이 더 구체적이에요. 지금 건너뛰어도
            분석은 그대로 진행돼요.
          </Text>

          <Pressable
            onPress={onInput}
            accessibilityRole="button"
            accessibilityLabel="내 몸 정보 입력하기"
            style={({ pressed }) => [styles.primary, pressed && styles.pressed]}
          >
            <Text style={styles.primaryText}>입력하기</Text>
          </Pressable>

          <Pressable
            onPress={onSkip}
            accessibilityRole="button"
            accessibilityLabel="건너뛰고 분석 계속하기"
            style={({ pressed }) => [styles.secondary, pressed && styles.pressed]}
          >
            <Text style={styles.secondaryText}>건너뛰기</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: colors.brandOverlay,
    justifyContent: 'flex-end',
  },
  backdropTop: { flex: 1 },
  sheet: {
    backgroundColor: colors.cardBg,
    borderTopLeftRadius: radius.modal,
    borderTopRightRadius: radius.modal,
    paddingTop: spacing.cardPadding,
    paddingBottom: spacing.cardPadding * 2,
    paddingHorizontal: spacing.screenX,
    gap: 14,
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.divider,
    borderRadius: radius.button,
    alignSelf: 'center',
    marginBottom: 6,
  },
  title: { ...typography.heading, color: colors.textPrimary },
  subtitle: { ...typography.caption, color: colors.textSecondary },
  primary: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 6,
  },
  primaryText: { ...typography.button, color: colors.textWhite },
  secondary: {
    height: layout.ctaHeight,
    borderRadius: radius.button,
    borderWidth: 1,
    borderColor: colors.inputBorder,
    backgroundColor: colors.bg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryText: { ...typography.buttonSecondary, color: colors.textPrimary },
  pressed: { opacity: 0.85 },
});
